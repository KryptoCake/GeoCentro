# GeoCentro - Observatorio Geológico y Climático de Centroamérica

## Initial Concept
Crear un sitio web de monitoreo geológico y climático que recopile, procese y visualice información proveniente de sitios oficiales de los países centroamericanos, utilizando técnicas de web scraping, y desplegarlo en un VPS (Hostinger). El enfoque inicial será sísmico y volcánico, con futura expansión a fenómenos climáticos extremos.

## Visión del Producto
GeoCentro aspira a convertirse en la plataforma de referencia para el monitoreo de eventos sísmicos, volcánicos y climáticos en la región de Centroamérica. Al centralizar datos de múltiples agencias oficiales (comenzando con INETER en Nicaragua), el sitio ofrece visualizaciones interactivas claras y datos en tiempo real que ayudan a la población, turistas e investigadores a comprender la actividad geológica de la región de manera sencilla y accesible.

## Público Objetivo
- **Ciudadanos locales:** Para estar al tanto de los sismos recientes y alertas en su área.
- **Turistas y viajeros:** Para verificar las condiciones de seguridad cerca de zonas volcánicas activas.
- **Investigadores y educadores:** Como fuente de datos históricos consolidados sobre eventos geológicos en Centroamérica.

## Características Clave (Fase Piloto - Nicaragua)
1. **Mapa Interactivo (Leaflet.js):**
   - Visualización de sismos recientes (últimas 72 horas).
   - Ubicación de volcanes activos.
   - Enlaces a webcams en vivo (INETER) de volcanes como Masaya, San Cristóbal, Momotombo y Telica.
2. **Listado Histórico y Estadísticas:**
   - Tabla interactiva con los sismos detectados (magnitud, profundidad, ubicación, hora).
   - Filtros por fecha, magnitud y profundidad.
3. **Herramientas de visualización:**
   - Visualización en tiempo real de sismogramas de estaciones de INETER (MASN, WILN, etc.) a través de un proxy local.
4. **Scraping Automatizado:**
   - Scraping periódico de datos de sismos de INETER.
   - Almacenamiento en base de datos SQLite con fechas estandarizadas en formato `YYYY-MM-DD`.
