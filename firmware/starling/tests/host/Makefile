# SPDX-License-Identifier: Apache-2.0
# Host tests for Starling. Run: make -C firmware/starling/tests/host

CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O1 -g
CFLAGS += -ffp-contract=off -D_POSIX_C_SOURCE=200809L

STARLING = ../..
FW = ../../..
SRC = $(FW)/src
CORE = $(FW)/core
MONO = $(FW)/third_party/monocypher
STUBS = $(STARLING)/stubs
HOST_RAM = $(FW)/tests/host

CFLAGS += -I$(STARLING)/src -I$(CORE) -I$(SRC) -I$(MONO) \
	-I$(STUBS)/lora -I$(STUBS)/radio -I$(HOST_RAM)

TESTS = geofence_fake fence_store gossip ubx_nmea demo

OBJ = \
	build/protocol.o build/shape.o build/geofence.o build/cue.o \
	build/gnss_fake.o build/gnss_ubx.o build/fence_store.o \
	build/gossip.o build/power.o build/app.o \
	build/fence_gossip.o build/radio_hal.o \
	build/monocypher.o build/monocypher-ed25519.o build/store_ram.o

test: $(TESTS:%=build/test_%)
	@for t in $(TESTS); do ./build/test_$$t || exit 1; done

build/protocol.o: $(SRC)/protocol.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/shape.o: $(SRC)/shape.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/geofence.o: $(SRC)/geofence.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/cue.o: $(SRC)/cue.c | build
	$(CC) $(CFLAGS) -c -o $@ $<

build/gnss_fake.o: $(STARLING)/src/gnss_fake.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/gnss_ubx.o: $(STARLING)/src/gnss_ubx.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/fence_store.o: $(STARLING)/src/fence_store.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/gossip.o: $(STARLING)/src/gossip.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/power.o: $(STARLING)/src/power.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/app.o: $(STARLING)/src/app.c | build
	$(CC) $(CFLAGS) -c -o $@ $<

build/fence_gossip.o: $(STUBS)/lora/fence_gossip.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/radio_hal.o: $(STUBS)/radio/radio_hal.c | build
	$(CC) $(CFLAGS) -c -o $@ $<

build/monocypher.o: $(MONO)/monocypher.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/monocypher-ed25519.o: $(MONO)/monocypher-ed25519.c | build
	$(CC) $(CFLAGS) -c -o $@ $<
build/store_ram.o: $(HOST_RAM)/store_ram.c | build
	$(CC) $(CFLAGS) -c -o $@ $<

build/test_%: test_%.c $(OBJ) | build
	$(CC) $(CFLAGS) -o $@ $< $(OBJ) -lm

build:
	mkdir -p build

clean:
	rm -rf build

.PHONY: test clean
.SECONDARY: $(OBJ)
