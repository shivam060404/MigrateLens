import { Project, SyntaxKind } from 'ts-morph';
/** Pure AST adapter; semantics are approved by the trusted controller.
 * @param {string} source
 * @param {string} scenario
 * @param {string} mode
 */
export function analyzeSource(source, scenario, mode = 'analyze') {
if (!['path','field','query'].includes(scenario) || !['analyze','repair'].includes(mode)) throw new Error('Unsupported fixture operation');
const project = new Project({ useInMemoryFileSystem: true });
const file = project.createSourceFile('client.ts', source);
const usages = [];
const unresolved = [];
let changes = 0;
/** @type {{node: import("ts-morph").Node, replacement: string}[]} */
const edits = [];
for (const call of file.getDescendantsOfKind(SyntaxKind.CallExpression)) {
  if (call.getExpression().getText() === 'fetch') {
    const arg = call.getArguments()[0];
    usages.push({ classification:'candidate', line:call.getStartLineNumber(), text:arg?.getText(), reason:'Explicit fixture binding; arbitrary wrappers are unsupported' });
    if (!arg || !arg.getText().includes('${base}')) unresolved.push({line:call.getStartLineNumber(),reason:'URL not statically bound'});
  }
}
// Narrow recipes require an exact integration symbol and node context. Never rename all name fields.
if (mode === 'repair') {
  if (scenario === 'path') {
    const fn = file.getFunctionOrThrow('getCustomer');
    for (const call of fn.getDescendantsOfKind(SyntaxKind.CallExpression)) {
      const arg = call.getArguments()[0];
      if (call.getExpression().getText() === 'fetch' && arg?.getText() === '`${base}/v1/customers/${encodeURIComponent(id)}`') {
        edits.push({node: arg, replacement: '`${base}/v2/customers/${encodeURIComponent(id)}`'});
      }
    }
  } else if (scenario === 'field') {
    const fn = file.getFunctionOrThrow('getCustomer');
    for (const access of fn.getDescendantsOfKind(SyntaxKind.PropertyAccessExpression)) {
      if (access.getText() === 'customer.name' && access.getFirstAncestorByKind(SyntaxKind.ReturnStatement)) {
        edits.push({node: access, replacement: 'customer.profile?.displayName'});
      }
    }
  } else {
    const fn = file.getFunctionOrThrow('listCustomers');
    for (const call of fn.getDescendantsOfKind(SyntaxKind.CallExpression)) {
      const arg = call.getArguments()[0];
      if (call.getExpression().getText() === 'query.set' && arg?.getText() === '"pageSize"') {
        edits.push({node: arg, replacement: '"limit"'});
      }
    }
  }
  if (edits.length !== 1) throw new Error('Unsupported fixture shape: expected exactly one bounded edit');
  edits[0].node.replaceWithText(edits[0].replacement);
  changes = edits.length;
}
return { schema_version:'1', analyzer:'ts-morph-26.0.0/fixture-1', scope:'registered Northstar integration only', usages, unresolved, changes, source:mode === 'repair' ? file.getFullText() : undefined };
}
