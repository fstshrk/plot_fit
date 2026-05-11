# plot-fit

Visualize cycling data from `.fit` files produced by Garmin and other bike computers.

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

This plots power, heart rate, speed, cadence, and altitude by default.

**Choose specific fields:**
```bash
python plot_fit.py ride.fit --fields power heart_rate cadence
```

**See all fields available in a file:**
```bash
python plot_fit.py ride.fit --list-fields
```

**Generate an interactive GPS map:**
```bash
python plot_fit.py ride.fit --map
```

This saves a `ride.html` file you can open in a browser.

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

## Notes

- Uses [garmin-fit-sdk](https://github.com/garmin/fit-python-sdk) rather than `fitparse`, which fails to parse newer Garmin files correctly.
- `--list-fields` shows all message types in the file, not just time-series records. Only fields under `[record]` are plottable over time; fields under `[session]` and `[lap]` are single-value summaries printed to the console.
