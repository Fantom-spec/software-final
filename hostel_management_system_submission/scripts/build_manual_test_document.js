// Usage: node build_manual_test_document.js <data.json> <out.docx>   (called by build_manual_test_document.py)
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, Header, Footer, AlignmentType, HeadingLevel,
  BorderStyle, WidthType, ShadingType, PageNumber, LevelFormat, HeightRule, PageBreak, VerticalAlign,
} = require('docx');

const data = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const OUT = process.argv[3];
const W = 9906;                       // content width (A4, 1000 DXA side margins)
const FONT = 'Arial';
const border = {style: BorderStyle.SINGLE, size: 4, color: 'BFBFBF'};
const borders = {top: border, bottom: border, left: border, right: border};
const executed = data.total - data.counts['Not Executed'];
const status = executed === 0 ? 'NOT EXECUTED' : executed < data.total ? 'PARTIALLY EXECUTED' : 'COMPLETE';

const run = (text, o = {}) => new TextRun({text: String(text), font: FONT, size: o.size || 20, bold: o.bold, italics: o.italics, color: o.color});
const para = (text, o = {}) => new Paragraph({
  children: Array.isArray(text) ? text : [run(text, o)],
  spacing: {before: o.before ?? 0, after: o.after ?? 80, line: o.line},
  alignment: o.align, keepNext: o.keepNext, keepLines: o.keepLines, indent: o.indent, border: o.border, pageBreakBefore: o.pageBreakBefore,
});
const h1 = t => new Paragraph({heading: HeadingLevel.HEADING_1, children: [new TextRun({text: t, font: FONT, size: 30, bold: true, color: '1F3864'})], spacing: {before: 300, after: 140}, keepNext: true});
const h2 = (t, pb) => new Paragraph({heading: HeadingLevel.HEADING_2, pageBreakBefore: !!pb, children: [new TextRun({text: t, font: FONT, size: 25, bold: true, color: '1F3864'})], spacing: {before: 260, after: 100}, keepNext: true});
const h3 = (t, pb) => new Paragraph({heading: HeadingLevel.HEADING_3, pageBreakBefore: !!pb, children: [new TextRun({text: t, font: FONT, size: 22, bold: true, color: '000000'})], spacing: {before: 120, after: 60}, keepNext: true,
  border: {top: {style: BorderStyle.SINGLE, size: 6, color: '8EAADB', space: 6}}});
const bullet = (t, ref = 'bullets') => new Paragraph({numbering: {reference: ref, level: 0}, children: Array.isArray(t) ? t : [run(t)], spacing: {after: 60}});

function cell(children, width, o = {}) {
  return new TableCell({
    children: (Array.isArray(children) ? children : [children]).map(c => (typeof c === 'string' || typeof c === 'number') ? para(String(c), {after: 40, size: o.size, bold: o.bold}) : c),
    width: {size: width, type: WidthType.DXA}, borders,
    shading: o.fill ? {fill: o.fill, type: ShadingType.CLEAR, color: 'auto'} : undefined,
    margins: {top: 60, bottom: 60, left: 100, right: 100}, verticalAlign: o.valign, columnSpan: o.span,
  });
}
const row = (cells, o = {}) => new TableRow({children: cells, cantSplit: o.cantSplit !== false, tableHeader: o.header, height: o.height ? {value: o.height, rule: HeightRule.AT_LEAST} : undefined});
const table = (rows, widths) => new Table({width: {size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA}, columnWidths: widths, rows});
const kv = (pairs, w1 = 2300) => table(pairs.map(([k, v]) => row([cell(k, w1, {fill: 'EAF0FA', bold: true}), cell(v, W - w1)])), [w1, W - w1]);
const headerRow = (labels, widths) => row(labels.map((l, i) => cell(l, widths[i], {fill: '1F3864', bold: true})).map((c, i) => c), {header: true});

function image(ref, maxW = 590, maxH = 470) {
  let s = Math.min(maxW / ref.w, maxH / ref.h, 1.5);
  return new Paragraph({alignment: AlignmentType.CENTER, spacing: {before: 40, after: 40},
    children: [new ImageRun({type: ref.abs.toLowerCase().endsWith('.png') ? 'png' : 'jpg', data: fs.readFileSync(ref.abs), transformation: {width: Math.round(ref.w * s), height: Math.round(ref.h * s)},
      altText: {title: ref.caption || 'screenshot', description: ref.caption || 'screenshot', name: 'screenshot'}})]});
}
const caption = t => para([run(t, {size: 17, italics: true, color: '595959'})], {align: AlignmentType.CENTER, after: 100});

// white header text for dark header cells
function th(labels, widths) {
  return row(labels.map((l, i) => new TableCell({children: [new Paragraph({children: [new TextRun({text: l, font: FONT, size: 19, bold: true, color: 'FFFFFF'})]})],
    width: {size: widths[i], type: WidthType.DXA}, borders, shading: {fill: '1F3864', type: ShadingType.CLEAR, color: 'auto'}, margins: {top: 60, bottom: 60, left: 100, right: 100}})), {header: true});
}
const boxed = (children, fill, color) => table([row([new TableCell({children, width: {size: W, type: WidthType.DXA}, borders: {top: {style: BorderStyle.SINGLE, size: 8, color}, bottom: {style: BorderStyle.SINGLE, size: 8, color}, left: {style: BorderStyle.SINGLE, size: 8, color}, right: {style: BorderStyle.SINGLE, size: 8, color}},
  shading: {fill, type: ShadingType.CLEAR, color: 'auto'}, margins: {top: 100, bottom: 100, left: 160, right: 160}})])], [W]);

const children = [];

// ---------------------------------------------------------------- cover
children.push(para('', {after: 600}));
children.push(para([run('Manual Test Document', {size: 56, bold: true, color: '1F3864'})], {after: 120}));
children.push(para([run('Room Allocation module - Hostel Management System', {size: 30, color: '404040'})], {after: 60}));
children.push(para([run('BCSE301P Software Engineering - Assessment 8', {size: 24, color: '404040'})], {after: 60}));
children.push(para([run('School of Computer Science Engineering and Information Systems, VIT', {size: 22, color: '595959'})], {after: 360}));
children.push(kv([
  ['Document generated', data.generated],
  ['Test cases', `${data.total} (${data.cases.filter(c => c.priority === 'P1').length} priority P1, ${data.cases.filter(c => c.priority === 'P2').length} P2, ${data.cases.filter(c => c.priority === 'P3').length} P3)`],
  ['Execution status', `${status}: ${executed} of ${data.total} cases executed`],
  ['Results so far', `Pass ${data.counts.Pass}   Fail ${data.counts.Fail}   Blocked ${data.counts.Blocked}   Not executed ${data.counts['Not Executed']}`],
  ['Reference screenshots captured', data.refCaptured.replace('T', ' ').slice(0, 19) + ' UTC (by script, from the running application)'],
]));
children.push(para('', {after: 200}));
children.push(boxed([
  para([run('Please read before using this document', {bold: true, size: 22})], {after: 80}),
  bullet('Every case lists its preconditions, steps, input data and the expected result. Follow the cases in the order shown: later cases use data created by earlier ones.'),
  bullet([run('The screenshot printed under each case is a REFERENCE image of the expected screen. ', {bold: true}), run('A script drove the real application and captured it, so you know what a correct result looks like. It is not a tester\'s evidence and does not mean the case passed.')]),
  bullet('The result boxes (actual result, status, tester, date, evidence) are blank until a person executes the case. Paste your own screenshot into the evidence box.'),
  bullet(executed === 0 ? 'At the moment no case has been executed, so this document records no pass or fail results.' : `${executed} of ${data.total} cases have recorded results; the others are still blank.`),
], 'FFF2CC', 'BF9000'));
children.push(new Paragraph({children: [new PageBreak()]}));

// ---------------------------------------------------------------- 1 purpose
children.push(h1('1. Purpose and scope'));
children.push(para('This document is the manual test plan, test script and result record for the Room Allocation module of the Hostel Management System. A tester follows the steps in a web browser, compares what happens with the expected result and records the actual result, the status and evidence.'));
children.push(para('In scope: allocating, reallocating and cancelling room allocations; listing, searching and filtering; available rooms; the student\'s own view; adding blocks, rooms and students; login, logout, lockout, role-based access, CSRF protection and basic injection handling; and the screen layout on a phone-sized window.'));
children.push(para('The same functions are also covered by the automated test suite (see the automated test report). Manual testing adds what a person can judge: what the screens look like, how messages read, and whether the workflows can really be performed by a user, including a few security checks that need the browser\'s developer tools (marked "UI + browser DevTools").'));

// ---------------------------------------------------------------- 2 environment
children.push(h1('2. Test environment and tester details (fill in)'));
children.push(kv([['Tester name', ''], ['Registration number', ''], ['Date(s) of execution', ''], ['Operating system', ''], ['Browser and version', ''], ['Python version', ''],
  ['Application build tested', ''], ['Start command used', 'DEMO_ALLOCATIONS=0 python scripts/serve_demo.py   (AUTH-09: LOGIN_MAX_ATTEMPTS=5 DEMO_ALLOCATIONS=0 python scripts/serve_demo.py)'], ['Notes', '']].map(([k, v]) => [k, v])));

// ---------------------------------------------------------------- 3 test data
children.push(h1('3. Test data'));
children.push(para('The demo server (scripts/serve_demo.py) starts with an empty throw-away database and this data. Restart it (Ctrl+C, run again) before each complete pass.', {keepNext: true}));
children.push(h2('3.1 Staff accounts'));
const aw = [1900, 3600, 2200, 2206];
children.push(table([th(['Role', 'E-mail', 'Password', 'Notes'], aw), ...data.accounts.map(a => row([cell(a.role, aw[0]), cell(a.email, aw[1]), cell(a.password, aw[2]), cell('', aw[3])]))], aw));
children.push(h2('3.2 Students (password for all: student123)'));
const sw = [700, 2200, 3000, 1100, 1800, 1106];
children.push(table([th(['Id', 'Name', 'E-mail', 'Roll no', 'Course', 'Batch'], sw), ...data.students.map(s => row([cell(s.id, sw[0]), cell(s.name, sw[1]), cell(s.email, sw[2]), cell(s.roll, sw[3]), cell(s.course, sw[4]), cell(s.batch, sw[5])]))], sw));
children.push(h2('3.3 Blocks and rooms'));
const rw = [900, 2400, 2000, 2000, 2606];
children.push(table([th(['Room id', 'Block', 'Room number', 'Floor', 'Capacity (beds)'], rw), ...data.rooms.map(r => row([cell(r.id, rw[0]), cell(r.block, rw[1]), cell(r.number, rw[2]), cell(r.floor, rw[3]), cell(r.capacity, rw[4])]))], rw));
children.push(para('Allocation ids are assigned in creation order: the first allocation created is id 1, the second id 2, and so on (cases AUTHZ-10 and AUTHZ-11 rely on this).', {before: 100, size: 18, italics: true}));

// ---------------------------------------------------------------- 4 procedure
children.push(h1('4. Procedure'));
[
  'Start the application (section 2) and open http://127.0.0.1:5000 in Chrome or Firefox.',
  'Create the folder assessment8_testing/manual_testing/evidence/ for your screenshots.',
  'Execute the cases in the order of section 6. The minimum is every case with priority P1; P2 and P3 are recommended.',
  'For each case: do the steps exactly as written; compare the result with the expected result; take a screenshot of the decisive screen.',
  'Cases marked "UI + browser DevTools" need the developer tools (F12): the Elements tab to edit or delete a form field, the Network tab to read an HTTP status, the Console tab for the one fetch(...) snippet in AUTHZ-11.',
  'Record the result for each case in manual_test_execution.csv (Executed = Y; Status = Pass, Fail or Blocked; Actual result; Evidence file name; Executed by; Date) and save the screenshot under that name in the evidence folder.',
  'If a case fails, add a new defect row to assessment8_testing/defects.csv and put its id in the Defect ID column.',
  'Regenerate this document with python scripts/build_manual_test_document.py: it then shows your recorded results and embeds your evidence screenshots.',
].forEach(t => children.push(bullet(t, 'steps')));
children.push(h2('Status definitions'));
children.push(table([th(['Status', 'Meaning'], [1800, W - 1800]),
  row([cell('Pass', 1800, {bold: true}), cell('The actual result matches the expected result in every respect.', W - 1800)]),
  row([cell('Fail', 1800, {bold: true}), cell('The actual result differs from the expected result. Describe exactly what you saw and raise a defect.', W - 1800)]),
  row([cell('Blocked', 1800, {bold: true}), cell('The case could not be performed (for example a precondition could not be created). Say why.', W - 1800)]),
  row([cell('Not Executed', 1800, {bold: true}), cell('Nobody has performed the case. This is the starting state and must stay unchanged until the case is really executed.', W - 1800)]),
], [1800, W - 1800]));
children.push(para('Never record a result you did not observe. Leave cases you did not run as Not Executed.', {before: 120, bold: true}));

// ---------------------------------------------------------------- 5 index
children.push(h1('5. Case index'));
const iw = [1350, 3250, 1250, 950, 1550, 1556];
children.push(table([th(['Case', 'Scenario', 'Req.', 'Prio.', 'Technique', 'Status'], iw),
  ...data.cases.map(c => row([cell(c.id, iw[0], {bold: true, size: 18}), cell(c.scenario, iw[1], {size: 18}), cell(c.requirement, iw[2], {size: 18}), cell(c.priority, iw[3], {size: 18}),
    cell(c.technique.replace('browser ', ''), iw[4], {size: 18}), cell(c.result.status, iw[5], {size: 18, fill: {Pass: 'E2F0D9', Fail: 'F8D7DA', Blocked: 'FFF2CC'}[c.result.status]})]))], iw));

// ---------------------------------------------------------------- 6 cases
children.push(h1('6. Test cases'));
const modules = [...new Set(data.cases.map(c => c.module))];
const mark = (sel, name) => `[${sel === name ? 'X' : ' '}] ${name}`;
for (const m of modules) {
  children.push(h2(`6.${modules.indexOf(m) + 1} ${m}`, true));
  let first = true;
  for (const c of data.cases.filter(x => x.module === m)) {
    const r = c.result, done = r.status !== 'Not Executed';
    children.push(h3(`${c.id}  -  ${c.scenario}`, !first));
    first = false;
    const iw4 = [1400, 3553, 1400, 3553];
    children.push(table([row([cell('Requirement', iw4[0], {fill: 'EAF0FA', bold: true, size: 18}), cell(c.requirement, iw4[1], {size: 18}), cell('Priority', iw4[2], {fill: 'EAF0FA', bold: true, size: 18}), cell(c.priority, iw4[3], {size: 18})]),
      row([cell('Technique', iw4[0], {fill: 'EAF0FA', bold: true, size: 18}), cell(c.technique, iw4[1], {size: 18}), cell('Module', iw4[2], {fill: 'EAF0FA', bold: true, size: 18}), cell(c.module, iw4[3], {size: 18})])], iw4));
    children.push(para('', {after: 40}));
    children.push(table([
      row([cell('Preconditions', 1800, {fill: 'EAF0FA', bold: true}), cell(c.preconditions || '-', W - 1800)]),
      row([cell('Steps', 1800, {fill: 'EAF0FA', bold: true}), cell(c.steps.map(s => para(s, {after: 40})), W - 1800)], {cantSplit: false}),
      row([cell('Input data', 1800, {fill: 'EAF0FA', bold: true}), cell(c.input || '-', W - 1800)]),
      row([cell('Expected result', 1800, {fill: 'E2F0D9', bold: true}), cell(c.expected, W - 1800)]),
    ], [1800, W - 1800]));
    children.push(para([run('Reference screenshot' + (c.ref.length > 1 ? 's' : '') + ' (expected state, captured by script - not tester evidence)', {bold: true, size: 18, color: '404040'})], {before: 100, after: 20, keepNext: true}));
    for (const ref of c.ref) { children.push(image(ref, ref.h > ref.w ? 210 : 560, ref.h > ref.w ? 400 : 300)); children.push(caption(ref.caption)); }
    const multi = c.ref.length > 1;   // several images: the result box starts on its own page
    children.push(para([run('Result (to be recorded by the tester)' + (multi ? `  -  ${c.id}: ${c.scenario}` : ''), {bold: true, size: multi ? 20 : 18, color: '404040'})], {before: 60, after: 20, keepNext: true, pageBreakBefore: multi}));
    const fillStatus = {Pass: 'E2F0D9', Fail: 'F8D7DA', Blocked: 'FFF2CC'}[r.status];
    const evCell = r.status !== 'Not Executed' && c.evidence ? [image(c.evidence, 560, 360)] : [para(done ? `Evidence file: ${r.evidenceName || '(none recorded)'}` : `Paste your screenshot here  (save it as evidence/${c.id}.png and record that file name)`, {size: 17, italics: true, color: '7F7F7F'})];
    children.push(table([
      row([cell('Actual result', 1800, {fill: 'EAF0FA', bold: true}), cell(done ? r.actual : '', W - 1800)], {height: 900}),
      row([cell('Status', 1800, {fill: 'EAF0FA', bold: true}), cell(['Pass', 'Fail', 'Blocked'].map(n => mark(r.status, n)).join('      ') + (done ? '' : '      (not executed)'), W - 1800, {fill: fillStatus})]),
      row([cell('Executed by / date', 1800, {fill: 'EAF0FA', bold: true}), cell(done ? `${r.by}   /   ${r.date}` : '                                         /', W - 1800)]),
      row([cell('Defect id', 1800, {fill: 'EAF0FA', bold: true}), cell(r.defect || '', W - 1800)]),
      row([cell('Tester evidence', 1800, {fill: 'EAF0FA', bold: true}), cell(evCell, W - 1800)], {height: 1100, cantSplit: false}),
    ], [1800, W - 1800]));
    children.push(para('', {after: 40}));
  }
}

// ---------------------------------------------------------------- 7 summary
children.push(h1('7. Results summary'));
const pri = p => data.cases.filter(c => c.priority === p);
const cnt = (arr, s) => arr.filter(c => c.result.status === s).length;
const mw = [2300, 1400, 1400, 1400, 1700, 1706];
children.push(table([th(['Group', 'Pass', 'Fail', 'Blocked', 'Not executed', 'Total'], mw),
  ...[['All cases', data.cases], ['Priority P1', pri('P1')], ['Priority P2', pri('P2')], ['Priority P3', pri('P3')]].map(([n, a]) => row([cell(n, mw[0], {bold: true}), cell(cnt(a, 'Pass'), mw[1]), cell(cnt(a, 'Fail'), mw[2]), cell(cnt(a, 'Blocked'), mw[3]), cell(cnt(a, 'Not Executed'), mw[4]), cell(a.length, mw[5])]))], mw));
children.push(para(executed === 0 ? 'No case has been executed yet; the table will fill in when results are recorded and this document is regenerated.' : '', {before: 100, italics: true}));

// ---------------------------------------------------------------- 8 defects
children.push(h1('8. Defects found during manual testing'));
const fails = data.cases.filter(c => c.result.status === 'Fail');
const dw = [1000, 3100, 1200, 4606];
const blank = n => Array.from({length: n}, () => row([cell('', dw[0]), cell('', dw[1]), cell('', dw[2]), cell('', dw[3])], {height: 520}));
children.push(table([th(['Case', 'Scenario', 'Defect id', 'What was observed'], dw),
  ...(fails.length ? fails.map(c => row([cell(c.id, dw[0]), cell(c.scenario, dw[1]), cell(c.result.defect || '', dw[2]), cell(c.result.actual, dw[3])])) : blank(5))], dw));

// ---------------------------------------------------------------- 9 sign-off
children.push(h1('9. Sign-off'));
children.push(table([th(['', 'Name', 'Signature', 'Date'], [2300, 3000, 2606, 2000]),
  row([cell('Tester', 2300, {bold: true}), cell('', 3000), cell('', 2606), cell('', 2000)], {height: 700}),
  row([cell('Reviewer', 2300, {bold: true}), cell('', 3000), cell('', 2606), cell('', 2000)], {height: 700})], [2300, 3000, 2606, 2000]));

// ---------------------------------------------------------------- appendix
children.push(h1('Appendix A. How the reference screenshots were made'));
children.push(para('The reference screenshots were produced by scripts/browser/capture_manual_case_screens.mjs. It starts the demo server on a fresh database (no allocations, lockout limit 5), walks the cases in the order of this document with a headless Chrome browser at 1366 x 800 pixels (390 x 844 for the mobile cases) and saves the decisive screen of each case.'));
children.push(para('Where a case needs developer tools (editing a field, removing a CSRF token) the script performs the same change, and for drop-down lists it expands the list so the options are visible in the picture. The images therefore show what a correct application displays. They do not replace a tester\'s own evidence and are not proof that a person ran the case.'));
children.push(para('Dates inside the screenshots (for example default start dates) are the dates on which the script ran and will differ from the dates on your screen.'));

const doc = new Document({
  creator: 'Hostel Management System project', title: 'Manual Test Document - Room Allocation module', description: 'BCSE301P Assessment 8',
  styles: {default: {document: {run: {font: FONT, size: 20}}}, paragraphStyles: [
    {id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: {size: 30, bold: true, font: FONT}, paragraph: {spacing: {before: 300, after: 140}, outlineLevel: 0}},
    {id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: {size: 25, bold: true, font: FONT}, paragraph: {spacing: {before: 260, after: 100}, outlineLevel: 1}},
    {id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: {size: 22, bold: true, font: FONT}, paragraph: {spacing: {before: 120, after: 60}, outlineLevel: 2}},
  ]},
  numbering: {config: [
    {reference: 'bullets', levels: [{level: 0, format: LevelFormat.BULLET, text: '\u2022', alignment: AlignmentType.LEFT, style: {paragraph: {indent: {left: 540, hanging: 270}}}}]},
    {reference: 'steps', levels: [{level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: {paragraph: {indent: {left: 540, hanging: 360}}}}]},
  ]},
  sections: [{
    properties: {page: {size: {width: 11906, height: 16838}, margin: {top: 1100, bottom: 1000, left: 1000, right: 1000}}},
    headers: {default: new Header({children: [para([run('Manual Test Document  |  Room Allocation module  |  BCSE301P Assessment 8', {size: 16, color: '7F7F7F'})], {align: AlignmentType.RIGHT, after: 0})]})},
    footers: {default: new Footer({children: [new Paragraph({alignment: AlignmentType.CENTER, children: [new TextRun({text: 'Page ', font: FONT, size: 16, color: '7F7F7F'}), new TextRun({children: [PageNumber.CURRENT], font: FONT, size: 16, color: '7F7F7F'}), new TextRun({text: ' of ', font: FONT, size: 16, color: '7F7F7F'}), new TextRun({children: [PageNumber.TOTAL_PAGES], font: FONT, size: 16, color: '7F7F7F'}), new TextRun({text: `    |    Status: ${status}`, font: FONT, size: 16, color: '7F7F7F'})]})]})},
    children,
  }],
});
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(OUT, buf); console.log('docx written', (buf.length / 1048576).toFixed(1) + ' MB'); });
