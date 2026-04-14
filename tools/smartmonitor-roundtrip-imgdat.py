#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from library.pythoncheck import check_python_version
from library.smartmonitor_imgdat import (
    collect_resource_spans,
    parse_imgdat_file,
    rebuild_imgdat,
)

check_python_version()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Round-trip a SmartMonitor img.dat using parsed known records and copied resource spans."
    )
    parser.add_argument("input", help="Source img.dat")
    parser.add_argument(
        "-o",
        "--output",
        help="Write rebuilt img.dat to this path",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print resource span summary.",
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser()
    if not input_path.is_file():
        raise SystemExit(f"Input file not found: {input_path}")

    original = input_path.read_bytes()
    parsed = parse_imgdat_file(input_path)
    rebuilt = rebuild_imgdat(original, parsed)

    if args.summary:
        spans = collect_resource_spans(parsed)
        print(f"Resource spans: {len(spans)}")
        for span in spans:
            print(
                f"  - off=0x{span.offset:06x} size={span.size} "
                f"records={span.record_indexes} types={span.record_type_names}"
            )

    print(f"input_sha256  = {sha256_bytes(original)}")
    print(f"rebuilt_sha256= {sha256_bytes(rebuilt)}")
    print(f"byte_equal    = {original == rebuilt}")

    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.write_bytes(rebuilt)
        print(f"wrote {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
