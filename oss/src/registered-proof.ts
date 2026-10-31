import { cpSync, existsSync, mkdirSync, mkdtempSync, readdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { Project, SyntaxKind } from 'ts-morph';
import { canonical, hash } from './engine.js';
import { limitedRead, proposeRegisteredPath, readRegisteredInput, registrationRoot } from './registered.js';
import { assertNoKnownSecret } from './secrets.js';
import type { Check } from './model.js';

const here = dirname(fileURLToPath(import.meta.url));
const template = join(here, '..', 'templates', 'registered-path.test.mjs');
const require = createRequire(import.meta.url);
const tsc = require.resolve('typescript/bin/tsc');
const IDS = ['BASELINE_OLD', 'REPRO_NEW', 'REPAIR_NEW', 'REGRESSION'] as const;

function readFileSync(path: string): Buffer;
function readFileSync(path: string, encoding: 'utf8'): string;
function readFileSync(path: string, encoding?: 'utf8'): Buffer | string {
  const bytes = limitedRead(path, 1_000_000);
  return encoding ? bytes.toString(encoding) : bytes;
}

interface Vector {
  args: unknown[];
  pathParams: Record<string, string>;
  response: unknown;
  expected: unknown;
}
interface Proof {
  exportName: string;
  cases: [Vector, Vector];
}
interface Registration {
  provider: string;
  oldSpec: string;
  newSpec: string;
  sourceFiles: string[];
  mappings: { operation: string }[];
  proof?: unknown;
}
export interface RegisteredManifest {
  schemaVersion: 'registered-1';
  classification: 'unattested local registered proposal';
  verdict: 'LOCAL_CHECKS_PASSED' | 'VALIDATION_FAILED';
  identities: Record<string, unknown>;
  checks: Check[];
  limitations: string[];
  fingerprint: string;
}

function record(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`Invalid ${label}`);
  return value as Record<string, unknown>;
}
function proofFrom(config: Registration): Proof {
  const value = record(config.proof, 'proof vectors');
  if (Object.keys(value).sort().join(',') !== 'cases,exportName' ||
      typeof value.exportName !== 'string' || !/^[A-Za-z_$][A-Za-z0-9_$]*$/.test(value.exportName) ||
      !Array.isArray(value.cases) || value.cases.length !== 2) throw new Error('Invalid registered proof contract');
  const cases = value.cases.map((item, index) => {
    const row = record(item, `proof case ${index}`);
    if (Object.keys(row).sort().join(',') !== 'args,expected,pathParams,response' ||
        !Array.isArray(row.args) || row.args.length < 1 || row.args.length > 8 ||
        row.args[0] !== 'http://fixture.invalid' ||
        row.args.some(arg => !['string', 'number', 'boolean'].includes(typeof arg))) throw new Error('Invalid proof case');
    const pathParams = record(row.pathParams, 'path parameters');
    if (Object.values(pathParams).some(item => typeof item !== 'string' || item.length > 256)) throw new Error('Invalid path parameter');
    return row as unknown as Vector;
  });
  return { exportName: value.exportName, cases: cases as [Vector, Vector] };
}
function assertStandaloneSource(source: string): void {
  const project = new Project({ useInMemoryFileSystem: true });
  const file = project.createSourceFile('registered-source.ts', source);
  if (file.getImportDeclarations().length || file.getExportDeclarations().some(item => item.getModuleSpecifierValue()) ||
      file.getDescendantsOfKind(SyntaxKind.ImportEqualsDeclaration).length ||
      file.getDescendantsOfKind(SyntaxKind.ImportKeyword).length ||
      file.getDescendantsOfKind(SyntaxKind.CallExpression).some(call => call.getExpression().getText() === 'require')) {
    throw new Error('Registered proof requires standalone source without imports or require');
  }
  if (file.getStatements().some(statement => !statement.isKind(SyntaxKind.TypeAliasDeclaration) &&
      !statement.isKind(SyntaxKind.InterfaceDeclaration) && !statement.isKind(SyntaxKind.FunctionDeclaration))) {
    throw new Error('Registered proof requires declaration-only module top level');
  }
}
function matchesResponseShape(value: unknown, schemaValue: unknown, depth = 0): boolean {
  if (depth > 8) throw new Error('Response schema exceeds proof depth');
  const schema = record(schemaValue, 'response schema');
  const allowed = new Set(['type', 'properties', 'required', 'items', 'additionalProperties', 'description']);
  if (Object.keys(schema).some(key => !allowed.has(key))) throw new Error('Response schema exceeds supported proof subset');
  const types = typeof schema.type === 'string' ? [schema.type] : schema.type;
  if (!Array.isArray(types) || types.length < 1 || types.some(item => !['object', 'array', 'string', 'integer', 'number', 'boolean', 'null'].includes(item))) {
    throw new Error('Response schema type unsupported');
  }
  for (const type of types) {
    if (type === 'null' && value === null) return true;
    if (type === 'string' && typeof value === 'string') return true;
    if (type === 'boolean' && typeof value === 'boolean') return true;
    if (type === 'integer' && typeof value === 'number' && Number.isInteger(value)) return true;
    if (type === 'number' && typeof value === 'number' && Number.isFinite(value)) return true;
    if (type === 'array' && Array.isArray(value)) {
      if (!schema.items) throw new Error('Array response schema requires items');
      if (value.every(item => matchesResponseShape(item, schema.items, depth + 1))) return true;
    }
    if (type === 'object' && value && typeof value === 'object' && !Array.isArray(value)) {
      const data = value as Record<string, unknown>;
      const properties = record(schema.properties, 'response properties');
      const required = schema.required === undefined ? [] : schema.required;
      if (!Array.isArray(required) || required.some(item => typeof item !== 'string')) throw new Error('Invalid response required list');
      if (required.some(key => !(key in data))) continue;
      if (Object.entries(data).some(([key, item]) => {
        if (key in properties) return !matchesResponseShape(item, properties[key], depth + 1);
        return schema.additionalProperties === false;
      })) continue;
      return true;
    }
  }
  return false;
}
function readBound(configPath: string) {
  const proposal = proposeRegisteredPath(configPath);
  const configBytes = limitedRead(resolve(configPath), 16_384);
  if (`sha256:${hash(configBytes)}` !== proposal.identities.registration) throw new Error('Registration changed during proof');
  const config = JSON.parse(configBytes.toString('utf8')) as Registration;
  const proof = proofFrom(config);
  if (config.mappings.length !== 1) throw new Error('Registered path proof requires exactly one mapping');
  const root = registrationRoot(configPath);
  const sourceName = config.sourceFiles[0];
  if (!sourceName) throw new Error('Missing source');
  const source = readRegisteredInput(root, sourceName, ['.ts', '.tsx'], 65_536);
  const oldSpec = readRegisteredInput(root, config.oldSpec, ['.json'], 1_000_000);
  const newSpec = readRegisteredInput(root, config.newSpec, ['.json'], 1_000_000);
  if (`sha256:${hash(source)}` !== proposal.identities.sources[sourceName] ||
      `sha256:${hash(oldSpec)}` !== proposal.identities.oldSpec ||
      `sha256:${hash(newSpec)}` !== proposal.identities.newSpec) throw new Error('Registered input changed during proof');
  for (const [label, bytes] of [['registration', configBytes], ['source', source], ['old contract', oldSpec], ['new contract', newSpec]] as const) {
    assertNoKnownSecret(label, bytes);
  }
  assertStandaloneSource(source.toString('utf8'));
  const oldPaths = record(record(JSON.parse(oldSpec.toString('utf8')) as unknown, 'old contract').paths, 'old paths');
  const newPaths = record(record(JSON.parse(newSpec.toString('utf8')) as unknown, 'new contract').paths, 'new paths');
  const operation = config.mappings[0]?.operation;
  const getOperation = (paths: Record<string, unknown>) => {
    const found = Object.values(paths).map(item => record(item, 'path item').get)
      .find(item => item && record(item, 'GET operation').operationId === operation);
    if (!found) throw new Error('Mapped GET operation absent');
    return found;
  };
  const oldOperation = getOperation(oldPaths);
  const newOperation = getOperation(newPaths);
  if (canonical(oldOperation) !== canonical(newOperation)) {
    throw new Error('Registered path proof requires otherwise identical GET operations');
  }
  const responses = record(record(oldOperation, 'GET operation').responses, 'responses');
  const success = record(responses['200'], '200 response');
  const content = record(success.content, 'response content');
  const json = record(content['application/json'], 'JSON response');
  const responseSchema = record(json.schema, 'response schema');
  for (const vector of proof.cases) {
    if (!matchesResponseShape(vector.response, responseSchema)) throw new Error('Proof response does not match supported OpenAPI schema');
  }
  return { proposal, configBytes, config, proof, source, oldSpec, newSpec, sourceName };
}

function checks(folder: string): Check[] {
  const files = ['source.ts', 'candidate.ts', 'registration.json', 'old-api.json', 'new-api.json', 'repair.patch', 'tests/proof.test.mjs'];
  const before = files.map(file => hash(readFileSync(join(folder, file))));
  const testRun = spawnSync(process.execPath, ['--experimental-strip-types', '--disable-warning=ExperimentalWarning', '--test', join(folder, 'tests', 'proof.test.mjs')], {
    cwd: folder, encoding: 'utf8', timeout: 15_000, maxBuffer: 100_000,
    env: { PATH: process.env.PATH ?? '', HOME: folder, TMPDIR: tmpdir() },
  });
  const output = `${testRun.stdout ?? ''}\n${testRun.stderr ?? ''}`;
  const result: Check[] = IDS.map(id => ({
    id,
    outcome: new RegExp(`^ok \\d+ - ${id}$`, 'm').test(output) ? 'PASS' :
      new RegExp(`^not ok \\d+ - ${id}$`, 'm').test(output) ? 'FAIL' : 'ERROR',
    reason: testRun.error ? 'Local proof process unavailable' : 'Executed caller-local registered mock test',
  }));
  if (testRun.status !== 0 && result.every(item => item.outcome === 'PASS')) {
    result[0] = { id: 'BASELINE_OLD', outcome: 'ERROR', reason: 'Proof process exited despite passing test lines' };
  }
  const staticRun = spawnSync(process.execPath, [tsc, '--noEmit', '--strict', '--skipLibCheck', '--target', 'ES2022', '--lib', 'ES2022,DOM', 'candidate.ts'], {
    cwd: folder, encoding: 'utf8', timeout: 15_000, maxBuffer: 30_000,
    env: { PATH: process.env.PATH ?? '', HOME: folder, TMPDIR: tmpdir() },
  });
  result.push({ id: 'STATIC', outcome: staticRun.error ? 'ERROR' : staticRun.status === 0 ? 'PASS' : 'FAIL', reason: 'Executed strict TypeScript compiler' });
  const after = files.map(file => hash(readFileSync(join(folder, file))));
  const clean = readdirSync(folder).every(name => new Set(['source.ts', 'candidate.ts', 'registration.json', 'old-api.json', 'new-api.json', 'repair.patch', 'tests', 'manifest.json', 'report.md']).has(name)) &&
    readdirSync(join(folder, 'tests')).join(',') === 'proof.test.mjs';
  result.push({ id: 'POLICY', outcome: clean && before.every((item, index) => item === after[index]) ? 'PASS' : 'FAIL', reason: 'Proof inputs stayed immutable and no extra artifacts appeared' });
  return result;
}

function makeManifest(folder: string, input: ReturnType<typeof readBound>, observed: Check[]): RegisteredManifest {
  const bound = input.proposal.identities;
  const body = {
    schemaVersion: 'registered-1' as const,
    classification: 'unattested local registered proposal' as const,
    verdict: observed.length === 6 && observed.every(item => item.outcome === 'PASS') ? 'LOCAL_CHECKS_PASSED' as const : 'VALIDATION_FAILED' as const,
    identities: {
      registration: bound.registration, oldSpec: bound.oldSpec, newSpec: bound.newSpec, sources: bound.sources,
      candidate: `sha256:${hash(readFileSync(join(folder, 'candidate.ts')))}`,
      patch: `sha256:${hash(readFileSync(join(folder, 'repair.patch')))}`,
      testSuite: `sha256:${hash(readFileSync(join(folder, 'tests', 'proof.test.mjs')))}`,
      policy: `sha256:${hash(canonical({ allowedRules: ['ML-PATH-001'], maxChangedFiles: 1, maxChangedLines: 1, noPublication: true, proofEnvironment: 'caller-local-unattested' }))}`,
      implementation: `sha256:${hash(Buffer.concat(['registered.js', 'registered-proof.js', 'contracts.js', 'secrets.js'].map(file => readFileSync(join(here, file)))))}`,
      runner: `node:${process.version};typescript:5.9.3;caller-local-unattested`,
    },
    checks: observed,
    limitations: [
      'Mapping and expected outputs are self-declared, not independently approved.',
      'Proof executes consumer source in the caller environment; it is not a sandbox.',
      'Local hashes do not authenticate CI origin or authorize publication.',
      'Known credential patterns are rejected before artifact creation; this is not a complete secret scanner.',
      'Only one direct-fetch path migration with unchanged GET operation is covered.',
    ],
  };
  return { ...body, fingerprint: hash(canonical(body)) };
}
function report(value: RegisteredManifest): string {
  const rows = value.checks.map(item => `| ${item.id} | ${item.outcome} |`).join('\n');
  return `# MigrateLens registered local proof\n\nVerdict: **${value.verdict}**\n\nFingerprint: \`${value.fingerprint}\`\n\n| Check | Result |\n|---|---|\n${rows}\n\n${value.limitations.join('\n')}\n`;
}

export function proveRegistered(configPath: string, outputRoot: string) {
  const input = readBound(configPath);
  const root = resolve(outputRoot);
  mkdirSync(root, { recursive: true });
  const folder = mkdtempSync(join(root, 'registered-path-'));
  mkdirSync(join(folder, 'tests'));
  writeFileSync(join(folder, 'source.ts'), input.source);
  writeFileSync(join(folder, 'candidate.ts'), input.proposal.candidateSource);
  writeFileSync(join(folder, 'registration.json'), input.configBytes);
  writeFileSync(join(folder, 'old-api.json'), input.oldSpec);
  writeFileSync(join(folder, 'new-api.json'), input.newSpec);
  writeFileSync(join(folder, 'repair.patch'), input.proposal.patch);
  cpSync(template, join(folder, 'tests', 'proof.test.mjs'));
  const evidence = makeManifest(folder, input, checks(folder));
  writeFileSync(join(folder, 'manifest.json'), `${JSON.stringify(evidence, null, 2)}\n`);
  writeFileSync(join(folder, 'report.md'), report(evidence));
  return { folder, evidence };
}

export function verifyRegistered(manifestPath: string, configPath: string): RegisteredManifest {
  const target = resolve(manifestPath);
  if (basename(target) !== 'manifest.json' || !existsSync(target)) throw new Error('Registered proof manifest missing');
  const folder = dirname(target);
  const saved = JSON.parse(readFileSync(target, 'utf8')) as RegisteredManifest;
  if (saved.schemaVersion !== 'registered-1') throw new Error('Unsupported registered proof schema');
  const input = readBound(configPath);
  if (!readFileSync(join(folder, 'registration.json')).equals(input.configBytes) ||
      !readFileSync(join(folder, 'source.ts')).equals(input.source) ||
      !readFileSync(join(folder, 'old-api.json')).equals(input.oldSpec) ||
      !readFileSync(join(folder, 'new-api.json')).equals(input.newSpec) ||
      readFileSync(join(folder, 'candidate.ts'), 'utf8') !== input.proposal.candidateSource ||
      readFileSync(join(folder, 'repair.patch'), 'utf8') !== input.proposal.patch ||
      !readFileSync(join(folder, 'tests', 'proof.test.mjs')).equals(readFileSync(template))) {
    throw new Error('Registered proof inputs or candidate stale');
  }
  const current = makeManifest(folder, input, checks(folder));
  if (canonical(current) !== canonical(saved) || readFileSync(join(folder, 'report.md'), 'utf8') !== report(saved)) {
    throw new Error('Registered proof evidence changed or stale');
  }
  return current;
}

/** Shareable metadata only. This is a local assertion, not authenticated CI provenance. */
export function exportRegistered(manifestPath: string, configPath: string) {
  const evidence = verifyRegistered(manifestPath, configPath);
  const sources = evidence.identities.sources as Record<string, string>;
  return {
    schemaVersion: 'registered-export-1',
    classification: 'unattested local metadata',
    verdict: evidence.verdict,
    fingerprint: evidence.fingerprint,
    manifestHash: `sha256:${hash(readFileSync(resolve(manifestPath)))}`,
    identities: {
      registration: evidence.identities.registration,
      oldSpec: evidence.identities.oldSpec,
      newSpec: evidence.identities.newSpec,
      sourceHashes: Object.values(sources).sort(),
      candidate: evidence.identities.candidate,
      patch: evidence.identities.patch,
      testSuite: evidence.identities.testSuite,
      policy: evidence.identities.policy,
      implementation: evidence.identities.implementation,
      runner: evidence.identities.runner,
    },
    checks: evidence.checks.map(({ id, outcome }) => ({ id, outcome })),
  };
}

export function previewRegistered(manifestPath: string, configPath: string): string {
  const evidence = verifyRegistered(manifestPath, configPath);
  if (evidence.verdict !== 'LOCAL_CHECKS_PASSED') throw new Error('Draft preview requires passing local checks');
  const registration = JSON.parse(readFileSync(resolve(configPath), 'utf8')) as Registration;
  const rows = evidence.checks.map(item => `| ${item.id} | ${item.outcome} |`).join('\n');
  const sourcePath = registration.sourceFiles[0];
  if (!sourcePath) throw new Error('Missing registered source path');
  return `# Draft PR preview — publication blocked

## Detected change

- Provider: ${registration.provider}
- Rule: ML-PATH-001
- Consumer file: \`${sourcePath}\`
- Old contract: \`${evidence.identities.oldSpec}\`
- New contract: \`${evidence.identities.newSpec}\`

## Proposed repair

- One direct-fetch endpoint path edit
- Source: \`${(evidence.identities.sources as Record<string, string>)[sourcePath]}\`
- Candidate: \`${evidence.identities.candidate}\`
- Patch: \`${evidence.identities.patch}\`

## Local proof

| Check | Result |
|---|---|
${rows}

Evidence fingerprint: \`${evidence.fingerprint}\`

## Publication gate

This is an unsigned local proposal. Mapping and expected outputs are self-declared. Customer CI provenance, authenticated semantic approval, secret scanning and trusted GitHub installation scope are not established. Do not publish this as a verified migration.
`;
}
