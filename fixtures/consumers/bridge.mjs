// Protocol adapter only. Expected answers remain in the trusted controller.
import { getCustomer, listCustomers } from './client.ts';
let raw = '';
for await (const chunk of process.stdin) raw += chunk;
const request = JSON.parse(raw);
const results = [];
for (const operation of request.operations) {
  try {
    results.push({ value: operation.kind === 'get' ? await getCustomer(request.base, operation.id) : await listCustomers(request.base, operation.size) });
  } catch (error) {
    results.push({ error: error instanceof Error ? error.message : 'unknown' });
  }
}
process.stdout.write(JSON.stringify(results));
