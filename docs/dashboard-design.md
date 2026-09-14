# Dashboard design provenance and public-use policy

## Independent implementation

The Grafana dashboards in this repository are independently implemented in dashboard JSON, Flux, JavaScript, and Apache ECharts. They do not contain SolarAssistant source code, compiled software, CSS, frontend assets, icons, logos, screenshots, or proprietary program files.

Solar production, load, grid exchange, battery power, voltage, current, state of charge, temperature, frequency, and energy totals are functional categories common to hybrid-inverter monitoring. The project expresses those functions through its own layout, terminology, calculations, query structure, color system, and interaction model.

## Visual system

The supported dashboards use a project-specific operational-console design:

- a horizontal system-state strip;
- compact KPI tiles with colored top accents;
- horizontal power-capacity bars;
- centered bidirectional bars for battery and grid flow;
- full-width time-series analysis;
- ledger-oriented daily and monthly energy views;
- a parallel-inverter operations matrix.

Project colors are assigned consistently:

| Category | Color |
|---|---|
| Load | blue |
| Solar PV | amber |
| Battery / charging | teal-green |
| Battery / discharging | orange |
| Grid import | purple |
| Grid export | green |
| Fault or unavailable | red |
| Neutral or standby | gray |

## Third-party boundary

The dashboards require Grafana, InfluxDB, and—where identified—the Volkov Labs Business Charts plugin using Apache ECharts. Those projects retain their own names, trademarks, code, and licenses. This repository stores original dashboard configuration and does not vendor their software.

SolarAssistant is credited only where its published technical documentation materially informed hardware wiring or data-migration procedures. That credit does not imply that these dashboards are SolarAssistant dashboards, derivatives, replacements endorsed by SolarAssistant, or compatible with every SolarAssistant installation.

## Publication rules

Contributors must not add:

- screenshots or cropped images from another monitoring product;
- copied icons, logos, stylesheets, JavaScript, or frontend assets;
- proprietary software or backup archives;
- credentials, API tokens, passwords, private keys, or production database files;
- personal addresses, precise site coordinates, or private operational identifiers;
- third-party code without its source, license, and required notices.

When a dashboard is influenced by general industry practice, implement the function independently and document any material external technical source. Attribution is not a substitute for permission.

## Configuration variables

Public dashboards use Grafana variables for the InfluxDB bucket and Home Assistant entity prefix. The Operational Console also exposes hidden variables for battery capacity, optional external-shunt entities, site time zone, activity thresholds, and chart scales. Users should customize those variables after import rather than editing Flux or JavaScript directly.

## No affiliation

This is an independent community project. It is not affiliated with, endorsed by, sponsored by, or supported by Sol-Ark, SolarAssistant, Grafana Labs, InfluxData, Volkov Labs, or their respective owners.
