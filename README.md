# oscclip

**There is a better maintained alternative available; just use this instead: https://github.com/theimpostor/osc**

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

## Examples

**Setting the clipboard**

```
$ echo "Foo" | osc-copy
```

**Setting the clipboard and bypass terminal multiplexers**

```
$ echo "Foo" | osc-copy --bypass
```

**Reading the clipboard**

```
$ osc-paste
Foo
```

**Copying arbitrary data types** (kitty protocol)

```
$ osc-copy -m image/png < screenshot.png
$ osc-paste -m image/png > screenshot.png
```

**Listing the MIME types available on the clipboard** (kitty protocol)

```
$ osc-paste --list-mime
text/plain
image/png
```

**Clearing the clipboard**

```
$ osc-copy --clear
```

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
$ just
```

Tooling: [ruff](https://docs.astral.sh/ruff/) (lint & format),
[mypy](https://mypy-lang.org/) (`--strict`), [ty](https://docs.astral.sh/ty/)
and [pytest](https://pytest.org).

## Tested Terminals

* [alacritty](https://github.com/alacritty/alacritty) (OSC 52)
* [foot](https://codeberg.org/dnkl/foot) (OSC 52)
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
