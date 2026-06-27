"""Chat UI over the RAG pipeline — `streamlit run app.py`.

A thin presentation layer: every answer still goes through
src.generation.answer.answer_question, the same function the notebook and
the evaluation suite use. Nothing about retrieval or generation changes
here; this only adds a chat history and a sources panel on top.

Streamlit reruns this whole script on every user interaction. The
embedder/reranker singletons in src/embeddings/embedder.py and
src/retrieval/reranker.py already survive reruns on their own (they're
module-level globals, not re-imported), so the @st.cache_resource warm-up
below isn't strictly required for correctness — it exists so the *first*
question a user asks doesn't silently eat the ~20-30s model-loading cost
with no feedback. Without it, the first chat message would look stalled.
"""

import streamlit as st

from src.generation.answer import answer_question
from src.generation.prompt import format_citation

st.set_page_config(page_title="RAG · Química de Recubrimientos", page_icon="🧪", layout="wide")


@st.cache_resource(show_spinner="Cargando modelos (solo la primera vez)...")
def warm_up():
    from src.embeddings.embedder import get_model as get_embedder
    from src.retrieval.reranker import get_model as get_reranker

    get_embedder()
    get_reranker()


warm_up()

if "messages" not in st.session_state:
    st.session_state.messages = []  # each: {"role", "content", "sources"}

with st.sidebar:
    st.header("🧪 RAG Chemistry")
    st.caption(
        "RAG construido desde cero (sin LangChain/LlamaIndex) sobre 436 fuentes de "
        "química de recubrimientos. 100% local: Ollama + FAISS + sentence-transformers."
    )
    st.markdown("[Ver el código en GitHub](https://github.com/Halexoh/RAG-chemistry)")
    st.divider()
    if st.session_state.messages:
        last_sources = st.session_state.messages[-1].get("sources")
        if last_sources:
            st.subheader("Fuentes de la última respuesta")
            for s in last_sources:
                st.markdown(format_citation(s))
                with st.expander("Ver fragmento"):
                    st.write(s["text"])

st.title("Pregúntale a los libros de recubrimientos")
st.caption("En español o inglés. Las respuestas citan siempre su fuente exacta.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if query := st.chat_input("¿Qué es la corrosión por picadura?"):
    st.session_state.messages.append({"role": "user", "content": query, "sources": None})
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        with st.spinner("Buscando en los libros y generando la respuesta..."):
            result = answer_question(query)
        st.write(result["answer"])

    st.session_state.messages.append(
        {"role": "assistant", "content": result["answer"], "sources": result["sources"]}
    )
    st.rerun()
