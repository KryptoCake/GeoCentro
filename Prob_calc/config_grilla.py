#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config_grilla.py — Definición ÚNICA de la grilla de GEOCENTRO.

Todos los componentes (pronóstico 72h, importador KMZ, enriquecedor de
celdas) deben importar la grilla de aquí. Si la grilla se define dos
veces, tarde o temprano se desalinea — este módulo es la fuente de verdad.
"""
import numpy as np

# Región de análisis: Centroamérica completa (fuentes sísmicas relevantes
# para Nicaragua incluyen Costa Rica, El Salvador, Honduras, Guatemala).
LAT_MIN, LAT_MAX = 7.0, 16.0
LON_MIN, LON_MAX = -93.5, -81.5
TAMANO_CELDA = 0.2          # grados (~22 km)


def construir_grilla():
    """Retorna (lats_1d, lons_1d, LAT_2d, LON_2d, forma).
    Centroides de celda; forma = (n_lat, n_lon)."""
    lats = np.arange(LAT_MIN + TAMANO_CELDA / 2, LAT_MAX, TAMANO_CELDA)
    lons = np.arange(LON_MIN + TAMANO_CELDA / 2, LON_MAX, TAMANO_CELDA)
    LAT, LON = np.meshgrid(lats, lons, indexing="ij")
    return lats, lons, LAT, LON, (len(lats), len(lons))


def indice_celda(lat, lon):
    """(lat, lon) -> índice plano de celda, o -1 si cae fuera de la grilla.
    Vectorizado: acepta escalares o arrays."""
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    i = np.floor((lat - LAT_MIN) / TAMANO_CELDA).astype(int)
    j = np.floor((lon - LON_MIN) / TAMANO_CELDA).astype(int)
    _, _, _, _, (nlat, nlon) = construir_grilla()
    fuera = (i < 0) | (i >= nlat) | (j < 0) | (j >= nlon)
    idx = i * nlon + j
    return np.where(fuera, -1, idx)
