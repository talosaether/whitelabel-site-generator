const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

// These assert structure and behaviour, not copy, so branding the site does not mean
// rewriting them. The header links and the site name are read from the page itself.
const PAGES = ['/', '/services', '/about', '/contact'];
const mainNav = page => page.getByRole('navigation', { name: 'Main navigation' });

async function siteName(page) {
  // "<label> · <site name>": whatever follows the separator is the name.
  return (await page.title()).split(' · ').slice(1).join(' · ');
}

test('boosted navigation, head metadata and history', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  const name = await siteName(page);
  expect(name.length).toBeGreaterThan(0);
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expect(page.locator('.brand-mark')).toBeVisible();
  const links = await mainNav(page).getByRole('link').allInnerTexts();
  expect(links.length).toBeGreaterThanOrEqual(1);
  expect(links.length).toBeLessThanOrEqual(4);
  // A marker on the live document proves later navigation never reloads the page.
  await page.evaluate(() => { window.testDocumentMarker = true; });
  for (const link of links) {
    await mainNav(page).getByRole('link', { name: link, exact: true }).click();
    await expect(page).toHaveTitle(new RegExp(` · ${name}$`));
    await expect(mainNav(page).locator('[aria-current=page]')).toHaveText(link);
    expect(await page.evaluate(() => window.testDocumentMarker)).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    // Boosted swaps replace the body only, so the script keeps head metadata in sync.
    const head = await page.evaluate(() => ({
      description: document.querySelector('meta[name=description]').content,
      canonical: document.querySelector('link[rel=canonical]').href,
      mainDescription: document.querySelector('main').dataset.description,
      mainCanonical: document.querySelector('main').dataset.canonical,
    }));
    expect(head.description).toBe(head.mainDescription);
    expect(head.description.length).toBeGreaterThan(40);
    expect(head.canonical).toBe(head.mainCanonical);
    expect(head.canonical.startsWith('https://')).toBe(true);
  }
  const lastTitle = await page.title();
  await page.getByRole('link', { name: `${name} home` }).click();
  await expect(page).toHaveTitle(`Home · ${name}`);
  await page.goBack();
  await expect(page).toHaveTitle(lastTitle);
  await page.goForward();
  await expect(page).toHaveTitle(`Home · ${name}`);
  await page.screenshot({ path: `../../recovery/${test.info().project.name}.png`, fullPage: true });
  expect(errors).toEqual([]);
});

test('every page passes automated accessibility checks', async ({ page }) => {
  for (const path of PAGES) {
    await page.goto(path);
    const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
    expect(violations.map(violation => `${path} ${violation.id}`)).toEqual([]);
  }
});

test('keyboard skip link', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/#main$/);
});

test('the navigation and the footer fit the viewport', async ({ page }) => {
  await page.goto('/services');
  const boxes = locator => locator.evaluateAll(els => els.map(el => {
    const box = el.getBoundingClientRect();
    return { x: Math.round(box.x), y: Math.round(box.y), width: Math.round(box.width), height: Math.round(box.height) };
  }));

  // The header links hold one row at every width, including a 320px phone, which is
  // the whole reason the navigation is at most four links.
  const links = await boxes(page.locator('.site-nav a'));
  expect(links.length).toBeGreaterThanOrEqual(1);
  expect([...new Set(links.map(link => link.y))]).toHaveLength(1);
  expect(Math.min(...links.map(link => link.height))).toBeGreaterThanOrEqual(44);
  await page.setViewportSize({ width: 320, height: 720 });
  expect([...new Set((await boxes(page.locator('.site-nav a'))).map(link => link.y))]).toHaveLength(1);
  await page.setViewportSize(test.info().project.use.viewport);

  // Nothing is hidden: the footer lists every page.
  await expect(page.getByRole('navigation', { name: 'All pages' }).getByRole('link')).toHaveCount(PAGES.length);

  // The footer's contact buttons sit on one row, share the width evenly, and are tappable.
  const buttons = await boxes(page.locator('.footer-contact a'));
  expect(buttons.length).toBeGreaterThanOrEqual(1);
  expect([...new Set(buttons.map(button => button.y))]).toHaveLength(1);
  expect(Math.max(...buttons.map(b => b.width)) - Math.min(...buttons.map(b => b.width))).toBeLessThanOrEqual(1);
  expect(Math.min(...buttons.map(button => button.height))).toBeGreaterThanOrEqual(44);

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
