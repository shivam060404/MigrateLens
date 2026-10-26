import { Project, SyntaxKind } from 'ts-morph';
import type { Finding, Recipe, Scenario } from './model.js';

const EVIDENCE: Partial<Record<Scenario, string>> = {
  path: 'Fictional provider mapping: same GET operationId and response shape',
  field: 'Fictional provider mapping: name and profile.displayName are equivalent',
  query: 'Fictional provider mapping: pageSize and limit retain integer semantics',
};

export function plan(scenario: Scenario, findings: Finding[]): Recipe | null {
  if (findings.length !== 1) return null;
  const finding = findings[0];
  if (!finding) return null;
  const approved = EVIDENCE[scenario];
  if (!approved) return null;
  const expected: Record<string, string> = {
    path: 'ML-PATH-001', field: 'ML-FIELD-001', query: 'ML-QUERY-001',
  };
  if (finding.ruleId !== expected[scenario]) return null;
  if (scenario === 'field' && finding.after !== '/profile/displayName') return null;
  return { ...finding, semanticEvidence: approved, allowedPath: 'client.ts' };
}

export interface PatchResult {
  candidate: string;
  changes: number;
  line: number;
}

export function applyRecipe(source: string, recipe: Recipe): PatchResult {
  if (Buffer.byteLength(source) > 65_536 || recipe.allowedPath !== 'client.ts') throw new Error('Source or path outside approved fixture scope');
  const project = new Project({ useInMemoryFileSystem: true });
  const file = project.createSourceFile('client.ts', source);
  const edits: { line: number; apply: () => void }[] = [];
  if (recipe.kind === 'endpoint_path') {
    const fn = file.getFunction('getCustomer');
    if (!fn || recipe.before !== '/v1/customers/{id}' || recipe.after !== '/v2/customers/{id}') throw new Error('Unsupported path recipe');
    for (const call of fn.getDescendantsOfKind(SyntaxKind.CallExpression)) {
      const arg = call.getArguments()[0];
      if (call.getExpression().getText() === 'fetch' && arg?.getText() === '`${base}/v1/customers/${encodeURIComponent(id)}`') {
        edits.push({ line: arg.getStartLineNumber(), apply: () => arg.replaceWithText('`${base}/v2/customers/${encodeURIComponent(id)}`') });
      }
    }
  } else if (recipe.kind === 'response_field') {
    const fn = file.getFunction('getCustomer');
    if (!fn || recipe.before !== '/name' || recipe.after !== '/profile/displayName') throw new Error('Unsupported field recipe');
    for (const access of fn.getDescendantsOfKind(SyntaxKind.PropertyAccessExpression)) {
      if (access.getText() === 'customer.name' && access.getFirstAncestorByKind(SyntaxKind.ReturnStatement)) {
        edits.push({ line: access.getStartLineNumber(), apply: () => access.replaceWithText('customer.profile?.displayName') });
      }
    }
  } else if (recipe.kind === 'query_parameter') {
    const fn = file.getFunction('listCustomers');
    if (!fn || recipe.before !== 'pageSize' || recipe.after !== 'limit') throw new Error('Unsupported query recipe');
    for (const call of fn.getDescendantsOfKind(SyntaxKind.CallExpression)) {
      const arg = call.getArguments()[0];
      if (call.getExpression().getText() === 'query.set' && arg?.getText() === '"pageSize"') {
        edits.push({ line: arg.getStartLineNumber(), apply: () => arg.replaceWithText('"limit"') });
      }
    }
  }
  if (edits.length !== 1) throw new Error('Exactly one approved AST edit is required');
  const edit = edits[0];
  if (!edit) throw new Error('Missing approved edit');
  edit.apply();
  return { candidate: file.getFullText(), changes: 1, line: edit.line };
}

export function unifiedPatch(source: string, result: PatchResult): string {
  const oldLines = source.split('\n');
  const newLines = result.candidate.split('\n');
  if (oldLines.length !== newLines.length) throw new Error('Line count changed outside bounded recipe');
  const changed = oldLines.map((value, index) => value === newLines[index] ? -1 : index).filter((index) => index >= 0);
  if (changed.length !== 1 || changed[0] !== result.line - 1) throw new Error('Candidate changed outside approved AST node');
  const line = changed[0];
  if (line === undefined) throw new Error('Missing changed line');
  return `--- a/client.ts\n+++ b/client.ts\n@@ -${line + 1},1 +${line + 1},1 @@\n-${oldLines[line]}\n+${newLines[line]}\n`;
}
