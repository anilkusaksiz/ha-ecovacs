# Ecovacs Custom

Custom Home Assistant integration for ECOVACS devices.

This integration replaces the built-in Home Assistant `ecovacs` integration and
adds additional support and fixes that are not yet available upstream.

## Current additions

- Improved support for DEEBOT T30C OMNI Gen2 (`r0321c`)
- V2 cleaning commands
- V2 map support
- Map outline version 2 support
- Mop washing station action
- Mop drying station action
- Dustbin emptying
- Live station switches for mop washing, mop drying, and dustbin emptying
- Scenario Clean buttons: one button per scenario saved in the ECOVACS app
- Working "Last job" event on the T30C (finished or manually stopped)
- T30C-specific capability fixes

## Installation

Install through HACS as a custom repository:

`https://github.com/anilkusaksiz/ha-ecovacs`

Repository type: **Integration**

This custom component uses the same `ecovacs` domain as the built-in Home Assistant
integration and therefore replaces it when installed.

## Scenario Clean

Every scenario saved under **Scenario Clean** in the ECOVACS app is exposed as a
button on the device, named after the scenario (for example
`button.r2_d2_just_vacuum`). Pressing it starts that scenario, the same as the
play button in the app.

The list is read from the robot when Home Assistant starts. Scenarios added in
the app later get a button on the next refresh, which happens on reload,
restart, or when you call `homeassistant.update_entity` on a scenario button.
Renamed scenarios update their button name, and deleted scenarios make their
button unavailable.

## Development

The integration uses the official `deebot-client` package with runtime patches
for unsupported devices and features.

Currently tested with:

- ECOVACS DEEBOT T30C OMNI Gen2
- Device class: `r0321c`
- Firmware: `1.41.0`

## Disclaimer

This is an unofficial community project and is not affiliated with ECOVACS or
Home Assistant.
