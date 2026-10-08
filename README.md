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
- T30C-specific capability fixes

## Installation

Install through HACS as a custom repository:

`https://github.com/anilkusaksiz/ha-ecovacs`

Repository type: **Integration**

This custom component uses the same `ecovacs` domain as the built-in Home Assistant
integration and therefore replaces it when installed.

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
