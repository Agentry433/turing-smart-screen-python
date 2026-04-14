#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from library.pythoncheck import check_python_version
from library.smartmonitor_ui import (
    SmartMonitorTheme,
    parse_ui_file,
    widget_record_fields,
    widget_type_name,
)

check_python_version()


def summarize_theme(theme: SmartMonitorTheme, include_records: bool = False) -> dict:
    widget_types = Counter(widget.widget_type for widget in theme.widgets)
    sensors = []
    for widget in theme.widgets:
        if widget.sensor is None:
            continue
        sensors.append(
            {
                "object_name": widget.object_name,
                "widget_type": widget.widget_type,
                "widget_type_name": widget_type_name(widget.widget_type),
                "fast_sensor": widget.sensor.fast_sensor,
                "sensor_type_name": widget.sensor.sensor_type_name,
                "sensor_name": widget.sensor.sensor_name,
                "reading_name": widget.sensor.reading_name,
                "is_div_1204": widget.sensor.is_div_1204,
            }
        )

    widgets = []
    for widget in theme.widgets:
        widget_info = (
            {
                "global_id": widget.global_id,
                "same_type_id": widget.same_type_id,
                "object_name": widget.object_name,
                "parent_name": widget.parent_name,
                "widget_type": widget.widget_type,
                "widget_type_name": widget_type_name(widget.widget_type),
                "geometry": {
                    "x": widget.geometry.x,
                    "y": widget.geometry.y,
                    "width": widget.geometry.width,
                    "height": widget.geometry.height,
                },
                "font_text": widget.font.text if widget.font else "",
                "font_name": widget.font.name if widget.font else "",
                "font_size": widget.font.size if widget.font else 0,
                "datetime_format": widget.datetime_format,
                "sensor": (
                    {
                        "fast_sensor": widget.sensor.fast_sensor,
                        "sensor_type_name": widget.sensor.sensor_type_name,
                        "sensor_name": widget.sensor.sensor_name,
                        "reading_name": widget.sensor.reading_name,
                    }
                    if widget.sensor
                    else None
                ),
            }
        )
        if include_records:
            try:
                widget_info["record_fields"] = widget_record_fields(widget)
            except ValueError:
                widget_info["record_fields"] = None
        widgets.append(widget_info)

    return {
        "path": theme.path,
        "widget_parents": [
            {
                "object_name": parent.object_name,
                "widget_type": parent.widget_type,
                "widget_type_name": widget_type_name(parent.widget_type),
                "geometry": {
                    "x": parent.geometry.x,
                    "y": parent.geometry.y,
                    "width": parent.geometry.width,
                    "height": parent.geometry.height,
                },
                "background_type": parent.background_type,
                "background_color": parent.background_color,
                "background_image_path": parent.background_image_path,
            }
            for parent in theme.widget_parents
        ],
        "widget_count": len(theme.widgets),
        "widget_type_counts": dict(sorted(widget_types.items())),
        "sensors": sensors,
        "widgets": widgets,
    }


def print_human_summary(summary: dict) -> None:
    print(f"Theme: {summary['path']}")
    for parent in summary["widget_parents"]:
        geometry = parent["geometry"]
        print(
            "Background:",
            f"{parent['object_name']}",
            f"type={parent['background_type']}",
            f"size={geometry['width']}x{geometry['height']}",
            f"image={parent['background_image_path'] or '-'}",
        )
    print(f"Widgets: {summary['widget_count']}")
    if summary["widget_type_counts"]:
        type_bits = [f"type {widget_type}={count}" for widget_type, count in summary["widget_type_counts"].items()]
        print("Widget types:", ", ".join(type_bits))
    if summary["sensors"]:
        print("Sensors:")
        for sensor in summary["sensors"]:
            sensor_desc = " / ".join(
                part
                for part in (
                    sensor["sensor_type_name"],
                    sensor["sensor_name"],
                    sensor["reading_name"],
                )
                if part
            )
            print(
                f"  - {sensor['object_name']}: type={sensor['widget_type']} ({sensor['widget_type_name']}) fast={sensor['fast_sensor']} {sensor_desc}"
            )
    if summary["widgets"]:
        print("Widgets detail:")
        for widget in summary["widgets"]:
            geometry = widget["geometry"]
            details = [
                f"id={widget['global_id']}/{widget['same_type_id']}",
                f"type={widget['widget_type']} ({widget['widget_type_name']})",
                f"pos={geometry['x']},{geometry['y']}",
                f"size={geometry['width']}x{geometry['height']}",
            ]
            if widget["font_text"]:
                details.append(f"text={widget['font_text']!r}")
            if widget["datetime_format"]:
                details.append(f"datetime={widget['datetime_format']!r}")
            if widget["sensor"]:
                sensor = widget["sensor"]
                sensor_desc = " / ".join(
                    part
                    for part in (
                        sensor["sensor_type_name"],
                        sensor["sensor_name"],
                        sensor["reading_name"],
                    )
                    if part
                )
                if sensor_desc:
                    details.append(f"sensor={sensor_desc}")
            if widget.get("record_fields") is not None:
                details.append(f"record={widget['record_fields']}")
            print(f"  - {widget['object_name']}: " + ", ".join(details))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Decode and inspect vendor SmartMonitor .ui files."
    )
    parser.add_argument("input", help="Path to encrypted vendor .ui file")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of a human summary.",
    )
    parser.add_argument(
        "--records",
        action="store_true",
        help="Include normalized per-widget record fields inferred from the decompiler.",
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser()
    if not input_path.is_file():
        raise SystemExit(f"Input file not found: {input_path}")

    theme = parse_ui_file(input_path)
    summary = summarize_theme(theme, include_records=args.records)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print_human_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
