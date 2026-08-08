# web-navigator — Skill de navegación web para Google AI Edge Gallery

Skill personalizada que le da a tus modelos locales (Gemma 4 E2B/E4B) acceso a la web en vivo, con dos acciones:

- **search** — busca en Google (vía [Serper](https://serper.dev) o [SerpAPI](https://serpapi.com)) o en la web (vía [Jina Search](https://jina.ai)) y devuelve los mejores resultados con títulos, URLs y snippets.
- **read** — lee el contenido completo de cualquier página web, convertido a markdown limpio (vía [Jina Reader](https://r.jina.ai)), ideal para el contexto limitado de modelos pequeños.

El modelo decide solo cuándo buscar y cuándo leer una página, siguiendo las instrucciones de `SKILL.md`.

## 1. Consigue una API key (solo necesitas UNA)

| Proveedor | Qué da | Gratis |
|---|---|---|
| **Serper** ([serper.dev](https://serper.dev)) | Resultados reales de Google | 2,500 búsquedas |
| **SerpAPI** ([serpapi.com](https://serpapi.com)) | Resultados reales de Google | 100 búsquedas/mes |
| **Jina** ([jina.ai](https://jina.ai)) | Búsqueda web + lector de páginas | Tokens gratis al registrarse |

La skill detecta cuál le diste automáticamente: keys `jina_...` → Jina Search; keys hexadecimales de 64 caracteres → SerpAPI; cualquier otra → Serper. Si la detección fallara, puedes forzar el proveedor con un prefijo: `serpapi:TU_KEY`, `serper:TU_KEY` o `jina:TU_KEY`. La acción **read** funciona con cualquiera de las tres (Jina Reader tiene un nivel gratuito sin key, aunque con límites de velocidad; con key de Jina el límite sube).

> **Nota:** si Serper llegara a rechazar peticiones desde el webview de la app (error de red/CORS), usa una key de Jina — su API está diseñada para funcionar desde navegadores.

## 2. Instala la skill en Edge Gallery

### Opción A — Archivo local (la más simple)

1. Copia la carpeta `web-navigator/` completa a tu teléfono (por USB, Drive, o `adb push web-navigator /sdcard/Download/`).
2. Abre **Google AI Edge Gallery → Agent Skills**.
3. Elige **importar desde archivo local** y selecciona la carpeta.
4. Cuando te pida el secret, pega tu API key.

### Opción B — Por URL (requiere hosting con MIME types correctos)

Las URLs raw de GitHub no sirven para la parte JavaScript. Hospeda la carpeta en **GitHub Pages** (agrega un archivo `.nojekyll` en la raíz) o en Cloudflare Pages, verifica que `SKILL.md` cargue en el navegador, y pega esa URL en la opción de importar por URL.

## 3. Úsala

Ejemplos de prompts que activan la skill automáticamente:

- «¿Hubo sismos hoy en Nicaragua?»
- «Busca las últimas noticias sobre el volcán Masaya»
- «Lee esta página y resúmela: https://www.ineter.gob.ni/...»

## Estructura

```
web-navigator/
├── SKILL.md            # Metadatos + instrucciones para el LLM
├── scripts/
│   └── index.html      # Lógica JS: llamadas a Serper / Jina desde el webview
└── README.md           # Este archivo (no lo usa la app)
```

## Limitaciones conocidas

- Los modelos de 2–4B a veces formatean mal la llamada a la herramienta; si falla, reformula el prompt («busca en la web: ...»).
- El contenido de páginas se trunca a ~8,000 caracteres para no desbordar el contexto del modelo.
- Sin conexión a internet la skill devuelve error (los modelos siguen funcionando offline, pero sin web).
