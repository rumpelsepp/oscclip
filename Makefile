# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: MIT

GO ?= go

.PHONY: build
build: osc-copy osc-paste

.PHONY: osc-copy
osc-copy:
	$(GO) build $(GOFLAGS) -o $@ ./cmd/$@

.PHONY: osc-paste
osc-paste:
	$(GO) build $(GOFLAGS) -o $@ ./cmd/$@
