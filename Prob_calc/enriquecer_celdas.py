#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enriquecer_celdas.py — Construye la TABLA MAESTRA de atributos por celda
combinando: Slab2 (profundidad del slab), Vs30 (clase de sitio) y todas las
capas importadas por importar_kmz.py.

Salida: datos/celdas_atributos.csv con una fila por celda:
    idx, lat, lon, slab_prof_km, vs30_ms, clase_sitio, amp_factor,
    capa_<nombre>...  (una columna por capa KMZ importada)

También expone clasificar_evento(lat, lon, prof_km) para etiquetar cada
sismo del catálogo como 'cortical' / 'interfaz' / 'intraslab' usando la
geometría real de Slab2 — la separación de poblaciones sísmicas que el
modelo de 72h necesita.

Requiere: numpy, pandas, scipy (interpolación). Los npz de datos/ deben
existir (correr antes descargar_datos.py en una máquina con internet).
"""
import glob
import os

import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator

import config_grilla as CG

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, "datos")


# ----------------------------------------------------------------------
# Interpoladores sobre las grillas nativas (Slab2 ~5 km, Vs30 ~1 km)
# ----------------------------------------------------------------------

def _interp_de_npz(ruta, campo):
    d = np.load(ruta)
    lat, lon, Z = d["lat"], d["lon"], d[campo]
    # RegularGridInterpolator exige ejes crecientes
    if lat[0] > lat[-1]:
        lat, Z = lat[::-1], Z[::-1, :]
    if lon[0] > lon[-1]:
        lon, Z = lon[::-1], Z[:, ::-1]
    return RegularGridInterpolator((lat, lon), Z, bounds_error=False,
                                   fill_value=np.nan)


def cargar_slab2():
    ruta = os.path.join(DATOS, "slab2_cam_dep.npz")
    return _interp_de_npz(ruta, "profundidad_km") if os.path.exists(ruta) else None


def cargar_vs30():
    ruta = os.path.join(DATOS, "vs30_ca.npz")
    return _interp_de_npz(ruta, "vs30_ms") if os.path.exists(ruta) else None


# ----------------------------------------------------------------------
# Clasificaciones derivadas
# ----------------------------------------------------------------------

def clase_sitio_nehrp(vs30):
    """Clase de sitio NEHRP a partir de Vs30 (m/s). Vectorizado."""
    vs30 = np.asarray(vs30, dtype=float)
    clases = np.full(vs30.shape, "?", dtype=object)
    clases[vs30 > 1500] = "A"                      # roca dura
    clases[(vs30 > 760) & (vs30 <= 1500)] = "B"    # roca
    clases[(vs30 > 360) & (vs30 <= 760)] = "C"     # suelo muy denso/roca blanda
    clases[(vs30 > 180) & (vs30 <= 360)] = "D"     # suelo rígido
    clases[(vs30 > 0) & (vs30 <= 180)] = "E"       # suelo blando (arcillas)
    return clases


def factor_amplificacion_intensidad(vs30, vs30_ref=760.0):
    """Incremento de intensidad MMI por efecto de sitio, forma logarítmica
    simple ΔI = k·log10(vs30_ref / vs30), con k≈1.3 (orden de magnitud de
    relaciones tipo Borcherdt). PLACEHOLDER honesto: calibrar con reportes
    macrosísmicos locales; el propósito es que suelo blando (Managua,
    sedimentos lacustres) amplifique ~+0.8 MMI y roca reduzca."""
    vs30 = np.asarray(vs30, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        dI = 1.3 * np.log10(vs30_ref / vs30)
    return np.clip(np.nan_to_num(dI, nan=0.0), -1.0, 1.5)


def clasificar_evento(lat, s_lon, prof_km, interp_slab,
                      tol_interfaz_km=20.0, min_cortical_km=35.0):
    """Régimen tectónico de un evento usando Slab2. Vectorizado.
    - 'cortical'  : sobre el slab (o sin slab debajo) y somero (< ~35 km)
    - 'interfaz'  : a ±tol de la superficie del slab (megathrust)
    - 'intraslab' : claramente por debajo de la superficie del slab
    - 'manto/otro': profundo sin slab debajo
    Los umbrales incluyen la incertidumbre de profundidad del catálogo y
    del propio Slab2 (~±10-15 km combinados)."""
    lat = np.atleast_1d(np.asarray(lat, dtype=float))
    lon = np.atleast_1d(np.asarray(s_lon, dtype=float))
    prof = np.atleast_1d(np.asarray(prof_km, dtype=float))
    prof_slab = interp_slab(np.column_stack([lat, lon]))
    reg = np.full(lat.shape, "cortical", dtype=object)
    con_slab = np.isfinite(prof_slab)
    delta = prof - prof_slab
    reg[con_slab & (np.abs(delta) <= tol_interfaz_km)] = "interfaz"
    reg[con_slab & (delta > tol_interfaz_km)] = "intraslab"
    reg[~con_slab & (prof >= min_cortical_km)] = "manto/otro"
    # somero sobre slab profundo sigue siendo cortical (queda por defecto)
    return reg if reg.size > 1 else reg[0]


# ----------------------------------------------------------------------
# Construcción de la tabla maestra
# ----------------------------------------------------------------------

def construir_tabla():
    lats, lons, LAT, LON, forma = CG.construir_grilla()
    puntos = np.column_stack([LAT.ravel(), LON.ravel()])
    df = pd.DataFrame({"idx": np.arange(len(puntos)),
                       "lat": puntos[:, 0], "lon": puntos[:, 1]})

    interp_slab = cargar_slab2()
    if interp_slab is not None:
        df["slab_prof_km"] = interp_slab(puntos)
        print(f"[slab2] {np.isfinite(df.slab_prof_km).sum()} celdas sobre slab")
    else:
        df["slab_prof_km"] = np.nan
        print("[slab2] datos/slab2_cam_dep.npz NO encontrado — columna NaN. "
              "Corre descargar_datos.py en una máquina con internet.")

    interp_vs30 = cargar_vs30()
    if interp_vs30 is not None:
        df["vs30_ms"] = interp_vs30(puntos)
        df["clase_sitio"] = clase_sitio_nehrp(df.vs30_ms)
        df["amp_factor"] = factor_amplificacion_intensidad(df.vs30_ms)
        print(f"[vs30] rango {np.nanmin(df.vs30_ms):.0f}-"
              f"{np.nanmax(df.vs30_ms):.0f} m/s")
    else:
        df["vs30_ms"], df["clase_sitio"], df["amp_factor"] = np.nan, "?", 0.0
        print("[vs30] datos/vs30_ca.npz NO encontrado — columnas NaN.")

    # capas KMZ importadas
    for ruta in sorted(glob.glob(os.path.join(DATOS, "capa_*.npz"))):
        nombre = os.path.basename(ruta)[5:-4]
        df[f"capa_{nombre}"] = np.load(ruta)["valores"]
        print(f"[capa] incorporada: {nombre}")

    salida = os.path.join(DATOS, "celdas_atributos.csv")
    df.to_csv(salida, index=False, float_format="%.4f")
    print(f"[tabla] {len(df)} celdas -> {salida}")
    return df


if __name__ == "__main__":
    construir_tabla()
