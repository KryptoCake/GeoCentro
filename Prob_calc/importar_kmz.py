#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
importar_kmz.py — Importa polígonos (KMZ/KML de Google Earth, o GeoJSON) y
los RASTERIZA a la grilla de GEOCENTRO. El point-in-polygon se ejecuta UNA
vez aquí; las consultas posteriores son lookups O(1) por índice de celda.

Sin dependencias más allá de numpy + matplotlib (stdlib para KML/zip/json).
El test de pertenencia usa matplotlib.path.Path.contains_points (robusto,
implementación en C, maneja polígonos con huecos vía compound paths).

Uso:
  python3 importar_kmz.py zona_volcanica.kmz --capa zona_volcanica
  python3 importar_kmz.py poblacion.geojson --capa zonas_pobladas \
          --atributo poblacion
  python3 importar_kmz.py --listar

Almacena en zonas.sqlite:
  capas(nombre, tipo, n_poligonos, creado_en)
  celda_capa(capa, idx_celda, valor)   -- valor: 1.0 pertenencia, o atributo
Y espeja cada capa como npz en ./datos/capa_<nombre>.npz para consumo
directo de numpy sin tocar sqlite.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import zipfile
import xml.etree.ElementTree as ET

import numpy as np
from matplotlib.path import Path

import config_grilla as CG

AQUI = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(AQUI, "zonas.sqlite")
DATOS = os.path.join(AQUI, "datos")


# ----------------------------------------------------------------------
# Lectura de geometrías
# ----------------------------------------------------------------------

def leer_kml_poligonos(kml_bytes):
    """Extrae polígonos de un KML. Retorna lista de dicts:
    {nombre, exterior: [(lon,lat)...], huecos: [[(lon,lat)...], ...],
     atributos: {...de ExtendedData...}}
    Maneja Placemark > Polygon y MultiGeometry."""
    # KML usa namespace; lo neutralizamos para consultas simples
    texto = kml_bytes.decode("utf-8", errors="replace")
    texto = re.sub(r'\sxmlns(:\w+)?="[^"]+"', "", texto, count=10)
    root = ET.fromstring(texto)

    def coords(elem):
        """Parsea un bloque <coordinates>: 'lon,lat[,alt] lon,lat...'"""
        pts = []
        for token in elem.text.split():
            partes = token.split(",")
            if len(partes) >= 2:
                pts.append((float(partes[0]), float(partes[1])))
        return pts

    poligonos = []
    for pm in root.iter("Placemark"):
        nombre_el = pm.find("name")
        nombre = nombre_el.text.strip() if nombre_el is not None and nombre_el.text else "sin_nombre"
        atributos = {}
        for data in pm.iter("Data"):
            k = data.get("name")
            v = data.find("value")
            if k and v is not None and v.text:
                atributos[k] = v.text.strip()
        for sd in pm.iter("SimpleData"):
            if sd.get("name") and sd.text:
                atributos[sd.get("name")] = sd.text.strip()
        for pol in pm.iter("Polygon"):
            ext = pol.find(".//outerBoundaryIs//coordinates")
            if ext is None:
                continue
            huecos = [coords(h) for h in
                      pol.findall(".//innerBoundaryIs//coordinates")]
            poligonos.append(dict(nombre=nombre, exterior=coords(ext),
                                  huecos=huecos, atributos=atributos))
    return poligonos


def leer_geojson_poligonos(ruta):
    with open(ruta, encoding="utf-8") as f:
        gj = json.load(f)
    feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
    poligonos = []
    for ft in feats:
        geom = ft.get("geometry", {})
        props = ft.get("properties", {}) or {}
        nombre = str(props.get("name", props.get("nombre", "sin_nombre")))
        anillos_multi = []
        if geom.get("type") == "Polygon":
            anillos_multi = [geom["coordinates"]]
        elif geom.get("type") == "MultiPolygon":
            anillos_multi = geom["coordinates"]
        for anillos in anillos_multi:
            poligonos.append(dict(
                nombre=nombre,
                exterior=[(p[0], p[1]) for p in anillos[0]],
                huecos=[[(p[0], p[1]) for p in h] for h in anillos[1:]],
                atributos={k: str(v) for k, v in props.items()}))
    return poligonos


def leer_archivo(ruta):
    ext = os.path.splitext(ruta)[1].lower()
    if ext == ".kmz":
        with zipfile.ZipFile(ruta) as zf:
            kmls = [n for n in zf.namelist() if n.lower().endswith(".kml")]
            if not kmls:
                sys.exit("[error] KMZ sin KML interno")
            # doc.kml primero si existe (convención de Google Earth)
            kmls.sort(key=lambda n: (os.path.basename(n) != "doc.kml", n))
            return leer_kml_poligonos(zf.read(kmls[0]))
    if ext == ".kml":
        return leer_kml_poligonos(open(ruta, "rb").read())
    if in_(ext, ".geojson", ".json"):
        return leer_geojson_poligonos(ruta)
    sys.exit(f"[error] formato no soportado: {ext}")


def in_(x, *vals):
    return x in vals


# ----------------------------------------------------------------------
# Rasterización a la grilla
# ----------------------------------------------------------------------

def _cerrar(pts):
    v = np.asarray(pts, dtype=float)
    if not np.allclose(v[0], v[-1]):
        v = np.vstack([v, v[:1]])
    return v


def contiene_puntos(pol, puntos_xy):
    """Pertenencia con huecos por LÓGICA DE CONJUNTOS explícita:
    dentro(exterior) Y NO dentro(ningún hueco), con un Path por anillo.
    NOTA VERIFICADA: los compound paths de matplotlib NO restan huecos en
    contains_point (comprobado en 3.10, cualquier orientación/códigos), así
    que la resta se hace aquí manualmente — robusto entre versiones."""
    dentro = Path(_cerrar(pol["exterior"])).contains_points(puntos_xy)
    for h in pol["huecos"]:
        if len(h) >= 3:
            dentro &= ~Path(_cerrar(h)).contains_points(puntos_xy)
    return dentro


def rasterizar(poligonos, atributo=None):
    """Retorna array (n_celdas,) con el valor de capa por celda:
    - sin atributo: 1.0 si el CENTROIDE de la celda cae en algún polígono
    - con atributo: valor numérico del polígono que la contiene (si varios
      se solapan, se SUMA — correcto para población; documentado).
    """
    _, _, LAT, LON, forma = CG.construir_grilla()
    centros = np.column_stack([LON.ravel(), LAT.ravel()])   # Path usa (x,y)
    valores = np.zeros(len(centros))
    for pol in poligonos:
        if len(pol["exterior"]) < 3:
            continue
        dentro = contiene_puntos(pol, centros)
        if atributo is None:
            valores[dentro] = 1.0
        else:
            crudo = pol["atributos"].get(atributo)
            if crudo is None:
                print(f"[aviso] polígono '{pol['nombre']}' sin atributo "
                      f"'{atributo}'; se omite")
                continue
            valores[dentro] += float(str(crudo).replace(",", ""))
    return valores


# ----------------------------------------------------------------------
# Persistencia
# ----------------------------------------------------------------------

def guardar_capa(nombre, valores, tipo, n_pol):
    os.makedirs(DATOS, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS capas(
        nombre TEXT PRIMARY KEY, tipo TEXT, n_poligonos INTEGER,
        creado_en INTEGER)""")
    con.execute("""CREATE TABLE IF NOT EXISTS celda_capa(
        capa TEXT, idx_celda INTEGER, valor REAL,
        PRIMARY KEY (capa, idx_celda))""")
    con.execute("DELETE FROM celda_capa WHERE capa=?", (nombre,))
    nz = np.nonzero(valores)[0]
    con.executemany("INSERT INTO celda_capa VALUES (?,?,?)",
                    [(nombre, int(i), float(valores[i])) for i in nz])
    con.execute("INSERT OR REPLACE INTO capas VALUES (?,?,?,?)",
                (nombre, tipo, n_pol, int(time.time())))
    con.commit(); con.close()
    np.savez_compressed(os.path.join(DATOS, f"capa_{nombre}.npz"),
                        valores=valores)
    print(f"[capa] '{nombre}': {len(nz)}/{len(valores)} celdas con valor "
          f"({n_pol} polígonos) -> zonas.sqlite + capa_{nombre}.npz")


def listar():
    if not os.path.exists(DB):
        print("(sin capas aún)"); return
    con = sqlite3.connect(DB)
    for fila in con.execute("SELECT nombre,tipo,n_poligonos,creado_en FROM capas"):
        print(f"  {fila[0]:24s} {fila[1]:10s} {fila[2]:4d} polígonos  "
              f"{time.strftime('%Y-%m-%d', time.gmtime(fila[3]))}")
    con.close()


def consultar_punto(lat, lon):
    """Demo de consulta O(1): ¿en qué capas cae este punto?"""
    idx = int(CG.indice_celda(lat, lon))
    if idx < 0:
        print("punto fuera de la grilla"); return
    con = sqlite3.connect(DB)
    filas = list(con.execute(
        "SELECT capa, valor FROM celda_capa WHERE idx_celda=?", (idx,)))
    con.close()
    print(f"celda {idx} @ ({lat},{lon}):")
    for capa, valor in filas or [("(ninguna capa)", "")]:
        print(f"  {capa}: {valor}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("archivo", nargs="?", help="ruta a .kmz/.kml/.geojson")
    ap.add_argument("--capa", help="nombre de la capa destino")
    ap.add_argument("--atributo", default=None,
                    help="atributo numérico a rasterizar (ej. poblacion)")
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--punto", nargs=2, type=float, metavar=("LAT", "LON"))
    a = ap.parse_args()
    if a.listar:
        listar(); sys.exit(0)
    if a.punto:
        consultar_punto(*a.punto); sys.exit(0)
    if not a.archivo or not a.capa:
        ap.error("se requieren archivo y --capa (o --listar / --punto)")
    pols = leer_archivo(a.archivo)
    print(f"[lectura] {len(pols)} polígonos en {a.archivo}")
    vals = rasterizar(pols, atributo=a.atributo)
    guardar_capa(a.capa, vals, "atributo" if a.atributo else "pertenencia",
                 len(pols))
