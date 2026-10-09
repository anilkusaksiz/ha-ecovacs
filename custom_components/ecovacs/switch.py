"""Ecovacs switch module."""

from dataclasses import dataclass
from typing import Any, override

from deebot_client.capabilities import CapabilityExecuteTypes, CapabilitySetEnable
from deebot_client.commands import StationAction
from deebot_client.events import EnableEvent, OtaEvent
from deebot_client.events.station import State as StationState
from deebot_client.events.station import StationEvent
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EcovacsConfigEntry
from .entity import (
    EcovacsCapabilityEntityDescription,
    EcovacsDescriptionEntity,
    EcovacsEntity,
)
from .util import get_supported_entities


@dataclass(kw_only=True, frozen=True)
class EcovacsSwitchEntityDescription(
    SwitchEntityDescription,
    EcovacsCapabilityEntityDescription[CapabilitySetEnable],
):
    """Ecovacs switch entity description."""


@dataclass(kw_only=True, frozen=True)
class EcovacsStationActionSwitchEntityDescription(SwitchEntityDescription):
    """Describe a state-backed station action switch."""

    action: StationAction
    active_state: StationState


ENTITY_DESCRIPTIONS: tuple[EcovacsSwitchEntityDescription, ...] = (
    EcovacsSwitchEntityDescription(
        capability_fn=lambda c: c.settings.advanced_mode,
        key="advanced_mode",
        translation_key="advanced_mode",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
    ),
    EcovacsSwitchEntityDescription(
        capability_fn=lambda c: c.clean.continuous,
        key="continuous_cleaning",
        translation_key="continuous_cleaning",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
    ),
    EcovacsSwitchEntityDescription(
        capability_fn=lambda c: c.settings.carpet_auto_fan_boost,
        key="carpet_auto_fan_boost",
        translation_key="carpet_auto_fan_boost",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
    ),
    EcovacsSwitchEntityDescription(
        capability_fn=lambda c: c.clean.preference,
        key="clean_preference",
        translation_key="clean_preference",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
    ),
    EcovacsSwitchEntityDescription(
        capability_fn=lambda c: c.settings.true_detect,
        key="true_detect",
        translation_key="true_detect",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
    ),
    EcovacsSwitchEntityDescription(
        capability_fn=lambda c: c.settings.border_switch,
        key="border_switch",
        translation_key="border_switch",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
    ),
    EcovacsSwitchEntityDescription(
        capability_fn=lambda c: c.settings.child_lock,
        key="child_lock",
        translation_key="child_lock",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
    ),
    EcovacsSwitchEntityDescription(
        capability_fn=lambda c: c.settings.moveup_warning,
        key="move_up_warning",
        translation_key="move_up_warning",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
    ),
    EcovacsSwitchEntityDescription(
        capability_fn=lambda c: c.settings.cross_map_border_warning,
        key="cross_map_border_warning",
        translation_key="cross_map_border_warning",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
    ),
    EcovacsSwitchEntityDescription(
        capability_fn=lambda c: c.settings.safe_protect,
        key="safe_protect",
        translation_key="safe_protect",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
    ),
    EcovacsSwitchEntityDescription(
        capability_fn=lambda c: c.settings.sweep_mode,
        key="sweep_mode",
        translation_key="sweep_mode",
        entity_category=EntityCategory.CONFIG,
    ),
    EcovacsSwitchEntityDescription(
        capability_fn=lambda c: c.settings.voice_assistant,
        key="voice_assistant",
        translation_key="voice_assistant",
        entity_category=EntityCategory.CONFIG,
    ),
    EcovacsSwitchEntityDescription(
        capability_fn=lambda c: c.settings.border_spin,
        key="border_spin",
        translation_key="border_spin",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
    ),
)

OTA_ENTITY_DESCRIPTION = SwitchEntityDescription(
    key="ota_auto_update",
    translation_key="ota_auto_update",
    entity_category=EntityCategory.CONFIG,
)


STATION_ENTITY_DESCRIPTIONS = (
    EcovacsStationActionSwitchEntityDescription(
        action=StationAction.EMPTY_DUSTBIN,
        active_state=StationState.EMPTYING_DUSTBIN,
        key="station_action_empty_dustbin",
        translation_key="station_action_empty_dustbin",
    ),
    EcovacsStationActionSwitchEntityDescription(
        action=StationAction.DRY_MOP,
        active_state=StationState.DRYING_MOP,
        key="station_action_dry_mop",
        translation_key="station_action_dry_mop",
    ),
    EcovacsStationActionSwitchEntityDescription(
        action=StationAction.WASH_MOP,
        active_state=StationState.WASHING_MOP,
        key="station_action_wash_mop",
        translation_key="station_action_wash_mop",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EcovacsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add entities for passed config_entry in HA."""
    controller = config_entry.runtime_data
    entities: list[EcovacsEntity] = get_supported_entities(
        controller, EcovacsSwitchEntity, ENTITY_DESCRIPTIONS
    )
    entities.extend(
        EcovacsStationActionSwitchEntity(
            device, device.capabilities.station.action, description
        )
        for device in controller.devices
        if device.capabilities.station
        for description in STATION_ENTITY_DESCRIPTIONS
        if description.action in device.capabilities.station.action.types
    )
    entities.extend(
        EcovacsOtaSwitchEntity(device, ota, OTA_ENTITY_DESCRIPTION)
        for device in controller.devices
        if isinstance(ota := device.capabilities.settings.ota, CapabilitySetEnable)
    )
    if entities:
        async_add_entities(entities)


class EcovacsSwitchEntity(
    EcovacsDescriptionEntity[CapabilitySetEnable],
    SwitchEntity,
):
    """Ecovacs switch entity."""

    entity_description: EcovacsSwitchEntityDescription

    _attr_is_on = False

    @override
    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: EnableEvent) -> None:
            self._attr_is_on = event.enabled
            self.async_write_ha_state()

        self._subscribe(self._capability.event, on_event)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self._device.execute_command(self._capability.set(True))

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self._device.execute_command(self._capability.set(False))


class EcovacsOtaSwitchEntity(
    EcovacsDescriptionEntity[CapabilitySetEnable[OtaEvent]],
    SwitchEntity,
):
    """Automatic firmware updates switch."""

    _attr_is_on = False
    _supports_auto = True

    @property
    @override
    def available(self) -> bool:
        """Return True if the device is online and supports automatic updates."""
        return super().available and self._supports_auto

    @override
    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: OtaEvent) -> None:
            self._supports_auto = event.support_auto
            if event.auto_enabled is not None:
                self._attr_is_on = event.auto_enabled
            self.async_write_ha_state()

        self._subscribe(self._capability.event, on_event)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self._device.execute_command(self._capability.set(True))

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self._device.execute_command(self._capability.set(False))


class EcovacsStationActionSwitchEntity(
    EcovacsDescriptionEntity[CapabilityExecuteTypes[StationAction]],
    SwitchEntity,
):
    """Represent a station action using its live work state."""

    entity_description: EcovacsStationActionSwitchEntityDescription

    _attr_is_on = False

    @override
    async def async_added_to_hass(self) -> None:
        """Subscribe to station state updates."""
        await super().async_added_to_hass()

        async def on_event(event: StationEvent) -> None:
            self._attr_is_on = event.state == self.entity_description.active_state
            self.async_write_ha_state()

        self._subscribe(StationEvent, on_event)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start the station action."""
        await self._device.execute_command(
            self._capability.execute(self.entity_description.action)
        )

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the station action."""
        await self._device.execute_command(
            self._device.capabilities.custom.set(
                "stationAction",
                {"act": 4, "type": self.entity_description.action.value},
            )
        )
