# osu-tools Proxy Server

Docker server for osu-tools which provides a simple difficulty analysis of an osu! beatmap.

## Environment Variables

|Name|Description|
|:--:|:----------|
|`STAT_SERVER_CUSTOM_MODS`|Implements custom mod name listing. Also enables `custom` mod name-set option. (see next.)|
|`STAT_SERVER_PREFERRED`|Switches baseline of `preferred` mod list. Available are `preferred`, `community`, `custom`.|
