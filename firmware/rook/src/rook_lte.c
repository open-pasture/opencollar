/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_lte.h"

#include <stdio.h>
#include <string.h>

#include <zephyr/logging/log.h>
#include <zephyr/net/socket.h>
#include <zephyr/net/tls_credentials.h>
#include <zephyr/random/random.h>
#include <modem/lte_lc.h>
#include <nrf_modem_at.h>

#include "rook_backoff.h"
#include "rook_battery.h"
#include "rook_fence.h"
#include "rook_http.h"
#include "rook_queue.h"
#include "rook_report.h"

LOG_MODULE_REGISTER(rook_lte, LOG_LEVEL_INF);

#define BODY_CAP CONFIG_ROOK_LTE_BODY_BYTES
#define RX_CAP (12288 + 1024) /* the largest command plus headers */

static K_MUTEX_DEFINE(lock);
static struct rook_queue queue;           /* under lock */
static uint32_t boundary_version;         /* under lock */
static struct k_poll_signal sig = K_POLL_SIGNAL_INITIALIZER(sig);
static K_SEM_DEFINE(fence_done, 0, 1);

/* Hand-off of one downloaded command to the main thread */
static char rx[RX_CAP];
static const char *fence_wire;
static size_t fence_len;
static struct rook_fence_result fence_res;

static struct rook_url url;
static char token[PROVISION_KEY_MAX + 1];
static char collar_id[PROTO_MAX_ID_BYTES + 1];
static char body[BODY_CAP];
static char head[512];
static struct rook_backoff backoff;

static uint32_t rnd(void *ctx)
{
	(void)ctx;
	return sys_rand32_get();
}

struct k_poll_signal *rook_lte_signal(void)
{
	return &sig;
}

void rook_lte_on_fix(const struct app *a, const struct app_fix_in *in,
		     const struct app_fix_out *out, uint8_t sats)
{
	struct rook_sample s = {0};
	int64_t at;

	if (!in->valid || !app_now(a, k_uptime_get(), &at)) {
		return;
	}
	s.at = at;
	s.lat_e7 = (int32_t)(in->lat * 1e7 + (in->lat < 0 ? -0.5 : 0.5));
	s.lon_e7 = (int32_t)(in->lon * 1e7 + (in->lon < 0 ? -0.5 : 0.5));
	s.accuracy_dm = in->accuracy_m * 10 > 65535 ? 65535 : (uint16_t)(in->accuracy_m * 10);
	s.sats = sats;
	if (out->fenced) {
		s.boundary_version = out->version;
		s.margin_cm = (int32_t)(out->r.margin_m * 100);
		s.fence = out->r.margin_m < 0 ? ROOK_FENCE_OUTSIDE
			  : out->cmd.active ? ROOK_FENCE_WARN : ROOK_FENCE_INSIDE;
	}
	k_mutex_lock(&lock, K_FOREVER);
	boundary_version = out->fenced ? out->version : 0;
	/* Thin the 1 Hz fixes: one sample per sample period */
	{
		const struct rook_sample *last =
			queue.n ? rook_queue_peek(&queue, queue.n - 1) : NULL;

		if (!last || s.at - last->at >= CONFIG_ROOK_LTE_SAMPLE_S ||
		    s.fence != last->fence) {
			rook_queue_push(&queue, &s);
		}
	}
	k_mutex_unlock(&lock);
}

void rook_lte_service(struct app *a)
{
	if (!fence_wire) {
		return;
	}
	fence_res = rook_fence_download(a, fence_wire, fence_len, k_uptime_get());
	fence_wire = NULL;
	k_sem_give(&fence_done);
}

/* ---- One HTTP exchange: connect, send, read all, close ---- */

static int exchange(const char *method, const char *suffix, const char *req_body,
		    size_t body_len, struct rook_http_resp *resp)
{
	struct zsock_addrinfo hints = {.ai_socktype = NET_SOCK_STREAM};
	struct zsock_addrinfo *res = NULL;
	char port[8];
	int fd, n, k, total = 0;
	int hl = rook_http_head(head, sizeof(head), method, &url, suffix, token, body_len);

	if (hl < 0) {
		return -ENOMEM;
	}
	snprintf(port, sizeof(port), "%u", url.port);
	if (zsock_getaddrinfo(url.host, port, &hints, &res) != 0 || !res) {
		return -EHOSTUNREACH;
	}
	fd = zsock_socket(res->ai_family, NET_SOCK_STREAM,
			  url.tls ? NET_IPPROTO_TLS_1_2 : NET_IPPROTO_TCP);
	if (fd < 0) {
		zsock_freeaddrinfo(res);
		return -errno;
	}
	if (url.tls) {
		sec_tag_t tags[] = {CONFIG_ROOK_LTE_SEC_TAG};
		int verify = ZSOCK_TLS_PEER_VERIFY_REQUIRED;

		zsock_setsockopt(fd, ZSOCK_SOL_TLS, ZSOCK_TLS_SEC_TAG_LIST, tags, sizeof(tags));
		zsock_setsockopt(fd, ZSOCK_SOL_TLS, ZSOCK_TLS_HOSTNAME, url.host, strlen(url.host));
		zsock_setsockopt(fd, ZSOCK_SOL_TLS, ZSOCK_TLS_PEER_VERIFY, &verify, sizeof(verify));
	}
	{
		struct zsock_timeval tv = {.tv_sec = 60};

		zsock_setsockopt(fd, ZSOCK_SOL_SOCKET, ZSOCK_SO_RCVTIMEO, &tv, sizeof(tv));
		zsock_setsockopt(fd, ZSOCK_SOL_SOCKET, ZSOCK_SO_SNDTIMEO, &tv, sizeof(tv));
	}
	k = zsock_connect(fd, res->ai_addr, res->ai_addrlen);
	zsock_freeaddrinfo(res);
	if (k < 0) {
		k = -errno;
		goto out;
	}
	if (zsock_send(fd, head, hl, 0) != hl ||
	    (body_len && zsock_send(fd, req_body, body_len, 0) != (ssize_t)body_len)) {
		k = -EIO;
		goto out;
	}
	while (total < (int)sizeof(rx) - 1 &&
	       (n = zsock_recv(fd, rx + total, sizeof(rx) - 1 - total, 0)) > 0) {
		total += n;
	}
	rx[total] = 0;
	k = rook_http_parse(rx, total, resp) == 0 ? 0 : -EBADMSG;
out:
	zsock_close(fd);
	return k;
}

static int status_of(int err, const struct rook_http_resp *r)
{
	return err ? -1 : r->status;
}

/* ---- The cycle ---- */

static int do_report(void)
{
	struct rook_report_info info = {
		.collar_id = collar_id,
		.fw = APP_FW_VERSION,
		.uptime_s = (uint32_t)(k_uptime_get() / 1000),
	};
	struct rook_battery bat;
	struct rook_http_resp r;
	uint16_t n;
	int len, err, st;

	if (rook_battery_read(&bat) == 0) {
		info.has_battery = true;
		info.soc = bat.soc;
		info.battery_v = bat.voltage_v;
		info.has_charging = true;
		info.charging = bat.charging;
	}
	k_mutex_lock(&lock, K_FOREVER);
	info.boundary_version = boundary_version;
	info.dropped = queue.overwritten;
	len = rook_report_encode(&info, &queue, CONFIG_ROOK_LTE_MAX_FIXES, body, sizeof(body), &n);
	k_mutex_unlock(&lock);
	if (len < 0) {
		return -ENOMEM;
	}
	err = exchange("POST", "/report", body, len, &r);
	st = status_of(err, &r);
	LOG_INF("report: %u fixes, %d bytes -> %d", n, len, st);
	switch (rook_http_action(st, 0)) {
	case ROOK_ACT_DONE:
	case ROOK_ACT_DROP:
		k_mutex_lock(&lock, K_FOREVER);
		rook_queue_drop(&queue, n); /* the oldest n are the ones sent */
		k_mutex_unlock(&lock);
		break;
	default:
		break; /* SPLIT: the next cycle sends fewer (MAX_FIXES / body cap) */
	}
	return st;
}

static int post_ack(const struct slot_ack *ack)
{
	struct rook_http_resp r;
	char at[32] = "";
	int len, err;

	if (ack->has_at) {
		proto_time_format(ack->at, at, sizeof(at));
	}
	len = snprintf(body, sizeof(body),
		       "{\"command_id\":\"%s\",\"version\":%u,\"status\":\"%s\"%s%s%s%s%s}",
		       ack->command_id.s, (unsigned)ack->version,
		       ack_status_str((enum ack_status)ack->status),
		       ack->status == ACK_REJECTED ? ",\"code\":\"" : "",
		       ack->status == ACK_REJECTED ? reject_str((enum reject_code)ack->code) : "",
		       ack->status == ACK_REJECTED ? "\"" : "", ack->has_at ? ",\"at\":\"" : "",
		       ack->has_at ? at : "");
	if (ack->has_at && len < (int)sizeof(body) - 2) {
		body[len - 1] = '"';
		body[len++] = '}';
		body[len] = 0;
	}
	err = exchange("POST", "/ack", body, len, &r);
	return status_of(err, &r);
}

static int do_boundary(void)
{
	struct rook_http_resp r;
	char q[48];
	uint32_t have;
	int err, st;

	k_mutex_lock(&lock, K_FOREVER);
	have = MAX(boundary_version, rook_fence_seq());
	k_mutex_unlock(&lock);
	snprintf(q, sizeof(q), "/boundary?have=%u", (unsigned)have);
	err = exchange("GET", q, NULL, 0, &r);
	st = status_of(err, &r);
	if (st != 200 || r.body_len == 0) {
		return st;
	}
	/* Verify on the main thread; wait for it */
	fence_len = r.body_len;
	fence_wire = r.body;
	k_poll_signal_raise(&sig, 1);
	k_sem_take(&fence_done, K_FOREVER);
	LOG_INF("boundary: code %s, seq %u%s", reject_str(fence_res.code),
		(unsigned)fence_res.ack.version, fence_res.handed_on ? ", to LoRa" : "");
	if (fence_res.has_ack) {
		LOG_INF("ack -> %d", post_ack(&fence_res.ack));
	}
	return st;
}

static int lte_up(void)
{
	int err;

	if (strlen(CONFIG_ROOK_LTE_APN)) {
		/* Default PDN context; must be set while offline */
		lte_lc_func_mode_set(LTE_LC_FUNC_MODE_DEACTIVATE_LTE);
		err = nrf_modem_at_printf("AT+CGDCONT=0,\"IP\",\"%s\"", CONFIG_ROOK_LTE_APN);
		if (err) {
			LOG_WRN("APN set failed: %d", err);
		}
	}
	if (IS_ENABLED(CONFIG_ROOK_LTE_PSM)) {
		lte_lc_psm_req(true);
	}
	LOG_INF("LTE-M: attaching");
	err = lte_lc_connect(); /* blocks until registered or the lte_lc timeout */
	if (err) {
		LOG_WRN("LTE-M attach failed: %d", err);
		return err;
	}
	/* GNSS keeps running: system mode is LTE-M + GPS (main.c) */
	LOG_INF("LTE-M: registered");
	return 0;
}

static void thread_fn(void *p1, void *p2, void *p3)
{
	(void)p1, (void)p2, (void)p3;
	bool attached = false;

	rook_backoff_init(&backoff, rnd, NULL);
	for (;;) {
		uint32_t wait_s = CONFIG_ROOK_LTE_REPORT_S;
		int st;

		if (!attached) {
			attached = lte_up() == 0;
			if (!attached) {
				k_sleep(K_SECONDS(rook_backoff_delay(&backoff, -1, -1)));
				continue;
			}
		}
		st = do_report();
		if (rook_http_action(st, 0) == ROOK_ACT_DONE) {
			st = do_boundary();
		}
		if (st == 200 || st == 204) {
			rook_backoff_reset(&backoff);
		} else {
			wait_s = rook_backoff_delay(&backoff, st, -1);
			if (wait_s == 0) {
				wait_s = CONFIG_ROOK_LTE_REPORT_S;
			}
			LOG_WRN("cycle failed (%d), next in %u s", st, wait_s);
		}
		k_sleep(K_SECONDS(wait_s));
	}
}

K_THREAD_STACK_DEFINE(rook_stack, CONFIG_ROOK_LTE_STACK_SIZE);
static struct k_thread rook_thread;

int rook_lte_start(const struct app *a)
{
	const char *ep = strlen(CONFIG_ROOK_LTE_BASE_URL) ? CONFIG_ROOK_LTE_BASE_URL
							   : a->prov.endpoint;
	const char *tok = strlen(CONFIG_ROOK_LTE_AUTH_TOKEN) ? CONFIG_ROOK_LTE_AUTH_TOKEN
							     : a->prov.key;

	if (!a->prov.ok && !strlen(CONFIG_ROOK_LTE_BASE_URL)) {
		LOG_WRN("Not provisioned: no endpoint, LTE reporter off");
		return -ENOENT;
	}
	if (rook_url_parse(ep, IS_ENABLED(CONFIG_ROOK_LTE_ALLOW_HTTP), &url) != 0) {
		LOG_ERR("Bad endpoint: %s", ep);
		return -EINVAL;
	}
	strncpy(token, tok, sizeof(token) - 1);
	strncpy(collar_id, a->prov.ok ? a->prov.collar_id.s : "unprovisioned",
		sizeof(collar_id) - 1);
	rook_queue_init(&queue);
	rook_battery_init();
	k_thread_create(&rook_thread, rook_stack, K_THREAD_STACK_SIZEOF(rook_stack), thread_fn,
			NULL, NULL, NULL, K_PRIO_PREEMPT(8), 0, K_NO_WAIT);
	k_thread_name_set(&rook_thread, "rook_lte");
	LOG_INF("LTE reporter: %s://%s:%u%s", url.tls ? "https" : "http", url.host, url.port,
		url.path);
	return 0;
}
