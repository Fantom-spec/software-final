// Real-browser verification of the running app. Prints one line per check and exits non-zero on any failure.
// Usage: node verify_ui.mjs <baseUrl>
import {launch, login} from './lib.mjs';
const base = process.argv[2] || 'http://127.0.0.1:5000';
const results = [];
process.on('uncaughtException', e => { console.log('FAIL  verification script crashed before finishing  -> ' + String(e.message).split('\n')[0]); process.exit(1); });
process.on('unhandledRejection', e => { console.log('FAIL  verification script crashed before finishing  -> ' + String(e && e.message).split('\n')[0]); process.exit(1); });
const check = (name, ok, detail = '') => { results.push({name, ok, detail}); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  -> ' + detail : ''}`); };

const browser = await launch();
const problems = {console: [], csp: [], http: []};
async function newPage(w, h) {
  const p = await browser.newPage();
  await (await p.createCDPSession()).send("Network.clearBrowserCookies");
  await p.setViewport({width: w, height: h});
  p.on('console', m => { if (m.type() === 'error') problems.console.push(m.text()); });
  p.on('response', r => { if (r.status() >= 400 && !r.url().endsWith('/favicon.ico')) problems.http.push(`${r.status()} ${r.url()}`); });
  await p.evaluateOnNewDocument(() => document.addEventListener('securitypolicyviolation', e => console.error('CSP:' + e.violatedDirective + ' ' + e.blockedURI)));
  return p;
}

// 1. Layout at several widths (admin)
const pages = ['/', '/allocation/', '/allocation/available', '/rooms', '/students', '/allocation/create', '/blocks/new', '/rooms/new', '/students/new'];
for (const w of [320, 390, 768, 1366]) {
  const p = await newPage(w, 800);
  await login(p, base, 'admin@hms.test', 'admin123');
  for (const path of pages) {
    await p.goto(base + path, {waitUntil: 'networkidle0'});
    const r = await p.evaluate(() => {
      const t = document.querySelector('#sidebarToggle'), h = document.querySelector('.page-title');
      const vis = e => e && getComputedStyle(e).display !== 'none';
      let overlap = false;
      if (vis(t) && h) { const a = t.getBoundingClientRect(), b = h.getBoundingClientRect(); overlap = !(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top); }
      return {overflow: document.documentElement.scrollWidth - innerWidth, overlap};
    });
    check(`layout ${w}px ${path}`, r.overflow <= 0 && !r.overlap, `horizontalOverflow=${r.overflow}px toggleOverlapsTitle=${r.overlap}`);
  }
  await p.close();
}

// 2. Mobile menu opens, shows navigation, and POST logout works
{
  const p = await newPage(390, 800);
  await login(p, base, 'admin@hms.test', 'admin123');
  await p.goto(base + '/', {waitUntil: 'networkidle0'});
  const hiddenBefore = await p.evaluate(() => document.querySelector('.sidebar').getBoundingClientRect().right <= 0);
  await p.click('#sidebarToggle');
  await new Promise(r => setTimeout(r, 400));
  const shown = await p.evaluate(() => document.querySelector('.sidebar').getBoundingClientRect().right > 100);
  check('mobile: menu closed initially, opens on hamburger tap', hiddenBefore && shown);
  await Promise.all([p.waitForNavigation({waitUntil: 'networkidle0'}), p.click('.logout-form button')]);
  check('logout button (POST+CSRF) ends the session', p.url().includes('/auth/login'), p.url());
  const flash = await p.$eval('.alert', e => e.textContent.trim()).catch(() => '');
  check('logout gives feedback message', /logged out/i.test(flash), flash);
  await p.goto(base + '/', {waitUntil: 'networkidle0'});
  check('after logout, dashboard is not reachable', p.url().includes('/auth/login'));
  await p.close();
}

// 3. Desktop: cancel confirmation, server-side validation retains input, role menus
{
  const p = await newPage(1366, 800);
  await login(p, base, 'admin@hms.test', 'admin123');
  const labels = await p.$$eval('.sidebar a.sidebar-link', as => as.map(a => a.textContent.trim()));
  check('admin sidebar items', JSON.stringify(labels) === JSON.stringify(['Dashboard', 'Allocations', 'Available Rooms', 'Rooms', 'Students']), labels.join(' | '));
  check('only one visible Logout control (desktop)', await p.evaluate(() => [...document.querySelectorAll('a,button')].filter(e => /logout/i.test(e.textContent) && e.offsetParent).length) === 1);

  await p.goto(base + '/allocation/', {waitUntil: 'networkidle0'});
  const before = await p.$$eval('table tbody tr', r => r.length);
  await p.click('form[data-confirm] button[type=submit]');
  await p.waitForSelector('#confirmModal.show', {visible: true});
  const modalMsg = await p.$eval('#confirmModalMessage', e => e.textContent.trim());
  await new Promise(r => setTimeout(r, 400)); // let the slide-in animation finish
  await p.click('#confirmModal .btn-outline-secondary');
  await p.waitForSelector('#confirmModal', {hidden: true});
  await new Promise(r => setTimeout(r, 600)); // let the fade-out finish before reopening
  const afterGoBack = await p.$$eval('table tbody tr', r => r.length);
  check('cancel: confirmation modal shown with message; "Go back" keeps the allocation', /sure/i.test(modalMsg) && afterGoBack === before, `modal="${modalMsg}" rows ${before}->${afterGoBack}`);
  await p.click('form[data-confirm] button[type=submit]');
  await p.waitForSelector('#confirmModal.show', {visible: true});
  await new Promise(r => setTimeout(r, 400));
  await Promise.all([p.waitForNavigation({waitUntil: 'networkidle0'}), p.click('#confirmModalOk')]);
  const flashCancel = await p.$eval('.alert', e => e.textContent.trim()).catch(() => '');
  check('cancel: "Confirm" cancels the allocation and shows feedback', /cancel/i.test(flashCancel), flashCancel);

  await p.goto(base + '/allocation/create', {waitUntil: 'networkidle0'});
  const studentVal = await p.$$eval('#student_id option', o => o.map(x => x.value).filter(Boolean)[0]);
  const roomVal = await p.$$eval('#room_id option', o => o.map(x => x.value).filter(Boolean)[0]);
  await p.select('#student_id', studentVal); await p.select('#room_id', roomVal);
  await p.evaluate(() => { document.querySelector('#start_date').value = '2026-11-10'; const e = document.querySelector('#end_date'); e.min = ''; e.value = '2026-11-01'; HTMLFormElement.prototype.submit.call(document.querySelector('form.needs-validation')); });
  await p.waitForNavigation({waitUntil: 'networkidle0'});
  const err = await p.$eval('.alert-error, .alert-danger', e => e.textContent.trim()).catch(() => '');
  const kept = await p.evaluate(() => ({s: document.querySelector('#student_id').value, r: document.querySelector('#room_id').value, sd: document.querySelector('#start_date').value, ed: document.querySelector('#end_date').value}));
  check('validation error shown after server-side check', /cannot be earlier/i.test(err), err);
  check('validation error keeps all entered values', kept.s === studentVal && kept.r === roomVal && kept.sd === '2026-11-10' && kept.ed === '2026-11-01', JSON.stringify(kept));
  const visible = await p.$eval('.alert-error, .alert-danger', e => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }).catch(() => false);
  check('error message is visible in the first screen (no scrolling needed)', visible);
  await new Promise(r => setTimeout(r, 6500)); // beyond the 5 s fade-out used for success/info messages
  check('error message persists beyond the 5 s auto-dismiss window', await p.$('.alert-error, .alert-danger') !== null);
  await p.close();
}

// 3a. A blocked submit must leave the button usable (it used to stay stuck on "Processing...")
{
  const p = await newPage(1366, 800);
  await login(p, base, 'admin@hms.test', 'admin123');
  await p.goto(base + '/allocation/create', {waitUntil: 'networkidle0'});
  await p.click('form.needs-validation button[type=submit]');
  await new Promise(r => setTimeout(r, 500));
  const st = await p.$eval('form.needs-validation button[type=submit]', b => ({disabled: b.disabled, text: b.textContent.trim()}));
  check('submit button stays usable after a blocked submit', !st.disabled && /Create allocation/.test(st.text), JSON.stringify(st));
  await p.close();
}

// 3b. Admin data entry through the real forms, then log in as the new student
{
  const p = await newPage(1366, 800);
  await login(p, base, 'admin@hms.test', 'admin123');
  const submit = () => Promise.all([p.waitForNavigation({waitUntil: 'networkidle0'}), p.click('form.needs-validation button[type=submit]')]);
  const successFlash = () => p.$eval('.alert-success', e => e.textContent.trim()).catch(() => '');
  await p.goto(base + '/blocks/new', {waitUntil: 'networkidle0'});
  await p.type('#name', 'Block C'); await p.type('#location', 'South Campus');
  await submit();
  const f1 = await successFlash();
  check('admin adds a block through the form', /Block "Block C" added\./.test(f1) && p.url().endsWith('/rooms'), f1);
  await p.goto(base + '/rooms/new', {waitUntil: 'networkidle0'});
  const blockVal = await p.$$eval('#block_id option', o => (o.find(x => x.textContent.trim() === 'Block C') || {}).value);
  await p.select('#block_id', blockVal);
  await p.type('#room_number', '301'); await p.type('#floor', '3');
  await submit();
  const f2 = await successFlash();
  const roomRow = await p.$$eval('table tbody tr', r => r.map(x => x.textContent.replace(/\s+/g, ' ')).find(t => t.includes('Block C') && t.includes('301')) || '');
  check('admin adds a room through the form', /Room 301 added to Block C\./.test(f2) && roomRow.includes('0 / 2 beds'), f2 + ' | ' + roomRow.trim());
  await p.goto(base + '/students/new', {waitUntil: 'networkidle0'});
  await p.type('#name', 'Frank Green'); await p.type('#email', 'frank@student.test'); await p.type('#roll_no', 'STU900');
  await p.type('#course', 'B.Tech IT'); await p.type('#batch', '2026');
  await p.type('#password', 'Frank#Pass123'); await p.type('#confirm_password', 'Frank#Pass123');
  await submit();
  const f3 = await successFlash();
  check('admin adds a student through the form', /Student Frank Green \(STU900\) added\./.test(f3), f3);
  await p.close();
  const q = await newPage(1366, 800);
  await login(q, base, 'frank@student.test', 'Frank#Pass123');
  const menu = await q.$$eval('.sidebar a.sidebar-link', as => as.map(a => a.textContent.trim()));
  check('new student can log in and sees the student menu', JSON.stringify(menu) === JSON.stringify(['Dashboard', 'Available Rooms', 'My Allocation']), menu.join(' | '));
  await q.close();
}

// 4. Student role
{
  const p = await newPage(1366, 800);
  await login(p, base, 'john@student.test', 'student123');
  const labels = await p.$$eval('.sidebar a.sidebar-link', as => as.map(a => a.textContent.trim()));
  check('student sidebar items', JSON.stringify(labels) === JSON.stringify(['Dashboard', 'Available Rooms', 'My Allocation']), labels.join(' | '));
  await Promise.all([p.waitForNavigation({waitUntil: 'networkidle0'}), p.click('.sidebar a[href*="/allocation/student/"]')]);
  check('My Allocation opens the student\'s own allocation page', /\/allocation\/student\/\d+$/.test(p.url()), p.url());
  await p.close();
}

// 5. Nothing blocked by CSP, no JS errors, no failed requests
check('no CSP violations in any page', problems.csp.length === 0 && !problems.console.some(m => m.startsWith('CSP:')), problems.console.filter(m => m.startsWith('CSP:')).join('; '));
check('no JavaScript/console errors', problems.console.filter(m => !m.startsWith('CSP:')).length === 0, problems.console.slice(0, 3).join('; '));
check('no failed HTTP requests (4xx/5xx) other than intended ones', problems.http.filter(x => !/\/allocation\/\d+\/cancel/.test(x)).length === 0, problems.http.slice(0, 3).join('; '));

await browser.close();
const failed = results.filter(r => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} browser checks passed`);
process.exit(failed ? 1 : 0);
