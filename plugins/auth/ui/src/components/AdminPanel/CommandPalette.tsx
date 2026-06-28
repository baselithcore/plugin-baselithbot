/**
 * ⌘K command palette — jump to any console section or run a quick action
 * (toggle theme, open account, sign out). Fully keyboard-driven.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, CornerDownLeft } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { NAV_ITEMS } from './nav';
import type { TabType } from '../../types';

export interface PaletteAction {
  id: string;
  label: string;
  icon: LucideIcon;
  run: () => void;
}

interface Row {
  key: string;
  label: string;
  section: string;
  Icon: LucideIcon;
  run: () => void;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onSelectTab: (tab: TabType) => void;
  actions: PaletteAction[];
}

const CommandPalette = ({ open, onClose, onSelectTab, actions }: CommandPaletteProps) => {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const rows = useMemo<Row[]>(() => {
    const nav: Row[] = NAV_ITEMS.map((it) => ({
      key: `nav:${it.id}`,
      label: t(it.labelKey),
      section: t('command.section.navigate'),
      Icon: it.icon,
      run: () => onSelectTab(it.id),
    }));
    const acts: Row[] = actions.map((a) => ({
      key: `act:${a.id}`,
      label: a.label,
      section: t('command.section.actions'),
      Icon: a.icon,
      run: a.run,
    }));
    const all = [...nav, ...acts];
    const q = query.trim().toLowerCase();
    return q ? all.filter((r) => r.label.toLowerCase().includes(q)) : all;
  }, [query, actions, onSelectTab, t]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setCursor(0);
      const id = window.setTimeout(() => inputRef.current?.focus(), 0);
      return () => window.clearTimeout(id);
    }
  }, [open]);

  useEffect(() => {
    setCursor((c) => Math.min(c, Math.max(rows.length - 1, 0)));
  }, [rows.length]);

  if (!open) return null;

  const runAt = (idx: number) => {
    const row = rows[idx];
    if (!row) return;
    row.run();
    onClose();
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setCursor((c) => (rows.length ? (c + 1) % rows.length : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setCursor((c) => (rows.length ? (c - 1 + rows.length) % rows.length : 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      runAt(cursor);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  let lastSection = '';

  return (
    <div className="cmdk-overlay" onMouseDown={onClose}>
      <div
        className="cmdk"
        role="dialog"
        aria-modal="true"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="cmdk-input">
          <Search size={17} />
          <input
            ref={inputRef}
            value={query}
            placeholder={t('command.placeholder')}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            aria-label={t('command.placeholder')}
          />
          <kbd className="tb-kbd">ESC</kbd>
        </div>
        <div className="cmdk-list">
          {rows.length === 0 && <div className="cmdk-empty">{t('command.noResults')}</div>}
          {rows.map((row, idx) => {
            const header = row.section !== lastSection ? row.section : null;
            lastSection = row.section;
            const Icon = row.Icon;
            return (
              <div key={row.key}>
                {header && <div className="cmdk-section">{header}</div>}
                <button
                  type="button"
                  className={`cmdk-row ${idx === cursor ? 'active' : ''}`}
                  onMouseEnter={() => setCursor(idx)}
                  onClick={() => runAt(idx)}
                >
                  <Icon size={16} className="cmdk-row-ico" />
                  <span className="cmdk-row-label">{row.label}</span>
                  {idx === cursor && <CornerDownLeft size={14} className="cmdk-row-enter" />}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default CommandPalette;
