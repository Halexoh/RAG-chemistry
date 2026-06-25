# 04 — Índice vectorial (FAISS) y filtro de bibliografía

## Por qué un índice y no comparar vector por vector

En la fase 3 probamos similitud calculando `todos_los_vectores @ query_vector` directamente con NumPy — funciona, pero escanea linealmente cada vector. Para 1899 chunks es instantáneo; para una biblioteca de 50-200 libros (decenas de miles de chunks) sigue siendo manejable, pero un índice estructurado (FAISS) es la pieza estándar que permite escalar sin cambiar el resto del pipeline. Usamos `IndexFlatIP`: hace exactamente la misma búsqueda exhaustiva (sin aproximación), pero optimizada en C++, y calcula directamente producto punto — que, al estar los vectores normalizados (fase 3), es igual a similitud coseno.

## Por qué un solo índice para todos los libros

Para que una pregunta pueda recuperar el mejor chunk sin importar de qué libro venga (como el ejemplo de corrosión que cruzó ambos libros en la fase 3), el índice combina los chunks de todos los libros en `data/processed/`, no uno por libro.

## Decisión: excluir bibliografía en el índice, no en los datos

La fase 3 encontró que la búsqueda semántica pura trae listas de referencias bibliográficas con score alto. La solución implementada es un filtro heurístico (`reference_filter.is_bibliography_like`) aplicado **solo al construir el índice**: `chunks.jsonl` y `embeddings.npy` quedan intactos; el filtro decide qué entra al índice de búsqueda, no qué se conserva como dato. Esto hace la decisión reversible — si el heurístico resulta mal calibrado, se reconstruye el índice sin tocar nada de las fases anteriores.

### El heurístico, y un experimento que se descartó

Señal: una lista de referencias numerada tiene tanto (a) varias líneas que empiezan con "N. " seguido de un autor en mayúscula, como (b) varios años de cita entre paréntesis, ej. "(1986)". Validado contra ejemplos reales de *Coatings Materials*: cero falsos positivos en una muestra de chunks de contenido genuino (tablas de tiempos históricos con años sueltos, listas numeradas de propiedades químicas, secciones con subíndices "16.3").

Con esta regla, el *Handbook of Corrosion Engineering* tiene un estilo bibliográfico distinto (años sin paréntesis: "1992", "1994" en vez de "(1992)"), así que parte de su bibliografía evade el filtro. Se probó relajar la regla (marcar también cuando hay ≥3 líneas numeradas, sin exigir años entre paréntesis) para capturarla — y esto introdujo **falsos positivos reales**: contenido químico genuino (ecuaciones de formación de incrustaciones, química de adhesivos de caseína, films de zinc) quedó marcado como bibliografía solo por tener 3 líneas que casualmente empezaban con un número.

**Decisión:** se descartó la regla relajada y se mantuvo la versión conservadora (`paren_years >= 2 and numbered_lines >= 2`). Perder contenido real es peor que dejar pasar algo de ruido bibliográfico — sobre todo en un RAG donde la fase de retrieval (fase 5, con reranking) es el lugar más apropiado para terminar de discriminar señal de ruido, no un regex de extracción.

## Resultado en datos reales

- 1899 chunks totales → **1794 indexados**, **105 excluidos** por el filtro (5.5%).
- La query de prueba "¿Qué es la corrosión por picadura?" mejoró de 0/5 a 2/5 resultados con contenido sustantivo real en el top-5 (antes del filtro, los 5 eran bibliografía). Sigue sin ser perfecto — exactamente el tipo de mejora incremental, no milagrosa, que se espera de un filtro heurístico simple. El resto se ataca con reranking en la fase de retrieval.

## Artefactos

- `vectorstore/index.faiss` — índice FAISS (`IndexFlatIP`, 768 dimensiones)
- `vectorstore/metadata.jsonl` — un registro por vector indexado, mismo orden que las filas del índice (correspondencia posicional, igual que `embeddings.npy` ↔ `chunks.jsonl` en la fase 3)

Ninguno de los dos se versiona en git (son derivados, regenerables con `python -m src.indexing.build_index`).
