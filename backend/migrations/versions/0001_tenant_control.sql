-- Frozen revision 0001. Do not regenerate after deployment.

CREATE SCHEMA ml;

REVOKE ALL ON SCHEMA ml FROM PUBLIC;

GRANT USAGE ON SCHEMA ml TO ml_runtime;

CREATE TABLE ml.tenants (
	tenant_id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_tenants PRIMARY KEY (tenant_id)
);

ALTER TABLE ml.tenants ENABLE ROW LEVEL SECURITY;

ALTER TABLE ml.tenants FORCE ROW LEVEL SECURITY;


REVOKE ALL ON ml.tenants FROM PUBLIC;

GRANT SELECT ON ml.tenants TO ml_runtime;

CREATE TABLE ml.audit_events (
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	subject VARCHAR(128) NOT NULL, 
	action VARCHAR(80) NOT NULL, 
	resource_id UUID NOT NULL, 
	correlation_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_audit_events PRIMARY KEY (tenant_id, id), 
	CONSTRAINT fk_audit_events_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES ml.tenants (tenant_id)
);

ALTER TABLE ml.audit_events ENABLE ROW LEVEL SECURITY;

ALTER TABLE ml.audit_events FORCE ROW LEVEL SECURITY;


REVOKE ALL ON ml.audit_events FROM PUBLIC;

GRANT SELECT, INSERT ON ml.audit_events TO ml_runtime;

CREATE TABLE ml.budgets (
	tenant_id UUID NOT NULL, 
	limit_microusd BIGINT NOT NULL, 
	reserved_microusd BIGINT DEFAULT '0' NOT NULL, 
	spent_microusd BIGINT DEFAULT '0' NOT NULL, 
	CONSTRAINT pk_budgets PRIMARY KEY (tenant_id), 
	CONSTRAINT fk_budgets_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES ml.tenants (tenant_id), 
	CONSTRAINT nonnegative_budget CHECK (limit_microusd >= 0 AND reserved_microusd >= 0 AND spent_microusd >= 0)
);

ALTER TABLE ml.budgets ENABLE ROW LEVEL SECURITY;

ALTER TABLE ml.budgets FORCE ROW LEVEL SECURITY;


REVOKE ALL ON ml.budgets FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE ON ml.budgets TO ml_runtime;

CREATE TABLE ml.memberships (
	tenant_id UUID NOT NULL, 
	subject VARCHAR(128) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	active BOOLEAN DEFAULT true NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_memberships PRIMARY KEY (tenant_id, subject), 
	CONSTRAINT fk_memberships_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES ml.tenants (tenant_id), 
	CONSTRAINT membership_role CHECK (role IN ('owner','maintainer','reviewer','viewer','worker'))
);

ALTER TABLE ml.memberships ENABLE ROW LEVEL SECURITY;

ALTER TABLE ml.memberships FORCE ROW LEVEL SECURITY;


REVOKE ALL ON ml.memberships FROM PUBLIC;

GRANT SELECT ON ml.memberships TO ml_runtime;

CREATE TABLE ml.providers (
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	classification VARCHAR(30) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_providers PRIMARY KEY (tenant_id, id), 
	CONSTRAINT fk_providers_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES ml.tenants (tenant_id), 
	CONSTRAINT provider_test_only CHECK (classification IN ('fictional','internal_test'))
);

ALTER TABLE ml.providers ENABLE ROW LEVEL SECURITY;

ALTER TABLE ml.providers FORCE ROW LEVEL SECURITY;


REVOKE ALL ON ml.providers FROM PUBLIC;

GRANT SELECT ON ml.providers TO ml_runtime;

CREATE TABLE ml.repositories (
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	enabled BOOLEAN DEFAULT true NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_repositories PRIMARY KEY (tenant_id, id), 
	CONSTRAINT fk_repositories_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES ml.tenants (tenant_id)
);

ALTER TABLE ml.repositories ENABLE ROW LEVEL SECURITY;

ALTER TABLE ml.repositories FORCE ROW LEVEL SECURITY;


REVOKE ALL ON ml.repositories FROM PUBLIC;

GRANT SELECT ON ml.repositories TO ml_runtime;

CREATE TABLE ml.bindings (
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	repository_id UUID NOT NULL, 
	provider_id UUID NOT NULL, 
	declared_version VARCHAR(100) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_bindings PRIMARY KEY (tenant_id, id), 
	CONSTRAINT fk_bindings_tenant_id_repositories FOREIGN KEY(tenant_id, repository_id) REFERENCES ml.repositories (tenant_id, id), 
	CONSTRAINT fk_bindings_tenant_id_providers FOREIGN KEY(tenant_id, provider_id) REFERENCES ml.providers (tenant_id, id), 
	CONSTRAINT uq_binding_repository UNIQUE (tenant_id, repository_id, id)
);

ALTER TABLE ml.bindings ENABLE ROW LEVEL SECURITY;

ALTER TABLE ml.bindings FORCE ROW LEVEL SECURITY;


REVOKE ALL ON ml.bindings FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE ON ml.bindings TO ml_runtime;

CREATE TABLE ml.repository_grants (
	tenant_id UUID NOT NULL, 
	repository_id UUID NOT NULL, 
	subject VARCHAR(128) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_repository_grants PRIMARY KEY (tenant_id, repository_id, subject), 
	CONSTRAINT fk_repository_grants_tenant_id_repositories FOREIGN KEY(tenant_id, repository_id) REFERENCES ml.repositories (tenant_id, id), 
	CONSTRAINT fk_repository_grants_tenant_id_memberships FOREIGN KEY(tenant_id, subject) REFERENCES ml.memberships (tenant_id, subject)
);

ALTER TABLE ml.repository_grants ENABLE ROW LEVEL SECURITY;

ALTER TABLE ml.repository_grants FORCE ROW LEVEL SECURITY;


REVOKE ALL ON ml.repository_grants FROM PUBLIC;

GRANT SELECT ON ml.repository_grants TO ml_runtime;

CREATE TABLE ml.cases (
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	repository_id UUID NOT NULL, 
	binding_id UUID NOT NULL, 
	identity_hash VARCHAR(64) NOT NULL, 
	base_sha VARCHAR(40) NOT NULL, 
	old_contract_hash VARCHAR(64) NOT NULL, 
	new_contract_hash VARCHAR(64) NOT NULL, 
	policy_hash VARCHAR(64) NOT NULL, 
	revision INTEGER DEFAULT '1' NOT NULL, 
	version INTEGER DEFAULT '1' NOT NULL, 
	state VARCHAR(30) DEFAULT 'RECEIVED' NOT NULL, 
	cancel_requested BOOLEAN DEFAULT false NOT NULL, 
	verdict VARCHAR(40), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_cases PRIMARY KEY (tenant_id, id), 
	CONSTRAINT fk_cases_tenant_id_bindings FOREIGN KEY(tenant_id, repository_id, binding_id) REFERENCES ml.bindings (tenant_id, repository_id, id), 
	CONSTRAINT uq_case_repository UNIQUE (tenant_id, repository_id, id), 
	CONSTRAINT uq_case_identity UNIQUE (tenant_id, binding_id, identity_hash), 
	CONSTRAINT case_versions CHECK (revision > 0 AND version > 0), 
	CONSTRAINT case_state CHECK (state IN ('RECEIVED','ANALYZING','WAITING_FOR_INPUT','READY_TO_REPAIR','REPAIRING','VALIDATING','AWAITING_REVIEW','PUBLISHING','PUBLISHED','COMPLETED','FAILED','CANCELLED'))
);

ALTER TABLE ml.cases ENABLE ROW LEVEL SECURITY;

ALTER TABLE ml.cases FORCE ROW LEVEL SECURITY;


REVOKE ALL ON ml.cases FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE ON ml.cases TO ml_runtime;

CREATE TABLE ml.artifacts (
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	size_bytes BIGINT NOT NULL, 
	object_key VARCHAR(300) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_artifacts PRIMARY KEY (tenant_id, id), 
	CONSTRAINT fk_artifacts_tenant_id_cases FOREIGN KEY(tenant_id, case_id) REFERENCES ml.cases (tenant_id, id), 
	CONSTRAINT uq_artifact_object UNIQUE (tenant_id, object_key), 
	CONSTRAINT artifact_size CHECK (size_bytes BETWEEN 0 AND 10000000)
);

ALTER TABLE ml.artifacts ENABLE ROW LEVEL SECURITY;

ALTER TABLE ml.artifacts FORCE ROW LEVEL SECURITY;


REVOKE ALL ON ml.artifacts FROM PUBLIC;

GRANT SELECT, INSERT ON ml.artifacts TO ml_runtime;

CREATE TABLE ml.case_events (
	tenant_id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	sequence INTEGER NOT NULL, 
	kind VARCHAR(80) NOT NULL, 
	payload JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_case_events PRIMARY KEY (tenant_id, case_id, sequence), 
	CONSTRAINT fk_case_events_tenant_id_cases FOREIGN KEY(tenant_id, case_id) REFERENCES ml.cases (tenant_id, id)
);

ALTER TABLE ml.case_events ENABLE ROW LEVEL SECURITY;

ALTER TABLE ml.case_events FORCE ROW LEVEL SECURITY;


REVOKE ALL ON ml.case_events FROM PUBLIC;

GRANT SELECT, INSERT ON ml.case_events TO ml_runtime;

CREATE TABLE ml.jobs (
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	attempt INTEGER NOT NULL, 
	state VARCHAR(20) DEFAULT 'QUEUED' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_jobs PRIMARY KEY (tenant_id, id), 
	CONSTRAINT fk_jobs_tenant_id_cases FOREIGN KEY(tenant_id, case_id) REFERENCES ml.cases (tenant_id, id), 
	CONSTRAINT uq_case_attempt UNIQUE (tenant_id, case_id, attempt), 
	CONSTRAINT attempt_bounds CHECK (attempt BETWEEN 1 AND 3), 
	CONSTRAINT job_state CHECK (state IN ('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED'))
);

ALTER TABLE ml.jobs ENABLE ROW LEVEL SECURITY;

ALTER TABLE ml.jobs FORCE ROW LEVEL SECURITY;


REVOKE ALL ON ml.jobs FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE ON ml.jobs TO ml_runtime;

CREATE TABLE ml.outbox (
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	case_version INTEGER NOT NULL, 
	kind VARCHAR(80) NOT NULL, 
	state VARCHAR(20) DEFAULT 'PENDING' NOT NULL, 
	attempts INTEGER DEFAULT '0' NOT NULL, 
	available_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	lease_until TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_outbox PRIMARY KEY (tenant_id, id), 
	CONSTRAINT fk_outbox_tenant_id_cases FOREIGN KEY(tenant_id, case_id) REFERENCES ml.cases (tenant_id, id), 
	CONSTRAINT uq_outbox_event UNIQUE (tenant_id, case_id, case_version, kind), 
	CONSTRAINT dispatch_attempts CHECK (attempts BETWEEN 0 AND 3), 
	CONSTRAINT outbox_state CHECK (state IN ('PENDING','LEASED','DELIVERED','DEAD'))
);

ALTER TABLE ml.outbox ENABLE ROW LEVEL SECURITY;

ALTER TABLE ml.outbox FORCE ROW LEVEL SECURITY;


REVOKE ALL ON ml.outbox FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE ON ml.outbox TO ml_runtime;

CREATE TABLE ml.reservations (
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	job_id UUID NOT NULL, 
	estimate_microusd BIGINT NOT NULL, 
	actual_microusd BIGINT, 
	settled BOOLEAN DEFAULT false NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_reservations PRIMARY KEY (tenant_id, id), 
	CONSTRAINT fk_reservations_tenant_id_jobs FOREIGN KEY(tenant_id, job_id) REFERENCES ml.jobs (tenant_id, id), 
	CONSTRAINT uq_job_reservation UNIQUE (tenant_id, job_id), 
	CONSTRAINT reservation_amounts CHECK (estimate_microusd > 0 AND (actual_microusd IS NULL OR actual_microusd >= 0))
);

ALTER TABLE ml.reservations ENABLE ROW LEVEL SECURITY;

ALTER TABLE ml.reservations FORCE ROW LEVEL SECURITY;


REVOKE ALL ON ml.reservations FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE ON ml.reservations TO ml_runtime;

CREATE INDEX ix_outbox_dispatch ON ml.outbox (tenant_id, state, available_at);

CREATE INDEX ix_cases_repository ON ml.cases (tenant_id, repository_id, created_at);

-- Install policies after every referenced table exists.
CREATE POLICY tenant_scope ON ml.tenants USING (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = tenants.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active)) WITH CHECK (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = tenants.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active));

CREATE POLICY tenant_scope ON ml.audit_events USING (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = audit_events.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active)) WITH CHECK (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = audit_events.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active));

CREATE POLICY tenant_scope ON ml.budgets USING (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = budgets.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active)) WITH CHECK (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = budgets.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active));

CREATE POLICY tenant_scope ON ml.memberships USING (subject = current_setting('ml.subject', true) AND active AND (NULLIF(current_setting('ml.tenant_id', true), '') IS NULL OR tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid)) WITH CHECK (subject = current_setting('ml.subject', true) AND active AND (NULLIF(current_setting('ml.tenant_id', true), '') IS NULL OR tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid));

CREATE POLICY tenant_scope ON ml.providers USING (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = providers.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active)) WITH CHECK (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = providers.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active));

CREATE POLICY tenant_scope ON ml.repositories USING (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = repositories.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active)) WITH CHECK (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = repositories.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active));

CREATE POLICY tenant_scope ON ml.bindings USING (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = bindings.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active)) WITH CHECK (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = bindings.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active));

CREATE POLICY tenant_scope ON ml.repository_grants USING (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = repository_grants.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active) AND subject = current_setting('ml.subject', true)) WITH CHECK (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = repository_grants.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active) AND subject = current_setting('ml.subject', true));

CREATE POLICY tenant_scope ON ml.cases USING (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = cases.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active)) WITH CHECK (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = cases.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active));

CREATE POLICY tenant_scope ON ml.artifacts USING (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = artifacts.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active)) WITH CHECK (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = artifacts.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active));

CREATE POLICY tenant_scope ON ml.case_events USING (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = case_events.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active)) WITH CHECK (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = case_events.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active));

CREATE POLICY tenant_scope ON ml.jobs USING (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = jobs.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active)) WITH CHECK (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = jobs.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active));

CREATE POLICY tenant_scope ON ml.outbox USING (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = outbox.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active)) WITH CHECK (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = outbox.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active));

CREATE POLICY tenant_scope ON ml.reservations USING (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = reservations.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active)) WITH CHECK (tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid AND EXISTS (SELECT 1 FROM ml.memberships m WHERE m.tenant_id = reservations.tenant_id AND m.subject = current_setting('ml.subject', true) AND m.active));
