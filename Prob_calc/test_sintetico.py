#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_sintetico.py — Validación end-to-end de Prob_calc SIN internet.

Genera: (1) un KMZ real (zip con doc.kml) con dos polígonos — una "zona
volcánica" a lo largo de la cadena nicaragüense y una "zona poblada" con
atributo de población alrededor de Managua, incluyendo un HUECO para probar
compound paths; (2) npz sintéticos de Slab2 (plano inclinado tipo Cocos:
20 km en la fosa, buzando ~25° hacia el NE) y Vs30 (roca en montaña,
suelo blando cerca de la costa/lagos). Luego corre el importador y el
enriquecedor, y verifica con aserciones puntos de control conocidos.

Este test valida la LÓGICA. Los datos reales llegan con descargar_datos.py.
"""
import os
import subprocess
import sys
import zipfile

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, "datos")
os.makedirs(DATOS, exist_ok=True)
sys.path.insert(0, AQUI)
import config_grilla as CG                                    # noqa: E402

KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document><name>test</name>
<Placemark><name>cadena_volcanica_ni</name>
 <Polygon><outerBoundaryIs><LinearRing><coordinates>
  -87.6,12.4,0 -86.9,11.7,0 -85.9,11.0,0 -85.6,11.6,0
  -86.6,12.4,0 -87.3,12.9,0 -87.6,12.4,0
 </coordinates></LinearRing></outerBoundaryIs></Polygon>
</Placemark>
<Placemark><name>managua_metro</name>
 <ExtendedData><Data name="poblacion"><value>1200000</value></Data></ExtendedData>
 <Polygon>
  <outerBoundaryIs><LinearRing><coordinates>
   -86.45,12.30,0 -86.05,12.30,0 -86.05,11.95,0 -86.45,11.95,0 -86.45,12.30,0
  </coordinates></LinearRing></outerBoundaryIs>
  <innerBoundaryIs><LinearRing><coordinates>
   -86.36,12.24,0 -86.18,12.24,0 -86.18,12.00,0 -86.36,12.00,0 -86.36,12.24,0
  </coordinates></LinearRing></innerBoundaryIs>
 </Polygon>
</Placemark>
</Document></kml>"""


def generar_kmz():
    ruta = os.path.join(AQUI, "test_zonas.kmz")
    with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", KML)
    return ruta


def generar_slab2_sintetico():
    """Plano inclinado: fosa mesoamericana aproximada como la recta que pasa
    por (14.0,-93.0) y (8.0,-84.0); profundidad 20 km en la fosa creciendo
    ~9 km por cada 0.1° de distancia perpendicular hacia el NE (buzamiento
    ~40 km/50 km ≈ realista para Cocos bajo Nicaragua). NaN al SO (sin slab)."""
    lat = np.arange(5.0, 18.0, 0.05)
    lon = np.arange(-95.5, -79.5, 0.05)
    LON, LAT = np.meshgrid(lon, lat)
    # distancia con signo a la fosa (positiva hacia tierra/NE)
    # recta: pasa por P1(-93,14) P2(-84,8) en (lon,lat); normal hacia NE
    dx, dy = (-84.0 - -93.0), (8.0 - 14.0)                 # dirección de la fosa
    nx, ny = -dy, dx                                        # normal (NE)
    norm = np.hypot(nx, ny); nx, ny = nx / norm, ny / norm
    d = (LON - -93.0) * nx + (LAT - 14.0) * ny              # grados con signo
    prof = 20.0 + np.clip(d, 0, None) * 90.0                # km, crece tierra adentro
    prof[d < -0.3] = np.nan                                 # mar afuera de la fosa
    np.savez_compressed(os.path.join(DATOS, "slab2_cam_dep.npz"),
                        lat=lat, lon=lon, profundidad_km=prof,
                        fuente="SINTETICO test")


def generar_vs30_sintetico():
    """Vs30: 900 m/s de base (roca), 250 m/s en una franja alrededor de la
    depresión nicaragüense (lagos/sedimentos, lat 11.5-12.5, lon -86.7,-85.5)."""
    lat = np.arange(5.0, 18.0, 0.02)
    lon = np.arange(-95.5, -79.5, 0.02)
    LON, LAT = np.meshgrid(lon, lat)
    vs30 = np.full(LAT.shape, 900.0, dtype=np.float32)
    blando = (LAT > 11.5) & (LAT < 12.5) & (LON > -86.7) & (LON < -85.5)
    vs30[blando] = 250.0
    np.savez_compressed(os.path.join(DATOS, "vs30_ca.npz"),
                        lat=lat, lon=lon, vs30_ms=vs30, fuente="SINTETICO test")


def correr(cmd):
    print(f"\n$ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=AQUI, capture_output=True, text=True)
    print(r.stdout, r.stderr or "")
    assert r.returncode == 0, f"fallo: {cmd}"
    return r.stdout


if __name__ == "__main__":
    print("=== generando insumos sintéticos ===")
    kmz = generar_kmz()
    generar_slab2_sintetico()
    generar_vs30_sintetico()

    print("\n=== importar_kmz: capa de pertenencia (zona volcánica) ===")
    correr([sys.executable, "importar_kmz.py", kmz, "--capa", "zona_volcanica"])

    print("=== importar_kmz: capa con atributo (población) ===")
    correr([sys.executable, "importar_kmz.py", kmz, "--capa",
            "zonas_pobladas", "--atributo", "poblacion"])

    print("=== enriquecer_celdas: tabla maestra ===")
    correr([sys.executable, "enriquecer_celdas.py"])

    print("=== ASERCIONES ===")
    import pandas as pd
    from enriquecer_celdas import cargar_slab2, clasificar_evento
    df = pd.read_csv(os.path.join(DATOS, "celdas_atributos.csv"))

    def celda(lat, lon):
        return df.iloc[int(CG.indice_celda(lat, lon))]

    # T1: Masaya (11.98,-86.16) dentro de la zona volcánica dibujada
    assert celda(11.98, -86.16)["capa_zona_volcanica"] == 1.0, "T1"
    # T2: Bluefields (12.01,-83.76) fuera de ella
    assert celda(12.01, -83.76)["capa_zona_volcanica"] == 0.0, "T2"
    # T3: el HUECO del polígono de Managua (centro ~12.15,-86.25) NO puntúa
    assert celda(12.10, -86.30)["capa_zonas_pobladas"] == 0.0, "T3 (hueco)"
    # T4: borde poblado de Managua (12.05,-86.40) sí recibe la población
    assert celda(12.05, -86.40)["capa_zonas_pobladas"] == 1200000.0, "T4"
    # T5: Vs30 blando en la depresión -> clase D/E y amplificación positiva
    c = celda(12.0, -86.2)
    assert c["clase_sitio"] in ("D", "E") and c["amp_factor"] > 0.3, "T5"
    # T6: roca lejos de la depresión -> amplificación ~<=0
    assert celda(14.5, -89.0)["amp_factor"] <= 0.05, "T6"
    # T7: slab más profundo tierra adentro que cerca de la fosa
    p_costa = celda(11.2, -87.2)["slab_prof_km"]
    p_tierra = celda(13.0, -85.5)["slab_prof_km"]
    assert np.isfinite(p_costa) and np.isfinite(p_tierra) and \
        p_tierra > p_costa + 30, f"T7 ({p_costa} vs {p_tierra})"
    # T8: clasificador de régimen tectónico
    interp = cargar_slab2()
    assert clasificar_evento(12.0, -86.2, 8.0, interp) == "cortical", "T8a"
    prof_slab_aqui = float(interp(np.array([[12.0, -86.2]]))[0])
    assert clasificar_evento(12.0, -86.2, prof_slab_aqui, interp) == "interfaz", "T8b"
    assert clasificar_evento(12.0, -86.2, prof_slab_aqui + 60, interp) == "intraslab", "T8c"

    print("T1-T8: TODAS LAS ASERCIONES PASAN [OK]")
    print("\nPipeline validado. Con los npz reales de descargar_datos.py, "
          "los mismos comandos producen la tabla con datos verdaderos.")
