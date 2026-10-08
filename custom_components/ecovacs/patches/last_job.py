"""Last job report for devices that do not send reportStats.

The T30C never sends ``reportStats``, which is what the "Last job" event
entity listens for. At the end of every job it sends ``onLastTimeStats``
(area, time, scenario name) instead. A job that finishes on its own is
preceded by ``onEvt`` with code 1021; a job stopped from the app is not.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import TYPE_CHECKING, Any

import deebot_client.messages.json as json_messages
from deebot_client.events import CleanJobStatus, Event, ReportStatsEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

CLEAN_FINISHED_CODE = 1021

# onEvt and onLastTimeStats arrive within milliseconds of each other.
_FINISHED_WINDOW_SECONDS = 60


@dataclass(frozen=True)
class CleanFinishedEvent(Event):
    """The device reported that a cleaning job finished on its own."""

    monotonic_time: float


class OnEvt(MessageBodyDataDict):
    """Device event message."""

    NAME = "onEvt"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if data.get("code") == CLEAN_FINISHED_CODE:
            event_bus.notify(CleanFinishedEvent(monotonic()))
            return HandlingResult.success()

        return HandlingResult.analyse()


class OnLastTimeStats(MessageBodyDataDict):
    """Summary of the job that just ended."""

    NAME = "onLastTimeStats"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        finished = event_bus.get_last_event(CleanFinishedEvent)
        if (
            finished
            and monotonic() - finished.monotonic_time < _FINISHED_WINDOW_SECONDS
        ):
            status = CleanJobStatus.FINISHED
        else:
            status = CleanJobStatus.MANUALLY_STOPPED

        event_bus.notify(
            ReportStatsEvent(
                area=data.get("area"),
                time=data.get("time"),
                type=data.get("type"),
                cleaning_id=str(data.get("start", "")),
                status=status,
                content=[],
            )
        )
        return HandlingResult.success()


def apply_last_job_patch() -> None:
    """Register the messages with deebot-client."""
    for message in (OnEvt, OnLastTimeStats):
        json_messages.MESSAGES.setdefault(message.NAME, message)
