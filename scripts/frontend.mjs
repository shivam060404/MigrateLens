/** Invoke the installed workspace Next CLI without downloading tools implicitly. */
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const frontend = fileURLToPath(new URL("../frontend/", import.meta.url));
const require = createRequire(new URL("../frontend/package.json", import.meta.url));
const command = process.argv[2];
if (!["typegen", "build"].includes(command) || process.argv.length !== 3) {
  throw new Error("Usage: node scripts/frontend.mjs typegen|build");
}
const args = [require.resolve("next/dist/bin/next"), command, frontend];
if (command === "build") args.push("--webpack");
const result = spawnSync(process.execPath, args, { stdio: "inherit" });
if (result.error) throw result.error;
process.exit(result.status ?? 1);
