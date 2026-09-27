#include "console.h"

#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>

static const struct device *const uart = DEVICE_DT_GET(DT_CHOSEN(zephyr_console));

static char line[CONSOLE_LINE_MAX + 1];
static size_t len;
static bool overflow;
static atomic_t ready;
static struct k_poll_signal *signal;

static void isr(const struct device *dev, void *user_data)
{
	uint8_t buf[16];

	ARG_UNUSED(user_data);

	while (uart_irq_update(dev) > 0 && uart_irq_rx_ready(dev) > 0) {
		int n = uart_fifo_read(dev, buf, sizeof(buf));

		for (int i = 0; i < n; i++) {
			uint8_t c = buf[i];

			if (atomic_get(&ready)) {
				continue; /* The last line is still being handled */
			}
			if (c == '\r' || c == '\n') {
				if (len == 0 && !overflow) {
					continue; /* The LF of a CRLF, or an empty line */
				}
				line[len] = '\0';
				atomic_set(&ready, 1);
				k_poll_signal_raise(signal, 0);
			} else if (c == 0x08 || c == 0x7f) {
				if (len > 0) {
					len--; /* Backspace, for people typing */
				}
			} else if (len < CONSOLE_LINE_MAX) {
				line[len++] = (char)c;
			} else {
				overflow = true;
			}
		}
	}
}

int console_init(struct k_poll_signal *sig)
{
	uint8_t c;
	int err;

	if (!device_is_ready(uart)) {
		return -ENODEV;
	}
	signal = sig;
	uart_irq_rx_disable(uart);
	err = uart_irq_callback_user_data_set(uart, isr, NULL);
	if (err) {
		return err;
	}
	while (uart_poll_in(uart, &c) == 0) {
		/* Drain what arrived before we listened */
	}
	uart_irq_rx_enable(uart);
	return 0;
}

const char *console_line(size_t *out_len, bool *out_overflow)
{
	if (!atomic_get(&ready)) {
		return NULL;
	}
	*out_len = len;
	*out_overflow = overflow;
	return line;
}

void console_release(void)
{
	len = 0;
	overflow = false;
	atomic_set(&ready, 0);
}
