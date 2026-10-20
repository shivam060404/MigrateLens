# Frontend

Next.js application workspace. Routes and layouts live in `src/app/`, feature components in `src/features/`, shared transport code in `src/shared/api/`.

```sh
# From repository root, after bootstrap:
make dev-frontend
```

The development server binds to `127.0.0.1:3000`. The server-side rewrite forwards `/api/v1/*` to the local backend on port 8000. The initial page shows a real connection check and incomplete implementation status. It contains no fabricated cases or metrics.

API types are generated with `make schemas`. Add product case/review screens only after the fixture acceptance path passes. Authentication and tenant-aware UI are future Phase 2/6 work.
