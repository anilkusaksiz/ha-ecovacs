"""Ecovacs button module."""

from dataclasses import dataclass
from typing import override

from deebot_client.capabilities import (
    CapabilityExecute,
    CapabilityExecuteTypes,
    CapabilityLifeSpan,
)
from deebot_client.commands import StationAction
from deebot_client.device import Device
from deebot_client.events import LifeSpan
from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EcovacsConfigEntry
from .const import SUPPORTED_LIFESPANS, SUPPORTED_STATION_ACTIONS
from .entity import (
    EcovacsCapabilityEntityDescription,
    EcovacsDescriptionEntity,
    EcovacsEntity,
)
from .patches.scenario import (
    CapabilityScenario,
    Scenario,
    ScenariosEvent,
    get_scenario_capability,
)
from .util import get_supported_entities

# Icons used by the ECOVACS app for scenario presets.
SCENARIO_ICONS = {
    "map-customize-clean": "mdi:robot-vacuum",
    "map-customize-mop": "mdi:water",
    "map-customize-sweepdrag": "mdi:robot-vacuum-variant",
}


@dataclass(kw_only=True, frozen=True)
class EcovacsButtonEntityDescription(
    ButtonEntityDescription,
    EcovacsCapabilityEntityDescription,
):
    """Ecovacs button entity description."""


@dataclass(kw_only=True, frozen=True)
class EcovacsLifespanButtonEntityDescription(ButtonEntityDescription):
    """Ecovacs lifespan button entity description."""

    component: LifeSpan


@dataclass(kw_only=True, frozen=True)
class EcovacsStationActionButtonEntityDescription(ButtonEntityDescription):
    """Ecovacs station action button entity description."""

    action: StationAction


@dataclass(kw_only=True, frozen=True)
class EcovacsScenarioButtonEntityDescription(ButtonEntityDescription):
    """Ecovacs scenario clean button entity description."""

    scenario_id: str


ENTITY_DESCRIPTIONS: tuple[EcovacsButtonEntityDescription, ...] = (
    EcovacsButtonEntityDescription(
        capability_fn=lambda caps: caps.map.relocation if caps.map else None,
        key="relocate",
        translation_key="relocate",
        entity_category=EntityCategory.CONFIG,
    ),
)

STATION_ENTITY_DESCRIPTIONS = tuple(
    EcovacsStationActionButtonEntityDescription(
        action=action,
        key=f"station_action_{action.name.lower()}",
        translation_key=f"station_action_{action.name.lower()}",
        entity_registry_enabled_default=action is StationAction.CLEAN_BASE,
    )
    for action in SUPPORTED_STATION_ACTIONS
    if action is StationAction.CLEAN_BASE
)


LIFESPAN_ENTITY_DESCRIPTIONS = tuple(
    EcovacsLifespanButtonEntityDescription(
        component=component,
        key=f"reset_lifespan_{component.name.lower()}",
        translation_key=f"reset_lifespan_{component.name.lower()}",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    )
    for component in SUPPORTED_LIFESPANS
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EcovacsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add entities for passed config_entry in HA."""
    controller = config_entry.runtime_data
    entities: list[EcovacsEntity] = get_supported_entities(
        controller, EcovacsButtonEntity, ENTITY_DESCRIPTIONS
    )
    entities.extend(
        EcovacsResetLifespanButtonEntity(
            device, device.capabilities.life_span, description
        )
        for device in controller.devices
        for description in LIFESPAN_ENTITY_DESCRIPTIONS
        if description.component in device.capabilities.life_span.types
    )
    entities.extend(
        EcovacsStationActionButtonEntity(
            device, device.capabilities.station.action, description
        )
        for device in controller.devices
        if device.capabilities.station
        for description in STATION_ENTITY_DESCRIPTIONS
        if description.action in device.capabilities.station.action.types
    )
    async_add_entities(entities)

    for device in controller.devices:
        if capability := get_scenario_capability(device.capabilities):
            _async_setup_scenario_buttons(
                config_entry, async_add_entities, device, capability
            )


@callback
def _async_setup_scenario_buttons(
    config_entry: EcovacsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    device: Device,
    capability: CapabilityScenario,
) -> None:
    """Add a button per scenario, including scenarios created later in the app."""
    added: set[str] = set()

    async def on_scenarios(event: ScenariosEvent) -> None:
        new = [scenario for scenario in event.scenarios if scenario.id not in added]
        added.update(scenario.id for scenario in new)
        async_add_entities(
            EcovacsScenarioButtonEntity(device, capability, scenario)
            for scenario in new
        )

    # The first subscription requests the scenario list from the device.
    config_entry.async_on_unload(
        device.events.subscribe(capability.event, on_scenarios)
    )


class EcovacsButtonEntity(
    EcovacsDescriptionEntity[CapabilityExecute],
    ButtonEntity,
):
    """Ecovacs button entity."""

    entity_description: EcovacsLifespanButtonEntityDescription

    @override
    async def async_press(self) -> None:
        """Press the button."""
        await self._device.execute_command(self._capability.execute())


class EcovacsResetLifespanButtonEntity(
    EcovacsDescriptionEntity[CapabilityLifeSpan],
    ButtonEntity,
):
    """Ecovacs reset lifespan button entity."""

    entity_description: EcovacsLifespanButtonEntityDescription

    @override
    async def async_press(self) -> None:
        """Press the button."""
        await self._device.execute_command(
            self._capability.reset(self.entity_description.component)
        )


class EcovacsStationActionButtonEntity(
    EcovacsDescriptionEntity[CapabilityExecuteTypes[StationAction]],
    ButtonEntity,
):
    """Ecovacs station action button entity."""

    entity_description: EcovacsStationActionButtonEntityDescription

    @override
    async def async_press(self) -> None:
        """Press the button."""
        await self._device.execute_command(
            self._capability.execute(self.entity_description.action)
        )


class EcovacsScenarioButtonEntity(
    EcovacsDescriptionEntity[CapabilityScenario],
    ButtonEntity,
):
    """Ecovacs scenario clean button entity."""

    entity_description: EcovacsScenarioButtonEntityDescription

    def __init__(
        self, device: Device, capability: CapabilityScenario, scenario: Scenario
    ) -> None:
        """Initialize entity."""
        super().__init__(
            device,
            capability,
            EcovacsScenarioButtonEntityDescription(
                key=f"scenario_{scenario.id}",
                translation_key="scenario",
                scenario_id=scenario.id,
            ),
        )
        self._exists = True
        self._update_scenario(scenario)

    @property
    @override
    def available(self) -> bool:
        """Return True if the scenario still exists on the device."""
        return super().available and self._exists

    @override
    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_scenarios(event: ScenariosEvent) -> None:
            scenario = next(
                (
                    scenario
                    for scenario in event.scenarios
                    if scenario.id == self.entity_description.scenario_id
                ),
                None,
            )
            self._exists = scenario is not None
            if scenario:
                self._update_scenario(scenario)
            self.async_write_ha_state()

        self._subscribe(self._capability.event, on_scenarios)

    def _update_scenario(self, scenario: Scenario) -> None:
        self._attr_name = scenario.name
        self._attr_icon = SCENARIO_ICONS.get(scenario.icon or "")

    @override
    async def async_press(self) -> None:
        """Press the button."""
        await self._device.execute_command(
            self._capability.start(self.entity_description.scenario_id)
        )
