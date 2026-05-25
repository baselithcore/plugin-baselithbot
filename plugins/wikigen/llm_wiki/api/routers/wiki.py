"""Wiki browsing endpoints: groups index + page reader.

Drives the sidebar (``/api/wiki/pages``), the citation preview
(``/api/wiki/page/{id}``), and the grouping queries used by the
sidebar's "by garanzia / by edizione" tabs (``/api/groups[/{key}]``).
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request

from llm_wiki import config
from llm_wiki.admin.obsidian_init import read_state as read_obsidian_state
from llm_wiki.admin.tenants import TenantContext
from llm_wiki.api.deps import get_tenant
from llm_wiki.api.routers.system import serialize_rule
from llm_wiki.auth.obsidian_gate import user_can_open_obsidian
from llm_wiki.wiki.groups import compute_groups, get_rule, list_rules
from llm_wiki.wiki.parser import parse_file, walk_wiki


def _require_wiki_read_or_anon(request: Request) -> None:
    """Conditional wiki read gate (PR audit MED #5).

    Per design la wiki è browsing pubblico (stile Karpathy LLM-Wiki).
    Però quando il deploy ha ``AUTH_REQUIRED=true`` (multi-tenant
    produzione, no anonymous chat), enforce ``wiki.read``:

    - Postgres OFF → bypass (setup mode).
    - Postgres ON + AUTH_REQUIRED=false → bypass (dev / public wiki).
    - Postgres ON + AUTH_REQUIRED=true → richiede ``wiki.read``
      (seedato a tutti i 4 ruoli system → zero regressioni).
    """
    if not config.POSTGRES_ENABLED or not config.AUTH_REQUIRED:
        return
    from llm_wiki.auth.dependencies import require_permission

    require_permission("wiki.read")(request)


def _obsidian_uri(vault_root: Any, relative_path: str) -> str:
    """Build `obsidian://open?vault=<name>&file=<rel>` for the given page.

    `relative_path` is the file path relative to the vault root (e.g.
    `wiki/sources/abc.md`). Vault name override comes from
    `OBSIDIAN_VAULT_NAME`; otherwise it derives from the vault dir name.
    """
    vault_name = config.OBSIDIAN_VAULT_NAME or vault_root.name
    return f"obsidian://open?vault={quote(vault_name, safe='')}&file={quote(relative_path, safe='/')}"


router = APIRouter(dependencies=[Depends(_require_wiki_read_or_anon)])


@router.get("/api/groups")
def get_groups_index(ctx: TenantContext = Depends(get_tenant)) -> dict[str, Any]:
    return {"rules": [serialize_rule(r) for r in list_rules(ctx.pack)]}


@router.get("/api/groups/{rule_key}")
def get_groups(
    rule_key: str, ctx: TenantContext = Depends(get_tenant)
) -> dict[str, Any]:
    rule = get_rule(rule_key, ctx.pack)
    if rule is None:
        raise HTTPException(
            status_code=404, detail=f"unknown grouping rule: {rule_key}"
        )
    groups = compute_groups(rule, wiki_dir=ctx.wiki_dir, wiki_root=ctx.vault_root)
    return {
        "rule": serialize_rule(rule),
        "count": len(groups),
        "groups": groups,
    }


@router.get("/api/wiki/pages")
def list_pages(ctx: TenantContext = Depends(get_tenant)) -> dict[str, Any]:
    files = walk_wiki(ctx.wiki_dir)
    pages: list[dict[str, Any]] = []
    for f in files:
        page = parse_file(f, ctx.vault_root)
        if not page:
            continue
        pages.append(
            {
                "document_id": page.document_id,
                "title": page.title,
                "type": page.page_type,
                "category": page.category,
                "tags": page.tags,
                "wikilinks_count": len(page.wikilinks),
            }
        )
    pages.sort(key=lambda p: (p["type"], p["category"], p["title"]))
    return {"count": len(pages), "pages": pages}


@router.get("/api/wiki/page/{doc_id:path}")
def get_page(
    doc_id: str,
    request: Request,
    ctx: TenantContext = Depends(get_tenant),
) -> dict[str, Any]:
    candidate = ctx.wiki_dir / f"{doc_id}.md"
    if not candidate.exists():
        matches = list(ctx.wiki_dir.rglob(f"{doc_id.split('/')[-1]}.md"))
        if not matches:
            raise HTTPException(status_code=404, detail=f"page not found: {doc_id}")
        candidate = matches[0]

    page = parse_file(candidate, ctx.vault_root)
    if not page:
        raise HTTPException(status_code=500, detail="parse failed")

    # Two-key gate: per-tenant marker + per-user permission. Either
    # missing → omit the field so the frontend hides the "Open in
    # Obsidian" button (no surprise redirect to a vault the caller
    # cannot read).
    obsidian_uri: str | None = None
    if read_obsidian_state(ctx.vault_root).enabled and user_can_open_obsidian(request):
        obsidian_uri = _obsidian_uri(ctx.vault_root, page.relative_path)

    return {
        "document_id": page.document_id,
        "title": page.title,
        "type": page.page_type,
        "category": page.category,
        "tags": page.tags,
        "aliases": page.aliases,
        "wikilinks_out": page.wikilinks,
        "body": page.body,
        "relative_path": page.relative_path,
        "obsidian_uri": obsidian_uri,
    }
