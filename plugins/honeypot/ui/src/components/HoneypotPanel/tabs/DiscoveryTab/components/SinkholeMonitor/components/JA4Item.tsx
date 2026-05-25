/**
 * JA4Item - Display a JA4 fingerprint with classification
 */

import { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface JA4ItemProps {
  fingerprint: string;
  count: number;
}

export function JA4Item({ fingerprint, count }: JA4ItemProps) {
  const [copied, setCopied] = useState(false);
  const classification = count > 500 ? 'threat' : count > 100 ? 'suspicious' : 'normal';

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    await navigator.clipboard.writeText(fingerprint);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="ja4-item">
      <span className="ja4-fingerprint" title={fingerprint}>
        {fingerprint}
      </span>
      <div className="ja4-meta">
        <button className="ja4-copy-btn" onClick={handleCopy} title="Copy fingerprint">
          {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
        <span className="ja4-count">{count} hits</span>
        <span className={`ja4-badge ${classification}`}>
          {classification === 'threat'
            ? 'Threat'
            : classification === 'suspicious'
              ? 'Suspicious'
              : 'Normal'}
        </span>
      </div>
    </div>
  );
}
