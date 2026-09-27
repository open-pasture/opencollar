/*
 * Line input on the console UART (the board's USB serial), for provisioning
 * and bench commands (protocol v1 §3.9). One line at a time: the UART
 * interrupt collects bytes until CR or LF, then raises a poll signal and
 * ignores input until the main thread has handled the line. The buffer is
 * the 12 KB command receive buffer, so a full boundary command fits on one
 * line. No echo: a pasted 12 KB command must not be slowed down by it.
 */
#ifndef OPENCOLLAR_CONSOLE_H
#define OPENCOLLAR_CONSOLE_H

#include <stdbool.h>
#include <stddef.h>

#include <zephyr/kernel.h>

#include "protocol.h"

/* "boundary " + the largest command, with room to see that one is too large */
#define CONSOLE_LINE_MAX (PROTO_MAX_COMMAND_BYTES + 32)

/* Start listening; sig is raised when a line is ready */
int console_init(struct k_poll_signal *sig);

/* The ready line (NUL-terminated), its length, and whether it was cut short */
const char *console_line(size_t *len, bool *overflow);

/* The main thread is done with the line: listen again */
void console_release(void);

#endif
