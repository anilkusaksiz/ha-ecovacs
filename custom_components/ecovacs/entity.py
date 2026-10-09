"""Ecovacs mqtt entity module."""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any, override

from deebot_client.capabilities import Capabilities
from deebot_client.device import Device
from deebot_client.events import AvailabilityEvent
from deebot_client.events.base import Event
from sucks import EventListener, VacBot

from homeassistant.core import CALLBACK_TYPE, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN

# deebot-client reports the device unavailable as soon as one availability
# check (every 60 s) gets no answer in time. Single misses are common, so only
# show the entities as unavailable when the device stays unreachable.
UNAVAILABLE_GRACE_SECONDS = 150


class EcovacsEntity[CapabilityEntityT](Entity):
    """Ecovacs entity."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _always_available: bool = False

    def __init__(
        self,
        device: Device,
        capability: CapabilityEntityT,
        **kwargs: Any,
    ) -> None:
        """Initialize entity."""
        super().__init__(**kwargs)
        self._attr_unique_id = (
            f"{device.device_info['did']}_{self.entity_description.key}"
        )

        self._device = device
        self._capability = capability
        self._subscribed_events: set[type[Event]] = set()
        self._cancel_unavailable: CALLBACK_TYPE | None = None

    @property
    @override
    def device_info(self) -> DeviceInfo | None:
        """Return device specific attributes."""
        device_info = self._device.device_info
        info = DeviceInfo(
            identifiers={(DOMAIN, device_info["did"])},
            manufacturer="Ecovacs",
            sw_version=self._device.fw_version,
            serial_number=device_info["name"],
            model_id=device_info["class"],
        )

        if nick := device_info.get("nick"):
            info["name"] = nick

        if model := device_info.get("deviceName"):
            info["model"] = model

        if mac := self._device.mac:
            info["connections"] = {(dr.CONNECTION_NETWORK_MAC, mac)}

        return info

    @override
    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        if not self._always_available:

            @callback
            def set_unavailable(_now: Any) -> None:
                self._cancel_unavailable = None
                self._attr_available = False
                self.async_write_ha_state()

            async def on_available(event: AvailabilityEvent) -> None:
                if event.available:
                    self._cancel_pending_unavailable()
                    if not self._attr_available:
                        self._attr_available = True
                        self.async_write_ha_state()
                elif self._attr_available and self._cancel_unavailable is None:
                    self._cancel_unavailable = async_call_later(
                        self.hass, UNAVAILABLE_GRACE_SECONDS, set_unavailable
                    )

            self._subscribe(AvailabilityEvent, on_available)
            self.async_on_remove(self._cancel_pending_unavailable)

    @callback
    def _cancel_pending_unavailable(self) -> None:
        """Cancel a scheduled switch to unavailable."""
        if self._cancel_unavailable is not None:
            self._cancel_unavailable()
            self._cancel_unavailable = None

    def _subscribe[EventT: Event](
        self,
        event_type: type[EventT],
        callback: Callable[[EventT], Coroutine[Any, Any, None]],
    ) -> None:
        """Subscribe to events."""
        self._subscribed_events.add(event_type)
        self.async_on_remove(self._device.events.subscribe(event_type, callback))

    async def async_update(self) -> None:
        """Update the entity.

        Only used by the generic entity update service.
        """
        for event_type in self._subscribed_events:
            self._device.events.request_refresh(event_type)


class EcovacsDescriptionEntity[CapabilityEntityT](EcovacsEntity[CapabilityEntityT]):
    """Ecovacs entity."""

    def __init__(
        self,
        device: Device,
        capability: CapabilityEntityT,
        entity_description: EntityDescription,
        **kwargs: Any,
    ) -> None:
        """Initialize entity."""
        self.entity_description = entity_description
        super().__init__(device, capability, **kwargs)


@dataclass(kw_only=True, frozen=True)
class EcovacsCapabilityEntityDescription[CapabilityEntityT](
    EntityDescription,
):
    """Ecovacs entity description."""

    capability_fn: Callable[[Capabilities], CapabilityEntityT | None]


class EcovacsLegacyEntity(Entity):
    """Ecovacs legacy bot entity."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: VacBot) -> None:
        """Initialize the legacy Ecovacs entity."""
        self.device = device
        vacuum = device.vacuum

        self.error: str | None = None
        self._attr_unique_id = vacuum["did"]

        if (name := vacuum.get("nick")) is None:
            name = vacuum["did"]

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vacuum["did"])},
            manufacturer="Ecovacs",
            model=vacuum.get("deviceName"),
            name=name,
            serial_number=vacuum["did"],
        )

        self._event_listeners: list[EventListener] = []

    @property
    @override
    def available(self) -> bool:
        """Return True if the entity is available."""
        return super().available and self.state is not None

    @override
    async def async_will_remove_from_hass(self) -> None:
        """Remove event listeners on entity remove."""
        for listener in self._event_listeners:
            listener.unsubscribe()
