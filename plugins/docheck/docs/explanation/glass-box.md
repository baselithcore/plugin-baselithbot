# Glass Box

doCheck è **glass-box**: ogni verdetto del sistema è tracciabile, citabile, riproducibile. Questo documento spiega cosa significa e come è enforced tecnicamente.

## Tesi

Un compliance checker che dice "violazione GDPR — confidence 0.83" senza poter mostrare:

- **dove** nel documento (bbox, riga, pagina),
- **quale** clausola della normativa è stata violata (excerpt verbatim),
- **come** ci è arrivato (reasoning step-by-step),

è inutilizzabile in contesto enterprise. Auditor, DPO, legal counsel hanno bisogno di **prova**, non di output statistico.

doCheck fa l'opposto. Ogni `Finding` ha tutti e tre, **enforced a livello di tipo**.

## Finding contract

```python
# docheck-engine/src/docheck/schemas/finding.py
class Finding(BaseModel):
    id: str
    severity: Literal["FAIL", "WARN", "PASS", "INFO"]
    rule_id: str
    policy_ref: PolicyRef        # → excerpt verbatim della clausola
    evidence: Evidence            # → bbox + chunk_id + page
    explanation: str              # → spiegazione human-readable
    confidence: float
    reasoning: list[ReasoningStep]
```

Backed by [docheck-shared-schemas/finding.schema.json](../../docheck-shared-schemas/finding.schema.json) (single source of truth FE/BE).

### `evidence`

```python
class Evidence(BaseModel):
    chunk_id: str
    page: int
    line_start: int | None
    line_end: int | None
    bbox: tuple[float, float, float, float] | None  # (x0, y0, x1, y1) in punti PDF
    snippet: str                                     # testo verbatim del chunk
```

Garantisce che il viewer possa scrollare al punto preciso e disegnare highlight.

### `policy_ref`

```python
class PolicyRef(BaseModel):
    id: str            # rule id, es. "GDPR-ART-32"
    policy_id: str     # es. "EU_GDPR_2018"
    version: str       # SemVer policy
    title: str
    excerpt: str       # verbatim della clausola
```

`excerpt` è il punto critico: non è una parafrasi, è il testo letterale della normativa. Permette al revisore di:

- verificare con sentenza/regolamento ufficiale,
- copia-incollare in report legali,
- avere una prova citabile in tribunale.

### `reasoning`

```python
class ReasoningStep(BaseModel):
    agent: str                     # "legal", "technical", "pii"
    step: str                      # "retrieve" | "verify" | "decide"
    input: dict                    # what was passed
    output: dict                   # what was produced
    duration_ms: int
```

Catena step-by-step. Permette debug, post-mortem, e regression test deterministici.

## Enforcement — non è un gentleman agreement

Tre livelli di guardrail:

### 1. Pydantic validator

Validation custom rifiuta finding che:

- Hanno `evidence.bbox=None` su documenti con layout (PDF text-based, DOCX). Eccezione esplicita per TXT/MD: bbox sintetico generato dal parser.
- Hanno `policy_ref.excerpt` vuoto o di lunghezza < soglia.
- Non hanno `reasoning` chain.

Output LLM invalido → rifiutato lato schema, mai persistito.

### 2. Sub-string match retrieval

Per agenti RAG (`legal`, `pii` LLM verifier), `policy_ref.excerpt` deve essere **substring di un retrieval result reale**. Implementazione:

```python
def validate_excerpt(excerpt: str, retrieved_docs: list[str]) -> bool:
    norm = lambda s: re.sub(r"\s+", " ", s.lower().strip())
    e = norm(excerpt)
    return any(e in norm(d) for d in retrieved_docs)
```

Se l'agente "inventa" un excerpt non presente nel retrieval → finding scartato → warning loggato. Risolve il problema di hallucination LLM su contenuti normativi (rischio compliance critico).

### 3. Repair retry + failover

LLM JSON output non valido (parse fail o schema fail) → 1 retry con prompt di repair che mostra l'errore al modello → se ancora fail, agente skippa il chunk + push errore in `state.errors`.

Mai inventare per "fare quadrare" l'output.

## Conseguenze pratiche

### Per chi scrive policy

Vedi [tutorial 02](../tutorials/02-author-policy.md). `excerpt` deve essere **letterale** dalla normativa target. Parafrasi → l'agente non riuscirà a citarlo (substring fail) → policy effettivamente non applicabile.

### Per chi integra il sistema

Il viewer UI deve poter renderizzare bbox. Se il client custom ignora `evidence.bbox` o `policy_ref.excerpt`, sta degradando il valore del prodotto.

### Per audit

`GET /api/v1/reports/{id}` restituisce report firmato Ed25519. Un terzo (auditor esterno, DPO) può:

1. Recuperare public key da `/api/v1/info/pubkey`.
2. Validare `signature` sul `payload` canonico.
3. Per ogni finding nel payload, verificare manualmente `evidence` e `policy_ref` contro documento + normativa.

Riproducibilità completa.

## Telemetria reasoning

`state.trace` contiene tutti gli step di tutti gli agenti. UI espone via `Reasoning Drawer` ([docheck-ui/components/reasoning/](../../docheck-ui/components/reasoning/)). Permette di "guardare dentro" il LLM senza essere ML engineer.

## Perché questo non rallenta troppo

Costi:

- Substring match: O(n) sui retrieval result, < 1ms per finding.
- Pydantic validation: < 5ms per finding.
- Repair retry: solo se fail (target: < 5% finding).

Trade-off accettato: maggiore robustezza compliance >> latency overhead trascurabile.

## Anti-pattern

❌ "Il finding è giusto ma l'excerpt non matcha — degrada il check."
✅ Investiga: o l'agente ha allucinato, o il retrieval k è troppo basso, o la policy excerpt è scritta male.

❌ Nascondere `reasoning` agli utenti finali per "non confonderli".
✅ Mostralo, ma con UX progressiva (drawer chiuso di default, expandable).

❌ Confidence 1.0 da LLM semantic agent.
✅ LLM-based agent capped a 0.85; `1.0` riservato a deterministic check (regex, numeric, format).

## Vedi anche

- [agentic-flow.md](agentic-flow.md) — dove fit ogni agente nel flusso.
- [security-model.md](security-model.md) — perché audit chain + report signing complementano glass-box.
- [reference/schemas.md](../reference/schemas.md) — JSON contract Finding/Report.
- [blueprint/04_data_flow.md](../../blueprint/04_data_flow.md) — design intent originale.
