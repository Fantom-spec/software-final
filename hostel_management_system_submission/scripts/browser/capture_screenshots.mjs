// Captures screenshots of the RUNNING app (demo server with demo data) into <outDir> and writes manifest.json.
// Usage: node capture_screenshots.mjs <baseUrl> <outDir>
import fs from 'node:fs';
import path from 'node:path';
import {launch, login} from './lib.mjs';

const base = process.argv[2] || 'http://127.0.0.1:5000';
const outDir = process.argv[3] || '../../assessment9_ui/screenshots';
fs.mkdirSync(outDir, {recursive: true});
const manifest = [];
const sleep = ms => new Promise(r => setTimeout(r, ms));
const VIEWPORTS = {desktop: {width: 1366, height: 800}, mobile: {width: 390, height: 844}};
const browser = await launch();

async function fresh(vp) {
  const p = await browser.newPage();
  await (await p.createCDPSession()).send('Network.clearBrowserCookies');
  await p.setViewport(VIEWPORTS[vp]);
  return p;
}
async function shot(p, vp, name, description) {
  const file = `${name}_${vp}.png`;
  await p.screenshot({path: path.join(outDir, file), fullPage: true});
  manifest.push({file, viewport: vp, size: `${VIEWPORTS[vp].width}x${VIEWPORTS[vp].height}`, url: p.url().replace(base, ''), description});
  console.log('captured', file);
}
const go = (p, u) => p.goto(base + u, {waitUntil: 'networkidle0'});
// Pick an <option> by visible text so every screenshot uses deliberate, named data.
const optionValue = (p, sel, text) => p.$$eval(`${sel} option`, (o, t) => (o.find(x => x.textContent.includes(t)) || {}).value, text);

for (const vp of Object.keys(VIEWPORTS)) {
  // ---- anonymous: login + failed login
  let p = await fresh(vp);
  await go(p, '/auth/login');
  await shot(p, vp, 'login', 'Login screen (empty form)');
  await p.type('input[name=email]', 'admin@hms.test');
  await p.type('input[name=password]', 'wrong-password');
  await Promise.all([p.waitForNavigation({waitUntil: 'networkidle0'}), p.click('button[type=submit]')]);
  await shot(p, vp, 'login_error', 'Login with wrong password: error feedback');
  await p.close();

  // ---- admin
  p = await fresh(vp);
  await login(p, base, 'admin@hms.test', 'admin123');
  await shot(p, vp, 'admin_dashboard', 'Admin dashboard (populated: statistics, occupancy, recent allocations)');
  await go(p, '/allocation/');
  await shot(p, vp, 'admin_allocations', 'Allocation list with 3 active allocations, filters and actions');
  await go(p, '/allocation/create');
  await shot(p, vp, 'admin_create_form', 'Create allocation form (empty)');
  const dana = await optionValue(p, '#student_id', 'Dana Evans');      // has no allocation
  const john = await optionValue(p, '#student_id', 'John Doe');        // already has an active allocation
  const room201 = await optionValue(p, '#room_id', 'Block A - 201');
  if (!dana || !john || !room201) throw new Error('demo data not as expected (Dana/John/Block A 201 missing)');
  await p.select('#student_id', dana);
  await p.select('#room_id', room201);
  await sleep(300);
  await shot(p, vp, 'admin_create_form_filled', 'Create allocation form filled in (Dana Evans, Block A 201); live room availability preview shown');
  // server-side validation error: end date before start date (bypasses client checks on purpose)
  await p.evaluate(() => { document.querySelector('#start_date').value = '2026-11-10'; const e = document.querySelector('#end_date'); e.min = ''; e.value = '2026-11-01'; HTMLFormElement.prototype.submit.call(document.querySelector('form.needs-validation')); });
  await p.waitForNavigation({waitUntil: 'networkidle0'});
  await shot(p, vp, 'admin_create_error_dates', 'Server-side validation error (end date before start date); entered values are kept');
  // business-rule error: student already has an active allocation
  await go(p, '/allocation/create');
  await p.select('#student_id', john);
  await p.select('#room_id', room201);
  await p.evaluate(() => HTMLFormElement.prototype.submit.call(document.querySelector('form.needs-validation')));
  await p.waitForNavigation({waitUntil: 'networkidle0'});
  await shot(p, vp, 'admin_create_error_duplicate', 'Business-rule error: student already has an active allocation');
  // reallocate
  await go(p, '/allocation/');
  const href = await p.$eval('a[href*="/reallocate"]', a => a.getAttribute('href'));
  await go(p, href);
  await shot(p, vp, 'admin_reallocate_form', 'Reallocate form for an existing allocation');
  // confirmation modal
  await go(p, '/allocation/');
  await p.click('form[data-confirm] button[type=submit]');
  await p.waitForSelector('#confirmModal.show', {visible: true});
  await sleep(500);
  await shot(p, vp, 'admin_cancel_confirmation', 'Confirmation modal before cancelling an allocation');
  await p.close();

  p = await fresh(vp);
  await login(p, base, 'admin@hms.test', 'admin123');
  await go(p, '/allocation/available');
  await shot(p, vp, 'admin_available_rooms', 'Available rooms with block filter and occupancy bars');
  await go(p, '/allocation/available?show_all=true');
  await shot(p, vp, 'admin_available_rooms_all', 'Available rooms including full rooms (show all)');
  await go(p, '/rooms');
  await shot(p, vp, 'admin_rooms', 'Rooms list (admin: Add block / Add room buttons)');
  await go(p, '/blocks/new');
  await shot(p, vp, 'admin_add_block_form', 'Add block form (admin only)');
  await go(p, '/rooms/new');
  await p.select('#block_id', await optionValue(p, '#block_id', 'Block B'));
  await p.type('#room_number', '103');
  await p.type('#floor', '1');
  await shot(p, vp, 'admin_add_room_form', 'Add room form filled in (admin only)');
  await go(p, '/students/new');
  await shot(p, vp, 'admin_add_student_form', 'Add student form (admin only)');
  await p.type('#name', 'Duplicate Test'); await p.type('#email', 'john@student.test'); await p.type('#roll_no', 'STU777');
  await p.type('#password', 'Passw0rd!123'); await p.type('#confirm_password', 'Passw0rd!123');
  await p.evaluate(() => HTMLFormElement.prototype.submit.call(document.querySelector('form.needs-validation')));
  await p.waitForNavigation({waitUntil: 'networkidle0'});
  await shot(p, vp, 'admin_add_student_error', 'Add student: duplicate e-mail rejected; entries kept, passwords cleared');
  await go(p, '/students');
  await shot(p, vp, 'admin_students', 'Students list with allocation status');
  if (vp === 'mobile') {
    await go(p, '/');
    await p.click('#sidebarToggle');
    await sleep(500);
    await shot(p, vp, 'admin_menu_open', 'Mobile: navigation drawer opened with the hamburger button');
  }
  await p.close();

  // ---- warden
  p = await fresh(vp);
  await login(p, base, 'warden@hms.test', 'warden123');
  await shot(p, vp, 'warden_dashboard', 'Warden dashboard');
  await p.close();

  // ---- student
  p = await fresh(vp);
  await login(p, base, 'john@student.test', 'student123');
  await shot(p, vp, 'student_dashboard', 'Student dashboard (with current allocation)');
  if (vp === 'mobile') { await p.click('#sidebarToggle'); await sleep(500); }
  await Promise.all([p.waitForNavigation({waitUntil: 'networkidle0'}), p.click('.sidebar a[href*="/allocation/student/"]')]);
  await shot(p, vp, 'student_my_allocation', 'Student "My Allocation" page');
  await go(p, '/allocation/available');
  await shot(p, vp, 'student_available_rooms', 'Student view of available rooms (read-only)');
  await p.close();
}
await browser.close();
const generated = new Date().toISOString();
fs.writeFileSync(path.join(outDir, 'manifest.json'), JSON.stringify({generated, base: 'demo server (scripts/serve_demo.py)', count: manifest.length, byViewport: {desktop: manifest.filter(m => m.viewport === 'desktop').length, mobile: manifest.filter(m => m.viewport === 'mobile').length}, screenshots: manifest}, null, 2));
console.log(`\n${manifest.length} screenshots written to ${outDir}`);
