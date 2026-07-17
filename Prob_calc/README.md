# Prob_calc — Capas de datos para el cálculo probabilístico de riesgo GEOCENTRO

Infraestructura de **atributos por celda**: rasteriza una sola vez las capas
geoespaciales (Slab2, Vs30, polígonos KMZ propios) sobre la grilla única de
GEOCENTRO, para que toda consulta posterior sea un lookup O(1) por índice de
celda — sin geometría en tiempo de consulta.

## Orden de ejecución

```
# 1. EN TU MÁQUINA/VPS (requiere internet; ~700 MB de descarga temporal):
pip install requests netCDF4 numpy
python3 descargar_datos.py --limpiar
#    -> datos/slab2_cam_dep.npz   (placa de Cocos, Hayes et al. 2018)
#    -> datos/vs30_ca.npz         (Vs30 híbrido recortado, Heath et al. 2020)

# 2. Importar tus polígonos de Google Earth (repetible por capa):
python3 importar_kmz.py mi_zona.kmz --capa zona_volcanica
python3 importar_kmz.py poblados.kmz --capa zonas_pobladas --atributo poblacion

# 3. Construir/reconstruir la tabla maestra (tras cualquier cambio de capa):
python3 enriquecer_celdas.py
#    -> datos/celdas_atributos.csv   (una fila por celda, todas las capas)

# Consultas rápidas:
python3 importar_kmz.py --listar
python3 importar_kmz.py --punto 12.13 -86.25
```

## Archivos

| Archivo | Estado | Función |
|---|---|---|
| `config_grilla.py` | ✔ probado | Definición ÚNICA de la grilla (7–16°N, −93.5–−81.5°, 0.2°). `pronostico_72h.py` debe migrar a importar de aquí. |
| `descargar_datos.py` | ⚠ no ejecutable en sandbox | Slab2 CAM vía API de ScienceBase (URLs dinámicas, no se pudren) + Vs30 global con recorte en ventana (no carga el grd completo en RAM). |
| `importar_kmz.py` | ✔ probado (T1–T4) | KMZ/KML/GeoJSON → rasterización a grilla → `zonas.sqlite` + npz espejo. Huecos por lógica de conjuntos (los compound paths de matplotlib NO restan huecos — verificado). |
| `enriquecer_celdas.py` | ✔ probado (T5–T8) | Tabla maestra + `clasificar_evento()` (cortical/interfaz/intraslab vía Slab2) + clase de sitio NEHRP + amplificación ΔMMI. |
| `test_sintetico.py` | ✔ 8/8 | End-to-end sin internet, con datos sintéticos geométricamente realistas. |

## Advertencias honestas

- `factor_amplificacion_intensidad` (k=1.3, forma log) es un **placeholder
  de orden de magnitud**, no una relación calibrada. Calibrar con reportes
  macrosísmicos locales ("Sentido en:" de OVSICORI) antes de publicar.
- Los umbrales de `clasificar_evento` (±20 km interfaz, 35 km cortical)
  absorben la incertidumbre combinada de profundidad del catálogo y de
  Slab2; son razonables pero revisables cuando tengas estadística propia.
- La rasterización usa el **centroide** de cada celda: polígonos más
  angostos que ~0.2° pueden "saltarse" celdas. Para capas finas (fallas
  individuales), subdividir el polígono o densificar la grilla.
- `descargar_datos.py` no pudo probarse end-to-end desde el sandbox (sin
  acceso a usgs.gov); la estructura de los .grd (nombres de variables x/y/z,
  lon 0–360 en Slab2, profundidad negativa) está manejada con los formatos
  documentados, pero la primera ejecución real puede requerir un ajuste
  menor — los mensajes de error están diseñados para diagnosticarlo rápido.
