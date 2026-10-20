import { analyzeSource } from './recipes.mjs';
const [scenario, mode = 'analyze'] = process.argv.slice(2);
const chunks = [];
let size = 0;
for await (const chunk of process.stdin) {
  size += chunk.length;
  if (size > 65536) throw new Error('Source exceeds analysis byte budget');
  chunks.push(chunk);
}
process.stdout.write(JSON.stringify(analyzeSource(Buffer.concat(chunks).toString('utf8'), scenario, mode)));
