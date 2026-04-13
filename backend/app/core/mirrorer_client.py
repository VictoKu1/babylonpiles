"""
Async HTTP client for the internal mirrorer adapter service.
"""

from typing import Any, Dict

import httpx


class MirrorerClient:
    """HTTP client for dispatching mirror runs and fetching logs."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=None, write=None, pool=None)
        )

    async def run_job(
        self,
        run_id: int,
        provider: str,
        variant: str,
        destination_subpath: str,
    ) -> Dict[str, Any]:
        response = await self._client.post(
            f"{self.base_url}/api/v1/run",
            json={
                "run_id": run_id,
                "provider": provider,
                "variant": variant,
                "destination_subpath": destination_subpath,
            },
        )
        response.raise_for_status()
        return response.json()

    async def get_logs(self, run_id: int, tail: int = 40) -> Dict[str, Any]:
        response = await self._client.get(
            f"{self.base_url}/api/v1/runs/{run_id}/logs",
            params={"tail": tail},
        )
        response.raise_for_status()
        return response.json()

    async def health(self) -> Dict[str, Any]:
        response = await self._client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self._client.aclose()
