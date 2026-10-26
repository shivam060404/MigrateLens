// Fictional Northstar integration. Internal domain shape stays stable.
type WireCustomer = { id: string; name?: string | null; profile?: { displayName?: string | null }; tier: string; unrelated: { name: string } };
export type Customer = { id: string; name: string | null; tier: string; unrelatedName: string };
export async function getCustomer(base: string, id: string): Promise<Customer | null> {
  const response = await fetch(`${base}/v9/customers/${encodeURIComponent(id)}`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`provider:${response.status}`);
  const customer: WireCustomer = await response.json();
  return { id: customer.id, name: customer.name ?? null, tier: customer.tier, unrelatedName: customer.unrelated.name };
}
export async function listCustomers(base: string, pageSize?: number): Promise<string[]> {
  const query = new URLSearchParams();
  if (pageSize !== undefined) query.set("pageSize", String(pageSize));
  const response = await fetch(`${base}/customers?${query.toString()}`);
  if (!response.ok) throw new Error(`provider:${response.status}`);
  const data: { items: { id: string }[] } = await response.json();
  return data.items.map(customer => customer.id);
}
