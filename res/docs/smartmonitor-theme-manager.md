# SmartMonitor Theme Manager

The 3.5" HID SmartMonitor does not use the normal `res/themes/*` format from this project.
It uses a vendor `img.dat` bundle that must be uploaded to the monitor.

The helper tool is:

```bash
python3 tools/smartmonitor-theme-manager.py
```

## Supported workflows

### List installed SmartMonitor themes

```bash
python3 tools/smartmonitor-theme-manager.py list
```

### Import a ready `img.dat`

```bash
python3 tools/smartmonitor-theme-manager.py import my-theme /path/to/img.dat
```

This stores the file in:

```text
res/smartmonitor/themes/my-theme/img.dat
```

### Activate a theme in `config.yaml`

```bash
python3 tools/smartmonitor-theme-manager.py activate my-theme
```

This updates `display.SMARTMONITOR_HID_THEME_FILE` to the imported file.

### Import and activate in one step

```bash
python3 tools/smartmonitor-theme-manager.py import-activate my-theme /path/to/img.dat
```

### Upload a stored theme to the monitor

```bash
python3 tools/smartmonitor-theme-manager.py upload my-theme
```

### Show currently configured theme file

```bash
python3 tools/smartmonitor-theme-manager.py current
```

### List vendor theme directories from the unpacked Windows app

```bash
python3 tools/smartmonitor-theme-manager.py vendor-list
```

### Compile a vendor `.ui` theme into `img.dat`

```bash
python3 tools/smartmonitor-theme-manager.py vendor-compile "theme_science fiction" /tmp/science-fiction.img.dat
```

This uses the experimental Linux-side `.ui -> img.dat` compiler for the currently supported widget subset.

### Compile and import a vendor theme into the repo library

```bash
python3 tools/smartmonitor-theme-manager.py vendor-import science-fiction-compiled "theme_science fiction"
```

This stores the compiled file in:

```text
res/smartmonitor/themes/science-fiction-compiled/img.dat
```

### Compile, import, and activate in one step

```bash
python3 tools/smartmonitor-theme-manager.py vendor-import-activate science-fiction-compiled "theme_science fiction"
```

## Important note

`res/themes/*` and vendor SmartMonitor themes are different systems:

- `res/themes/*` = normal project themes (`theme.yaml`, `background.png`, etc.)
- vendor SmartMonitor themes = `.ui + images + config.ini -> img.dat`

For the 3.5" HID SmartMonitor, only the vendor `img.dat` path is relevant.
