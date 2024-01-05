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

func parseOSC52Resp(data []byte) ([]byte, error) {
	prefix_len := 6
	if len(data) < prefix_len && (!bytes.Equal(data[:5], []byte("\033]52;")) || !bytes.Equal(data[len(data)-2:], []byte("\033\\"))) {
		return nil, fmt.Errorf("got invalid OSC52 response: %x", data)
	}

	var (
		dataBuf = data[6 : len(data)-1]
		bufSize = base64.StdEncoding.DecodedLen(len(dataBuf))
		buf     = make([]byte, bufSize)
	)

	n, err := base64.StdEncoding.Decode(buf, dataBuf)
	return buf[:n], err
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

	response, err := parseOSC52Resp(slice)
	if err != nil {
		die(err.Error(), 1)
	}

	if args.Trim {
		response = bytes.TrimSpace(response)
	}

	if !bytes.HasSuffix(response, []byte("\n")) {
		response = append(response, '\n')
	}

	if _, err := io.Copy(os.Stderr, bytes.NewReader(response)); err != nil {
		die(err.Error(), 1)
	}
}
