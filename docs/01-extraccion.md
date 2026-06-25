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

En la carga inicial (74 archivos, 1594 páginas combinadas) no se detectó ninguna página escaneada — ambos libros tienen texto nativo limpio. Al ampliar el corpus a 11 libros (6491 páginas), el camino de OCR finalmente se ejercitó con datos reales: 5 páginas (0.08%) en 3 libros distintos no tenían texto nativo y se resolvieron correctamente vía Tesseract — confirmando que el fallback funciona en producción, no solo en los tests unitarios.

## Actualización: más convenciones de nombre de archivo de las anticipadas

Al cargar 9 libros adicionales (de varias editoriales/fuentes), aparecieron formatos de nombre de archivo que el `chapter_from_filename` original (un solo regex, `ch(\d+)\.pdf$`) no cubría:

| Convención | Ejemplo real | Libro |
|---|---|---|
| Número justo antes de la extensión | `44044ch7.pdf` | Coatings Materials |
| Número al inicio + descripción | `Ch5. abrasive blasting...pdf` | Corrosion Control Through Organic Coatings |
| ID numérico + guion bajo + número (± letra de sub-parte) | `90725_05a.pdf`, `13372_06.pdf` | Failure Analysis, varios Handbooks |
| "part" en vez de "ch" | `part 1 - paint composition...pdf` | Paint and Surface Coatings |
| Sin número — el archivo es un artículo con título propio | `An Aspect of Concrete Protection by Surface Coating.pdf` | Organic Coatings for Corrosion Control (volumen tipo symposium) |

`chapter_from_filename` ahora prueba varios patrones en orden (ver `chapters.py`). Para el último caso (sin número), se agregó `structural_label_from_filename` — reconoce nombres de secciones no numeradas por código corto (`_fm`, `_toc`, `_indx`, `_pref`, `_fore`, `_ref`, `_glo`, `_supp`) o por palabra completa en inglés/español (`preface`/`prefacio`, `index`/`índice`, `portada`, `copyright`...). Si ninguno de los dos reconoce el archivo, el nombre del archivo mismo se usa como capítulo — correcto para libros tipo *symposium* donde cada PDF es un artículo independiente sin numeración de capítulo.

Validado contra los nombres reales de los 11 libros antes de correr la extracción completa: el 100% de los 459 archivos multi-PDF quedó clasificado en exactamente una de las tres categorías (numérico, estructural, o título propio) — ningún archivo quedó sin resolver.

Nota deliberada: `_glo` (glosario) y `_supp` (suplemento) se mapean a etiquetas propias ("Glossary", "Supplement") en vez de a una categoría estructural genérica, porque sí pueden tener contenido técnico real (definiciones, datos suplementarios) — no se excluyen del índice en la fase 4, a diferencia de `_fm`/`_toc`/`_indx`/`_pref`/`_fore`/`_ref`.

## Output

`data/processed/<book_slug>/pages.jsonl` — un registro JSON por página:

```json
{"book": "...", "chapter": "7", "page": 3, "source_file": "44044ch7.pdf", "text": "...", "extraction_method": "native"}
```

Este formato (texto a nivel de página, con metadata completa) es la entrada de la fase de chunking — cada chunk hereda `book`/`chapter`/`page` de las páginas de las que proviene.

## Pendiente para una siguiente iteración

- Extracción de tablas (`pdfplumber`) como bloques estructurados en vez de texto corrido.
- Extracción de imágenes/diagramas con referencia a página, para indexarlas o describirlas.
