from ope import history


def _result(run_id="ope-1", ttfb=100.0, weight=200_000, words=800, findings=("F-1",)):
    return {
        "run_id": run_id,
        "target": "https://example.com",
        "final_url": "https://example.com",
        "inventory": {"ttfb_ms": ttfb, "page_weight_bytes": weight, "word_count": words},
        "findings": [{"id": fid} for fid in findings],
        "checks": {"03-code.head_metadata": {"status": "PASS"}},
    }


def test_saved_run_is_reloadable_and_scoped_to_its_target(tmp_path):
    assert history.save_run(_result(), tmp_path) is not None
    runs = history.load_runs("https://example.com", tmp_path)
    assert len(runs) == 1
    assert runs[0]["run_id"] == "ope-1"
    assert runs[0]["metrics"] == {"ttfb_ms": 100.0, "page_weight_bytes": 200_000.0, "word_count": 800.0}
    assert runs[0]["finding_ids"] == ["F-1"]
    assert history.load_runs("https://other.example", tmp_path) == []


def test_load_runs_returns_newest_first(tmp_path):
    history.save_run(_result(run_id="ope-1"), tmp_path)
    history.save_run(_result(run_id="ope-2"), tmp_path)
    assert [run["run_id"] for run in history.load_runs("https://example.com", tmp_path)] == ["ope-2", "ope-1"]


def test_compare_reports_metric_regressions_in_both_directions():
    baseline = history.snapshot(_result(ttfb=100.0, weight=200_000, words=800))
    worse = history.compare({"ttfb_ms": 900.0, "page_weight_bytes": 900_000, "word_count": 100}, [], baseline)
    assert {item["metric"] for item in worse["metric_regressions"]} == {"ttfb_ms", "page_weight_bytes", "word_count"}


def test_compare_ignores_jitter_below_the_absolute_floor():
    baseline = history.snapshot(_result(ttfb=100.0, weight=200_000, words=800))
    steady = history.compare({"ttfb_ms": 120.0, "page_weight_bytes": 210_000, "word_count": 790}, [], baseline)
    assert steady["metric_regressions"] == []


def test_compare_tracks_new_and_resolved_findings():
    baseline = history.snapshot(_result(findings=("F-1", "F-2")))
    diff = history.compare({}, [{"id": "F-2"}, {"id": "F-3"}], baseline)
    assert diff["new_findings"] == ["F-3"]
    assert diff["resolved_findings"] == ["F-1"]


def test_attach_baseline_marks_a_first_run_as_having_no_comparison(tmp_path):
    result = history.attach_baseline(_result(), tmp_path)
    attached = result["inventory"]["history"]
    assert attached["runs_recorded"] == 0
    assert attached["baseline_run_id"] is None
    assert attached["metric_regressions"] is None
    assert attached["store_writable"] is True


def test_attach_baseline_compares_against_the_previous_run(tmp_path):
    history.save_run(_result(run_id="ope-1", ttfb=100.0), tmp_path)
    result = history.attach_baseline(_result(run_id="ope-2", ttfb=1200.0, findings=("F-1", "F-9")), tmp_path)
    attached = result["inventory"]["history"]
    assert attached["runs_recorded"] == 1
    assert attached["baseline_run_id"] == "ope-1"
    assert [item["metric"] for item in attached["metric_regressions"]] == ["ttfb_ms"]
    assert attached["new_findings"] == ["F-9"]


def test_save_run_returns_none_when_the_store_is_not_writable(tmp_path):
    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory", encoding="utf-8")
    assert history.save_run(_result(), blocked) is None
