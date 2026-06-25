# 06 — Generación con citación obligatoria

## Qué es "grounding" y por qué es la pieza que justifica todo lo anterior

Un LLM general, preguntado directamente "¿qué es la corrosión por picadura?", contestaría usando su conocimiento de entrenamiento — sin decir de dónde lo sacó, y sin garantía de que sea correcto para *tus* libros específicos. "Grounding" significa forzar al modelo a responder **solo** con lo que está en los chunks recuperados, y a señalar exactamente cuál. Sin esto, todo el trabajo de las fases 1-5 (extracción, chunking, embeddings, índice, reranking) sería decorativo — el LLM podría ignorarlo y alucinar igual.

## Cómo se fuerza el grounding: instrucciones explícitas, no magia

`SYSTEM_PROMPT` (en `src/generation/prompt.py`) le da al modelo tres reglas explícitas:
1. Responder *solo* con los fragmentos del mensaje, nunca con conocimiento propio.
2. Cerrar cada afirmación con una cita exacta `[Libro, Capítulo, p. X-Y]`.
3. Si los fragmentos no alcanzan para responder, decirlo en vez de adivinar.

No hay ningún mecanismo que *obligue* técnicamente al modelo a cumplir esto — es una instrucción, no una restricción de la arquitectura. Por eso se valida con pruebas reales (abajo), no se asume.

## Formato de citación

`format_citation()` reutiliza exactamente los campos que cada chunk viene cargando desde la fase 2 (`book`, `chapter`, `page_start`, `page_end`) — ninguna fase de generación necesita volver a tocar el PDF original ni inventar metadata nueva. `chapter_label()` maneja los dos formatos de capítulo que coexisten en el corpus: capítulos numéricos puros (libros multi-archivo → "Chapter 7") y títulos descriptivos ya extraídos del TOC (libros de archivo único → "5. Corrosion Failures" se usa tal cual).

## Decisión: el idioma de respuesta lo decide el modelo, no un parámetro

En vez de detectar el idioma de la pregunta con código y pasar un flag, la instrucción "responde en el mismo idioma de la pregunta" queda en el system prompt y se delega al modelo. Es más simple y, validado en pruebas reales, funciona de forma confiable tanto en español como en inglés.

## Validación con preguntas reales

**Pregunta en español, dentro del corpus** — `"¿Qué es la corrosión por picadura?"`:
> La corrosión por picadura es un tipo de corrosión localizada que se caracteriza por la formación de cavidades o "huecos" en el material. Es considerada más peligrosa que la corrosión uniforme debido a su dificultad para ser detectada, predicha y diseñada contra ella **[Handbook of Corrosion Engineering, 5. Corrosion Failures, p. 343-345]**.

**Pregunta en inglés, dentro del corpus** — `"What is polyurea used for in protective coatings?"`:
> Polyurea is used for protective coatings due to its rapid curing ability, ability to be sprayed on damp or wet surfaces without performance degradation, and excellent resistance to physical rupture, water, chemicals, and weather **[Coatings Materials and Surface Coatings, Chapter 7, p. 1-2, 3-4]**.

**Pregunta fuera de dominio** — `"¿Cuál es la capital de Mongolia?"`:
> Lo siento, pero los fragmentos proporcionados no contienen información sobre la capital de Mongolia ni sobre ningún tema relacionado. Los pasajes se centran en reacciones químicas y datos de corrosión a alta temperatura para diversos materiales metálicos.

El tercer caso es el más importante de los tres: confirma que el modelo prefiere admitir falta de información antes que alucinar — el comportamiento exacto que el grounding busca garantizar.

## Qué no cubre esta fase

No hay todavía una medida objetiva de qué tan seguido el modelo *realmente* cumple las reglas del prompt a gran escala (más allá de estos 3 casos de prueba manual) — eso es exactamente lo que la fase 7 (evaluación) debe cuantificar con un conjunto de preguntas más grande.
