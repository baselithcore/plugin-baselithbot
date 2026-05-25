"""Italian PII / format regex patterns shared across technical rules and PII agent."""

import re

PATTERNS: dict[str, re.Pattern[str]] = {
    "codice_fiscale": re.compile(r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b"),
    "partita_iva": re.compile(r"\bIT?\d{11}\b"),
    "iban_it": re.compile(r"\bIT\d{2}[A-Z0-9]{23}\b"),
    "iso_date": re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
}

# Italian month names (full form). Used for verbose date detection.
IT_MONTHS = (
    r"gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre"
)

EN_MONTHS = (
    r"january|february|march|april|may|june|july|august|"
    r"september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
)

ANY_DATE = re.compile(
    r"\b("
    r"\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}"
    r"|\d{1,2}\s*°?\s+(?:" + IT_MONTHS + r")\s+\d{2,4}"
    r"|\d{1,2}\s+(?:" + EN_MONTHS + r")\s+\d{2,4}"
    r"|(?:" + EN_MONTHS + r")\s+\d{1,2},?\s+\d{2,4}"
    r")\b",
    re.IGNORECASE,
)

# Italian postal code (CAP): 5 digits.
CAP_IT = re.compile(r"\b\d{5}\b")

# Legal references: D.Lgs., L., DPR, Reg. UE — common malformed patterns.
LEGAL_REF = re.compile(
    r"\b(?:D\.?\s*Lgs\.?|D\.?\s*L\.?|D\.?\s*P\.?\s*R\.?|L\.?|Legge|"
    r"Reg\.?\s*UE|Regolamento\s+\(UE\)|Direttiva)\b[^.\n]{0,80}",
    re.IGNORECASE,
)

# Currency-bearing amount patterns: €1.234,56 or 1234.56 EUR or 1,234.56 USD.
AMOUNT_WITH_CURRENCY = re.compile(
    r"(?:€|\$|£|EUR|USD|GBP)\s*\d[\d.,]*|\d[\d.,]*\s*(?:€|\$|£|EUR|USD|GBP)\b",
    re.IGNORECASE,
)

# Bare amount candidates near currency-relevant lemmas (importo, prezzo, ecc.)
BARE_AMOUNT = re.compile(
    r"(?<![\w.,])\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?(?![\w])|\d+[.,]\d{2}\b"
)

CURRENCY_TRIGGERS = re.compile(
    r"\b(importo|prezzo|costo|canone|corrispettivo|amount|price|fee|cost)\b",
    re.IGNORECASE,
)
