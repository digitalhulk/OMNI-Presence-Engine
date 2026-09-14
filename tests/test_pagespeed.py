from ope.integrations.pagespeed import PageSpeedClient, PageSpeedConfig, PageSpeedError, extract_vitals, fetch_vitals


def test_missing_api_key_short_circuits_without_network(monkeypatch):
    monkeypatch.delenv("OPE_PAGESPEED_API_KEY", raising=False)
    assert PageSpeedConfig.from_env().api_key == ""
    assert fetch_vitals("https://example.com") is None


def test_extract_vitals_reads_lab_metrics_and_missing_field_data():
    payload = {
        "lighthouseResult": {
            "audits": {
                "first-contentful-paint": {"numericValue": 1200.5},
                "largest-contentful-paint": {"numericValue": 2100.0},
                "cumulative-layout-shift": {"numericValue": 0.05},
                "total-blocking-time": {"numericValue": 90.0},
            }
        },
        "loadingExperience": {},
    }
    vitals = extract_vitals(payload)
    assert vitals == {"fcp_ms": 1200.5, "lcp_ms": 2100.0, "cls": 0.05, "tbt_ms": 90.0, "inp_ms": None}


def test_extract_vitals_reads_inp_field_data_when_present():
    payload = {
        "lighthouseResult": {"audits": {}},
        "loadingExperience": {"metrics": {"INTERACTION_TO_NEXT_PAINT": {"percentile": 180}}},
    }
    assert extract_vitals(payload)["inp_ms"] == 180.0


def test_extract_vitals_never_guesses_on_malformed_payload():
    assert extract_vitals({}) == {"fcp_ms": None, "lcp_ms": None, "cls": None, "tbt_ms": None, "inp_ms": None}
    assert extract_vitals({"lighthouseResult": None})["lcp_ms"] is None


class _FailingClient:
    config = PageSpeedConfig(api_key="test-key")

    def fetch(self, url, *, strategy="mobile"):
        raise PageSpeedError("boom")


def test_fetch_vitals_returns_none_on_client_failure_not_a_guess():
    assert fetch_vitals("https://example.com", _FailingClient()) is None


class _WorkingClient:
    config = PageSpeedConfig(api_key="test-key")

    def fetch(self, url, *, strategy="mobile"):
        assert url == "https://example.com"
        return {"lighthouseResult": {"audits": {"largest-contentful-paint": {"numericValue": 1800.0}}}}


def test_fetch_vitals_returns_extracted_metrics_when_configured():
    vitals = fetch_vitals("https://example.com", _WorkingClient())
    assert vitals["lcp_ms"] == 1800.0
