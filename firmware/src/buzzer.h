/* SparkFun Qwiic Buzzer (BOB-24474) over I2C. */
#ifndef OPENCOLLAR_BUZZER_H
#define OPENCOLLAR_BUZZER_H

#include <stdint.h>

/* Returns 0 if the buzzer answered with the expected ID. */
int buzzer_init(void);

/* volume 0-4; duration_ms 0 means play until buzzer_stop(). */
int buzzer_play(uint16_t freq_hz, uint8_t volume, uint16_t duration_ms);

int buzzer_stop(void);

#endif
