import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Providers } from '@/components/providers';
import { THEME_INIT_SCRIPT } from '@/lib/theme';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const jbm = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'doCheck — Compliance Checker',
  description: 'Local-first enterprise document compliance checker',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it" className={`${inter.variable} ${jbm.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} suppressHydrationWarning />
      </head>
      <body className="bg-bg-canvas text-text-primary font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
