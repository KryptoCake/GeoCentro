# Specification: Deploy website on Hostinger VPS

## Overview
El objetivo de este track es realizar el despliegue del sitio web de GeoCentro y su scraper automático en el VPS de Hostinger. La aplicación web Flask estará gestionada por Gunicorn en segundo plano y Nginx actuará como proxy inverso para exponerla al público. El scraper se programará como una tarea periódica de Cron.

## Requisitos Funcionales
1. **Directorio de Producción:** La aplicación debe estar desplegada en la ruta `/var/www/geocentro` con los permisos adecuados.
2. **Entorno Virtual (venv):** La aplicación debe ejecutarse aislada en un entorno virtual de Python con todas las dependencias listadas en `requirements.txt` instaladas.
3. **Servicio Gunicorn:** Gunicorn debe servir la aplicación Flask localmente en el puerto 8000, con al menos 3 workers para manejar concurrencia.
4. **Servicio de Sistema (Systemd):** Configurar y habilitar el servicio `geocentro.service` para asegurar el inicio automático y la resiliencia ante reinicios.
5. **Servidor Web Nginx:** Configurar Nginx para escuchar en el puerto 80, redirigir peticiones a Gunicorn y servir la carpeta `/static/` directamente de forma eficiente.
6. **Programación del Scraper (Cron):** Configurar una tarea programada (cron job) para ejecutar el script `scraper.py` cada 30 minutos y registrar la salida en `scraper.log`.

## Criterios de Aceptación
1. El comando `systemctl status geocentro` muestra que la aplicación está activa y ejecutándose bajo Gunicorn.
2. El comando `systemctl status nginx` muestra que Nginx está activo y sin errores de configuración.
3. Una petición HTTP a la IP pública o dominio del VPS retorna el código de estado 200 y el HTML de la portada de GeoCentro.
4. Los recursos estáticos (CSS, JS, imágenes) se cargan correctamente en el navegador sin errores 404.
5. La tarea programada de cron existe y puede ejecutar con éxito `scraper.py` (lo cual se puede verificar ejecutándolo manualmente desde el entorno virtual).
