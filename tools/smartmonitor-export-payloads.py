#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from library.pythoncheck import check_python_version
from library.smartmonitor_imgdat import parse_imgdat_file, resource_payload_size

check_python_version()

from PIL import Image


def save_grayscale_png(payload: bytes, width: int, height: int, path: Path) -> None:
    expected = width * height
    if len(payload) < expected:
        raise ValueError(f"Payload is too small for {width}x{height}: {len(payload)} < {expected}")
    image = Image.frombytes("L", (width, height), payload[:expected])
    image.save(path)


def export_record_payload(parsed, data: bytes, record_index: int, output_dir: Path) -> list[Path]:
    matching = [record for record in parsed.records if record.index == record_index]
    if not matching:
        raise ValueError(f"Record index not found: {record_index}")
    record = matching[0]
    fields = record.fields
    written: list[Path] = []

    if record.record_type_name == "static_text_widget":
        offset = int(fields["text_bitmap_offset"])
        width = int(fields["rendered_width"])
        height = int(fields["rendered_height"])
        payload = data[offset:offset + width * height]
        path = output_dir / f"record_{record_index:03d}_static_text.png"
        save_grayscale_png(payload, width, height, path)
        written.append(path)
        return written

    if record.record_type_name == "number_widget":
        offset = int(fields["glyph_bitmap_offset"])
        glyph_widths = [int(value) for value in fields["glyph_widths"]]
        height = int(fields["glyph_bitmap_height"])
        atlas_width = sum(glyph_widths)
        payload = data[offset:offset + atlas_width * height]
        atlas_path = output_dir / f"record_{record_index:03d}_number_atlas.png"
        save_grayscale_png(payload, atlas_width, height, atlas_path)
        written.append(atlas_path)

        atlas = Image.open(atlas_path)
        cursor = 0
        for glyph_index, glyph_width in enumerate(glyph_widths):
            if glyph_width <= 0:
                continue
            glyph = atlas.crop((cursor, 0, cursor + glyph_width, height))
            glyph_path = output_dir / f"record_{record_index:03d}_glyph_{glyph_index:02d}.png"
            glyph.save(glyph_path)
            written.append(glyph_path)
            cursor += glyph_width
        return written

    if record.record_type_name == "datetime_widget":
        offset = int(fields["glyph_bitmap_offset"])
        height = int(fields["glyph_bitmap_height"])
        bytes_per_row = int(fields["glyph_bitmap_width"])
        width = bytes_per_row * 4
        payload = data[offset:offset + bytes_per_row * height]
        pixels = bytearray()
        lut = [0, 85, 170, 255]
        for byte in payload:
            for shift in (6, 4, 2, 0):
                pixels.append(lut[(byte >> shift) & 0x3])
        atlas_path = output_dir / f"record_{record_index:03d}_datetime_atlas.png"
        Image.frombytes("L", (width, height), bytes(pixels[:width * height])).save(atlas_path)
        written.append(atlas_path)
        return written

    if record.record_type_name in {"startup_image", "background_image"}:
        offset_key = "asset_offset"
        width = int(fields["width"])
        height = int(fields["height"])
        frame_count = int(fields["frame_count"])
        payload = data[int(fields[offset_key]):int(fields[offset_key]) + width * height * 2 * frame_count]
        for frame_index in range(frame_count):
            start = frame_index * width * height * 2
            rgb = []
            frame_payload = payload[start:start + width * height * 2]
            for pixel_index in range(0, len(frame_payload), 2):
                value = int.from_bytes(frame_payload[pixel_index:pixel_index + 2], "little")
                r = ((value >> 11) & 0x1F) << 3
                g = ((value >> 5) & 0x3F) << 2
                b = (value & 0x1F) << 3
                rgb.extend((r, g, b))
            frame = Image.frombytes("RGB", (width, height), bytes(rgb))
            path = output_dir / f"record_{record_index:03d}_frame_{frame_index:02d}.png"
            frame.save(path)
            written.append(path)
        return written

    if record.record_type_name == "image_widget":
        offset = int(fields["asset_offset"])
        width = int(fields["width"])
        height = int(fields["height"])
        frame_count = int(fields["frame_count"])
        is_png = bool(fields["is_png"])
        bytes_per_pixel = 3 if is_png else 2
        payload_size = width * height * bytes_per_pixel * frame_count
        payload = data[offset:offset + payload_size]
        if is_png:
            frame_bytes = width * height * 3
            for frame_index in range(frame_count):
                start = frame_index * frame_bytes
                alpha_plane = payload[start:start + width * height]
                color_plane = payload[start + width * height:start + frame_bytes]
                rgba = bytearray()
                for idx in range(width * height):
                    color = int.from_bytes(color_plane[idx * 2:idx * 2 + 2], "little")
                    r = ((color >> 11) & 0x1F) << 3
                    g = ((color >> 5) & 0x3F) << 2
                    b = (color & 0x1F) << 3
                    a = alpha_plane[idx]
                    rgba.extend((r, g, b, a))
                frame = Image.frombytes("RGBA", (width, height), bytes(rgba))
                path = output_dir / f"record_{record_index:03d}_frame_{frame_index:02d}.png"
                frame.save(path)
                written.append(path)
        else:
            frame_bytes = width * height * 2
            for frame_index in range(frame_count):
                start = frame_index * frame_bytes
                frame_payload = payload[start:start + frame_bytes]
                rgb = []
                for pixel_index in range(0, len(frame_payload), 2):
                    value = int.from_bytes(frame_payload[pixel_index:pixel_index + 2], "little")
                    r = ((value >> 11) & 0x1F) << 3
                    g = ((value >> 5) & 0x3F) << 2
                    b = (value & 0x1F) << 3
                    rgb.extend((r, g, b))
                frame = Image.frombytes("RGB", (width, height), bytes(rgb))
                path = output_dir / f"record_{record_index:03d}_frame_{frame_index:02d}.png"
                frame.save(path)
                written.append(path)
        return written

    raise ValueError(f"Export for {record.record_type_name} is not implemented")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export decoded SmartMonitor img.dat payloads to PNGs for inspection."
    )
    parser.add_argument("imgdat", help="Path to img.dat")
    parser.add_argument("record_indexes", nargs="+", type=int, help="Record indexes to export")
    parser.add_argument("-o", "--output-dir", default="/tmp/smartmonitor_payloads", help="Output directory")
    args = parser.parse_args()

    input_path = Path(args.imgdat).expanduser()
    if not input_path.is_file():
        raise SystemExit(f"img.dat not found: {input_path}")

    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    parsed = parse_imgdat_file(input_path)
    data = input_path.read_bytes()

    for record_index in args.record_indexes:
        paths = export_record_payload(parsed, data, record_index, output_dir)
        for path in paths:
            print(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
