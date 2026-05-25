"""Suite di evals per la qualità RAG.

Pure functions + dataclass result. Niente assert pytest qui dentro:
gli evals girano via CLI (``wiki-wl evals run --golden <path>``) e
producono report machine-readable. Pytest può importare e asserire
su soglie minime in test separati.
"""
