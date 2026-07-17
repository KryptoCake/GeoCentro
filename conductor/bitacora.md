# Bitácora de Sesiones de Desarrollo (Conductor)

Este archivo registra el historial de sesiones de desarrollo y los hitos alcanzados por el agente Antigravity en el proyecto GeoCentro.

---

## Sesión: 8 de junio de 2026

### 1. Correcciones de Control de Calidad (UAT)
* **Enlaces de "Ver Fuente" (NHC):**
  * **Causa:** Las alertas guardadas previamente contenían URLs relativas que se resolvían localmente en el servidor, provocando recargas o errores 404 locales.
  * **Solución:**
    * Agregamos normalización de URLs en **[scraper.py](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/scraper.py)** para garantizar rutas absolutas antes del guardado.
    * Implementamos una limpieza automática de alertas con enlaces corruptos en **[database.py](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/database.py)** (`init_db`).
    * Añadimos un fallback redundante en **[clima.js](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/static/js/clima.js)** para asegurar que los enlaces siempre apunten a dominios válidos con `target="_blank"`.
* **Interactividad de la Etiqueta "Otros":**
  * **Causa:** La etiqueta de país "Otros" (y las demás etiquetas) eran texto plano estático.
  * **Solución:**
    * Convertimos los badges de país en enlaces interactivos a `/historical?pais=NombreDelPais`.
    * Añadimos soporte en **[historical.js](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/static/js/historical.js)** para capturar parámetros de consulta. Al recibir `?pais=Otros`, cambia automáticamente la visualización al feed global **USGS (Global)** y filtra la tabla e histogramas al instante.
    * Enriquecimos los estilos de hover y cursor pointer de las insignias en **[style.css](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/static/css/style.css)**.

### 2. Corrección del Feed de Noticias en Portada
* **Problema:** El feed de noticias de la Portada mostraba únicamente alertas climáticas recientes, ocultando por completo las alertas de sismos.
* **Causa:** La consulta a la API de noticias `/api/news?limit=6` sin categoría retornaba los boletines climáticos más recientes de la NOAA (los cuales son muy frecuentes), desplazando los sismos geológicos anteriores.
* **Solución:** Modificamos **[main.js](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/static/js/main.js)** para consultar `/api/news?categoria=general&limit=6`, aislando las noticias geológicas y sísmicas en la Portada, y dejando el monitoreo meteorológico de forma exclusiva en la sección **Clima** (`/clima`).

### 3. Checkpoint de Conductor y Subida a GitHub
* **Cierre de Track:** Marcamos como completados todos los ítems de la Fase 3 del despliegue en VPS y cerramos la pista de despliegue en **[tracks.md](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/conductor/tracks.md)** y **[plan.md](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/conductor/tracks/deploy_vps_20260522/plan.md)** bajo el checkpoint de versión `9b7f2fc` y `fc36c03`.
* **Sincronización:** Integramos los cambios con la rama remota de GitHub (`origin/main`) mediante pull rebase y resolvimos los conflictos de planificación de forma exitosa. Subimos los commits definitivos (incluyendo la corrección del feed de la portada con SHA: `e86afa5`).

### 4. Plan de Despliegue VPS
* Diseñamos un plan de despliegue y actualización continua en el archivo **[vps_agent_deployment_plan.md](file:///C:/Users/PC/.gemini/antigravity/brain/98522864-9897-4022-8619-0c0dd78548c7/vps_agent_deployment_plan.md)** para que el agente que opera en la VPS de Hostinger aplique la actualización en producción sin caídas del servicio.

---

## Sesión: 10 de junio de 2026

### 1. Sistema de Respaldos de la VPS (Opción 1)
* **Objetivo:** Implementar un sistema de respaldo diario automático y rotativo para base de datos y archivos de GeoCentro.
* **Implementación:**
  * Creado **[backup_vps.py](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/backup_vps.py)**, un script portable de Python que realiza el respaldo en caliente de la base de datos SQLite con `sqlite3.Connection.backup()`, empaqueta en `.tar.gz`, excluye carpetas de desarrollo/pesadas (`venv`, `.git`, `__pycache__`), y aplica una retención de 7 días.
  * Modificado **[setup_cron.sh](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/setup_cron.sh)** para registrar el cron job diario a las 2:00 AM usando el Python del entorno virtual.
  * Actualizado **[verify_all.sh](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/verify_all.sh)** para incluir la validación de la configuración de respaldos y el listado de archivos en la sección 5.
  * Actualizado **[.gitignore](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/.gitignore)** para omitir la carpeta local de pruebas `backups/`.
* **Pruebas y Verificación:**
  * Ejecución manual de `backup_vps.py` exitosa localmente.
  * Integridad de la base de datos en el archivo comprimido validada exitosamente mediante `PRAGMA integrity_check;` en Python.
* **Sincronización:** Stage y commit de los archivos (`.gitignore`, `backup_vps.py`, `setup_cron.sh`, `verify_all.sh`, bitácora y plan de la sesión). Sincronizado y subido al repositorio.

### 2. Importación de Sismos Históricos (2016-2017)
* **Objetivo:** Integrar 2,804 registros de sismos recopilados en 2016-2017 en la base de datos de GeoCentro.
* **Implementación:**
  * Creado el script de migración **[migrate_2016_backup.py](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/migrate_2016_backup.py)** para procesar el dump SQL `backups/b8_18981120_Events.sql`.
  * Conversión de fechas a `YYYY-MM-DD` y coordenadas a números flotantes con signo (eliminación de sufijos `N`, `S`, `E`, `W`).
  * Normalización y separación de magnitudes (ej: `2.3MW` -> `2.3` y tipo `MW`).
  * Limpieza automática de mojibake (caracteres extraños por codificación sucesiva) de los nombres de las regiones.
  * Clasificación heurística de país con fallback a `Nicaragua` (al ser scraping local de INETER).
  * Prevención robusta de duplicados mediante la comprobación de hash SHA-256 única del sismo.
* **Pruebas y Verificación:**
  * Se ejecutó el script exitosamente. Se importaron **2,803 registros nuevos** a la base de datos `geocentro.db` (1 registro falló debido a una errata de coordenadas en el dump original `11:25N`, lo cual fue solucionado posteriormente).
  * Una segunda pasada del script omitió los 2,803 registros y cargó con éxito el registro restante reparado, verificando el funcionamiento del control de duplicados.
  * El conteo total de sismos locales incrementó de **436 a 3,239** en la base de datos de desarrollo.
* **Sincronización:** Stage, commit y push de las herramientas de migración y planes al repositorio remoto.

---

## Sesión: 8 de julio de 2026

### 1. Auditoría y Deduplicación del Catálogo de Sismos (Capa Raw/Canónica)
* **Objetivo:** Implementar el plan de deduplicación definitivo v4.1 (diseñado con Fable 5) para eliminar la redundancia multi-agencia de sismos, corregir la geoclasificación por coordenadas y garantizar la estabilidad de los enlaces históricos de la base de datos de GeoCentro.
* **Implementación:**
  * **[database.py](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/database.py):**
    * Creamos la tabla `sismos_raw` (capa cruda e inmutable de reportes) y agregamos `t_epoch` (epoch UTC) e índices a ambas tablas.
    * Activamos modo `WAL` y `busy_timeout=5000` para concurrencia segura ante scrapers de n8n.
    * Implementamos geoclasificación robusta continental mediante **clamping + Haversine** a los bounding boxes exclusivos de los 6 países centroamericanos (umbral 500 km).
    * Desarrollamos matching atómico con ventana de $\pm45$s y distancia adaptativa continua con score determinista normalizado.
    * Definimos la magnitud canónica como la **mediana** post-filtrado por agencia, impidiendo que una agencia vote múltiples veces si tiene feeds duplicados.
    * Rediseñamos `save_sismo` bajo transacciones `BEGIN IMMEDIATE` atómicas e implementamos rescate transparente de IDs en `get_sismo_by_id`.
  * **[scraper.py](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/scraper.py):**
    * Retiramos el fallback estático a `'Costa Rica'` de OVSICORI.
    * Modificamos los scrapers para registrar el epoch Unix (`scraped_at`), la fuente/ feed de ingesta (`feed`) y la institución (`agencia`).
  * **[app.py](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/app.py):**
    * Agregamos el endpoint `/api/sismos/<int:sismo_id>` que utiliza `database.get_sismo_by_id` para resolver reportes crudos antiguos.
  * **[migrate_and_depurate.py](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/migrate_and_depurate.py):**
    * Script de migración única: realiza backup en caliente con `sqlite3.Connection.backup()`, inicializa el esquema, clona el histórico a raw, vacía y reprocesa en lote ordenado por `t_epoch` llamando a la deduplicación atómica.
* **Pruebas y Verificación:**
  * Se ejecutó `migrate_and_depurate.py` con éxito rotundo.
  * **Suite de Aserciones:** Pasaron las 8 aserciones de regresión: conversión UTC (A1), doblete del 26-06 (A2), Masachapa fusionados (A3), Guanacaste 09-06 magnitud mediana post-filtro (A4), exclusión de telesismos de Costa Rica (A5), clasificación del Golfo de Fonseca (A6), reproducibilidad/idempotencia en lote limpio (A7) y redirección de IDs (A8).
  * El catálogo local depuró **64 duplicados** (factor 1.9%) y corrigió la distribución geográfica (eliminó 162 sismos incorrectamente marcados como `'Otros'`, asignando 507 nuevos sismos de forma precisa a Honduras y otros países centroamericanos).
  * El scraper local (`scraper.py`) corrió y añadió 182 sismos deduplicando en caliente en transacciones atómicas.
  * La aplicación local (`app.py`) levantó correctamente en el puerto 5000 sin fallos de importación.
* **Sincronización:** Stage, commit y push de todos los archivos (`database.py`, `scraper.py`, `app.py`, `migrate_and_depurate.py` y bitácora de sesión) cerrando el track.

---

## Sesión: 17 de julio de 2026

### 1. Sincronización Remota de GitHub
* **Objetivo:** Subir los cambios de la sesión de deduplicación de base de datos (`50ec1d2..1bdc6ca`) al repositorio remoto.
* **Implementación:** Realizado `git pull --rebase` y `git push origin main` con éxito para alinear las ramas de desarrollo y remota en GitHub.

### 2. Integración de Módulo Prob_calc (Riesgo Sísmico y Régimen Tectónico)
* **Objetivo:** Integrar la infraestructura matemática y de datos de riesgo sísmico generada en diseño con Claude Fable 5.
* **Implementación:**
  * **Dependencias:** Instalación en el Python del sistema y global del entorno virtual de las librerías `numpy`, `matplotlib`, `shapely`, `netCDF4` y `scipy`.
  * **Estructura:** Creada la carpeta `Prob_calc` en la raíz e incorporados los 5 scripts del módulo (`config_grilla.py`, `descargar_datos.py`, `importar_kmz.py`, `enriquecer_celdas.py`, `test_sintetico.py`).
  * **Corrección Windows/CP1252:** Modificada la línea 150 de `test_sintetico.py` para reemplazar el caracter unicode `\u2714` (✔) por `[OK]`, solventando el error de codificación de consola `UnicodeEncodeError`.
  * **Gitignore:** Actualizado `.gitignore` para excluir la carpeta de datos temporal `Prob_calc/datos/`, los arrays binarios `Prob_calc/*.npz`, el archivo `Prob_calc/test_zonas.kmz` y las bases de datos SQLite sintéticas del track de pruebas.
* **Pruebas y Verificación:**
  * Se ejecutó `test_sintetico.py` desde el nuevo directorio del proyecto con éxito rotundo.
  * **Suite de Aserciones:** Pasaron las 8 aserciones de prueba sintéticas (`T1-T8`) de rasterización, point-in-polygon Shapely con exclusión de huecos, clases de sitio NEHRP por Vs30, y clasificador del régimen tectónico (cortical/interfaz/intraslab) contra Slab2.
* **Sincronización:** Stage, commit de todos los archivos fuente de `Prob_calc` y actualización del Conductor cerrando el track.




