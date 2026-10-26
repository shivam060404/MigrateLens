import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import type { Scenario } from './model.js';

const fixtures = join(dirname(fileURLToPath(import.meta.url)), '..', 'fixtures');
export const SCENARIOS: readonly Scenario[] = ['path', 'field', 'query', 'ambiguous', 'unchanged'];

export interface Fixture {
  scenario: Scenario;
  source: string;
  oldBytes: Buffer;
  newBytes: Buffer;
  sourcePath: string;
}

export function loadFixture(scenario: string): Fixture {
  if (!SCENARIOS.includes(scenario as Scenario)) throw new Error('Unsupported fictional fixture');
  const sourcePath = join(fixtures, 'client.ts');
  return {
    scenario: scenario as Scenario,
    sourcePath,
    source: readFileSync(sourcePath, 'utf8'),
    oldBytes: readFileSync(join(fixtures, `${scenario}-old.json`)),
    newBytes: readFileSync(join(fixtures, `${scenario}-new.json`)),
  };
}
