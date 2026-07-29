# Plan de Despliegue en Producción: Antigravity CLI (Hostinger VPS)

Este documento define la secuencia técnica para aplicar y desplegar las nuevas capacidades de **Riesgo Sísmico Interactivo (Prob_calc)** y **Soporte de Estándar KML** en el servidor VPS de producción de GeoCentro mediante el Antigravity CLI.

---

## Fases del Plan de Despliegue

### Fase 1: Sincronización del Repositorio
Acceder al directorio del proyecto en la VPS (`/var/www/geocentro/` o el directorio configurado para producción) y alinear la rama de producción con la de desarrollo:
```bash
git pull origin main
```

### Fase 2: Instalación de Dependencias en el Entorno Virtual
Activar el entorno virtual de producción e instalar las librerías geoespaciales y científicas:
```bash
source venv/bin/activate
pip install numpy matplotlib shapely netcdf4 scipy
```
> [!NOTE]
> En la mayoría de distribuciones modernas de Linux (como Ubuntu Server), `pip` instalará las wheels binarias precompiladas que incluyen la librería de C `GEOS` (para Shapely) y la librería `NetCDF4` integradas, eliminando la necesidad de instalarlas a nivel del sistema operativo.

### Fase 3: Descarga de Datasets Científicos
Ejecutar el script para descargar las capas de datos reales del USGS (Slab2 y grilla global de Vs30) con recorte automatizado. Este script descargará inicialmente ~700 MB de servidores federales y los compilará a arrays NumPy locales binarios de solo ~160 KB:
```bash
python Prob_calc/descargar_datos.py --limpiar
```

### Fase 4: Construcción y Enriquecimiento de la Grilla
Ejecutar el precomputador para rasterizar la grilla centroamericana de $0.2^\circ$, interpolar el Vs30 real, la profundidad del Slab2 de la placa de Cocos y las capas volcánicas del KMZ:
```bash
python Prob_calc/enriquecer_celdas.py
```
> [!TIP]
> Este script generará el archivo `Prob_calc/datos/celdas_atributos.csv`. Este CSV contiene 2,700 filas y será cargado en caché de memoria por el backend de Flask para consultas instantáneas de $O(1)$.

### Fase 5: Reinicio y Validación del Servicio de Gunicorn
Para que Flask recargue el backend (creación de tablas `poligonos`/`poligono_puntos` relacionales, carga perezosa de la grilla enriquecida y endpoints `/risk-map` y KML):
```bash
sudo systemctl restart geocentro
```

---

## Plan de Verificación en Producción

### 1. Pruebas Unitarias de Base de Datos
Correr la suite local de tests en producción para garantizar el correcto point-in-polygon y KML:
```bash
python C:\Users\PC\.gemini\antigravity\brain\4ee4696d-18d0-4e73-a769-e60cd49ade42\scratch\test_risk_map.py
```

### 2. Pruebas de Carga HTTP
Verificar el correcto renderizado y las cabeceras de KML:
```bash
curl -I http://127.0.0.1:5000/risk-map
curl -I http://127.0.0.1:5000/api/poligonos/exportar-kml
```
