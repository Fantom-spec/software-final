// Reference screenshots for the manual test sheet: walks the cases in sheet order on a FRESH demo server
// (DEMO_ALLOCATIONS=0, LOGIN_MAX_ATTEMPTS=5) and captures the decisive screen of each case.
// These show the EXPECTED state as produced by a script. They are NOT evidence that a human executed a case.
// Usage: node capture_manual_case_screens.mjs <baseUrl> <outDir>
import fs from 'node:fs';
import path from 'node:path';
import {launch} from './lib.mjs';

const base = process.argv[2] || 'http://127.0.0.1:5000';
const out = process.argv[3] || '../../assessment8_testing/manual_testing/reference_screenshots';
fs.rmSync(out, {recursive: true, force: true});
fs.mkdirSync(out, {recursive: true});
const D = {width: 1366, height: 800}, M = {width: 390, height: 844};
const CRED = {admin: ['admin@hms.test', 'admin123'], warden: ['warden@hms.test', 'warden123'], student: ['john@student.test', 'student123'],
              accountant: ['accountant@hms.test', 'accountant123'], frank: ['frank@student.test', 'Frank#Pass123']};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const iso = n => { const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
const browser = await launch();
const shots = {}, failures = [];
let cur = null;

async function newPage(vp) { const p = await browser.newPage(); await p.setViewport(vp); return p; }
async function clearCookies(p) { await (await p.createCDPSession()).send('Network.clearBrowserCookies'); cur = null; }
async function go(p, u) { await p.goto(base + u, {waitUntil: 'networkidle0'}); }
async function loginForm(p, who) {
  await go(p, '/auth/login');
  await p.type('input[name=email]', CRED[who][0]); await p.type('input[name=password]', CRED[who][1]);
  await Promise.all([p.waitForNavigation({waitUntil: 'networkidle0'}), p.click('button[type=submit]')]);
  cur = who;
}
async function as(p, who) { if (cur === who) return; await clearCookies(p); await loginForm(p, who); }
async function snap(id, caption, p, opts = {}) {
  const n = (shots[id] = shots[id] || []).length + 1;
  const file = `${id}_${n}.jpg`;
  await p.screenshot({path: path.join(out, file), type: 'jpeg', quality: 72, fullPage: !!opts.fullPage, ...(opts.clip ? {clip: opts.clip} : {})});
  shots[id].push({file, caption});
}
const optionValue = (p, sel, text) => p.$$eval(`${sel} option`, (o, t) => (o.find(x => x.textContent.includes(t)) || {}).value, text);
const FORM = 'form.needs-validation';
const clickSubmit = p => Promise.all([p.waitForNavigation({waitUntil: 'networkidle0'}), p.click(`${FORM} button[type=submit]`)]);
const bypassSubmit = async p => { await Promise.all([p.waitForNavigation({waitUntil: 'networkidle0'}), p.evaluate(f => HTMLFormElement.prototype.submit.call(document.querySelector(f)), FORM)]); };
const dropCsrf = p => p.evaluate(f => document.querySelector(f + ' input[name=csrf_token]').remove(), FORM);
const expand = (p, sel) => p.evaluate(s => { const e = document.querySelector(s); e.size = e.options.length; }, sel);
const setVal = (p, sel, v) => p.evaluate((s, x) => { document.querySelector(s).value = x; }, sel, v);
const rowHref = (p, name, part) => p.evaluate((n, q) => [...document.querySelectorAll('tbody tr')].find(r => r.textContent.includes(n)).querySelector(`a[href*="${q}"]`).getAttribute('href'), name, part);
async function fillAlloc(p, student, roomText, extra = {}) {
  await go(p, '/allocation/create');
  await p.select('#student_id', await optionValue(p, '#student_id', student));
  await p.select('#room_id', await optionValue(p, '#room_id', roomText));
  if (extra.start) await setVal(p, '#start_date', extra.start);
  if (extra.end) await setVal(p, '#end_date', extra.end);
}
async function run(id, fn) {
  try { await fn(); if (!shots[id]) throw new Error('no screenshot taken'); }
  catch (e) { failures.push(`${id}: ${String(e.message).split('\n')[0]}`); console.log('FAILED', id, '-', String(e.message).split('\n')[0]); }
}
const P = await newPage(D), P2 = await newPage(D), PM = await newPage(M);
const cookieHome = async () => { await clearCookies(P); };

// ------------------------------------------------------------ Authentication
await run('AUTH-01', async () => { await clearCookies(P); await loginForm(P, 'admin'); await snap('AUTH-01', 'Admin dashboard after a successful login, with the welcome message', P); });
await run('AUTH-02', async () => { await clearCookies(P); await loginForm(P, 'warden'); await snap('AUTH-02', 'Warden dashboard after login', P); });
await run('AUTH-03', async () => { await clearCookies(P); await loginForm(P, 'student'); await snap('AUTH-03', 'Student dashboard after login', P); });
await run('AUTH-04', async () => { await clearCookies(P); await go(P, '/auth/login'); await P.type('input[name=email]', 'admin@hms.test'); await P.type('input[name=password]', 'wrong-password');
  await Promise.all([P.waitForNavigation({waitUntil: 'networkidle0'}), P.click('button[type=submit]')]); await snap('AUTH-04', 'Wrong password: error message, still on the login page', P); });
await run('AUTH-05', async () => { await clearCookies(P); await go(P, '/auth/login'); await P.type('input[name=email]', 'nobody@example.com'); await P.type('input[name=password]', 'x');
  await Promise.all([P.waitForNavigation({waitUntil: 'networkidle0'}), P.click('button[type=submit]')]); await snap('AUTH-05', 'Unknown user: the same generic error message', P); });
await run('AUTH-06', async () => { await as(P, 'admin'); await go(P, '/'); await Promise.all([P.waitForNavigation({waitUntil: 'networkidle0'}), P.click('.logout-form button')]); cur = null;
  await snap('AUTH-06', 'Step 1: after clicking Logout - login page with "You have been logged out."', P); await go(P, '/allocation/');
  await snap('AUTH-06', 'Step 2: opening /allocation/ while logged out redirects to the login page', P); });
await run('AUTH-07', async () => { await clearCookies(P); await go(P, '/rooms'); await snap('AUTH-07', 'Anonymous access to /rooms is redirected to the login page with a message', P); });
await run('AUTH-08', async () => { await clearCookies(P); await go(P, '/auth/login'); await P.evaluate(() => document.querySelector('input[name=csrf_token]').remove());
  await P.type('input[name=email]', 'admin@hms.test'); await P.type('input[name=password]', 'admin123');
  await Promise.all([P.waitForNavigation({waitUntil: 'networkidle0'}), P.click('button[type=submit]')]); await snap('AUTH-08', 'Login without the CSRF token: request rejected (HTTP 400 page)', P); });
await run('AUTH-09', async () => { await clearCookies(P);
  for (let i = 0; i < 5; i++) { await go(P, '/auth/login'); await P.type('input[name=email]', 'dana@student.test'); await P.type('input[name=password]', 'wrong' + i);
    await Promise.all([P.waitForNavigation({waitUntil: 'networkidle0'}), P.click('button[type=submit]')]); }
  await snap('AUTH-09', 'Attempt 5 of 5 (wrong password): still the normal error message', P);
  await go(P, '/auth/login'); await P.type('input[name=email]', 'dana@student.test'); await P.type('input[name=password]', 'student123');
  await Promise.all([P.waitForNavigation({waitUntil: 'networkidle0'}), P.click('button[type=submit]')]);
  await snap('AUTH-09', 'Attempt 6 with the CORRECT password: locked out message', P);
  await clearCookies(P); await loginForm(P, 'student'); await snap('AUTH-09', 'A different account (John) can still log in', P); });
await run('AUTH-10', async () => { await as(P, 'admin'); await go(P, '/auth/logout'); await snap('AUTH-10', 'Step 1: opening /auth/logout in the address bar - "Method Not Allowed"', P);
  await go(P, '/'); await snap('AUTH-10', 'Step 2: the dashboard is still shown - you are still logged in', P); });

// ------------------------------------------------------------ Allocation
await run('ALLOC-01', async () => { await as(P, 'admin'); await fillAlloc(P, 'John Doe', 'Block A - 101'); await clickSubmit(P); await snap('ALLOC-01', 'John Doe allocated to Block A 101 (open-ended): success message and the new row', P); });
await run('ALLOC-08', async () => { await fillAlloc(P, 'Jane Smith', 'Block A - 101', {end: iso(90)}); await clickSubmit(P); await snap('ALLOC-08', 'Jane Smith allocated with an end date (90 days ahead)', P); });
await run('OCC-01', async () => { await go(P, '/rooms'); await snap('OCC-01', 'Rooms page: Block A 101 is 2 / 2 beds and Full', P); });
await run('ALLOC-05', async () => { await fillAlloc(P, 'John Doe', 'Block B - 101'); await clickSubmit(P); await snap('ALLOC-05', 'Second allocation for John refused: "already has an active room allocation"', P); });
await run('ALLOC-15', async () => { await snap('ALLOC-15', 'The same screen: the form is shown again with John Doe and Block B 101 still selected', P); });
await run('ALLOC-11', async () => { await fillAlloc(P, 'Bob Wilson', 'Block A - 102', {end: iso(0)}); await clickSubmit(P); await snap('ALLOC-11', 'Bob Wilson allocated with start date = end date = today', P); });
await run('ALLOC-02', async () => {
  await go(P2, '/allocation/create');                                   // tab 2 opened BEFORE the room fills up
  await fillAlloc(P, 'Alice Brown', 'Block A - 102'); await clickSubmit(P);   // tab 1 takes the last bed
  await P2.select('#student_id', await optionValue(P2, '#student_id', 'Carlos Diaz'));
  await P2.select('#room_id', await optionValue(P2, '#room_id', 'Block A - 102'));
  await Promise.all([P2.waitForNavigation({waitUntil: 'networkidle0'}), P2.click(`${FORM} button[type=submit]`)]);
  await snap('ALLOC-02', 'Tab 2 (stale form): room 102 is no longer available - the server refuses the allocation', P2); });
await run('ALLOC-09', async () => { await as(P, 'warden'); await fillAlloc(P, 'Carlos Diaz', 'Block A - 201'); await clickSubmit(P); await snap('ALLOC-09', 'Warden allocates Carlos Diaz to Block A 201', P); });
await run('ALLOC-03', async () => { await as(P, 'admin'); await go(P, '/allocation/create');
  await P.evaluate(() => { const o = [...document.querySelectorAll('#student_id option')].find(x => x.value); o.value = '99999'; });
  await P.select('#student_id', '99999'); await P.select('#room_id', await optionValue(P, '#room_id', 'Block A - 202')); await bypassSubmit(P);
  await snap('ALLOC-03', 'Student id 99999 (edited in DevTools): "Selected student does not exist."', P); });
await run('ALLOC-04', async () => { await go(P, '/allocation/create'); await P.select('#student_id', await optionValue(P, '#student_id', 'Dana Evans'));
  await P.evaluate(() => { const o = [...document.querySelectorAll('#room_id option')].find(x => x.value); o.value = '99999'; }); await P.select('#room_id', '99999'); await bypassSubmit(P);
  await snap('ALLOC-04', 'Room id 99999 (edited in DevTools): "Selected room does not exist."', P); });
await run('ALLOC-06', async () => { await go(P, '/allocation/create'); await P.click(`${FORM} button[type=submit]`); await sleep(400);
  await snap('ALLOC-06', 'Submitting with Student and Room empty: the required fields are flagged and nothing is sent', P); });
await run('ALLOC-07', async () => { await fillAlloc(P, 'Dana Evans', 'Block A - 202'); await P.evaluate(() => { const s = document.querySelector('#start_date'); s.type = 'text'; s.value = '2026-13-45'; }); await bypassSubmit(P);
  await snap('ALLOC-07', 'Start date "2026-13-45" (field changed to text in DevTools): "Invalid date format"', P); });
await run('ALLOC-10', async () => { await fillAlloc(P, 'Dana Evans', 'Block A - 202'); await setVal(P, '#start_date', iso(10)); await P.evaluate(() => document.querySelector('#start_date').dispatchEvent(new Event('change')));
  await setVal(P, '#end_date', iso(5)); await P.click(`${FORM} button[type=submit]`); await sleep(400);
  await snap('ALLOC-10', 'End date (today+5) before start date (today+10): the form refuses to submit', P); });
await run('ALLOC-14', async () => { await fillAlloc(P, 'Dana Evans', 'Block A - 202'); await P.evaluate(() => { const s = document.querySelector('#start_date'); s.type = 'text'; s.value = '1900-01-01'; }); await bypassSubmit(P);
  await snap('ALLOC-14', 'Start date 1900-01-01: "Dates must be between 2000-01-01 and 2100-12-31."', P); });
await run('ALLOC-13', async () => { await fillAlloc(P, 'Dana Evans', 'Block A - 202'); await dropCsrf(P); await clickSubmit(P);
  await snap('ALLOC-13', 'CSRF token deleted in DevTools: "Your request could not be verified" (HTTP 400)', P); });

// ------------------------------------------------------------ Reallocation
await run('REALLOC-01', async () => { await go(P, '/allocation/'); const href = await rowHref(P, 'John Doe', 'reallocate'); await go(P, href);
  await P.select('#new_room_id', await optionValue(P, '#new_room_id', 'Block B - 101')); await clickSubmit(P);
  await snap('REALLOC-01', 'John reallocated to Block B 101: message "Student reallocated to room 101 successfully."', P); });
await run('OCC-02', async () => { await go(P, '/rooms'); await snap('OCC-02', 'Rooms page: Block A 101 is now 1 / 2 beds and Available; Block B 101 is 1 / 3', P); });
await run('REALLOC-03', async () => { await go(P, '/allocation/'); await go(P, await rowHref(P, 'Carlos Diaz', 'reallocate')); await expand(P, '#new_room_id');
  await snap('REALLOC-03', 'Reallocate form for Carlos (list expanded for the screenshot): Block A 102 (full) is not offered', P); });
await run('REALLOC-06', async () => { await go(P, '/allocation/'); await go(P, await rowHref(P, 'Jane Smith', 'reallocate'));
  await P.evaluate(() => { const o = [...document.querySelectorAll('#new_room_id option')].find(x => x.value); o.value = '1'; }); await P.select('#new_room_id', '1'); await bypassSubmit(P);
  await snap('REALLOC-06', 'Room id 1 = Jane\'s current room (option value edited in DevTools): "Student is already in that room. Choose a different room."', P); });
await run('REALLOC-04', async () => { await go(P, '/allocation/'); await go(P, await rowHref(P, 'Jane Smith', 'reallocate')); await P.click(`${FORM} button[type=submit]`); await sleep(400);
  await snap('REALLOC-04', 'No room selected: the field is flagged and the form is not submitted', P); });
await run('REALLOC-02', async () => { await go(P, '/allocation/'); await go(P, await rowHref(P, 'Jane Smith', 'reallocate'));
  await P.evaluate(() => { const o = [...document.querySelectorAll('#new_room_id option')].find(x => x.value); o.value = '99999'; }); await P.select('#new_room_id', '99999'); await bypassSubmit(P);
  await snap('REALLOC-02', 'Room id 99999 (edited in DevTools): "Selected room does not exist."', P); });
await run('REALLOC-05', async () => { await go(P, '/allocation/'); await go(P, await rowHref(P, 'Jane Smith', 'reallocate')); await P.select('#new_room_id', await optionValue(P, '#new_room_id', 'Block A - 201')); await dropCsrf(P); await clickSubmit(P);
  await snap('REALLOC-05', 'CSRF token deleted: "Your request could not be verified" (HTTP 400); Jane stays where she is', P); });

// ------------------------------------------------------------ Cancellation
const carlosCancel = 'form[data-confirm] button[type=submit]';
const clickRowCancel = (p, name) => p.evaluate(n => [...document.querySelectorAll('tbody tr')].find(r => r.textContent.includes(n)).querySelector('form[data-confirm] button[type=submit]').click(), name);
await run('CANCEL-02', async () => { await go(P, '/allocation/'); await clickRowCancel(P, 'Carlos Diaz'); await P.waitForSelector('#confirmModal.show', {visible: true}); await sleep(600);
  await snap('CANCEL-02', 'Confirmation dialog for cancelling Carlos Diaz\'s allocation', P); await P.click('#confirmModal .btn-outline-secondary'); await P.waitForSelector('#confirmModal', {hidden: true}); await sleep(700);
  await snap('CANCEL-02', 'After "Go back": the dialog is closed and Carlos is still Active', P); });
await run('CANCEL-01', async () => { await clickRowCancel(P, 'Carlos Diaz'); await P.waitForSelector('#confirmModal.show', {visible: true}); await sleep(600);
  await Promise.all([P.waitForNavigation({waitUntil: 'networkidle0'}), P.click('#confirmModalOk')]); await snap('CANCEL-01', 'After "Confirm": "Allocation cancelled successfully." and Carlos is gone from the active list', P); });
await run('CANCEL-04', async () => { await go(P, '/allocation/?status=cancelled'); await snap('CANCEL-04', 'Status = Cancelled: Carlos is listed as Cancelled with no action buttons', P); });
await run('CANCEL-03', async () => { await go(P, '/allocation/'); await P.evaluate(n => { const r = [...document.querySelectorAll('tbody tr')].find(x => x.textContent.includes(n)); r.querySelector('form[data-confirm] input[name=csrf_token]').remove(); }, 'Bob Wilson');
  await clickRowCancel(P, 'Bob Wilson'); await P.waitForSelector('#confirmModal.show', {visible: true}); await sleep(600);
  await Promise.all([P.waitForNavigation({waitUntil: 'networkidle0'}), P.click('#confirmModalOk')]); await snap('CANCEL-03', 'Cancel without a CSRF token: HTTP 400 page; Bob\'s allocation is untouched', P); });

// ------------------------------------------------------------ List / available / student
await run('LIST-01', async () => { await go(P, '/allocation/?search=Jane'); await snap('LIST-01', 'Search "Jane": only Jane Smith\'s row', P); await go(P, '/allocation/?search=nobody-matches'); await snap('LIST-01', 'Search "nobody-matches": "No allocations found."', P); });
await run('LIST-02', async () => { await go(P, '/allocation/?block=2&status=active'); await snap('LIST-02', 'Block B filter: only Block B rows', P); await go(P, '/allocation/?status=cancelled'); await snap('LIST-02', 'Status Cancelled filter: only cancelled allocations', P); });
await run('AVAIL-01', async () => { await go(P, '/allocation/available'); await snap('AVAIL-01', 'Available Rooms: Block A 102 (full) is not listed', P, {fullPage: true}); });
await run('AVAIL-03', async () => { await go(P, '/allocation/available?show_all=true'); await snap('AVAIL-03', 'Step 1: "Show full rooms" ticked - the full room appears', P, {fullPage: true});
  await go(P, '/allocation/available?show_all=true&block=2'); await snap('AVAIL-03', 'Step 2: Block B selected - only Block B rooms', P, {fullPage: true}); });
await run('OCC-03', async () => { await go(P, '/allocation/create'); await expand(P, '#room_id'); await snap('OCC-03', 'New Allocation room list (expanded for the screenshot): the full Block A 102 is not offered', P); });
await run('AVAIL-02', async () => { await as(P, 'student'); await go(P, '/allocation/available'); await snap('AVAIL-02', 'Student view of Available Rooms (read-only)', P, {fullPage: true}); });
await run('STUDENT-01', async () => { await go(P, '/'); await Promise.all([P.waitForNavigation({waitUntil: 'networkidle0'}), P.click('.sidebar a[href*="/allocation/student/"]')]); await snap('STUDENT-01', 'My Allocation: John Doe\'s room (Block B 101 after the reallocation)', P); });
await run('STUDENT-02', async () => { await go(P, '/allocation/student/2'); await snap('STUDENT-02', 'Opening another student\'s allocation: redirected to the dashboard with a message', P); });

// ------------------------------------------------------------ Authorization
await run('AUTHZ-01', async () => { await as(P, 'admin'); await go(P, '/students'); await snap('AUTHZ-01', 'Admin can open the Students page (all management pages load)', P); });
await run('AUTHZ-02', async () => { await as(P, 'warden'); await go(P, '/rooms'); await snap('AUTHZ-02', 'Warden can open the Rooms page', P); });
await run('AUTHZ-03', async () => { await as(P, 'student'); await go(P, '/allocation/'); await snap('AUTHZ-03', 'Student opening /allocation/: redirected with "You do not have permission..."', P); });
await run('AUTHZ-05', async () => { await as(P, 'accountant'); await go(P, '/allocation/'); await snap('AUTHZ-05', 'Accountant opening /allocation/: permission message', P); });
await run('AUTHZ-07', async () => { await as(P, 'student'); await go(P, '/rooms'); await snap('AUTHZ-07', 'Student opening /rooms: permission message', P); });
await run('AUTHZ-10', async () => { await go(P, '/allocation/2/reallocate'); await snap('AUTHZ-10', 'Student opening /allocation/2/reallocate: permission message', P); });
await run('AUTHZ-11', async () => { await go(P, '/'); await P.evaluate(() => fetch('/allocation/2/cancel', {method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: 'csrf_token=' + document.querySelector('input[name=csrf_token]').value}).then(r => r.status));
  await as(P, 'admin'); await go(P, '/allocation/'); await snap('AUTHZ-11', 'Admin check after the student\'s forged request: Jane\'s allocation (id 2) is still Active', P); });

// ------------------------------------------------------------ Security
await run('SEC-01', async () => { await as(P, 'admin'); await go(P, '/allocation/?search=' + encodeURIComponent("' OR '1'='1")); await snap('SEC-01', 'Payload 1 in the search box: normal page, no error', P);
  await go(P, '/allocation/?search=' + encodeURIComponent("'; DROP TABLE rooms; --")); await snap('SEC-01', 'Payload 2: normal page; the Rooms table is unaffected', P); await go(P, '/rooms'); await snap('SEC-01', 'Rooms page afterwards: all rooms are still there', P); });
await run('SEC-03', async () => { await go(P, '/allocation/?search=' + encodeURIComponent('<script>alert(1)</script>')); await snap('SEC-03', 'XSS payload: shown as plain text in the search field, no alert box', P); });
await run('SEC-05', async () => { await fillAlloc(P, 'Dana Evans', 'Block A - 202'); await setVal(P, `${FORM} input[name=csrf_token]`, 'forged'); await clickSubmit(P); await snap('SEC-05', 'Forged CSRF token: HTTP 400 "Your request could not be verified"', P); });
await run('SEC-06', async () => { await as(P, 'admin'); await go(P, '/'); await Promise.all([P.waitForNavigation({waitUntil: 'networkidle0'}), P.click('.logout-form button')]); cur = null; await loginForm(P, 'warden');
  await snap('SEC-06', 'After admin logout and warden login: the Warden dashboard only', P); });
await run('SEC-07', async () => { await clearCookies(P); await go(P, '/auth/login'); await snap('SEC-07', 'Login page: no demo accounts or passwords are displayed', P); });
await run('DASH-01', async () => { await as(P, 'admin'); await go(P, '/'); await snap('DASH-01', 'Admin dashboard with the data created by the previous cases', P, {fullPage: true}); });

// ------------------------------------------------------------ UI
await run('UI-01', async () => { await go(PM, '/allocation/'); await snap('UI-01', 'Mobile (390 px): Allocations - no sideways scrolling, hamburger beside the title', PM, {fullPage: true});
  await go(PM, '/'); await PM.click('#sidebarToggle'); await sleep(600); await snap('UI-01', 'Mobile: the navigation drawer after tapping the hamburger button', PM);
  await go(PM, '/rooms/new'); await snap('UI-01', 'Mobile: a form page (Add room) also fits the screen', PM, {fullPage: true}); });
await run('UI-02', async () => { const clip = {x: 0, y: 0, width: 262, height: 430};
  await as(P, 'admin'); await go(P, '/'); await snap('UI-02', 'Admin sidebar', P, {clip});
  await as(P, 'warden'); await go(P, '/'); await snap('UI-02', 'Warden sidebar', P, {clip});
  await as(P, 'student'); await go(P, '/'); await snap('UI-02', 'Student sidebar', P, {clip}); });
await run('UI-03', async () => { await as(P, 'admin'); await go(P, '/'); await snap('UI-03', 'Exactly one Logout control (bottom of the sidebar)', P, {clip: {x: 0, y: 560, width: 262, height: 240}});
  await Promise.all([P.waitForNavigation({waitUntil: 'networkidle0'}), P.click('.logout-form button')]); cur = null; await P.goBack({waitUntil: 'networkidle0'});
  await snap('UI-03', 'After Logout and the browser Back button: the login page, not the dashboard', P); });

// ------------------------------------------------------------ Data entry (run last)
await run('ADD-01', async () => { await as(P, 'admin'); await go(P, '/blocks/new'); await P.type('#name', 'Block C'); await P.type('#location', 'South Campus'); await clickSubmit(P); await snap('ADD-01', 'Block C added: message on the Rooms page', P); });
await run('ADD-02', async () => { await go(P, '/rooms/new'); await P.select('#block_id', await optionValue(P, '#block_id', 'Block C')); await P.type('#room_number', '301'); await P.type('#floor', '3'); await clickSubmit(P);
  await snap('ADD-02', 'Room 301 added to Block C: message and the new row in the table', P, {fullPage: true}); });
await run('ADD-03', async () => { await go(P, '/students/new'); await P.type('#name', 'Frank Green'); await P.type('#email', 'frank@student.test'); await P.type('#roll_no', 'STU900'); await P.type('#course', 'B.Tech IT'); await P.type('#batch', '2026');
  await P.type('#password', 'Frank#Pass123'); await P.type('#confirm_password', 'Frank#Pass123'); await clickSubmit(P); await snap('ADD-03', 'Step 3: Frank Green added - message and the new row in the Students list', P, {fullPage: true});
  await clearCookies(P); await loginForm(P, 'frank'); await snap('ADD-03', 'Step 4: logging in as Frank works and shows the student menu', P); });
await run('ADD-04', async () => { await as(P, 'admin');
  const stu = async (d, cap) => { await go(P, '/students/new'); for (const [k, v] of Object.entries({name: 'Test Person', email: 'tp@student.test', roll_no: 'TP1', password: 'Passw0rd!123', confirm_password: 'Passw0rd!123', ...d})) await P.type('#' + k, v); await bypassSubmit(P); await snap('ADD-04', cap, P); };
  await stu({email: 'john@student.test'}, '1: duplicate e-mail rejected');
  await stu({roll_no: 'STU900'}, '2: duplicate roll number rejected');
  await stu({password: 'abc', confirm_password: 'abc'}, '3: too-short password rejected');
  await go(P, '/rooms/new'); await P.select('#block_id', await optionValue(P, '#block_id', 'Block C')); await P.type('#room_number', '301'); await P.type('#floor', '3'); await bypassSubmit(P); await snap('ADD-04', '4: duplicate room number in the same block rejected', P);
  await go(P, '/blocks/new'); await P.type('#name', 'block c'); await bypassSubmit(P); await snap('ADD-04', '5: duplicate block name rejected (case-insensitive)', P); });
await run('ADD-05', async () => { await as(P, 'warden'); await go(P, '/rooms'); await snap('ADD-05', 'Warden: the Rooms page has no Add buttons', P); await go(P, '/rooms/new'); await snap('ADD-05', 'Warden opening /rooms/new: permission message', P);
  await as(P, 'student'); await go(P, '/students/new'); await snap('ADD-05', 'Student opening /students/new: permission message', P); });

await browser.close();
fs.writeFileSync(path.join(out, 'reference_manifest.json'), JSON.stringify({generated: new Date().toISOString(), note: 'Script-captured reference screenshots of the EXPECTED state. Not evidence of human execution.', cases: shots}, null, 2));
const n = Object.values(shots).reduce((a, s) => a + s.length, 0);
console.log(`\n${Object.keys(shots).length} cases, ${n} screenshots, ${failures.length} failures`);
failures.forEach(f => console.log('  -', f));
process.exit(failures.length ? 1 : 0);
