# Contexto para carpeta Documentos
## Este es mi entorno de trabajo personal

- Incluye documentos .docx, .txt y .md
- También hojas de cálculo y archivos PDF
- Eres un agente de desarrollo versatil y fullstack

# Conocimiento Adquirido y Visión del Proyecto

## Sesión Actual (10 de junio de 2026)
- **Proyecto:** Monitor de eventos geológicos y climáticos para Centroamérica (GeoCentro).
- **Funcionalidad actual:** Sistema de respaldos automáticos y rotativos en caliente para la base de datos SQLite y archivos de código fuente (rutina en Python `backup_vps.py` ejecutada vía `cron` a las 2:00 AM), y migración de sismos históricos heredados (2016-2017) desde un dump SQL a la base de datos de producción.
- **Detalles técnicos:** Copia segura de base de datos con `sqlite3.Connection.backup()`, compresión en `.tar.gz` con exclusión de directorios pesados, retención de 7 días, script de verificación integrado (`verify_all.sh`), y migración de datos estructurada con parser en Python (`migrate_2016_backup.py`) que corrige coordenadas, mojibake en descripciones, separa magnitudes e infiere países, incrementando la base de datos local de 436 a 3,239 registros sin duplicaciones.

## Sesiones Anteriores
- **Sesión (8 de junio de 2026):** Integración global de sismos (USGS) con Layer Control en mapas y timeline dinámico, nueva división meteorológica con Windy embed, extremos de hoy en vivo para 6 capitales y alertas tropicales de ciclones de la NOAA/NHC. UAT: Estandarización de URLs absolutas para alertas climáticas en la BD y JS, interactividad total en badges de países redirigiendo a su historial filtrado (especialmente para "Otros" con el feed global del USGS), y aislamiento de feeds de noticias.
- **Sesión (5 de julio de 2025):** Estandarización de fechas de sismos (`YY/MM/DD` vs `YYYY-MM-DD`) entre scraping, BD y servidor, y reconstrucción de la base de datos.

## Visión Futura del Proyecto
- **Objetivo:** Evolucionar a un sitio web productivo para monitorear eventos geológicos y climáticos en Centroamérica.
- **Plataforma de Alojamiento:** Hostinger.com (dominio ya adquirido).
- **Contenido futuro:** Eventos sísmicos, eventos climáticos, noticias relevantes.
- **Funcionalidades avanzadas:** Integración de Inteligencia Artificial para actualizaciones periódicas de información interactiva.
- **Rol de Gemini CLI:** Será una parte integral del desarrollo y mantenimiento del proyecto.
