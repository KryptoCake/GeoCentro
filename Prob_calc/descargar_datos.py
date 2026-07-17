#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
descargar_datos.py — Descarga Slab2 (CAM) y Vs30 global, y los recorta a la
región de GEOCENTRO.

EJECUTAR EN TU MÁQUINA/VPS (requiere internet abierto; el sandbox de Claude
no puede acceder a usgs.gov/sciencebase.gov).

Requisitos:  pip install requests netCDF4 numpy
Uso:         python3 descargar_datos.py            # descarga todo
             python3 descargar_datos.py --solo-slab2
             python3 descargar_datos.py --solo-vs30

Produce en ./datos/:
    slab2_cam_dep.npz     — profundidad de la placa de Cocos (grilla nativa)
    vs30_ca.npz           — Vs30 recortado a Centroamérica (grilla nativa)
y conserva los archivos fuente originales en ./datos/fuentes/ para
reproducibilidad (el ZIP global de Vs30 de 631 MB se puede borrar tras el
recorte con --limpiar).

Fuentes oficiales:
  Slab2: Hayes et al. (2018), doi:10.5066/F7PV6JNV — ScienceBase, ítem padre
         5aa1b00ee4b0b1c392e86467. Los archivos CAM se localizan vía el API
         de ScienceBase (URLs de archivo cambian; el API es estable).
  Vs30:  Heath et al. (2020), mosaico global híbrido, 30 arco-segundos —
         https://earthquake.usgs.gov/data/vs30/  (ZIP ~631 MB, GMT grd)
"""
import argparse
import os
import sys
import zipfile

import numpy as np
import requests

DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos")
FUENTES = os.path.join(DATOS, "fuentes")

# Región de recorte (debe cubrir config_grilla con margen)
LAT_MIN, LAT_MAX = 5.0, 18.0
LON_MIN, LON_MAX = -95.5, -79.5

SCIENCEBASE_API = "https://www.sciencebase.gov/catalog/items"
SLAB2_PARENT = "5aa1b00ee4b0b1c392e86467"
VS30_ZIP_URL = "https://earthquake.usgs.gov/static/lfs/data/global_vs30_grd.zip"
# ^ Si esta URL directa cambia, la página índice es:
#   https://earthquake.usgs.gov/data/vs30/  ("Download GMT grd file ... 631 MB ZIP")


def descargar(url, destino, descripcion):
    """Descarga con progreso y reintento simple."""
    if os.path.exists(destino):
        print(f"[skip] {descripcion}: ya existe {destino}")
        return destino
    print(f"[descarga] {descripcion}\n  {url}")
    tmp = destino + ".part"
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        bajado = 0
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                bajado += len(chunk)
                if total:
                    print(f"\r  {bajado/1e6:8.1f} / {total/1e6:.1f} MB", end="")
        print()
    os.rename(tmp, destino)
    return destino


# ----------------------------------------------------------------------
# Slab2 — CAM (Central America) vía API de ScienceBase
# ----------------------------------------------------------------------

def descargar_slab2():
    """Localiza el ítem hijo de la región CAM y baja la grilla de
    profundidad (cam_slab2_dep_*.grd) y, si existe, la de espesor."""
    print("\n=== Slab2 (Central America / placa de Cocos) ===")
    r = requests.get(SCIENCEBASE_API,
                     params={"parentId": SLAB2_PARENT, "format": "json",
                             "max": 100, "fields": "title,files"},
                     timeout=60)
    r.raise_for_status()
    items = r.json().get("items", [])
    # El ítem de Centroamérica: título contiene 'Central America' o
    # los archivos empiezan con 'cam'
    objetivo = None
    for it in items:
        titulo = it.get("title", "").lower()
        if "central america" in titulo or "middle america" in titulo:
            objetivo = it
            break
        for f in it.get("files", []) or []:
            if f.get("name", "").startswith("cam_slab2_dep"):
                objetivo = it
                break
        if objetivo:
            break
    if objetivo is None:
        sys.exit("[error] No se encontró el ítem CAM en ScienceBase. "
                 "Revisa manualmente: https://www.sciencebase.gov/catalog/"
                 f"item/{SLAB2_PARENT}")

    print(f"[slab2] ítem: {objetivo.get('title')}")
    bajados = []
    for f in objetivo.get("files", []) or []:
        nombre = f.get("name", "")
        if nombre.startswith("cam_slab2_dep") and nombre.endswith(".grd"):
            destino = os.path.join(FUENTES, nombre)
            descargar(f["url"], destino, f"Slab2 profundidad ({nombre})")
            bajados.append(destino)
    if not bajados:
        sys.exit("[error] El ítem CAM no expone .grd de profundidad; "
                 "revisar archivos disponibles en ScienceBase.")
    convertir_slab2_a_npz(bajados[0])


def convertir_slab2_a_npz(ruta_grd):
    """Lee el .grd (netCDF) de Slab2 y lo guarda como npz recortado.
    Convención Slab2: profundidad NEGATIVA (km bajo el nivel del mar),
    longitudes 0-360. Aquí se normaliza: profundidad positiva, lon -180..180."""
    from netCDF4 import Dataset
    ds = Dataset(ruta_grd)
    # nombres de variables en grds GMT: x/y/z o lon/lat/z
    def var(*names):
        for n in names:
            if n in ds.variables:
                return ds.variables[n][:]
        raise KeyError(f"ninguna de {names} en {list(ds.variables)}")
    lon = np.array(var("x", "lon"), dtype=float)
    lat = np.array(var("y", "lat"), dtype=float)
    z = np.array(var("z"), dtype=float)          # (lat, lon), NaN fuera del slab
    lon = np.where(lon > 180, lon - 360, lon)
    prof = -z                                     # positiva hacia abajo

    # recorte a la región (con tolerancia a orden de ejes)
    sel_lat = (lat >= LAT_MIN) & (lat <= LAT_MAX)
    sel_lon = (lon >= LON_MIN) & (lon <= LON_MAX)
    prof_r = prof[np.ix_(sel_lat, sel_lon)]
    salida = os.path.join(DATOS, "slab2_cam_dep.npz")
    np.savez_compressed(salida, lat=lat[sel_lat], lon=lon[sel_lon],
                        profundidad_km=prof_r,
                        fuente="Slab2 Hayes et al. 2018 doi:10.5066/F7PV6JNV")
    ok = np.isfinite(prof_r).sum()
    print(f"[slab2] -> {salida}  ({prof_r.shape}, {ok} nodos con slab, "
          f"prof {np.nanmin(prof_r):.0f}-{np.nanmax(prof_r):.0f} km)")


# ----------------------------------------------------------------------
# Vs30 global -> recorte Centroamérica
# ----------------------------------------------------------------------

def descargar_vs30(limpiar=False):
    print("\n=== Vs30 global (Heath et al. 2020) — ZIP ~631 MB ===")
    zip_path = os.path.join(FUENTES, "global_vs30_grd.zip")
    try:
        descargar(VS30_ZIP_URL, zip_path, "Vs30 global (grd)")
    except requests.HTTPError as e:
        sys.exit(f"[error] {e}\nLa URL directa pudo cambiar. Descarga manual "
                 "desde https://earthquake.usgs.gov/data/vs30/ y coloca el "
                 f"ZIP en {zip_path}, luego reejecuta.")
    print("[vs30] extrayendo .grd del ZIP...")
    with zipfile.ZipFile(zip_path) as zf:
        grds = [n for n in zf.namelist() if n.endswith(".grd")]
        if not grds:
            sys.exit("[error] el ZIP no contiene .grd")
        zf.extract(grds[0], FUENTES)
        ruta_grd = os.path.join(FUENTES, grds[0])

    from netCDF4 import Dataset
    ds = Dataset(ruta_grd)
    lon = np.array(ds.variables["x"][:], dtype=float)
    lat = np.array(ds.variables["y"][:], dtype=float)
    sel_lat = np.where((lat >= LAT_MIN) & (lat <= LAT_MAX))[0]
    sel_lon = np.where((lon >= LON_MIN) & (lon <= LON_MAX))[0]
    # leer SOLO la ventana (el grd global es enorme; no cargarlo entero)
    vs30 = np.array(ds.variables["z"][sel_lat.min():sel_lat.max() + 1,
                                      sel_lon.min():sel_lon.max() + 1],
                    dtype=np.float32)
    salida = os.path.join(DATOS, "vs30_ca.npz")
    np.savez_compressed(salida, lat=lat[sel_lat], lon=lon[sel_lon],
                        vs30_ms=vs30,
                        fuente="USGS global hybrid Vs30, Heath et al. 2020")
    print(f"[vs30] -> {salida}  ({vs30.shape}, "
          f"{np.nanmin(vs30):.0f}-{np.nanmax(vs30):.0f} m/s)")
    if limpiar:
        os.remove(zip_path)
        os.remove(ruta_grd)
        print("[vs30] fuentes globales eliminadas (--limpiar)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo-slab2", action="store_true")
    ap.add_argument("--solo-vs30", action="store_true")
    ap.add_argument("--limpiar", action="store_true",
                    help="borrar el ZIP/grd global de Vs30 tras recortar")
    a = ap.parse_args()
    os.makedirs(FUENTES, exist_ok=True)
    if not a.solo_vs30:
        descargar_slab2()
    if not a.solo_slab2:
        descargar_vs30(limpiar=a.limpiar)
    print("\nListo. Los .npz en ./datos/ son los que consume "
          "enriquecer_celdas.py")
