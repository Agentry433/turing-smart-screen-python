# Changelog

All notable changes to this fork are documented here.

The format is based on a simple chronological release history.

## v0.2.1 - Autostart and Broader Runtime Support

- Added Linux user autostart support via `systemd --user`.
- Added `Enable autostart` / `Disable autostart` controls to `configure.py`.
- Broadened SmartMonitor runtime support across more themes.
- Added runtime fallback logic for themes with recoverable `source_ui` metadata.

## v0.2.0 - Shutdown Handling Improvements

- Improved application shutdown behavior.
- Stopped background runtime workers more cleanly on exit.
- Reduced cases where the process stayed alive after close or `Ctrl+C`.

## v0.1.0 - Initial Public HIDdev Release

- First public GitHub release of the SmartMonitor HID fork.
- Linux SmartMonitor HID support published in a cleaned repository package.
- Vendor `.dat` theme upload workflow included.
- Runtime integration available for supported SmartMonitor themes.
