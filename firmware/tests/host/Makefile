# Host tests for the collar logic, one binary per module. Run: make -C firmware/tests/host
#
# The firmware's shape rules are single precision in a fixed order of
# operations, so floating-point contraction stays off here as in the build.

CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O1 -g
CFLAGS += -ffp-contract=off -D_POSIX_C_SOURCE=200809L -I../../third_party/monocypher

SRC = ../../src
MONO = ../../third_party/monocypher
FW = protocol shape geofence cue command config slots acks provision app
TESTS = geofence shape command config slots store cue provision app herd

OBJ = $(FW:%=build/fw_%.o) build/monocypher.o build/monocypher-ed25519.o \
      build/store_ram.o build/json.o
HDR = $(wildcard $(SRC)/*.h) $(wildcard *.h)

test: $(TESTS:%=build/test_%)
	@for t in $(TESTS); do ./build/test_$$t || exit 1; done

build/fw_%.o: $(SRC)/%.c $(HDR) | build
	$(CC) $(CFLAGS) -c -o $@ $<

build/monocypher.o: $(MONO)/monocypher.c $(MONO)/monocypher.h | build
	$(CC) $(CFLAGS) -c -o $@ $<

build/monocypher-ed25519.o: $(MONO)/monocypher-ed25519.c $(MONO)/monocypher-ed25519.h | build
	$(CC) $(CFLAGS) -c -o $@ $<

build/store_ram.o: store_ram.c $(HDR) | build
	$(CC) $(CFLAGS) -c -o $@ $<

build/json.o: json.c json.h | build
	$(CC) $(CFLAGS) -c -o $@ $<

build/test_%: test_%.c $(OBJ) $(HDR)
	$(CC) $(CFLAGS) -o $@ $< $(OBJ) -lm

build:
	mkdir -p build

clean:
	rm -rf build

.PHONY: test clean
.SECONDARY: $(OBJ)
