# Plan de Implementación — Track: risk_kml_map_20260717

**Estado:** En progreso
**Checkpoint pre-implementación:** `998465d`

---

## Fase 1: Base de Datos (`database.py`)
- [ ] Crear tablas `poligonos` y `poligono_puntos` en `init_db()`.
- [ ] Implementar la función de precarga de polígonos de prueba por defecto (Managua, León, Masaya).
- [ ] Implementar `add_poligono()`, `get_poligonos()` y `evaluar_punto()`.
- [ ] Implementar la función auxiliar `generar_kml()` para exportación.
- [ ] Implementar `importar_kml_data()` utilizando un parser XML estándar (como `xml.etree.ElementTree`).

## Fase 2: Backend Flask (`app.py`)
- [ ] Agregar la ruta `/risk-map` para renderizar la vista del mapa.
- [ ] Agregar el endpoint GET `/api/poligonos` para retornar las geometrías en JSON/GeoJSON.
- [ ] Agregar el endpoint GET `/api/poligonos/exportar-kml` para descargar el archivo KML.
- [ ] Agregar el endpoint POST `/api/poligonos/importar-kml` para procesar archivos KML subidos.
- [ ] Agregar el endpoint GET/POST `/api/riesgo/evaluar` para la calculadora interactiva.

## Fase 3: Frontend y Mapa (HTML/CSS/JS)
- [ ] Modificar `templates/base.html` para incorporar el enlace `"Mapa de Riesgo"` en el menú.
- [ ] Crear la plantilla `templates/risk_map.html` con Leaflet y la interfaz del sidebar lateral.
- [ ] Crear el script `static/js/risk_map.js` que maneja el mapa, el pin interactivo, llamadas a la API y carga/descarga de KML.
- [ ] Estilizar el mapa y sidebar en `static/css/style.css`.

## Fase 4: Verificación
- [ ] Validar la importación/exportación de KML (probar con archivos de Google Earth).
- [ ] Validar la calculadora por clic interactivo en el mapa.
- [ ] Crear y ejecutar tests automatizados de point-in-polygon relacional en `test_risk_map.py`.
