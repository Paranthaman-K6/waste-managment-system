import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  timeout: 30000,
  use: { baseURL: 'https://wms.getvoroa.com', headless: true },
  projects: [{ name: 'desktop', use: { ...devices['Desktop Chrome'] } }],
});
