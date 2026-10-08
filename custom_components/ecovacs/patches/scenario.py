"""Scenario clean ("Quick Command") support for deebot-client.

The ECOVACS app calls these "Scenario Clean". They are saved cleaning
presets, listed with ``getQuickCommand`` and started with ``clean_V2``
using the ``qcClean`` content type and the scenario's ``qcid``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from deebot_client.capabilities import Capabilities, CapabilityEvent
from deebot_client.commands.json.clean import CleanV2
from deebot_client.commands.json.common import JsonCommandWithMessageHandling
from deebot_client.events import Event
from deebot_client.message import HandlingResult, MessageBodyDataList
from deebot_client.models import CleanAction

if TYPE_CHECKING:
    from deebot_client.command import Command
    from deebot_client.event_bus import EventBus

SCENARIO_CLEAN_TYPE = "qcClean"


@dataclass(frozen=True)
class Scenario:
    """Scenario clean preset."""

    id: str
    name: str
    icon: str | None = None
    map_id: str | None = None


@dataclass(frozen=True)
class ScenariosEvent(Event):
    """Scenario clean presets event."""

    scenarios: tuple[Scenario, ...]


class GetScenarios(JsonCommandWithMessageHandling, MessageBodyDataList):
    """Get scenario clean presets command."""

    NAME = "getQuickCommand"

    def __init__(self) -> None:
        super().__init__({"type": "1,2"})

    @classmethod
    def _handle_body_data_list(
        cls, event_bus: EventBus, data: list[dict[str, Any]]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        scenarios: dict[str, Scenario] = {}
        for group in data:
            for item in group.get("array", []):
                scenario_id = str(item["qcid"])
                scenarios[scenario_id] = Scenario(
                    id=scenario_id,
                    name=item.get("name") or scenario_id,
                    icon=item.get("icon"),
                    map_id=item.get("mid") or group.get("mid"),
                )

        event_bus.notify(ScenariosEvent(tuple(scenarios.values())))
        return HandlingResult.success()


class CleanScenario(CleanV2):
    """Start a scenario clean preset."""

    def __init__(self, scenario_id: str) -> None:
        self._scenario_id = scenario_id
        super().__init__(CleanAction.START)

    def _get_args(self, action: CleanAction) -> dict[str, Any]:
        # Always start the scenario, even when Clean._execute asks to resume a
        # paused job, so the button runs the preset that was pressed.
        return {
            "act": CleanAction.START.value,
            "content": {"type": SCENARIO_CLEAN_TYPE, "value": self._scenario_id},
        }


@dataclass(frozen=True)
class CapabilityScenario(CapabilityEvent[ScenariosEvent]):
    """Capability to list and start scenario clean presets."""

    start: Callable[[str], Command]


@dataclass(frozen=True, kw_only=True)
class ScenarioCapabilities(Capabilities):
    """Capabilities with scenario clean support."""

    scenario: CapabilityScenario | None = None


def get_scenario_capability(capabilities: Capabilities) -> CapabilityScenario | None:
    """Return the scenario capability, if the device supports it."""
    return getattr(capabilities, "scenario", None)
