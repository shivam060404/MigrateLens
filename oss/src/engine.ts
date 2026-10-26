import { createHash } from 'node:crypto';
import { applyRecipe, unifiedPatch } from './recipes.js';
import { detect, parseContract } from './contracts.js';
import { loadFixture } from './fixture.js';
import type { Finding, Recipe, Scenario, Verdict } from './model.js';
import { plan } from './recipes.js';

export function hash(value: string | Buffer): string {
  return createHash('sha256').update(value).digest('hex');
}

export function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value !== null && typeof value === 'object') {
    return `{${Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => `${JSON.stringify(key)}:${canonical(item)}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

export interface PreparedCase {
  scenario: Scenario;
  source: string;
  sourcePath: string;
  oldBytes: Buffer;
  newBytes: Buffer;
  findings: Finding[];
  recipe: Recipe | null;
  candidate: string;
  patch: string;
  preliminaryVerdict: Verdict | null;
  reason: string | null;
}

export function prepare(scenario: string): PreparedCase {
  const fixture = loadFixture(scenario);
  const findings = detect(parseContract(fixture.oldBytes), parseContract(fixture.newBytes));
  const recipe = plan(fixture.scenario, findings);
  const preliminaryVerdict: Verdict | null = findings.length === 0 ? 'ANALYSIS_ONLY' : recipe ? null : 'NEEDS_CLARIFICATION';
  const reason = findings.length === 0 ? 'No supported contract change' : recipe ? null : 'No approved semantic mapping or recipe';
  if (!recipe) return { ...fixture, findings, recipe, candidate: fixture.source, patch: '', preliminaryVerdict, reason };
  const result = applyRecipe(fixture.source, recipe);
  const patch = unifiedPatch(fixture.source, result);
  return { ...fixture, findings, recipe, candidate: result.candidate, patch, preliminaryVerdict, reason };
}
