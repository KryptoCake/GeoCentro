# Pila Tecnológica (Tech Stack) - GeoCentro

## Backend
- **Lenguaje:** Python 3.10+
- **Framework Web:** Flask (desarrollo rápido, ligero y modular)
- **Servidor WSGI (Producción):** Gunicorn (3 workers recomendados)
- **Base de Datos:** SQLite (archivo local `sismos.db`), estructurado con las siguientes tablas:
  - `sismos` (id, fecha, hora, latitud, longitud, profundidad, magnitud, localizacion, pais, enlace_detalle, creado_en)
  - `noticias` (id, titulo, enlace, fecha, fuente, creado_en)

## Scraping y Automatización
- **Scraping:** BeautifulSoup4 y Requests para la extracción de datos de sismos e información geológica de INETER.
- **Automatización:** Cron jobs locales (programados cada 30 minutos) que ejecutan `scraper.py` dentro de un entorno virtual de Python (`venv`).

## Frontend
- **Estructura y Maquetación:** HTML5 semántico.
- **Estilos:** Vanilla CSS (sin frameworks como Tailwind, priorizando control total y rendimiento).
- **Interactividad y Lógica de Cliente:** Vanilla JavaScript (ES6+).
- **Mapas:** Leaflet.js (librería de mapas de código abierto) cargando tiles de OpenStreetMap (o Mapbox/CartoDB en modo oscuro).
- **Visualización adicional:** Visualización de sismogramas dinámicos (.gif) e imágenes de webcams (.jpg) provistos por proxies en el backend de Flask para evitar problemas de CORS y HTTPS mixto.

## Servidor y Despliegue
- **Sistema Operativo:** Ubuntu/Debian (VPS Hostinger).
- **Proxy Inverso:** Nginx (manejando peticiones HTTP en puerto 80/443 y redirigiéndolas al puerto 8000 de Gunicorn).
- **Gestión de Procesos:** Systemd (servicio `/etc/systemd/system/geocentro.service`).
