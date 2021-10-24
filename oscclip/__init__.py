#!/usr/bin/env python3

import argparse
import base64
import os
import subprocess
import sys
import time


def die(msg: str):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def osc52_copy(data: bytes, primary: bool, direct: bool):
    data_enc = base64.b64encode(data)
    clipboard = b"p" if primary else b"c"
    buf = b"\033]52;" + clipboard + b";" + data_enc + b"\a"
    if "TMUX" in os.environ and not direct:
        buf = b"\033Ptmux;\033" + buf + b"\033\\"
    sys.stdout.buffer.write(buf)


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


def osc52_paste(primary: bool) -> bytes:
    if "TMUX" in os.environ:
        return _tmux_osc52_paste(primary)
    die("Pasting from anything different than tmux is currently broken. Help is appreciated: https://codeberg.org/rumpelsepp/oscclip")
    return b""

    # clipboard = b"p" if primary else b"c"
    # buf = b"\033]52;" + clipboard + b";?\a"
    # sys.stdout.buffer.write(buf)
    #
    # # FIXME: Does not work.
    # with open("/dev/tty", "rb") as f:
    #     buf = f.read()
    #     print(buf)
    #
    # return buf


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
        help="Do not bypass terminal multiplexers",
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

    data = osc52_paste(args.primary)
    if args.trim_newline:
        data = data.strip()
    sys.stdout.buffer.write(data)
