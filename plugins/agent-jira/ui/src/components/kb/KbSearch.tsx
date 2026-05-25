import { useState } from 'react';
import { Search, FileText } from 'lucide-react';
import { KbDocumentEntry } from '../../types';

interface KbSearchProps {
  query: string;
  setQuery: (q: string) => void;
  suggestions: KbDocumentEntry[];
}

export const KbSearch = ({ query, setQuery, suggestions }: KbSearchProps) => {
  const [suggestOpen, setSuggestOpen] = useState(false);

  return (
    <div className="kb-search-container">
      <div className="kb-search-input-wrapper">
        <Search className="kb-search-icon" size={18} />
        <input
          className="kb-search-input"
          placeholder="Cerca contenuti o path..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setSuggestOpen(true)}
          onBlur={() => setTimeout(() => setSuggestOpen(false), 200)}
        />
      </div>

      {suggestOpen && suggestions.length > 0 && query.trim().length >= 2 && (
        <div className="kb-suggestions">
          <div className="kb-suggestions-header">Risultati Suggeriti</div>
          {suggestions.map((doc) => {
            const fileName = doc.path.split('/').pop() || doc.path;
            const displayTitle = doc.label || fileName.replace(/\.[^.]+$/, '');

            return (
              <button
                key={doc.path}
                type="button"
                className="kb-suggestion-item"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  setQuery(displayTitle);
                  setSuggestOpen(false);
                }}
              >
                <div className="kb-suggestion-icon">
                  <FileText size={14} />
                </div>
                <div className="kb-suggestion-content">
                  <span className="kb-suggestion-label">{displayTitle}</span>
                  <span className="kb-suggestion-path">{fileName}</span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
