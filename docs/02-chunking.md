# 02 — Chunking

## Qué es un chunk y por qué hace falta

Un embedding (fase 3) resume el significado de un texto en un solo vector. Si le pasas un capítulo completo de 20 páginas, el vector termina siendo un promedio borroso de demasiadas ideas distintas — y al buscar, recuperas el capítulo entero o nada, sin precisión. Un chunk es un fragmento lo bastante pequeño para que su embedding represente *una* idea coherente, y lo bastante grande para tener contexto suficiente como para ser útil por sí solo.

## Decisión: tamaño en tokens, no en caracteres ni palabras

El presupuesto real que importa aguas abajo (el modelo de embeddings, el LLM) se mide en tokens — piezas de sub-palabra (BPE), no caracteres ni palabras. Dos fragmentos con el mismo número de caracteres pueden tener un número de tokens muy distinto: notación química densa en símbolos tokeniza peor que prosa narrativa. Usamos `tiktoken` (encoding `cl100k_base`) solo como herramienta de conteo/partición — es liviano (sin descarga de modelo pesado) y un estándar de facto para razonar sobre tokens, aunque el LLM final (Qwen vía Ollama) tenga su propio tokenizador interno. La aproximación es suficientemente buena para decidir tamaños de chunk.

**Tamaños elegidos:** `chunk_size=600` tokens, `overlap=100` tokens. Es un punto de partida razonable (no una verdad matemática): suficientemente grande para conservar contexto alrededor de una fórmula o tabla, suficientemente chico para que el embedding no se diluya. Se ajustará con evidencia en la fase de evaluación (fase 7).

## Decisión: overlap entre chunks consecutivos

Sin overlap, un hecho importante que cae justo en la frontera de dos chunks queda partido — ninguno de los dos fragmentos lo contiene completo. Con `overlap=100`, los últimos 100 tokens de un chunk son los primeros 100 del siguiente, así que cualquier frontera queda íntegra dentro de al menos un chunk. Verificado en datos reales: comparando dos chunks consecutivos del capítulo 7 de *Coatings Materials*, comparten 418 caracteres idénticos en el punto de unión.

## Decisión: nunca cruzar la frontera de un capítulo

Cada chunk se genera **dentro de un solo capítulo** — la función `chunk_pages()` recibe solo las páginas de un capítulo a la vez, agrupadas por `itertools.groupby` sobre el orden en que `pages.jsonl` ya las escribió (fase 1 garantiza que las páginas de un mismo capítulo quedan contiguas, sin necesidad de un sort adicional). Un chunk que mezclara el final de un capítulo con el inicio del siguiente tendría una cita ambigua (¿de qué capítulo es?) y mezclaría contexto de temas no relacionados en el mismo embedding.

## Metadata que hereda cada chunk

```json
{"book": "...", "chapter": "7", "page_start": 1, "page_end": 2, "chunk_index": 1, "text": "...", "n_tokens": 600}
```

`page_start`/`page_end` se calculan rastreando, token por token, de qué página original vino cada uno — necesario porque un chunk de 600 tokens casi siempre cruza al menos una frontera de página dentro del mismo capítulo.

## Resultado en datos reales

- *Coatings Materials and Surface Coatings* (464 páginas) → 686 chunks
- *Handbook of Corrosion Engineering* (1130 páginas) → 1213 chunks
