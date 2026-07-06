# Especificación: Deduplicación Raw/Canónica de Sismos

## Problema

El catálogo de sismos de GeoCentro sufre de duplicación multi-agencia (~4-71% dependiendo del período). El mismo evento sísmico se registra múltiples veces porque cada agencia (INETER, OVSICORI recientes, OVSICORI sentidos) lo reporta de forma independiente con ligeras diferencias en coordenadas, magnitud y tiempo de origen. Adicionalmente, la asignación de país se basa en texto de la descripción y no en coordenadas, causando clasificaciones erróneas para sismos lejanos (telesismos).

## Origen de la Especificación

El plan fue diseñado iterativamente a través de 4 rondas de revisión técnica con el modelo Claude Fable 5 (Anthropic). Las observaciones originales y las iteraciones del plan se encuentran en:

- `implementation_plans_for_agents/observaciones de Fable 5.txt` — Observaciones iniciales sobre la BD
- `implementation_plans_for_agents/plan_deduplicacion_v4_final.md` — Plan v4.0
- `implementation_plans_for_agents/Plan de implementacion Fable V. 4.1.txt` — **Plan v4.1 definitivo**

## Decisiones de Diseño Cerradas (D1–D9)

Ver tabla completa en el plan v4.1. Resumen:

1. Capa cruda inmutable (`sismos_raw`) + canónica deduplicada (`sismos`)
2. Matching por `t_epoch` (Unix UTC), ventana ±45 s
3. Distancia adaptativa continua: `clamp(60 + 40·(max_mag − 4.0), 60, 250)` km
4. Magnitud canónica = mediana de un reporte por institución (no por feed)
5. Columnas `agencia` (institución) y `feed` (trazabilidad) separadas
6. País por distancia mínima al bounding box (clamp + Haversine)
7. Concurrencia: WAL + busy_timeout + BEGIN IMMEDIATE
8. IDs canónicos heredados del raw fundador e inmutables
9. Desempates deterministas: ORDER BY scraped_at DESC, id DESC

## Archivos Impactados

- `database.py` — Esquema, funciones de geoclasificación, deduplicación, rescate de IDs
- `scraper.py` — Pasar agencia/feed/scraped_at; eliminar fallback a Costa Rica
- `app.py` — Endpoint de rescate de IDs
- `migrate_and_depurate.py` — Script de migración única con suite de 8 aserciones

## Criterio de Rollback

Restaurar `geocentro.db.bak` creado por el script de migración + revertir al checkpoint git `50ec1d2`.
