# Plan de Implementación: Deploy website on Hostinger VPS

Este documento detalla los pasos para realizar el despliegue del proyecto GeoCentro en el servidor de producción.

---

## Phase 1: Environment and Files Preparation [checkpoint: 211891c]
- [x] **Task: Preparar entorno de sistema y dependencias** [0c27a65]
  - [x] Instalar dependencias del sistema operativo (nginx, python3-pip, python3-venv, curl, git) si no están presentes.
  - [x] Crear el directorio `/var/www/geocentro` y asignar permisos al usuario actual (`root`).
  - [x] Copiar todos los archivos del proyecto desde el directorio de trabajo actual a `/var/www/geocentro`.
  - [x] Crear el entorno virtual de Python en `/var/www/geocentro/venv`.
  - [x] Actualizar `pip` e instalar dependencias del archivo `requirements.txt` en el entorno virtual.
  - [x] Instalar `gunicorn` en el entorno virtual.
- [x] **Task: Conductor - User Manual Verification 'Phase 1: Environment and Files Preparation' (Protocol in workflow.md)** [211891c]

## Phase 2: Configuration and Daemon Setup [checkpoint: 23d4c96]
- [x] **Task: Configurar e iniciar el servicio Gunicorn con Systemd** [b54fe58]
  - [x] Crear el archivo de servicio `/etc/systemd/system/geocentro.service` configurado para ejecutarse como el usuario adecuado y apuntar a `/var/www/geocentro`.
  - [x] Recargar el daemon de Systemd (`systemctl daemon-reload`).
  - [x] Iniciar el servicio `geocentro.service` y habilitarlo para que inicie con el sistema.
  - [x] Verificar el estado de la aplicación mediante `systemctl status geocentro`.
- [x] **Task: Configurar Nginx como Proxy Inverso** [c5b7b9c]
  - [x] Crear el archivo de configuración de Nginx `/etc/nginx/sites-available/geocentro` apuntando al puerto local 8000 y definiendo el alias para `/static/`.
  - [x] Habilitar el sitio mediante enlace simbólico a `/etc/nginx/sites-enabled/`.
  - [x] Deshabilitar el sitio predeterminado (default) de Nginx.
  - [x] Verificar la sintaxis de la configuración de Nginx (`nginx -t`).
  - [x] Reiniciar Nginx (`systemctl restart nginx`).
- [x] **Task: Conductor - User Manual Verification 'Phase 2: Configuration and Daemon Setup' (Protocol in workflow.md)** [23d4c96]

## Phase 3: Scraping Automation and Final Verification [checkpoint: 9b7f2fc]
- [x] **Task: Configurar Cron Job para automatización de Scraping**
  - [x] Crear script de automatización `setup_cron.sh` para crontab.
  - [x] Ejecutar `setup_cron.sh` para registrar el cron job en el sistema.
- [x] **Task: Pruebas de funcionamiento y verificación del sitio**
  - [x] Crear script `verify_all.sh` para comprobar servicios, logs y registros de base de datos.
  - [x] Ejecutar manualmente el scraper una vez desde el entorno virtual para verificar la conexión con INETER.
  - [x] Ejecutar `verify_all.sh` para confirmar que todo funciona correctamente.
- [x] **Task: Configurar subdominio DNS en Coolify proxy** [274938e]
  - [x] Ejecutar `configure_subdomain.sh` para registrar el subdominio `geocentro.grupopy.me`.
  - [x] Verificar la resolución DNS y la accesibilidad HTTPS a `geocentro.grupopy.me`.
- [x] **Task: Conductor - User Manual Verification 'Phase 3: Scraping Automation and Final Verification' (Protocol in workflow.md)** [9b7f2fc]

## Phase 4: Import Legacy 2016-2017 Earthquake Data [checkpoint: c1b7783]
- [x] **Task: Crear el script de migración `migrate_2016_backup.py`** [c1b7783]
  - [x] Desarrollar parser de SQL dump `b8_18981120_Events.sql` para extraer inserciones de `evento`.
  - [x] Implementar conversión de coordenadas (`11.56N` -> `11.56`, `85.58W` -> `-85.58`).
  - [x] Implementar conversión de fechas (`YY/MM/DD` -> `YYYY-MM-DD`).
  - [x] Implementar decodificación sucesiva para corregir mojibake en descripciones.
  - [x] Implementar importación segura mediante la API `save_sismo` con prevención de duplicidad por hash.
- [x] **Task: Ejecutar la migración local y verificar integridad de base de datos**
  - [x] Ejecutar `migrate_2016_backup.py`.
  - [x] Comprobar el recuento total e integridad de sismos importados.
  - [x] Confirmar que segundas pasadas no insertan registros duplicados.
- [x] **Task: Conductor - User Manual Verification 'Phase 4: Import Legacy 2016-2017 Earthquake Data' (Protocol in workflow.md)**
