# SmartMonitor HID Notes

These notes document the 3.5" HID SmartMonitor discovered from Linux `hidraw` access and USBPcap captures of the vendor Windows application.

## Confirmed transport

- USB HID only, no `tty`, no DRM/framebuffer
- `VID:PID = 0483:0065`
- Interrupt endpoints:
  - `0x02` OUT, 64 bytes
  - `0x81` IN, 64 bytes
- Linux `hidraw` writes use a leading zero report ID and 64-byte payloads

## Confirmed upload flow

Theme download is not a raw framebuffer push. The vendor application uses:

1. `01 72 65 73 65 74 ...` (`\x01reset`)
2. wait about 2.5 seconds
3. `79 6d 6f 64 65 6d ...` (`ymodem`)
4. device replies with `06 43 ...`
5. YMODEM upload of `img.dat`

The captured YMODEM transfer used:

- remote filename: `img.dat`
- declared file size: `524070`
- 1024-byte `STX` data blocks
- final padded block with `0x1A`
- `EOT`
- final empty block 0

The device ACKs every stage with an `IN` report starting with `0x06`.

## Runtime packets seen after upload

Three recurring OUT packet families were observed after the theme transfer.

### Command `0x00`

Format:

- byte 0: command `0x00`
- byte 1: pair count
- then repeated `(tag, value_be16)`

Example:

```text
00 06 04 00 42 05 00 26 06 00 3f 07 00 00 08 00 00 03 00 43
```

decodes to:

```text
(4, 66), (5, 38), (6, 63), (7, 0), (8, 0), (3, 67)
```

### Command `0x02`

Format:

- byte 0: command `0x02`
- byte 1: pair count
- then repeated `(tag, value_be16)`

Example:

```text
02 14 01 00 38 02 07 37 03 00 0a 04 00 00 05 00 38 ...
```

decodes to:

```text
(1, 56), (2, 1847), (3, 10), (4, 0), (5, 56), ...
```

### Command `0x03`

Observed layout:

```text
03 01 15 yy mm dd HH MM SS weekday 64
```

Example:

```text
03 01 15 1a 04 0b 14 35 26 06 64
```

This matches:

- year offset from 2000: `0x1a` -> `2026`
- month/day/hour/minute/second
- weekday

## Current status

- HID transport works from Linux
- theme upload can be reproduced with `reset + ymodem + img.dat`
- the previous experimental `rev.A` framebuffer hypothesis is incorrect for this device
- the remaining work is mapping runtime `(tag -> metric)` pairs so system telemetry can be generated natively from this project
