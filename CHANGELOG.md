# Changelog

All notable changes to this fork will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added — HID SmartMonitor Support

#### New hardware revision
- **`A_HID`** — new display revision for SmartMonitor devices over USB HID (hidraw)
- `LcdCommRevAHid` class in `library/lcd/lcd_comm_rev_a_hid.py`
  - 64-byte HID report transport
  - YMODEM theme upload protocol
  - Runtime tag/value update protocol
  - Auto-detection of hidraw devices via sysfs uevent
  - Device recovery on write failure
  - Optional HID trace logging for debugging

#### Runtime system
- `library/smartmonitor_runtime.py` — runtime tag update engine
  - Live sensor data推送 without framebuffer redraw
  - Theme metadata caching (tags mapping per theme)
  - Bundled `.img.dat` theme support
  - Disk I/O sampling for disk usage tags
  - Value smoothing and clamping

#### Theme compilation pipeline
- `library/smartmonitor_compile.py` — compile vendor UI XML to `.img.dat`
- `library/smartmonitor_imgdat.py` — `.img.dat` file inspection and manipulation
- `library/smartmonitor_render.py` — render sensor data to tag payloads
- `library/smartmonitor_ui.py` — encode vendor UI XML definitions

#### Configuration
- New `config.yaml` options under `display:`:
  - `REVISION: A_HID`
  - `SMARTMONITOR_HID_RUNTIME` — enable runtime tag updates
  - `SMARTMONITOR_HID_THEME_FILE` — path to compiled `.img.dat` theme
  - `SMARTMONITOR_HID_UPLOAD_ON_START` — upload theme on startup
  - `SMARTMONITOR_HID_SEND_TIME` — sync time with display
  - `SMARTMONITOR_HID_CMD` — command mode selector
  - `SMARTMONITOR_HID_UPDATE_INTERVAL` — sensor update interval (seconds)
  - `SMARTMONITOR_HID_TIME_INTERVAL` — time sync interval (seconds)
  - `SMARTMONITOR_HID_TAGS` — tag ID mapping for sensors

#### Tools
- `smartmonitor-compile-theme.py` — compile vendor UI XML themes
- `smartmonitor-inspect-imgdat.py` — inspect compiled theme files
- `smartmonitor-decode-ui.py` — decode vendor UI definitions
- `smartmonitor-analyze-pcap.py` — analyze USB traffic PCAP captures
- `smartmonitor-probe-tags.py` — discover available tag IDs
- `smartmonitor-send-runtime.py` — send runtime tag updates manually
- `smartmonitor-compare-theme-imgdat.py` — compare theme img.dat files
- `smartmonitor-export-payloads.py` — export render payloads
- `smartmonitor-font-fit.py` — font fitting utility
- `smartmonitor-render-text-payload.py` — render text payloads
- `smartmonitor-roundtrip-imgdat.py` — img.dat roundtrip test
- `smartmonitor-theme-manager.py` — theme management utility
- `smartmonitor-upload-theme.py` — upload theme to display
- `smartmonitor-theme-editor.py` — GUI theme editor
- `turing-theme-extractor.py` — extract themes from vendor packages

#### Configuration wizard
- `configure.py` updated with:
  - "SmartMonitor HID (experimental)" model selector
  - HID theme file picker
  - HID runtime settings panel
  - hidraw device auto-detection on Linux
  - Theme compilation on save

#### Resources
- `res/smartmonitor/` directory structure:
  - `themes/` — compiled HID themes
  - `projects/` — vendor UI project templates

#### Tests
- `tools/vendor_hid_probe/` — HID device probing utilities
- `tools/lsusb/` — USB device identification

### Changed
- `configure.py` — added HID model selection and theme management UI
- `main.py` — integrated smartmonitor_runtime for HID displays
- `library/display.py` — HID display initialization support
- `library/config.py` — HID configuration loading

### Internal
- `tools/ghidra_scripts/` — reverse engineering scripts for protocol analysis
- `ghidra_12.0.4_PUBLIC/` — Ghidra installation for protocol RE
- `tmp_payloads/`, `tmp_payloads_seq/` — temporary payload directories
- `WIND/` — Windows-specific files

---

## [Original upstream project]

For changes from the original [mathoudebine/turing-smart-screen-python](https://github.com/mathoudebine/turing-smart-screen-python) project, see the upstream repository's release notes.

This fork is based on the upstream version with HID SmartMonitor support added on top.
