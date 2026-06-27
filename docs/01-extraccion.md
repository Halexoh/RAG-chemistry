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

## Integración del archivo personal "Prolac" (685 PDFs, 12 categorías temáticas)

Hasta este punto, cada carpeta en `data/raw/` era un libro completo. La siguiente carga fue distinta: un archivo personal acumulado durante años de experiencia profesional en recubrimientos, organizado en 12 carpetas temáticas (`01_Corrosion_y_Proteccion`, `03_Materias_Primas`, etc.), cada una con una mezcla de libros completos, fichas técnicas de proveedores, papers, tesis y normas — algunas carpetas anidadas varios niveles.

### Por qué no se puede distinguir "libro" de "carpeta de documentos sueltos" por la forma del contenido

El primer intento fue un heurístico de forma: "una carpeta plana con muchos PDFs sueltos, sin subcarpetas, es un libro multi-archivo (como en la fase original)". Esto falla con datos reales: varias carpetas temáticas del archivo (ej. `07_Tecnologias_de_Resinas/Alquidicas`) son *exactamente* igual de planas — muchos PDFs sueltos, sin subcarpetas — pero son documentos independientes (fichas técnicas, papers), no capítulos de un mismo libro. Aplicar el heurístico de forma las habría fusionado en un único "libro" falso, citando una ficha técnica de poliuretano como si fuera el "capítulo 14" de un libro inexistente.

**Decisión:** la distinción se hace por **convención de nombre de carpeta**, no por forma de contenido — ver `extraction/run.py::discover_sources`. Una carpeta `[Autor_Año]_Titulo` (corchetes) es un libro real; cualquier otra cosa es una categoría, donde cada PDF suelto se convierte en su propio documento independiente (citado por su propio título, no como "capítulo N de la categoría"), y cada subcarpeta se recorre recursivamente igual. Validado contra las 8 carpetas-libro reales y las decenas de carpetas-categoría reales del archivo: ninguna categoría plana terminó fusionada por error.

### Nuevas convenciones de nombre de archivo: `Cap_NN_`/`Sec_NN_` (español)

El propio archivo personal usa su propia convención, ninguna de las anteriores: `Cap_01_Introduccion.pdf`, `Sec_10_Sistemas_de_Recubrimiento.pdf`, con sub-partes (`Cap_05a_..._Parte1.pdf`/`Cap_05b_..._Parte2.pdf`) igual que los libros anteriores. Se agregaron dos patrones nuevos a `NUMERIC_CHAPTER_PATTERNS`, con guardas explícitas contra falsos positivos (`Capacitor`, `Security` empiezan con "cap"/"sec" pero no son capítulos). También aparecieron secciones estructurales nuevas en español completo (`Contenido`, `Tabla_de_Contenido`, `Referencias`, `Glosario`, `Directorio`) y un prefijo centinela `ZZ_` para secciones que van al final del libro (`ZZ_Indice.pdf`) — `structural_label_from_filename` se generalizó para normalizar guiones bajos a espacios antes de buscar coincidencias, en vez de depender de un único estilo de separador.

### Dos mecanismos de deduplicación distintos, porque los duplicados reales no siguen una sola señal

Construir y validar contra el archivo completo expuso duplicados reales de dos tipos distintos:

1. **Marcador de versión explícito** (`_v2`, `_v3`...): un archivo re-exportado o re-escaneado más tarde, con el original dejado por error en la carpeta. `dedupe_versioned_chapters` conserva solo la versión más alta *cuando al menos un archivo del grupo tiene el marcador* — sin él, dos archivos con el mismo número de capítulo (`05a`/`05b`) son sub-partes genuinas, ambas se conservan.
2. **Contenido idéntico sin ningún marcador en el nombre**: encontrado por hash MD5 sobre el archivo completo (`drop_exact_duplicate_files`), no por convención de nombre — el caso real que lo motivó fue `Sec_11_Miscelaneos.pdf` y `Sec_11b_Miscelaneos_cont.pdf`, donde el nombre sugiere contenido distinto ("_cont" = continuación) pero el contenido es un copy-paste accidental idéntico.

Ningún mecanismo por sí solo cubre ambos casos: el de versión no detectaría el caso 2 (no hay `_vN`), y aplicar hash-dedup ciego sin la guarda de versión explícita arriesgaría borrar sub-partes genuinas que casualmente compartan contenido inicial. Se mantienen como dos pasos independientes en `extraction/chapters.py`.

### Bug real encontrado: TOC con solo enlaces de navegación

Validando contra los 685 PDFs reales, 5 artículos cortos de NACE (formato "artículo independiente", sin convención de capítulo) crasheaban con `IndexError: list index out of range` en `chapter_map_from_toc`. Causa: su TOC embebido no son capítulos, son enlaces de navegación de una página web exportada a PDF (`"NACE Home Page"`, `"Search Site"`) — *todas* las entradas tienen `page == -1` y no hay ningún hermano en el TOC con página real de la cual heredar. El código asumía que si `get_toc()` no está vacío, hay al menos un nivel con páginas resolubles. Corregido devolviendo `{}` (sin mapa de capítulos, igual que un PDF sin TOC) cuando ningún nivel tiene páginas resolubles — con test de regresión.

### Limpieza de "restos de reorganización" encontrados por validación, no por suposición

Tres casos reales de archivos sueltos que resultaron ser restos de una reorganización anterior del propio archivo personal (un libro re-consolidado en una nueva estructura, con los archivos viejos por capítulo dejados atrás sin borrar) — detectados comparando contenido (no solo nombre) contra el libro consolidado, y eliminados tras confirmación explícita: 4 archivos `ch1-4...pdf` (Forsgren), 23 archivos `part N.pdf`/`contents.pdf`/`index.pdf` (Paint and Surface Coatings), y 2 pares de duplicados exactos cruzando categorías distintas. Ver `git log` para el detalle exacto de qué se eliminó y por qué.

### Resultado final tras la integración completa

685 PDFs de entrada → **436 fuentes** en `data/processed/` (8 libros con convención de corchetes + 428 documentos independientes) = exactamente `8 + (457 documentos independientes originales − 29 eliminados por duplicado)`, confirmando que ninguna fuente se perdió ni se sobrescribió por colisión de slug. **20997 páginas** extraídas en total, sin ninguna excepción no recuperable.

## Pendiente para una siguiente iteración

- Extracción de tablas (`pdfplumber`) como bloques estructurados en vez de texto corrido.
- Extracción de imágenes/diagramas con referencia a página, para indexarlas o describirlas.
