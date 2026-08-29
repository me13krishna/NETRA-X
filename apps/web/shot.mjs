import { chromium } from 'playwright';
const OUT = process.argv[2];
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1600, height: 1000 } });
p.on('pageerror', e => console.log('  [page error]', String(e).slice(0,140)));
await p.goto('http://127.0.0.1:3000', { waitUntil: 'networkidle' });
await p.fill('input[type=email]', 'analyst@netra-x.local');
await p.fill('input[type=password]', 'AnalystPass2026!');
await p.click('button[type=submit]');
await p.waitForTimeout(3500);
await p.screenshot({ path: `${OUT}/dashboard.png` });
console.log('  captured dashboard');
const btn = p.locator('button:has-text("Attribution")').first();
if (await btn.count()) { await btn.click(); await p.waitForTimeout(2500); await p.screenshot({ path: `${OUT}/attribution.png` }); console.log('  captured attribution'); }
await b.close();
