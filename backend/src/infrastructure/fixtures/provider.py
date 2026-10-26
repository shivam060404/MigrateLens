"""Resettable synthetic HTTP provider. No production/network source fetching."""

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit


@contextmanager
def provider(scenario: str, version: str):
    if scenario not in {"path", "field", "query"} or version not in {"old", "new"}:
        raise ValueError("Only registered supported provider versions may run")
    interactions: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            parsed = urlsplit(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            interactions.append({"method": "GET", "path": path, "query": query})
            status = 200
            body: object
            prefix = (
                "/v2/customers/" if scenario == "path" and version == "new" else "/v1/customers/"
            )
            if path == "/customers":
                key = "limit" if scenario == "query" and version == "new" else "pageSize"
                if any(k != key for k in query):
                    status, body = 400, {"error": "unknown query parameter"}
                else:
                    try:
                        size = int(query.get(key, ["2"])[0])
                        if not 1 <= size <= 3:
                            raise ValueError()
                        body = {"items": [{"id": i} for i in ["ada", "null", "missing"][:size]]}
                    except ValueError:
                        status, body = 400, {"error": "invalid page size"}
            elif path.startswith(prefix):
                identifier = unquote(path[len(prefix) :])
                if identifier == "boom":
                    status, body = 503, {"error": "fixture unavailable"}
                elif identifier not in {"ada", "null", "missing", "a/b ?"}:
                    status, body = 404, {"error": "not found"}
                else:
                    customer: dict[str, object] = {
                        "id": identifier,
                        "tier": "standard",
                        "unrelated": {"name": "unrelated-company"},
                    }
                    name = None if identifier == "null" else "Ada Lovelace"
                    if scenario == "field" and version == "new":
                        customer["profile"] = (
                            {} if identifier == "missing" else {"displayName": name}
                        )
                    elif identifier != "missing":
                        customer["name"] = name
                    body = customer
            else:
                status, body = 404, {"error": "not found"}
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("X-Fixture-Build", f"northstar-{scenario}-{version}-1")
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", interactions
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
