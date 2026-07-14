import os
import tempfile

import anyio
import httpx
import pytest


class ASGIClient:
    """Synchronous facade over HTTPX ASGITransport without TestClient threads."""

    def __init__(self, app):
        self.app = app

    def request(self, method, url, **kwargs):
        async def send():
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.request(method, url, **kwargs)
        return anyio.run(send)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)


@pytest.fixture()
def client():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["LEGAL_AGENT_DB"] = os.path.join(tmp, "test.db")
        import app.main as main
        main.db = main.Database(os.environ["LEGAL_AGENT_DB"])
        main.service = main.LegalCaseService(main.db)
        main.auth.db = main.db
        main.auth.required = False
        yield ASGIClient(main.app)


@pytest.fixture()
def case(client):
    response = client.post("/api/v1/cases", json={"purpose": "Chuẩn bị chuyển nhượng quyền sử dụng đất"})
    assert response.status_code == 201
    return response.json()
