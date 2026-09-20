import { test, expect } from 'playwright/test';
test.describe('Reclaim screenshots', () => {
  test('homepage', async ({ page }) => {
    await page.goto('https://wms.getvoroa.com/');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'tests/screenshots/homepage.png', fullPage: true });
  });
  test('login dashboard', async ({ page }) => {
    await page.goto('https://wms.getvoroa.com/');
    await page.click('text=Sign in');
    await page.fill('#username', 'admin');
    await page.fill('#password', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'tests/screenshots/dashboard.png', fullPage: true });
  });
});
