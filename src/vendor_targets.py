"""Vendors in scope and the URLs we scrape for each."""

VENDORS = {
    "datadog": {
        "name": "Datadog",
        "g2": "https://www.g2.com/products/datadog/reviews",
        "pricing": "https://www.datadoghq.com/pricing/",
        "status": "https://status.datadoghq.com/",
        "homepage": "https://www.datadoghq.com/",
    },
    "newrelic": {
        "name": "New Relic",
        "g2": "https://www.g2.com/products/new-relic/reviews",
        "pricing": "https://newrelic.com/pricing",
        "status": "https://status.newrelic.com/",
        "homepage": "https://newrelic.com/",
    },
    "honeycomb": {
        "name": "Honeycomb",
        "g2": "https://www.g2.com/products/honeycomb-io/reviews",
        "pricing": "https://www.honeycomb.io/pricing",
        "status": "https://status.honeycomb.io/",
        "homepage": "https://www.honeycomb.io/",
    },
    "grafana": {
        "name": "Grafana Cloud",
        "g2": "https://www.g2.com/products/grafana-cloud/reviews",
        "pricing": "https://grafana.com/pricing/",
        "status": "https://status.grafana.com/",
        "homepage": "https://grafana.com/products/cloud/",
    },
    "splunk": {
        "name": "Splunk",
        "g2": "https://www.g2.com/products/splunk-enterprise/reviews",
        "pricing": "https://www.splunk.com/en_us/products/pricing.html",
        "status": "https://status.splunk.com/",
        "homepage": "https://www.splunk.com/",
    },
}
