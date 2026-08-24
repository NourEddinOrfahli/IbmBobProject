"""
Runtime validation script for TASK 2 - Pro Max Daily Automation.

DO NOT modify any production code.

Usage:
    cd backend
    ..\.venv\Scripts\python.exe ..\validate_scheduler_runtime.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import time

# ---------------------------------------------------------------------------
# Env vars - set BEFORE any backend module is imported
# ---------------------------------------------------------------------------

_TMP_STORE = os.path.join(tempfile.gettempdir(), "space_interpreter_validation_store.json")
if os.path.exists(_TMP_STORE):
    os.remove(_TMP_STORE)

os.environ["DAILY_BULLETIN_ENABLED"]  = "true"
os.environ["DAILY_BULLETIN_HOUR"]     = "7"
os.environ["DAILY_BULLETIN_MINUTE"]   = "0"
os.environ["DAILY_BULLETIN_TIMEZONE"] = "UTC"
os.environ["BULLETIN_STORE_PATH"]     = _TMP_STORE

SAFE_ENV_VARS = {
    "DAILY_BULLETIN_ENABLED":  os.environ["DAILY_BULLETIN_ENABLED"],
    "DAILY_BULLETIN_HOUR":     os.environ["DAILY_BULLETIN_HOUR"],
    "DAILY_BULLETIN_MINUTE":   os.environ["DAILY_BULLETIN_MINUTE"],
    "DAILY_BULLETIN_TIMEZONE": os.environ["DAILY_BULLETIN_TIMEZONE"],
    "BULLETIN_STORE_PATH":     os.environ["BULLETIN_STORE_PATH"],
}

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_here    = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.join(_here, "backend")
if _backend not in sys.path:
    sys.path.insert(0, _backend)

# ---------------------------------------------------------------------------
# Reload config so it picks up the new env vars
# ---------------------------------------------------------------------------

import importlib
import config as _config_module
importlib.reload(_config_module)

import main as main_module
importlib.reload(main_module)

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SEP = "-" * 70


def step(n, title):
    print("\n" + SEP)
    print("  STEP %d: %s" % (n, title))
    print(SEP)


def check(label, condition, detail=""):
    icon = "[PASS]" if condition else "[FAIL]"
    print("  %s  %s" % (icon, label))
    if detail:
        print("         %s" % detail)
    if not condition:
        print("\n" + "=" * 70)
        print("  VALIDATION FAILED - stopping.")
        print("=" * 70)
        sys.exit(1)


def pp(obj):
    return json.dumps(obj, indent=4, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------

print("\n" + "=" * 70)
print("  SPACE INTERPRETER - Scheduler Runtime Validation")
print("=" * 70)

print("\n[ENV] Environment variables used (secrets excluded):")
for k, v in SAFE_ENV_VARS.items():
    print("     %s=%s" % (k, v))

client = TestClient(main_module.app, raise_server_exceptions=False)
client.__enter__()

# ---------------------------------------------------------------------------
# STEP 1 - status BEFORE trigger
# ---------------------------------------------------------------------------

step(1, "GET /api/daily-news/status  BEFORE trigger")

r = client.get("/api/daily-news/status")
check("HTTP 200", r.status_code == 200, "got %d" % r.status_code)
body_before = r.json()
print("\n  Full response (BEFORE trigger):")
print(pp(body_before))

sched_before = body_before["data"]["scheduler"]
check("success==true in body",          body_before.get("success") is True)
check("scheduler key present",          "scheduler" in body_before["data"])
check("latest_bulletin key present",    "latest_bulletin" in body_before["data"])
check("scheduler.enabled == true",      sched_before["enabled"] is True,
      "got: %s" % sched_before["enabled"])
check("last_run is null (not yet run)", sched_before["last_run"] is None,
      "got: %s" % sched_before["last_run"])
check("latest_bulletin is null",        body_before["data"]["latest_bulletin"] is None)

# ---------------------------------------------------------------------------
# STEP 2 - trigger_now()
# ---------------------------------------------------------------------------

step(2, "Trigger scheduler job immediately via trigger_now()")

scheduler_instance = main_module._scheduler
check("Scheduler instance is set", scheduler_instance is not None)

print("  Calling trigger_now() ...")
t0 = time.monotonic()
asyncio.run(scheduler_instance.trigger_now())
elapsed = time.monotonic() - t0
print("  trigger_now() completed in %.2fs" % elapsed)

# ---------------------------------------------------------------------------
# STEP 3 - in-memory scheduler status
# ---------------------------------------------------------------------------

step(3, "Verify in-memory scheduler status after trigger")

s = scheduler_instance.status
print("  last_run      : %s" % s.last_run)
print("  last_success  : %s" % s.last_success)
print("  last_apod_date: %s" % s.last_apod_date)
print("  last_status   : %s" % s.last_status)

check("last_run is populated",         s.last_run is not None)
check("last_status == 'success'",      s.last_status == "success",
      "got: %s" % s.last_status)
check("last_success is populated",     s.last_success is not None)
check("last_apod_date is populated",   s.last_apod_date is not None,
      "got: %s" % s.last_apod_date)

# ---------------------------------------------------------------------------
# STEP 4 - BulletinStore persistence
# ---------------------------------------------------------------------------

step(4, "Verify BulletinStore persistence")

check("bulletin_store.json was created", os.path.exists(_TMP_STORE),
      "expected at: %s" % _TMP_STORE)

with open(_TMP_STORE, "r", encoding="utf-8") as fh:
    store_raw = json.load(fh)

# Print with story redacted for readability
display = json.loads(json.dumps(store_raw))
if display.get("latest") and isinstance(display["latest"].get("story"), dict):
    display["latest"]["story"] = {"<redacted>": "..."}
for date_key in list(display.get("records", {}).keys()):
    rec = display["records"][date_key]
    if isinstance(rec.get("story"), dict):
        rec["story"] = {"<redacted>": "..."}
print("\n  bulletin_store.json (story fields redacted):")
print(pp(display))

check("latest record exists",         store_raw.get("latest") is not None)
check("latest.status == 'success'",   store_raw["latest"]["status"] == "success",
      "got: %s" % store_raw["latest"].get("status"))
check("latest.apod_date is set",      bool(store_raw["latest"].get("apod_date")),
      "got: %s" % store_raw["latest"].get("apod_date"))
check("latest.generated_at is set",   bool(store_raw["latest"].get("generated_at")))
check("latest.story is a dict",       isinstance(store_raw["latest"].get("story"), dict))
check("story has language field",     "language" in store_raw["latest"]["story"])
check("story has source_data",        "source_data" in store_raw["latest"]["story"])

sd = store_raw["latest"]["story"]["source_data"]
check("source_data.source == 'NASA APOD'",
      sd.get("source") == "NASA APOD", "got: %s" % sd)

recorded_apod_date = store_raw["latest"]["apod_date"]
print("\n  Recorded APOD date: %s" % recorded_apod_date)
check("apod_date matches scheduler.last_apod_date",
      recorded_apod_date == s.last_apod_date,
      "store=%s  scheduler=%s" % (recorded_apod_date, s.last_apod_date))

# ---------------------------------------------------------------------------
# STEP 5 - status AFTER trigger
# ---------------------------------------------------------------------------

step(5, "GET /api/daily-news/status  AFTER trigger")

r2 = client.get("/api/daily-news/status")
check("HTTP 200", r2.status_code == 200, "got %d" % r2.status_code)
body_after = r2.json()
print("\n  Full response (AFTER trigger):")
print(pp(body_after))

sched_after = body_after["data"]["scheduler"]
lb_after    = body_after["data"]["latest_bulletin"]

check("scheduler.enabled == true",          sched_after["enabled"] is True)
check("scheduler.status == 'success'",      sched_after["status"] == "success",
      "got: %s" % sched_after["status"])
check("scheduler.last_run is populated",    sched_after["last_run"] is not None)
check("scheduler.last_success is populated",sched_after["last_success"] is not None)
check("scheduler.apod_date is populated",   sched_after["apod_date"] is not None)
check("latest_bulletin is NOT null",        lb_after is not None)
check("latest_bulletin.status == 'success'",lb_after["status"] == "success",
      "got: %s" % lb_after["status"])
check("latest_bulletin.apod_date matches",  lb_after["apod_date"] == recorded_apod_date,
      "got: %s" % lb_after["apod_date"])
check("latest_bulletin.generated_at is set",bool(lb_after.get("generated_at")))

# ---------------------------------------------------------------------------
# STEP 6 - Idempotency
# ---------------------------------------------------------------------------

step(6, "Idempotency - trigger again for the same APOD date")

records_before = len(store_raw.get("records", {}))
print("  Records in store before 2nd trigger: %d" % records_before)
print("  Triggering again for APOD date %s ..." % recorded_apod_date)

asyncio.run(scheduler_instance.trigger_now())

with open(_TMP_STORE, "r", encoding="utf-8") as fh:
    store_after_retry = json.load(fh)

records_after = len(store_after_retry.get("records", {}))
print("  Records in store after 2nd trigger:  %d" % records_after)

check("No new records added (idempotency)",
      records_after == records_before,
      "before=%d  after=%d" % (records_before, records_after))

check("Scheduler status == 'skipped' after 2nd trigger",
      scheduler_instance.status.last_status == "skipped",
      "got: %s" % scheduler_instance.status.last_status)

print("\n  Idempotency confirmed - second trigger for APOD date %s" % recorded_apod_date)
print("  was correctly SKIPPED. No duplicate bulletin generated.")

# ---------------------------------------------------------------------------
# STEP 7 - No API key in response
# ---------------------------------------------------------------------------

step(7, "Security - no API key in status response")

status_text = json.dumps(body_after)
check("No 'sk-' in status response",        "sk-" not in status_text)
check("No 'Bearer' in status response",     "Bearer" not in status_text)
check("No 'api_key' in status response",    "api_key" not in status_text.lower())
check("No 'Authorization' in response",     "Authorization" not in status_text)

# ---------------------------------------------------------------------------
# Teardown
# ---------------------------------------------------------------------------

client.__exit__(None, None, None)

if os.path.exists(_TMP_STORE):
    os.remove(_TMP_STORE)
    print("\n  Cleaned up temp store: %s" % _TMP_STORE)

# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 70)
print("  ALL VALIDATION STEPS PASSED")
print("=" * 70)

print("\n  Environment variables used (secrets excluded):")
for k, v in SAFE_ENV_VARS.items():
    print("    %s=%s" % (k, v))

print("""
  Results:
    scheduler.enabled         : %s
    scheduler.status          : %s
    scheduler.last_run        : %s
    scheduler.last_success    : %s
    scheduler.apod_date       : %s
    latest_bulletin.status    : %s
    latest_bulletin.apod_date : %s
    latest_bulletin.generated : %s
    idempotency               : CONFIRMED (2nd trigger -> 'skipped')
    api key in response       : NOT PRESENT
""" % (
    sched_after["enabled"],
    sched_after["status"],
    sched_after["last_run"],
    sched_after["last_success"],
    sched_after["apod_date"],
    lb_after["status"],
    lb_after["apod_date"],
    lb_after["generated_at"],
))
