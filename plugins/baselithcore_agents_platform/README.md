# BaselithCore Agents Platform

Create complex, **scope-bounded** coding agents from natural language, run them on
**Claude / OpenAI / local Ollama**, and ground every run in the framework's own
documentation over **MCP** — so agents build autonomously without drifting out of scope.

## What it does

1. **Natural language → blueprint.** `BlueprintBuilder` distils a free-text request
   into a validated `AgentBlueprint`: a persona, a provider, and a hard
   `BlueprintScope` (capability allow-list, documentation namespaces, iteration cap).
2. **Scoped execution.** `AgentRuntime` enforces the scope on every call, grounds the
   model in retrieved docs, and **composes the native `CodingAgent`** (sandbox-backed)
   for `fix`/`test` rather than re-implementing it.
3. **MCP doc-grounding.** The framework's Markdown corpus is indexed and exposed both
   as REST and as MCP tools (`search_baselith_docs`, `get_baselith_doc`,
   `create_agent`, `run_agent`).

## Architecture

```
plugin.py          RouterPlugin entry point — MCP tools, router, UI tab, config schema
service.py         Facade composing builder + runtime + docs + registry
builder.py         NL → AgentBlueprint (LLM JSON synthesis, defensive fallback)
runtime.py         Scope-enforced execution; delegates fix/test to coding_agent
providers.py       Claude / OpenAI / Ollama resolution over the core LLM config
docs_index.py      Dependency-free Markdown indexer for MCP grounding
registry.py        In-memory blueprint + run store (storage-shaped seam)
mcp_tools.py       MCP tool surface returned from get_mcp_tools()
router.py          Async FastAPI surface under /api/baselithcore_agents_platform
ui/                React + Vite dark-glass dashboard (Builder / Agents / Runs / Docs / Models)
```

Every source file is async, fully typed, and under the 500-LOC cap. The plugin is
covered by the official strict-typing gate and ships a verified `integrity_sha256`.

## Configuration (`configs/plugins.yaml`)

```yaml
baselithcore_agents_platform:
  enabled: true
  default_provider: ollama      # or anthropic / openai (needs LLM_API_KEY)
  # ollama_base: http://localhost:11434
```

## Dashboard

```bash
cd plugins/baselithcore_agents_platform/ui
npm install && npm run build      # emits ui/dist (only built output ships)
```

Served at `/api/baselithcore_agents_platform/ui/`. Until built, the route degrades to
a placeholder rather than a 500.

## Tests

```bash
python -m pytest plugins/baselithcore_agents_platform/tests/ -p no:cacheprovider
```

All LLM access is mocked; tests assert scope enforcement, grounding, blueprint
fallback, and fence-stripping.
