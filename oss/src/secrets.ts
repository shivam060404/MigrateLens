/** Conservative publication preflight. CI must also use its own secret scanner. */
const patterns: [string, RegExp][] = [
  ['private key', /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/i],
  ['GitHub token', /\b(?:ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)[A-Za-z0-9_]{20,}\b/],
  ['AWS access key', /\b(?:AKIA|ASIA)[A-Z0-9]{16}\b/],
  ['OpenAI style key', /\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b/],
  ['synthetic secret canary', /\bMIGRATELENS_SECRET_CANARY_[A-Za-z0-9_-]+\b/],
];

export function assertNoKnownSecret(label: string, bytes: Buffer): void {
  for (const [kind, pattern] of patterns) {
    if (pattern.test(bytes.toString('utf8'))) {
      throw new Error(`${label} contains ${kind}; proof artifact creation refused`);
    }
  }
}
