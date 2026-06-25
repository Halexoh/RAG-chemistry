# 05 — Retrieval: FAISS + reranking con cross-encoder

## Bi-encoder vs. cross-encoder — la distinción que justifica esta fase

El modelo de embeddings (fase 3) es un **bi-encoder**: codifica la pregunta y cada chunk *por separado*, sin que se "vean" entre sí. Eso es exactamente lo que permite precalcular el vector de cada chunk una sola vez y comparar contra miles de ellos en milisegundos con FAISS (fase 4) — pero tiene un costo: el modelo nunca razona directamente sobre la relación pregunta-chunk, solo sobre cuán parecidos son sus vectores por separado. De ahí el problema de bibliografía de las fases 3-4: una lista de referencias puede compartir vocabulario con la pregunta sin responderla.

Un **cross-encoder** procesa el par `(pregunta, chunk)` junto, en una sola pasada por el transformer, así que sí puede evaluar relevancia real. Es mucho más preciso — y mucho más caro: no se puede precalcular nada, hay que correrlo de nuevo por cada par para cada pregunta nueva. Por eso solo se aplica sobre los ~20 candidatos que ya entregó FAISS, no sobre los 1794 chunks del índice. Esta combinación (bi-encoder para recall amplio y rápido + cross-encoder para precisión final) es el patrón estándar de **retrieval en dos etapas**.

## Decisión: `BAAI/bge-reranker-base`

Igual que con los embeddings, necesitamos que el reranker entienda preguntas en español sobre pasajes en inglés — un cross-encoder monolingüe en inglés no tiene ninguna garantía de evaluar bien esa relación cross-lingual. `bge-reranker-base` es multilingüe y de tamaño moderado (~1.1 GB).

## Parámetros: `fetch_k=20`, `top_k=5`

FAISS trae 20 candidatos (recall amplio, barato) y el cross-encoder los reordena para quedarse con los 5 mejores. `fetch_k` debe ser sensiblemente mayor que `top_k` — si fueran iguales, el reranking no podría rescatar un buen chunk que el bi-encoder hubiera rankeado, por ejemplo, en la posición 15.

## Nota sobre los scores

El cross-encoder devuelve logits crudos (no probabilidades) — valores como `0.0005` no significan "0.05% de confianza", solo importa el **orden relativo** entre candidatos, no su magnitud absoluta.

## Resultado en datos reales — comparación directa

Misma query de prueba en las tres fases, mismo top-5:

| Fase | Resultado |
|---|---|
| 3 — embeddings puros (sin índice ni filtro) | 0/5 relevantes — pura bibliografía |
| 4 — FAISS + filtro heurístico de bibliografía | 2/5 relevantes |
| 5 — FAISS (top-20) + reranking con cross-encoder | ~4/5 relevantes, **0 bibliografía** en el top-5 |

El cross-encoder termina de resolver lo que el regex de la fase 4 solo atacaba parcialmente — confirma la apuesta de fase 4 de no perfeccionar el filtro heurístico y dejarle este trabajo a un componente diseñado para evaluar relevancia real.
