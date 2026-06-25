# 00 — Decisiones de arquitectura inicial

## Contexto

Primer RAG construido desde cero, alimentado con libros de química de recubrimientos en PDF (capítulos separados, mezcla de texto nativo y escaneado, mayormente en inglés). Objetivo doble: aprender los fundamentos de RAG en profundidad, y producir una pieza de portafolio presentable.

## Decisiones y por qué

**100% local (Ollama + FAISS) en vez de APIs en la nube**
Evita costos recurrentes y mantiene los PDFs (con derechos de autor) fuera de servicios de terceros. Apple Silicon tiene suficiente potencia para modelos de 7-8B parámetros cuantizados con latencia razonable.

**Sin frameworks (LangChain/LlamaIndex)**
El objetivo es entender el mecanismo interno de un RAG — chunking, embeddings, índice vectorial, retrieval, prompting — no solo saber invocar una librería. Cada pieza se construye a mano en `src/`.

**FAISS en vez de una vector DB con servidor (Chroma, Pinecone, Weaviate)**
No se necesita un servidor para una colección local de 50-200 libros. FAISS es una librería embebida: sin proceso adicional, sin red, fácil de razonar.

**Embeddings multilingües (ej. BAAI/bge-m3 o intfloat/multilingual-e5)**
El contenido fuente está en inglés pero las preguntas pueden hacerse en español. Un modelo multilingüe permite que una query en español recupere correctamente un chunk en inglés sin traducir manualmente antes de buscar.

**Citación obligatoria (libro/capítulo/página) en cada respuesta**
Para contenido técnico-científico, una respuesta sin fuente verificable no es confiable. Esto también obliga al pipeline a preservar metadata granular desde la extracción hasta la generación.

**PDFs fuente no se versionan en el repo (`.gitignore`)**
Los libros de química son material con derechos de autor; el repo público debe mostrar el *código* del pipeline, no redistribuir el contenido protegido.

**Documentación dual: `docs/` (decisiones) + notebook (walkthrough técnico)**
`docs/` está pensado para quien evalúa el proyecto rápido (reclutador, cliente). El notebook en `notebooks/` es el detalle pedagógico paso a paso para quien quiere entender o reproducir cada fase.
