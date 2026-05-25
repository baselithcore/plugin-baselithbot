import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

interface ThemeColors {
  primary: string;
  primaryHover: string;
  background: string;
  panel: string;
  sidebar: string;
  textPrimary: string;
  textSecondary: string;
  textSidebar: string;
  borderColor: string;
  inputBg: string;
  userBubble: string;
  userBubbleText: string;
  assistantBubble: string;
  assistantBubbleText: string;
  navHoverBg: string;
  navActiveBg: string;
  navActiveColor: string;
  chainColor: string;
  logoUrl?: string;
  loginLogoUrl?: string;
  uploadHoverColor?: string;
  uploadHoverBg?: string;
  tableSelectBg?: string;
  settingsNavActiveBg?: string;
  settingsNavColor?: string;
  settingsNavActiveColor?: string;
  settingsIconColor?: string;
  statusError?: string;
  statusWarning?: string;
}

interface BrandingConfig {
  companyName: string;
  logoUrl: string;
  faviconUrl: string;
  light: ThemeColors;
  dark: ThemeColors;
}

interface BrandingContextType {
  config: BrandingConfig | null;
  logoUrl: string;
  loginLogoUrl: string;
}

const BrandingContext = createContext<BrandingContextType>({
  config: null,
  logoUrl: '',
  loginLogoUrl: '',
});

export const useBranding = () => useContext(BrandingContext);

export const BrandingProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [config, setConfig] = useState<BrandingConfig | null>(null);
  const [logoUrl, setLogoUrl] = useState<string>('');
  const [loginLogoUrl, setLoginLogoUrl] = useState<string>('');

  useEffect(() => {
    fetch('/branding.json')
      .then((res) => res.json())
      .then((data: BrandingConfig) => {
        setConfig(data);

        // Favicon loading
        const faviconUrl = data.faviconUrl || '/logo_placeholder.svg';
        const existingLinks = document.querySelectorAll("link[rel~='icon']");
        existingLinks.forEach((l) => l.parentNode?.removeChild(l));

        const link: HTMLLinkElement = document.createElement('link');
        link.rel = 'icon';
        link.href = faviconUrl;
        document.getElementsByTagName('head')[0].appendChild(link);

        // Sync page title
        if (data.companyName) {
          document.title = data.companyName;
        }

        // Set initial CSS variables
        applyTheme(data, isDarkMode());
      })
      .catch((err) => console.error('Failed to load branding config:', err));
  }, []);

  const isDarkMode = () => {
    const root = document.documentElement;
    if (root.classList.contains('dark')) return true;
    if (root.classList.contains('light')) return false;
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  };

  // Observer for theme changes
  useEffect(() => {
    if (!config) return;

    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (
          mutation.type === 'attributes' &&
          (mutation.attributeName === 'class' || mutation.attributeName === 'data-tenant-theme')
        ) {
          applyTheme(config, isDarkMode());
        }
      });
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class', 'data-tenant-theme'],
    });

    // Also listen for system theme changes if we are in 'auto' mode
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleMediaChange = () => {
      if (
        !document.documentElement.classList.contains('dark') &&
        !document.documentElement.classList.contains('light')
      ) {
        applyTheme(config, isDarkMode());
      }
    };
    mediaQuery.addEventListener('change', handleMediaChange);

    return () => {
      observer.disconnect();
      mediaQuery.removeEventListener('change', handleMediaChange);
    };
  }, [config]);

  const applyTheme = (conf: BrandingConfig, isDark: boolean) => {
    const palette = isDark ? conf.dark : conf.light;
    const root = document.documentElement;

    setLogoUrl(palette.logoUrl || conf.logoUrl || '');
    setLoginLogoUrl(palette.loginLogoUrl || conf.logoUrl || '');

    // Brand colors. NOTE: per-tenant overrides (sidebar bg / brand /
    // accent) are applied by `DomainContext.applyTenantTheme` and live
    // as inline `style` properties on <html>, so they win over the
    // assignments below thanks to CSS custom-property cascade — the
    // last setProperty call (DomainContext) overrides BrandingContext.
    root.style.setProperty('--color-brand', palette.primary);
    root.style.setProperty('--color-brand-strong', palette.primaryHover);
    root.style.setProperty('--color-brand-contrast', isDark ? palette.primary : palette.sidebar);

    const brandBase = palette.primary.startsWith('#') ? palette.primary : '#003b5c';
    root.style.setProperty('--color-brand-soft', `${brandBase}1a`);
    root.style.setProperty('--color-brand-ring', `${brandBase}47`);
    root.style.setProperty('--color-sidebar-bg', palette.sidebar);

    root.style.setProperty('--color-sidebar-bg', palette.sidebar);
    root.style.setProperty('--color-sidebar-text', palette.textSidebar || '#ffffff');
    root.style.setProperty('--color-sidebar-hover', palette.navHoverBg || 'rgba(255,255,255,0.1)');
    root.style.setProperty(
      '--color-sidebar-active-bg',
      palette.navActiveBg || 'rgba(255,255,255,0.2)'
    );
    root.style.setProperty(
      '--color-sidebar-active-text',
      palette.navActiveColor || palette.primary
    );

    // Core surfaces
    root.style.setProperty('--color-canvas', palette.background);
    root.style.setProperty('--color-canvas-raised', palette.panel);
    root.style.setProperty('--color-surface', palette.panel);

    if (palette.navHoverBg && !isDark) {
      root.style.setProperty('--color-surface-hover', palette.navHoverBg);
    } else {
      // Fallback or dark mode logic
      root.style.setProperty(
        '--color-surface-hover',
        isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'
      );
    }

    // Neutral ink
    root.style.setProperty('--color-ink', palette.textPrimary);
    root.style.setProperty('--color-ink-muted', palette.textSecondary);

    // Borders
    root.style.setProperty('--color-border', palette.borderColor);

    // Semantic
    if (palette.statusError) root.style.setProperty('--color-danger', palette.statusError);
    if (palette.statusWarning) root.style.setProperty('--color-warning', palette.statusWarning);
  };

  const value = useMemo<BrandingContextType>(
    () => ({
      config,
      logoUrl: logoUrl || config?.logoUrl || '',
      loginLogoUrl: loginLogoUrl || logoUrl || config?.logoUrl || '',
    }),
    [config, logoUrl, loginLogoUrl]
  );

  return <BrandingContext.Provider value={value}>{children}</BrandingContext.Provider>;
};
