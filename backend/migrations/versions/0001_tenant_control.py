"""Initial tenant control plane; frozen SQL is part of this immutable revision."""

from pathlib import Path
from alembic import op

revision = "0001_tenant_control"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute((Path(__file__).with_suffix(".sql")).read_text())


def downgrade():
    raise RuntimeError("Destructive downgrade is disabled; restore a reviewed backup instead")
