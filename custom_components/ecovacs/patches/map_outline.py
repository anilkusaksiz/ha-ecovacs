"""Runtime patch for ECOVACS map outline version 2."""

from __future__ import annotations

from typing import Any

from deebot_client.event_bus import EventBus
from deebot_client.events.map import MapInfoEvent
from deebot_client.message import HandlingResult
from deebot_client.messages.json.map import OnMapInfoV2


def _handle_body_data_dict(
    cls: type[OnMapInfoV2],
    event_bus: EventBus,
    data: dict[str, Any],
) -> HandlingResult:
    """Handle map info versions supported by newer ECOVACS models."""
    if (outline_version := data.get("outlineVer")) == "0":
        return HandlingResult.success()

    if outline_version not in ("1", "2"):
        return HandlingResult.analyse()

    event_bus.notify(
        MapInfoEvent(
            map_id=data["mid"],
            info=data["info"],
        )
    )
    return HandlingResult.success()


def apply_map_outline_patch() -> None:
    """Apply support for map outline version 2."""
    OnMapInfoV2._handle_body_data_dict = classmethod(_handle_body_data_dict)