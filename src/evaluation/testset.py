"""A small, hand-written test set for evaluating retrieval and generation quality.

There's no human-labeled "gold" relevance dataset for this corpus — building
one properly would mean manually reading hundreds of chunks. Instead, each
in-domain question is paired with a topic keyword and a source book that
were verified to actually occur in that book's chunks (see docs/07 for the
verification), giving an objective, if approximate, way to check whether
retrieval found something on-topic without requiring manual judgment per
question. Out-of-domain questions check the opposite: that the system
admits it doesn't know, instead of guessing from the LLM's own training data.

This is intentionally small (15 cases). The point of phase 7 is having a
repeatable, automatable check at all — not exhaustive coverage.
"""

COATINGS_BOOK = "Coatings Materials and Surface Coatings"
HANDBOOK_BOOK = "Handbook of Corrosion Engineering"

TEST_CASES = [
    # In-domain — Coatings Materials and Surface Coatings
    {
        "query": "What is polyurea used for in protective coatings?",
        "in_domain": True,
        "expected_book": COATINGS_BOOK,
        "expected_keywords": ["polyurea"],
    },
    {
        "query": "¿Qué es el Parylene y para qué se usa como recubrimiento?",
        "in_domain": True,
        "expected_book": COATINGS_BOOK,
        "expected_keywords": ["parylene"],
    },
    {
        "query": "What are thermoplastic elastomers?",
        "in_domain": True,
        "expected_book": COATINGS_BOOK,
        "expected_keywords": ["thermoplastic elastomer"],
    },
    {
        # No expected_book: "primer" is legitimately covered in both books
        # (66 occurrences in Coatings Materials, 52 in the Handbook's own
        # "Protective Coatings" chapter) — found via a real eval failure,
        # see docs/07-evaluacion.md. Checking the book here would penalize
        # a correct answer just for citing the "wrong" of two valid sources.
        "query": "¿Qué función cumple un primer en un sistema de recubrimiento?",
        "in_domain": True,
        "expected_keywords": ["primer"],
    },
    {
        "query": "What is a zinc-rich coating used for?",
        "in_domain": True,
        "expected_book": COATINGS_BOOK,
        "expected_keywords": ["zinc-rich"],
    },
    # In-domain — Handbook of Corrosion Engineering
    {
        "query": "¿Qué es la corrosión por picadura?",
        "in_domain": True,
        "expected_book": HANDBOOK_BOOK,
        "expected_keywords": ["pitting"],
    },
    {
        "query": "What is cathodic protection?",
        "in_domain": True,
        "expected_book": HANDBOOK_BOOK,
        "expected_keywords": ["cathodic protection"],
    },
    {
        "query": "¿Qué es la corrosión galvánica?",
        "in_domain": True,
        "expected_book": HANDBOOK_BOOK,
        "expected_keywords": ["galvanic"],
    },
    {
        "query": "What causes stress corrosion cracking?",
        "in_domain": True,
        "expected_book": HANDBOOK_BOOK,
        "expected_keywords": ["stress corrosion"],
    },
    {
        "query": "¿Qué son los inhibidores de corrosión?",
        "in_domain": True,
        "expected_book": HANDBOOK_BOOK,
        "expected_keywords": ["inhibitor"],
    },
    # Out-of-domain — should trigger a refusal, not a guess
    {
        "query": "¿Cuál es la capital de Mongolia?",
        "in_domain": False,
    },
    {
        "query": "What's a good recipe for chocolate cake?",
        "in_domain": False,
    },
    {
        "query": "¿Quién ganó el mundial de fútbol de 2022?",
        "in_domain": False,
    },
    {
        "query": "What is the best programming language for web development?",
        "in_domain": False,
    },
    {
        "query": "¿Cuántos planetas tiene el sistema solar?",
        "in_domain": False,
    },
]
