#!/usr/bin/env python3

import argparse
import base64
import os
import sys


def osc52_copy(data: bytes, primary: bool):
    data_enc = base64.b64encode(data)
    clipboard = b"p" if primary else b"c"
    buf = b"\033]52;" + clipboard + b";" + data_enc + b"\a"
    if "TMUX" in os.environ:
        buf = b"\033Ptmux;\033" + buf + b"\033\\"
    sys.stdout.buffer.write(buf)


def osc52_paste(primary: bool) -> bytes:
    clipboard = b"p" if primary else b"c"
    buf = b"\033]52;" + clipboard + b";?\a"
    sys.stdout.buffer.write(buf)

    # FIXME: Does not work.
    with open("/dev/tty", "rb") as f:
        buf = f.read()
        print(buf)

    return buf


def osc_copy():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--clear",
        action="store_true",
        help="Instead of copying anything, clear the clipboard",
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

    osc52_copy(data, args.primary)


def osc_paste():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--clear",
        action="store_true",
        help="Instead of copying anything, clear the clipboard",
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
    osc52_paste(args.primary)
