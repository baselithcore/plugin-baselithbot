from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    """
    Modello di richiesta per il chatbot.
    Contiene la query dell'utente e, opzionalmente, il conversation_id.
    Il flag `stream` viene accettato per compatibilità ma l'endpoint dedicato
    allo streaming è `/chat/stream`.
    """

    query: str
    conversation_id: Optional[str] = None
    stream: Optional[bool] = False
    rag_only: bool = False
    kb_label: Optional[str] = None
    metadata: Dict[str, Any] = {}

    model_config = ConfigDict(extra="forbid")  # rifiuta campi non previsti


class FeedbackDocumentReference(BaseModel):
    """
    Riferimento a una fonte (file locale o URL) utilizzata nella risposta.
    - document_id: identificativo interno del documento indicizzato
    - path/url: posizione della fonte (filesystem o esterna)
    - title: descrizione leggibile per l'admin
    - source_type: categoria della fonte (path/url)
    - score: punteggio massimo assegnato dal reranker (se disponibile)
    """

    document_id: Optional[str] = None
    title: Optional[str] = None
    path: Optional[str] = None
    url: Optional[str] = None
    origin: Optional[str] = None
    source_type: Optional[Literal["path", "url"]] = None
    score: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class FeedbackRequest(BaseModel):
    """
    Modello per la registrazione di un feedback su una risposta generata.
    - query: la domanda posta
    - answer: la risposta fornita dal bot
    - feedback: valutazione positiva o negativa
    - conversation_id: sessione del widget (se presente)
    - sources: riferimenti ai documenti utilizzati nella risposta
    """

    query: str
    answer: str
    feedback: Literal["positive", "negative"]
    conversation_id: Optional[str] = None
    sources: Optional[List[Union[FeedbackDocumentReference, Dict[str, Any]]]] = None
    comment: Optional[str] = None

    model_config = ConfigDict(extra="allow")
