"""
Compiled regex patterns and onset-timing constants for the differential
diagnosis agent.

Kept separate from lexicons so importing patterns does not drag in the large
data tables, and vice versa.
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Final

# Radiation / spread of pain detection.
_RADIATION_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b(?:fino a(?:l|lla|llo|i|gli|lle)?|si estende|estende(?:rsi|ndosi)?|"
    r"diffonde|diffondersi|raggiunge|arriva (?:al|alla|allo|ai|agli|alle)|"
    r"anche (?:al|alla|allo|ai|agli|alle|in)|irradia(?:to|ta)?|"
    r"verso (?:il|la|lo|i|gli|le)|si propaga)\b",
    re.IGNORECASE,
)

_SEVERITY_REGEX: Final[re.Pattern[str]] = re.compile(
    r"(?:nrs|scala|severità|intensità|punteggio)\s*[:=]?\s*(\d{1,2})", re.IGNORECASE
)

# Italian onset/timing markers. Each tuple is (regex, callable→datetime|None).
# ``_ONSET_QUAL`` absorbs the optional approximate qualifier between "da" and
# the number ("da più di 10 anni", "da circa 3 giorni", "da oltre 2 mesi").
_ONSET_QUAL: Final[str] = r"(?:circa\s+|quasi\s+|oltre\s+|pi[uù]\s+di\s+|almeno\s+)?"
_ONSET_HOURS_REGEX: Final[re.Pattern[str]] = re.compile(
    rf"\bda\s+{_ONSET_QUAL}(\d{{1,3}})\s*(or[ae]|h)\b", re.IGNORECASE
)
_ONSET_DAYS_REGEX: Final[re.Pattern[str]] = re.compile(
    rf"\bda\s+{_ONSET_QUAL}(\d{{1,3}})\s*(giorn[oi]|gg)\b", re.IGNORECASE
)
_ONSET_WEEKS_REGEX: Final[re.Pattern[str]] = re.compile(
    rf"\bda\s+{_ONSET_QUAL}(\d{{1,3}})\s*settiman[ae]\b", re.IGNORECASE
)
_ONSET_MINUTES_REGEX: Final[re.Pattern[str]] = re.compile(
    rf"\bda\s+{_ONSET_QUAL}(\d{{1,3}})\s*minut[oi]\b", re.IGNORECASE
)
_ONSET_MONTHS_REGEX: Final[re.Pattern[str]] = re.compile(
    rf"\bda\s+{_ONSET_QUAL}(\d{{1,3}})\s*mes[ei]\b", re.IGNORECASE
)
_ONSET_YEARS_REGEX: Final[re.Pattern[str]] = re.compile(
    rf"\bda\s+{_ONSET_QUAL}(\d{{1,3}})\s*ann[oi]\b", re.IGNORECASE
)

_ONSET_KEYWORDS: Final[tuple[tuple[str, timedelta], ...]] = (
    ("adesso", timedelta(minutes=5)),
    ("in questo momento", timedelta(minutes=5)),
    ("ora", timedelta(minutes=5)),
    ("poco fa", timedelta(minutes=30)),
    ("pochi minuti fa", timedelta(minutes=15)),
    ("un'ora fa", timedelta(hours=1)),
    ("mezz'ora fa", timedelta(minutes=30)),
    # Risveglio: most specific first so substring matches don't shadow them.
    ("appena sveglio", timedelta(hours=8)),
    ("appena svegliata", timedelta(hours=8)),
    ("appena svegliato", timedelta(hours=8)),
    ("appena alzato", timedelta(hours=8)),
    ("appena alzata", timedelta(hours=8)),
    ("al risveglio", timedelta(hours=8)),
    ("da quando mi sono svegliato", timedelta(hours=8)),
    ("da quando mi sono svegliata", timedelta(hours=8)),
    ("mi sono svegliato", timedelta(hours=8)),
    ("mi sono svegliata", timedelta(hours=8)),
    # Notte.
    ("stanotte", timedelta(hours=10)),
    ("questa notte", timedelta(hours=10)),
    ("durante la notte", timedelta(hours=10)),
    # Mattina (incluse varianti regionali "stamani"/"stamane").
    ("da stamattina", timedelta(hours=6)),
    ("da stamani", timedelta(hours=6)),
    ("da stamane", timedelta(hours=6)),
    ("da questa mattina", timedelta(hours=6)),
    ("stamattina", timedelta(hours=6)),
    ("stamani", timedelta(hours=6)),
    ("stamane", timedelta(hours=6)),
    ("questa mattina", timedelta(hours=6)),
    # Sera/pomeriggio.
    ("stasera", timedelta(hours=2)),
    ("questa sera", timedelta(hours=2)),
    ("oggi pomeriggio", timedelta(hours=3)),
    ("nel pomeriggio", timedelta(hours=4)),
    ("da oggi", timedelta(hours=6)),
    ("oggi", timedelta(hours=6)),
    ("ieri sera", timedelta(days=1)),
    ("ieri notte", timedelta(days=1)),
    ("ieri mattina", timedelta(days=1, hours=6)),
    ("ieri pomeriggio", timedelta(days=1)),
    ("ieri", timedelta(days=1)),
    ("l'altro ieri", timedelta(days=2)),
    ("altro ieri", timedelta(days=2)),
    ("due giorni fa", timedelta(days=2)),
    ("tre giorni fa", timedelta(days=3)),
    ("qualche giorno fa", timedelta(days=3)),
    ("settimana scorsa", timedelta(days=7)),
    ("la settimana scorsa", timedelta(days=7)),
    ("qualche settimana fa", timedelta(weeks=2)),
    ("mese scorso", timedelta(days=30)),
    ("il mese scorso", timedelta(days=30)),
    ("qualche mese fa", timedelta(days=60)),
)

_FORTE_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b(molto\s+forte|fortissim[oa]|insopportabile|atroce)\b", re.IGNORECASE
)
_MEDIUM_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b(forte|intens[oa])\b", re.IGNORECASE
)
_MILD_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b(lieve|leggero|moderato)\b", re.IGNORECASE
)

# Italian denial markers. The parser scans each lexicon trigger appearing in
# the utterance and checks whether a negation cue sits within a short window
# *before* the trigger (typical Italian negation surface: "non ho febbre",
# "nessuna nausea", "niente vomito", "senza tosse", "no, non ho la febbre").
# Window is short because chained clauses can flip polarity ("non ho febbre,
# ho solo tosse" must not deny "tosse").
#
# CRITICAL: substring matching is unsafe for short cues — "no " collides with
# "sono ", "non" collides with the Italian word "nonna". Each cue is compiled
# as a regex anchored to word boundaries (or punctuation/start-of-string for
# the trailing "no" variants).
_DENIAL_CUE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bnon\s+ho\b",
        r"\bnon\s+ha\b",
        r"\bnon\s+avvert[oe]\b",
        r"\bnon\s+sent[oe]\b",
        r"\bnon\s+riferis[co][oe]\b",
        r"\bnon\s+not[oa]\b",
        r"\bnon\s+c['']è\b",
        r"\bnon\s+c['']e\b",
        r"\bnon\s+present[ei]\b",
        r"\bnego\b",
        r"\bnega\b",
        r"\bniente\b",
        r"\bnessun[oa]?\b",
        r"\bsenza\b",
        r"(?:^|[,.;:!?\s])no(?=[\s,.;:!?])",
        r"\bmai\s+avut[oa]\b",
        r"\bnon\s+mi\s+pare\b",
        r"\bnon\s+credo\b",
        r"\bmai\s+prese\b",
        r"\bmai\s+presi\b",
    )
)

_DENIAL_WINDOW_CHARS: Final[int] = 48

# Global-denial patterns — short Italian replies that mean "no, niente" for
# whatever slot the agent just asked about. Used to mark allergy/medication/
# PMH slots as satisfied without forcing the agent to re-ask twice.
_GLOBAL_DENIAL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    # Single-word denials and their light variants.
    re.compile(
        r"^(?:no|niente|nulla|mai|nessun[oa]?)\s*[.,!?]*$",
        re.IGNORECASE,
    ),
    # "no, mai" / "no grazie" / "no nessuno".
    re.compile(
        r"^no[\s,.]+(?:mai|grazie|nessun[oa]?|niente|nulla)\s*[.,!?]*$",
        re.IGNORECASE,
    ),
    # "nessun farmaco" / "nessuna allergia" / "niente di particolare".
    re.compile(
        r"^(?:no\s*,?\s*)?(?:nessun[oa]?|niente|nulla)\s+\w+\s*[.,!?]*$",
        re.IGNORECASE,
    ),
)

# Polarity flippers: when one of these appears between a denial cue and the
# symptom trigger, the symptom is **not** denied (the clause has switched
# from negation to affirmation).
_POLARITY_FLIP_MARKERS: Final[tuple[str, ...]] = (
    ", ",
    "; ",
    ". ",
    "! ",
    "? ",
    " ma ",
    " però ",
    " pero ",
    " invece ",
    " mentre ",
    " solo ",
    " anche ",
    " ho ",
    " ha ",
    " avverto ",
    " avverte ",
    " sento ",
    " sente ",
    " noto ",
    " nota ",
    " presento ",
    " presenta ",
    " riferisco ",
    " riferisce ",
)

# Italian aggravating / relieving modifier cues. Capturing the *clause* the
# patient used (truncated) gives the clinician the raw context while letting
# the slot-fill predicate recognise the modifier via the canonical
# ``peggiora:`` / ``migliora:`` prefix.
_AGGRAVATING_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b("
    r"peggior[aoi]|aggrav[aoi]|scatena|provoca|"
    r"aumenta\s+con|fa\s+male\s+quando|fa\s+stare\s+peggio|"
    r"peggio\s+con|peggio\s+quando|peggio\s+se"
    r")\b",
    re.IGNORECASE,
)
_RELIEVING_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b("
    r"miglior[aoi]|allevi[aoi]|scompare|sparisce|sparito|"
    r"si\s+attenua|passa\s+con|passa\s+se|"
    r"riduce|ridotto|cala|calmo\s+con|allevia\s+con|"
    r"sto\s+meglio\s+(?:con|se|quando)|mi\s+sento\s+meglio"
    r")\b",
    re.IGNORECASE,
)
