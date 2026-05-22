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

## Phase 3: Scraping Automation and Final Verification
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
- [ ] **Task: Conductor - User Manual Verification 'Phase 3: Scraping Automation and Final Verification' (Protocol in workflow.md)**
