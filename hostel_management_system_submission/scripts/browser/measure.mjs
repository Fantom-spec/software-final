// Usage: node measure.mjs <baseUrl> <email> <password> [width=390] [height=844] path1 path2 ...
import {launch, login} from './lib.mjs';
const [base, email, password, w='390', h='844', ...paths] = process.argv.slice(2);
const b = await launch();
const page = await b.newPage();
await page.setViewport({width: +w, height: +h});
await login(page, base, email, password);
for (const p of paths) {
  await page.goto(base + p, {waitUntil: 'networkidle0'});
  const r = await page.evaluate(() => {
    const de = document.documentElement;
    const rect = s => { const e = document.querySelector(s); if (!e || !e.offsetParent && getComputedStyle(e).position !== 'fixed') return null; const r = e.getBoundingClientRect(); return {l:r.left,t:r.top,r:r.right,b:r.bottom}; };
    const t = rect('#sidebarToggle'), h1 = rect('.page-title');
    const overlap = t && h1 ? !(t.r <= h1.l || h1.r <= t.l || t.b <= h1.t || h1.b <= t.t) : false;
    const wide = [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1 && !e.closest('.table-responsive') && !e.closest('.sidebar')).slice(0,3).map(e => e.tagName.toLowerCase() + '.' + [...e.classList].join('.'));
    const logouts = [...document.querySelectorAll('a,button')].filter(e => /logout/i.test(e.textContent) && e.offsetParent !== null).length;
    return {viewport: innerWidth, scrollWidth: de.scrollWidth, overflowX: de.scrollWidth > innerWidth, toggleOverlapsTitle: overlap, visibleLogoutControls: logouts, offenders: wide};
  });
  console.log(p.padEnd(34), JSON.stringify(r));
}
await b.close();
