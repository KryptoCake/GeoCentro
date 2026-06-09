# Bitácora de Sesiones de Desarrollo (Conductor)

Este archivo registra el historial de sesiones de desarrollo y los hitos alcanzados por el agente Antigravity en el proyecto GeoCentro.

---

## Sesión: 8 de junio de 2026

### 1. Correcciones de Control de Calidad (UAT)
* **Enlaces de "Ver Fuente" (NHC):**
  * **Causa:** Las alertas guardadas previamente contenían URLs relativas que se resolvían localmente en el servidor, provocando recargas o errores 404 locales.
  * **Solución:**
    * Agregamos normalización de URLs en **[scraper.py](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/scraper.py)** para garantizar rutas absolutas antes del guardado.
    * Implementamos una limpieza automática de alertas con enlaces corruptos en **[database.py](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/database.py)** (`init_db`).
    * Añadimos un fallback redundante en **[clima.js](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/static/js/clima.js)** para asegurar que los enlaces siempre apunten a dominios válidos con `target="_blank"`.
* **Interactividad de la Etiqueta "Otros":**
  * **Causa:** La etiqueta de país "Otros" (y las demás etiquetas) eran texto plano estático.
  * **Solución:**
    * Convertimos los badges de país en enlaces interactivos a `/historical?pais=NombreDelPais`.
    * Añadimos soporte en **[historical.js](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/static/js/historical.js)** para capturar parámetros de consulta. Al recibir `?pais=Otros`, cambia automáticamente la visualización al feed global **USGS (Global)** y filtra la tabla e histogramas al instante.
    * Enriquecimos los estilos de hover y cursor pointer de las insignias en **[style.css](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/static/css/style.css)**.

### 2. Corrección del Feed de Noticias en Portada
* **Problema:** El feed de noticias de la Portada mostraba únicamente alertas climáticas recientes, ocultando por completo las alertas de sismos.
* **Causa:** La consulta a la API de noticias `/api/news?limit=6` sin categoría retornaba los boletines climáticos más recientes de la NOAA (los cuales son muy frecuentes), desplazando los sismos geológicos anteriores.
* **Solución:** Modificamos **[main.js](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/static/js/main.js)** para consultar `/api/news?categoria=general&limit=6`, aislando las noticias geológicas y sísmicas en la Portada, y dejando el monitoreo meteorológico de forma exclusiva en la sección **Clima** (`/clima`).

### 3. Checkpoint de Conductor y Subida a GitHub
* **Cierre de Track:** Marcamos como completados todos los ítems de la Fase 3 del despliegue en VPS y cerramos la pista de despliegue en **[tracks.md](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/conductor/tracks.md)** y **[plan.md](file:///c:/Users/PC/Documents/Proyectos_nuevos/GeoCentro/conductor/tracks/deploy_vps_20260522/plan.md)** bajo el checkpoint de versión `9b7f2fc` y `fc36c03`.
* **Sincronización:** Integramos los cambios con la rama remota de GitHub (`origin/main`) mediante pull rebase y resolvimos los conflictos de planificación de forma exitosa. Subimos los commits definitivos (incluyendo la corrección del feed de la portada con SHA: `e86afa5`).

### 4. Plan de Despliegue VPS
* Diseñamos un plan de despliegue y actualización continua en el archivo **[vps_agent_deployment_plan.md](file:///C:/Users/PC/.gemini/antigravity/brain/98522864-9897-4022-8619-0c0dd78548c7/vps_agent_deployment_plan.md)** para que el agente que opera en la VPS de Hostinger aplique la actualización en producción sin caídas del servicio.
