import { ReactNode, useEffect, useRef, useState } from 'react';
import { ChevronDown, LogOut, Moon, Settings as SettingsIcon, Sun } from 'lucide-react';
import type { AuthUser } from '../types';

interface HeroProps {
  jiraManual: boolean;
  analysisEnabled: boolean;
  error: string | null;
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
  user?: AuthUser | null;
  onLogout?: () => void;
  onOpenSettings?: () => void;
  children?: ReactNode;
}

const Hero = ({
  error,
  theme,
  onToggleTheme,
  user,
  onLogout,
  onOpenSettings,
  children,
}: HeroProps) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [menuOpen]);

  return (
    <header className="hero">
      <div className="hero-brand">
        <p className="eyebrow-mini">agent-jira</p>
        <h1>Jira AI Console</h1>
        {error && <div className="badge badge-warn">Backend down: {error}</div>}
      </div>

      <div className="hero-center">{children}</div>

      <div className="hero-status">
        {user && (
          <div className="user-menu" ref={menuRef}>
            <button
              type="button"
              className="user-trigger"
              onClick={() => setMenuOpen((v) => !v)}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
            >
              <span className="user-avatar" aria-hidden="true">
                {(user.display_name || user.email || '?').trim().charAt(0).toUpperCase()}
              </span>
              <span className="user-name">{user.display_name || user.email}</span>
              <ChevronDown size={13} className={`user-chevron ${menuOpen ? 'is-open' : ''}`} />
            </button>
            {menuOpen && (
              <div className="user-dropdown" role="menu">
                <div className="user-dropdown-header">
                  <span className="user-dropdown-name">{user.display_name || user.email}</span>
                  {user.display_name && <span className="user-dropdown-email">{user.email}</span>}
                  <div className="user-dropdown-rows">
                    {user.role && (
                      <div className="user-dropdown-row">
                        <span className="user-dropdown-row-key">Ruolo</span>
                        <span className="user-dropdown-row-val">
                          {user.role === 'admin' ? 'Admin' : 'Proprietario'}
                        </span>
                      </div>
                    )}
                    {user.tenant_id && (
                      <div className="user-dropdown-row">
                        <span className="user-dropdown-row-key">Tenant</span>
                        <span
                          className="user-dropdown-row-val user-dropdown-row-val--mono"
                          title={user.tenant_id}
                        >
                          {user.tenant_id.slice(0, 8)}…
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                {onOpenSettings && (
                  <button
                    type="button"
                    className="user-dropdown-item"
                    role="menuitem"
                    onClick={() => {
                      setMenuOpen(false);
                      onOpenSettings();
                    }}
                  >
                    <SettingsIcon size={14} />
                    <span>Impostazioni</span>
                  </button>
                )}
                {onLogout && (
                  <>
                    <div className="user-dropdown-divider" />
                    <button
                      type="button"
                      className="user-dropdown-item user-dropdown-item--danger"
                      role="menuitem"
                      onClick={() => {
                        setMenuOpen(false);
                        onLogout();
                      }}
                    >
                      <LogOut size={14} />
                      <span>Esci</span>
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        )}
        <button
          className="theme-toggle"
          onClick={onToggleTheme}
          title={`Passa al tema ${theme === 'dark' ? 'chiaro' : 'scuro'}`}
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </div>
    </header>
  );
};

export default Hero;
