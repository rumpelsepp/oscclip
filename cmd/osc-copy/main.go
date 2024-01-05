package main

import (
	"fmt"
	"io"
	"os"
	"runtime/debug"
	"strings"

	"github.com/alecthomas/kong"
	"github.com/aymanbagabas/go-osc52/v2"
)

func die(msg string, code int) {
	fmt.Fprintln(os.Stderr, msg)
	os.Exit(1)
}

type cli struct {
	Text    string `kong:"arg,default='-',help='Text to copy, - means stdin (default)'"`
	Bypass  bool   `kong:"help='Bypass terminal multiplexers if present'"`
	Clear   bool   `kong:"short='c',help='Clear clipboard and exit'"`
	Trim    bool   `kong:"short='t',help='Trim whitespace of input'"`
	Primary bool   `kong:"short='p',help='Use the primary X11 clipboard'"`
	Version bool   `kong:"help='Print version information and exit'"`
}

func main() {
	var args cli
	kong.Parse(&args)

	if args.Clear {
		seq := osc52.Clear()
		if args.Primary {
			seq = seq.Primary()
		}

		_, err := seq.WriteTo(os.Stderr)
		if err != nil {
			die(err.Error(), 1)
		}
		os.Exit(0)
	}

	if args.Version {
		buildInfo, ok := debug.ReadBuildInfo()
		if ok {
			fmt.Println(strings.TrimSpace(buildInfo.String()))
		} else {
			fmt.Println("unknown")
		}

		os.Exit(0)
	}

	var (
		seq  osc52.Sequence
		text = args.Text
	)

	if text == "-" {
		t, err := io.ReadAll(os.Stdin)
		if err != nil {
			die(err.Error(), 1)
		}

		text = string(t)
	}

	if args.Trim {
		text = strings.TrimSpace(text)
	}

	seq = osc52.New(text)
	if args.Primary {
		seq = seq.Primary()
	}

	if args.Bypass {
		if _, ok := os.LookupEnv("TMUX"); ok {
			seq = osc52.New(text).Tmux()
		} else if _, ok := os.LookupEnv("STY"); ok {
			seq = osc52.New(text).Screen()
		}
	}

	_, err := seq.WriteTo(os.Stderr)
	if err != nil {
		die(err.Error(), 1)
	}
}
