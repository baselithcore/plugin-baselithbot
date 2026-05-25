import { test, expect } from '@playwright/test';

test.describe('Agent Jira Smoke Test', () => {
  test('should load the home page and show the chat input', async ({ page }) => {
    await page.goto('/');

    // Check for the main title or a distinctive element
    await expect(page.locator('h1')).toBeVisible();

    // Check if the chat input is present
    const chatInput = page.getByPlaceholder(/Chiedi qualcosa/i);
    await expect(chatInput).toBeVisible();
  });

  test('should navigate to the knowledge base tab', async ({ page }) => {
    await page.goto('/');

    // Click on the KB tab
    await page.click('button:has-text("Knowledge Base")');

    // Check if the KB view is active (e.g. by checking for a search input or a specific heading)
    await expect(page.locator('input[placeholder*="cerca"]')).toBeVisible();
  });
});
