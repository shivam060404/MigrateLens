"""Reject misdirected live isolation test connections before any write."""

import pytest

from src.config.database_gate import validate_test_database_urls

BASE = "postgresql+psycopg2://{role}@localhost:5433/migratelens_test"


def test_disposable_pair_accepted():
    assert (
        validate_test_database_urls(
            BASE.format(role="postgres"), BASE.format(role="ml_development")
        )
        == "migratelens_test"
    )


@pytest.mark.parametrize(
    "runtime",
    [
        "postgresql+psycopg2://ml_development@localhost:5433/MigrateLens",
        "postgresql+psycopg2://ml_development@elsewhere:5433/migratelens_test",
        "postgresql+psycopg2://ml_development@localhost:5432/migratelens_test",
        "postgresql+psycopg2://postgres@localhost:5433/migratelens_test",
        "postgresql+psycopg2://ml_development@localhost:5433/migratelens_test?host=elsewhere",
        "postgresql+psycopg2://ml_development@/migratelens_test",
    ],
)
def test_misdirected_pair_rejected(runtime):
    with pytest.raises(ValueError):
        validate_test_database_urls(BASE.format(role="postgres"), runtime)
