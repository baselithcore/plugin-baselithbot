import React, { useState } from 'react';
import { Settings, X, Loader2, Zap } from 'lucide-react';
import { CATEGORY_ICONS } from './constants';
import './PentestTab.css';

interface GenerateOptionsState {
  name: string;
  categories: string[];
  limit: number;
  honeypotId: string;
}

interface GeneratePlaybookModalProps {
  onClose: () => void;
  onGenerate: (options: GenerateOptionsState) => Promise<void>;
  isGenerating: boolean;
}

export const GeneratePlaybookModal: React.FC<GeneratePlaybookModalProps> = ({
  onClose,
  onGenerate,
  isGenerating,
}) => {
  const [generateOptions, setGenerateOptions] = useState<GenerateOptionsState>({
    name: '',
    categories: ['prompt_injection', 'jailbreak'],
    limit: 100,
    honeypotId: '',
  });

  const toggleCategory = (cat: string) => {
    setGenerateOptions((prev) => ({
      ...prev,
      categories: prev.categories.includes(cat)
        ? prev.categories.filter((c) => c !== cat)
        : [...prev.categories, cat],
    }));
  };

  return (
    <div className="hp-modal-overlay" onClick={onClose}>
      <div className="hp-modal hp-modal--generate" onClick={(e) => e.stopPropagation()}>
        <div className="hp-modal-header">
          <h3>
            <Settings size={18} /> Generate Playbook
          </h3>
          <button className="hp-modal-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <div className="hp-modal-body">
          <div className="hp-form-group">
            <label>Playbook Name</label>
            <input
              type="text"
              placeholder={`Threat Playbook ${new Date().toLocaleDateString()}`}
              value={generateOptions.name}
              onChange={(e) => setGenerateOptions((prev) => ({ ...prev, name: e.target.value }))}
              className="hp-input"
            />
          </div>
          <div className="hp-form-group">
            <label>Attack Categories</label>
            <div className="hp-category-grid">
              {Object.entries(CATEGORY_ICONS).map(([cat, info]) => (
                <button
                  key={cat}
                  className={`hp-category-btn ${generateOptions.categories.includes(cat) ? 'active' : ''}`}
                  onClick={() => toggleCategory(cat)}
                  style={{ '--cat-color': info.color } as React.CSSProperties}
                >
                  {info.icon} {info.label}
                </button>
              ))}
            </div>
          </div>
          <div className="hp-form-group">
            <label>Max Events to Analyze</label>
            <input
              type="range"
              min="10"
              max="500"
              step="10"
              value={generateOptions.limit}
              onChange={(e) =>
                setGenerateOptions((prev) => ({ ...prev, limit: Number(e.target.value) }))
              }
              className="hp-range"
            />
            <span className="hp-range-value">{generateOptions.limit} events</span>
          </div>
        </div>
        <div className="hp-modal-footer">
          <button className="hp-btn hp-btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="hp-btn hp-btn-primary hp-btn-glow"
            onClick={() => onGenerate(generateOptions)}
            disabled={isGenerating || generateOptions.categories.length === 0}
          >
            {isGenerating ? <Loader2 size={14} className="spin" /> : <Zap size={14} />}
            Generate Playbook
          </button>
        </div>
      </div>
    </div>
  );
};

export type { GenerateOptionsState };
