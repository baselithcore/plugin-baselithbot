class JiraClientError(RuntimeError):
    """Errore generato quando l'integrazione Jira non riesce a completare l'operazione."""


__all__ = ["JiraClientError"]
