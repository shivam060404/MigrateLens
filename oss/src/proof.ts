import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { canonical, hash, prepare } from './engine.js';
import type { Check, EvidenceManifest, Scenario, Verdict } from './model.js';

const here = dirname(fileURLToPath(import.meta.url));
const template = join(here, '..', 'templates', 'proof.test.mjs');
const require = createRequire(import.meta.url);
const tsc = require.resolve('typescript/bin/tsc');
const CHECKS = ['BASELINE_OLD', 'REPRO_NEW', 'REPAIR_NEW', 'REGRESSION'] as const;

function runChecks(folder: string, hasRecipe: boolean): Check[] {
  if (!hasRecipe) return [];
  const testFile = join(folder, 'tests', 'proof.test.mjs');
  const guarded = ['source.ts', 'candidate.ts', 'old-api.json', 'new-api.json', 'tests/proof.test.mjs'];
  const before = guarded.map((file) => hash(readFileSync(join(folder, file))));
  const testRun = spawnSync(process.execPath, ['--experimental-strip-types', '--disable-warning=ExperimentalWarning', '--test', testFile], {
    cwd: folder, encoding: 'utf8', timeout: 15_000, maxBuffer: 100_000,
    env: { PATH: process.env.PATH ?? '', HOME: folder, TMPDIR: tmpdir() },
  });
  const transcript = `${testRun.stdout ?? ''}\n${testRun.stderr ?? ''}`;
  const checks: Check[] = CHECKS.map((id) => ({
    id,
    outcome: new RegExp(`^ok \\d+ - ${id}$`, 'm').test(transcript) ? 'PASS' :
      new RegExp(`^not ok \\d+ - ${id}$`, 'm').test(transcript) ? 'FAIL' : 'ERROR',
    reason: testRun.error ? `${testRun.error.name}: proof test unavailable` : 'Executed customer-local mock contract test',
  }));
  if (testRun.status !== 0 && checks.every((check) => check.outcome === 'PASS')) {
    checks[0] = { id: 'BASELINE_OLD', outcome: 'ERROR', reason: 'Proof process exited without a trustworthy passing test run' };
  }
  const staticRun = spawnSync(process.execPath, [tsc, '--noEmit', '--strict', '--skipLibCheck', '--target', 'ES2022', '--lib', 'ES2022,DOM', 'candidate.ts'], {
    cwd: folder, encoding: 'utf8', timeout: 15_000, maxBuffer: 30_000,
    env: { PATH: process.env.PATH ?? '', HOME: folder, TMPDIR: tmpdir() },
  });
  checks.push({ id: 'STATIC', outcome: staticRun.error ? 'ERROR' : staticRun.status === 0 ? 'PASS' : 'FAIL', reason: 'Executed strict TypeScript compiler on candidate' });
  const source = readFileSync(join(folder, 'source.ts'), 'utf8');
  const candidate = readFileSync(join(folder, 'candidate.ts'), 'utf8');
  const patch = readFileSync(join(folder, 'repair.patch'), 'utf8');
  const changedLines = source.split('\n').filter((line, index) => line !== candidate.split('\n')[index]).length;
  const after = guarded.map((file) => hash(readFileSync(join(folder, file))));
  const intact = before.every((value, index) => value === after[index]);
  const allowedTop = new Set(['source.ts', 'candidate.ts', 'repair.patch', 'old-api.json', 'new-api.json', 'scenario.json', 'tests', 'manifest.json', 'report.md']);
  const clean = readdirSync(folder).every((name) => allowedTop.has(name)) &&
    readdirSync(join(folder, 'tests')).join(',') === 'proof.test.mjs';
  checks.push({ id: 'POLICY', outcome: intact && clean && changedLines === 1 && patch.startsWith('--- a/client.ts\n+++ b/client.ts\n') ? 'PASS' : 'FAIL', reason: 'Approved single-line change, immutable proof inputs and no extra artifact files' });
  return checks;
}

function decision(checks: Check[], fallback: Verdict | null): Verdict {
  if (fallback) return fallback;
  return checks.length === 6 && checks.every((check) => check.outcome === 'PASS') ? 'VERIFIED_FOR_DECLARED_SCOPE' : 'VALIDATION_FAILED';
}

function identities(folder: string, scenario: Scenario): Record<string, string> {
  const prepared = prepare(scenario);
  const git = spawnSync('git', ['rev-parse', 'HEAD'], {
    cwd: process.cwd(), encoding: 'utf8', timeout: 3_000, maxBuffer: 1_000,
  });
  const checkoutCommit = git.stdout?.trim();
  if (git.status !== 0 || !checkoutCommit || !/^[0-9a-f]{40}$/.test(checkoutCommit)) {
    throw new Error('A Git checkout commit is required for a proof claim');
  }
  const files: Record<string, string> = {
    source: 'source.ts', candidate: 'candidate.ts', patch: 'repair.patch',
    old_contract: 'old-api.json', new_contract: 'new-api.json', test_suite: 'tests/proof.test.mjs',
  };
  const result: Record<string, string> = {};
  for (const [key, file] of Object.entries(files)) result[key] = hash(readFileSync(join(folder, file)));
  result.recipe = hash(canonical(prepared.recipe));
  result.findings = hash(canonical(prepared.findings));
  result.policy = hash(canonical({ allowedPath: 'client.ts', maxChangedLines: 1, noPublication: true }));
  result.implementation = hash([
    ...['contracts.js', 'recipes.js', 'engine.js', 'proof.js'].map((file) => readFileSync(join(here, file))),
    readFileSync(join(here, '..', 'package.json')),
  ].reduce((all, part) => Buffer.concat([all, part]), Buffer.alloc(0)));
  result.runner = `node:${process.version};typescript:5.9.3;ts-morph:26.0.0;caller-local-or-ci-unattested`;
  result.source_path = 'fictional:northstar/client.ts';
  result.checkout_commit = checkoutCommit;
  result.candidate_tree = hash(canonical({ path: 'client.ts', content: result.candidate }));
  result.scenario = hash(readFileSync(join(folder, 'scenario.json')));
  return result;
}

function manifest(folder: string, scenario: Scenario, checks: Check[], fallback: Verdict | null): EvidenceManifest {
  const body = {
    schemaVersion: 'oss-1' as const,
    classification: 'fictional development fixture; unsigned local or CI evidence' as const,
    scenario,
    verdict: decision(checks, fallback),
    identities: identities(folder, scenario),
    checks,
    limitations: [
      'Fictional registered fixture only; no general repository coverage claim.',
      'Mock checks execute in the caller environment and are not a security sandbox.',
      'Unsigned local manifest is not authenticated CI provenance or publication approval.',
      'Structural OpenAPI subset only; pinned oasdiff integration remains pending.',
    ],
  };
  return { ...body, fingerprint: hash(canonical(body)) };
}

function writePack(folder: string, scenario: Scenario, negativeControl = false): void {
  const prepared = prepare(scenario);
  if (negativeControl && scenario !== 'path') throw new Error('Negative control is defined for the path fixture only');
  const candidate = negativeControl ? prepared.candidate.replace('/v2/customers/', '/v9/customers/') : prepared.candidate;
  const patch = negativeControl ? prepared.patch.replace('/v2/customers/', '/v9/customers/') : prepared.patch;
  mkdirSync(join(folder, 'tests'));
  writeFileSync(join(folder, 'source.ts'), prepared.source);
  writeFileSync(join(folder, 'candidate.ts'), candidate);
  writeFileSync(join(folder, 'repair.patch'), patch);
  writeFileSync(join(folder, 'old-api.json'), prepared.oldBytes);
  writeFileSync(join(folder, 'new-api.json'), prepared.newBytes);
  writeFileSync(join(folder, 'scenario.json'), `${JSON.stringify({ scenario, reason: prepared.reason, negativeControl })}\n`);
  cpSync(template, join(folder, 'tests', 'proof.test.mjs'));
}

export function prove(scenario: string, outputRoot: string, negativeControl = false): { folder: string; evidence: EvidenceManifest } {
  const prepared = prepare(scenario);
  const target = resolve(outputRoot);
  mkdirSync(target, { recursive: true });
  const folder = mkdtempSync(join(target, `${prepared.scenario}-`));
  writePack(folder, prepared.scenario, negativeControl);
  const evidence = manifest(folder, prepared.scenario, runChecks(folder, prepared.recipe !== null), prepared.preliminaryVerdict);
  writeFileSync(join(folder, 'manifest.json'), `${JSON.stringify(evidence, null, 2)}\n`);
  const rows = evidence.checks.map((check) => `| ${check.id} | ${check.outcome} |`).join('\n');
  writeFileSync(join(folder, 'report.md'), `# MigrateLens fictional proof\n\nVerdict: **${evidence.verdict}**\n\nFingerprint: \`${evidence.fingerprint}\`\n\n| Check | Result |\n|---|---|\n${rows}\n\n${evidence.limitations.join('\n')}\n`);
  return { folder, evidence };
}

export function verify(manifestPath: string): EvidenceManifest {
  const target = resolve(manifestPath);
  if (basename(target) !== 'manifest.json' || !existsSync(target)) throw new Error('Proof manifest missing');
  const folder = dirname(target);
  const saved = JSON.parse(readFileSync(target, 'utf8')) as EvidenceManifest;
  if (saved.schemaVersion !== 'oss-1') throw new Error('Unsupported proof schema');
  const prepared = prepare(saved.scenario);
  const control = JSON.parse(readFileSync(join(folder, 'scenario.json'), 'utf8')) as { negativeControl?: boolean };
  const expectedCandidate = control.negativeControl ? prepared.candidate.replace('/v2/customers/', '/v9/customers/') : prepared.candidate;
  const expectedPatch = control.negativeControl ? prepared.patch.replace('/v2/customers/', '/v9/customers/') : prepared.patch;
  if (readFileSync(join(folder, 'source.ts'), 'utf8') !== prepared.source ||
      !readFileSync(join(folder, 'old-api.json')).equals(prepared.oldBytes) ||
      !readFileSync(join(folder, 'new-api.json')).equals(prepared.newBytes) ||
      readFileSync(join(folder, 'candidate.ts'), 'utf8') !== expectedCandidate ||
      readFileSync(join(folder, 'repair.patch'), 'utf8') !== expectedPatch ||
      !readFileSync(join(folder, 'tests', 'proof.test.mjs')).equals(readFileSync(template))) {
    throw new Error('Proof inputs, recipe candidate or tests stale against current registered fixture');
  }
  const current = manifest(folder, saved.scenario, runChecks(folder, prepared.recipe !== null), prepared.preliminaryVerdict);
  if (canonical(current) !== canonical(saved)) throw new Error('Proof evidence changed or stale');
  if (readFileSync(join(folder, 'report.md'), 'utf8') !== renderReport(saved)) throw new Error('Proof report changed');
  return current;
}

function renderReport(evidence: EvidenceManifest): string {
  const rows = evidence.checks.map((check) => `| ${check.id} | ${check.outcome} |`).join('\n');
  return `# MigrateLens fictional proof\n\nVerdict: **${evidence.verdict}**\n\nFingerprint: \`${evidence.fingerprint}\`\n\n| Check | Result |\n|---|---|\n${rows}\n\n${evidence.limitations.join('\n')}\n`;
}
