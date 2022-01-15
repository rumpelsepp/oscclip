# oscclip

`oscclip` is a little, zero dependency python utility which utilized the system clipboard via OSC52 escape sequences.
Using these sequences, the system clipboard is accessible via SSH as well.
Terminal multiplexers, such as `tmux` and `screen` are supported.

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

## Tested Terminals

* foot


## Installation

**Arch Linux**

```
$ paru -S oscclip
```

**Run via poetry**

Check if your distribution provides [`poetry`](https://python-poetry.org) it via its package management system!
It might be called `python-poetry`, `python3-poetry` or similar!

Otherwise: https://python-poetry.org/docs/#installation

```
$ poetry install 
$ poetry run ocs-copy
```
