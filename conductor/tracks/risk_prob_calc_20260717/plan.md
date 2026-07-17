# Plan de Implementación — Track: risk_prob_calc_20260717

**Estado:** Completado
**Checkpoint pre-implementación:** `1bdc6ca`
**Checkpoint post-implementación:** `89b8fcc`

---

## Fase 1: Instalación de Dependencias
- [x] Instalar librerías geoespaciales y científicas core en el entorno virtual: `numpy`, `matplotlib`, `shapely`, `netCDF4`, `scipy`.
- [x] Instalar dependencias en el Python global del sistema para habilitar subprocesos de prueba.

## Fase 2: Integración de Código
- [x] Crear el directorio `Prob_calc` en el directorio raíz del proyecto GeoCentro.
- [x] Copiar los módulos fuente extraídos: `config_grilla.py`, `descargar_datos.py`, `importar_kmz.py`, `enriquecer_celdas.py`.
- [x] Aplicar la corrección CP1252-safe en `test_sintetico.py` (cambiar el caracter unicode de check mark ✔ por [OK] en la línea 150) para evitar fallos de codificación de consola en Windows.
- [x] Copiar `README.md` explicativo.

## Fase 3: Configuración de Git
- [x] Actualizar `.gitignore` para ignorar los archivos de datos sintéticos, base de datos Sqlite de prueba e interpolaciones locales (`.npz`, `.sqlite`, `.csv` e insumos sintéticos `test_zonas.kmz`).
- [x] Realizar `git add` de los archivos fuente y del `.gitignore`.
- [x] Crear el commit de versión final `89b8fcc`.

## Fase 4: Verificación
- [x] Ejecutar `test_sintetico.py` en la nueva ubicación y verificar que pase la suite 8/8 unitaria.
