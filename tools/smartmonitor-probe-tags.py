#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from library.pythoncheck import check_python_version

check_python_version()


def build_value(tag: int, mode: str) -> int:
    if mode == "tag":
        return tag
    if mode == "tagx10":
        return tag * 10
    if mode == "tagx100":
        return tag * 100
    if mode == "clock":
        return datetime.now().minute * 100 + datetime.now().second
    raise ValueError(f"Unsupported probe mode {mode}")


def main():
    try:
        from library.lcd.lcd_comm_rev_a_hid import LcdCommRevAHid
        from library.log import logger
    except ModuleNotFoundError as exc:
        raise SystemExit(
            f"Missing Python dependency: {exc.name}. Install the project requirements before using this tool."
        ) from exc

    parser = argparse.ArgumentParser(description="Probe SmartMonitor runtime tags by sending obvious test values")
    parser.add_argument("--port", default="AUTO", help="hidraw path or AUTO")
    parser.add_argument("--cmd", type=lambda value: int(value, 0), choices=(0, 2), default=2,
                        help="Runtime command to use for probing")
    parser.add_argument("--start-tag", type=int, default=1, help="First tag to probe")
    parser.add_argument("--end-tag", type=int, default=20, help="Last tag to probe")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between probes in seconds")
    parser.add_argument("--mode", choices=("tag", "tagx10", "tagx100", "clock"), default="tagx100",
                        help="Value generation mode")
    parser.add_argument("--sync-time", action="store_true", help="Send current time before each probe")
    args = parser.parse_args()

    if args.start_tag > args.end_tag:
        parser.error("--start-tag must be <= --end-tag")

    lcd = LcdCommRevAHid(com_port=args.port)
    try:
        lcd.openSerial()
        for tag in range(args.start_tag, args.end_tag + 1):
            if args.sync_time:
                lcd.smartmonitor_send_datetime(datetime.now())
            value = build_value(tag, args.mode)
            lcd.smartmonitor_send_raw_command(args.cmd, [(tag, value)])
            logger.info("Probe cmd=%d tag=%d value=%d", args.cmd, tag, value)
            time.sleep(args.delay)
    finally:
        lcd.closeSerial()


if __name__ == "__main__":
    main()
