# ![Icon](https://raw.githubusercontent.com/mathoudebine/turing-smart-screen-python/main/res/icons/monitor-icon-17865/24.png) turing-smart-screen-python — HID Fork

> **Forked from:** [mathoudebine/turing-smart-screen-python](https://github.com/mathoudebine/turing-smart-screen-python)
>
> **This fork adds support for HID-based SmartMonitor displays** (USB HID / hidraw protocol).

---

⚠️ **DISCLAIMER** — This project is **not affiliated, associated, authorized, endorsed by, or in any way officially connected with Turing / XuanFang / Kipye brands**. All product and company names are the registered trademarks of their original owners.

This is an open-source alternative software, NOT the original software provided for the smart screens.

---

![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black) ![Windows](https://img.shields.io/badge/Windows%2010%2F11-0078D6?style=for-the-badge&logoColor=white) ![Python](https://img.shields.io/badge/Python-3.9+-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) [![Licence](https://img.shields.io/github/license/mathoudebine/turing-smart-screen-python?style=for-the-badge)](./LICENSE)

A Python system monitor program and an abstraction library for **small IPS USB-C displays**, with **additional support for HID (USB HID / hidraw) SmartMonitor devices**.

## What's new in this fork

### HID SmartMonitor support

This fork introduces **`A_HID` revision** — a new communication layer that works with SmartMonitor displays over **USB HID (hidraw)** instead of traditional UART/serial.

| Feature | Description |
|---------|-------------|
| **HID transport** | Communicates via `/dev/hidraw*` on Linux using raw HID reports (64-byte) |
| **YMODEM protocol** | Theme upload via YMODEM transfer over HID |
| **Runtime tag updates** | Live sensor data推送 via tag/value packets without framebuffer redraw |
| **Pre-compiled themes** | Uses `.img.dat` theme files compiled from vendor UI definitions |
| **Auto-detection** | Automatic hidraw device discovery via sysfs uevent parsing |
| **Time sync** | Optional RTC synchronization with the display |

### Configuration

Add to your `config.yaml`:

```yaml
display:
  REVISION: A_HID
  BRIGHTNESS: 20
  SMARTMONITOR_HID_RUNTIME: true
  SMARTMONITOR_HID_THEME_FILE: /path/to/your-theme-compiled.dat
  SMARTMONITOR_HID_UPLOAD_ON_START: false
  SMARTMONITOR_HID_SEND_TIME: false
  SMARTMONITOR_HID_CMD: 2
  SMARTMONITOR_HID_UPDATE_INTERVAL: 2
  SMARTMONITOR_HID_TIME_INTERVAL: 1
  SMARTMONITOR_HID_TAGS:
    CPU_TEMP: 1
    GPU_TEMP: 5
    RAM_PERCENT: 12
```

### New tools

| Tool | Purpose |
|------|---------|
| `smartmonitor-compile-theme.py` | Compile vendor UI XML themes to `.img.dat` |
| `smartmonitor-inspect-imgdat.py` | Inspect compiled theme files |
| `smartmonitor-decode-ui.py` | Decode vendor UI definitions |
| `smartmonitor-analyze-pcap.py` | Analyze PCAP captures of USB traffic |
| `smartmonitor-probe-tags.py` | Discover available tag IDs on a display |
| `smartmonitor-send-runtime.py` | Send runtime tag updates manually |
| `smartmonitor-theme-editor.py` | GUI editor for HID themes |

### Architecture

```
┌─────────────────────────────────────────────┐
│           System Monitor (main.py)           │
├─────────────────────────────────────────────┤
│  library/smartmonitor_runtime.py — runtime   │
│  library/smartmonitor_compile.py — compiler  │
│  library/smartmonitor_render.py — renderer   │
│  library/smartmonitor_imgdat.py — img.dat    │
│  library/smartmonitor_ui.py — UI encoder     │
├─────────────────────────────────────────────┤
│  library/lcd/lcd_comm_rev_a_hid.py — HID     │
│  library/lcd/lcd_comm_rev_a.py — UART Rev A  │
│  library/lcd/lcd_comm_rev_b.py — UART Rev B  │
│  library/lcd/lcd_comm_rev_c.py — UART Rev C  │
│  library/lcd/lcd_comm_rev_d.py — UART Rev D  │
├─────────────────────────────────────────────┤
│         USB Transport (HID / Serial)          │
└─────────────────────────────────────────────┘
```

## Original features (from upstream)

### ✅ Supported smart screens models:

| ✅ Turing Smart Screen 3.5" | ✅ XuanFang 3.5" | ✅ Turing Smart Screen 5" |
|---|---|---|
| ✅ Turing Smart Screen 2.1" / 2.8" | ✅ UsbPCMonitor 3.5" / 5" | ✅ Kipye Qiye Smart Display 3.5" |
| ✅ WeAct Studio Display FS V1 0.96" | ✅ WeAct Studio Display FS V1 3.5" | ✅ **SmartMonitor HID (this fork)** |

### System monitor

* Fully functional multi-OS code base (Windows, Linux, macOS).
* Display configuration using GUI configuration wizard or `config.yaml` file.
* Support multiple hardware sensors and metrics (CPU/GPU usage, temperatures, memory, disks, etc).
* Creation of themes with `theme.yaml` files using theme editor.
* Auto-detect COM port / HID device based on the selected smart screen model.
* Tray icon with Exit option.

## How to start

### Prerequisites

```bash
pip install -r requirements.txt
```

### Run system monitor

```bash
python main.py
```

### Run configuration wizard

```bash
python configure.py
```

### Simple program example

```bash
python simple-program.py
```

## Troubleshooting

### HID device not found (Linux)

1. Check if hidraw device exists:
   ```bash
   ls -la /dev/hidraw*
   ```

2. Check device uevent:
   ```bash
   cat /sys/class/hidraw/hidraw*/device/uevent
   ```

3. Ensure proper permissions (udev rule):
   ```
   SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0483", MODE="0666"
   ```

### General troubleshooting

Check [open/closed issues](https://github.com/mathoudebine/turing-smart-screen-python/issues) & [the wiki Troubleshooting page](https://github.com/mathoudebine/turing-smart-screen-python/wiki/Troubleshooting)

## License

This project is licensed under the **GNU General Public License v3.0 or later**.

Original work Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
Modifications and additions Copyright (C) 2024–2026 [Your Name]

See [LICENSE](./LICENSE) for details.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=mathoudebine/turing-smart-screen-python&type=Date)](https://star-history.com/#mathoudebine/turing-smart-screen-python&Date)
