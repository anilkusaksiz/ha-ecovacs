"""Runtime patches for deebot-client."""

from __future__ import annotations

import logging

import deebot_client.hardware.r0321c as upstream_r0321c

from . import r0321c
from .map_outline import apply_map_outline_patch

_LOGGER = logging.getLogger(__name__)

_PATCHED = False


def apply_deebot_patches() -> None:
    """Apply custom deebot-client patches."""
    global _PATCHED

    if _PATCHED:
        return

    # Replace the stock r0321c capability profile with our T30C Gen2 profile.
    upstream_r0321c.get_device_info = r0321c.get_device_info

    # Accept outlineVer=2 in getMapInfo_V2 responses.
    apply_map_outline_patch()

    _PATCHED = True

    _LOGGER.info("Applied custom deebot-client patches")