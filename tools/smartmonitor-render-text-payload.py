#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from library.pythoncheck import check_python_version
from library.smartmonitor_render import (
    DEFAULT_NUMBER_GLYPHS,
    render_number_glyph_payload,
    render_static_text_payload,
    save_number_glyph_preview,
    save_payload_preview,
)
from library.smartmonitor_ui import FontSpec

check_python_version()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render experimental SmartMonitor text/glyph payloads with PIL."
    )
    parser.add_argument("--text", help="Static text to render")
    parser.add_argument("--number-glyphs", action="store_true", help="Render the default number glyph set")
    parser.add_argument("--font-name", default="Arial")
    parser.add_argument("--font-size", type=int, default=12)
    parser.add_argument("--bold", action="store_true")
    parser.add_argument("--italic", action="store_true")
    parser.add_argument("-o", "--output", required=True, help="Output PNG")
    args = parser.parse_args()

    font = FontSpec(
        name=args.font_name,
        size=args.font_size,
        bold=args.bold,
        italic=args.italic,
        bold_value=int(args.bold),
        italic_value=int(args.italic),
    )

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.number_glyphs:
        widths, height, payload = render_number_glyph_payload(font, DEFAULT_NUMBER_GLYPHS)
        save_number_glyph_preview(payload, widths, height, output_path)
        print(f"glyph_widths={widths}")
        print(f"glyph_height={height}")
        print(f"payload_size={len(payload)}")
        print(output_path)
        return 0

    if args.text is None:
        raise SystemExit("Provide either --text or --number-glyphs")

    rendered = render_static_text_payload(args.text, font)
    save_payload_preview(rendered.payload, rendered.width, rendered.height, output_path)
    print(f"width={rendered.width}")
    print(f"height={rendered.height}")
    print(f"payload_size={len(rendered.payload)}")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
