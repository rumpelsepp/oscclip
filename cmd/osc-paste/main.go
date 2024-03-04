package main

import (
	"bufio"
	"bytes"
	"encoding/base64"
	"fmt"
	"io"
	"os"
	"runtime/debug"
	"strings"

	"github.com/alecthomas/kong"
	"github.com/aymanbagabas/go-osc52/v2"
	"github.com/gdamore/tcell/v2"
)

type cli struct {
	Trim    bool `kong:"short='t',help='Trim whitespace of input'"`
	Primary bool `kong:"short='p',help='Use the primary X11 clipboard'"`
	Version bool `kong:"help='Print version information and exit'"`
}

type OSC52Response struct {
	Source string
	Data   []byte
}

func ParseOSC52Resp(raw []byte) (*OSC52Response, error) {
	var (
		prefixLen = 4
		source    string
	)

	// Check OSC52 header.
	if !bytes.Equal(raw[:prefixLen], []byte("\x1b]52")) {
		return nil, fmt.Errorf("invalid OSC52 header: %x", raw[:prefixLen])
	}

	// Check OSC52 terminator.
	if raw[len(raw)-1] != '\a' {
		return nil, fmt.Errorf("invalid OSC52 data; invalid terminator: %x", raw)
	}

	// Strip header.
	raw = raw[prefixLen:]

	if raw[0] == ';' && raw[2] == ';' {
		// Variant 1: source is set.
		source = string(raw[1])
		prefixLen = 3
	} else if raw[0] == ';' && raw[1] == ';' && raw[2] != ';' {
		// Variant 2: source is unset.
		source = "c"
		prefixLen = 2
	} else {
		// Variant 3: Data is invalid.
		return nil, fmt.Errorf("invalid OSC52 arguments: %x", raw)
	}

	// Strip arguments and terminator.
	raw = raw[prefixLen : len(raw)-1]

	bufSize := base64.StdEncoding.DecodedLen(len(raw))
	data := make([]byte, bufSize)
	n, err := base64.StdEncoding.Decode(data, raw)
	if err != nil {
		return nil, fmt.Errorf("%s: %q", err, raw)
	}

	return &OSC52Response{Source: source, Data: data[:n]}, nil
}

func die(msg string, code int) {
	fmt.Fprintln(os.Stderr, msg)
	os.Exit(1)
}

func main() {
	var args cli
	kong.Parse(&args)

	if args.Version {
		buildInfo, ok := debug.ReadBuildInfo()
		if ok {
			fmt.Println(strings.TrimSpace(buildInfo.String()))
		} else {
			fmt.Println("unknown")
		}

		os.Exit(0)
	}

	seq := osc52.Query()

	if args.Primary {
		seq = seq.Primary()
	}

	tty, err := tcell.NewDevTty()
	if err != nil {
		die(err.Error(), 1)
	}

	tty.Start()
	_, err = seq.WriteTo(tty)
	if err != nil {
		die(err.Error(), 1)
	}
	reader := bufio.NewReader(tty)
	slice, err := reader.ReadSlice('\a')
	if err != nil {
		die(err.Error(), 1)
	}
	tty.Stop()
	tty.Close()

	resp, err := ParseOSC52Resp(slice)
	if err != nil {
		die(err.Error(), 1)
	}

	data := resp.Data

	if args.Trim {
		data = bytes.TrimSpace(data)
	}

	if !bytes.HasSuffix(data, []byte("\n")) {
		data = append(data, '\n')
	}

	if _, err := io.Copy(os.Stderr, bytes.NewReader(data)); err != nil {
		die(err.Error(), 1)
	}
}
