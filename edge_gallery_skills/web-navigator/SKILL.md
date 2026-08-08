---
name: web-navigator
description: Search the live web and read the full content of web pages. Use for current events, news, recent facts beyond training data, prices, weather, or whenever the user shares a URL they want summarized or explained.
metadata:
  homepage: https://github.com/KryptoCake/GeoCentro/tree/main/edge_gallery_skills/web-navigator
  require-secret: true
  require-secret-description: Enter a Serper API key from https://serper.dev (2,500 free Google searches) OR a Jina API key starting with "jina_" from https://jina.ai (free tokens on signup). Either one works.
---

## Overview

This skill gives you live web access with two actions:

- **search**: query a real search engine and get back the top results (titles, URLs, snippets, and a direct answer box when available).
- **read**: fetch the full content of a specific web page, converted to clean markdown.

## Implementation Requirements

You must invoke the `run_js` tool referencing `index.html`.

### Data Schema

Transmit `data` as a JSON string with these fields:

- **action**: String, mandatory. Either `"search"` or `"read"`.
- **query**: String, mandatory when action is `"search"`. The search query.
- **url**: String, mandatory when action is `"read"`. Full URL including `https://`.
- **gl**: String, optional, only for search. Two-letter country code to localize results (e.g. `"ni"` for Nicaragua, `"us"` for United States). Default `"ni"`.
- **hl**: String, optional, only for search. Two-letter language code for results (e.g. `"es"`, `"en"`). Default `"es"`.

### Examples

Search: `{"action": "search", "query": "sismos recientes en Nicaragua"}`

Read a page: `{"action": "read", "url": "https://www.ineter.gob.ni/geofisica/sis/sismolo.html"}`

## Recommended Workflow

1. When the user asks about current or factual information, call **search** first with the user's question phrased as a literal search query. Keep the user's exact intent — do not simplify "¿Hubo un sismo hoy en Managua?" into just "sismo Managua".
2. If the search snippets already answer the question, respond directly citing the source URLs.
3. If a specific result looks promising but the snippet is not enough, call **read** with that result's URL to get the full page, then answer.
4. When the user directly gives you a URL, skip search and call **read** immediately.

## Processing Results

- Answer in the user's language, concisely and factually.
- Always cite the source URLs you used.
- Page content from **read** may be truncated; if key information seems missing, say so.
- If the tool returns an error, report it clearly to the user with the suggestion included in the error message. Do not invent an answer.

**Constraint:** Use only this tool for web access; do not call alternative functions.
