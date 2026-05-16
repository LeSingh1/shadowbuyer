"""Actionbook Quote Hunter — fills vendor 'Contact Sales' forms.

Safety rail: NEVER submits. We fill, capture filled state, then mock the
AE response so downstream agents (Negotiator) have something to work with.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
ACTIONBOOK_API_KEY = os.getenv("ACTIONBOOK_API_KEY", "")
ACTIONBOOK_BASE_URL = os.getenv("ACTIONBOOK_BASE_URL", "https://api.actionbook.ai")

TEST_PROFILE = {
    "first_name": "Alex",
    "last_name": "Rivers",
    "email": "alex.rivers+shadowbuyer@example.com",
    "company": "Shadowbuyer Inc",
    "job_title": "VP Engineering",
    "phone": "+1-415-555-0142",
    "company_size": "201-500",
    "country": "United States",
    "use_case": "Evaluating observability tools to replace incumbent.",
}


def _mock_ae_response(vendor: str) -> dict[str, Any]:
    """Mock AE response — exactly the shape the brief mandates for Datadog."""
    catalog = {
        "Datadog": {
            "vendor": "Datadog",
            "ae_email": "ae@datadog.com",
            "first_quote": "$2,300/host/year",
            "discount_offered": "10% Annual",
            "competitor_dig": "We're more reliable than New Relic during incidents.",
        },
        "New Relic": {
            "vendor": "New Relic",
            "ae_email": "ae@newrelic.com",
            "first_quote": "$0.30/GB ingest, $99/user/mo",
            "discount_offered": "15% if committed by EOQ",
            "competitor_dig": "Datadog will nickel-and-dime you on every custom metric.",
        },
        "Honeycomb": {
            "vendor": "Honeycomb",
            "ae_email": "ae@honeycomb.io",
            "first_quote": "$130/mo Pro + usage",
            "discount_offered": "20% startup credit, 6 months",
            "competitor_dig": "Splunk costs 10x for half the cardinality.",
        },
        "Grafana Cloud": {
            "vendor": "Grafana Cloud",
            "ae_email": "ae@grafana.com",
            "first_quote": "$8/active series, Pro tier",
            "discount_offered": "Free tier extension + 12% Annual",
            "competitor_dig": "You don't get locked in like with Datadog's proprietary agent.",
        },
        "Splunk": {
            "vendor": "Splunk",
            "ae_email": "ae@splunk.com",
            "first_quote": "$1,800/GB/day ingest baseline",
            "discount_offered": "Volume tier kicks in at 100GB",
            "competitor_dig": "Grafana is a hobby toy — we power Fortune 50 SOCs.",
        },
    }
    return catalog.get(vendor, {
        "vendor": vendor,
        "ae_email": f"ae@{vendor.lower().replace(' ', '')}.com",
        "first_quote": "TBD",
        "discount_offered": "TBD",
        "competitor_dig": "TBD",
    })


def hunt_quote(vendor_name: str, contact_form_url: str) -> dict[str, Any]:
    """Fill the contact form via Actionbook, capture state, mock AE reply.

    Returns a single record persisted to fixtures/quote_<slug>.json.
    """
    slug = vendor_name.lower().replace(" ", "_")
    record: dict[str, Any] = {
        "vendor": vendor_name,
        "form_url": contact_form_url,
        "test_profile": TEST_PROFILE,
        "actionbook_run": None,
        "screenshot_path": None,
        "submitted": False,           # safety rail: ALWAYS False
        "ae_response": _mock_ae_response(vendor_name),
    }

    if ACTIONBOOK_API_KEY:
        try:
            payload = {
                "url": contact_form_url,
                "task": (
                    f"Fill the Contact Sales form with: "
                    f"first_name={TEST_PROFILE['first_name']}, "
                    f"last_name={TEST_PROFILE['last_name']}, "
                    f"email={TEST_PROFILE['email']}, "
                    f"company={TEST_PROFILE['company']}, "
                    f"job_title={TEST_PROFILE['job_title']}, "
                    f"phone={TEST_PROFILE['phone']}, "
                    f"company_size={TEST_PROFILE['company_size']}, "
                    f"country={TEST_PROFILE['country']}, "
                    f"use_case='{TEST_PROFILE['use_case']}'. "
                    "DO NOT click submit. Take a screenshot of the filled form."
                ),
                "capture_screenshot": True,
                "stop_before_submit": True,
            }
            r = requests.post(
                f"{ACTIONBOOK_BASE_URL}/v1/run",
                headers={"Authorization": f"Bearer {ACTIONBOOK_API_KEY}"},
                json=payload,
                timeout=120,
            )
            r.raise_for_status()
            run = r.json()
            record["actionbook_run"] = {
                "run_id": run.get("run_id"),
                "status": run.get("status"),
                "filled_fields": run.get("filled_fields"),
            }
            shot = run.get("screenshot_base64")
            if shot:
                path = FIXTURES / f"quote_{slug}_screenshot.png"
                path.write_bytes(base64.b64decode(shot))
                record["screenshot_path"] = str(path.name)
        except Exception as exc:  # noqa: BLE001
            record["actionbook_error"] = f"{type(exc).__name__}: {exc}"

    (FIXTURES / f"quote_{slug}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return record


if __name__ == "__main__":
    out = hunt_quote("Datadog", "https://www.datadoghq.com/contact-sales/")
    print(json.dumps(out, indent=2))
