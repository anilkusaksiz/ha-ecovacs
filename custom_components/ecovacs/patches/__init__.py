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

    upstream_r0321c.get_device_info = r0321c.get_device_info
    apply_map_outline_patch()

    caps = upstream_r0321c.get_device_info().capabilities

    _LOGGER.warning(
        "T30C patch active: clean=%s area=%s map=%s station_actions=%s",
        caps.clean.action.command.__name__,
        caps.clean.action.area.__name__,
        caps.map.set.execute.__name__ if caps.map and caps.map.set else None,
        [action.name for action in caps.station.action.types],
    )

    _PATCHED = True