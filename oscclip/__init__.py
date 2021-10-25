#!/usr/bin/env python3

import argparse
import base64
import curses
import os
import subprocess
import sys
import time


def die(msg: str):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def write_tty(data: bytes):
    with open("/dev/tty", "wb") as f:
        f.write(data)
        f.flush()


def read_tty(terminator: bytes) -> bytes:
    with open("/dev/tty", "rb", buffering=0) as f:
        data = b""
        while terminator not in data:
            data += f.read(1)
    return data


def _tmux_dcs_passthrough(data: bytes) -> bytes:
    return b"\033Ptmux;\033" + data + b"\033\\"


def _tmux_query_osc52() -> bool:
    p = subprocess.run(["tmux", "show-options", "-s"], check=True, capture_output=True)
    if "set-clipboard on" in p.stdout.decode():
        return True
    return False


def _tmux_osc52_paste(primary: bool) -> bytes:
    if not _tmux_query_osc52():
        die("tmux `set-clipboard` is disabled")
    if primary:
        die("primary clipboard is not supported under tmux")
    try:
        subprocess.run(["tmux", "refresh-client", "-l"], check=True)
        # It might be a bit racy; give the terminal time.
        time.sleep(0.05)
        p = subprocess.run(["tmux", "save-buffer", "-"], check=True, capture_output=True)
    except Exception as e:
        die(f"calling `tmux` failed: {e}")
    return p.stdout


def _parse_osc52_response(data: bytes) -> bytes:
    # TODO: Make indices more robust.
    if data[:5] != b"\033]52;" or data[-2:] != b"\033\\":
        raise RuntimeError(f"received invalid OSC52 response: {str(data)}")
    return base64.b64decode(data[7:-2])


def osc52_copy(data: bytes, primary: bool, direct: bool):
    data_enc = base64.b64encode(data)
    clipboard = b"p" if primary else b"c"
    buf = b"\033]52;" + clipboard + b";" + data_enc + b"\a"
    if "TMUX" in os.environ and not direct:
        buf = _tmux_dcs_passthrough(buf)
    write_tty(buf)


def osc52_paste(primary: bool) -> bytes:
    if "TMUX" in os.environ:
        return _tmux_osc52_paste(primary)

    clipboard = b"p" if primary else b"c"
    buf = b"\033]52;" + clipboard + b";?\a"
    write_tty(buf)
    return _parse_osc52_response(read_tty(b"\033\\"))


def osc_copy():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--clear",
        action="store_true",
        help="Instead of copying anything, clear the clipboard",
    )
    parser.add_argument(
        "-d",
        "--direct",
        action="store_true",
        help="Bypass terminal multiplexers",
    )
    parser.add_argument(
        "-n",
        "--trim-newline",
        action="store_true",
        help="Do not copy the trailing newline character",
    )
    parser.add_argument(
        "-p",
        "--primary",
        action="store_true",
        help='Use the "primary" clipboard',
    )
    parser.add_argument(
        "text",
        nargs="?",
        help="Text to copy",
    )
    args = parser.parse_args()

    if args.clear:
        data = b""
    else:
        data = args.text.encode() if args.text else sys.stdin.buffer.read()
    if args.trim_newline:
        data = data.strip()

    osc52_copy(data, args.primary, args.direct)


def osc_paste():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n",
        "--trim-newline",
        action="store_true",
        help="Do not copy the trailing newline character",
    )
    parser.add_argument(
        "-p",
        "--primary",
        action="store_true",
        help='Use the "primary" clipboard',
    )
    args = parser.parse_args()

    try:
        curses.initscr()
        curses.noecho()
        curses.cbreak()
        data = osc52_paste(args.primary)
    finally:
        curses.nocbreak()
        curses.echo()
        curses.endwin()

    if args.trim_newline:
        data = data.strip()
    print(data.decode())
