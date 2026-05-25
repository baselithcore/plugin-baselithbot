"""Seed default Italian + EU + World policies into vector store. Tenant-aware."""
from __future__ import annotations
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docheck-engine" / "src"))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker  # noqa: E402
from docheck.core.config import settings  # noqa: E402
from docheck.core.tenant import set_tenant  # noqa: E402
from docheck.db.models import Base, Policy, PolicyRule  # noqa: E402
from docheck.services.embedding import embed, get_or_create_collection  # noqa: E402


SEED_POLICIES = [
    {
        "id": "IT_GDPR_2026", "version": "3.0.0", "scope": "global_default", "lang": "it",
        "title": "GDPR Italia",
        "rules": [
            {"id": "GDPR-Art-13", "type": "presence", "severity": "fail",
             "excerpt": "Il titolare informa l'interessato del periodo di conservazione dei dati personali o, se non è possibile, dei criteri utilizzati per determinare tale periodo."},
            {"id": "GDPR-Art-5",  "type": "presence", "severity": "fail",
             "excerpt": "I dati personali devono essere adeguati, pertinenti e limitati a quanto necessario rispetto alle finalità per le quali sono trattati."},
            {"id": "GDPR-Art-7",  "type": "presence", "severity": "warn",
             "excerpt": "Quando il trattamento è basato sul consenso, il titolare deve essere in grado di dimostrare che l'interessato ha prestato il proprio consenso."},
        ],
    },
    {
        "id": "IT_Codice_Civile_Contratti", "version": "1.2.0", "scope": "global_default", "lang": "it",
        "title": "Codice Civile — Disciplina contratti",
        "rules": [
            {"id": "CC-Recesso", "type": "presence", "severity": "warn",
             "excerpt": "Il diritto di recesso deve essere specificato in clausola contrattuale espressa."},
            {"id": "CC-Foro",    "type": "presence", "severity": "warn",
             "excerpt": "Indicare foro competente per le controversie derivanti dal contratto."},
        ],
    },
    {
        "id": "EU_AI_Act_2024", "version": "1.0.0", "scope": "eu", "lang": "en",
        "title": "EU AI Act 2024",
        "rules": [
            {"id": "AIACT-Transparency", "type": "presence", "severity": "fail",
             "excerpt": "Providers of high-risk AI systems shall ensure transparency obligations toward users."},
        ],
    },
]


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", default="default", help="Target tenant id")
    args = ap.parse_args()

    set_tenant(args.tenant)
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    eng = create_async_engine(f"sqlite+aiosqlite:///{settings.db_path}")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    coll = get_or_create_collection("policy_rules")

    async with async_sessionmaker(eng, expire_on_commit=False)() as db:
        for p in SEED_POLICIES:
            existing = await db.get(Policy, (p["id"], p["version"]))
            if existing is None:
                db.add(Policy(
                    id=p["id"], version=p["version"], title=p["title"],
                    scope=p["scope"], lang=p["lang"], created_by=None,
                    tenant_id=args.tenant,
                ))
            for r in p["rules"]:
                if await db.get(PolicyRule, r["id"]) is None:
                    db.add(PolicyRule(
                        id=r["id"], policy_id=p["id"], policy_version=p["version"],
                        rule_type=r["type"], severity=r["severity"], excerpt=r["excerpt"],
                    ))
        await db.commit()

    # Index excerpts in Chroma
    rule_ids: list[str] = []
    excerpts: list[str] = []
    metadatas: list[dict] = []
    for p in SEED_POLICIES:
        for r in p["rules"]:
            rule_ids.append(r["id"])
            excerpts.append(r["excerpt"])
            metadatas.append({
                "policy_id": p["id"], "version": p["version"],
                "scope": p["scope"], "title": p["title"], "excerpt": r["excerpt"],
            })
    vectors = embed(excerpts)
    coll.upsert(ids=rule_ids, documents=excerpts, metadatas=metadatas, embeddings=vectors)
    print(f"Seeded {len(rule_ids)} rules across {len(SEED_POLICIES)} policies for tenant '{args.tenant}'.")


if __name__ == "__main__":
    asyncio.run(main())
