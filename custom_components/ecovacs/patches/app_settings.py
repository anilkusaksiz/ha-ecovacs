"""T30C settings from the ECOVACS app that deebot-client does not cover.

Every command here was checked against a T30C Omni Gen2 (firmware 1.41.0).
The robot announces each change with an ``on<Name>`` message, so the
set commands do not need to read the value back themselves.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from time import monotonic
from typing import TYPE_CHECKING, Any

import deebot_client.messages.json as json_messages
from deebot_client.capabilities import CapabilitySetEnable, CapabilitySetTypes
from deebot_client.commands.json.auto_empty import GetAutoEmpty, SetAutoEmpty
from deebot_client.commands.json.common import ExecuteCommand, JsonGetCommand
from deebot_client.events import EnableEvent, Event
from deebot_client.events.auto_empty import AutoEmptyEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.messages.json.auto_empty import OnAutoEmpty

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo


# --- Events -----------------------------------------------------------------


@dataclass(frozen=True)
class MopExpandEvent(EnableEvent):
    """TruEdge adaptive edge mopping."""


@dataclass(frozen=True)
class CleaningSolutionEvent(EnableEvent):
    """Intelligent addition of cleaning solution."""


@dataclass(frozen=True)
class DoNotDisturbEvent(EnableEvent):
    """Do not disturb."""


@dataclass(frozen=True)
class OffPeakChargingEvent(EnableEvent):
    """Off-peak charging. The robot needs the window on every change."""

    start: str
    end: str


@dataclass(frozen=True)
class DryMopEvent(EnableEvent):
    """Forced operation without water."""


@dataclass(frozen=True)
class CarpetFirstEvent(EnableEvent):
    """Clean carpets first."""


@dataclass(frozen=True)
class CarpetFineEvent(EnableEvent):
    """Carpet fine cleaning."""


@dataclass(frozen=True)
class FloorDirectionEvent(EnableEvent):
    """Clean along the floor."""


@dataclass(frozen=True)
class WashModeEvent(Event):
    """Mop wash method."""

    value: str


@dataclass(frozen=True)
class WashFrequencyEvent(Event):
    """Mop auto-wash frequency."""

    value: str


@dataclass(frozen=True)
class DryingDurationEvent(Event):
    """Hot air drying duration."""

    value: str


@dataclass(frozen=True)
class DustPowerEvent(Event):
    """Dust collection power."""

    value: str


@dataclass(frozen=True)
class CarpetRecognitionEvent(Event):
    """Carpet recognition sensitivity."""

    value: str


@dataclass(frozen=True)
class SwitchStatePushEvent(Event):
    """Keys the robot reported in its last onSwitchState message."""

    keys: frozenset[str]
    monotonic_time: float


# --- Option mappings --------------------------------------------------------

WASH_MODES = {"eco": 0, "standard": 1, "deep": 2}
DRYING_DURATIONS = {"two_hours": 120, "three_hours": 180, "four_hours": 240}
DUST_POWERS = {"quiet": 0, "standard": 1}
CARPET_RECOGNITION = {"standard": 0, "sensitive": 1}
WASH_BY_ROOM = "by_room"
WASH_INTERVALS = {"every_10_min": 10, "every_15_min": 15, "every_25_min": 25}
WASH_FREQUENCIES = (WASH_BY_ROOM, *WASH_INTERVALS)


def _option(mapping: dict[str, int], value: Any) -> str | None:
    """Return the option name for a raw value, if known."""
    for option, raw in mapping.items():
        if raw == value:
            return option
    return None


# --- Commands ---------------------------------------------------------------


class _SetCommand(ExecuteCommand, ABC):
    """Set command whose result arrives as an on<Name> message."""


_ENABLE_MESSAGES: list[type[MessageBodyDataDict]] = []


def _enable_commands(
    name: str, event: type[EnableEvent]
) -> tuple[type[JsonGetCommand], type[_SetCommand]]:
    """Build the get/set pair for a setting that only has ``enable``."""

    class OnSetting(MessageBodyDataDict):
        NAME = f"on{name}"

        @classmethod
        def _handle_body_data_dict(
            cls, event_bus: EventBus, data: dict[str, Any]
        ) -> HandlingResult:
            event_bus.notify(event(bool(data["enable"])))
            return HandlingResult.success()

    class GetSetting(OnSetting, JsonGetCommand):
        NAME = f"get{name}"

    class SetSetting(_SetCommand):
        NAME = f"set{name}"

        def __init__(self, enable: bool) -> None:
            super().__init__({"enable": int(enable)})

    _ENABLE_MESSAGES.append(OnSetting)
    return GetSetting, SetSetting


GetMopExpand, SetMopExpand = _enable_commands("MopExpandState", MopExpandEvent)
GetCleaningSolution, SetCleaningSolution = _enable_commands(
    "CfState", CleaningSolutionEvent
)
GetDoNotDisturb, SetDoNotDisturb = _enable_commands("Block", DoNotDisturbEvent)


class OnChargeTime(MessageBodyDataDict):
    """Off-peak charging message."""

    NAME = "onChargeTime"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers."""
        event_bus.notify(
            OffPeakChargingEvent(bool(data["enable"]), data["start"], data["end"])
        )
        return HandlingResult.success()


class GetOffPeakCharging(OnChargeTime, JsonGetCommand):
    """Get off-peak charging."""

    NAME = "getChargeTime"


class SetOffPeakCharging(_SetCommand):
    """Set off-peak charging, keeping the charging window."""

    NAME = "setChargeTime"

    def __init__(self, enable: bool) -> None:
        super().__init__({"enable": int(enable)})

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[HandlingResult, dict[str, Any]]:
        # The robot rejects the change without the window ("start or end is null").
        if last := event_bus.get_last_event(OffPeakChargingEvent):
            self._args.update(start=last.start, end=last.end)
        return await super()._execute(authenticator, device_info, event_bus)


class OnWashInfo(MessageBodyDataDict):
    """Mop wash settings message."""

    NAME = "onWashInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers."""
        if (mode := _option(WASH_MODES, data.get("mode"))) is not None:
            event_bus.notify(WashModeEvent(mode))
        if data.get("wiseMode") == 1:
            event_bus.notify(WashFrequencyEvent(WASH_BY_ROOM))
        elif (interval := _option(WASH_INTERVALS, data.get("interval"))) is not None:
            event_bus.notify(WashFrequencyEvent(interval))
        if "dryMop" in data:
            event_bus.notify(DryMopEvent(bool(data["dryMop"])))
        return HandlingResult.success()


class GetWashSettings(OnWashInfo, JsonGetCommand):
    """Get mop wash settings."""

    NAME = "getWashInfo"


class SetWashSettings(_SetCommand):
    """Set mop wash settings."""

    NAME = "setWashInfo"


def set_wash_mode(option: str) -> SetWashSettings:
    """Set the mop wash method."""
    return SetWashSettings({"mode": WASH_MODES[option]})


def set_wash_frequency(option: str) -> SetWashSettings:
    """Wash the mop after each room or every N minutes."""
    if option == WASH_BY_ROOM:
        return SetWashSettings({"wiseMode": 1})
    return SetWashSettings({"wiseMode": 0, "interval": WASH_INTERVALS[option]})


def set_dry_mop(enable: bool) -> SetWashSettings:
    """Allow mopping without washing when the water tanks need attention."""
    return SetWashSettings({"dryMop": int(enable)})


class OnDryingDuration(MessageBodyDataDict):
    """Hot air drying duration message."""

    NAME = "onDryingDuration"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers."""
        if (option := _option(DRYING_DURATIONS, data.get("duration"))) is not None:
            event_bus.notify(DryingDurationEvent(option))
        return HandlingResult.success()


class GetDryingDuration(OnDryingDuration, JsonGetCommand):
    """Get hot air drying duration."""

    NAME = "getDryingDuration"


class SetDryingDuration(_SetCommand):
    """Set hot air drying duration."""

    NAME = "setDryingDuration"

    def __init__(self, option: str) -> None:
        super().__init__({"duration": DRYING_DURATIONS[option]})


class OnAutoEmptyWithPower(OnAutoEmpty):
    """Auto-empty message that also reports the dust collection power."""

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers."""
        if (power := _option(DUST_POWERS, data.get("intensity"))) is not None:
            event_bus.notify(DustPowerEvent(power))
        return super()._handle_body_data_dict(event_bus, data)


class GetAutoEmptyWithPower(OnAutoEmptyWithPower, GetAutoEmpty):
    """Get auto-empty settings including the dust collection power."""


class SetDustPower(_SetCommand):
    """Set the dust collection power, keeping auto-empty on or off."""

    NAME = "setAutoEmpty"

    def __init__(self, option: str) -> None:
        super().__init__({"intensity": DUST_POWERS[option]})

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[HandlingResult, dict[str, Any]]:
        # The robot rejects the change without "enable" ("get act fail").
        last = event_bus.get_last_event(AutoEmptyEvent)
        self._args["enable"] = int(last.enabled) if last else 1
        return await super()._execute(authenticator, device_info, event_bus)


# Settings without a working get command. The robot reports them in
# onSwitchState when they change and in the onFwBuryPoint-common-setting
# snapshot it sends after any setting change.
SWITCH_STATE_EVENTS: dict[str, type[EnableEvent]] = {
    "carpetCleaningFirst": CarpetFirstEvent,
    "carpetCleaningFine": CarpetFineEvent,
    "floorDirectionClean": FloorDirectionEvent,
}
CARPET_RECOGNITION_KEY = "ultrasonicRecognizeLevel"

# The snapshot is taken just before a change is applied, so it can report
# the old value right after onSwitchState reported the new one.
_SNAPSHOT_LAG_SECONDS = 10


def _notify_switch_state(event_bus: EventBus, key: str, value: Any) -> None:
    if event := SWITCH_STATE_EVENTS.get(key):
        event_bus.notify(event(bool(value)))
    elif key == CARPET_RECOGNITION_KEY:
        if (option := _option(CARPET_RECOGNITION, value)) is not None:
            event_bus.notify(CarpetRecognitionEvent(option))


class OnSwitchState(MessageBodyDataDict):
    """Switch state change message."""

    NAME = "onSwitchState"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers."""
        event_bus.notify(SwitchStatePushEvent(frozenset(data), monotonic()))
        for key, value in data.items():
            _notify_switch_state(event_bus, key, value)
        return HandlingResult.success()


class OnSettingsSnapshot(MessageBodyDataDict):
    """Settings snapshot the robot sends after any setting change."""

    NAME = "onFwBuryPoint-common-setting"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers."""
        recent: frozenset[str] = frozenset()
        if (push := event_bus.get_last_event(SwitchStatePushEvent)) and (
            monotonic() - push.monotonic_time < _SNAPSHOT_LAG_SECONDS
        ):
            recent = push.keys

        for key in (*SWITCH_STATE_EVENTS, CARPET_RECOGNITION_KEY):
            if key in recent or not isinstance(entry := data.get(key), dict):
                continue
            for value in entry.get("values", []):
                if value.get("name") == "isOn" and "valueInt" in value:
                    _notify_switch_state(event_bus, key, value["valueInt"])
        return HandlingResult.success()


class SetSwitchState(_SetCommand):
    """Set one switch state setting."""

    NAME = "setSwitchState"

    def __init__(self, key: str, value: int) -> None:
        super().__init__({key: value})


# --- Capabilities -----------------------------------------------------------


def _switch_state_capability(key: str) -> CapabilitySetEnable:
    return CapabilitySetEnable(
        SWITCH_STATE_EVENTS[key],
        [],
        lambda enable: SetSwitchState(key, int(enable)),
    )


@dataclass(frozen=True, kw_only=True)
class AppSettings:
    """T30C settings from the ECOVACS app."""

    auto_empty_enabled: CapabilitySetEnable = CapabilitySetEnable(
        AutoEmptyEvent, [GetAutoEmptyWithPower()], lambda enable: SetAutoEmpty(enable)
    )
    carpet_first: CapabilitySetEnable = _switch_state_capability("carpetCleaningFirst")
    carpet_fine: CapabilitySetEnable = _switch_state_capability("carpetCleaningFine")
    carpet_recognition: CapabilitySetTypes = CapabilitySetTypes(
        CarpetRecognitionEvent,
        [],
        lambda option: SetSwitchState(
            CARPET_RECOGNITION_KEY, CARPET_RECOGNITION[option]
        ),
        types=tuple(CARPET_RECOGNITION),
    )
    cleaning_solution: CapabilitySetEnable = CapabilitySetEnable(
        CleaningSolutionEvent, [GetCleaningSolution()], SetCleaningSolution
    )
    do_not_disturb: CapabilitySetEnable = CapabilitySetEnable(
        DoNotDisturbEvent, [GetDoNotDisturb()], SetDoNotDisturb
    )
    dry_mop: CapabilitySetEnable = CapabilitySetEnable(
        DryMopEvent, [GetWashSettings()], set_dry_mop
    )
    drying_duration: CapabilitySetTypes = CapabilitySetTypes(
        DryingDurationEvent,
        [GetDryingDuration()],
        SetDryingDuration,
        types=tuple(DRYING_DURATIONS),
    )
    dust_power: CapabilitySetTypes = CapabilitySetTypes(
        DustPowerEvent,
        [GetAutoEmptyWithPower()],
        SetDustPower,
        types=tuple(DUST_POWERS),
    )
    floor_direction: CapabilitySetEnable = _switch_state_capability(
        "floorDirectionClean"
    )
    mop_expand: CapabilitySetEnable = CapabilitySetEnable(
        MopExpandEvent, [GetMopExpand()], SetMopExpand
    )
    off_peak_charging: CapabilitySetEnable = CapabilitySetEnable(
        OffPeakChargingEvent, [GetOffPeakCharging()], SetOffPeakCharging
    )
    wash_frequency: CapabilitySetTypes = CapabilitySetTypes(
        WashFrequencyEvent,
        [GetWashSettings()],
        set_wash_frequency,
        types=WASH_FREQUENCIES,
    )
    wash_mode: CapabilitySetTypes = CapabilitySetTypes(
        WashModeEvent,
        [GetWashSettings()],
        set_wash_mode,
        types=tuple(WASH_MODES),
    )


def get_app_settings(capabilities: Any) -> AppSettings | None:
    """Return the app settings, if the device has them."""
    return getattr(capabilities, "app_settings", None)


def apply_app_settings_patch() -> None:
    """Register the messages with deebot-client."""
    for message in (
        *_ENABLE_MESSAGES,
        OnChargeTime,
        OnWashInfo,
        OnDryingDuration,
        OnAutoEmptyWithPower,
        OnSwitchState,
        OnSettingsSnapshot,
    ):
        json_messages.MESSAGES[message.NAME] = message
