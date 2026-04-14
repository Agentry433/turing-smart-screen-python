#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import hashlib
import struct
from collections import Counter
from pathlib import Path


def iter_epb_packets(path: Path):
    with path.open("rb") as stream:
        while True:
            header = stream.read(8)
            if len(header) < 8:
                return

            block_type, block_len = struct.unpack("<II", header)
            body = stream.read(block_len - 12)
            block_end = stream.read(4)
            if len(body) != block_len - 12 or len(block_end) != 4:
                return

            if block_type != 0x00000006 or len(body) < 20:
                continue

            _, ts_hi, ts_lo, captured_len, _ = struct.unpack("<IIIII", body[:20])
            packet = body[20:20 + captured_len]
            timestamp = ((ts_hi << 32) | ts_lo) / 1_000_000
            yield timestamp, packet


def parse_usbpcap_packet(packet: bytes):
    if len(packet) < 27:
        return None

    header_len = struct.unpack_from("<H", packet, 0)[0]
    if header_len not in (27, 28) or len(packet) < header_len:
        return None

    data_len = struct.unpack_from("<I", packet, 23)[0]
    payload = packet[header_len:header_len + data_len]
    return {
        "info": packet[16],
        "bus": struct.unpack_from("<H", packet, 17)[0],
        "device": struct.unpack_from("<H", packet, 19)[0],
        "endpoint": packet[21],
        "transfer": packet[22],
        "payload": payload,
        "data_len": data_len,
    }


def collect_interrupt_events(path: Path):
    events = []
    for timestamp, packet in iter_epb_packets(path):
        parsed = parse_usbpcap_packet(packet)
        if not parsed:
            continue
        if parsed["transfer"] != 1 or parsed["endpoint"] not in (0x02, 0x81):
            continue

        parsed["timestamp"] = timestamp
        events.append(parsed)
    return events


def auto_select_device(events):
    counts = Counter()
    for event in events:
        if event["endpoint"] == 0x02 and event["info"] == 0 and event["data_len"] == 64:
            counts[event["device"]] += 1

    if not counts:
        raise RuntimeError("No 64-byte HID interrupt OUT transfers found in capture")

    return counts.most_common(1)[0][0]


def split_segments(events, gap_seconds: float):
    segments = []
    current = []
    previous_ts = None

    for event in events:
        if previous_ts is not None and event["timestamp"] - previous_ts > gap_seconds:
            segments.append(current)
            current = []
        current.append(event)
        previous_ts = event["timestamp"]

    if current:
        segments.append(current)
    return segments


def crc16_xmodem(payload: bytes) -> int:
    crc = 0
    for byte in payload:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def extract_ymodem_from_segment(segment):
    reports = [
        event["payload"]
        for event in segment
        if event["endpoint"] == 0x02 and event["info"] == 0 and event["data_len"] == 64
    ]
    if not reports or not reports[0].startswith(b"ymodem"):
        return None

    reports = reports[1:]
    frames = []
    index = 0

    while index < len(reports):
        report = reports[index]
        first_byte = report[0]

        if first_byte == 0x01:
            frame_size = 133
        elif first_byte == 0x02:
            frame_size = 1029
        elif first_byte == 0x04:
            frames.append(("EOT", None, b""))
            index += 1
            continue
        else:
            if any(report):
                raise ValueError(f"Unexpected non-zero report during YMODEM parsing: {report[:16].hex()}")
            index += 1
            continue

        raw = b""
        while len(raw) < frame_size and index < len(reports):
            raw += reports[index]
            index += 1
        frame = raw[:frame_size]
        block_number = frame[1]
        payload = frame[3:-2]
        checksum = int.from_bytes(frame[-2:], "big")
        if (frame[1] ^ frame[2]) != 0xFF:
            raise ValueError(f"Invalid YMODEM block complement for block {block_number}")
        if crc16_xmodem(payload) != checksum:
            raise ValueError(f"Invalid YMODEM CRC for block {block_number}")

        frames.append(("SOH" if first_byte == 0x01 else "STX", block_number, payload))

    if not frames or frames[0][0] != "SOH" or frames[0][1] != 0:
        raise ValueError("Did not find YMODEM block 0")

    name_field, size_field, *_ = frames[0][2].split(b"\x00")
    remote_name = name_field.decode("ascii", "replace")
    declared_size = int(size_field.decode("ascii", "replace") or "0")

    data = bytearray()
    for frame_type, block_number, payload in frames[1:]:
        if frame_type == "STX":
            data.extend(payload)
        elif frame_type == "SOH" and block_number != 0:
            data.extend(payload)

    return {
        "remote_name": remote_name,
        "declared_size": declared_size,
        "payload": bytes(data[:declared_size]),
        "frames": frames,
    }


def decode_tag_values(payload: bytes):
    if len(payload) < 2:
        return None
    count = payload[1]
    offset = 2
    values = []
    for _ in range(count):
        if offset + 3 > len(payload):
            break
        tag = payload[offset]
        value = int.from_bytes(payload[offset + 1:offset + 3], "big")
        values.append((tag, value))
        offset += 3
    return values


def format_segment_summary(index, segment):
    out_payloads = [event for event in segment if event["endpoint"] == 0x02 and event["info"] == 0 and event["data_len"]]
    in_payloads = [event for event in segment if event["endpoint"] == 0x81 and event["info"] == 1 and event["data_len"]]
    duration = segment[-1]["timestamp"] - segment[0]["timestamp"]
    first_out = out_payloads[0]["payload"][:16].hex() if out_payloads else "-"
    first_in = in_payloads[0]["payload"][:16].hex() if in_payloads else "-"
    return f"segment {index:02d}: duration={duration:.3f}s out={len(out_payloads)} in={len(in_payloads)} first_out={first_out} first_in={first_in}"


def main():
    parser = argparse.ArgumentParser(description="Analyze USBPcap captures for the HID SmartMonitor")
    parser.add_argument("capture", type=Path, help="Path to .pcapng USBPcap capture")
    parser.add_argument("--device", type=int, default=None, help="USB device address inside the capture")
    parser.add_argument("--gap", type=float, default=0.5, help="Segment split gap in seconds")
    parser.add_argument("--extract-ymodem", type=Path, default=None, help="Write extracted img.dat from first YMODEM transfer")
    parser.add_argument("--decode-runtime", action="store_true", help="Decode command 0/2/3 packets after the transfer")
    args = parser.parse_args()

    events = collect_interrupt_events(args.capture)
    try:
        device = args.device if args.device is not None else auto_select_device(events)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    device_events = [event for event in events if event["device"] == device]
    if not device_events:
        raise SystemExit(f"No HID interrupt traffic found for device address {device}")

    segments = split_segments(device_events, gap_seconds=args.gap)
    print(f"Selected USB device address: {device}")
    print(f"Total interrupt events: {len(device_events)}")
    print(f"Segments: {len(segments)}")
    for index, segment in enumerate(segments):
        print(format_segment_summary(index, segment))

    ymodem_segment = None
    extracted = None
    for segment in segments:
        try:
            extracted = extract_ymodem_from_segment(segment)
        except ValueError:
            continue
        if extracted:
            ymodem_segment = segment
            break

    if extracted:
        sha256 = hashlib.sha256(extracted["payload"]).hexdigest()
        print(
            f"YMODEM: remote_name={extracted['remote_name']} size={len(extracted['payload'])} "
            f"declared={extracted['declared_size']} sha256={sha256}"
        )
        if args.extract_ymodem:
            args.extract_ymodem.write_bytes(extracted["payload"])
            print(f"Extracted YMODEM payload to {args.extract_ymodem}")
    else:
        print("YMODEM transfer not found")

    if args.decode_runtime:
        print("Runtime packet decode:")
        for segment in segments:
            if segment is ymodem_segment:
                continue
            for event in segment:
                if event["endpoint"] != 0x02 or event["info"] != 0 or event["data_len"] != 64:
                    continue
                payload = event["payload"]
                if payload[0] in (0x00, 0x02):
                    print(
                        f"{event['timestamp']:.6f} cmd={payload[0]} count={payload[1]} "
                        f"values={decode_tag_values(payload)}"
                    )
                elif payload[0] == 0x03 and len(payload) >= 11:
                    year = 2000 + payload[3]
                    print(
                        f"{event['timestamp']:.6f} cmd=3 "
                        f"time={year:04d}-{payload[4]:02d}-{payload[5]:02d} "
                        f"{payload[6]:02d}:{payload[7]:02d}:{payload[8]:02d} weekday={payload[9]}"
                    )


if __name__ == "__main__":
    main()
