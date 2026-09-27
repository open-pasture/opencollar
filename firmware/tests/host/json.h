/*
 * A small JSON reader for the test vector files. Test code only: the
 * firmware never builds a JSON tree (see src/command.c).
 */
#ifndef TEST_JSON_H
#define TEST_JSON_H

#include <stdbool.h>
#include <stddef.h>

enum jtype { J_NULL, J_BOOL, J_NUM, J_STR, J_ARR, J_OBJ };

struct jval {
	enum jtype t;
	bool b;
	double num;
	const char *raw; /* Number: the token as written */
	size_t raw_len;
	char *str; /* String: decoded, NUL-terminated (may contain NULs) */
	size_t str_len;
	struct jval *items; /* Array items or object values */
	char **keys;        /* Object keys */
	size_t n;
};

/* Parse a whole file; exits the test on failure. The text stays in memory. */
struct jval *json_load(const char *path);

const struct jval *jget(const struct jval *obj, const char *key);
const char *jstr(const struct jval *obj, const char *key);
double jnum(const struct jval *obj, const char *key);
bool jbool(const struct jval *obj, const char *key);

#endif
