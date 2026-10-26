export type Scenario = 'path' | 'field' | 'query' | 'ambiguous' | 'unchanged';
export type RepairKind = 'endpoint_path' | 'response_field' | 'query_parameter';
export type Outcome = 'PASS' | 'FAIL' | 'ERROR' | 'UNAVAILABLE';
export type Verdict = 'VERIFIED_FOR_DECLARED_SCOPE' | 'VALIDATION_FAILED' | 'NEEDS_CLARIFICATION' | 'ANALYSIS_ONLY' | 'UNSUPPORTED';

export interface Finding {
  ruleId: string;
  kind: RepairKind;
  operation: string;
  before: string;
  after: string;
}

export interface Recipe {
  ruleId: string;
  kind: RepairKind;
  operation: string;
  before: string;
  after: string;
  semanticEvidence: string;
  allowedPath: string;
}

export interface Check {
  id: 'BASELINE_OLD' | 'REPRO_NEW' | 'REPAIR_NEW' | 'REGRESSION' | 'STATIC' | 'POLICY';
  outcome: Outcome;
  reason: string;
}

export interface EvidenceManifest {
  schemaVersion: 'oss-1';
  classification: 'fictional development fixture; unsigned local or CI evidence';
  scenario: Scenario;
  verdict: Verdict;
  identities: Record<string, string>;
  checks: Check[];
  limitations: string[];
  fingerprint: string;
}
