import type { Finding } from './model.js';

type Json = Record<string, unknown>;
function object(value: unknown, name: string): Json {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`Invalid ${name}`);
  return value as Json;
}
function field(value: unknown, name: string): string {
  if (typeof value !== 'string' || !value) throw new Error(`Invalid ${name}`);
  return value;
}

export function parseContract(bytes: Buffer): Json {
  if (bytes.byteLength > 1_000_000) throw new Error('Contract exceeds byte budget');
  const contract = object(JSON.parse(bytes.toString('utf8')) as unknown, 'OpenAPI contract');
  const version = field(contract.openapi, 'OpenAPI version');
  if (!/^3\.[01]\./.test(version)) throw new Error('Only OpenAPI 3.0/3.1 is supported');
  // Inspect parsed keys so escaped JSON spellings cannot bypass the no-ref boundary.
  const pending: { value: unknown; depth: number }[] = [{ value: contract, depth: 0 }];
  let nodes = 0;
  while (pending.length) {
    const current = pending.pop();
    if (!current) break;
    nodes += 1;
    if (nodes > 50_000 || current.depth > 64) throw new Error('Contract exceeds structure budget');
    if (!current.value || typeof current.value !== 'object') continue;
    const entries = Array.isArray(current.value) ? current.value.map((value, index) => [String(index), value] as const) : Object.entries(current.value);
    for (const [key, value] of entries) {
      if (key === '$ref') throw new Error('Referenced contracts require review');
      pending.push({ value, depth: current.depth + 1 });
    }
  }
  object(contract.paths, 'paths');
  return contract;
}

function operations(contract: Json): Map<string, { path: string; operation: Json }> {
  const result = new Map<string, { path: string; operation: Json }>();
  for (const [path, item] of Object.entries(object(contract.paths, 'paths'))) {
    const method = object(item, 'path item').get;
    if (!method) continue;
    const operation = object(method, 'GET operation');
    const id = field(operation.operationId, 'operationId');
    if (result.has(id)) throw new Error('Duplicate operationId is unsupported');
    result.set(id, { path, operation });
  }
  return result;
}

function responseProperties(operation: Json): Json {
  const responses = object(operation.responses, 'responses');
  const success = object(responses['200'], '200 response');
  const content = object(success.content, 'response content');
  const json = object(content['application/json'], 'JSON response');
  const schema = object(json.schema, 'response schema');
  return object(schema.properties, 'response properties');
}

function queryParameters(operation: Json): string[] {
  const parameters = operation.parameters;
  if (!Array.isArray(parameters)) return [];
  return parameters.map((item) => object(item, 'parameter'))
    .filter((item) => item.in === 'query')
    .map((item) => field(item.name, 'parameter name'));
}

function comparable(value: unknown, depth = 0): unknown {
  if (depth > 64) throw new Error('Contract comparison exceeds depth budget');
  if (Array.isArray(value)) return value.map(item => comparable(item, depth + 1));
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).filter(([key]) => key !== 'description' && key !== 'summary' && !(depth === 0 && key === 'info'))
      .sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => [key, comparable(item, depth + 1)]));
  }
  return value;
}

export function detect(oldContract: Json, newContract: Json): Finding[] {
  const oldOps = operations(oldContract);
  const newOps = operations(newContract);
  const findings: Finding[] = [];
  for (const [id, oldOp] of oldOps) {
    const next = newOps.get(id);
    if (!next) throw new Error('Removed operation without mapping is unsupported');
    if (oldOp.path !== next.path) {
      findings.push({ ruleId: 'ML-PATH-001', kind: 'endpoint_path', operation: id, before: oldOp.path, after: next.path });
    }
    if (id === 'getCustomer') {
      const before = responseProperties(oldOp.operation);
      const after = responseProperties(next.operation);
      if ('name' in before && !('name' in after)) {
        const afterPointer = 'profile' in after ? '/profile/displayName' : 'nickname' in after ? '/nickname/displayName' : '';
        if (!afterPointer) throw new Error('Removed response field without supported relocation');
        findings.push({ ruleId: 'ML-FIELD-001', kind: 'response_field', operation: id, before: '/name', after: afterPointer });
      }
    }
    if (id === 'listCustomers') {
      const before = queryParameters(oldOp.operation);
      const after = queryParameters(next.operation);
      if (before.includes('pageSize') && !after.includes('pageSize') && after.includes('limit')) {
        findings.push({ ruleId: 'ML-QUERY-001', kind: 'query_parameter', operation: id, before: 'pageSize', after: 'limit' });
      }
    }
  }
  if (findings.length > 1) throw new Error('Multiple simultaneous changes require separate plans');
  if (findings.length === 0 && JSON.stringify(comparable(oldContract)) !== JSON.stringify(comparable(newContract))) {
    throw new Error('Unsupported contract change outside repair rules');
  }
  if (findings.length === 1 && findings[0]) {
    const finding = findings[0];
    const oldComparable = structuredClone(oldContract);
    const paths = object(oldComparable.paths, 'paths');
    if (finding.kind === 'endpoint_path') {
      paths[finding.after] = paths[finding.before];
      delete paths[finding.before];
    } else {
      const operationPath = oldOps.get(finding.operation)?.path;
      if (!operationPath) throw new Error('Mapped operation missing');
      const operation = object(object(paths[operationPath], 'path item').get, 'GET operation');
      if (finding.kind === 'query_parameter') {
        const parameters = operation.parameters;
        if (!Array.isArray(parameters)) throw new Error('Query parameters missing');
        const matches = parameters.filter(item => {
          const parameter = object(item, 'parameter');
          return parameter.in === 'query' && parameter.name === finding.before;
        });
        if (matches.length !== 1) throw new Error('Query rename requires one old parameter');
        object(matches[0], 'parameter').name = finding.after;
      } else if (finding.kind === 'response_field') {
        const properties = responseProperties(operation);
        const oldField = finding.before.slice(1);
        const oldSchema = properties[oldField];
        if (!oldSchema) throw new Error('Relocated field missing');
        delete properties[oldField];
        if (finding.after === '/profile/displayName') {
          properties.profile = { type: 'object', properties: { displayName: oldSchema } };
        } else if (finding.after === '/nickname/displayName') {
          properties.nickname = { type: 'object', properties: { displayName: oldSchema } };
        } else {
          throw new Error('Unsupported response field relocation');
        }
      }
    }
    if (JSON.stringify(comparable(oldComparable)) !== JSON.stringify(comparable(newContract))) {
      throw new Error('Supported migration includes another unsupported contract change');
    }
  }
  return findings;
}
