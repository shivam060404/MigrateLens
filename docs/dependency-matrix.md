# Dependency matrix

Selected direct dependency versions; existing installed libraries used for checks. Full transitive license/security review and clean bootstrap remain open.

| Package | Version | License metadata | Source |
|---|---|---|---|
| fastapi | 0.139.0 | MIT | https://pypi.org/project/fastapi/0.139.0/ |
| uvicorn | 0.51.0 | BSD-3-Clause | https://pypi.org/project/uvicorn/0.51.0/ |
| pydantic | 2.13.4 | MIT | https://pypi.org/project/pydantic/2.13.4/ |
| pydantic-settings | 2.14.2 | MIT | https://pypi.org/project/pydantic-settings/2.14.2/ |
| sqlalchemy | 2.0.51 | MIT | https://pypi.org/project/sqlalchemy/2.0.51/ |
| alembic | 1.18.5 | MIT | https://pypi.org/project/alembic/1.18.5/ |
| httpx | 0.28.1 | BSD-3-Clause | https://pypi.org/project/httpx/0.28.1/ |
| cryptography | 49.0.0 | Apache-2.0 OR BSD-3-Clause | https://pypi.org/project/cryptography/49.0.0/ |
| pyyaml | 6.0.3 | MIT | https://pypi.org/project/pyyaml/6.0.3/ |
| pytest | 9.1.1 | MIT | https://pypi.org/project/pytest/9.1.1/ |
| ruff | 0.15.21 | MIT | https://pypi.org/project/ruff/0.15.21/ |
| mypy | 2.3.0 | MIT | https://pypi.org/project/mypy/2.3.0/ |
| types-PyYAML | 6.0.12.20260518 | Apache-2.0 | https://pypi.org/project/types-PyYAML/6.0.12.20260518/ |
| next | 16.2.12 | MIT | https://www.npmjs.com/package/next/v/16.2.12 |
| react | 19.2.4 | MIT | https://www.npmjs.com/package/react/v/19.2.4 |
| react-dom | 19.2.4 | MIT | https://www.npmjs.com/package/react-dom/v/19.2.4 |
| typescript | 5.9.3 | Apache-2.0 | https://www.npmjs.com/package/typescript/v/5.9.3 |
| ts-morph | 26.0.0 | MIT | https://www.npmjs.com/package/ts-morph/v/26.0.0 |

Runtime: Python 3.14.6; Node 22.23.1; pnpm 11.11.0; uv 0.11.32. Build metadata uses setuptools 83.0.0 and wheel 0.47.0. Runtime/container digests are not resolved.

Primary API references consulted:

- [FastAPI modular applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [Next.js project structure](https://nextjs.org/docs/app/getting-started/project-structure)
- [ts-morph expression API](https://ts-morph.com/details/expressions)
- [uv environment locking](https://docs.astral.sh/uv/pip/compile/)
- [pnpm explicit dependency checks before scripts](https://pnpm.io/settings/build#verifydepsbeforerun)
