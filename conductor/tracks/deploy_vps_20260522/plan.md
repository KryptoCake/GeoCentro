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

## Phase 2: Configuration and Daemon Setup
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
- [ ] **Task: Conductor - User Manual Verification 'Phase 2: Configuration and Daemon Setup' (Protocol in workflow.md)**

## Phase 3: Scraping Automation and Final Verification
- [ ] **Task: Configurar Cron Job para automatización de Scraping**
  - [ ] Agregar una tarea en crontab para ejecutar `/var/www/geocentro/venv/bin/python scraper.py` cada 30 minutos, guardando logs en `/var/www/geocentro/scraper.log`.
- [ ] **Task: Pruebas de funcionamiento y verificación del sitio**
  - [ ] Realizar una petición curl local `curl http://127.0.0.1:8000` para comprobar la respuesta directa de Gunicorn.
  - [ ] Realizar una petición a la IP pública del VPS o al dominio configurado para comprobar que Nginx sirve la aplicación.
  - [ ] Ejecutar manualmente el scraper una vez desde el entorno virtual para verificar que se conecta correctamente a INETER y almacena datos en la BD de producción.
  - [ ] Validar que se crea el archivo `scraper.log` y registrar cualquier error inicial.
- [ ] **Task: Conductor - User Manual Verification 'Phase 3: Scraping Automation and Final Verification' (Protocol in workflow.md)**
