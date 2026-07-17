# Especificación: Módulo Prob_calc (Cálculo de Riesgo Sísmico)

## Objetivo
Integrar el módulo `Prob_calc` al proyecto GeoCentro para robustecer científicamente la estimación del riesgo sísmico y la caracterización tectónica de la sismicidad en Centroamérica. 

El módulo permite:
1. **Definir la grilla única:** Grilla discreta de celdas de $0.2^\circ$ (config_grilla.py).
2. **Descargar e interpolar datos globales de referencia:**
   - **Slab2 (USGS):** Interfaz 3D de subducción de la placa de Cocos bajo la placa del Caribe.
   - **Vs30 (USGS):** Velocidad de ondas sísmicas en los primeros 30 metros de suelo (proxy de amplificación local).
3. **Importar geometría local (KMZ/GeoJSON):** Rasterizar polígonos personalizados dibujados en Google Earth (zonas volcánicas, áreas de población, tipos de suelo manuales) directamente a las celdas de la grilla en preprocesamiento.
4. **Enriquecer y caracterizar celdas y eventos:**
   - Crear tabla maestra `celdas_atributos.csv` con todos los parámetros precomputados.
   - Clasificar en tiempo de ingesta el régimen tectónico de cada sismo (`cortical` si es superficial, `interfaz` si ocurre en el plano de contacto de subducción, o `intraslab` si ocurre dentro de la placa que desciende).
   - Estimar el factor de amplificación de sitio $\Delta MMI = 1.3 \cdot \log_{10}(760/Vs30)$.

## Origen de la Especificación
Diseño conceptual realizado iterativamente con Claude Fable 5 y versionado en el archivo `implementation_plans_for_agents/files.zip`.

## Archivos Integrados en `Prob_calc/`
* `config_grilla.py` — Definición geométrica de la grilla.
* `descargar_datos.py` — Descargador ScienceBase y recorte regional Vs30.
* `importar_kmz.py` — Rasterizador Shapely para polígonos KMZ/KML/GeoJSON.
* `enriquecer_celdas.py` — Tabla maestra y clasificación de régimen sísmico.
* `test_sintetico.py` — Suite de tests unitarios end-to-end.
* `README.md` — Documentación de uso.
