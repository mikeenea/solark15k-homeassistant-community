# SolarAssistant historical Energy Totals backfill

This procedure converts the SolarAssistant backup `tdhome-2026-08-15-at-12-22`
into daily and cumulative Energy Totals for the Sol-Ark historian. It does not
modify Home Assistant Recorder or its statistics database.

## Source confirmed

The backup is an InfluxDB portable backup of database `solar_assistant`, with
shards 91 through 104. Its metadata defines hourly continuous-query series for:

- PV energy
- load energy
- grid import and export energy
- battery charge and discharge energy

The continuous queries write to measurements such as `PV power hourly` and
`Grid power in hourly`. Their field is called `combined`; its values are
watt-hours even though the underlying source measurements are power in watts.

## 1. Download and restore the backup

Download every file from the Google Drive folder into one directory. Keep the
`.manifest`, `.meta`, and `.tar.gz` filenames unchanged. The restore requires
the complete shard set.

Run an isolated InfluxDB 1.8 container and restore the portable backup:

```bash
docker run --name sa-backfill -d -p 18086:8086 \
  -v "$PWD/tdhome-2026-08-15-at-12-22:/backup:ro" \
  influxdb:1.8

docker exec sa-backfill influxd restore -portable \
  -db solar_assistant -newdb solar_assistant_restore /backup
```

If the restore command reports that the server must be stopped, stop the
container, restore into its data volume with a one-shot container, then restart
it. Do not restore this backup over the production InfluxDB database.

## 2. Create and inspect the backfill

```bash
python3 tools/solarassistant_energy_backfill.py \
  --source-url http://127.0.0.1:18086 \
  --output solarassistant_energy_totals.csv
```

The default timezone is `America/New_York`, which assigns hourly points to the
correct Tennessee calendar day across daylight-saving transitions. Review the
CSV before using `--write`. The `hours_present`, `expected_hours`, and
`complete_day` columns identify partial boundary days and account for 23- or
25-hour daylight-saving transition days.

## 3. Optional lifetime-total alignment

Without anchors, cumulative totals begin at zero on the first restored day.
To align the historical curves with the inverter lifetime counters, record the
six lifetime totals at the backup endpoint and create `anchors.json`:

```json
{
  "pv": 0.0,
  "load": 0.0,
  "grid_import": 0.0,
  "grid_export": 0.0,
  "battery_charge": 0.0,
  "battery_discharge": 0.0
}
```

Replace the zeros with kWh values and rerun with `--anchors anchors.json`. The
tool shifts each cumulative series so its final backup point equals the anchor;
daily energy is never changed.

## 4. Write to the project InfluxDB 2 bucket

For the prepared CSV, run this from a computer on the same network as InfluxDB:

```bash
python tools/solarassistant_energy_backfill.py \
  --input-csv data/solarassistant_energy_totals_2026-05-10_to_2026-08-15.csv \
  --write \
  --influx2-url http://INFLUXDB_HOST:8086 \
  --influx2-org home \
  --influx2-bucket solark
```

The utility prompts for the write token without displaying it. The longer
restore-and-write form below remains available when regenerating the CSV.

```bash
python3 tools/solarassistant_energy_backfill.py \
  --source-url http://127.0.0.1:18086 \
  --anchors anchors.json \
  --output solarassistant_energy_totals.csv \
  --write \
  --influx2-url http://INFLUXDB_HOST:8086 \
  --influx2-org YOUR_ORG \
  --influx2-bucket solark \
  --influx2-token YOUR_TOKEN
```

The target measurement is `solark_energy_totals` with tag
`source=solarassistant_backfill`. Each point uses the local day-end timestamp.
Re-running the same input is safe: InfluxDB updates the same measurement, tag,
field, and timestamp rather than adding duplicate energy.

## Validation

Before accepting the backfill, verify:

1. all six source measurements contain points;
2. the CSV's first and last dates match SolarAssistant history;
3. no daily value is negative;
4. cumulative values never decrease;
5. anchored final totals equal the recorded backup-end counters; and
6. several daily values agree with SolarAssistant's Energy view within normal
   rounding tolerance.

After validation, remove the temporary container with `docker rm -f sa-backfill`.
