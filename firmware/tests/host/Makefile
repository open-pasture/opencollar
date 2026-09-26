CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O1 -g

test: build/test_main
	./build/test_main

build/test_main: test_main.c ../../src/geofence.c ../../src/cue.c ../../src/geofence.h ../../src/cue.h
	mkdir -p build
	$(CC) $(CFLAGS) -o $@ test_main.c ../../src/geofence.c ../../src/cue.c -lm

clean:
	rm -rf build

.PHONY: test clean
