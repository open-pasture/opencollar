/* Shared by the host tests. Run them all: make -C firmware/tests/host */
#ifndef TEST_H
#define TEST_H

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

/* A labelled check for table-driven tests */
#define CHECK_CASE(cond, name, ...)                                                    \
	do {                                                                           \
		if (!(cond)) {                                                         \
			printf("FAIL %s:%d: %s: ", __FILE__, __LINE__, (name));        \
			printf(__VA_ARGS__);                                           \
			printf("\n");                                                  \
			failures++;                                                    \
		}                                                                      \
	} while (0)

static inline int test_done(const char *suite)
{
	if (failures) {
		printf("%s: %d failure(s)\n", suite, failures);
		return EXIT_FAILURE;
	}
	printf("%s: all tests passed\n", suite);
	return EXIT_SUCCESS;
}

#ifndef VECTORS
#define VECTORS "vectors"
#endif

#endif
