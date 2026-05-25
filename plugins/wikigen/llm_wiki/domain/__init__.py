"""Domain abstraction layer.

A *Domain Pack* is a self-contained directory under ``domains/<name>/``
declaring everything that varies between vertical wikis: prompts, page-type
taxonomy, frontmatter schema, few-shot examples, UI labels.

The core engine is parametric on a :class:`DomainPack`. At process startup
:func:`load_pack` reads ``APP_DOMAIN`` from the environment, materialises
the pack from disk, validates it against :class:`DomainPack` and caches it
for the rest of the process lifetime (single-tenant by design).
"""

from __future__ import annotations

from llm_wiki.domain.pack import (
    DomainPack,
    FrontmatterField,
    GroupingRule,
    PageType,
    UILabels,
)
from llm_wiki.domain.prompts import (
    PromptNotFoundError,
    PromptRegistry,
    get_registry,
    render,
    reset_registry_cache,
)
from llm_wiki.domain.registry import get_pack, load_pack, reset_pack_cache
from llm_wiki.domain.schema import (
    FrontmatterSchema,
    FrontmatterValidationError,
    get_schema,
    reset_schema_cache,
)
from llm_wiki.domain.strategies import (
    DefaultPageTypeStrategy,
    ExtractorStrategy,
    GenerationContext,
    PageTypeStrategy,
    StrategyBundle,
    get_strategies,
    reset_strategies_cache,
    select_page_type_strategy,
)

__all__ = [
    "DefaultPageTypeStrategy",
    "DomainPack",
    "ExtractorStrategy",
    "FrontmatterField",
    "FrontmatterSchema",
    "FrontmatterValidationError",
    "GenerationContext",
    "GroupingRule",
    "PageType",
    "PageTypeStrategy",
    "PromptNotFoundError",
    "PromptRegistry",
    "StrategyBundle",
    "UILabels",
    "get_pack",
    "get_registry",
    "get_schema",
    "get_strategies",
    "load_pack",
    "render",
    "reset_pack_cache",
    "reset_registry_cache",
    "reset_schema_cache",
    "reset_strategies_cache",
    "select_page_type_strategy",
]
