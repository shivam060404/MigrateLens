#!/usr/bin/env node
import { prepare } from './engine.js';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { prove, verify } from './proof.js';
import { analyzeRegistered, proposeRegisteredPath } from './registered.js';
import { exportRegistered, previewRegistered, proveRegistered, verifyRegistered } from './registered-proof.js';

function option(args: string[], name: string, fallback?: string): string {
  const index = args.indexOf(name);
  if (index === -1) {
    if (fallback !== undefined) return fallback;
    throw new Error(`${name} is required`);
  }
  const value = args[index + 1];
  if (!value || value.startsWith('--')) throw new Error(`${name} requires a value`);
  return value;
}

function main(argv: string[]): number {
  const [command, ...args] = argv;
  if (!command) throw new Error('Command required: scan, plan, patch, prove, verify, evidence');
  if (command === 'publish') throw new Error('Live publication is gated; no GitHub write path is implemented');
  if (command === 'preview') {
    process.stdout.write(previewRegistered(option(args, '--manifest'), option(args, '--config')));
    return 0;
  }
  if (command === 'export') {
    const summary = exportRegistered(option(args, '--manifest'), option(args, '--config'));
    process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
    return summary.verdict === 'VALIDATION_FAILED' ? 1 : 0;
  }
  if (command === 'verify' || command === 'evidence') {
    const result = args.includes('--config') ? verifyRegistered(option(args, '--manifest'), option(args, '--config')) : verify(option(args, '--manifest'));
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
    return result.verdict === 'VALIDATION_FAILED' ? 1 : 0;
  }
  if (args.includes('--config')) {
    if (args.includes('--fixture') || args.includes('--negative-control')) throw new Error('Registered analysis cannot use fixture options');
    if (command === 'prove') {
      const config = option(args, '--config');
      const result = proveRegistered(config, option(args, '--output', 'artifacts/registered-proof'));
      if (args.includes('--summary')) {
        const destination = resolve(option(args, '--summary'));
        const summary = exportRegistered(resolve(result.folder, 'manifest.json'), config);
        mkdirSync(dirname(destination), { recursive: true });
        writeFileSync(destination, `${JSON.stringify(summary, null, 2)}\n`);
      }
      process.stdout.write(`${JSON.stringify({ folder: result.folder, ...result.evidence }, null, 2)}\n`);
      return result.evidence.verdict === 'VALIDATION_FAILED' ? 1 : 0;
    }
    if (!['scan', 'plan', 'patch'].includes(command)) throw new Error('Registered inputs support scan, plan, patch and prove only');
    const result = command === 'patch' ? proposeRegisteredPath(option(args, '--config')) : analyzeRegistered(option(args, '--config'));
    if ('candidateSource' in result) delete (result as { candidateSource?: string }).candidateSource;
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
    return 0;
  }
  const scenario = option(args, '--fixture', 'path');
  if (command === 'prove') {
    const result = prove(scenario, option(args, '--output', 'artifacts/oss-proof'), args.includes('--negative-control'));
    process.stdout.write(`${JSON.stringify({ folder: result.folder, ...result.evidence }, null, 2)}\n`);
    return result.evidence.verdict === 'VALIDATION_FAILED' ? 1 : 0;
  }
  const prepared = prepare(scenario);
  if (command === 'scan') process.stdout.write(`${JSON.stringify({ scenario, findings: prepared.findings }, null, 2)}\n`);
  else if (command === 'plan') process.stdout.write(`${JSON.stringify({ scenario, recipe: prepared.recipe, verdict: prepared.preliminaryVerdict, reason: prepared.reason }, null, 2)}\n`);
  else if (command === 'patch') process.stdout.write(`${JSON.stringify({ scenario, patch: prepared.patch, verdict: prepared.preliminaryVerdict, reason: prepared.reason }, null, 2)}\n`);
  else throw new Error('Unknown command');
  return 0;
}

try {
  process.exitCode = main(process.argv.slice(2));
} catch (error) {
  process.stderr.write(`${JSON.stringify({ error: error instanceof Error ? error.message : 'Unknown failure' })}\n`);
  process.exitCode = 2;
}
