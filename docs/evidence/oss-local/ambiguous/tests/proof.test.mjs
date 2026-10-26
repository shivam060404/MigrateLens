// Generated proof pack executes only when the caller runs `prove` or `verify` locally/in CI.
// This is a test harness, not an isolation boundary for consumer code.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import * as original from '../source.ts';
import * as repaired from '../candidate.ts';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const scenario = JSON.parse(readFileSync(join(root, 'scenario.json'), 'utf8')).scenario;
const oldSpec = JSON.parse(readFileSync(join(root, 'old-api.json'), 'utf8'));
const newSpec = JSON.parse(readFileSync(join(root, 'new-api.json'), 'utf8'));

function mock(spec) {
  const details = Object.entries(spec.paths).find(([, item]) => item.get?.operationId === 'getCustomer');
  const list = Object.entries(spec.paths).find(([, item]) => item.get?.operationId === 'listCustomers');
  assert.ok(details && list, 'registered GET operations required');
  const detailPrefix = details[0].replace('{id}', '');
  const listPath = list[0];
  const queryName = list[1].get.parameters.find(p => p.in === 'query').name;
  const properties = details[1].get.responses['200'].content['application/json'].schema.properties;
  return async (address) => {
    const url = new URL(address);
    let status = 200;
    let body;
    if (url.pathname === listPath) {
      if ([...url.searchParams.keys()].some(key => key !== queryName)) {
        status = 400; body = { error: 'unknown query parameter' };
      } else {
        body = { items: [{ id: 'ada' }, { id: 'null' }] };
      }
    } else if (url.pathname.startsWith(detailPrefix)) {
      const id = decodeURIComponent(url.pathname.slice(detailPrefix.length));
      if (!['ada', 'null', 'missing'].includes(id)) {
        status = 404; body = { error: 'missing' };
      } else {
        body = { id, tier: 'standard', unrelated: { name: 'unrelated-company' } };
        if ('profile' in properties) body.profile = id === 'missing' ? {} : { displayName: id === 'null' ? null : 'Ada Lovelace' };
        else if ('name' in properties && id !== 'missing') body.name = id === 'null' ? null : 'Ada Lovelace';
      }
    } else {
      status = 404; body = { error: 'missing' };
    }
    return { status, ok: status >= 200 && status < 300, json: async () => body };
  };
}

async function targeted(module, spec) {
  globalThis.fetch = mock(spec);
  try {
    if (scenario === 'query') {
      assert.deepEqual(await module.listCustomers('http://fixture.invalid', 2), ['ada', 'null']);
    } else {
      const value = await module.getCustomer('http://fixture.invalid', 'ada');
      assert.equal(value?.name, 'Ada Lovelace');
      assert.equal(value?.unrelatedName, 'unrelated-company');
    }
    return true;
  } catch {
    return false;
  }
}

test('BASELINE_OLD', async () => {
  assert.equal(await targeted(original, oldSpec), true);
});
test('REPRO_NEW', async () => {
  assert.equal(await targeted(original, newSpec), false);
});
test('REPAIR_NEW', async () => {
  assert.equal(await targeted(repaired, newSpec), true);
});
test('REGRESSION', async () => {
  globalThis.fetch = mock(newSpec);
  const missing = await repaired.getCustomer('http://fixture.invalid', 'missing');
  assert.equal(missing?.name, null);
  assert.equal(missing?.unrelatedName, 'unrelated-company');
  const absent = await repaired.getCustomer('http://fixture.invalid', 'does-not-exist');
  assert.equal(absent, null);
  if (scenario === 'query') {
    assert.deepEqual(await repaired.listCustomers('http://fixture.invalid'), ['ada', 'null']);
  } else {
    assert.deepEqual(await repaired.listCustomers('http://fixture.invalid', 2), ['ada', 'null']);
  }
});
