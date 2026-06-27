# 07 — Evaluación

## Por qué no hay un "gold dataset" tradicional

Evaluar un RAG correctamente requeriría un conjunto de preguntas con respuestas y fuentes correctas etiquetadas a mano por un experto — construir eso a este punto del proyecto significaría leer cientos de chunks manualmente. En su lugar, esta fase usa un atajo honesto: 15 preguntas reales, cada una verificada contra el corpus (no inventada) — para las preguntas dentro de dominio, se confirmó primero con `grep` que la palabra clave esperada realmente aparece en el libro esperado (ver fase de construcción del test set) antes de escribir el caso de prueba. No es un gold dataset, pero tampoco son afirmaciones sin verificar.

Métricas usadas, todas deterministas y sin LLM-as-judge (evitar depender de la corrección de *otro* modelo para evaluar este):

- **keyword_hit**: ¿algún chunk recuperado contiene la palabra clave esperada?
- **book_hit**: ¿algún chunk recuperado viene del libro esperado? (cuando aplica — ver hallazgo abajo)
- **citation_validity**: ¿cada cita en la respuesta generada corresponde a una fuente realmente recuperada (libro + rango de página que se superpone), o el modelo inventó una?
- **refusal** (preguntas fuera de dominio): ¿la respuesta admite explícitamente que no tiene la información?
- **fabricated_citation** (preguntas fuera de dominio): ¿la respuesta incluyó una cita pese a no responder realmente?

## Iteración 1 — primera corrida (solo filtro de bibliografía, fase 4)

| Métrica | Valor |
|---|---|
| keyword_hit_rate | 1.00 |
| book_hit_rate | 0.90 |
| citation_validity_rate | 0.80 |
| out_of_domain_refusal_rate | 1.00 |
| out_of_domain_fabricated_citation_rate | 0.60 |

`out_of_domain_refusal_rate = 1.00` confirma lo más importante: el modelo **nunca alucinó una respuesta** a una pregunta fuera de dominio. Pero `fabricated_citation_rate = 0.60` mostró un problema nuevo: en 3 de 5 preguntas fuera de dominio, el modelo se negó a responder correctamente *pero igual citó una fuente* — por ejemplo, citando páginas del **índice alfabético** del Handbook (`[Handbook of Corrosion Engineering, Index, p. 1066-1067]`).

## Hallazgo: las páginas de índice son ruido, igual que la bibliografía

Inspeccionando esos casos: FAISS siempre devuelve sus top-k candidatos, sin importar si alguno es realmente relevante. Una página de índice alfabético (lista densa de "término, número de página") comparte suficiente vocabulario genérico con casi cualquier pregunta como para rankear alto por embedding — el mismo problema de la fase 4, pero con un tipo de sección distinto (`Table of Contents`, `Index`, `Front Matter`, `Acknowledgments`, `Preface`).

**Corrección:** [`src/indexing/structural_filter.py`](../src/indexing/structural_filter.py) excluye estas secciones del índice por nombre exacto de capítulo — sin regex, sin riesgo de falso positivo, porque cada chunk ya trae su capítulo desde la fase 1. Tras reconstruir el índice (1546 chunks indexados, 353 excluidos entre bibliografía y secciones estructurales):

| Métrica | Antes | Después del filtro estructural |
|---|---|---|
| out_of_domain_fabricated_citation_rate | 0.60 | 0.40 |

Mejora real, no perfecta — el resto resultó ser un problema distinto.

## Hallazgo: el modelo no sigue la instrucción de "no citar al rechazar" el 100% de las veces

En los casos restantes, el modelo seguía citando una fuente real (ya no del índice, sino de un capítulo legítimo) solo para "justificar" por qué no podía responder — no es alucinación de contenido, es una cita innecesaria adjunta a un rechazo correcto. Se ajustó el `SYSTEM_PROMPT` ([`src/generation/prompt.py`](../src/generation/prompt.py)) añadiendo una instrucción explícita: *si rechazas responder, no incluyas ninguna cita*.

Tras el ajuste, `citation_validity_rate` subió de 0.80 a 0.90, pero `fabricated_citation_rate` en preguntas fuera de dominio no bajó de 0.40 en la corrida siguiente. Conclusión honesta: un modelo de 7B parámetros sin fine-tuning específico no sigue una instrucción de prompt el 100% de las veces, incluso siendo explícita. Esto es una limitación real del modelo local elegido, no un bug del pipeline — quedaría para una iteración futura (few-shot examples en el prompt, o un modelo más grande) si se necesitara cerrar esa brecha por completo.

## Hallazgo: un fallo de "book_hit" que resultó ser un defecto del test, no del sistema

La pregunta "¿qué función cumple un primer en un sistema de recubrimiento?" fallaba consistentemente `book_hit` (se esperaba *Coatings Materials and Surface Coatings*). Inspeccionando la respuesta real, el sistema citaba correctamente `[Handbook of Corrosion Engineering, 9. Protective Coatings, p. 830-831]` — una fuente perfectamente válida, porque **"primer" se menciona en ambos libros** (66 veces en uno, 52 en el capítulo "Protective Coatings" del otro). El test asumía una sola fuente "correcta" para un tema que el corpus cubre legítimamente en dos lugares.

**Corrección:** se quitó la restricción `expected_book` de ese caso de prueba (ver [`src/evaluation/testset.py`](../src/evaluation/testset.py)) en vez de forzar el sistema a comportarse distinto — el sistema tenía razón, el test estaba mal planteado.

## Resultado final (tras corregir el test set, `eval/results/20260625_101610.json`)

| Métrica | Valor |
|---|---|
| keyword_hit_rate | 1.00 |
| book_hit_rate | 1.00 (sobre 9 casos con libro esperado bien definido) |
| citation_validity_rate | 0.80 |
| out_of_domain_refusal_rate | 1.00 |
| out_of_domain_fabricated_citation_rate | 0.20 |
| latencia promedio | 12.4s por pregunta |

`fabricated_citation_rate` terminó incluso mejor de lo esperado (0.20, 1 de 5) tras el filtro estructural y el ajuste de prompt. `citation_validity_rate` bajó levemente respecto a una corrida intermedia (0.90 → 0.80) sin ningún cambio de código entre una corrida y la otra — recordatorio de que el LLM muestrea con temperatura > 0, así que estas métricas tienen varianza entre corridas y un solo número no captura eso. La latencia también varió bastante entre corridas (30-45s en unas, 12.4s en esta) según qué tan caliente estuviera el modelo en memoria y la presión de RAM del momento (ver abajo) — otra razón para no sobre-interpretar un solo run.

## Sobre la latencia y los recursos de la máquina

Esta máquina tiene 16 GB de RAM. Con el modelo de embeddings (~1.1 GB), el reranker (~1.1 GB) y el LLM de Ollama (~4.7 GB) cargados a la vez, una corrida de evaluación llegó a usar 6.9 GB de los 8 GB de swap disponibles — memoria bajo presión real, con paginación activa. Esto es información honesta sobre los límites de correr "todo local" en hardware de consumo: funciona, pero el primer cuello de botella no es el código, es la RAM disponible para tener tres modelos residentes simultáneamente. Para uso en producción (no portafolio), el primer paso sería evitar tener los tres modelos cargados a la vez, o moverse a un modelo más pequeño.

## Corpus ampliado a 11 libros — resultado real (`eval/results/20260625_120715.json`)

| Métrica | 2 libros | 11 libros |
|---|---|---|
| keyword_hit_rate | 1.00 | 0.90 |
| book_hit_rate | 1.00 | 0.89 |
| citation_validity_rate | 0.80 | 0.70 |
| out_of_domain_refusal_rate | 1.00 | 0.80 |
| out_of_domain_fabricated_citation_rate | 0.20 | 0.40 |
| latencia promedio | 12.4s | 43.3s |

Empeoró en todas las métricas, de forma consistente con lo esperado al escalar 5.5x el corpus (1899 → 6957 chunks totales) sin cambiar el modelo de reranking ni el tamaño del top-k: más libros significa más candidatos compitiendo por el mismo top-5 final, y temas que antes tenían una sola fuente clara en el corpus ahora compiten con pasajes superficialmente similares de otros libros. Esto no es una regresión de código — es la razón por la que un sistema de retrieval en producción con un corpus grande normalmente necesita ajustar `top_k` de FAISS, el tamaño del reranking, o filtros adicionales por tema/libro, ninguno de los cuales se justificaba con 2 libros.

La latencia subió de forma desproporcionada (3.5x) frente al crecimiento del corpus (5.5x en chunks, pero la búsqueda FAISS sigue siendo milisegundos): la causa real no es el tamaño del índice, sino dos cambios de infraestructura hechos en esta misma fase para resolver un segfault real (ver [docs/04-indexacion.md](04-indexacion.md)) — forzar el embedder y el reranker a CPU (en vez de MPS/GPU) y la presión de memoria de la máquina de 16 GB corriendo simultáneamente el embedder, el reranker y Ollama. La sección de latencia más abajo ya documentaba esta máquina como el cuello de botella; el corpus ampliado simplemente lo hizo más visible.

No se "arregló" nada de esto en esta fase — documentarlo honestamente y dejarlo como limitación conocida es preferible a ajustar el test set o el umbral de las métricas para que luzcan mejor.

## Corpus ampliado a 436 fuentes — la integración del archivo personal "Prolac"

Tras integrar el archivo personal de 685 PDFs (ver [docs/01-extraccion.md](01-extraccion.md)), correr de nuevo el test set de 15 preguntas (`eval/results/20260626_160938.json`) expuso una regresión real y dos bugs distintos — no uno solo.

| Métrica | 11 libros | 436 fuentes (primera corrida) |
|---|---|---|
| keyword_hit_rate | 0.90 | 0.80 |
| book_hit_rate | 0.89 | 0.44 |
| citation_validity_rate | 0.70 | 0.30 |
| out_of_domain_fabricated_citation_rate | 0.40 | 0.80 |

### Hallazgo 1: `book_hit` cayó porque el test set asumía un mundo de 2 fuentes por tema, no porque la recuperación empeoró

Inspeccionando los casos que fallaban `book_hit` (polyurea, zinc-rich, corrosión galvánica): en cada uno, la respuesta citaba correctamente una fuente real y relevante del archivo Prolac que **no existía cuando se escribió el test set** — por ejemplo, "What is polyurea used for?" ahora se responde desde *Polyurethanes (Meier-Westhues)*, un libro dedicado a poliuretanos, más específico que el capítulo genérico de *Coatings Materials* que el test esperaba. No es una alucinación ni una recuperación peor: es una fuente mejor, que el test no podía anticipar.

**Corrección:** se quitó `expected_book` de esos 3 casos en [`src/evaluation/testset.py`](../src/evaluation/testset.py) — mismo criterio que el caso de "primer" documentado arriba, aplicado ahora a una escala mayor porque el corpus creció de 2 a 436 fuentes. `expected_keywords` se mantiene intacto en todos los casos: sigue siendo la señal honesta de si el tema realmente se encontró, sin importar en qué fuente.

Dos preguntas (`parylene`, `corrosión por picadura`) siguen fallando *también* `keyword_hit` — esa sí es una caída real de recall, no un defecto del test: con 436 fuentes compitiendo por el mismo top-5 final, un pasaje específico puede quedar fuera del top-k aunque el tema exista en el corpus (verificado por separado, no solo asumido). Se deja documentado como limitación abierta, igual que el resto de esta sección — no se ajustó `top_k` ni el reranker para forzar que suba, siguiendo el mismo criterio de la fase 4 de no ajustar parámetros solo para que una métrica luzca mejor.

### Hallazgo 2: bug real en el regex de citas — los títulos `(Autor, Año)` rompían la extracción

`book_title_from_bracket_folder` (fase de extracción, ver docs/01) genera títulos como `"Coatings Materials and Surface Coatings (Tracton, 2007)"` — con una coma *dentro* del campo de libro. El regex de citas (`CITATION_RE` en [`src/evaluation/metrics.py`](../src/evaluation/metrics.py)) asumía que el primer campo no tenía comas (`[^,\]]+`), así que cortaba el libro en la primera coma — partiendo "Coatings Materials and Surface Coatings" / "(Tracton" / "2007) ..." en vez de un solo campo. Resultado: toda cita de uno de los 8 libros con esta convención de nombre quedaba mal parseada e invalidada, **incluso cuando el modelo citó perfectamente bien** — un bug en la herramienta de evaluación, no en el sistema evaluado.

**Corrección:** el campo de libro ahora excluye solo `]` (no `,`), apoyándose en que el campo de capítulo (que sí excluye comas) ancla dónde termina el libro y empieza el capítulo — ver el regex actualizado y su comentario en `metrics.py`, con test de regresión específico para un título con coma interna.

Además, se reforzó `SYSTEM_PROMPT` ([`src/generation/prompt.py`](../src/generation/prompt.py)) con una instrucción explícita: copiar la cita textualmente del encabezado del excerpt, nunca de un número de sección interno del propio texto (causa de un segundo patrón de cita malformada visto en los datos reales, ej. `[5.10, p. 467-468]`, donde el modelo usaba el número de capítulo como si fuera la cita completa).

### Resultado tras corregir el test set, el regex y el prompt (`eval/results/20260627_163203.json`)

| Métrica | 436 fuentes (primera corrida) | Tras los 3 fixes |
|---|---|---|
| keyword_hit_rate | 0.80 | 0.80 |
| book_hit_rate | 0.44 | 0.67 |
| citation_validity_rate | 0.30 | 0.70 |
| out_of_domain_fabricated_citation_rate | 0.80 | 0.60 |

`citation_validity_rate` (0.30→0.70) y `book_hit_rate` (0.44→0.67, sobre los 6 casos que conservan `expected_book`) recuperan niveles comparables a los del corpus de 11 libros — confirmando que la caída inicial era mayormente artefacto del test y del bug de regex, no degradación real de retrieval/generación. `out_of_domain_fabricated_citation_rate` sigue siendo ruidoso entre corridas (0.20/0.60/0.80 vistos en distintas ejecuciones con el mismo código) porque el LLM local muestrea con temperatura > 0 — ya documentado como limitación conocida arriba; no se persiguió más allá de esto, sería sobre-ajustar a una sola corrida.

## Qué queda abierto, a propósito

- `fabricated_citation_rate = 0.20` no es cero. Documentado arriba como limitación conocida del modelo, no oculto.
- El conjunto de prueba sigue siendo de 15 preguntas — suficiente para encontrar y corregir 3 problemas reales en esta fase, no suficiente para afirmar cobertura estadística robusta.
- Las métricas basadas en un LLM con temperatura > 0 varían entre corridas — un solo run no es una medición definitiva, sería deseable promediar varias corridas si esto fuera más allá de un portafolio.
- Sigue sin haber un juicio de calidad de la *redacción* de la respuesta (solo de si cita correctamente) — un LLM-as-judge sería el siguiente paso natural si el proyecto creciera más allá de portafolio.
