import { test, expect, installApiStubs } from './fixtures';

/**
 * Visual snapshot suite for the key surfaces. Each test mocks the backend
 * via Playwright's `page.route` so the suite can run offline.
 *
 * Run locally:
 *   npx playwright install chromium
 *   npx playwright test
 *
 * Update baselines:
 *   npx playwright test --update-snapshots
 */

const STABLE_THEME = async (page: import('@playwright/test').Page) => {
  // Force light theme so snapshots stay deterministic regardless of
  // the test runner host's dark-mode preference.
  await page.addInitScript(() => {
    document.documentElement.classList.add('light');
  });
};

test.describe('chat surfaces', () => {
  test.beforeEach(async ({ page }) => {
    await STABLE_THEME(page);
  });

  test('empty state — desktop', async ({ stubbedPage: page }) => {
    await page.goto('/');
    await expect(page.getByText('Knowledge Base Demo')).toBeVisible();
    await expect(page.locator('h1')).toContainText('Cosa vuoi sapere');
    await expect(page).toHaveScreenshot('empty-state-desktop.png', { fullPage: true });
  });

  test('command palette open', async ({ stubbedPage: page }) => {
    await page.goto('/');
    await page.locator('h1').waitFor();
    await page.keyboard.press('Meta+/');
    await expect(page.getByRole('dialog', { name: /tavolozza comandi/i })).toBeVisible();
    await expect(page).toHaveScreenshot('command-palette.png');
  });

  test('settings modal', async ({ stubbedPage: page }) => {
    await page.goto('/');
    await page.locator('h1').waitFor();
    await page.keyboard.press('Meta+,');
    await expect(page.getByRole('dialog', { name: 'Impostazioni' })).toBeVisible();
    await expect(page).toHaveScreenshot('settings-modal.png');
  });

  test('help modal', async ({ stubbedPage: page }) => {
    await page.goto('/');
    await page.locator('h1').waitFor();
    await page.keyboard.press('?');
    await expect(page.getByRole('dialog', { name: /scorciatoie/i })).toBeVisible();
    await expect(page).toHaveScreenshot('help-modal.png');
  });

  test('upload modal — empty', async ({ stubbedPage: page }) => {
    await page.goto('/');
    await page.locator('h1').waitFor();
    await page.keyboard.press('Meta+u');
    const dialog = page.getByRole('dialog', { name: 'Carica documento' });
    await expect(dialog).toBeVisible();
    await expect(page).toHaveScreenshot('upload-modal-empty.png');
  });
});

test.describe('first-run setup', () => {
  test.beforeEach(async ({ page }) => {
    await STABLE_THEME(page);
    // Override the default branding to enter setup mode.
    await installApiStubs(page, { branding: { setup_mode: true } });
  });

  test('wizard screen — desktop', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('dialog', { name: /setup wizard/i })).toBeVisible();
    await expect(page.getByText('Configura la tua knowledge base')).toBeVisible();
    await expect(page).toHaveScreenshot('wizard-screen.png', { fullPage: true });
  });

  test('wizard screen — mobile', async ({ page }) => {
    test.skip(test.info().project.name !== 'mobile', 'mobile-only viewport');
    await page.goto('/');
    await expect(page.getByText('Configurazione wiki')).toBeVisible();
    await expect(page).toHaveScreenshot('wizard-screen-mobile.png', { fullPage: true });
  });
});

test.describe('responsive', () => {
  test.beforeEach(async ({ page }) => {
    await STABLE_THEME(page);
  });

  test('empty state — mobile', async ({ stubbedPage: page }) => {
    test.skip(test.info().project.name !== 'mobile', 'mobile-only viewport');
    await page.goto('/');
    await expect(page.locator('h1')).toBeVisible();
    await expect(page).toHaveScreenshot('empty-state-mobile.png', { fullPage: true });
  });

  test('upload modal — mobile', async ({ stubbedPage: page }) => {
    test.skip(test.info().project.name !== 'mobile', 'mobile-only viewport');
    await page.goto('/');
    await page.locator('h1').waitFor();
    await page.keyboard.press('Meta+u');
    await expect(page.getByRole('dialog', { name: 'Carica documento' })).toBeVisible();
    await expect(page).toHaveScreenshot('upload-modal-mobile.png');
  });
});
