#!/usr/bin/env python3
"""Exercise real dnsmasq packet filtering inside `sudo unshare --net` only.

No third-party Python libraries. No DHCP leases are requested on the real LAN.
The rendered fixture config must use nb-server and 192.0.2.2; the real boot
artifact may be served read-only. Namespace destruction removes the veth pair.
"""

import argparse
import ipaddress
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import tempfile
import time


def command(*args):
    return subprocess.check_output(args, text=True)


def packet(mac, xid, arch, pxe=True, port=67):
    hardware = bytes.fromhex(mac.replace(":", ""))
    bootp = struct.pack(
        "!BBBBIHH4s4s4s4s16s64s128s",
        1, 1, 6, 0, xid, 0, 0x8000,
        bytes(4), bytes(4), bytes(4), bytes(4),
        hardware.ljust(16, b"\0"), bytes(64), bytes(128),
    )
    options = b"\x63\x82\x53\x63\x35\x01" + bytes([1 if port == 67 else 3])
    options += b"\x5d\x02" + struct.pack("!H", arch)
    options += b"\x37\x04\x3c\x43\x42\x2b"
    if pxe:
        vendor = f"PXEClient:Arch:{arch:05d}:UNDI:003016".encode()
        options += bytes([60, len(vendor)]) + vendor
    payload = (bootp + options + b"\xff").ljust(300, b"\0")
    udp = struct.pack("!HHHH", 68, port, 8 + len(payload), 0) + payload
    ip = struct.pack(
        "!BBHHHBBH4s4s", 0x45, 0, 20 + len(udp), 1, 0, 64, 17, 0,
        bytes(4), ipaddress.IPv4Address("255.255.255.255").packed,
    )
    total = sum(struct.unpack("!10H", ip))
    while total >> 16:
        total = (total & 0xffff) + (total >> 16)
    ip = ip[:10] + struct.pack("!H", (~total) & 0xffff) + ip[12:]
    return b"\xff" * 6 + hardware + b"\x08\x00" + ip + udp


def receive(sock, xid, port, timeout=1.5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        sock.settimeout(max(0.01, deadline - time.monotonic()))
        try:
            frame = sock.recv(65535)
        except socket.timeout:
            break
        if frame[12:14] != b"\x08\x00" or len(frame) < 300:
            continue
        header = 14 + (frame[14] & 15) * 4
        if frame[23] != 17 or struct.unpack_from("!H", frame, header)[0] != port:
            continue
        bootp = frame[header + 8:]
        if bootp[0] == 2 and struct.unpack_from("!I", bootp, 4)[0] == xid:
            return bootp
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    # Refuse to execute in the host namespace or any namespace with LAN links.
    if os.geteuid() != 0 or os.stat("/proc/self/ns/net").st_ino == os.stat("/proc/1/ns/net").st_ino:
        raise SystemExit("Run ONLY through sudo unshare --net; host namespace refused")
    links = json.loads(command("ip", "-j", "link", "show"))
    if {link["ifname"] for link in links} != {"lo"}:
        raise SystemExit("Expected a fresh isolated namespace containing only loopback")
    config = args.config.read_text()
    if "interface=nb-server\n" not in config or ",proxy," not in config:
        raise SystemExit("Expected an offline nb-server proxy-only fixture")
    command("ip", "link", "set", "lo", "up")
    command("ip", "link", "add", "nb-server", "type", "veth", "peer", "name", "nb-client")
    command("ip", "addr", "add", "192.0.2.2/24", "dev", "nb-server")
    for link in ["nb-server", "nb-client"]:
        command("ip", "link", "set", link, "up")
    with tempfile.TemporaryFile() as log, socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3)) as sock:
        sock.bind(("nb-client", 0))
        process = subprocess.Popen(
            ["/usr/sbin/dnsmasq", "--keep-in-foreground", f"--conf-file={args.config}"],
            stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            time.sleep(0.3)
            if process.poll() is not None:
                raise RuntimeError("dnsmasq failed to start in the isolated namespace")
            cases = [
                ("cp03 UEFI architecture 7", "02:00:00:00:00:03", 7, True, True),
                ("cp03 UEFI architecture 9", "02:00:00:00:00:03", 9, True, True),
                ("cp01 excluded", "02:00:00:00:00:01", 7, True, False),
                ("cp02 excluded", "02:00:00:00:00:02", 7, True, False),
                ("unknown client excluded", "02:00:00:00:00:01", 7, True, False),
                ("cp03 legacy BIOS excluded", "02:00:00:00:00:03", 0, True, False),
                ("cp03 ordinary DHCP excluded", "02:00:00:00:00:03", 7, False, False),
            ]
            for port in (67, 4011):
                for index, (label, mac, arch, pxe, expected) in enumerate(cases, 100):
                    xid = port * 1000 + index
                    sock.send(packet(mac, xid, arch, pxe, port))
                    response = receive(sock, xid, port)
                    if (response is not None) != expected:
                        raise AssertionError(f"{label} port {port}: unexpected response={response is not None}")
                    if response is not None:
                        if response[16:20] != bytes(4):
                            raise AssertionError("Proxy attempted to allocate an address")
                        if response[20:24] != ipaddress.IPv4Address("192.0.2.2").packed:
                            raise AssertionError("Unexpected next boot server")
                        # dnsmasq's single-service UEFI path sends the file on 4011.
                        if port == 4011 and response[108:236].split(b"\0", 1)[0] != b"Talos-v1.14.1-amd64-secureboot.efi":
                            raise AssertionError("Expected boot artifact missing from proxy response")
                    print(f"PASS {label} port {port}", flush=True)
        finally:
            process.terminate()
            process.wait(timeout=5)
            log.seek(0)
            print(log.read().decode(errors="replace"))


if __name__ == "__main__":
    main()
