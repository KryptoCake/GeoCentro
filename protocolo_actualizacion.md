# Protocolo de Actualización y Despliegue en Producción (Hostinger VPS)
## Módulo: Webmaster Virtual para Hermes (Alertas y Noticias)

Este documento es un protocolo detallado para que el agente **Antigravity CLI** que opera en el servidor VPS de Hostinger actualice la aplicación **GeoCentro** a la versión que habilita la publicación de alertas personalizadas con imágenes y enlaces por parte del agente **Hermes**.

---

## 1. Cambios y Archivos Incluidos en esta Actualización

* **[database.py](file:///var/www/geocentro/database.py)**: Migración automática para la columna `imagen_url` y funciones CRUD de gestión de noticias.
* **[static/css/style.css](file:///var/www/geocentro/static/css/style.css)**: Estilos responsivos y de escalado para las fotos de noticias.
* **[static/js/main.js](file:///var/www/geocentro/static/js/main.js)**: Carga dinámica condicional de imágenes y enlaces en la portada.
* **[static/js/clima.js](file:///var/www/geocentro/static/js/clima.js)**: Carga dinámica condicional de imágenes y enlaces en la sección del clima.
* **[conductor/manage_alerts.py](file:///var/www/geocentro/conductor/manage_alerts.py)**: Nueva CLI de control para interactuar con la base de datos de alertas.
* **[.agents/skills/webmaster_alerts/SKILL.md](file:///var/www/geocentro/.agents/skills/webmaster_alerts/SKILL.md)**: Skill de workspace para entrenar y guiar a Hermes en la publicación de noticias.

---

## 2. Instrucciones de Actualización Paso a Paso en la VPS

El agente Antigravity de la VPS debe realizar el siguiente procedimiento:

### Paso 1: Actualizar el Repositorio de Producción
Acceder al directorio del proyecto y descargar los cambios desde la rama `main` en GitHub:
```bash
cd /var/www/geocentro
git pull origin main
```

### Paso 2: Ejecutar la Migración de la Base de Datos
Para aplicar la nueva columna `imagen_url` en la base de datos de producción (`geocentro.db`) sin corromper los datos existentes, ejecutar la inicialización de la base de datos de forma manual:
```bash
/var/www/geocentro/venv/bin/python -c "import database; database.init_db(); print('Migración de BD completada con éxito')"
```
*Salida esperada:* `Migración de BD completada con éxito`

### Paso 3: Reiniciar el Servicio Web (Systemd / Gunicorn)
Reiniciar el servicio para limpiar el caché de Gunicorn y hacer que Flask cargue el nuevo código de base de datos y scripts:
```bash
sudo systemctl restart geocentro
```

### Paso 4: Dar Permisos de Ejecución al Script CLI (Opcional)
Asegurar que el script de administración de alertas sea ejecutable por los usuarios o agentes correspondientes:
```bash
chmod +x /var/www/geocentro/conductor/manage_alerts.py
```

---

## 3. Registro y Activación del Skill para el Agente Hermes en VPS

Dado que Hermes es el encargado de redactar y publicar, debemos asegurarnos de que la nueva Skill sea visible en su entorno:

1. **Ubicación del Skill**: La carpeta `.agents/skills/webmaster_alerts/` se ubica dentro del repositorio de GeoCentro.
2. **Registro Automático**: Si la instancia local de Hermes utiliza el Workspace de GeoCentro como raíz de descubrimientos de skills, detectará la carpeta `.agents/` automáticamente.
3. **Registro Manual (Si es necesario)**: Si Hermes opera de forma global o aislada en la VPS, se debe enlazar la ruta del skill en su archivo `skills.json` o copiar la carpeta:
   - Ruta origen: `/var/www/geocentro/.agents/skills/webmaster_alerts/`
   - Si se requiere copiar a las skills globales de la VPS, realizar:
     ```bash
     cp -r /var/www/geocentro/.agents/skills/webmaster_alerts ~/.gemini/config/plugins/webmaster_alerts
     ```

---

## 4. Protocolo de Verificación en Producción

### Prueba 1: Verificar que el sitio cargue correctamente
Realizar una petición HTTP local para confirmar que no hay errores 500:
```bash
curl -I http://127.0.0.1:8000/
```
*Debe retornar HTTP status 200.*

### Prueba 2: Publicación de Alerta Manual vía CLI
Ejecutar el script de alertas en la VPS para publicar una noticia simulada:
```bash
/var/www/geocentro/venv/bin/python /var/www/geocentro/conductor/manage_alerts.py add --title "PRUEBA VPS: Alerta de Webmaster" --summary "Esta es una alerta de prueba generada durante la actualización del sistema en producción." --country "Otros" --category "general" --image-url "https://picsum.photos/400/300"
```
- Entrar al sitio web de producción desde el navegador.
- Comprobar que la tarjeta de la noticia se renderice en la portada con la foto correspondiente.

### Prueba 3: Eliminación de la Alerta de Prueba
Eliminar la alerta insertada para mantener limpia la producción:
1. Buscar el ID de la alerta de prueba:
   ```bash
   /var/www/geocentro/venv/bin/python /var/www/geocentro/conductor/manage_alerts.py list
   ```
2. Borrar la alerta por su ID (ej. 91):
   ```bash
   /var/www/geocentro/venv/bin/python /var/www/geocentro/conductor/manage_alerts.py delete 91 --force
   ```

---

## 5. Plan de Rollback (En caso de fallos graves)

Si la aplicación web no arranca o la base de datos se bloquea:

1. **Revertir Código**: Revertir el repositorio de Git al commit anterior:
   ```bash
   git reset --hard HEAD@{1}
   ```
2. **Revertir Base de Datos**: Si es necesario restaurar la base de datos de producción (la migración solo añade una columna, por lo que suele ser inofensiva; no obstante, si ocurre un fallo de integridad):
   - Restaurar el último respaldo automático en caliente de la base de datos (ubicados en `/var/www/geocentro/backups/`).
3. **Reiniciar Servicio**:
   ```bash
   sudo systemctl restart geocentro
   ```
