"""Transaction-local identity; a privileged database connection is never accepted."""

from contextlib import contextmanager
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from src.domain.control import AccessDenied, Membership, Principal, Role
from src.infrastructure.persistence.schema import memberships


class Database:
    def __init__(self, engine: Engine):
        if engine.dialect.name != "postgresql":
            raise ValueError("The control plane requires PostgreSQL")
        self.engine = engine

    @contextmanager
    def transaction(self, principal: Principal, tenant_id: UUID):
        with self.engine.begin() as connection:
            role = (
                connection.execute(
                    sa.text("""
                SELECT r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb
                    OR r.rolreplication AS privileged,
                    current_user <> session_user AS switched,
                    EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                        WHERE n.nspname='ml' AND pg_has_role(current_user,c.relowner,'MEMBER')) AS owns_tables
                FROM pg_roles r WHERE r.rolname=current_user
            """)
                )
                .mappings()
                .one()
            )
            if role["privileged"] or role["switched"] or role["owns_tables"]:
                raise AccessDenied("Runtime database role is privileged or owns application tables")
            connection.execute(
                sa.text(
                    "SELECT set_config('ml.subject', :subject, true), set_config('ml.tenant_id', '', true)"
                ),
                {"subject": principal.subject},
            )
            member = connection.execute(
                sa.select(memberships.c.role).where(
                    memberships.c.tenant_id == tenant_id,
                    memberships.c.subject == principal.subject,
                    memberships.c.active.is_(True),
                )
            ).scalar_one_or_none()
            if member is None:
                raise AccessDenied("Active authenticated membership required")
            connection.execute(
                sa.text("SELECT set_config('ml.tenant_id', :tenant, true)"),
                {"tenant": str(tenant_id)},
            )
            yield connection, Membership(tenant_id, principal.subject, Role(member))
