# Plan de Despliegue en Producción (VPS Hostinger) para el Agente Antigravity CLI

Este documento contiene el plan detallado y los comandos secuenciales que el agente Antigravity CLI ejecutará en la VPS de destino para pasar los cambios de UAT, el sistema de respaldos y la migración histórica a producción.

Dado que la aplicación base ya está en producción, este plan se enfoca en la **actualización en caliente (hot-update)** de los archivos, la inicialización de tareas cron y la migración de datos históricos sin interrumpir el servicio.

---

## 1. Pasos de Despliegue (Actualización)

El agente Antigravity CLI debe ejecutar la siguiente secuencia de comandos en el directorio del proyecto `/var/www/geocentro`.

### Paso 1.1: Obtener la última versión del repositorio
El agente debe descargar todos los cambios del repositorio, incluyendo el script de migración, el dump SQL histórico y el script de respaldos:
```bash
cd /var/www/geocentro
git fetch origin main
git reset --hard origin/main
```

### Paso 1.2: Actualizar dependencias de Python (si aplica)
Activar el entorno virtual e instalar cualquier dependencia del archivo `requirements.txt` (por si hay cambios):
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Paso 1.3: Ejecutar la migración de sismos históricos (2016-2017)
Ejecutar el script en Python para procesar el dump SQL `backups/b8_18981120_Events.sql` e importar los sismos legacy a la base de datos SQLite de producción:
```bash
python migrate_2016_backup.py
```
> [!NOTE]
> El script evitará duplicados automáticamente mediante la validación del hash único de cada sismo. Si algunos registros ya estuvieran presentes, se omitirán de manera segura.

### Paso 1.4: Configurar los Cron Jobs (Scraper y Respaldos)
Ejecutar el script de automatización cron para registrar tanto la tarea periódica del scraper (cada 30 minutos) como la tarea diaria del respaldo en caliente (2:00 AM) en el crontab del sistema:
```bash
bash setup_cron.sh
```

### Paso 1.5: Reiniciar el servicio de producción (Gunicorn)
Reiniciar el daemon de Systemd para que Gunicorn cargue el código Python actualizado:
```bash
sudo systemctl restart geocentro
```

---

## 2. Plan de Verificación

El agente debe auto-verificar el estado de la aplicación ejecutando las herramientas de diagnóstico:

### A. Ejecución del script de verificación general
Ejecutar el script de diagnóstico del sistema (el cual incluye la nueva sección 5 para validar respaldos):
```bash
bash verify_all.sh
```

**Resultados esperados en la salida:**
* **Gunicorn y Nginx:** Deben reportar estado `active (running)`.
* **Database Sismos Count:** El total de sismos locales debe superar los **3,230 registros** (reflejando la importación de los sismos de 2016-2017).
* **Backup Configuration and Status:**
  * Debe confirmar que `backup_vps.py` existe y es ejecutable.
  * Debe reportar: `Daily backup cron job: Configured`.

### B. Prueba de Ejecución Manual del Respaldo
Validar que el script de respaldo en caliente pueda ejecutarse sin errores de permisos o de SQLite:
```bash
python backup_vps.py
```
*Resultado esperado:* Debe crear un archivo `.tar.gz` en `/var/www/geocentro/backups/` y reportar éxito en la consola.

### C. Prueba de Conexión HTTP
```bash
curl -I http://127.0.0.1:8000/
```
*Resultado esperado:* Debe devolver una respuesta HTTP `200 OK`.

---

## 3. Procedimiento de Reversión (Rollback)

Si la verificación local falla o reporta errores críticos que afecten la disponibilidad del sitio:
```bash
# 1. Revertir al commit anterior estable en producción
git reset --hard HEAD@{1}

# 2. Re-aplicar la configuración cron previa (si es necesario)
crontab -r  # Limpiar crontab actual
# Restablecer el cronjob básico del scraper anterior
(echo "*/30 * * * * /var/www/geocentro/venv/bin/python /var/www/geocentro/scraper.py >> /var/www/geocentro/scraper.log 2>&1") | crontab -

# 3. Reiniciar el servicio
sudo systemctl restart geocentro
```
