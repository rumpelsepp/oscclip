# oscclip

[![Packaging status](https://repology.org/badge/vertical-allrepos/oscclip.svg)](https://repology.org/project/oscclip/versions)

`oscclip` is a set of utilities which utilize the system clipboard via
terminal escape sequences.  Using these sequences, the system clipboard is
accessible via SSH as well.  Terminal multiplexers, such as `tmux` and
`screen`, are supported.

Two protocols are implemented:

* **OSC 52** — the classic clipboard escape sequence which is supported by
  many terminal emulators.  It is limited to plain text.
* **The kitty clipboard protocol (OSC 5522)** — a modern protocol developed by
  the [kitty](https://sw.kovidgoyal.net/kitty/) terminal emulator.  In addition
  to plain text, it supports arbitrary data types like images, proper error
  reporting and a permission system.

Both tools auto-detect the terminal's capabilities and prefer the kitty
clipboard protocol with fallback to OSC 52.  The behavior can be pinned with
the `--protocol` option.

## Installation

```
$ pipx install oscclip
# or: uv tool install oscclip
```

## Examples

**Setting the clipboard**

```
$ echo "Foo" | osc-copy
```

**Reading the clipboard**

```
$ osc-paste
Foo
```

**Copying arbitrary data types** (kitty protocol).  The MIME type is
detected automatically from the data:

```
$ osc-copy < screenshot.png
$ osc-copy -m image/png < screenshot.png
$ osc-paste -m image/png > screenshot.png
```

**Listing the MIME types available on the clipboard** (kitty protocol)

```
$ osc-paste --list-mime
text/plain
image/png
```

**Displaying an image from the clipboard in the terminal** (kitty graphics protocol)

```
$ osc-paste --image
```

This requires a terminal which implements the kitty graphics protocol, e.g.
kitty, Ghostty, WezTerm or Konsole.

**Clearing the clipboard**

```
$ osc-copy --clear
```

**Bypassing terminal multiplexers** (see the tmux caveat below)

```
$ echo "Foo" | osc-copy --bypass
```

Run `osc-copy --help` / `osc-paste --help` for the full list of options.

## Permissions

Terminals which implement the kitty clipboard protocol ask the user for
permission when the clipboard is read.  In kitty, this behavior can be
controlled with the `clipboard_control` option in `kitty.conf`.

## Development

The project is managed with [uv](https://docs.astral.sh/uv/); project tasks
are defined in the [justfile](justfile).

```
$ git clone https://github.com/rumpelsepp/oscclip
$ cd oscclip
$ uv sync
$ just            # lint + typecheck + test
```

Run `just --list` to see all tasks.

Tooling: [ruff](https://docs.astral.sh/ruff/) (lint & format),
[mypy](https://mypy-lang.org/) (`--strict`), [ty](https://docs.astral.sh/ty/)
and [pytest](https://pytest.org).

## Fuzzing

The parsers are covered by property-based tests
([hypothesis](https://hypothesis.readthedocs.io/), in
`tests/test_properties.py`) and by a coverage-guided fuzzer
([atheris](https://github.com/google/atheris), libFuzzer-based, in
`fuzz/fuzz_parsers.py` with seeds in `fuzz/corpus/`):

```
$ just fuzz         # hypothesis with the extended "fuzz" profile
$ just fuzz-native  # atheris for 60s; crashes land in fuzz/crashes/
```

## Tested Terminals

* [alacritty](https://github.com/alacritty/alacritty) (OSC 52)
* [foot](https://codeberg.org/dnkl/foot) (OSC 52)
* [ghostty](https://ghostty.org/) (OSC 52 and kitty clipboard protocol)
* [kitty](https://sw.kovidgoyal.net/kitty/) (OSC 52 and kitty clipboard protocol)
* tmux 3.8 (OSC 52 mediation)

For a list of terminals that support OSC 52, see
[this table](https://github.com/ojroques/vim-oscyank#terminals-with-osc52-support).

## Caveats

### tmux

tmux mediates clipboard access between panes and the outer terminal.  The
behavior is controlled by two tmux server options:

* `set-clipboard` (default: `external`) — whether tmux sets the system
  clipboard of the outer terminal.  Only with `set -s set-clipboard on`
  does tmux accept OSC 52 clipboard writes from panes, so this is required
  for `osc-copy` to work from inside tmux.
* `get-clipboard` (tmux >= 3.7) — how tmux answers clipboard queries from
  panes.  With `buffer` (the default in tmux 3.8), tmux answers with its
  newest paste buffer; `request` and `both` forward the query to the outer
  terminal instead (`tmux set -s get-clipboard both`).

tmux does not implement the kitty clipboard protocol (OSC 5522); `oscclip`
detects this and automatically falls back to OSC 52.

With `--bypass`, all escape sequences are wrapped in tmux' passthrough DCS
sequences and reach the outer terminal unchanged.  This requires the
`allow-passthrough` option (`tmux set -w allow-passthrough on`).
