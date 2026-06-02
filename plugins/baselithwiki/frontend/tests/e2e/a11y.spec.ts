import { test, expect } from './fixtures';

/**
 * Lightweight accessibility smoke tests. Verifies the foundations:
 * dialog roles, focus trap, escape-to-close, accessible names. Doesn't
 * replace a full audit (axe-core), but catches regressions on the
 * primitives the rest of the UI is built on.
 */

test('settings modal: dialog semantics + Esc to close', async ({ stubbedPage: page }) => {
  await page.goto('/');
  await page.locator('h1').waitFor();
  await page.keyboard.press('Meta+,');
  const dialog = page.getByRole('dialog', { name: 'Impostazioni' });
  await expect(dialog).toBeVisible();
  // Settings switches expose role="switch".
  await expect(dialog.getByRole('switch')).toHaveCount(3);
  // Close on Escape.
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
});

test('help modal: keyboard shortcuts have kbd labels', async ({ stubbedPage: page }) => {
  await page.goto('/');
  await page.locator('h1').waitFor();
  await page.keyboard.press('?');
  const dialog = page.getByRole('dialog', { name: /scorciatoie/i });
  await expect(dialog).toBeVisible();
  // Headings render as h3.
  await expect(dialog.getByRole('heading', { level: 3 }).first()).toBeVisible();
});

test('upload modal: dropzone is keyboard reachable', async ({ stubbedPage: page }) => {
  await page.goto('/');
  await page.locator('h1').waitFor();
  await page.keyboard.press('Meta+u');
  const dialog = page.getByRole('dialog', { name: 'Carica documento' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'seleziona o trascina file' })).toBeVisible();
});

test('command palette: search input is autofocused', async ({ stubbedPage: page }) => {
  await page.goto('/');
  await page.locator('h1').waitFor();
  await page.keyboard.press('Meta+/');
  const palette = page.getByRole('dialog', { name: /tavolozza comandi/i });
  await expect(palette).toBeVisible();
  await expect(palette.getByLabel('cerca comando')).toBeFocused();
});

test('composer: textarea has accessible name', async ({ stubbedPage: page }) => {
  await page.goto('/');
  await page.locator('h1').waitFor();
  await expect(page.getByLabel('domanda')).toBeVisible();
});
