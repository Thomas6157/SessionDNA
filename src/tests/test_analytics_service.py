"""Behavioural checks using temporary data only; never touch the athlete files."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sessiondna_analytics import AnalyticsService, FEATURE_LABELS


def has(module):
    return importlib.util.find_spec(module) is not None


class FakeMessage:
    def __init__(self, name, **values):
        self.name, self.values = name, values

    def get_value(self, field, fallback=None):
        return self.values.get(field, fallback)


def fake_fit_module(messages):
    class Reader:
        def __init__(self, path):
            pass

        def __enter__(self):
            return iter(messages)

        def __exit__(self, *args):
            pass

    return types.SimpleNamespace(FitReader=Reader, FitDataMessage=FakeMessage)


class AnalyticsFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.catalog_dir = self.root / "data/processed/triathlon"
        self.catalog_dir.mkdir(parents=True)
        (self.root / "data/raw").mkdir(parents=True)
        self.service = AnalyticsService(self.root)
        self.start = pd.Timestamp("2026-09-27T22:30:00Z")  # Monday in Paris
        self.activity = self.row("a_s1", "running", 120)
        self.catalog = {"activities": [self.activity], "profiles": {}}
        self.save()
        (self.root / "data/raw/a.fit").write_bytes(b"test data, not a real fit")

    def tearDown(self):
        self.temp.cleanup()

    def row(self, id, sport, seconds):
        return {"id": id, "filename": "a.fit", "session_index": 1, "sport": sport,
                "start_utc": self.start.isoformat(), "end_utc": (self.start + pd.Timedelta(seconds=seconds)).isoformat(),
                "timer_min": seconds / 60, "elapsed_min": seconds / 60, "distance_km": 1.2,
                "status": "ok", "hr_session_mean": 130, "power_session_mean": 200}

    def save(self):
        self.service.catalog_path.write_text(json.dumps(self.catalog), encoding="utf-8")

    def prepare_model(self):
        import joblib
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.impute import SimpleImputer
        from sklearn.pipeline import make_pipeline

        self.service.dataset_dir.mkdir(parents=True)
        self.service.model_dir.mkdir(parents=True)
        rng = np.random.default_rng(17)
        matrix = rng.normal(size=(36, 6))
        matrix[31, 1] = np.nan
        frame = pd.DataFrame(matrix, columns=list(FEATURE_LABELS))
        frame["filename"] = [f"f{i}.fit" for i in range(36)]
        frame.loc[31, "filename"] = "a.fit"
        frame["split"] = ["train"] * 30 + ["test"] * 6
        frame["fit_sha256"] = hashlib.sha256((self.root / "data/raw/a.fit").read_bytes()).hexdigest()
        dataset_path = self.service.dataset_dir / "dataset.csv"
        frame.to_csv(dataset_path, index=False)
        sha = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
        labels = np.array(["ef", "endurance_soutenue", "seuil"] * 12)
        model = make_pipeline(SimpleImputer(strategy="median"), RandomForestClassifier(n_estimators=12, max_depth=4, random_state=42, n_jobs=1))
        model.fit(frame.loc[:29, list(FEATURE_LABELS)], labels[:30])
        joblib.dump({"model": model, "features": list(FEATURE_LABELS), "dataset_id": "fixture"}, self.service.model_dir / "model.joblib")
        (self.service.model_dir / "metrics.json").write_text(json.dumps({"dataset_sha256": sha, "train_n": 30, "test_n": 6, "chosen": "foret", "metrics": {"accuracy": 0.5, "macro avg": {"f1-score": 0.4}}}), encoding="utf-8")
        (self.service.dataset_dir / "manifest.json").write_text(json.dumps({"dataset_id": "fixture", "dataset_sha256": sha}), encoding="utf-8")

    @unittest.skipUnless(has("duckdb"), "DuckDB optional dependency")
    def test_week_boundary_missing_totals_and_parquet_round_trip(self):
        other = self.row("b_s1", "swimming", 240)
        other.update(distance_km=None, timer_min=None)
        self.catalog["activities"].append(other)
        self.save()
        result = self.service.overview()
        self.assertEqual(result["counts"], {"activities": 2, "running": 1, "swimming": 1})
        self.assertEqual(result["missing"], {"duration": 1, "distance": 1, "date": 0})
        self.assertEqual(result["totals"]["duration_min"], 2)
        self.assertEqual(result["totals"]["distance_km"], 1.2)
        self.assertEqual({week["week"] for week in result["weekly"]}, {"2026-09-28"})
        export = self.service.export_parquet()
        import duckdb
        with duckdb.connect(":memory:") as connection:
            actual = connection.execute("SELECT id, distance_km FROM read_parquet(?) ORDER BY id", [export["path"]]).fetchall()
        self.assertEqual(actual, [("a_s1", 1.2), ("b_s1", None)])
        with self.assertRaises(ValueError):
            self.service.export_parquet(self.root / "data/raw/overwrite.parquet")

    @unittest.skipUnless(has("duckdb"), "DuckDB optional dependency")
    def test_empty_catalog_is_not_an_error(self):
        self.catalog["activities"] = []
        self.save()
        result = self.service.overview()
        self.assertEqual(result["counts"], {"activities": 0})
        self.assertEqual(result["weekly"], [])
        self.assertIsNone(result["totals"]["distance_km"])

    def test_unavailable_dependency_is_explicit(self):
        with patch("sessiondna_analytics.importlib.import_module", side_effect=ImportError("missing")):
            result = self.service.overview()
            self.assertEqual(result["status"], "unavailable")
            self.assertEqual(result["totals"], {})

    def test_lookup_and_raw_path_are_confined(self):
        with self.assertRaises(ValueError):
            self.service.analyze("' OR 1=1; --")
        with self.assertRaises(ValueError):
            self.service._fit_path({"filename": "../secret.fit"})
        self.catalog["activities"].append(dict(self.activity))
        self.save()
        with self.assertRaises(ValueError):
            self.service._catalog()

    @unittest.skipUnless(has("ruptures"), "ruptures optional dependency")
    def test_segments_detect_change_without_bridging_pause_or_missing_bin(self):
        self.activity.update(end_utc=(self.start + pd.Timedelta(seconds=1200)).isoformat(), elapsed_min=20)
        self.catalog["profiles"]["a_s1"] = [[i / 4, 10.0 if i < 32 else 16.0, 140, 200, 80] for i in range(80)]
        self.catalog["profiles"]["a_s1"][10][1] = None
        self.save()
        events = [(self.start + pd.Timedelta(seconds=660), "stop_all"), (self.start + pd.Timedelta(seconds=720), "start")]
        with patch.object(self.service, "_fit_data", return_value=([], events)):
            result = self.service.segments("a_s1")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(any(abs(item["end_min"] - 8) < 0.3 for item in result["items"]))
        self.assertFalse(any(item["start_min"] < 12 and item["end_min"] > 11 for item in result["items"]))
        self.assertFalse(any(item["start_min"] < 2.75 and item["end_min"] > 2.5 for item in result["items"]))
        self.assertEqual(result["pauses"], [{"start_min": 11, "end_min": 12}])

    @unittest.skipUnless(has("ruptures"), "ruptures optional dependency")
    def test_segments_refuse_to_guess_timer_pauses(self):
        self.catalog["profiles"]["a_s1"] = [[0, 10, 130, 200, 70]]
        self.save()
        with patch.object(self.service, "_fit_data", side_effect=OSError("missing")):
            result = self.service.segments("a_s1")
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["items"], [])

    @unittest.skipUnless(has("ruptures"), "ruptures optional dependency")
    def test_partial_recording_gap_is_not_hidden_by_profile_means(self):
        self.catalog["profiles"]["a_s1"] = [[i / 4, 10, 130, 200, 70] for i in range(8)]
        self.save()
        stamps = [0, 1, 2, 40, 41, 42, 57, 72, 87, 102, 117]
        records = [(self.start + pd.Timedelta(seconds=i), None, None) for i in stamps]
        with patch.object(self.service, "_fit_data", return_value=(records, [])):
            result = self.service.segments("a_s1")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["recording_gaps"]), 1)
        self.assertTrue(all(item["start_min"] >= 0.75 for item in result["items"]))

    @unittest.skipUnless(has("shap"), "SHAP optional dependency")
    def test_shap_uses_frozen_preprocessing_and_reconstructs_prediction(self):
        from sklearn.pipeline import Pipeline
        self.prepare_model()
        model_path = self.service.model_dir / "model.joblib"
        before = model_path.read_bytes()
        with patch.object(Pipeline, "fit", side_effect=AssertionError("No fitting during explanation")):
            result = self.service.explanation("a_s1")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["split"], "test")
        probability = result["probabilities"][result["predicted_objective"]]
        self.assertAlmostEqual(result["baseline_probability"] + sum(row["contribution"] for row in result["contributions"]), probability, places=6)
        self.assertTrue(next(row for row in result["contributions"] if row["feature"] == "speed_mean")["imputed"])
        self.assertEqual(before, model_path.read_bytes())
        (self.service.dataset_dir / "dataset.csv").write_text("tampered\n", encoding="utf-8")
        self.assertEqual(self.service.explanation("a_s1")["status"], "unavailable")

    @unittest.skipUnless(has("shap"), "SHAP optional dependency")
    def test_explanation_rejects_changed_fit_and_unseen_activity(self):
        self.prepare_model()
        (self.root / "data/raw/a.fit").write_bytes(b"modified")
        self.assertEqual(self.service.explanation("a_s1")["status"], "unavailable")
        self.activity["filename"] = "unseen.fit"
        self.save()
        self.assertEqual(self.service.explanation("a_s1")["status"], "out_of_scope")

    def test_no_running_explanation_for_other_sports(self):
        self.activity["sport"] = "cycling"
        self.save()
        self.assertEqual(self.service.explanation("a_s1")["status"], "out_of_scope")

    def test_route_preserves_gaps_pauses_and_geojson_axis_order(self):
        semicircle = 2**31 / 180
        points = [(self.start + pd.Timedelta(seconds=second), 48 * semicircle, (2 + second / 10000) * semicircle) for second in [0, 1, 2, 30, 31, 32, 40, 41, 50, 51]]
        events = [(self.start + pd.Timedelta(seconds=35), "stop"), (self.start + pd.Timedelta(seconds=45), "start")]
        with patch.object(self.service, "_fit_data", return_value=(points, events)):
            result = self.service.route("a_s1")
        self.assertEqual(len(result["features"]), 3)
        self.assertEqual([len(item["geometry"]["coordinates"]) for item in result["features"]], [3, 3, 2])
        self.assertAlmostEqual(result["features"][0]["geometry"]["coordinates"][0][0], 2)
        self.assertAlmostEqual(result["features"][0]["geometry"]["coordinates"][0][1], 48)
        json.dumps(result, allow_nan=False)

    def test_route_never_joins_across_invalid_coordinates(self):
        points = [(self.start + pd.Timedelta(seconds=i), 500000000 if i != 2 else None, 25000000) for i in range(5)]
        with patch.object(self.service, "_fit_data", return_value=(points, [])):
            result = self.service.route("a_s1")
        self.assertEqual(len(result["features"]), 2)

    def test_fit_reader_selects_only_requested_multisport_session(self):
        second = self.row("a_s2", "cycling", 150)
        second.update(session_index=2, start_utc=(self.start + pd.Timedelta(seconds=100)).isoformat())
        self.catalog["activities"].append(second)
        self.save()
        messages = [FakeMessage("record", timestamp=self.start + pd.Timedelta(seconds=i), position_lat=500000000, position_long=25000000) for i in [-1, 0, 99, 100, 101, 121]]
        with patch.dict(sys.modules, {"fitdecode": fake_fit_module(messages)}):
            points, _ = self.service._fit_data(self.activity, positions=True)
        self.assertEqual([(item[0] - self.start).total_seconds() for item in points], [0, 99])

    @unittest.skipUnless(has("mlflow"), "MLflow optional dependency")
    def test_local_mlflow_register_is_idempotent_and_does_not_fit(self):
        self.prepare_model()
        model = self.service.model_dir / "model.joblib"
        before = model.read_bytes()

        def register_in_process():
            # MLflow retains SQLite pools for the process lifetime. A child
            # process exercises the real CLI lifecycle, releases Windows file
            # handles normally, and tests persistence across separate launches.
            # Do not reach into MLflow's private engine cache or force deletion.
            code = ("import json, sys; from pathlib import Path; "
                    "sys.path.insert(0, sys.argv[1]); "
                    "from sessiondna_analytics import AnalyticsService; "
                    "print(json.dumps(AnalyticsService(Path(sys.argv[2])).register_model()))")
            result = subprocess.run(
                [sys.executable, "-c", code, str(Path(__file__).resolve().parents[1]), str(self.root)],
                check=True, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
            return json.loads(result.stdout.strip().splitlines()[-1])

        first = register_in_process()
        second = register_in_process()
        self.assertEqual(first["status"], "ok")
        self.assertFalse(first["existing"])
        self.assertTrue(second["existing"])
        self.assertEqual(first["run_id"], second["run_id"])
        self.assertEqual(before, model.read_bytes())
        self.assertTrue(first["tracking_uri"].startswith("sqlite:///"))
        (self.service.dataset_dir / "dataset.csv").write_text("tampered\n", encoding="utf-8")
        refused = register_in_process()
        self.assertEqual(refused["status"], "unavailable")

    @unittest.skipUnless(has("duckdb"), "DuckDB optional dependency")
    def test_cli_build_produces_strict_json_and_preserves_sources(self):
        from build_analytics import build_analytics
        before = self.service.catalog_path.read_bytes()
        result = build_analytics(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["source_files_unchanged"])
        self.assertEqual(before, self.service.catalog_path.read_bytes())
        self.assertEqual(result["model_registry"]["status"], "not_requested")
        manifest = json.loads((self.service.export_dir / "build_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["parquet"]["rows"], 1)
        self.assertIn("data/processed/triathlon/catalog.json", manifest["source_sha256"])
        self.assertTrue((self.service.export_dir / "report.md").is_file())


if __name__ == "__main__":
    unittest.main()
