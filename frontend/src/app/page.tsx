import { SystemStatus } from "@/features/system-status/SystemStatus";

export default function Home() {
  return <main>
    <p className="label">Local reference · Fictional fixtures only</p>
    <h1>MigrateLens</h1>
    <p className="intro">API Compatibility &amp; Repair Intelligence</p>
    <p>Detect the change. Understand the impact. Verify the fix.</p>
    <SystemStatus />
    <section><h2>Implementation status</h2>
      <p>The migration CLI and evidence contracts are under development. Provider verification,
        tenant workflows, and publication gates must pass before a pilot is enabled.</p>
      <p>No customer repositories are connected. No pull requests are published.</p>
    </section>
  </main>;
}
