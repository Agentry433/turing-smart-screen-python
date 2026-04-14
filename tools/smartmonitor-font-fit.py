#!/usr/bin/env python3

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from library.pythoncheck import check_python_version
from library.smartmonitor_imgdat import parse_imgdat_file
from library.smartmonitor_render import (
    DEFAULT_NUMBER_GLYPHS,
    render_number_glyph_payload,
    render_static_text_payload,
    resolve_font_path,
)
from library.smartmonitor_ui import FontSpec, parse_theme_bundle

check_python_version()


def mse_bytes(left: bytes, right: bytes) -> float:
    size = min(len(left), len(right))
    if size == 0:
        return float("inf")
    total = 0
    for idx in range(size):
        diff = left[idx] - right[idx]
        total += diff * diff
    total += 255 * 255 * abs(len(left) - len(right))
    return total / max(len(left), len(right))


def static_text_target(imgdat_path: Path, record_index: int) -> tuple[int, int, bytes]:
    parsed = parse_imgdat_file(imgdat_path)
    data = imgdat_path.read_bytes()
    record = next(record for record in parsed.records if record.index == record_index)
    width = int(record.fields["rendered_width"])
    height = int(record.fields["rendered_height"])
    offset = int(record.fields["text_bitmap_offset"])
    payload = data[offset:offset + width * height]
    return width, height, payload


def number_target(imgdat_path: Path, record_index: int) -> tuple[list[int], int, bytes]:
    parsed = parse_imgdat_file(imgdat_path)
    data = imgdat_path.read_bytes()
    record = next(record for record in parsed.records if record.index == record_index)
    widths = [int(value) for value in record.fields["glyph_widths"]]
    height = int(record.fields["glyph_bitmap_height"])
    offset = int(record.fields["glyph_bitmap_offset"])
    payload = data[offset:offset + sum(widths) * height]
    return widths, height, payload


def candidate_fonts(font_name: str) -> list[Path]:
    roots = [
        Path("/tmp/smartmonitor_unpacked/app/fonts"),
        Path("/usr/share/fonts"),
        Path.home() / ".local/share/fonts",
    ]
    names = {font_name.lower(), font_name.lower().replace(" ", "")}
    candidates: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".ttf", ".otf"}:
                continue
            stem = path.stem.lower().replace(" ", "")
            if any(name in stem for name in names) or font_name.lower() in path.name.lower():
                if path not in seen:
                    candidates.append(path)
                    seen.add(path)

    resolved = resolve_font_path(font_name)
    if resolved:
        resolved_path = Path(resolved)
        if resolved_path.is_file() and resolved_path not in seen:
            candidates.insert(0, resolved_path)
            seen.add(resolved_path)

    fallback_queries = ["Liberation Sans", "DejaVu Sans", "Noto Sans"]
    for query in fallback_queries:
        resolved = resolve_font_path(query)
        if not resolved:
            continue
        resolved_path = Path(resolved)
        if resolved_path.is_file() and resolved_path not in seen:
            candidates.append(resolved_path)
            seen.add(resolved_path)
    return candidates


def fit_static_text(args) -> int:
    bundle = parse_theme_bundle(args.ui)
    widget = next(w for w in bundle.theme.widgets if w.global_id + 1 == args.widget_id)
    target_width, target_height, target_payload = static_text_target(Path(args.imgdat), args.record_index)

    font = widget.font or FontSpec(name=args.font_name or "Arial", size=args.min_size)
    if args.font_name:
        font.name = args.font_name

    font_paths = candidate_fonts(font.name)
    if args.extra_font:
        font_paths.extend(Path(path).expanduser() for path in args.extra_font)
    if not font_paths:
        raise SystemExit(f"No font candidates found for {font.name}")

    results = []
    for font_path in font_paths:
        for pixel_size in range(args.min_size, args.max_size + 1):
            rendered = render_static_text_payload(
                widget.font.text if widget.font else "",
                font,
                font_path=str(font_path),
                pixel_size=pixel_size,
            )
            score = (
                abs(rendered.width - target_width) * 1000
                + abs(rendered.height - target_height) * 1000
                + mse_bytes(rendered.payload, target_payload)
            )
            results.append((score, font_path, pixel_size, rendered.width, rendered.height))

    results.sort(key=lambda item: item[0])
    for score, font_path, pixel_size, width, height in results[: args.top]:
        print(
            f"score={score:.2f} size={pixel_size} rendered={width}x{height} "
            f"target={target_width}x{target_height} font={font_path}"
        )
    return 0


def fit_number(args) -> int:
    bundle = parse_theme_bundle(args.ui)
    widget = next(w for w in bundle.theme.widgets if w.global_id + 1 == args.widget_id)
    target_widths, target_height, target_payload = number_target(Path(args.imgdat), args.record_index)

    font = widget.font or FontSpec(name=args.font_name or "Arial", size=args.min_size)
    if args.font_name:
        font.name = args.font_name

    font_paths = candidate_fonts(font.name)
    if args.extra_font:
        font_paths.extend(Path(path).expanduser() for path in args.extra_font)
    if not font_paths:
        raise SystemExit(f"No font candidates found for {font.name}")

    results = []
    for font_path in font_paths:
        for pixel_size in range(args.min_size, args.max_size + 1):
            widths, height, payload = render_number_glyph_payload(
                font,
                DEFAULT_NUMBER_GLYPHS,
                font_path=str(font_path),
                pixel_size=pixel_size,
            )
            width_penalty = sum(abs(a - b) for a, b in zip(widths, target_widths)) + abs(len(widths) - len(target_widths)) * 50
            score = width_penalty * 1000 + abs(height - target_height) * 1000 + mse_bytes(payload, target_payload)
            results.append((score, font_path, pixel_size, widths, height))

    results.sort(key=lambda item: item[0])
    for score, font_path, pixel_size, widths, height in results[: args.top]:
        print(
            f"score={score:.2f} size={pixel_size} height={height} target_height={target_height} "
            f"widths={widths} target_widths={target_widths} font={font_path}"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search for fonts/sizes that best match vendor SmartMonitor text or number payloads."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("ui", help="Path to vendor .ui file")
    common.add_argument("imgdat", help="Path to compiled img.dat")
    common.add_argument("--widget-id", type=int, required=True, help="Widget global_id+1 from the theme")
    common.add_argument("--record-index", type=int, required=True, help="Record index in img.dat")
    common.add_argument("--font-name", help="Override font family name")
    common.add_argument("--extra-font", action="append", help="Extra font file candidate")
    common.add_argument("--min-size", type=int, default=8)
    common.add_argument("--max-size", type=int, default=28)
    common.add_argument("--top", type=int, default=10)

    static_parser = subparsers.add_parser("static-text", parents=[common])
    static_parser.set_defaults(func=fit_static_text)

    number_parser = subparsers.add_parser("number", parents=[common])
    number_parser.set_defaults(func=fit_number)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
