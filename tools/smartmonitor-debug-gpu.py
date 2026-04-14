#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from library.pythoncheck import check_python_version

check_python_version()


def main():
    try:
        import library.stats as stats
    except ModuleNotFoundError as exc:
        raise SystemExit(
            f"Missing Python dependency: {exc.name}. Install the project requirements before using this tool."
        ) from exc

    print("Gpu.stats() =", stats.sensors.Gpu.stats())
    print("Gpu.fps() =", stats.sensors.Gpu.fps())
    print("Gpu.fan_percent() =", stats.sensors.Gpu.fan_percent())
    print("Gpu.frequency() =", stats.sensors.Gpu.frequency())


if __name__ == "__main__":
    main()
