# BLANCO Cloud for Home Assistant

A Home Assistant integration for BLANCO water systems such as the CHOICE.ALL. It reads the
device data from the BLANCO Cloud through BLANCO's official
[Smart Home API client](https://github.com/blancoGDPD/blanco-smart-home-api-client), so no
Bluetooth adapter near the sink is needed.

The API is read only: the integration shows values, it cannot dispense water or change
settings. For local Bluetooth control see [blanco_unit](https://github.com/Nailik/blanco_unit).

## Requirements

- The device is connected to WiFi and the BLANCO Cloud (BLANCO UNIT app: Settings > WLAN und Cloud Connect).
- Device data sharing ("Gerätedatenfreigabe") is turned on in the BLANCO UNIT app.
- The serial number and service code from Settings > Geräteinformationen in the app.

## Installation

1. In HACS, add `https://github.com/tobiasvoll/blanco_cloud` as a custom repository of type *Integration*.
2. Download **BLANCO Cloud** and restart Home Assistant.
3. Go to Settings > Devices & services > Add integration > **BLANCO Cloud** and enter the serial number and service code.

## Entities

The cloud is polled every 30 seconds. Entities are only created for values your device reports.

| Entity | Description |
| --- | --- |
| CO2 remaining, Filter remaining | Remaining capacity in % |
| Cooling temperature, Heating temperature | Set points in °C |
| Water today, Still / Medium / Classic / Hot water today | Litres dispensed since midnight, usable in the energy dashboard's water section |
| Messages | Number of error messages, with code, severity and time as attributes |
| Problem | On while a warning or critical error is reported |
| Child lock, Absence mode | Current settings |
| Connectivity, Last online | Whether the device is connected to the cloud |

## How it works

The integration registers itself as an app with the BLANCO Cloud, derives the device id from
serial number and service code (SHA-256, as the UNIT app does) and gets a token for it. The
token is renewed automatically. If the access is revoked in the app, Home Assistant asks you
to allow it again. Removing the integration removes the app registration.
