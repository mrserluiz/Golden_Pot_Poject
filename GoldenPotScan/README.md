# GoldenPotScan v0.0.1

Experimental Paper Java port of the EtherTexture Item Scanner and Menu Inspector. The original Golden Pot Python project is kept intact.

## Build
Java 21, Maven; run `mvn package` in GoldenPotScan. Install the generated jar into plugins/ and restart Paper.

## Menu scan
Run `/gps menus scan auto` then open the menu. Generates `plugins/GoldenPotScan/menus/<id>.yml` with every slot. Cached lookup by title and inventory size avoids rescanning each opening. Custom visual CMD changes are off by default and restricted to gray glass panes. Set `visual.enabled: true` and `visual.slots.0.custom-model-data: 2340` in generated YAML, `/gps menus reload`, `/gps menus mode on`.

## Safety
Item migration is disabled by default to avoid duplicate work with EtherTexture Scanner Skript. Golden Anvil is disabled by default. Theosis legacy gem and BreweryX NBT semantics must be tested before enabling; modern 1.21+ CMD components require verification. Do not remove working Skripts yet.

## Commands
`/gps menus scan auto|<id>|cancel`, `/gps menus list|reload`, `/gps menus mode on|off`, `/gps menus log on|off`, `/gps items status`, `/gps items mode on|off`, `/gps items template ruby|sapphire|topaz|emerald`, `/gps reload`.
