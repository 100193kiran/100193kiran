import { test, expect } from '@playwright/test';

const baseURL = process.env.STORYBOOK_URL || 'http://127.0.0.1:6006';

test('button story visual baseline', async ({ page }) => {
  await page.goto(`${baseURL}/?path=/story/design-system-button--primary`);
  await page.setViewportSize({ width: 1100, height: 700 });
  await expect(page).toHaveScreenshot('button-primary.png', { maxDiffPixelRatio: 0.02 });
});
