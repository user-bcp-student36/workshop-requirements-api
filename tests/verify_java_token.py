from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient


def main() -> None:
    exchange = json.load(sys.stdin)
    with TemporaryDirectory(prefix="reqflow-java-interop-") as temporary:
        directory = Path(temporary)
        public_key = directory / "public.pem"
        public_key.write_text(exchange["publicKey"], encoding="ascii")
        os.environ.update({
            "AUTH_TOKEN_PUBLIC_KEY_LOCATION": str(public_key),
            "AUTH_TOKEN_ISSUER": exchange["issuer"],
            "AUTH_TOKEN_AUDIENCE": exchange["audience"],
            "WORKSHOP_DB_PATH": str(directory / "tasks.db"),
            "WORKSHOP_UPLOAD_DIR": str(directory / "uploads"),
        })
        from app.main import app

        with TestClient(app) as client:
            authorization = "Bearer " + exchange["token"]
            identity = app.state.token_verifier.verify(authorization)
            assert identity == {"username": exchange["username"], "role": exchange["role"]}
            response = client.get("/api/tasks", headers={"Authorization": authorization})
            assert response.status_code == 200
            tasks = response.json()
            assert len(tasks) == exchange["taskCount"]
            assert all(task["owner"] == exchange["username"] for task in tasks)
            summary = client.get("/api/summary", headers={"Authorization": authorization})
            assert summary.status_code == 200
            assert summary.json()["owner"] == exchange["username"]
        print("Java login -> FastAPI verification: PASS")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Java/FastAPI interoperability failed", file=sys.stderr)
        raise SystemExit(1)