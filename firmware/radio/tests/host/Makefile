# Host tests for radio airtime, duty, backoff, scheduler, HAL mock.
# Run: make -C firmware/radio/tests/host
# SPDX-License-Identifier: Apache-2.0

CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O1 -g
CFLAGS += -I../../include -D_POSIX_C_SOURCE=200809L

SRC = ../../src
MOCK = ../../src/mock

OBJ = build/airtime.o build/duty.o build/backoff.o build/sched.o \
      build/rhal.o build/us915.o build/rhal_mock.o

TESTS = airtime duty backoff sched hal_mock

test: $(TESTS:%=build/test_%)
	@for t in $(TESTS); do echo "== $$t =="; ./build/test_$$t || exit 1; done
	@echo "All radio host tests passed."

build/%.o: $(SRC)/%.c | build
	$(CC) $(CFLAGS) -c -o $@ $<

build/rhal_mock.o: $(MOCK)/rhal_mock.c | build
	$(CC) $(CFLAGS) -c -o $@ $<

build/test_%: test_%.c $(OBJ)
	$(CC) $(CFLAGS) -o $@ $< $(OBJ)

build:
	mkdir -p build

clean:
	rm -rf build

.PHONY: test clean
.SECONDARY: $(OBJ)
