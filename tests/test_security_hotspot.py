"""The public request form accepts bounded JSON without granting file access."""
import os
import tempfile
import unittest
from unittest.mock import patch

STATE = tempfile.TemporaryDirectory()
os.environ.setdefault("STATE_DIR", STATE.name)
os.environ.setdefault("SECRET_KEY", "hotspot-test-signing-key-" * 3)
os.environ.setdefault("SERVICE_API_KEY", "hotspot-test-service-key-" * 3)

import httpx
from fastapi import FastAPI
from app.api.v1.endpoints import system


class HotspotTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = FastAPI()
        self.app.include_router(system.public_router, prefix="/api/v1/system")
        self.queue = []
        self.state = patch.dict(system.hotspot_status, {"pending_requests": self.queue})
        self.state.start()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        self.state.stop()

    async def post(self, **changes):
        data = {"filename": "book.txt", "editor_name": "Reader", "client_ip": "192.168.4.100", "client_mac": "00:11:22:33:44:55"}
        data.update(changes)
        return await self.client.post("/api/v1/system/hotspot/request-upload", json=data)

    async def test_exact_frontend_payload_succeeds_and_ids_do_not_collide(self):
        first, second = await self.post(), await self.post()
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(first.json()["data"]["request_id"], second.json()["data"]["request_id"])
        self.assertEqual(self.queue[0]["status"], "pending")
        self.assertEqual(self.queue[0]["filename"], "book.txt")

    async def test_unsafe_filename_and_unbounded_fields_never_enter_queue(self):
        for changes in [{"filename": "../private"}, {"filename": ".permissions.json"}, {"editor_name": "x" * 201}, {"client_mac": "x" * 65}]:
            self.assertEqual((await self.post(**changes)).status_code, 422)
        self.assertEqual(self.queue, [])

    async def test_queue_has_a_fixed_capacity(self):
        self.queue.extend({"id": str(n)} for n in range(1000))
        self.assertEqual((await self.post()).status_code, 429)
        self.assertEqual(len(self.queue), 1000)


if __name__ == "__main__":
    unittest.main()
