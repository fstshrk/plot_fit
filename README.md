# plot-fit

Visualize cycling data from `.fit` files produced by Garmin, COROS, and other bike computers.

## Installation

```bash
pip install garmin-fit-sdk matplotlib pandas
```

For GPS map support (optional):

```bash
pip install folium
```

## Usage

```bash
python plot_fit.py ride.fit
```

Plots power, heart rate, speed, cadence, and altitude by default.

**Choose specific fields:**
```bash
python plot_fit.py ride.fit --fields "power,heart_rate,cadence"
```

**See all fields available in a file:**
```bash
python plot_fit.py ride.fit --list-fields
```

**Generate an interactive GPS map:**
```bash
python plot_fit.py ride.fit --map
```

Saves a `ride.html` file you can open in any browser.

## Plottable fields

Any field listed under `[record]` by `--list-fields` can be plotted. Common ones:

| Field | Description |
|---|---|
| `power` | Power output (W) |
| `heart_rate` | Heart rate (bpm) |
| `speed` | Speed (km/h) |
| `cadence` | Cadence (rpm) |
| `altitude` | Elevation (m) |
| `temperature` | Temperature (°C) |
| `accumulated_power` | Cumulative power (J) |
| `battery_level` | Battery level (%) — if recorded by your device |

Pass multiple fields as a comma-separated string:

```bash
python plot_fit.py ride.fit --fields "power,cadence,heart_rate,altitude"
```

## Notes

- Uses [garmin-fit-sdk](https://github.com/garmin/fit-python-sdk) rather than `fitparse`, which fails on newer Garmin and COROS files.
- `--list-fields` shows every message type in the file. Only fields under `[record]` are time-series and plottable; fields under `[session]` and `[lap]` are single-value summaries printed to the console.
- Battery data availability depends on your device firmware. COROS devices currently do not record battery level in `.fit` files.
