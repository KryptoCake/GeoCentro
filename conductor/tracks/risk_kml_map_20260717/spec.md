# Especificación: Mapa Interactivo de Riesgo Sísmico con Estándar KML

## Requerimientos
1. **Base de Datos Relacional:**
   - Tabla `poligonos`: `id`, `nombre`, `descripcion`, `peso`, `unidad`, `color`.
   - Tabla `poligono_puntos` (vértices): `id`, `poligono_id`, `latitud`, `longitud`, `orden`.
2. **Algoritmo de Intersección (Backend):**
   - Point-in-polygon robusto en Python utilizando `Shapely`.
   - Búsqueda en $O(1)$ de datos geofísicos Vs30 y Slab2 (grilla de `Prob_calc`).
   - Retorno de un diagnóstico unificado (atenuación, amplificación de sitio, pertenencia a polígonos, sismicidad histórica) con un score de riesgo del 0 al 100%.
3. **Estándar KML (Interoperabilidad):**
   - **Exportación KML:** Generar archivos `.kml` con la estructura oficial (etiquetas `<Polygon>`, `<outerBoundaryIs>`, `<coordinates>` y `<ExtendedData>` para los metadatos cuantitativos y cualitativos).
   - **Importación KML:** Parsea archivos KML en el backend, extrae polígonos y vértices, y los inserta en las tablas correspondientes de forma transaccional.
4. **Visualización Interactiva (Frontend):**
   - Página `/risk-map` con mapa Leaflet a pantalla completa.
   - Clic interactivo en el mapa para colocar un marcador y evaluar el riesgo de ese punto a través del API backend `/api/riesgo/evaluar`.
   - Sidebar premium lateral con gauge dinámico y detalles del diagnóstico.
   - Controles para descargar la base de datos de polígonos como KML y subir nuevos KML en caliente.
