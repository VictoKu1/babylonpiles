"""Torrent imports remain unavailable until peer and file policies can be enforced."""
from typing import Dict, Any, Optional, Callable
from app.models.pile import Pile
from app.models.update_log import UpdateLog

DISABLED_MESSAGE = (
    "Torrent imports are disabled; download files with a trusted client and upload them"
)


class TorrentSource:
    async def download(self, pile: Pile, update_log: UpdateLog,
                       progress_callback: Optional[Callable] = None) -> bool:
        update_log.error_message = DISABLED_MESSAGE
        return False

    async def get_available_content(self) -> Dict[str, Any]:
        return {"total_count": 0, "categories": {}, "enabled": False,
                "note": DISABLED_MESSAGE}

    async def cleanup(self):
        pass
