"""Page-tree derivation — the folder-less document hierarchy.

The tree is a *derived* read model: every note carries an optional ``parent``
scalar in its frontmatter, and this module folds the flat note list into a
nested :class:`TreeNode` forest for the sidebar. Files stay flat and portable;
the hierarchy is reconstructed on demand and never stored as a structure.

Robust by construction: notes whose ``parent`` points at a missing note are
surfaced at the root (never dropped), and a defensive visited-set breaks any
cycle that a hand-edited file might introduce.
"""

from __future__ import annotations

from .models import NoteMeta, TreeNode


def _sort_key(meta: NoteMeta) -> tuple[int, int, str]:
    """Siblings ordered by explicit ``order`` first, then title (stable)."""
    has_order = 0 if meta.order is not None else 1
    return (has_order, meta.order or 0, meta.title.lower())


def build_tree(metas: list[NoteMeta]) -> list[TreeNode]:
    """Fold a flat note list into a nested forest of :class:`TreeNode`."""
    by_id = {m.id: m for m in metas}
    children: dict[str | None, list[NoteMeta]] = {}
    for meta in metas:
        # Dangling / self parent ⇒ promote to root so nothing is ever lost.
        parent = (
            meta.parent if meta.parent in by_id and meta.parent != meta.id else None
        )
        children.setdefault(parent, []).append(meta)

    def assemble(parent: str | None, seen: frozenset[str]) -> list[TreeNode]:
        out: list[TreeNode] = []
        for meta in sorted(children.get(parent, []), key=_sort_key):
            if meta.id in seen:  # cycle guard
                continue
            out.append(
                TreeNode(
                    id=meta.id,
                    title=meta.title,
                    children=assemble(meta.id, seen | {meta.id}),
                )
            )
        return out

    return assemble(None, frozenset())
