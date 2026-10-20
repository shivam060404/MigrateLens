import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { analyzeSource } from './recipes.mjs';
const source = fs.readFileSync(new URL('../../fixtures/consumers/northstar/src/integrations/customer/client.ts', import.meta.url), 'utf8');
for (const [scenario, expected] of [['path', '/v2/customers/'], ['field', 'customer.profile?.displayName'], ['query', 'query.set("limit"']]) {
  test(`${scenario} preserves unrelated fields and produces one edit`, () => {
    const result = analyzeSource(source, scenario, 'repair');
    assert.equal(result.changes, 1);
    assert.ok(result.source?.includes(expected));
    assert.ok(result.source?.includes('customer.unrelated.name'));
  });
}
test('duplicate supported calls abstain instead of partially transforming', () => {
  const call = 'const response = await fetch(`${base}/v1/customers/${encodeURIComponent(id)}`);';
  const modified = source.replace(call, `${call}\n await fetch(\`\${base}/v1/customers/\${encodeURIComponent(id)}\`);`);
  assert.throws(() => analyzeSource(modified, 'path', 'repair'), /exactly one/);
});
test('unknown modes cannot select a recipe', () => {
  assert.throws(() => analyzeSource(source, 'field', 'execute'), /Unsupported/);
});
test('dynamic calls remain visible as unresolved', () => {
  const result = analyzeSource('export function f(url) { return fetch(url); }', 'path');
  assert.equal(result.unresolved.length, 1);
});
