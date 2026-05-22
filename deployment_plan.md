# Plan de Despliegue - GeoCentro en VPS (Hostinger)

Este plan de implementación está estructurado para que el CLI de Antigravity en tu VPS configure el entorno de producción, instale dependencias, configure el servicio de Flask con Gunicorn, programe el scraper en segundo plano y configure Nginx como proxy inverso.

## Requisitos Previos
- Acceso SSH al VPS con privilegios de `sudo`.
- Repositorio de GitHub público o con credenciales de acceso configuradas en el VPS (`https://github.com/KryptoCake/GeoCentro.git`).

---

## Cambios Propuestos y Tareas

### [Fase 1: Preparación del Sistema]

#### [NEW] [/etc/systemd/system/geocentro.service](file:///etc/systemd/system/geocentro.service)
Crear el servicio de Systemd para mantener activa la aplicación Flask (Gunicorn) en segundo plano.

#### [NEW] [/etc/nginx/sites-available/geocentro](file:///etc/nginx/sites-available/geocentro)
Crear el archivo de configuración para Nginx como proxy inverso hacia Gunicorn.

---

## Plan de Ejecución paso a paso para el CLI

### Paso 1: Instalar dependencias del sistema operativo
El CLI debe ejecutar comandos para actualizar los repositorios e instalar Python, pip, virtualenv, git y Nginx:
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git nginx curl
```

### Paso 2: Clonar el proyecto en el servidor
Establecer el directorio de trabajo en `/var/www/geocentro` y descargar el repositorio:
```bash
sudo mkdir -p /var/www/geocentro
sudo chown -R $USER:$USER /var/www/geocentro
git clone https://github.com/KryptoCake/GeoCentro.git /var/www/geocentro
```

### Paso 3: Configurar el entorno virtual y dependencias
Instalar las dependencias del proyecto en un entorno virtual aislado:
```bash
cd /var/www/geocentro
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### Paso 4: Crear el servicio Systemd para la App Web (Flask)
Crear el archivo `/etc/systemd/system/geocentro.service` con la siguiente configuración (reemplazando `tu_usuario` por el usuario del VPS):
```ini
[Unit]
Description=Servicio Web GeoCentro Flask con Gunicorn
After=network.target

[Service]
User=tu_usuario
WorkingDirectory=/var/www/geocentro
ExecStart=/var/www/geocentro/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### Paso 5: Configurar Nginx como Proxy Inverso
Crear el archivo `/etc/nginx/sites-available/geocentro` con la redirección al puerto local 8000:
```nginx
server {
    listen 80;
    server_name tu_dominio_o_ip;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/geocentro/static/;
    }
}
```
Habilitar el sitio y reiniciar Nginx:
```bash
sudo ln -sf /etc/nginx/sites-available/geocentro /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### Paso 6: Habilitar y arrancar el servicio de la App
```bash
sudo systemctl daemon-reload
sudo systemctl start geocentro
sudo systemctl enable geocentro
```

### Paso 7: Configurar el Scraper en segundo plano (Cron job)
Para actualizar los datos sísmicos automáticamente de manera periódica, añadir un Cron job para ejecutar el scraper cada 30 minutos:
```bash
# Editar el crontab del usuario
(crontab -l 2>/dev/null; echo "*/30 * * * * cd /var/www/geocentro && /var/www/geocentro/venv/bin/python scraper.py >> /var/www/geocentro/scraper.log 2>&1") | crontab -
```

---

## Plan de Verificación

### Pruebas Automatizadas en VPS
- Verificar estado del servicio Flask: `systemctl status geocentro`
- Verificar estado de Nginx: `systemctl status nginx`
- Realizar prueba de petición local: `curl http://127.0.0.1:8000/`

### Verificación Manual
- Acceder a `http://tu_dominio_o_ip` desde el navegador para confirmar que la portada con el mapa y la sección de herramientas funcionan correctamente.
- Validar el archivo `scraper.log` para certificar que el script se ejecuta correctamente.
