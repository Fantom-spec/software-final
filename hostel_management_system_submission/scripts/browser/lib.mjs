import chromium from '@sparticuz/chromium';
import puppeteer from 'puppeteer-core';

export async function launch() {
  const exe = process.env.CHROME_PATH || await chromium.executablePath();
  return puppeteer.launch({executablePath: exe, args: [...chromium.args, '--no-sandbox'], headless: 'shell'});
}

export async function login(page, base, email, password) {
  await page.goto(base + '/auth/login', {waitUntil: 'networkidle0'});
  await page.type('input[name=email]', email);
  await page.type('input[name=password]', password);
  await Promise.all([page.waitForNavigation({waitUntil: 'networkidle0'}), page.click('button[type=submit]')]);
}
