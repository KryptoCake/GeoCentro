# Plan de Implementación — Track: dedup_raw_canonical_20260706

**Estado:** En progreso
**Checkpoint pre-implementación:** `50ec1d2`
**Fuente del plan:** [Plan v4.1 de Fable 5](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/implementation_plans_for_agents/Plan%20de%20implementacion%20Fable%20V.%204.1.txt)

---

## Fase 1: Modificar `database.py` — Esquema, funciones core

- [ ] Agregar `compute_t_epoch()` con conversión UTC explícita
- [ ] Agregar `haversine()` y `determinar_pais_coordenadas()` con clamp+Haversine a BBox
- [ ] Agregar `deduplicate_and_sync(raw_id)` con BEGIN IMMEDIATE, score determinista
- [ ] Agregar `recalcular_canonico(canonical_id)` con mediana post-filtrado por agencia
- [ ] Agregar `get_sismo_by_id()` con lookup de rescate en `sismos_raw`
- [ ] Modificar `init_db()`: crear `sismos_raw`, agregar `t_epoch` a `sismos`, activar WAL/busy_timeout/FK
- [ ] Redefinir `save_sismo()`: firma extendida con agencia/feed/scraped_at, insertar en raw + dedup

## Fase 2: Modificar `scraper.py` — Identidad de agencia y feeds

- [ ] Cada scraper pasa `agencia`, `feed`, `scraped_at` al llamar a `save_sismo()`
- [ ] Eliminar fallback estático a `'Costa Rica'` en scrapers OVSICORI
- [ ] Delegar clasificación de país a `determinar_pais_coordenadas()` en `database.py`

## Fase 3: Modificar `app.py` — Endpoint de rescate de IDs

- [ ] Agregar endpoint `/api/sismos/<int:sismo_id>` usando `get_sismo_by_id()`

## Fase 4: Crear `migrate_and_depurate.py` — Migración única

- [ ] Backup en caliente con `sqlite3.Connection.backup()` + `PRAGMA integrity_check`
- [ ] Crear tabla `sismos_raw` + índices
- [ ] Migrar sismos actuales a `sismos_raw` (calcular t_epoch, derivar agencia/feed del campo tipo)
- [ ] Validar mapeo de tipos con `SELECT DISTINCT tipo, COUNT(*)` antes de procesar
- [ ] Vaciar `sismos` y reprocesar desde `sismos_raw` ORDER BY t_epoch, id
- [ ] Suite de aserciones A1–A8
- [ ] Reporte final: raw, canónicos, factor de dedup, conteos por país

## Fase 5: Verificación

- [ ] Ejecutar migración y validar aserciones
- [ ] Ejecutar `verify_all.sh`
- [ ] Verificación manual: timeline, mapa, badges, rescate de IDs
- [ ] Commit de cierre del track con checkpoint

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
