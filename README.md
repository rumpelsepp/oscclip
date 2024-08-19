# oscclip

**There is a better maintained alternative available; just use this instead: https://github.com/theimpostor/osc**

[![Packaging status](https://repology.org/badge/vertical-allrepos/oscclip.svg)](https://repology.org/project/oscclip/versions)

`oscclip` is a utility which utilizes the system clipboard via OSC52 escape sequences.
Using these sequences, the system clipboard is accessible via SSH as well.
Terminal multiplexers, such as `tmux` and `screen` are supported.

## Build

```
$ make
```

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

## Tested Terminals

* [alacritty](https://github.com/alacritty/alacritty)
* [foot](https://codeberg.org/dnkl/foot)

For a list of terminals that support OSC52, see [this table](https://github.com/ojroques/vim-oscyank#vim-oscyank).

## Caveats

### tmux

There is a [bug](https://github.com/tmux/tmux/pull/2942) in `tmux` 
Due to this `osc-paste` does not work with `tmux < 3.3` running in `foot`.

In order to make `--bypass` work, `allow-passthrough` must be enabled.
Check the manpage of `tmux`.
`osc-copy` issues a warning to `stderr` when this option is not set and `--bypass` is present.

In order to let `tmux` set the system clipboard, the option `set-clipboard` must be enabled.

## Installation

**Arch Linux**

```
$ paru -S oscclip
```

**NixOS**

```
$ nix-shell -p oscclip
```
