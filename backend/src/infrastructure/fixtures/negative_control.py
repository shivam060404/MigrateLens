"""Known, digest-approved negative control used only by the synthetic benchmark/tests."""

from src.application.ports import Analyzer


class IncorrectTierAnalyzer:
    def __init__(self, delegate: Analyzer):
        self.delegate = delegate

    def analyze(self, source: str, scenario: str, repair: bool = False) -> dict:
        result = self.delegate.analyze(source, scenario, repair)
        if repair:
            result = {
                **result,
                "source": result["source"].replace("tier: customer.tier", 'tier: "wrong-tier"'),
            }
        return result
