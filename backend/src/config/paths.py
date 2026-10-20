"""Repository-owned fixture paths; callers cannot choose customer-code locations."""

from pathlib import Path

# config/paths.py -> src -> backend -> repository root.
ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "fixtures/consumers/northstar/src/integrations/customer/client.ts"
BRIDGE = ROOT / "fixtures/consumers/bridge.mjs"
ANALYZER = ROOT / "backend/analyzer-ts/analyze.mjs"
