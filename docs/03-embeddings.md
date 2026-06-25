# 03 — Embeddings

## Qué es un embedding (en una frase)

Un embedding es una función que convierte texto en un vector de números reales, entrenada de forma que textos con significado parecido terminan en puntos cercanos de ese espacio vectorial. "El significado se vuelve geometría": comparar dos textos deja de ser comparar palabras y se vuelve medir una distancia (o, aquí, un producto punto) entre dos puntos.

## Decisión: modelo multilingüe (`intfloat/multilingual-e5-base`)

Los chunks están en inglés (texto fuente), pero las preguntas pueden llegar en español. Un modelo de embeddings monolingüe en inglés no garantiza que una pregunta en español caiga cerca de su respuesta en inglés en el espacio vectorial — dependería de que el modelo haya visto suficiente texto bilingüe alineado por accidente. Un modelo multilingüe está entrenado explícitamente para que el mismo concepto, en distintos idiomas, termine en la misma región del espacio.

`multilingual-e5-base` (768 dimensiones, ~1.1 GB) es un punto medio razonable entre calidad y velocidad para correr en CPU/MPS de Apple Silicon. `BAAI/bge-m3` es una alternativa de mayor calidad (y mayor costo computacional) si la evaluación de la fase 7 muestra que hace falta.

## Decisión: prefijos `query:` / `passage:` obligatorios

Los modelos de la familia E5 se entrenaron distinguiendo explícitamente "esto es algo que se busca" (`query: ...`) de "esto es algo que se indexa" (`passage: ...`). No es un detalle cosmético — omitir el prefijo degrada la calidad del embedding porque el modelo nunca vio esa entrada en ese formato durante el entrenamiento. `embedder.py` aísla esta regla en dos funciones puras (`add_passage_prefix`, `add_query_prefix`) precisamente para poder testearla sin necesidad de cargar el modelo de 1.1 GB en cada corrida de tests.

## Decisión: vectores normalizados (L2)

`normalize_embeddings=True` hace que cada vector tenga norma 1. Con vectores normalizados, similitud coseno y producto punto son la misma operación — y el producto punto es lo que un índice FAISS `IndexFlatIP` calcula de forma optimizada (fase 4). Decidir esto ahora evita tener que re-generar embeddings más adelante.

## Resultado en datos reales

| Libro | Chunks | Vectores | Tiempo |
|---|---|---|---|
| Coatings Materials and Surface Coatings | 686 | (686, 768) | ~40s |
| Handbook of Corrosion Engineering | 1213 | (1213, 768) | ~71s |

`embeddings.npy[i]` corresponde siempre a `chunks.jsonl` línea `i` (correspondencia posicional) — si se regenera `chunks.jsonl` (ej. cambiando `chunk_size`), hay que volver a correr esta fase.

## Hallazgo: la búsqueda semántica pura trae ruido de bibliografía

Probando una query real en español ("¿Qué es la corrosión por picadura?") contra los 1899 chunks combinados de ambos libros, el top-5 por similitud coseno devolvió casi puro texto de listas de referencias bibliográficas (que repiten la palabra "corrosion" muchas veces) en vez de contenido explicativo real — aunque el corpus sí contiene 138 chunks que mencionan "pitting" con contenido sustantivo (confirmado buscando el término directamente).

Esto es una limitación conocida de la búsqueda por similitud pura: un chunk de bibliografía puede tener una similitud de embedding engañosamente alta sin aportar información útil. Queda documentado como pendiente para la fase de retrieval (reranking, o filtrar/depriorizar secciones de referencias durante la extracción) en vez de parchearlo aquí — preferible resolverlo con evidencia en la fase de evaluación (fase 7) que con una corrección ad-hoc ahora.
