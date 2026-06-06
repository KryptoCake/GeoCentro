# Protocolo de Actualización y Despliegue en Producción (Hostinger VPS)

Este documento sirve como protocolo de instrucciones detalladas para el agente Antigravity que opera en el servidor VPS de Hostinger. Su objetivo es actualizar la aplicación **GeoCentro** a la versión que incluye el monitoreo extendido para Costa Rica y Guatemala de manera segura y sin interrupción del servicio.

---

## 1. Archivos Modificados en esta Versión
- **[app.py](file:///var/www/geocentro/app.py)**: Se expandió el proxy de cámaras web (`allowed_volcanoes`) con 8 nuevas URLs de flujos en vivo.
- **[scraper.py](file:///var/www/geocentro/scraper.py)**: Se incorporaron las funciones de scraping para OVSICORI (recientes y sentidos) y se integraron en la rutina principal.
- **[static/js/map.js](file:///var/www/geocentro/static/js/map.js)**: Se modificó el centro predeterminado del mapa a `[12.5, -87.5]` (zoom `6`) y se agregaron los nuevos volcanes (Turrialba, Fuego, Santiaguito) con soporte para múltiples cámaras web.
- **[templates/index.html](file:///var/www/geocentro/templates/index.html)**: Se unificó el aviso de copyright del modal de cámaras (INETER / OVSICORI / INSIVUMEH).
- **[templates/tools.html](file:///var/www/geocentro/templates/tools.html)**: Se expandió la grilla de cámaras web para soportar las 17 cámaras en total.

---

## 2. Instrucciones Paso a Paso para la Actualización

El agente Antigravity en la VPS debe seguir los siguientes pasos:

### Paso 1: Actualizar el Repositorio Local
Acceder al directorio del proyecto y descargar los últimos cambios de la rama `main`:
```bash
cd /var/www/geocentro
git pull origin main
```

### Paso 2: Validar e Instalar Dependencias (Opcional)
Asegurar que todas las librerías necesarias están instaladas en el entorno virtual (principalmente `beautifulsoup4` y `requests`):
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Paso 3: Reiniciar el Servicio Web (Systemd)
Dado que los archivos de Flask están en caché por Gunicorn, se debe reiniciar el servicio de Systemd configurado para la app web:
```bash
sudo systemctl restart geocentro
```

### Paso 4: Validar el Scraper Manualmente
Para corroborar que el scraper de Costa Rica conecta correctamente y no genera conflictos de red en el entorno del VPS, ejecutar el script manualmente una vez:
```bash
venv/bin/python scraper.py
```
*Comportamiento esperado en la primera corrida en VPS: Debería descargar e insertar en la base de datos `geocentro.db` los nuevos sismos de OVSICORI y reportar "Scraping total finalizado".*

---

## 3. Protocolo de Verificación y Rollback

### Verificaciones Post-Despliegue:
1. **Verificar Estado de Systemd**:
   ```bash
   sudo systemctl status geocentro
   ```
2. **Verificar Registros de Nginx**:
   Comprobar que no haya errores de redirección:
   ```bash
   sudo tail -n 20 /var/log/nginx/error.log
   ```
3. **Verificar Logs del Scraper**:
   Asegurar que el cronjob sigue funcionando correctamente tras las actualizaciones:
   ```bash
   tail -n 50 scraper.log
   ```

### Plan de Rollback (En caso de fallos graves):
Si la aplicación falla o no levanta tras el despliegue, revertir al commit anterior en producción ejecutando:
```bash
git reset --hard HEAD@{1}
sudo systemctl restart geocentro
```
