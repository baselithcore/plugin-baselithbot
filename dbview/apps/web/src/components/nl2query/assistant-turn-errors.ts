export interface ErrorHint {
  title: string;
  hint: string | null;
  /**
   * When true the UI surfaces a "Pick another model" action that opens the
   * model picker rather than a removed settings dialog. Ollama endpoint is
   * deployment-only (env-configured) and intentionally not editable from UI.
   */
  showModelPicker: boolean;
}

export function classifyError(msg: string, provider?: string): ErrorHint {
  const is502 =
    /502|llm_provider_error|cannot reach|fetch failed|ECONNREFUSED|model.*not found/i.test(msg);
  const isModelMissing = /model.*not found|no such model/i.test(msg);
  const isRateLimit = /rate_limited|429/i.test(msg);
  const isParseError = /SQL parse error|unparsable|unexpected '/i.test(msg);
  const isUnsafe = /unsafe_sql|safety/i.test(msg) && !isParseError;
  const isValidation = /validation_error|invalid request/i.test(msg) && !isParseError;
  const isSchemaMismatch = /schema_mismatch|not in schema/i.test(msg);

  if (is502 && provider === 'ollama') {
    return {
      title: isModelMissing ? 'Model not pulled on Ollama' : 'Ollama unreachable',
      hint: isModelMissing
        ? 'Pull the model on the Ollama host (e.g. `ollama pull codellama:7b`) or pick another installed coding model.'
        : 'Ensure `ollama serve` is reachable from the API. The endpoint is configured via `OLLAMA_BASE_URL` in the API environment.',
      showModelPicker: isModelMissing,
    };
  }
  if (is502) {
    return {
      title: `${provider ?? 'LLM'} provider failed`,
      hint: 'Check API key and network connectivity.',
      showModelPicker: false,
    };
  }
  if (isRateLimit) {
    return {
      title: 'Rate limit reached',
      hint: 'Limit is 20 requests / minute. Wait a moment and try again.',
      showModelPicker: false,
    };
  }
  if (isUnsafe) {
    return {
      title: 'Query rejected by safety validator',
      hint: 'The model produced unsafe SQL. Try rephrasing the question or pick a different model.',
      showModelPicker: true,
    };
  }
  if (isSchemaMismatch) {
    return {
      title: 'Schema mismatch',
      hint: 'Model referenced tables/columns absent from the schema. Try a more specific prompt.',
      showModelPicker: false,
    };
  }
  if (isParseError) {
    return {
      title: 'Model produced unparsable SQL',
      hint: 'Try a more specific prompt, switch to a stronger model, or rephrase the question.',
      showModelPicker: true,
    };
  }
  if (isValidation) {
    return {
      title: 'Invalid request',
      hint: 'The request body did not validate. Check the prompt and selected connection.',
      showModelPicker: false,
    };
  }
  return { title: 'Generation failed', hint: null, showModelPicker: false };
}
