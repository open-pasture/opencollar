# SPDX-License-Identifier: Apache-2.0
# Rook LTE host tests. Run: make -C firmware/rook/tests/host
# Reuses the collar core and the RAM store from firmware/tests/host.
CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O1 -g
FWROOT = ../../..
SRC = $(FWROOT)/src
CORE_T = $(FWROOT)/tests/host
MONO = $(FWROOT)/third_party/monocypher
ROOK = ../../src
CFLAGS += -ffp-contract=off -D_POSIX_C_SOURCE=200809L -D_DEFAULT_SOURCE -I$(SRC) -I$(ROOK) -I$(MONO) -I$(CORE_T)
CFLAGS += -DSAMPLES=\"../mock_server/samples\"

FW = protocol shape geofence cue command config slots acks provision app
ROOKS = rook_queue rook_backoff rook_report rook_http rook_fence rook_battery_math
TESTS = queue backoff report http fence battery

OBJ = $(FW:%=build/fw_%.o) $(ROOKS:%=build/%.o) build/monocypher.o build/monocypher-ed25519.o build/store_ram.o
HDR = $(wildcard $(SRC)/*.h) $(wildcard $(ROOK)/*.h) test.h

test: $(TESTS:%=build/test_%)
	@for t in $(TESTS); do ./build/test_$$t || exit 1; done

build/fw_%.o: $(SRC)/%.c $(HDR) | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/rook_%.o: $(ROOK)/rook_%.c $(HDR) | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/monocypher.o: $(MONO)/monocypher.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/monocypher-ed25519.o: $(MONO)/monocypher-ed25519.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/store_ram.o: $(CORE_T)/store_ram.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/test_%: test_%.c $(OBJ) $(HDR)
	$(CC) $(CFLAGS) -o $@ $< $(OBJ) -lm
build:
	mkdir -p build
clean:
	rm -rf build
.PHONY: test clean
.SECONDARY: $(OBJ)
