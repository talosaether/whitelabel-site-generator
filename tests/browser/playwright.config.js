const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
  testDir: '.',
  workers: 1,
  outputDir: '../../recovery/browser-results',
  use: { baseURL: process.env.BASE_URL || 'https://example.com', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1280, height: 800 } } },
    { name: 'mobile', use: { viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true } },
  ],
});
