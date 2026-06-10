# Contexto para carpeta Documentos
## Este es mi entorno de trabajo personal

- Incluye documentos .docx, .txt y .md
- También hojas de cálculo y archivos PDF
- Eres un agente de desarrollo versatil y fullstack

# Conocimiento Adquirido y Visión del Proyecto

## Sesión Actual (10 de junio de 2026)
- **Proyecto:** Monitor de eventos geológicos y climáticos para Centroamérica (GeoCentro).
- **Funcionalidad actual:** Sistema de respaldos automáticos y rotativos en caliente para la base de datos SQLite y archivos de código fuente, utilizando una rutina nativa en Python (`backup_vps.py`) ejecutada vía `cron` en la VPS a las 2:00 AM.
- **Detalles técnicos:** Copia segura usando `sqlite3.Connection.backup()`, compresión en `.tar.gz`, filtrado de exclusión de directorios pesados (`venv`, `.git`), retención de 7 días, soporte para envío a Telegram y script de verificación integrado (`verify_all.sh`).

## Sesiones Anteriores
- **Sesión (8 de junio de 2026):** Integración global de sismos (USGS) con Layer Control en mapas y timeline dinámico, nueva división meteorológica con Windy embed, extremos de hoy en vivo para 6 capitales y alertas tropicales de ciclones de la NOAA/NHC. UAT: Estandarización de URLs absolutas para alertas climáticas en la BD y JS, interactividad total en badges de países redirigiendo a su historial filtrado (especialmente para "Otros" con el feed global del USGS), y aislamiento de feeds de noticias.
- **Sesión (5 de julio de 2025):** Estandarización de fechas de sismos (`YY/MM/DD` vs `YYYY-MM-DD`) entre scraping, BD y servidor, y reconstrucción de la base de datos.

## Visión Futura del Proyecto
- **Objetivo:** Evolucionar a un sitio web productivo para monitorear eventos geológicos y climáticos en Centroamérica.
- **Plataforma de Alojamiento:** Hostinger.com (dominio ya adquirido).
- **Contenido futuro:** Eventos sísmicos, eventos climáticos, noticias relevantes.
- **Funcionalidades avanzadas:** Integración de Inteligencia Artificial para actualizaciones periódicas de información interactiva.
- **Rol de Gemini CLI:** Será una parte integral del desarrollo y mantenimiento del proyecto.
