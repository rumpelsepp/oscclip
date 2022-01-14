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
