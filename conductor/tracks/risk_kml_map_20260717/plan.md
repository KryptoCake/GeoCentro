# Plan de Implementación — Track: risk_kml_map_20260717

**Estado:** Completado
**Checkpoint pre-implementación:** `998465d`
**Checkpoint post-implementación:** `8a835cb`

---

## Fase 1: Base de Datos (`database.py`)
- [x] Crear tablas `poligonos` y `poligono_puntos` en `init_db()`.
- [x] Implementar la función de precarga de polígonos de prueba por defecto (Managua, León, Masaya).
- [x] Implementar `add_poligono()`, `get_poligonos()` y `evaluar_punto()`.
- [x] Implementar la función auxiliar `generar_kml()` para exportación.
- [x] Implementar `importar_kml_data()` utilizando un parser XML estándar (como `xml.etree.ElementTree`).

## Fase 2: Backend Flask (`app.py`)
- [x] Agregar la ruta `/risk-map` para renderizar la vista del mapa.
- [x] Agregar el endpoint GET `/api/poligonos` para retornar las geometrías en JSON/GeoJSON.
- [x] Agregar el endpoint GET `/api/poligonos/exportar-kml` para descargar el archivo KML.
- [x] Agregar el endpoint POST `/api/poligonos/importar-kml` para procesar archivos KML subidos.
- [x] Agregar el endpoint GET/POST `/api/riesgo/evaluar` para la calculadora interactiva.

## Fase 3: Frontend y Mapa (HTML/CSS/JS)
- [x] Modificar `templates/base.html` para incorporar el enlace `"Mapa de Riesgo"` en el menú.
- [x] Crear la plantilla `templates/risk_map.html` con Leaflet y la interfaz del sidebar lateral.
- [x] Crear el script `static/js/risk_map.js` que maneja el mapa, el pin interactivo, llamadas a la API y carga/descarga de KML.
- [x] Estilizar el mapa y sidebar en `static/css/style.css`.

## Fase 4: Verificación
- [x] Validar la importación/exportación de KML (probar con archivos de Google Earth).
- [x] Validar la calculadora por clic interactivo en el mapa.
- [x] Crear y ejecutar tests automatizados de point-in-polygon relacional en `test_risk_map.py`.
