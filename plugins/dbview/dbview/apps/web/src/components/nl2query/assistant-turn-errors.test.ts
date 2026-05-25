import { describe, expect, it } from 'vitest';
import { classifyError } from './assistant-turn-errors.js';

describe('classifyError', () => {
  it('detects Ollama unreachable when provider is ollama and message hints 502', () => {
    const r = classifyError('502 cannot reach ollama', 'ollama');
    expect(r.title).toMatch(/Ollama/i);
    // Endpoint is env-configured (not user-editable) → no settings link;
    // unreachable also can't be fixed by switching model.
    expect(r.showModelPicker).toBe(false);
  });

  it('offers model picker when ollama reports model not found', () => {
    const r = classifyError(
      "ollama (qwen2.5-coder:7b) returned 404: model 'qwen2.5-coder:7b' not found",
      'ollama'
    );
    expect(r.title).toMatch(/Model not pulled/i);
    expect(r.showModelPicker).toBe(true);
  });

  it('flags generic LLM provider failure when not ollama', () => {
    const r = classifyError('fetch failed at provider', 'openai');
    expect(r.title).toMatch(/openai/i);
    expect(r.showModelPicker).toBe(false);
  });

  it('detects rate-limit', () => {
    const r = classifyError('Got 429 rate_limited', 'openai');
    expect(r.title).toMatch(/rate limit/i);
  });

  it('classifies unsafe SQL', () => {
    const r = classifyError('Rejected by safety: unsafe_sql', 'openai');
    expect(r.title).toMatch(/safety/i);
  });

  it('does not mark unsafe when message is actually a parse error', () => {
    const r = classifyError('SQL parse error: unexpected', 'openai');
    expect(r.title).toMatch(/unparsable/i);
  });

  it('classifies schema mismatch', () => {
    const r = classifyError('schema_mismatch: column not in schema', 'openai');
    expect(r.title).toMatch(/schema mismatch/i);
  });

  it('classifies validation_error', () => {
    const r = classifyError('validation_error: invalid request body', 'openai');
    expect(r.title).toMatch(/invalid request/i);
  });

  it('falls back to generic Generation failed', () => {
    const r = classifyError('something else entirely', 'openai');
    expect(r.title).toBe('Generation failed');
    expect(r.hint).toBeNull();
  });
});
