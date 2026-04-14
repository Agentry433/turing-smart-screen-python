#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from library.pythoncheck import check_python_version
from library.smartmonitor_imgdat import parse_imgdat_file
from library.smartmonitor_ui import (
    SmartMonitorThemeBundle,
    detect_frame_count,
    parse_theme_bundle,
)

check_python_version()


def rgb24_to_rgb565(color: int) -> int:
    return ((color >> 8) & 0xF800) | ((color >> 5) & 0x07E0) | ((color >> 3) & 0x001F)


def build_expected_records(bundle: SmartMonitorThemeBundle) -> list[dict]:
    expected: list[dict] = []
    base_dir = bundle.base_dir

    if bundle.startup_pic and bundle.startup_pic.path:
        parent = bundle.theme.widget_parents[0] if bundle.theme.widget_parents else None
        expected.append(
            {
                "record_type_name": "startup_image",
                "x": 0,
                "y": 0,
                "width": parent.geometry.width if parent else 0,
                "height": parent.geometry.height if parent else 0,
                "frame_count": detect_frame_count(base_dir, bundle.startup_pic.path),
                "total_ms": bundle.startup_pic.total_ms,
                "delay_ms": bundle.startup_pic.delay_ms,
                "background_color_rgb565": rgb24_to_rgb565(bundle.startup_pic.bg_color & 0xFFFFFF),
            }
        )

    for parent in bundle.theme.widget_parents:
        if not parent.background_image_path:
            continue
        expected.append(
            {
                "record_type_name": "background_image",
                "x": 0,
                "y": 0,
                "width": parent.geometry.width,
                "height": parent.geometry.height,
                "frame_count": detect_frame_count(base_dir, parent.background_image_path),
                "background_mode_flag": int(parent.background_type == 0),
                "image_delay": parent.image_delay,
                "background_color_rgb565": rgb24_to_rgb565(parent.background_color & 0xFFFFFF),
            }
        )

    for widget in bundle.theme.widgets:
        if widget.widget_type == 4:
            expected.append(
                {
                    "record_type_name": "image_widget",
                    "widget_id": widget.global_id + 1,
                    "x": widget.geometry.x,
                    "y": widget.geometry.y,
                    "width": widget.geometry.width,
                    "height": widget.geometry.height,
                    "frame_count": detect_frame_count(base_dir, str(widget.raw_fields.get("imagePath", ""))),
                    "delay_ms": int(widget.raw_fields.get("imageDelay", "0") or 0),
                }
            )
        elif widget.widget_type == 5:
            font_color = widget.font.color if widget.font else 0
            expected.append(
                {
                    "record_type_name": "number_widget",
                    "widget_id": widget.global_id + 1,
                    "fast_sensor": widget.sensor.fast_sensor if widget.sensor else 0,
                    "x": widget.geometry.x,
                    "y": widget.geometry.y,
                    "width": widget.geometry.width,
                    "height": widget.geometry.height,
                    "h_align": int(widget.raw_fields.get("hAlign", 0) or 0),
                    "font_color_rgb565": rgb24_to_rgb565(font_color & 0xFFFFFF),
                    "font_alpha": (font_color >> 24) & 0xFF,
                    "is_div_1204": bool(widget.sensor and widget.sensor.is_div_1204),
                }
            )
        elif widget.widget_type == 2:
            font_color = widget.font.color if widget.font else 0
            expected.append(
                {
                    "record_type_name": "static_text_widget",
                    "widget_id": widget.global_id + 1,
                    "x": widget.geometry.x,
                    "y": widget.geometry.y,
                    "widget_width": widget.geometry.width,
                    "widget_height": widget.geometry.height,
                    "font_color_rgb565": rgb24_to_rgb565(font_color & 0xFFFFFF),
                    "font_alpha": (font_color >> 24) & 0xFF,
                }
            )

    return expected


def relevant_actual_fields(record_type_name: str, fields: dict) -> dict:
    allowed = {
        "startup_image": (
            "x",
            "y",
            "width",
            "height",
            "frame_count",
            "total_ms",
            "delay_ms",
            "background_color_rgb565",
        ),
        "background_image": (
            "x",
            "y",
            "width",
            "height",
            "background_mode_flag",
            "frame_count",
            "image_delay",
            "background_color_rgb565",
        ),
        "image_widget": (
            "widget_id",
            "x",
            "y",
            "width",
            "height",
            "frame_count",
            "delay_ms",
            "is_png",
        ),
        "number_widget": (
            "widget_id",
            "fast_sensor",
            "x",
            "y",
            "width",
            "height",
            "h_align",
            "font_color_rgb565",
            "font_alpha",
            "is_div_1204",
            "glyph_bitmap_height",
            "glyph_widths",
        ),
        "static_text_widget": (
            "widget_id",
            "x",
            "y",
            "rendered_width",
            "rendered_height",
            "font_color_rgb565",
            "font_alpha",
        ),
    }
    return {key: fields[key] for key in allowed.get(record_type_name, ()) if key in fields}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare a vendor theme source (.ui + config.ini) with a compiled img.dat."
    )
    parser.add_argument("ui", help="Path to vendor .ui file")
    parser.add_argument("imgdat", help="Path to compiled img.dat")
    args = parser.parse_args()

    bundle = parse_theme_bundle(args.ui)
    parsed = parse_imgdat_file(args.imgdat)
    expected = build_expected_records(bundle)
    actual = [
        record
        for record in parsed.records
        if record.record_type_name
        in {"startup_image", "background_image", "image_widget", "number_widget", "static_text_widget"}
    ]

    print(f"Theme: {bundle.ui_path}")
    print(f"img.dat: {parsed.path}")
    print(f"Expected records: {len(expected)}")
    print(f"Actual mapped records: {len(actual)}")

    for index, expected_record in enumerate(expected, start=1):
        record_type_name = expected_record["record_type_name"]
        candidates = [record for record in actual if record.record_type_name == record_type_name]
        chosen = None
        if "widget_id" in expected_record:
            for record in candidates:
                if record.fields.get("widget_id") == expected_record["widget_id"]:
                    chosen = record
                    break
        else:
            chosen = candidates[0] if candidates else None

        print(f"\n[{index:02d}] {record_type_name}")
        print("  expected:", expected_record)
        if chosen is None:
            print("  actual:   <missing>")
            continue
        print("  actual:  ", relevant_actual_fields(record_type_name, chosen.fields))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
