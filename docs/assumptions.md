# Assumptions register

1. This is a greenfield repository; preserve the supplied specification verbatim.
2. Only fictional fixture code is authorized for local execution. No customer code or credentials are available.
3. Local execution may use a sanitized host subprocess adapter, explicitly lacking a security isolation claim. Customer execution stays disabled until a verified dedicated runner exists.
4. Local identity is a development emulator. Production startup must fail closed; real OIDC is a pilot dependency.
5. Publication defaults to a local PR preview. Live GitHub installation and publication authorization are absent.
6. No cloud provider/account is selected. Paid provisioning, production calls, merge and deployment are outside authorization.
7. Python 3.14 and Node 22 are installed. Use uv and pnpm with exact resolved locks.
8. Docker CLI is installed but its daemon is unavailable at initial inspection. Compose verification is blocked until it runs; use actual host fixture servers for the first slice.
9. Repository has no Git metadata initially. Content hashes identify uncommitted inputs; never invent commit SHAs.
10. User explicitly requested root backend/frontend/infra architecture. ADR 0002 supersedes illustrative source paths in the original specification.
11. Foundation packages use a modular monolith with dependency inversion. Execution and publishing remain separate trust domains; package separation alone is not isolation.
12. Shell can execute installed Python/Node tools but denies local server binding. In-process API tests do not demonstrate network or provider integration.
