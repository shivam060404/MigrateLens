# Container build contract

Build definitions are pending dependency/bootstrap verification. Runtime images must be pinned and recorded, run as a non-root user, contain only their role's application code and locked dependencies, and use separate build/deploy operations.

The repair runtime receives no database, model account, signing or publisher credentials. Ordinary application containers do not establish the pilot sandbox boundary. A dedicated ephemeral VM or equivalent verified isolation remains required.
