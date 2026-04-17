# SmartMonitor `.ui` -> `img.dat` Reverse Notes

Current status: partial reverse engineering completed. The final `img.dat` write path is now located, but a native converter is not implemented yet.

## Confirmed facts

- The monitor does **not** accept `.ui` directly.
- The monitor receives only `img.dat` over HID via YMODEM.
- The Windows app uses two different flows:
  - `Save` stores the editable theme source (`.ui`)
  - `Download` compiles the current theme into `/img.dat` and then uses that for transfer
- `app/config.ini` stores the currently selected source theme in `uiPath=...`.

## File format observations

- Vendor theme source is stored as:
  - `<theme>.ui`
  - `images/...`
  - `config.ini`
- `.ui` is not plain XML on disk. It is first transformed by `FUN_004b8f10(...)` and only then parsed by `QDomDocument::setContent(...)`.
- `img.dat` is a compiled container.
- `img.dat` contains embedded bitmap payloads:
  - the root `app/img.dat` contains `29` `BM` signatures
  - the extracted capture `img.dat` contains `6` `BM` signatures
- This strongly suggests `img.dat` is a packed layout/resource container, not a raw framebuffer dump.
- `img.dat` starts with a little-endian slot count and then uses fixed `0x40`-byte record slots.
- In the installer sample `app/img.dat`, the first dword is `150`, so the record table spans `150 * 0x40 = 9600` bytes.

## Important Windows app functions

These addresses are from the vendor Windows application payload unpacked from `WIND/3.5 Inch SmartMonitor.exe`.

- `0x40cb90`
  - handler for `on_pushButton_save_clicked`
  - looks like `.ui` save dialog / save-path logic
- `0x40f6a0..0x410061`
  - large download/compile flow
  - checks theme path, builds `/img.dat`, calls compiler stages, emits download-related signal
- `0x47ecf0`
  - used by the download flow before `/img.dat` size check
  - decodes the `.ui`, parses it into a DOM-like model, serializes the final payload, and writes `/img.dat` directly
- `0x4be1a0`
  - large builder stage used by the compiler path
- `0x4c0a90..0x4c1cad`
  - large side writer stage
  - generates companion `.c` / `.h` files and emits a `FontMaker` signal
  - not the final `img.dat` writer
- `0x4c2780`
  - helper used by both `0x4be1a0` and `0x4c0a90`
  - likely copies or normalizes Qt string/binary payloads during packing

## Qt metaobject notes

One relevant QObject class has the metaobject at `0x5224e0`.

Decoded method names:

- `emitSave`
- `emitDownload`
- `emitRefreshSensor`
- `slotSetStatusBar`
- `slotDownloadEnd`
- `on_pushButton_new_clicked`
- `on_pushButton_load_clicked`
- `on_pushButton_save_clicked`
- `slotShowFileName`
- `on_pushButton_download_clicked`
- `on_pushButton_selectTheme_clicked`
- `on_checkBox_freeDrag_clicked`
- `on_pushButton_top_clicked`
- `on_pushButton_bottom_clicked`
- `on_pushButton_left_clicked`
- `on_pushButton_right_clicked`
- `on_pushButton_startupImage_clicked`
- `slotTitleMove`
- `on_pushButton_cutPic_clicked`

One important correction:

- helper `0x4c3930` emits `emitDownload`, not `emitSave`
- helper `0x4c8f70` emits `FontMaker.emitNewFilePath(QString)`

That matters because the `/img.dat` path is tied to the download/compile path, not to ordinary `.ui` saving.

Another important correction:

- `0x4c0a90` and sibling `0x4bcfa0` are not the final `img.dat` compiler.
- The actual `/img.dat` file is written inside `0x47ecf0`.

## Newly confirmed `img.dat` flow

- `0x40f6a0` calls `0x47ecf0`, then checks the size of `QCoreApplication::applicationDirPath() + "/img.dat"`.
- Near the tail of `0x47ecf0`:
  - a `QByteArray` payload is assembled
  - the payload is padded up to a `0x1000` boundary
  - `QFile` is opened for `/img.dat`
  - `QIODevice::write(...)` writes the compiled data directly
- This means there is no mandatory external compiler step for final `img.dat` generation.

## Widget type dispatch confirmed in `0x47ecf0`

- `type=2` -> `0x4b7c30`
- `type=3` -> `0x4a98f0`
- `type=4` -> `0x495500`
- `type=5` -> `0x49fd20`
- `type=6` -> `0x4911e0`

The type `6` handler clearly parses `dateTimeFormat`, `fontName`, `fontColor`, `fontSize`, `hAlign`, and geometry fields, then stores them into a QVariant-like record list.

## Current best understanding

- `.ui` source is decoded into an XML/DOM representation.
- Widget handlers convert each DOM node into typed QVariant-like records.
- `0x47ecf0` serializes those records and resource blobs into the final `img.dat`.
- `0x4be1a0 -> 0x4c0a90` is a parallel export path that generates C/header artifacts for `llLatticeInfo` / `llLatticeLibraryInfo`, but it is not required to produce `/img.dat`.
- A native parser now exists for the decoded XML, so vendor themes can be inspected without Windows.
- A partial native parser now exists for compiled `img.dat` slot records.

## First concrete record mapping

The installer sample `app/img.dat` matches `theme_science fiction`, which provides a direct source/binary pair for record mapping.

- `0x94` startup image record
  - matches `theme_science fiction/config.ini` `StartupPic`
  - inferred fields: `x`, `y`, `width`, `height`, `asset_token`, `total_ms`, `delay_ms`
- `0x81` background image record
  - matches `<widgetParent backgroundImagePath=...>`
  - inferred fields: `x`, `y`, `width`, `height`, `asset_token`, flags/background type
- `0x84` image widget record
  - matches type `4` widgets
  - confirmed fields: `widget_id`, `x`, `y`, `width`, `height`
  - bytes `0x0b..0x0e` are a big-endian asset offset
  - byte `0x0f` is `frame_count`
  - byte `0x10` is a suffix flag (`png` -> `1`)
  - bytes `0x11..0x12` are `imageDelay`
- `0x92` number widget record
  - matches type `5` widgets in `theme_science fiction`
  - confirmed fields: `widget_id`, `fast_sensor`, `x`, `y`, `width`, `height`, `h_align`
  - bytes `0x0c..0x0d` are `fontColor` converted from RGB24 to RGB565
  - byte `0x0e` is `isDiv1204`
  - byte `0x0f` is `fontColorAlpha`
  - bytes `0x10..0x13` are a big-endian offset to the rendered glyph-bitmap resource
  - bytes `0x14..0x15` are the rendered glyph height
  - bytes `0x16..0x2d` are `12` big-endian `u16` values; on the `science fiction` sample they look like per-glyph widths
- `0x93` static text record
  - matches type `2` widgets in `theme_science fiction`
  - confirmed fields: `widget_id`, `x`, `y`
  - bytes `0x07..0x0a` are the rendered text bitmap width/height, not the XML widget rectangle size
  - bytes `0x0b..0x0e` are a big-endian offset to the rendered text bitmap resource
  - bytes `0x0f..0x10` are `fontColor` converted to RGB565
  - byte `0x11` is `fontColorAlpha`

## Newly confirmed helper roles

- `0x00411fb0`
  - reads `StartupPic` from `config.ini`
  - confirmed fields: `path`, `totalMs`, `delayMs`, `bgColor`
- `0x00493e00`
  - counts animation frames for paths like `name00.png`, `name01.png`, ...
  - returns `1` for non-sequence assets
- `0x00494900`
  - resolves a resource path to the actual on-disk file, including `nameNN.ext` frame sets
- `0x00465a80`
  - normalizes `./relative/path` into a base-directory-relative path
- `0x00465b90`
  - does the reverse normalization for emitted/generated paths
- `0x004b9060`
  - loads image resources and converts them into packed pixel payloads
  - PNG path uses a 3-bytes-per-pixel style layout (alpha pass plus color pass)
  - non-PNG path uses a 2-bytes-per-pixel style layout
- `0x004c1cb0`
  - renders text with Qt font metrics into a bitmap payload
  - computes the compiled text width/height
  - bit-packs the glyph image according to `param_4`, which explains why compiled static-text sizes differ from XML rectangles

## Practical implication of the new helper map

- Resource preparation is no longer a black box:
  - frame counting is known
  - startup config loading is known
  - image payload generation is known
  - text glyph rendering is known
- The remaining hard part is the final compact token/resource serialization that places those prepared payloads into `img.dat`.

## Newly confirmed serializer details from `0x47ecf0`

- Resource offsets inside record slots are written big-endian, byte-by-byte from `offset >> 24` down to `offset & 0xff`.
- `0x84` image widget record packs:
  - `widget_id`
  - `x/y/width/height` as high-byte then low-byte
  - `asset_offset` at bytes `0x0b..0x0e`
  - `isEnable` at byte `0x0f`
  - image suffix flag (`png` -> `1`) at byte `0x10`
  - `imageDelay` at bytes `0x11..0x12`
- `0x81` background record packs:
  - `width/height`
  - `(backgroundType == 0)` flag at byte `0x0b`
  - `backgroundColor` as RGB565 at bytes `0x0c..0x0d`
  - `asset_offset` at bytes `0x0e..0x11`
  - `frame_count` at byte `0x12`
  - image suffix flag (`png` -> `1`) at byte `0x13`
  - `imageDelay` at bytes `0x14..0x15`
- `0x94` startup image record packs:
  - `x=y=0`
  - `width/height`
  - `asset_offset` at bytes `0x0b..0x0e`
  - `frame_count` at byte `0x0f`
  - `totalMs` at bytes `0x10..0x11`
  - `delayMs` at bytes `0x12..0x13`
  - startup background color as RGB565 at bytes `0x14..0x15`

## Newly confirmed resource span model

For the `theme_science fiction -> app/img.dat` pair, the resource payload sizes now derive cleanly from record geometry:

- startup image payload:
  - `width * height * 2 * frame_count`
  - sample: `480 * 320 * 2 * 5 = 1536000`
- background image payload:
  - `width * height * 2`
  - sample: `480 * 320 * 2 = 307200`
- image widget payload:
  - `width * height * (3 if png else 2) * frame_count`
  - sample A: `100 * 100 * 3 * 6 = 180000`
  - sample B: `72 * 72 * 3 * 6 = 93312`
- static text payload:
  - `rendered_width * rendered_height`
  - sample: `47 * 18 = 846`
- number glyph payload:
  - `sum(glyph_widths) * glyph_bitmap_height`
  - sample: `(13*10 + 7 + 8) * 27 = 3915`

This strongly suggests the resource section is just concatenated raw payload blocks with record offsets pointing directly into them, not an additional nested container format.

## Experimental compiler status

A native experimental compiler now exists in:

- [library/smartmonitor_compile.py](../../library/smartmonitor_compile.py)
- [tools/smartmonitor-compile-theme.py](../../tools/smartmonitor-compile-theme.py)

Current status on the known pair `theme_science fiction -> app/img.dat`:

- slot table layout matches exactly for records `1..18`
- overall compiled file size matches the vendor file exactly
- resource ordering now matches the vendor offsets for:
  - startup image
  - background image
  - image widgets
  - static text widgets
  - number glyph widgets
- the remaining mismatch is inside the generated text/number payload bytes themselves, not in the record structure

More specifically:

- static text renderer now reproduces the vendor `rendered_width` / `rendered_height`
- number glyph renderer now reproduces the vendor glyph widths and glyph height
- payload content is still approximate because Linux/PIL font rasterization is not byte-identical to the Windows/Qt output

## Per-widget record builders

The per-widget handlers append ordered QVariant lists before the final serializer packs them into the `img.dat` payload.

- `type=5` (`0x49fd20`, number)
  - ordered fields observed: `0x12`, `globalID+1`, `fastSensor`, `x`, `y`, `width`, `height`, `QFont`, `hAlign`, `fontColorRGB24`, `isDiv1204`, `fontColorAlpha`
- `type=6` (`0x4911e0`, datetime)
  - ordered fields observed: `0x0e`, `globalID+1`, `0x15`, `x`, `y`, `width`, `height`, `QFont`, `hAlign`, `fontColorRGB24`, `fontColorAlpha`, `dateTimeFormat`
- `type=3` (`0x4a98f0`, progress bar)
  - ordered fields observed: `0x0b`, `globalID+1`, `fastSensor`, `x`, `y`, `width`, `height`, `showType`, `bgColor`, `fgColor`, `frameColor`, `bgImagePath`, `fgImagePath`
- `type=2` (`0x4b7c30`, static text)
  - ordered fields observed: `0x13`, `globalID+1`, `x`, `y`, `width`, `height`, `QFont`, `fontColorRGB24`, `text`, `fontColorAlpha`

## Practical implication

At the moment, the most realistic way to get a working converter is:

1. Finish reversing the serialization logic in the tail of `0x47ecf0` and its byte-pack helpers.

## Why the converter is not ready yet

- `.ui` still uses a proprietary on-disk encoding before the DOM stage.
- The on-disk `.ui` encoding is now identified:
  - `0x4b8d80` implements RC4 KSA
  - `0x4b8e20` implements RC4 PRGA/XOR
  - `0x4b8e90` applies RC4 to the full file buffer
  - key string: `This product is designed by OuJianbo,zhe ge chan pin shi gzbkey she ji de`
  - key length is initialized at `0x520c10..0x520c57` using `strlen(...)`, so the effective length is `73`
- With that key, vendor `.ui` files decode directly into XML (`<?xml version="1.0" encoding="UTF-8"?> ...`).
- `img.dat` is a compiled packed format with embedded converted bitmap resources.
- The exact per-widget byte layout in the `QByteArray` serializer is still not fully decoded.
- The Windows binary is Qt/MinGW native code, so the remaining step is decompilation-level reverse engineering, not simple string extraction.

## Best next step

Use a native decompiler/disassembler on the Windows binary and continue from these exact functions:

- `0x47ecf0`
- byte-pack helpers called from the tail of `0x47ecf0`

The main short-term goal is to identify:

- how each widget record is serialized into bytes
- how images are embedded relative to those records
- how the first dword/record headers in `img.dat` map to widget type, size, and offsets

## Practical tooling

- A native `.ui` decoder now exists in:
  - [tools/smartmonitor-decode-ui.py](../../tools/smartmonitor-decode-ui.py)
- A native `.ui` parser now exists in:
  - [library/smartmonitor_ui.py](../../library/smartmonitor_ui.py)
- A partial `img.dat` parser now exists in:
  - [library/smartmonitor_imgdat.py](../../library/smartmonitor_imgdat.py)
- A native compiler now exists in:
  - [library/smartmonitor_compile.py](../../library/smartmonitor_compile.py)
  - [tools/smartmonitor-compile-theme.py](../../tools/smartmonitor-compile-theme.py)
