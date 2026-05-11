#!/usr/bin/env python3
"""
plot_fit.py — Visualize cycling data from .fit files produced by bike computers.

Dependencies:
    pip install garmin-fit-sdk matplotlib pandas

Usage:
    python plot_fit.py ride.fit
    python plot_fit.py ride.fit --fields power heart_rate speed cadence
    python plot_fit.py ride.fit --list-fields
    python plot_fit.py ride.fit --map          # requires: pip install folium
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


# ── Field configuration ────────────────────────────────────────────────────────

FIELD_CONFIG = {
    "power": {
        "label": "Power (W)",
        "color": "#f97316",
        "unit": "W",
        "smooth": 5,
    },
    "heart_rate": {
        "label": "Heart Rate (bpm)",
        "color": "#ef4444",
        "unit": "bpm",
        "smooth": 1,
    },
    "speed": {
        "label": "Speed (km/h)",
        "color": "#3b82f6",
        "unit": "km/h",
        "scale": 3.6,       # m/s → km/h
        "smooth": 3,
    },
    "cadence": {
        "label": "Cadence (rpm)",
        "color": "#a855f7",
        "unit": "rpm",
        "smooth": 3,
    },
    "altitude": {
        "label": "Altitude (m)",
        "color": "#22c55e",
        "unit": "m",
        "smooth": 1,
        "fill": True,
    },
    "temperature": {
        "label": "Temperature (°C)",
        "color": "#06b6d4",
        "unit": "°C",
        "smooth": 1,
    },
    "accumulated_power": {
        "label": "Accum. Power (J)",
        "color": "#fbbf24",
        "unit": "J",
        "smooth": 1,
    },
    "battery_level": {
        "label": "Battery (%)",
        "color": "#84cc16",
        "unit": "%",
        "smooth": 1,
    },
    "battery_voltage": {
        "label": "Battery Voltage (V)",
        "color": "#84cc16",
        "unit": "V",
        "smooth": 1,
        "scale": 0.001,  # mV → V if stored as millivolts
    },
}

# Battery fields that may appear in device_info_mesgs instead of record_mesgs
BATTERY_FIELDS = {"battery_level", "battery_voltage", "battery_status"}

DEFAULT_FIELDS = ["power", "heart_rate", "speed", "cadence", "altitude"]


# ── FIT parsing ────────────────────────────────────────────────────────────────

def open_fit(path: Path):
    try:
        from garmin_fit_sdk import Decoder, Stream
    except ImportError:
        sys.exit(
            "garmin-fit-sdk not found. Install it with:\n"
            "  pip install garmin-fit-sdk"
        )
    stream = Stream.from_file(str(path))
    decoder = Decoder(stream)
    messages, errors = decoder.read()
    if errors:
        print(f"Warning: {len(errors)} decode error(s) (data may be partial)", file=sys.stderr)
    return messages


def list_all_fields(path: Path):
    """Print every field from every message type in the file."""
    messages = open_fit(path)
    print("All fields found in the file (by message type):\n")
    for mtype in sorted(messages):
        records = messages[mtype]
        if not records:
            continue
        # Collect field → count across all records of this type
        counts: dict[str, int] = {}
        for rec in records:
            for k, v in rec.items():
                if v is not None:
                    counts[k] = counts.get(k, 0) + 1
        print(f"  [{mtype.removesuffix('_mesgs')}]  ({len(records)} record(s))")
        for fname in sorted(counts):
            print(f"    {fname:<40} {counts[fname]}")
    print()


def parse_fit(path: Path) -> pd.DataFrame:
    """Parse record messages (time-series data) into a DataFrame."""
    messages = open_fit(path)
    records = messages.get("record_mesgs", [])
    if not records:
        sys.exit("No 'record' messages found in the .fit file.")

    df = pd.DataFrame(records)

    # Pull battery fields from device_info_mesgs if not in records
    device_msgs = messages.get("device_info_mesgs", [])
    for field in BATTERY_FIELDS:
        if field not in df.columns:
            vals = [r[field] for r in device_msgs if field in r and r[field] is not None]
            if vals:
                df[field] = vals[0]  # scalar — same value across all rows

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values("timestamp").reset_index(drop=True)
        df["elapsed_s"] = (
            df["timestamp"] - df["timestamp"].iloc[0]
        ).dt.total_seconds()
    else:
        df["elapsed_s"] = df.index.astype(float)

    return df


# ── Summary stats ──────────────────────────────────────────────────────────────

def print_summary(df: pd.DataFrame):
    duration_s = df["elapsed_s"].iloc[-1]
    h, rem = divmod(int(duration_s), 3600)
    m, s = divmod(rem, 60)
    print(f"\n{'─'*44}")
    print(f"  Duration      : {h:02d}:{m:02d}:{s:02d}")

    if "speed" in df.columns:
        avg_kmh = df["speed"].mean() * 3.6
        max_kmh = df["speed"].max() * 3.6
        dist_km = (df["speed"] * df["elapsed_s"].diff().fillna(0)).sum() / 1000
        print(f"  Distance      : {dist_km:.2f} km")
        print(f"  Avg speed     : {avg_kmh:.1f} km/h  |  Max: {max_kmh:.1f} km/h")

    if "power" in df.columns:
        p = df["power"].dropna()
        np_power = (p[p > 0] ** 4).mean() ** 0.25 if len(p[p > 0]) else float("nan")
        print(f"  Avg power     : {p.mean():.0f} W  |  Max: {p.max():.0f} W  |  NP≈{np_power:.0f} W")

    if "heart_rate" in df.columns:
        hr = df["heart_rate"].dropna()
        print(f"  Avg HR        : {hr.mean():.0f} bpm  |  Max: {hr.max():.0f} bpm")

    if "cadence" in df.columns:
        cad = df["cadence"].dropna()
        moving = cad[cad > 0]
        print(f"  Avg cadence   : {moving.mean():.0f} rpm  (excluding zeros)")

    if "altitude" in df.columns:
        alt = df["altitude"].dropna()
        gain = alt.diff().clip(lower=0).sum()
        loss = (-alt.diff()).clip(lower=0).sum()
        print(f"  Elevation     : +{gain:.0f} m / -{loss:.0f} m")

    print(f"{'─'*44}\n")


# ── Plotting ───────────────────────────────────────────────────────────────────

def elapsed_formatter(seconds, _pos=None):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}:{m:02d}"


def plot_fields(df: pd.DataFrame, fields: list[str], title: str):
    available = [f for f in fields if f in df.columns]
    missing   = [f for f in fields if f not in df.columns]

    if missing:
        print(f"Note: fields not in file (skipped): {', '.join(missing)}")
    if not available:
        sys.exit("None of the requested fields are present in this .fit file.")

    x = df["elapsed_s"]

    fig = plt.figure(figsize=(14, 3 * len(available)), facecolor="#0f172a",
                     layout="constrained")
    fig.suptitle(title, color="white", fontsize=14, fontweight="bold")

    gs = gridspec.GridSpec(len(available), 1, figure=fig, hspace=0.45)

    for i, field in enumerate(available):
        cfg = FIELD_CONFIG.get(
            field, {"label": field, "color": "#94a3b8", "unit": "", "smooth": 1}
        )
        ax = fig.add_subplot(gs[i])
        ax.set_facecolor("#1e293b")
        for spine in ax.spines.values():
            spine.set_color("#334155")
        ax.tick_params(colors="#94a3b8", labelsize=9)
        ax.yaxis.label.set_color("#94a3b8")

        y = df[field].copy() * cfg.get("scale", 1)
        smooth = cfg.get("smooth", 1)
        y_smooth = y.rolling(smooth, center=True, min_periods=1).mean() if smooth > 1 else y

        color = cfg["color"]
        ax.plot(x, y, color=color, alpha=0.2, linewidth=0.8)
        ax.plot(x, y_smooth, color=color, linewidth=1.6)

        if cfg.get("fill"):
            ax.fill_between(x, y_smooth, alpha=0.15, color=color)

        ax.set_ylabel(cfg["label"], color="#94a3b8", fontsize=9)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(elapsed_formatter))
        ax.grid(axis="y", color="#334155", linewidth=0.5, linestyle="--")
        ax.grid(axis="x", color="#334155", linewidth=0.4, linestyle=":")

        valid = y_smooth.dropna()
        if len(valid):
            avg = valid.mean()
            mx  = valid.max()
            unit = cfg.get("unit", "")
            ax.axhline(avg, color=color, linewidth=0.8, linestyle="--", alpha=0.6)
            ax.text(
                0.995, 0.92, f"avg {avg:.0f}  max {mx:.0f} {unit}",
                transform=ax.transAxes, ha="right", va="top",
                color=color, fontsize=8, alpha=0.9,
            )

    ax.set_xlabel("Elapsed time (H:MM)", color="#94a3b8", fontsize=9)
    plt.show()


# ── Map (optional) ─────────────────────────────────────────────────────────────

def plot_map(df: pd.DataFrame, out_path: Path):
    try:
        import folium
    except ImportError:
        sys.exit("folium not found. Install it with:  pip install folium")

    if "position_lat" not in df.columns or "position_long" not in df.columns:
        sys.exit("No GPS data found in this .fit file.")

    # garmin-fit-sdk returns raw semicircles for some devices (e.g. COROS)
    lat = df["position_lat"].dropna()
    lon = df["position_long"].dropna()
    if lat.abs().max() > 90:  # semicircles, not degrees
        lat = lat * (180 / 2**31)
        lon = lon * (180 / 2**31)
    coords = list(zip(lat, lon))
    centre = [lat.mean(), lon.mean()]
    m = folium.Map(location=centre, zoom_start=13, tiles="CartoDB dark_matter")
    folium.PolyLine(coords, color="#f97316", weight=3, opacity=0.85).add_to(m)
    folium.Marker(coords[0],  popup="Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(coords[-1], popup="End",   icon=folium.Icon(color="red")).add_to(m)

    out_html = out_path.with_suffix(".html")
    m.save(str(out_html))
    print(f"Map saved to: {out_html}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Plot data from a .fit cycling file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Known plottable fields: {', '.join(FIELD_CONFIG)}\n"
               "Any field from [record] in --list-fields can be plotted.",
    )
    parser.add_argument("fit_file", help="Path to the .fit file")
    parser.add_argument(
        "--fields", default=",".join(DEFAULT_FIELDS), metavar="FIELD1,FIELD2,...",
        help=f"Comma-separated fields to plot (default: {','.join(DEFAULT_FIELDS)})",
    )
    parser.add_argument(
        "--map", action="store_true",
        help="Save an interactive HTML map of the GPS track (requires folium)",
    )
    parser.add_argument(
        "--list-fields", action="store_true",
        help="List all fields in every message type and exit",
    )
    args = parser.parse_args()
    fit_path = Path(args.fit_file)
    if not fit_path.exists():
        sys.exit(f"File not found: {fit_path}")

    print(f"Parsing {fit_path.name} …")

    if args.list_fields:
        list_all_fields(fit_path)
        return

    df = parse_fit(fit_path)
    print_summary(df)

    if args.map:
        plot_map(df, fit_path)

    plot_fields(df, [f.strip() for f in args.fields.split(",")], title=fit_path.stem)


if __name__ == "__main__":
    main()
