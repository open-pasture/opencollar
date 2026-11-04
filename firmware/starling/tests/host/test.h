/* SPDX-License-Identifier: Apache-2.0 */
#ifndef STARLING_TEST_H
#define STARLING_TEST_H

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

__attribute__((unused)) static int failures;

#define CHECK(cond)                                                                    \
	do {                                                                           \
		if (!(cond)) {                                                         \
			printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);         \
			failures++;                                                    \
		}                                                                      \
	} while (0)

#define CHECK_NEAR(a, b, tol) CHECK(fabs((a) - (b)) <= (tol))

static inline int test_done(const char *suite)
{
	if (failures) {
		printf("%s: %d failure(s)\n", suite, failures);
		return EXIT_FAILURE;
	}
	printf("%s: all tests passed\n", suite);
	return EXIT_SUCCESS;
}

#endif
