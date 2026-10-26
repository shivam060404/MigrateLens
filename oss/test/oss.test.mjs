import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync, mkdirSync, symlinkSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { prepare } from '../dist/engine.js';
import { parseContract } from '../dist/contracts.js';
import { applyRecipe } from '../dist/recipes.js';
import { prove, verify } from '../dist/proof.js';
import { analyzeRegistered, proposeRegisteredPath } from '../dist/registered.js';
import { previewRegistered, proveRegistered, verifyRegistered } from '../dist/registered-proof.js';

function temporary(fn) {
  const root = mkdtempSync(join(tmpdir(), 'migratelens-oss-test-'));
  try { return fn(root); }
  finally { rmSync(root, { recursive: true, force: true }); }
}

test('three supported changes have bounded plans and one-line AST patches', () => {
  for (const scenario of ['path', 'field', 'query']) {
    const prepared = prepare(scenario);
    assert.equal(prepared.findings.length, 1);
    assert.ok(prepared.recipe?.semanticEvidence);
    assert.match(prepared.patch, /^--- a\/client\.ts\n\+\+\+ b\/client\.ts\n/);
    assert.notEqual(prepared.source, prepared.candidate);
  }
});

test('ambiguous semantics and docs-only changes produce empty patches', () => {
  const ambiguous = prepare('ambiguous');
  assert.equal(ambiguous.preliminaryVerdict, 'NEEDS_CLARIFICATION');
  assert.equal(ambiguous.recipe, null);
  assert.equal(ambiguous.patch, '');
  const unchanged = prepare('unchanged');
  assert.equal(unchanged.preliminaryVerdict, 'ANALYSIS_ONLY');
  assert.deepEqual(unchanged.findings, []);
  assert.equal(unchanged.patch, '');
});

test('unresolved refs and duplicate target calls fail closed', () => {
  assert.throws(() => parseContract(Buffer.from('{"openapi":"3.1.0","paths":{},"$ref":"https://example.test"}')), /Referenced contracts/);
  assert.throws(() => parseContract(Buffer.from('{"openapi":"3.1.0","paths":{},"$\\u0072ef":"https://example.test"}')), /Referenced contracts/);
  const prepared = prepare('path');
  const duplicate = prepared.source.replace(
    '  const response = await fetch(`${base}/v1/customers/${encodeURIComponent(id)}`);',
    '  await fetch(`${base}/v1/customers/${encodeURIComponent(id)}`);\n  const response = await fetch(`${base}/v1/customers/${encodeURIComponent(id)}`);',
  );
  assert.throws(() => applyRecipe(duplicate, prepared.recipe), /Exactly one approved AST edit/);
});

test('local proof executes all declared checks for supported fixtures', () => temporary((root) => {
  for (const scenario of ['path', 'field', 'query']) {
    const { folder, evidence } = prove(scenario, root);
    assert.equal(evidence.verdict, 'VERIFIED_FOR_DECLARED_SCOPE');
    assert.deepEqual(evidence.checks.map(check => check.id), ['BASELINE_OLD', 'REPRO_NEW', 'REPAIR_NEW', 'REGRESSION', 'STATIC', 'POLICY']);
    assert.ok(evidence.checks.every(check => check.outcome === 'PASS'));
    assert.equal(verify(join(folder, 'manifest.json')).fingerprint, evidence.fingerprint);
  }
}));

test('wrong patch remains type-correct but fails repaired behavior', () => temporary((root) => {
  const { folder, evidence } = prove('path', root, true);
  assert.equal(evidence.verdict, 'VALIDATION_FAILED');
  const checks = Object.fromEntries(evidence.checks.map(check => [check.id, check.outcome]));
  assert.equal(checks.STATIC, 'PASS');
  assert.equal(checks.POLICY, 'PASS');
  assert.equal(checks.REPAIR_NEW, 'FAIL');
  assert.equal(verify(join(folder, 'manifest.json')).verdict, 'VALIDATION_FAILED');
}));

test('proof revalidation rejects candidate, test and report tampering', () => temporary((root) => {
  for (const file of ['candidate.ts', 'tests/proof.test.mjs', 'report.md', 'manifest.json']) {
    const { folder } = prove('path', root);
    const path = join(folder, file);
    writeFileSync(path, `${readFileSync(path, 'utf8')}\n// tampered\n`);
    assert.throws(() => verify(join(folder, 'manifest.json')));
  }
}));

test('unexpected proof artifact fails policy revalidation', () => temporary((root) => {
  const { folder } = prove('path', root);
  writeFileSync(join(folder, 'unexpected-secret.txt'), 'synthetic canary');
  assert.throws(() => verify(join(folder, 'manifest.json')), /changed or stale/);
}));

function registration(root, overrides = {}) {
  mkdirSync(join(root, 'src'));
  mkdirSync(join(root, 'specs'));
  writeFileSync(join(root, 'src', 'client.ts'), readFileSync(new URL('../fixtures/client.ts', import.meta.url)));
  writeFileSync(join(root, 'specs', 'old.json'), readFileSync(new URL('../fixtures/path-old.json', import.meta.url)));
  writeFileSync(join(root, 'specs', 'new.json'), readFileSync(new URL('../fixtures/path-new.json', import.meta.url)));
  const config = {
    schemaVersion: 1, provider: 'fictional-northstar', oldSpec: 'specs/old.json',
    newSpec: 'specs/new.json', sourceFiles: ['src/client.ts'],
    mappings: [{
      ruleId: 'ML-PATH-001', operation: 'getCustomer',
      before: '/v1/customers/{id}', after: '/v2/customers/{id}',
      evidenceRef: 'fixture-mapping-v1', revision: '1',
    }],
    ...overrides,
  };
  const path = join(root, 'migratelens.json');
  writeFileSync(path, JSON.stringify(config));
  return path;
}

test('registered local scan binds exact files and classifies direct fetch without a patch claim', () => temporary((root) => {
  const config = registration(root);
  const result = analyzeRegistered(config);
  assert.equal(result.verdict, 'ANALYSIS_ONLY');
  assert.equal(result.mappingDeclared, true);
  assert.equal(result.findings[0].ruleId, 'ML-PATH-001');
  assert.deepEqual(result.usage, [{ ruleId: 'ML-PATH-001', path: 'src/client.ts', classification: 'confirmed' }]);
  assert.equal(result.patch, '');
  assert.match(result.identities.sources['src/client.ts'], /^sha256:[0-9a-f]{64}$/);
  const first = result.identities.sources['src/client.ts'];
  writeFileSync(join(root, 'src', 'client.ts'), readFileSync(join(root, 'src', 'client.ts'), 'utf8') + '\n// changed');
  assert.notEqual(analyzeRegistered(config).identities.sources['src/client.ts'], first);
}));

test('registered path proposal changes one declared AST line without writing source', () => temporary((root) => {
  const config = registration(root);
  const sourcePath = join(root, 'src', 'client.ts');
  const original = readFileSync(sourcePath, 'utf8');
  const proposal = proposeRegisteredPath(config);
  assert.equal(proposal.verdict, 'ANALYSIS_ONLY');
  assert.equal(proposal.changedFiles, 1);
  assert.equal(proposal.changedLines, 1);
  assert.match(proposal.patch, /^--- a\/src\/client\.ts\n\+\+\+ b\/src\/client\.ts\n/);
  assert.match(proposal.patch, /\+.*\/v2\/customers\//);
  assert.equal(readFileSync(sourcePath, 'utf8'), original);
  registrationWrite(config, { mappings: [] });
  assert.throws(() => proposeRegisteredPath(config), /declared, confirmed/);
}));

test('registered analysis abstains on missing approval, uncertain usage and unsupported contracts', () => temporary((root) => {
  const config = registration(root, { mappings: [] });
  assert.equal(analyzeRegistered(config).verdict, 'NEEDS_CLARIFICATION');
  registrationWrite(config, { mappings: [{
    ruleId: 'ML-PATH-001', operation: 'getCustomer', before: '/v1/customers/{id}',
    after: '/v2/customers/{id}', evidenceRef: 'fixture-mapping-v1', revision: '1',
  }] });
  writeFileSync(join(root, 'src', 'client.ts'), 'const message = "/v1/customers/";');
  assert.equal(analyzeRegistered(config).usage[0].classification, 'candidate');
  assert.equal(analyzeRegistered(config).verdict, 'NEEDS_CLARIFICATION');
  writeFileSync(join(root, 'specs', 'new.json'), JSON.stringify({ openapi: '3.1.0', paths: {}, $ref: 'https://example.test/secret' }));
  assert.equal(analyzeRegistered(config).verdict, 'UNSUPPORTED');
}));

function registrationWrite(path, changes) {
  writeFileSync(path, JSON.stringify({ ...JSON.parse(readFileSync(path, 'utf8')), ...changes }));
}

test('registered paths reject traversal, symlinks, duplicate sources and unknown keys', () => temporary((root) => {
  const config = registration(root);
  registrationWrite(config, { sourceFiles: ['../outside.ts'] });
  assert.throws(() => analyzeRegistered(config), /outside admitted scope/);
  registrationWrite(config, { sourceFiles: ['src/client.ts', 'src/client.ts'] });
  assert.throws(() => analyzeRegistered(config), /Duplicate source/);
  registrationWrite(config, { sourceFiles: ['src/link.ts'] });
  symlinkSync(join(root, 'src', 'client.ts'), join(root, 'src', 'link.ts'));
  assert.throws(() => analyzeRegistered(config), /symlink/);
  mkdirSync(join(root, '.github'));
  writeFileSync(join(root, '.github', 'workflow.ts'), 'export const value = 1;');
  registrationWrite(config, { sourceFiles: ['.github/workflow.ts'] });
  assert.throws(() => analyzeRegistered(config), /protected by patch policy/);
  registrationWrite(config, { sourceFiles: ['src/client.ts'], extra: true });
  assert.throws(() => analyzeRegistered(config), /Invalid registration keys/);
}));

test('CLI admits registered scan and patch proposal but refuses registered proof', () => {
  const config = new URL('../fixtures/registered-path.json', import.meta.url).pathname;
  const cli = new URL('../dist/cli.js', import.meta.url).pathname;
  const scan = spawnSync(process.execPath, [cli, 'scan', '--config', config], { encoding: 'utf8' });
  assert.equal(scan.status, 0, scan.stderr);
  assert.equal(JSON.parse(scan.stdout).usage[0].classification, 'confirmed');
  const patch = spawnSync(process.execPath, [cli, 'patch', '--config', config], { encoding: 'utf8' });
  assert.equal(patch.status, 0, patch.stderr);
  assert.match(JSON.parse(patch.stdout).patch, /\+.*\/v2\/customers\//);
  const prove = spawnSync(process.execPath, [cli, 'prove', '--config', config], { encoding: 'utf8' });
  assert.equal(prove.status, 2);
  assert.match(prove.stderr, /Invalid proof vectors/);
});

test('registered direct-fetch proof executes six local checks and revalidates exact inputs', () => temporary((root) => {
  const config = new URL('../fixtures/registered-path-proof.json', import.meta.url).pathname;
  const { folder, evidence } = proveRegistered(config, root);
  assert.equal(evidence.verdict, 'LOCAL_CHECKS_PASSED');
  assert.deepEqual(evidence.checks.map(check => check.id), ['BASELINE_OLD', 'REPRO_NEW', 'REPAIR_NEW', 'REGRESSION', 'STATIC', 'POLICY']);
  assert.ok(evidence.checks.every(check => check.outcome === 'PASS'));
  assert.equal(verifyRegistered(join(folder, 'manifest.json'), config).fingerprint, evidence.fingerprint);
  const preview = previewRegistered(join(folder, 'manifest.json'), config);
  assert.match(preview, /Draft PR preview — publication blocked/);
  assert.match(preview, /LOCAL_CHECKS_PASSED|Evidence fingerprint/);
  assert.match(preview, /Do not publish this as a verified migration/);
  const cli = new URL('../dist/cli.js', import.meta.url).pathname;
  const cliPreview = spawnSync(process.execPath, [cli, 'preview', '--config', config, '--manifest', join(folder, 'manifest.json')], { encoding: 'utf8' });
  assert.equal(cliPreview.status, 0, cliPreview.stderr);
  assert.equal(cliPreview.stdout, preview);
  const publish = spawnSync(process.execPath, [cli, 'publish', '--config', config, '--manifest', join(folder, 'manifest.json')], { encoding: 'utf8' });
  assert.equal(publish.status, 2);
  assert.match(publish.stderr, /Live publication is gated/);
  writeFileSync(join(folder, 'candidate.ts'), readFileSync(join(folder, 'candidate.ts'), 'utf8').replace('/v2/customers/', '/v9/customers/'));
  const wrong = spawnSync(process.execPath, ['--experimental-strip-types', '--disable-warning=ExperimentalWarning', '--test', join(folder, 'tests', 'proof.test.mjs')], {
    cwd: folder, encoding: 'utf8', timeout: 15_000, maxBuffer: 100_000,
    env: { PATH: process.env.PATH ?? '', HOME: folder, TMPDIR: tmpdir() },
  });
  assert.match(`${wrong.stdout}\n${wrong.stderr}`, /not ok \d+ - REPAIR_NEW/);
  assert.throws(() => verifyRegistered(join(folder, 'manifest.json'), config), /stale/);
  assert.throws(() => previewRegistered(join(folder, 'manifest.json'), config), /stale/);
}));

test('registered proof rejects changed GET semantics and invalid local test vectors', () => temporary((root) => {
  const config = registration(root);
  const current = JSON.parse(readFileSync(config, 'utf8'));
  current.proof = JSON.parse(readFileSync(new URL('../fixtures/registered-path-proof.json', import.meta.url))).proof;
  writeFileSync(config, JSON.stringify(current));
  assert.equal(proveRegistered(config, join(root, 'output')).evidence.verdict, 'LOCAL_CHECKS_PASSED');
  const altered = JSON.parse(readFileSync(join(root, 'specs', 'new.json'), 'utf8'));
  altered.paths['/v2/customers/{id}'].get.responses['200'].description = 'Changed response meaning';
  writeFileSync(join(root, 'specs', 'new.json'), JSON.stringify(altered));
  assert.throws(() => proveRegistered(config, join(root, 'output')), /otherwise identical GET operations/);
  writeFileSync(join(root, 'specs', 'new.json'), readFileSync(new URL('../fixtures/path-new.json', import.meta.url)));
  current.proof.cases[0].args[0] = 'https://production.example';
  writeFileSync(config, JSON.stringify(current));
  assert.throws(() => proveRegistered(config, join(root, 'output')), /Invalid proof case/);
  current.proof.cases[0].args[0] = 'http://fixture.invalid';
  current.proof.cases[0].response.tier = 123;
  writeFileSync(config, JSON.stringify(current));
  assert.throws(() => proveRegistered(config, join(root, 'output')), /does not match supported OpenAPI schema/);
}));
