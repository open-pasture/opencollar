#include "json.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct p {
	const char *s;
	size_t i, n;
};

static void fail(const struct p *p, const char *what)
{
	fprintf(stderr, "json: %s at byte %zu\n", what, p->i);
	exit(2);
}

static void ws(struct p *p)
{
	while (p->i < p->n && strchr(" \t\r\n", p->s[p->i])) {
		p->i++;
	}
}

static unsigned hex4(const char *s)
{
	unsigned v = 0;

	for (int k = 0; k < 4; k++) {
		char c = s[k];

		v = v * 16 + (unsigned)(c <= '9' ? c - '0' : (c | 0x20) - 'a' + 10);
	}
	return v;
}

static void utf8(char *out, size_t *n, unsigned cp)
{
	if (cp < 0x80) {
		out[(*n)++] = (char)cp;
	} else if (cp < 0x800) {
		out[(*n)++] = (char)(0xc0 | cp >> 6);
		out[(*n)++] = (char)(0x80 | (cp & 0x3f));
	} else if (cp < 0x10000) {
		out[(*n)++] = (char)(0xe0 | cp >> 12);
		out[(*n)++] = (char)(0x80 | ((cp >> 6) & 0x3f));
		out[(*n)++] = (char)(0x80 | (cp & 0x3f));
	} else {
		out[(*n)++] = (char)(0xf0 | cp >> 18);
		out[(*n)++] = (char)(0x80 | ((cp >> 12) & 0x3f));
		out[(*n)++] = (char)(0x80 | ((cp >> 6) & 0x3f));
		out[(*n)++] = (char)(0x80 | (cp & 0x3f));
	}
}

static char *string(struct p *p, size_t *len)
{
	size_t start = ++p->i, n = 0;
	char *out;

	while (p->i < p->n && p->s[p->i] != '"') {
		p->i += p->s[p->i] == '\\' ? 2 : 1;
	}
	out = malloc(p->i - start + 1);
	for (size_t i = start; i < p->i; i++) {
		char c = p->s[i];

		if (c != '\\') {
			out[n++] = c;
			continue;
		}
		c = p->s[++i];
		switch (c) {
		case 'n':
			out[n++] = '\n';
			break;
		case 't':
			out[n++] = '\t';
			break;
		case 'r':
			out[n++] = '\r';
			break;
		case 'b':
			out[n++] = '\b';
			break;
		case 'f':
			out[n++] = '\f';
			break;
		case 'u': {
			unsigned cp = hex4(p->s + i + 1);

			i += 4;
			if (cp >= 0xd800 && cp < 0xdc00 && p->s[i + 1] == '\\' && p->s[i + 2] == 'u') {
				cp = 0x10000 + ((cp - 0xd800) << 10) + (hex4(p->s + i + 3) - 0xdc00);
				i += 6;
			}
			utf8(out, &n, cp);
			break;
		}
		default:
			out[n++] = c;
		}
	}
	out[n] = '\0';
	p->i++;
	*len = n;
	return out;
}

static void value(struct p *p, struct jval *v);

static void container(struct p *p, struct jval *v, char close)
{
	size_t cap = 8;

	v->items = malloc(cap * sizeof(*v->items));
	if (close == '}') {
		v->keys = malloc(cap * sizeof(*v->keys));
	}
	p->i++;
	ws(p);
	if (p->s[p->i] == close) {
		p->i++;
		return;
	}
	for (;;) {
		if (v->n == cap) {
			cap *= 2;
			v->items = realloc(v->items, cap * sizeof(*v->items));
			if (close == '}') {
				v->keys = realloc(v->keys, cap * sizeof(*v->keys));
			}
		}
		ws(p);
		if (close == '}') {
			size_t kl;

			if (p->s[p->i] != '"') {
				fail(p, "key expected");
			}
			v->keys[v->n] = string(p, &kl);
			ws(p);
			if (p->s[p->i++] != ':') {
				fail(p, "':' expected");
			}
		}
		value(p, &v->items[v->n++]);
		ws(p);
		if (p->s[p->i] == ',') {
			p->i++;
		} else if (p->s[p->i] == close) {
			p->i++;
			return;
		} else {
			fail(p, "',' expected");
		}
	}
}

static void value(struct p *p, struct jval *v)
{
	memset(v, 0, sizeof(*v));
	ws(p);
	switch (p->s[p->i]) {
	case '{':
		v->t = J_OBJ;
		container(p, v, '}');
		break;
	case '[':
		v->t = J_ARR;
		container(p, v, ']');
		break;
	case '"':
		v->t = J_STR;
		v->str = string(p, &v->str_len);
		break;
	case 't':
		v->t = J_BOOL;
		v->b = true;
		p->i += 4;
		break;
	case 'f':
		v->t = J_BOOL;
		p->i += 5;
		break;
	case 'n':
		v->t = J_NULL;
		p->i += 4;
		break;
	default: {
		char *end;

		v->t = J_NUM;
		v->raw = p->s + p->i;
		v->num = strtod(v->raw, &end);
		if (end == v->raw) {
			fail(p, "value expected");
		}
		v->raw_len = (size_t)(end - v->raw);
		p->i += v->raw_len;
	}
	}
}

struct jval *json_load(const char *path)
{
	FILE *f = fopen(path, "rb");
	struct p p = {0};
	struct jval *v = malloc(sizeof(*v));
	char *text;
	long n;

	if (!f) {
		fprintf(stderr, "json: cannot open %s\n", path);
		exit(2);
	}
	fseek(f, 0, SEEK_END);
	n = ftell(f);
	fseek(f, 0, SEEK_SET);
	text = malloc((size_t)n + 1);
	if (fread(text, 1, (size_t)n, f) != (size_t)n) {
		fprintf(stderr, "json: cannot read %s\n", path);
		exit(2);
	}
	text[n] = '\0';
	fclose(f);
	p.s = text;
	p.n = (size_t)n;
	value(&p, v);
	return v;
}

const struct jval *jget(const struct jval *obj, const char *key)
{
	if (!obj || obj->t != J_OBJ) {
		return NULL;
	}
	for (size_t i = 0; i < obj->n; i++) {
		if (strcmp(obj->keys[i], key) == 0) {
			return &obj->items[i];
		}
	}
	return NULL;
}

const char *jstr(const struct jval *obj, const char *key)
{
	const struct jval *v = jget(obj, key);

	return v && v->t == J_STR ? v->str : NULL;
}

double jnum(const struct jval *obj, const char *key)
{
	const struct jval *v = jget(obj, key);

	return v && v->t == J_NUM ? v->num : 0.0;
}

bool jbool(const struct jval *obj, const char *key)
{
	const struct jval *v = jget(obj, key);

	return v && v->t == J_BOOL && v->b;
}
