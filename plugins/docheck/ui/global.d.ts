import type { Messages } from '@/lib/i18n/messages';

declare module 'next-intl' {
  interface AppConfig {
    Messages: Messages;
  }
}
