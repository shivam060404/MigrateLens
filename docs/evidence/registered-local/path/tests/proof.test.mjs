// Runs in the caller's environment. This is a targeted local mock, not a sandbox.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import * as original from '../source.ts';
import * as repaired from '../candidate.ts';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const config = JSON.parse(readFileSync(join(root, 'registration.json'), 'utf8'));
const oldSpec = JSON.parse(readFileSync(join(root, 'old-api.json'), 'utf8'));
const newSpec = JSON.parse(readFileSync(join(root, 'new-api.json'), 'utf8'));
const vectors = config.proof.cases;
const operationId = config.mappings[0].operation;

function pathFor(spec, params) {
  const route = Object.entries(spec.paths).find(([, item]) => item.get?.operationId === operationId)?.[0];
  assert.ok(route, 'registered GET operation missing');
  return route.replace(/\{([^}]+)\}/g, (_, key) => {
    assert.equal(typeof params[key], 'string', `missing path parameter ${key}`);
    return encodeURIComponent(params[key]);
  });
}

async function targeted(module, spec, vector) {
  const expectedPath = pathFor(spec, vector.pathParams);
  const previous = globalThis.fetch;
  let requests = 0;
  let matched = false;
  const attempted = [];
  globalThis.fetch = async (address, options) => {
    requests += 1;
    const url = new URL(address);
    const method = options?.method ?? 'GET';
    attempted.push({ origin: url.origin, path: url.pathname, method });
    const found = url.origin === 'http://fixture.invalid' && url.pathname === expectedPath &&
      url.search === '' && url.hash === '' && method === 'GET' && options?.body === undefined;
    matched ||= found;
    return { status: found ? 200 : 404, ok: found, json: async () => found ? vector.response : { error: 'missing' } };
  };
  try {
    const entry = module[config.proof.exportName];
    assert.equal(typeof entry, 'function', 'registered export missing');
    assert.deepEqual(await entry(...vector.args), vector.expected);
    assert.equal(requests, 1, 'proof must make exactly one request');
    assert.equal(matched, true, 'proof must reach the declared endpoint');
    return { passed: true, requests, attempted };
  } catch {
    return { passed: false, requests, attempted };
  } finally {
    globalThis.fetch = previous;
  }
}

test('BASELINE_OLD', async () => {
  assert.equal((await targeted(original, oldSpec, vectors[0])).passed, true);
});
test('REPRO_NEW', async () => {
  const result = await targeted(original, newSpec, vectors[0]);
  assert.equal(result.passed, false);
  assert.equal(result.requests, 1, 'reproduction must execute exactly one request');
  assert.deepEqual(result.attempted, [{
    origin: 'http://fixture.invalid', path: pathFor(oldSpec, vectors[0].pathParams), method: 'GET',
  }], 'reproduction must call the old route on the fixture origin with GET');
  assert.notEqual(result.attempted[0].path, pathFor(newSpec, vectors[0].pathParams), 'old and new routes must differ');
});
test('REPAIR_NEW', async () => {
  assert.equal((await targeted(repaired, newSpec, vectors[0])).passed, true);
});
test('REGRESSION', async () => {
  assert.equal((await targeted(repaired, newSpec, vectors[1])).passed, true);
});
