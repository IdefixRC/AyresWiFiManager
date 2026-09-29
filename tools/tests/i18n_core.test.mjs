// Unit tests for the shared portal i18n helpers (the i18n-core block in data/*.html).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const CORE_RE = /\/\* i18n-core:begin \*\/[\s\S]*?\/\* i18n-core:end \*\//;

function loadCore(page) {
  const html = readFileSync(path.join(ROOT, page), 'utf8');
  const match = html.match(CORE_RE);
  assert.ok(match, `no i18n-core block in ${page}`);
  return new Function(`${match[0]}\nreturn AWMI18n;`)();
}

const I = loadCore('data/index.html');
const SUPPORTED = ['en', 'es', 'de'];
const pick = (browserLangs, extra = {}) =>
  I.resolve({ supported: SUPPORTED, urlLang: null, urlAllowed: true, configured: 'auto', browserLangs, ...extra });

test('primary() keeps only the language part, lower-cased', () => {
  assert.equal(I.primary('de-CH'), 'de');
  assert.equal(I.primary('EN_us'), 'en');
  assert.equal(I.primary(''), '');
  assert.equal(I.primary(undefined), '');
});

test('AUTO picks the first supported browser language', () => {
  assert.equal(pick(['es-AR']), 'es');
  assert.equal(pick(['en-US']), 'en');
  assert.equal(pick(['de-CH', 'en']), 'de');
  assert.equal(pick(['pt-BR', 'es']), 'es');
});

test('AUTO falls back to English', () => {
  assert.equal(pick(['fr-FR', 'it']), 'en');
  assert.equal(pick([]), 'en');
});

test('a missing /info behaves like AUTO', () => {
  assert.equal(pick(['es-AR'], { configured: null }), 'es');
  assert.equal(pick([], { configured: undefined }), 'en');
});

test('a fixed language beats the browser', () => {
  assert.equal(pick(['en-US'], { configured: 'de' }), 'de');
  assert.equal(pick(['en-US'], { configured: 'DE' }), 'de');
});

test('?lang wins only when allowed and supported', () => {
  assert.equal(pick(['en-US'], { configured: 'de', urlLang: 'es' }), 'es');
  assert.equal(pick(['en-US'], { configured: 'de', urlLang: 'es', urlAllowed: false }), 'de');
  assert.equal(pick(['en-US'], { configured: 'de', urlLang: 'xx' }), 'de');
});

test('an unsupported configured language falls back to AUTO', () => {
  assert.equal(pick(['es'], { configured: 'fr' }), 'es');
});

test('format() fills known placeholders and keeps unknown ones', () => {
  assert.equal(I.format('Networks found: {n}', { n: 3 }), 'Networks found: 3');
  assert.equal(I.format('Hi {name}', {}), 'Hi {name}');
  assert.equal(I.format('No vars', undefined), 'No vars');
});

test('lookup() falls back to English, then to the key', () => {
  const tables = { en: { a: 'A', b: 'B' }, de: { a: 'Ä' } };
  assert.equal(I.lookup(tables, 'de', 'a'), 'Ä');
  assert.equal(I.lookup(tables, 'de', 'b'), 'B');
  assert.equal(I.lookup(tables, 'de', 'zzz'), 'zzz');
  assert.equal(I.lookup(tables, 'xx', 'a'), 'A');
});

test('browserLangs() prefers navigator.languages', () => {
  assert.deepEqual(I.browserLangs({ languages: ['de-CH', 'en'], language: 'de-CH' }), ['de-CH', 'en']);
  assert.deepEqual(I.browserLangs({ languages: [], language: 'es-AR' }), ['es-AR']);
  assert.deepEqual(I.browserLangs({}), []);
  assert.deepEqual(I.browserLangs(undefined), []);
});
