# Plan de Implementación Definitivo — GEOCENTRO
# Deduplicación de sismos con capa Raw/Canónica y geoclasificación por coordenadas

**Versión:** 4.0 (consolidación final de cuatro rondas de revisión técnica)
**Objetivo:** Eliminar la duplicación multi-agencia del catálogo (~50–75% de los
registros actuales), corregir la asignación de país por coordenadas, y hacerlo
de forma no destructiva, reproducible, transaccionalmente segura y con
integridad referencial de IDs históricos.

---

## 0. Decisiones de diseño (cerradas — no reabrir sin causa)

| # | Decisión | Razón |
|---|----------|-------|
| D1 | Dos tablas: `sismos_raw` (todo reporte de toda agencia, inmutable) y `sismos` (canónica deduplicada) | Preservación científica; permite regenerar la canónica si cambia la heurística |
| D2 | Matching temporal por `t_epoch` (INTEGER, Unix UTC), ventana **±45 s** | ±45 s cubre discrepancias entre agencias (<10 s típico) sin fusionar réplicas reales (que ocurren a 1–2 min); epoch evita el bug de medianoche de comparar fecha/hora como texto |
| D3 | Distancia adaptativa **continua**: `dist_limit = clamp(60 + 40·(max_mag − 4.0), 60, 250)` km, con `max_mag = max(M_entrante, M_candidato)` | Sin discontinuidad en M5.0; escala con la zona de ruptura; simétrica al orden de llegada |
| D4 | Magnitud canónica = **mediana** de un reporte por **institución** (no por feed), redondeada a 1 decimal | El máximo sesga el b-value hacia arriba; las revisiones múltiples de una agencia no deben votar varias veces |
| D5 | Dos columnas de origen: `agencia` (institución: `INETER`, `OVSICORI`) y `feed` (`INETER`, `OVSICORI_REC`, `OVSICORI_SEN`, `HISTORICO`) | La dedup y la mediana operan sobre `agencia`; `feed` es trazabilidad. Evita que OVSICORI vote dos veces por tener dos feeds |
| D6 | País por **distancia mínima al bounding box** de cada país (clamp + Haversine), umbral 500 km; keywords solo para telesismos | Coordenadas son el dato duro; los centroides fallan en países alargados (Panamá, Honduras) y en el Golfo de Fonseca |
| D7 | Concurrencia: `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`, transacciones `BEGIN IMMEDIATE` | Transacciones deferred no evitan la carrera SELECT-luego-INSERT entre scrapers paralelos de n8n |
| D8 | El canónico **hereda el `id`** del reporte representativo; lookup de rescate para IDs de duplicados | No romper URLs/alertas ya publicadas |
| D9 | Desempates deterministas en todo: `ORDER BY scraped_at DESC, id DESC` | La migración debe ser reproducible; los históricos comparten `scraped_at` aproximado |

---

## 1. Esquema de base de datos (`database.py :: init_db`)

```sql
-- Tabla cruda: TODO reporte que llega, de cualquier agencia. Nunca se borra.
CREATE TABLE IF NOT EXISTS sismos_raw (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_utc           TEXT NOT NULL,
    hora_utc            TEXT NOT NULL,
    t_epoch             INTEGER NOT NULL,      -- Unix UTC del tiempo de ORIGEN del sismo
    latitud             REAL NOT NULL,
    longitud            REAL NOT NULL,
    profundidad         REAL,
    magnitud            REAL NOT NULL,
    tipo                TEXT,                  -- tipo de magnitud (MW/ML/MC/...)
    descripcion         TEXT,
    pais                TEXT,
    hash_id             TEXT,
    agencia             TEXT NOT NULL,         -- 'INETER' | 'OVSICORI'  (institución)
    feed                TEXT NOT NULL,         -- 'INETER' | 'OVSICORI_REC' | 'OVSICORI_SEN' | 'HISTORICO'
    scraped_at          INTEGER NOT NULL,      -- Unix UTC del momento de INGESTA
    sismo_canonical_id  INTEGER REFERENCES sismos(id)  -- NULL hasta deduplicar
);
CREATE INDEX IF NOT EXISTS idx_raw_tepoch ON sismos_raw(t_epoch);
CREATE INDEX IF NOT EXISTS idx_raw_canonical ON sismos_raw(sismo_canonical_id);

-- Tabla canónica: conserva el esquema actual de `sismos` + t_epoch
ALTER TABLE sismos ADD COLUMN t_epoch INTEGER;   -- (en migración; NOT NULL lógico)
CREATE INDEX IF NOT EXISTS idx_sismos_tepoch ON sismos(t_epoch);

PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
PRAGMA foreign_keys=ON;
```

---

## 2. Funciones nuevas en `database.py`

### 2.1 Conversión UTC explícita — NUNCA depender de la zona del sistema

```python
from datetime import datetime, timezone

def compute_t_epoch(fecha_utc: str, hora_utc: str) -> int:
    """'2026-07-05', '20:37:33' -> epoch Unix. UTC EXPLÍCITO:
    strptime produce datetime naive; .timestamp() sobre naive usa la zona
    LOCAL del sistema (bug latente si el VPS no corre en UTC)."""
    dt = datetime.strptime(f"{fecha_utc} {hora_utc}", "%Y-%m-%d %H:%M:%S")
    return int(dt.replace(tzinfo=timezone.utc).timestamp())
```

### 2.2 Geoclasificación — `determinar_pais_coordenadas(lat, lon, descripcion)`

1. Definir BBOX continentales **exclusivos** (no solapados) para GT, SV, HN, NI, CR, PA.
2. Para cada país: `d = haversine(lat, lon, clamp(lat, box), clamp(lon, box))`
   (distancia mínima del punto a la caja; 0 si cae dentro).
3. País de distancia mínima gana si `d <= 500 km`.
4. Si `d > 500 km`: buscar keywords de países lejanos en `descripcion`
   (Venezuela, Colombia, México, Ecuador, Guinea-Bissau, Perú, Chile...).
   Sin match → `'Otros'`.
5. El país se calcula SIEMPRE aquí; los scrapers nunca lo asignan por defecto.

### 2.3 Deduplicación en caliente — `deduplicate_and_sync(raw_id)`

```
BEGIN IMMEDIATE
  raw = SELECT * FROM sismos_raw WHERE id = raw_id

  candidatos = SELECT * FROM sismos
               WHERE t_epoch BETWEEN raw.t_epoch - 45 AND raw.t_epoch + 45

  match = None; mejor_score = inf
  PARA cada c EN candidatos:
      max_mag = max(raw.magnitud, c.magnitud)
      dist_limit = clamp(60 + 40*(max_mag - 4.0), 60, 250)
      d = haversine(raw, c)
      SI d <= dist_limit:
          score = d/dist_limit + abs(raw.t_epoch - c.t_epoch)/45   # determinista
          SI score < mejor_score: match, mejor_score = c, score

  SI match IS None:
      INSERT INTO sismos (...)  VALUES (datos de raw, pais recalculado)
      canonical_id = nuevo id
  SINO:
      canonical_id = match.id
      recalcular_canonico(canonical_id, incluyendo raw)   # ver 2.4

  UPDATE sismos_raw SET sismo_canonical_id = canonical_id WHERE id = raw_id
COMMIT
```

Notas:
- Si hay varios candidatos válidos, gana el de menor `score` (regla determinista;
  ver D9). Nunca depender del orden físico de filas.
- `recalcular_canonico` se ejecuta también cuando llega una REVISIÓN de un
  evento ya deduplicado: el canónico se actualiza, no queda congelado en la
  estimación preliminar.

### 2.4 Recalcular canónico — `recalcular_canonico(canonical_id)`

```
grupo = SELECT * FROM sismos_raw WHERE sismo_canonical_id = canonical_id
        (o que están por asociarse)

# Un solo reporte por INSTITUCIÓN: el más reciente, con desempate determinista
por_agencia = para cada agencia distinta en grupo:
                  ORDER BY scraped_at DESC, id DESC LIMIT 1

magnitud_canonica = round(mediana([r.magnitud for r in por_agencia]), 1)

representativo = elegir de por_agencia según:
    1. jerarquía por país del evento:
         Costa Rica  -> OVSICORI > INETER
         Nicaragua   -> INETER > OVSICORI
         otros       -> INETER > OVSICORI
    2. tipo de magnitud: MW > ML > MC > otros
    3. scraped_at DESC, id DESC

UPDATE sismos SET
    lat/lon/profundidad/descripcion/tipo/fecha/hora/t_epoch = del representativo,
    magnitud = magnitud_canonica,
    pais     = determinar_pais_coordenadas(rep.lat, rep.lon, rep.descripcion)
WHERE id = canonical_id
```

### 2.5 Rescate de IDs — `get_sismo_by_id(sismo_id)`

```
fila = SELECT FROM sismos WHERE id = ?
SI fila: RETORNAR fila
raw = SELECT FROM sismos_raw WHERE id = ? AND sismo_canonical_id IS NOT NULL
SI raw: RETORNAR SELECT FROM sismos WHERE id = raw.sismo_canonical_id
RETORNAR None
```

### 2.6 Redefinir `save_sismo(...)`

Firma extendida con `agencia`, `feed`, `scraped_at`. Inserta en `sismos_raw`
(calculando `t_epoch` con `compute_t_epoch`) y llama `deduplicate_and_sync`.
Transparente para el resto del código: la UI sigue leyendo `sismos`.

---

## 3. Cambios en `scraper.py`

- Cada scraper pasa explícitamente su identidad y momento de ingesta:
  - INETER: `agencia='INETER', feed='INETER'`
  - OVSICORI recientes: `agencia='OVSICORI', feed='OVSICORI_REC'`
  - OVSICORI sentidos: `agencia='OVSICORI', feed='OVSICORI_SEN'`
  - En todos: `scraped_at = int(datetime.now(timezone.utc).timestamp())`
- **Eliminar** todo fallback estático a `'Costa Rica'` (u otro país) en los
  scrapers de OVSICORI. El país lo deriva `determinar_pais_coordenadas` en
  `database.py`, siempre.

---

## 4. Cambios en `app.py`

- Endpoint `/api/sismos/<int:sismo_id>` (y toda búsqueda interna por ID) usa
  `database.get_sismo_by_id` → los IDs de reportes duplicados redirigen
  transparentemente a su canónico. Ningún enlace histórico muere.

---

## 5. Script de migración — `migrate_and_depurate.py` (una sola ejecución)

1. **Backup en caliente**: `src.backup(dst)` de `sqlite3` (compatible con WAL;
   una copia de archivo ingenua sobre WAL activo puede quedar inconsistente).
   Verificar el `.bak` con `PRAGMA integrity_check` antes de continuar.
2. Crear `sismos_raw` + índices; agregar `t_epoch` + índice a `sismos`;
   activar WAL.
3. Copiar `sismos` → `sismos_raw` conservando `id` y `hash_id`:
   - `t_epoch = compute_t_epoch(fecha_utc, hora_utc)`
   - `agencia`/`feed` por **heurística del campo `tipo`** — ⚠ SUPUESTO A
     VALIDAR: antes de correr el lote, imprimir `SELECT DISTINCT tipo, COUNT(*)`
     de la BD real y confirmar el mapeo con el operador. Registros no mapeables
     → `feed='HISTORICO'` con la mejor agencia inferible.
   - `scraped_at = t_epoch` (aproximación histórica), `sismo_canonical_id = NULL`.
4. Vaciar `sismos`.
5. Procesar todos los raw **`ORDER BY t_epoch, id`** (nunca por fecha/hora
   texto — mismo bug de medianoche del matching, en el ORDER BY), llamando
   `deduplicate_and_sync`. Al crear cada canónico nuevo, **forzar
   `sismos.id = id del representativo`** (preservación de IDs, D8).
6. Ejecutar la suite de aserciones (sección 6). Si alguna falla → informar y
   NO dar por buena la migración.
7. Reportar: total raw, total canónicos, factor de deduplicación, conteos por
   país antes/después, y los 10 grupos más grandes para inspección visual.

**Rollback:** detener servicio → restaurar `geocentro.db.bak` → reiniciar.
El script debe imprimir esta instrucción al inicio y al fallar.

---

## 6. Suite de aserciones (dentro del script de migración)

```python
# A1 — Conversión UTC. El valor esperado se GENERA, no se codifica a mano
#      (una constante manual equivocada haría "corregir" código correcto):
import calendar, time
esperado = calendar.timegm(time.strptime("2026-01-01 00:00:00", "%Y-%m-%d %H:%M:%S"))
assert compute_t_epoch("2026-01-01", "00:00:00") == esperado == 1767225600

# A2 — Doblete real del 26-06-2026: NO fusionar.
#      Honduras M5.9 05:57:03 (13.2034,-87.7912, 85 km) y
#      Masachapa M5.x 05:57:26-27 (11.95,-86.539 / 11.7676,-86.5573, 99-112 km).
#      Separación ~194-208 km; dist_limit(max_mag=5.9)=136 km -> 2 canónicos.
assert son_eventos_distintos(honduras_id, masachapa_id)

# A3 — Los reportes de Masachapa entre sí (1 s, ~20 km): SÍ fusionar en uno.

# A4 — Guanacaste 09-06 21:01:33 (5 reportes, M5.1-5.5): un solo canónico.
#      Magnitud esperada = mediana POST-filtrado (un reporte por institución),
#      calculada por el propio test desde los raw, no fijada a mano.

# A5 — Telesismos: el M7.1 en (10.407, -68.493) y el M6.4 en (6.04, -21.57)
#      NO se clasifican 'Costa Rica' (esperado: 'Venezuela'/'Otros').

# A6 — Golfo de Fonseca: un punto de prueba en el golfo se asigna al país
#      cuyo bbox esté más cerca, no al de centroide más compacto.

# A7 — Reproducibilidad: correr la deduplicación dos veces sobre el mismo
#      raw produce idéntico conjunto de canónicos (mismos ids, mismas
#      magnitudes). Verifica los desempates deterministas (D9).

# A8 — Rescate de IDs: el id de un reporte duplicado no-representativo
#      resuelve al canónico vía get_sismo_by_id.
```

---

## 7. Plan de verificación

**Automática:** correr `migrate_and_depurate.py` (aserciones A1–A8 + reporte de
factor de deduplicación; sanity check de orden de magnitud: reducción de
50–75%, NO cifra objetivo). Luego `verify_all.sh` para integridad física.

**Manual:** levantar `app.py`; verificar timeline y mapa sin duplicados
visuales; badges de país correctos; abrir por URL el ID de un duplicado
conocido y confirmar la redirección al canónico; insertar manualmente un
reporte de prueba duplicado vía `save_sismo` y confirmar que la dedup en
caliente lo asocia sin crear canónico nuevo.

**Post-despliegue (primera semana):** monitorear la razón raw/canónicos diaria.
Si se acerca a 1.0, los scrapers no están solapando (bien) o el matching no
encuentra pares (revisar); si supera ~4, sospechar ventana demasiado agresiva
o un feed nuevo duplicando.
