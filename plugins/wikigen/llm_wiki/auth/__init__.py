"""Auth + multi-tenant runtime.

Pacchetto creato in Fase 0; il contenuto reale (JWT, refresh token,
tenant context, password hashing, security middleware) arriva in
Fase 2 portando i moduli equivalenti da ``agent-jira`` e adattandoli.

Niente export per ora: tenere il package importabile abilita
``[tool.setuptools].packages`` e ``llm_wiki.auth.*`` import path
stabili per i moduli che verranno aggiunti.
"""
