#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from library.pythoncheck import check_python_version

check_python_version()


def parse_pair(raw: str) -> tuple[int, int]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("Pairs must use tag=value format")

    raw_tag, raw_value = raw.split("=", 1)
    try:
        tag = int(raw_tag, 0)
        value = int(raw_value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid pair {raw!r}: {exc}") from exc

    if not 0 <= tag <= 0xFF:
        raise argparse.ArgumentTypeError(f"Tag out of range in {raw!r}")
    if not 0 <= value <= 0xFFFF:
        raise argparse.ArgumentTypeError(f"Value out of range in {raw!r}")

    return tag, value


def main():
    try:
        from library.lcd.lcd_comm_rev_a_hid import LcdCommRevAHid
        from library.log import logger
    except ModuleNotFoundError as exc:
        raise SystemExit(
            f"Missing Python dependency: {exc.name}. Install the project requirements before using this tool."
        ) from exc

    parser = argparse.ArgumentParser(description="Send runtime packets to the HID SmartMonitor")
    parser.add_argument("--port", default="AUTO", help="hidraw path or AUTO")
    parser.add_argument("--time", action="store_true", help="Send the current date/time packet (cmd 0x03)")
    parser.add_argument("--cmd", type=lambda value: int(value, 0), choices=(0, 2), help="Runtime command for tag/value pairs")
    parser.add_argument("--pair", action="append", type=parse_pair, default=[], help="Pair in tag=value form, decimal or 0x-prefixed")
    args = parser.parse_args()

    if not args.time and args.cmd is None:
        parser.error("Specify --time and/or --cmd")
    if args.cmd is None and args.pair:
        parser.error("--pair requires --cmd")

    lcd = LcdCommRevAHid(com_port=args.port)
    try:
        lcd.openSerial()
        if args.time:
            lcd.smartmonitor_send_datetime(datetime.now())
            logger.info("Sent SmartMonitor time packet")
        if args.cmd is not None:
            lcd.smartmonitor_send_raw_command(args.cmd, args.pair)
            logger.info("Sent SmartMonitor cmd %d with %d pairs", args.cmd, len(args.pair))
    finally:
        lcd.closeSerial()


if __name__ == "__main__":
    main()
