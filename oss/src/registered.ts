import { createHash } from 'node:crypto';
import { lstatSync, readFileSync, realpathSync } from 'node:fs';
import { dirname, extname, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { Project, SyntaxKind } from 'ts-morph';
import { detect, parseContract } from './contracts.js';
import type { Finding } from './model.js';

type JsonObject = Record<string, unknown>;
type Classification = 'confirmed' | 'candidate' | 'unresolved' | 'not_affected';

interface Registration {
  schemaVersion: 1;
  provider: string;
  oldSpec: string;
  newSpec: string;
  sourceFiles: string[];
  mappings: { ruleId: string; operation: string; before: string; after: string; evidenceRef: string; revision: string }[];
  proof?: unknown;
}

function object(value: unknown, label: string): JsonObject {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`Invalid ${label}`);
  return value as JsonObject;
}

function string(value: unknown, label: string): string {
  if (typeof value !== 'string' || !value.trim() || value.length > 256) throw new Error(`Invalid ${label}`);
  return value;
}

function exactKeys(value: JsonObject, keys: string[], label: string): void {
  if (Object.keys(value).sort().join(',') !== keys.sort().join(',')) throw new Error(`Invalid ${label} keys`);
}

function checkedPath(root: string, name: string, extensions: string[]): string {
  const parts = name.split('/');
  if (isAbsolute(name) || !/^[A-Za-z0-9._/-]+$/.test(name) || parts.some(part => !part || part === '.' || part === '..') ||
      name.startsWith('-') || name.length > 256 || !extensions.includes(extname(name))) {
    throw new Error('Registered path is outside admitted scope');
  }
  if (extensions.includes('.ts') && parts.some(part =>
    ['.git', '.github', 'node_modules', 'infra', 'auth', 'authorization', 'security', 'secrets', 'deploy'].includes(part))) {
    throw new Error('Registered source path is protected by patch policy');
  }
  const target = resolve(root, name);
  const rel = relative(root, target);
  if (rel.startsWith('..') || isAbsolute(rel) || !target.startsWith(root + sep)) throw new Error('Registered path escapes root');
  let current = root;
  for (const part of parts) {
    current = join(current, part);
    if (lstatSync(current).isSymbolicLink()) throw new Error('Registered path contains a symlink');
  }
  if (realpathSync(target) !== target || !lstatSync(target).isFile()) throw new Error('Registered path is not a regular file');
  return target;
}

function limitedRead(path: string, limit: number): Buffer {
  const bytes = readFileSync(path);
  if (bytes.byteLength > limit) throw new Error('Registered input exceeds byte budget');
  return bytes;
}

function parseRegistration(bytes: Buffer): Registration {
  if (bytes.byteLength > 16_384) throw new Error('Registration exceeds byte budget');
  const value = object(JSON.parse(bytes.toString('utf8')) as unknown, 'registration');
  exactKeys(value, ['schemaVersion', 'provider', 'oldSpec', 'newSpec', 'sourceFiles', 'mappings', ...(value.proof === undefined ? [] : ['proof'])], 'registration');
  if (value.schemaVersion !== 1) throw new Error('Unsupported registration schema');
  const provider = string(value.provider, 'provider');
  if (!/^[A-Za-z0-9._-]+$/.test(provider)) throw new Error('Invalid provider identifier');
  const oldSpec = string(value.oldSpec, 'oldSpec');
  const newSpec = string(value.newSpec, 'newSpec');
  if (!Array.isArray(value.sourceFiles) || value.sourceFiles.length < 1 || value.sourceFiles.length > 32) throw new Error('Invalid sourceFiles');
  const sourceFiles = value.sourceFiles.map(item => string(item, 'source file'));
  if (new Set(sourceFiles).size !== sourceFiles.length) throw new Error('Duplicate source file');
  if (!Array.isArray(value.mappings) || value.mappings.length > 16) throw new Error('Invalid mappings');
  const mappings = value.mappings.map(item => {
    const row = object(item, 'mapping');
    exactKeys(row, ['ruleId', 'operation', 'before', 'after', 'evidenceRef', 'revision'], 'mapping');
    return {
      ruleId: string(row.ruleId, 'ruleId'), operation: string(row.operation, 'operation'),
      before: string(row.before, 'before'), after: string(row.after, 'after'),
      evidenceRef: string(row.evidenceRef, 'evidenceRef'), revision: string(row.revision, 'revision'),
    };
  });
  return { schemaVersion: 1, provider, oldSpec, newSpec, sourceFiles, mappings, proof: value.proof };
}

function digest(bytes: Buffer): string {
  return `sha256:${createHash('sha256').update(bytes).digest('hex')}`;
}

function classify(source: string, finding: Finding): Classification {
  const project = new Project({ useInMemoryFileSystem: true });
  const file = project.createSourceFile('source.ts', source);
  if (finding.kind === 'endpoint_path') {
    const prefix = finding.before.replace(/\{[^}]+\}$/, '');
    const matching = file.getDescendantsOfKind(SyntaxKind.CallExpression).filter(call =>
      call.getExpression().getText() === 'fetch' && call.getArguments()[0]?.getText().includes(prefix));
    if (matching.length === 1) return 'confirmed';
    if (matching.length > 1) return 'unresolved';
    return source.includes(prefix) ? 'candidate' : 'not_affected';
  }
  if (finding.kind === 'query_parameter') {
    const matching = file.getDescendantsOfKind(SyntaxKind.CallExpression).filter(call =>
      call.getExpression().getText().endsWith('.set') && call.getArguments()[0]?.getText() === JSON.stringify(finding.before));
    if (matching.length === 1) return 'confirmed';
    if (matching.length > 1) return 'unresolved';
    return source.includes(finding.before) ? 'candidate' : 'not_affected';
  }
  const oldField = finding.before.split('/').filter(Boolean).at(-1);
  if (!oldField) return 'unresolved';
  const access = file.getDescendantsOfKind(SyntaxKind.PropertyAccessExpression).filter(node => node.getName() === oldField);
  return access.length > 0 ? 'candidate' : source.includes(oldField) ? 'unresolved' : 'not_affected';
}

export function analyzeRegistered(configPath: string) {
  const path = resolve(configPath);
  if (lstatSync(path).isSymbolicLink() || !lstatSync(path).isFile()) throw new Error('Registration must be a regular file');
  const root = realpathSync(dirname(path));
  const registration = parseRegistration(limitedRead(path, 16_384));
  const oldPath = checkedPath(root, registration.oldSpec, ['.json']);
  const newPath = checkedPath(root, registration.newSpec, ['.json']);
  const oldBytes = limitedRead(oldPath, 1_000_000);
  const newBytes = limitedRead(newPath, 1_000_000);
  const sources = registration.sourceFiles.map(name => ({ name, bytes: limitedRead(checkedPath(root, name, ['.ts', '.tsx']), 65_536) }));
  const identities = {
    registration: digest(limitedRead(path, 16_384)),
    oldSpec: digest(oldBytes), newSpec: digest(newBytes),
    sources: Object.fromEntries(sources.map(item => [item.name, digest(item.bytes)])),
  };
  try {
    const findings = detect(parseContract(oldBytes), parseContract(newBytes));
    const usage = findings.flatMap(finding => sources.map(item => ({
      ruleId: finding.ruleId, path: item.name, classification: classify(item.bytes.toString('utf8'), finding),
    })));
    const mappingDeclared = findings.length === 1 && registration.mappings.some(mapping =>
      mapping.ruleId === findings[0]?.ruleId && mapping.operation === findings[0].operation &&
      mapping.before === findings[0].before && mapping.after === findings[0].after);
    const verdict = findings.length === 0 ? 'ANALYSIS_ONLY' :
      !mappingDeclared ? 'NEEDS_CLARIFICATION' : usage.some(item => item.classification === 'unresolved' || item.classification === 'candidate') ?
      'NEEDS_CLARIFICATION' : 'ANALYSIS_ONLY';
    return {
      provider: registration.provider, identities, findings, usage, mappingDeclared,
      verdict, patch: '', reason: findings.length === 0 ? 'No supported contract change' :
        !mappingDeclared ? 'Exact semantic mapping declaration missing' :
        'Registered inputs are analysis-only until repository proof and patch policy are implemented',
      limitations: ['Repository mapping is self-declared and not an authenticated approval', 'Read-only local analysis; no patch, proof or CI provenance claim', 'Response-field dataflow is candidate-only'],
    };
  } catch (error) {
    return {
      provider: registration.provider, identities, findings: [], usage: [], mappingDeclared: false,
      verdict: 'UNSUPPORTED', patch: '',
      reason: error instanceof Error ? error.message : 'Unsupported contract',
      limitations: ['Read-only local analysis; no patch, proof or CI provenance claim'],
    };
  }
}

export function proposeRegisteredPath(configPath: string) {
  const analysis = analyzeRegistered(configPath);
  if (analysis.findings.length !== 1 || analysis.findings[0]?.kind !== 'endpoint_path' ||
      !analysis.mappingDeclared || analysis.usage.length !== 1 ||
      analysis.usage[0]?.classification !== 'confirmed') {
    throw new Error('Registered patch requires one declared, confirmed endpoint path usage');
  }
  const path = resolve(configPath);
  const root = realpathSync(dirname(path));
  const registration = parseRegistration(limitedRead(path, 16_384));
  if (digest(limitedRead(path, 16_384)) !== analysis.identities.registration) throw new Error('Registration changed during planning');
  const name = registration.sourceFiles[0];
  const finding = analysis.findings[0];
  if (!name || !finding) throw new Error('Missing registered source or finding');
  const sourcePath = checkedPath(root, name, ['.ts', '.tsx']);
  const sourceBytes = limitedRead(sourcePath, 65_536);
  if (digest(sourceBytes) !== analysis.identities.sources[name] ||
      digest(limitedRead(checkedPath(root, registration.oldSpec, ['.json']), 1_000_000)) !== analysis.identities.oldSpec ||
      digest(limitedRead(checkedPath(root, registration.newSpec, ['.json']), 1_000_000)) !== analysis.identities.newSpec) {
    throw new Error('Registered input changed during planning');
  }
  const oldMatch = /^(.*)\{([^}]+)\}$/.exec(finding.before);
  const newMatch = /^(.*)\{([^}]+)\}$/.exec(finding.after);
  if (!oldMatch || !newMatch || oldMatch[2] !== newMatch[2] ||
      !oldMatch[1]?.startsWith('/') || !newMatch[1]?.startsWith('/')) {
    throw new Error('Endpoint patch supports one unchanged trailing path parameter');
  }
  const oldPrefix = oldMatch[1];
  const newPrefix = newMatch[1];
  const source = sourceBytes.toString('utf8');
  const project = new Project({ useInMemoryFileSystem: true });
  const file = project.createSourceFile(name, source);
  const matching = file.getDescendantsOfKind(SyntaxKind.CallExpression).filter(call =>
    call.getExpression().getText() === 'fetch' && call.getArguments()[0]?.getText().includes(oldPrefix));
  if (matching.length !== 1) throw new Error('Endpoint patch requires exactly one direct fetch call');
  const argument = matching[0]?.getArguments()[0];
  if (!argument || !argument.isKind(SyntaxKind.TemplateExpression) ||
      argument.getTemplateSpans().length !== 2 ||
      !argument.getText().includes(oldPrefix + '${') || !argument.getText().endsWith("}`")) {
    throw new Error('Endpoint patch requires a direct fetch template with one path parameter');
  }
  const originalArg = argument.getText();
  if (originalArg.split(oldPrefix).length !== 2) throw new Error('Endpoint prefix must appear exactly once');
  argument.replaceWithText(originalArg.replace(oldPrefix, newPrefix));
  const candidate = file.getFullText();
  const before = source.split('\n');
  const after = candidate.split('\n');
  const changed = before.map((line, index) => line === after[index] ? -1 : index).filter(index => index >= 0);
  if (before.length !== after.length || changed.length !== 1 || changed[0] === undefined) {
    throw new Error('Endpoint patch exceeded one-line policy');
  }
  const line = changed[0];
  const patch = `--- a/${name}\n+++ b/${name}\n@@ -${line + 1},1 +${line + 1},1 @@\n-${before[line]}\n+${after[line]}\n`;
  return {
    ...analysis, patch, candidateHash: digest(Buffer.from(candidate)), candidateSource: candidate, changedFiles: 1, changedLines: 1,
    reason: 'Bounded proposal only; customer CI proof has not executed',
  };
}
