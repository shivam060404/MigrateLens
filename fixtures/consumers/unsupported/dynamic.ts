// Analysis-only exclusion fixture. Never admitted to the host execution runner.
export async function dynamicRequest(base: string, pathFromCaller: string): Promise<Response> {
  return fetch(new URL(pathFromCaller, base));
}
