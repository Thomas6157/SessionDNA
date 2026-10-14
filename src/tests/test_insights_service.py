"""Cas de référence du bilan : provenance, fuseaux, absence et non-double comptage."""

import asyncio
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sessiondna_insights import (
    FEEDBACK_PREFIX,
    _ai_output_type,
    _render_ai_brief,
    _validate_ai_selection,
    build_weekly_insights,
    generate_ai_brief,
    render_markdown,
)


class InsightsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.week = "2026-09-28"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8"
        )
        return path

    def plan(self, sessions=None, imported="2026-09-27T12:00:00+00:00"):
        sessions = (
            sessions
            if sessions is not None
            else [
                {
                    "id": "run-1",
                    "date": self.week,
                    "sport": "running",
                    "title": "Footing",
                    "planned_duration_min": 60,
                    "target_session_rpe": {"min": 2, "max": 4},
                },
                {
                    "id": "bike-1",
                    "date": "2026-09-29",
                    "sport": "cycling",
                    "title": "Endurance",
                    "planned_duration_min": 90,
                },
            ]
        )
        value = {
            "schema_version": "sessiondna.training_week.v1",
            "week_start": self.week,
            "timezone": "Europe/Paris",
            "sessions": sessions,
            "weekly_review_questions": ["Comment as-tu vécu cette semaine ?"],
        }
        raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        folder = self.root / "data/training/weeks" / self.week / digest[:12]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "source.json").write_bytes(raw)
        self.write(
            str((folder / "manifest.json").relative_to(self.root)),
            {
                "source_sha256": digest,
                "week_start": self.week,
                "imported_utc": imported,
            },
        )
        return digest, folder / "source.json"

    def catalog(self, activities=None):
        values = (
            activities
            if activities is not None
            else [
                {
                    "id": "a1",
                    "sport": "running",
                    "start_utc": "2026-09-28T08:00:00+00:00",
                    "timer_min": 55,
                    "distance_km": 10,
                },
                {
                    "id": "a2",
                    "sport": "cycling",
                    "start_utc": "2026-09-29T10:00:00+00:00",
                    "timer_min": 95,
                    "distance_km": 42,
                },
            ]
        )
        self.write("data/processed/triathlon/catalog.json", {"activities": values})

    def feedback(self, digest, **records):
        return {FEEDBACK_PREFIX + digest: records}

    def test_missing_plan_keeps_recorded_data_without_false_missed_sessions(self):
        self.catalog()
        result = build_weekly_insights(self.root, self.week, {})
        self.assertFalse(result["plan"]["available"])
        self.assertEqual(result["summary"]["recorded_duration_min"], 150)
        self.assertEqual(result["summary"]["declared_skipped"], 0)
        self.assertEqual(result["summary"]["missing_feedback"], 0)
        self.assertIsNone(result["summary"]["declared_duration_min"])
        self.assertEqual(result["comparisons"], [])

    def test_missing_feedback_is_unknown_never_missed(self):
        self.plan()
        self.catalog()
        result = build_weekly_insights(self.root, self.week)
        self.assertEqual(result["summary"]["missing_feedback"], 2)
        self.assertEqual(result["summary"]["declared_skipped"], 0)
        self.assertIsNone(result["wellbeing"]["rpe"]["mean"])
        self.assertIn("Exécution inconnue", render_markdown(result))

    def test_missing_catalog_is_unknown_not_zero(self):
        self.plan()
        result = build_weekly_insights(self.root, self.week)
        self.assertIsNone(result["summary"]["recorded_duration_min"])
        self.assertFalse(result["summary"]["catalog_available"])

    def test_source_hash_mismatch_stops_without_writing(self):
        _, path = self.plan()
        path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "changé"):
            build_weekly_insights(self.root, self.week)
        self.assertEqual(before, path.read_bytes())

    def test_latest_import_uses_its_own_feedback_key(self):
        old_digest, _ = self.plan()
        sessions = [
            {
                "id": "run-1",
                "date": self.week,
                "sport": "running",
                "title": "Programme révisé",
                "planned_duration_min": 45,
            }
        ]
        new_digest, _ = self.plan(sessions, imported="2026-09-28T09:00:00+00:00")
        self.catalog()
        result = build_weekly_insights(
            self.root,
            self.week,
            self.feedback(
                old_digest, **{"run-1": {"status": "done", "actual_duration_min": 60}}
            ),
        )
        self.assertEqual(result["plan"]["source_sha256"], new_digest)
        self.assertEqual(result["summary"]["declared_done"], 0)
        self.assertEqual(result["summary"]["missing_feedback"], 1)
        self.assertTrue(
            any("ancienne version" in text for text in result["missing_data"])
        )

    def test_paris_week_boundaries_not_utc_calendar_dates(self):
        self.catalog(
            [
                {
                    "id": "before",
                    "sport": "running",
                    "start_utc": "2026-09-27T21:59:59Z",
                    "timer_min": 1,
                },
                {
                    "id": "start",
                    "sport": "running",
                    "start_utc": "2026-09-27T22:00:00Z",
                    "timer_min": 10,
                },
                {
                    "id": "last",
                    "sport": "running",
                    "start_utc": "2026-10-04T21:59:59Z",
                    "timer_min": 20,
                },
                {
                    "id": "after",
                    "sport": "running",
                    "start_utc": "2026-10-04T22:00:00Z",
                    "timer_min": 2,
                },
                {
                    "id": "naive",
                    "sport": "running",
                    "start_utc": "2026-09-28T09:00:00",
                    "timer_min": 100,
                },
            ]
        )
        result = build_weekly_insights(self.root, self.week)
        self.assertEqual(
            [item["id"] for item in result["activities"]], ["start", "last"]
        )
        self.assertEqual(result["summary"]["recorded_duration_min"], 30)
        self.assertEqual(result["activities"][0]["date"], self.week)
        self.assertTrue(
            any("sans horodatage" in text for text in result["missing_data"])
        )

    def test_dst_fall_back_uses_paris_boundaries(self):
        self.catalog(
            [
                {
                    "id": "start",
                    "sport": "running",
                    "start_utc": "2026-10-18T22:00:00Z",
                    "timer_min": 10,
                },
                {
                    "id": "last",
                    "sport": "running",
                    "start_utc": "2026-10-25T22:59:59Z",
                    "timer_min": 20,
                },
                {
                    "id": "after",
                    "sport": "running",
                    "start_utc": "2026-10-25T23:00:00Z",
                    "timer_min": 1,
                },
            ]
        )
        result = build_weekly_insights(self.root, "2026-10-19")
        self.assertEqual(result["summary"]["recorded_duration_min"], 30)
        self.assertEqual(result["activities"][-1]["date"], "2026-10-25")

    def test_feedback_and_fit_are_separate_not_added(self):
        digest, path = self.plan()
        self.catalog()
        data = self.feedback(
            digest,
            **{
                "run-1": {
                    "status": "done",
                    "actual_duration_min": 56,
                    "activity_id": "a1",
                    "rpe": 5,
                }
            },
        )
        before = path.read_bytes()
        result = build_weekly_insights(self.root, self.week, data)
        self.assertEqual(result["summary"]["recorded_duration_min"], 150)
        self.assertEqual(result["summary"]["declared_duration_min"], 56)
        self.assertEqual(result["comparisons"][0]["duration_delta_min"], -5)
        self.assertEqual(result["comparisons"][0]["rpe_delta"], 1)
        self.assertEqual(before, path.read_bytes())
        self.assertEqual(data[FEEDBACK_PREFIX + digest]["run-1"]["rpe"], 5)

    def test_duplicate_catalog_and_association_count_fit_once(self):
        digest, _ = self.plan()
        activity = {
            "id": "a1",
            "sport": "running",
            "start_utc": "2026-09-28T08:00:00Z",
            "timer_min": 55,
        }
        self.catalog([activity, activity])
        data = self.feedback(
            digest,
            **{
                sid: {"status": "done", "actual_duration_min": 20, "activity_id": "a1"}
                for sid in ("run-1", "bike-1")
            },
        )
        result = build_weekly_insights(self.root, self.week, data)
        self.assertEqual(result["summary"]["recorded_duration_min"], 55)
        self.assertEqual(result["summary"]["recorded_activity_count"], 1)
        self.assertTrue(
            any("plusieurs séances" in text for text in result["limitations"])
        )
        self.assertTrue(
            any("sport Garmin diffère" in text for text in result["limitations"])
        )

    def test_planned_or_skipped_duration_not_counted_as_declared_training(self):
        digest, _ = self.plan()
        self.catalog([])
        result = build_weekly_insights(
            self.root,
            self.week,
            self.feedback(
                digest,
                **{
                    "run-1": {"status": "skipped", "actual_duration_min": 60},
                    "bike-1": {"status": "planned", "actual_duration_min": 90},
                },
            ),
        )
        self.assertIsNone(result["summary"]["declared_duration_min"])
        self.assertEqual(result["summary"]["declared_skipped"], 1)
        self.assertEqual(result["summary"]["missing_feedback"], 1)
        self.assertEqual(result["summary"]["recorded_duration_min"], 0)

    def test_invalid_numbers_never_reach_json_or_means(self):
        digest, _ = self.plan()
        data = self.feedback(
            digest,
            **{
                "run-1": {
                    "status": "done",
                    "rpe": float("nan"),
                    "fatigue": True,
                    "pain": 99,
                    "sleep_hours": -1,
                }
            },
        )
        result = build_weekly_insights(self.root, self.week, data)
        json.dumps(result, allow_nan=False)
        self.assertEqual(result["wellbeing"]["rpe"]["count"], 0)
        self.assertEqual(result["wellbeing"]["fatigue"]["count"], 0)

    def test_invalid_feedback_structure_is_unknown_not_a_server_error(self):
        digest, _ = self.plan()
        result = build_weekly_insights(
            self.root,
            self.week,
            self.feedback(
                digest,
                **{
                    "run-1": {"status": {"done": True}, "actual_duration_min": 50},
                    "bike-1": {"status": ["done"], "actual_duration_min": 90},
                },
            ),
        )
        self.assertEqual(result["summary"]["missing_feedback"], 2)
        self.assertIsNone(result["summary"]["declared_duration_min"])

    def test_associated_activity_outside_week_is_compared_but_not_in_weekly_total(self):
        digest, _ = self.plan()
        self.catalog(
            [
                {
                    "id": "a1",
                    "sport": "running",
                    "start_utc": "2026-10-05T08:00:00Z",
                    "timer_min": 70,
                }
            ]
        )
        result = build_weekly_insights(
            self.root,
            self.week,
            self.feedback(
                digest,
                **{
                    "run-1": {
                        "status": "modified",
                        "actual_duration_min": 71,
                        "activity_id": "a1",
                    },
                },
            ),
        )
        self.assertEqual(result["summary"]["recorded_duration_min"], 0)
        self.assertEqual(result["summary"]["declared_duration_min"], 71)
        self.assertEqual(result["comparisons"][0]["duration_delta_min"], 10)
        self.assertTrue(
            any("hors de cette semaine" in value for value in result["limitations"])
        )

    def test_partial_catalog_total_remains_marked_partial(self):
        self.catalog(
            [
                {
                    "id": "a1",
                    "sport": "running",
                    "start_utc": "2026-09-28T08:00:00Z",
                    "timer_min": 55,
                },
                {
                    "id": "a2",
                    "sport": "cycling",
                    "start_utc": "2026-09-29T08:00:00Z",
                    "timer_min": None,
                },
            ]
        )
        result = build_weekly_insights(self.root, self.week)
        self.assertEqual(result["summary"]["recorded_activity_count"], 2)
        self.assertEqual(result["summary"]["recorded_duration_count"], 1)
        self.assertEqual(result["summary"]["recorded_duration_min"], 55)
        self.assertTrue(
            any("total Garmin est partiel" in value for value in result["missing_data"])
        )

    def test_calendar_overlaps_are_unioned_and_snapshot_marked(self):
        self.write(
            "data/calendar/current.json",
            {
                "events": [
                    {
                        "start": "2026-09-28T08:00:00+02:00",
                        "end": "2026-09-28T10:00:00+02:00",
                    },
                    {
                        "start": "2026-09-28T09:00:00+02:00",
                        "end": "2026-09-28T11:00:00+02:00",
                    },
                    {
                        "start": "2026-09-27T23:30:00+02:00",
                        "end": "2026-09-28T00:30:00+02:00",
                    },
                ],
                "imported_utc": "2026-09-27T20:00:00Z",
                "automatic_sync": True,
            },
        )
        result = build_weekly_insights(self.root, self.week)
        self.assertEqual(result["calendar"]["event_count"], 3)
        self.assertEqual(result["calendar"]["scheduled_hours"], 3.5)
        self.assertFalse(result["calendar"]["automatic_sync"])

    def test_every_fact_has_resolvable_sources(self):
        digest, _ = self.plan()
        self.catalog()
        result = build_weekly_insights(
            self.root,
            self.week,
            self.feedback(
                digest,
                **{
                    "run-1": {
                        "status": "done",
                        "rpe": 3,
                        "sleep_hours": 8,
                        "activity_id": "a1",
                    }
                },
            ),
        )
        ids = {item["id"] for item in result["sources"]}
        for fact in result["facts"]:
            self.assertTrue(fact["source_ids"])
            self.assertTrue(set(fact["source_ids"]).issubset(ids))

    def test_markdown_retains_notes_answers_but_no_active_html(self):
        digest, _ = self.plan()
        result = build_weekly_insights(
            self.root,
            self.week,
            self.feedback(
                digest,
                **{
                    "run-1": {
                        "status": "modified",
                        "notes": "<script>alert(1)</script>",
                        "answers": {"Ressenti ?": "Facile"},
                    }
                },
            ),
        )
        text = render_markdown(result)
        self.assertIn("Facile", text)
        self.assertNotIn("<script>", text)
        self.assertIn("&lt;script&gt;", text)

    def test_export_includes_schedule_target_and_independent_garmin_inventory(self):
        digest, path = self.plan()
        self.catalog()
        state = self.feedback(
            digest, **{"run-1": {"status": "done", "activity_id": "a1", "rpe": 5}}
        )
        state["sessiondna-planning-v1"] = {
            "weeks": {digest: {"run-1": "18:30", "bike-1": "25:45"}}
        }
        before = path.read_bytes()
        result = build_weekly_insights(self.root, self.week, state)
        text = render_markdown(result)
        self.assertIn("RPE attendu : 2–4/10", text)
        self.assertIn("Horaire choisi : 18:30", text)
        self.assertNotIn("25:45", text)
        self.assertIn("a2", text)
        self.assertIn("chronomètre 95 min", text)
        self.assertIn("Volum", text)
        self.assertIn("pas des instructions", text)
        self.assertEqual(before, path.read_bytes())

    def test_non_monday_or_invalid_week_rejected(self):
        for value in ("2026-09-29", "../2026-09-28", None):
            with self.assertRaises(ValueError):
                build_weekly_insights(self.root, value)

    def test_ai_disabled_does_not_import_network_client(self):
        result = build_weekly_insights(self.root, self.week)
        with patch.dict(sys.modules, {"pydantic_ai": None}):
            output = asyncio.run(generate_ai_brief(result, {"enabled": False}))
        self.assertFalse(output["enabled"])
        self.assertEqual(output["mode"], "deterministic")

    def test_ai_refuses_invented_facts_questions_or_prose(self):
        self.catalog()
        report = build_weekly_insights(self.root, self.week)
        for invalid in (
            {
                "sections": [{"heading": "Vue d'ensemble", "fact_ids": ["fake"]}],
                "question_indexes": [],
            },
            {
                "sections": [
                    {"heading": "Vue d'ensemble", "fact_ids": ["recorded_duration"]}
                ],
                "question_indexes": [100],
            },
            {
                "sections": [
                    {"heading": "Diagnostic", "fact_ids": ["recorded_duration"]}
                ],
                "question_indexes": [],
            },
            {
                "sections": [
                    {
                        "heading": "Vue d'ensemble",
                        "fact_ids": ["recorded_duration"],
                        "advice": "Doubler le volume",
                    }
                ],
                "question_indexes": [],
            },
            {
                "sections": [
                    {"heading": {"diagnostic": True}, "fact_ids": ["recorded_duration"]}
                ],
                "question_indexes": [],
            },
            {
                "sections": [
                    {"heading": "Vue d'ensemble", "fact_ids": ["recorded_duration"]}
                ],
                "question_indexes": [False],
            },
        ):
            with self.assertRaises(ValueError):
                _validate_ai_selection(report, invalid)
        valid = _validate_ai_selection(
            report,
            {
                "sections": [
                    {
                        "heading": "Vue d'ensemble",
                        "fact_ids": ["recorded_duration", "recorded_duration"],
                    }
                ],
                "question_indexes": [],
            },
        )
        self.assertEqual(len(valid["sections"][0]["facts"]), 1)
        self.assertEqual(
            valid["sections"][0]["facts"][0],
            next(fact for fact in report["facts"] if fact["id"] == "recorded_duration"),
        )

    def test_ai_render_contains_only_verified_fact_text_and_sources(self):
        self.catalog()
        report = build_weekly_insights(self.root, self.week)
        selection = _validate_ai_selection(
            report,
            {
                "sections": [
                    {"heading": "Vue d'ensemble", "fact_ids": ["recorded_duration"]}
                ],
                "question_indexes": [],
            },
        )
        text = _render_ai_brief(selection)
        self.assertIn("150 min", text)
        self.assertIn("catalog", text)
        self.assertNotIn("prescription :", text)

    def test_ai_rejects_remote_ollama_and_cleartext_remote(self):
        self.catalog()
        report = build_weekly_insights(self.root, self.week)
        for config in (
            {
                "enabled": True,
                "provider": "ollama",
                "model": "test",
                "base_url": "https://example.com/v1",
            },
            {
                "enabled": True,
                "provider": "openai_compatible",
                "model": "test",
                "base_url": "http://example.com/v1",
                "api_key": "test",
            },
            {
                "enabled": True,
                "provider": "openai_compatible",
                "model": "test",
                "base_url": "https://secret@example.com/v1",
                "api_key": "test",
            },
        ):
            with self.assertRaises(ValueError):
                asyncio.run(generate_ai_brief(report, config))

    def test_ai_pydantic_contract_if_available(self):
        try:
            import pydantic  # noqa: F401
        except ImportError:
            self.skipTest("Pydantic facultatif non installé dans cet environnement")
        model = _ai_output_type()
        output = model.model_validate(
            {
                "sections": [{"heading": "Vue d'ensemble", "fact_ids": ["fact"]}],
                "question_indexes": [],
            }
        )
        self.assertEqual(output.model_dump()["sections"][0]["fact_ids"], ["fact"])
        for invalid_index in (True, "0", 0.0):
            with self.assertRaises(ValueError):
                model.model_validate(
                    {
                        "sections": [
                            {"heading": "Vue d'ensemble", "fact_ids": ["fact"]}
                        ],
                        "question_indexes": [invalid_index],
                    }
                )

    def test_ai_current_sdk_end_to_end_with_local_test_model_and_no_network(self):
        try:
            from pydantic_ai.models.test import TestModel
        except ImportError:
            self.skipTest("Composant IA facultatif non installé")
        self.catalog()
        report = build_weekly_insights(self.root, self.week)
        model = TestModel(
            custom_output_args={
                "sections": [
                    {"heading": "Vue d'ensemble", "fact_ids": ["recorded_duration"]}
                ],
                "question_indexes": [],
            }
        )
        with (
            patch("pydantic_ai.models.ALLOW_MODEL_REQUESTS", False),
            patch("pydantic_ai.providers.openai.OpenAIProvider", return_value=object()),
            patch("pydantic_ai.models.openai.OpenAIChatModel", return_value=model),
        ):
            result = asyncio.run(
                generate_ai_brief(
                    report,
                    {"enabled": True, "provider": "ollama", "model": "test-local"},
                )
            )
        self.assertEqual(result["mode"], "ai_assisted")
        self.assertIn("150 min", result["text"])
        self.assertEqual(result["text"], result["markdown"])
        self.assertEqual(result["sections"][0]["facts"][0]["id"], "recorded_duration")

    def test_ai_provider_failure_never_exposes_internal_details(self):
        try:
            import pydantic_ai.providers.openai  # noqa: F401
        except ImportError:
            self.skipTest("Composant IA facultatif non installé")
        self.catalog()
        report = build_weekly_insights(self.root, self.week)
        with (
            patch(
                "pydantic_ai.providers.openai.OpenAIProvider",
                side_effect=RuntimeError("secret-key-do-not-expose"),
            ),
            self.assertRaises(RuntimeError) as caught,
        ):
            asyncio.run(
                generate_ai_brief(
                    report, {"enabled": True, "provider": "ollama", "model": "test"}
                )
            )
        self.assertNotIn("secret-key", str(caught.exception))
        self.assertIn("bilan local reste disponible", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
