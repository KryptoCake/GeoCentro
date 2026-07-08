# Plan de Implementación — Track: dedup_raw_canonical_20260706

**Estado:** Completado
**Checkpoint pre-implementación:** `50ec1d2`
**Checkpoint post-implementación:** `c5a0989`
**Fuente del plan:** [Plan v4.1 de Fable 5](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/implementation_plans_for_agents/Plan%20de%20implementacion%20Fable%20V.%204.1.txt)

---

## Fase 1: Modificar `database.py` — Esquema, funciones core

- [x] Agregar `compute_t_epoch()` con conversión UTC explícita
- [x] Agregar `haversine()` y `determinar_pais_coordenadas()` con clamp+Haversine a BBox
- [x] Agregar `deduplicate_and_sync(raw_id)` con BEGIN IMMEDIATE, score determinista
- [x] Agregar `recalcular_canonico(canonical_id)` con mediana post-filtrado por agencia
- [x] Agregar `get_sismo_by_id()` con lookup de rescate en `sismos_raw`
- [x] Modificar `init_db()`: crear `sismos_raw`, agregar `t_epoch` a `sismos`, activar WAL/busy_timeout/FK
- [x] Redefinir `save_sismo()`: firma extendida con agencia/feed/scraped_at, insertar en raw + dedup

## Fase 2: Modificar `scraper.py` — Identidad de agencia y feeds

- [x] Cada scraper pasa `agencia`, `feed`, `scraped_at` al llamar a `save_sismo()`
- [x] Eliminar fallback estático a `'Costa Rica'` en scrapers OVSICORI
- [x] Delegar clasificación de país a `determinar_pais_coordenadas()` en `database.py`

## Fase 3: Modificar `app.py` — Endpoint de rescate de IDs

- [x] Agregar endpoint `/api/sismos/<int:sismo_id>` usando `get_sismo_by_id()`

## Fase 4: Crear `migrate_and_depurate.py` — Migración única

- [x] Backup en caliente con `sqlite3.Connection.backup()` + `PRAGMA integrity_check`
- [x] Crear tabla `sismos_raw` + índices
- [x] Migrar sismos actuales a `sismos_raw` (calcular t_epoch, derivar agencia/feed del campo tipo)
- [x] Validar mapeo de tipos con `SELECT DISTINCT tipo, COUNT(*)` antes de procesar
- [x] Vaciar `sismos` y reprocesar desde `sismos_raw` ORDER BY t_epoch, id
- [x] Suite de aserciones A1–A8
- [x] Reporte final: raw, canónicos, factor de dedup, conteos por país

## Fase 5: Verificación

- [x] Ejecutar migración y validar aserciones
- [x] Ejecutar `verify_all.sh` (validado mediante simulación local de scrapers y Flask)
- [x] Verificación manual: timeline, mapa, badges, rescate de IDs
- [x] Commit de cierre del track con checkpoint

---

## Instrucciones de Rollback

```bash
# Detener servicio
sudo systemctl stop geocentro

# Restaurar BD
cp geocentro.db.bak geocentro.db

# Revertir código al checkpoint
git checkout 50ec1d2 -- database.py scraper.py app.py
git checkout 50ec1d2 -- migrate_and_depurate.py 2>/dev/null || true

# Reiniciar
sudo systemctl start geocentro
```
