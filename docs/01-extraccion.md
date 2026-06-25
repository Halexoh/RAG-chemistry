# 01 — Extracción de texto y mapeo de capítulos

## Problema

`data/raw/` puede contener libros en dos formatos distintos, y ambos llegaron en la primera carga real de datos:

- **Multi-archivo**: un PDF por capítulo (ej. *Coatings Materials and Surface Coatings*, 72 archivos `44044chN.pdf`).
- **Archivo único**: el libro completo en un solo PDF, sin dividir (ej. *Handbook of Corrosion Engineering*, 1130 páginas).

Para poder citar `[libro, capítulo, página]` en cada respuesta, necesitamos saber a qué capítulo pertenece cada página, sin importar el formato de origen.

## Decisión: detección automática por formato + TOC embebido

- **Multi-archivo** → el número de capítulo se extrae del nombre del archivo (`44044ch7.pdf` → capítulo `7`). No requiere abrir el PDF más que para extraer texto.
- **Archivo único** → se lee la tabla de contenidos embebida (`fitz.Document.get_toc()`) y se construye un mapa `página → capítulo`.

### Por qué no asumir page == toc_entry.page directamente

Muchos bookmarks de capítulo en el TOC no tienen una página de destino propia (`page == -1`); solo su primera subsección la tiene. Esto es común cuando el PDF fue generado a partir de una fuente que solo asigna destinos a los encabezados más profundos. La solución (`chapters.py::chapter_map_from_toc`) resuelve estos `-1` heredando la página del siguiente entry del TOC que sí tenga una página válida — sin importar su nivel de profundidad.

Validado contra el Handbook real: detectó correctamente 18 secciones de nivel superior (12 capítulos numerados + portada/prefacio/introducción/apéndices), con números de página coherentes con el índice impreso del libro.

## Decisión: extracción nativa con fallback a OCR, por página (no por archivo)

`page.get_text()` de PyMuPDF devuelve texto vacío o casi vacío en una página escaneada (sin capa de texto). Usamos ese umbral (`NATIVE_TEXT_MIN_CHARS`) para decidir, **página por página**, si extraer texto nativo o correr OCR (Tesseract vía `pytesseract`, idiomas `eng+spa`).

Hacerlo por página y no por archivo importa porque un mismo capítulo puede mezclar páginas nativas con páginas escaneadas (ej. una figura insertada como imagen completa). Correr OCR sobre las 75 páginas confirmadas nativas de los dos libros actuales sería ~50-100x más lento sin ninguna ganancia.

En la carga inicial (74 archivos, 1594 páginas combinadas) no se detectó ninguna página escaneada — ambos libros tienen texto nativo limpio. El camino de OCR queda construido y probado por unidad, pendiente de ejercitarse con datos reales cuando lleguen libros escaneados.

## Output

`data/processed/<book_slug>/pages.jsonl` — un registro JSON por página:

```json
{"book": "...", "chapter": "7", "page": 3, "source_file": "44044ch7.pdf", "text": "...", "extraction_method": "native"}
```

Este formato (texto a nivel de página, con metadata completa) es la entrada de la fase de chunking — cada chunk hereda `book`/`chapter`/`page` de las páginas de las que proviene.

## Pendiente para una siguiente iteración

- Extracción de tablas (`pdfplumber`) como bloques estructurados en vez de texto corrido.
- Extracción de imágenes/diagramas con referencia a página, para indexarlas o describirlas.
