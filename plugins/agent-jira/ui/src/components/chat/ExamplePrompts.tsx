import { Sparkles, ArrowRight, FileText, AlertTriangle, Workflow } from 'lucide-react';

type ExamplePromptsProps = {
  prompts: string[];
  onSelect: (prompt: string) => void;
};

const getPromptIcon = (text: string) => {
  const t = text.toLowerCase();
  if (t.includes('file') || t.includes('document')) return <FileText size={18} />;
  if (t.includes('rischi') || t.includes('problemi')) return <AlertTriangle size={18} />;
  if (t.includes('plan') || t.includes('progetto') || t.includes('onboarding'))
    return <Workflow size={18} />;
  return <Sparkles size={18} />;
};

const ExamplePrompts = ({ prompts, onSelect }: ExamplePromptsProps) => (
  <div className="example-prompts-grid">
    {prompts.map((prompt) => (
      <button key={prompt} type="button" className="prompt-card" onClick={() => onSelect(prompt)}>
        <div className="prompt-icon-wrapper">{getPromptIcon(prompt)}</div>
        <h3>{prompt}</h3>
        <div className="card-action">
          Chiedi ora <ArrowRight size={10} />
        </div>
      </button>
    ))}
  </div>
);

export default ExamplePrompts;
