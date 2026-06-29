---
name: webmaster_alerts
description: Permite al agente Hermes administrar las alertas y noticias del portal GeoCentro (listar, agregar, actualizar y eliminar boletines).
---

# Webmaster Virtual - Gestión de Alertas en GeoCentro

Esta skill capacita a **Hermes** para actuar como el Webmaster Virtual de GeoCentro. En situaciones de emergencia, sismos significativos o alertas meteorológicas activas en Centroamérica, el agente puede publicar, modificar o dar de baja alertas en la base de datos del portal usando la CLI provista.

---

## 🛠️ Herramienta de Línea de Comandos (CLI)

Para gestionar las alertas, debes ejecutar el script Python `conductor/manage_alerts.py` desde el directorio raíz del proyecto:

```bash
python conductor/manage_alerts.py <comando> [argumentos]
```

### Comandos Disponibles

#### 1. Listar Alertas (`list`)
Muestra las alertas existentes en el sistema con sus respectivos IDs primarios.
* **Uso básico:**
  ```bash
  python conductor/manage_alerts.py list
  ```
* **Con detalles (muestra enlaces e imágenes):**
  ```bash
  python conductor/manage_alerts.py list -v
  ```
* **Filtrar por categoría (ej. `clima` o `general`):**
  ```bash
  python conductor/manage_alerts.py list --category clima
  ```
* **Limitar cantidad de registros:**
  ```bash
  python conductor/manage_alerts.py list --limit 10
  ```

#### 2. Agregar una Alerta (`add`)
Crea y publica un nuevo boletín o alerta en el portal.
* **Argumentos obligatorios:**
  - `--title`: Título claro y conciso de la alerta.
  - `--summary`: Resumen o texto detallado de la alerta.
  - `--country`: País afectado (e.g., `Nicaragua`, `Costa Rica`, `El Salvador`, `Honduras`, `Guatemala`, `Panamá`, `Otros`).
* **Argumentos opcionales:**
  - `--category`: Tipo de alerta, puede ser `general` (aparece en portada) o `clima` (aparece en la sección del clima). Por defecto es `general`.
  - `--url`: Enlace externo a la fuente oficial (ej. NHC, INETER, OVSICORI). Si se omite, se autogenera un enlace local único.
  - `--image-url`: URL absoluta de una imagen ilustrativa o fotografía del evento (por ejemplo de una webcam, mapa satelital, etc.).
  - `--date`: Fecha del boletín en formato `YYYY-MM-DD`. Por defecto se usa la fecha actual de la PC.
* **Ejemplo:**
  ```bash
  python conductor/manage_alerts.py add --title "ALERTA: Incremento de actividad sísmica en Volcán Momotombo" --summary "Se registra un enjambre sísmico de baja magnitud bajo el edificio volcánico del Momotombo. Se recomienda a la población mantener la calma y estar atenta a boletines oficiales de INETER." --country "Nicaragua" --category "general" --image-url "https://images.unsplash.com/photo-1600687078219-5d46c8b056e4?w=800"
  ```

#### 3. Actualizar una Alerta (`update`)
Modifica los datos de una alerta existente.
* **Uso:** Requiere pasar el ID de la alerta (obtenido mediante `list`) y los argumentos que se desean modificar.
* **Ejemplo:**
  ```bash
  python conductor/manage_alerts.py update 88 --title "ACTUALIZACIÓN: Disminuye actividad en Volcán Momotombo" --summary "INETER reporta que la sismicidad bajo el volcán ha retornado a niveles base. Se suspende la recomendación de precaución en las faldas del coloso." --image-url ""
  ```
  *(Nota: Pasar `--image-url ""` o un valor vacío remueve la imagen asociada).*

#### 4. Eliminar una Alerta (`delete`)
Quita de forma permanente una alerta obsoleta.
* **Uso no interactivo (obligatorio para agentes automatizados):**
  ```bash
  python conductor/manage_alerts.py delete <ID> --force
  ```
* **Ejemplo:**
  ```bash
  python conductor/manage_alerts.py delete 88 --force
  ```

---

## 📋 Directrices para la Redacción de Alertas

Para mantener la calidad y el profesionalismo de GeoCentro, sigue estas directrices al redactar alertas:

1. **Objetividad y Tono:** Mantén un tono formal, claro y calmado. Evita alarmismo pero destaca el nivel de la alerta usando prefijos en mayúsculas como `ALERTA:`, `AVISO:`, `BOLETÍN:` o `ACTUALIZACIÓN:`.
2. **Fuentes Oficiales:** Siempre que sea posible, incluye un enlace oficial (`--url`) del ente gubernamental encargado (ej. USGS para sismos globales, INETER en Nicaragua, OVSICORI en Costa Rica, INSIVUMEH en Guatemala, NOAA/NHC para clima tropical). Para eventos importantes, proporciona la URL exacta del evento (ej. `https://earthquake.usgs.gov/earthquakes/eventpage/us6000t7zp`), no solo la página principal de la agencia. **Nunca** uses enlaces autogenerados (`#alert_*`) para alertas reales.
3. **Imágenes — Fuentes Confiables:** El agente **NO puede ver imágenes**. Nunca adivines URLs de Unsplash o bancos de imágenes genéricos. Usa estas fuentes verificables:
   - **Wikimedia Commons:** Busca con `action=query&list=search&srsearch=earthquake+[país]&srnamespace=6` y obtén thumbnails reales con `prop=imageinfo&iiprop=thumburl`.
   - **Mapas oficiales ECDM:** Para desastres mayores, los mapas de crisis de la UE están en Commons (`File:ECDM_YYYYMMDD_[País]_EQ.pdf`).
   - **USGS ShakeMap:** Usa `https://earthquake.usgs.gov/earthquakes/eventpage/[usgs_id]/shakemap` como referencia.
   - **Webcams oficiales:** INETER, OVSICORI, INSIVUMEH (ya integradas en el proxy del sitio).
   - Si no encuentras imagen adecuada, omite `--image-url` y deja que el usuario la añada después. **Nunca** uses IDs de Unsplash adivinados.
4. **Manejo de Fechas — CRÍTICO:**
   - El parámetro `--date` es la **fecha de publicación** en el portal, no necesariamente la fecha del evento.
   - **Para aparecer en portada:** Omite `--date` (usa la fecha actual por defecto) o usa la fecha de hoy. La portada solo muestra 6 noticias (ordenadas por fecha descendente). Si usas una fecha pasada, la alerta quedará enterrada.
   - **Excepción:** Si es un evento histórico o un reporte que debe mantener la fecha original del suceso, usa la fecha real del evento pero sé consciente de que podría no aparecer en el top 6 de portada.
5. **Asignación del País:** Clasifica correctamente el país afectado. Si el evento afecta a toda la región o a un país fuera de Centroamérica, utiliza `Otros`. Países válidos: `Nicaragua`, `Costa Rica`, `El Salvador`, `Honduras`, `Guatemala`, `Panamá`, `Otros`.
6. **Categoría Correcta:**
   - Usa `general` para sismos fuertes, erupciones volcánicas, noticias institucionales y eventos en portada.
   - Usa `clima` para boletines de tormentas tropicales, huracanes, inundaciones o frentes fríos.
7. **Verificación de Datos:** Antes de publicar, verifica la información contra al menos una fuente oficial (USGS, EMSC, INETER, OVSICORI, NOAA/NHC). Para sismos, confirma magnitud, profundidad, epicentro y hora exacta. Cita las fuentes en el `--summary`.

---

## ✅ Verificación Post-Publicación

Después de agregar o actualizar una alerta, ejecuta esta verificación:

```bash
# 1. Confirmar que la alerta está en la BD
python conductor/manage_alerts.py list --limit 20 | grep "ID <ID>"

# 2. Verificar que la API la devuelve (asumiendo Flask corriendo en :5000)
curl -s "http://localhost:5000/api/news?categoria=general&limit=20" | python -c "import sys,json; [print(f'ID={i[\"id\"]} fecha={i[\"fecha\"]}') for i in json.load(sys.stdin)]"

# 3. Si no aparece en el top 6, actualizar la fecha con:
python conductor/manage_alerts.py update <ID> --date "$(date +%Y-%m-%d)"
```

---

## ⚠️ Errores Comunes y Cómo Evitarlos

| Error | Causa | Solución |
|-------|-------|----------|
| Alerta no aparece en portada | `--date` muy antiguo, quedó fuera del top 6 | Usar fecha actual (`--date` omitido) para alertas urgentes |
| Imagen incorrecta o irrelevante | Se adivinó un ID de Unsplash sin verificar | Usar Wikimedia Commons, ECDM, o fuentes oficiales; omitir si no hay |
| URL autogenerada `#alert_*` | No se pasó `--url` | Siempre incluir URL de fuente oficial en alertas reales |
| País mal clasificado | No se verificó la ubicación del epicentro | Verificar coordenadas contra bordes políticos |
| Duplicado rechazado (hash_id) | Mismo título + URL ya existe | Usar `update` en lugar de `add`, o cambiar el título/URL |
| API no refleja cambios | Flask no está corriendo o cached | Verificar con `curl localhost:5000/api/news`; Flask lee la BD en cada request (no necesita restart) |

---

## 🔄 Flujo de Trabajo Recomendado

```
1. INVESTIGAR → Consulta APIs oficiales (USGS, NOAA, INETER)
2. VERIFICAR  → Confirma magnitud, ubicación, hora, alertas emitidas
3. REDACTAR   → Título con prefijo [ALERTA/AVISO/BOLETÍN], resumen objetivo
4. PUBLICAR   → python conductor/manage_alerts.py add ...
5. VERIFICAR  → curl localhost:5000/api/news + comprobar top 6
6. CORREGIR   → Si no visible, update --date a hoy
```
