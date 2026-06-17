interface InstructionsFieldProps {
  instructions: string;
  setInstructions: (v: string) => void;
}

export function InstructionsField({ instructions, setInstructions }: InstructionsFieldProps) {
  return (
    <div className="form-row">
      <label htmlFor="skill-author-instructions">Instructions (SKILL.md body)</label>
      <textarea
        id="skill-author-instructions"
        className="input"
        rows={14}
        value={instructions}
        onChange={(event) => setInstructions(event.target.value)}
        style={{ fontFamily: 'var(--font-mono, ui-monospace, monospace)', minHeight: 240 }}
        maxLength={32_000}
      />
      <div className="info-block">
        Markdown is injected into the agent prompt when the skill activates. Lead with "when to
        use", then steps, then an output contract.
      </div>
    </div>
  );
}
