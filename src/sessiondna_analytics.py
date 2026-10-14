"""Read-only sports analytics; derived exports never replace source data or models.

All signals use elapsed time. Missing samples and explicit FIT timer pauses split
analysis blocks. A statistical change point is not a training prescription.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import math
import threading
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


FEATURE_LABELS = {
    "timer_min": "Durée chronométrée (min)",
    "speed_mean": "Vitesse moyenne (km/h)",
    "speed_cv": "Variabilité relative de la vitesse",
    "speed_late_early_ratio": "Rapport vitesse fin / début",
    "hr_mean": "Fréquence cardiaque moyenne (bpm)",
    "hr_std": "Variabilité de la fréquence cardiaque (bpm)",
}
SEGMENT_LIMITATIONS = [
    "Découpage statistique exploratoire, pas une reconnaissance validée des blocs d'entraînement.",
    "Moyennes par fenêtres de 15 secondes ; les changements plus courts peuvent être invisibles.",
    "Temps écoulé : pauses de montre, fenêtres sans valeur et trous d'enregistrement de plus de 15 s séparent les blocs ; aucune récupération n'est déduite.",
]
MODEL_LIMITATIONS = [
    "Modèle exploratoire existant : seulement EF, endurance soutenue et seuil.",
    "Une contribution SHAP explique le calcul du modèle, pas une cause physiologique.",
    "Ces probabilités ne sont pas une confiance calibrée ; elles ne valident pas le type de séance.",
    "Les données ont déjà été explorées ; le petit test existant n'est pas prospectif.",
]


def _number(value: Any) -> float | None:
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _stamp(value: Any) -> pd.Timestamp:
    result = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(result):
        raise ValueError("Horodatage manquant ou invalide.")
    return result


def _unavailable(message: str, **extra: Any) -> dict:
    return {"status": "unavailable", "message": message, **extra}


class AnalyticsService:
    """Fixed-query analytics over the existing immutable data products.

    Optional dependencies are loaded lazily so missing extras cannot prevent the
    planner from starting. No network calls, fitting, label edits or Garmin sync.
    """

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.catalog_path = self.root / "data/processed/triathlon/catalog.json"
        self.model_dir = self.root / "data/processed/sport_model"
        self.dataset_dir = self.root / "data/processed/supervised"
        self.export_dir = self.root / "data/processed/analytics"
        self._lock = threading.RLock()
        self._catalog_key = None
        self._catalog_value = None

    def _catalog(self) -> dict:
        info = self.catalog_path.stat()
        key = (info.st_mtime_ns, info.st_size)
        with self._lock:
            if key != self._catalog_key:
                value = json.loads(self.catalog_path.read_text(encoding="utf-8-sig"))
                if not isinstance(value.get("activities"), list):
                    raise ValueError("Catalogue multisport invalide.")
                ids = [row.get("id") for row in value["activities"]]
                if len(ids) != len(set(ids)) or any(not isinstance(x, str) for x in ids):
                    raise ValueError("Identifiants du catalogue invalides ou dupliqués.")
                self._catalog_value, self._catalog_key = value, key
            return self._catalog_value

    def _activity(self, activity_id: str) -> dict:
        # IDs are looked up; they are never interpolated into SQL or file names.
        for activity in self._catalog()["activities"]:
            if activity["id"] == activity_id:
                return activity
        raise ValueError("Séance inconnue.")

    def _table(self) -> pd.DataFrame:
        columns = ["id", "filename", "sport", "start_utc", "timer_min", "elapsed_min", "distance_km", "hr_session_mean", "power_session_mean", "status"]
        frame = pd.DataFrame(self._catalog()["activities"]).reindex(columns=columns)
        frame["start_utc"] = pd.to_datetime(frame.start_utc, utc=True, errors="coerce")
        local = frame.start_utc.dt.tz_convert("Europe/Paris")
        frame["week"] = (local - pd.to_timedelta(local.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
        for field in ["timer_min", "elapsed_min", "distance_km", "hr_session_mean", "power_session_mean"]:
            frame[field] = pd.to_numeric(frame[field], errors="coerce")
            frame[field] = frame[field].where(np.isfinite(frame[field]) & frame[field].ge(0))
        frame["sport"] = frame.sport.fillna("unknown").astype(str)
        return frame

    def overview(self) -> dict:
        """Weekly aggregation with DuckDB; incomplete totals are explicitly marked."""
        try:
            duckdb = importlib.import_module("duckdb")
        except ImportError:
            return _unavailable("DuckDB n'est pas installé ; les totaux analytiques ne sont pas calculés.", counts={}, weekly=[], totals={})
        frame = self._table()
        with duckdb.connect(":memory:") as connection:
            connection.register("sessions", frame)
            counts = dict(connection.execute("SELECT sport, count(*) FROM sessions GROUP BY sport ORDER BY sport").fetchall())
            row = connection.execute("SELECT count(*), sum(timer_min), sum(distance_km), count(*) FILTER (WHERE timer_min IS NULL), count(*) FILTER (WHERE distance_km IS NULL), count(*) FILTER (WHERE start_utc IS NULL) FROM sessions").fetchone()
            result = connection.execute("SELECT week, sport, count(*) AS sessions, sum(timer_min) AS timer_min, sum(distance_km) AS distance_km, count(*) FILTER (WHERE timer_min IS NULL) AS missing_duration, count(*) FILTER (WHERE distance_km IS NULL) AS missing_distance FROM sessions WHERE week IS NOT NULL GROUP BY week, sport ORDER BY week, sport")
            names = [column[0] for column in result.description]
            weekly = [dict(zip(names, values, strict=True)) for values in result.fetchall()]
        for week in weekly:
            week["duration_hours"] = week["timer_min"] / 60 if week["timer_min"] is not None else None
        return {
            "status": "ok", "engine": "DuckDB", "generated_utc": datetime.now(timezone.utc).isoformat(),
            "counts": {"activities": row[0], **counts}, "weekly": weekly,
            "totals": {"duration_min": row[1], "duration_hours": row[1] / 60 if row[1] is not None else None, "distance_km": row[2]},
            "missing": {"duration": row[3], "distance": row[4], "date": row[5]},
            "limitations": ["Semaines civiles Europe/Paris. Sommes des valeurs présentes, durées chronométrées officielles FIT.", "Les sports ont des distances et sollicitations différentes : leur total ne mesure pas la charge physiologique."],
        }

    def _fit_path(self, activity: dict) -> Path:
        filename = activity.get("filename", "")
        if not filename or Path(filename).name != filename or Path(filename).suffix.lower() != ".fit":
            raise ValueError("Nom de fichier FIT invalide.")
        directory = (self.root / "data/raw").resolve()
        path = (directory / filename).resolve()
        if path.parent != directory:
            raise ValueError("Le fichier FIT doit rester dans data/raw.")
        return path

    def _fit_data(self, activity: dict, positions: bool = False) -> tuple[list, list]:
        """Return only records inside the requested FIT session, plus timer events."""
        fitdecode = importlib.import_module("fitdecode")
        start, end = _stamp(activity["start_utc"]), _stamp(activity["end_utc"])
        next_starts = [_stamp(other["start_utc"]) for other in self._catalog()["activities"]
                       if other.get("filename") == activity["filename"] and int(other.get("session_index", 1)) > int(activity.get("session_index", 1))]
        next_start = min(next_starts) if next_starts else None
        points, events = [], []
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with fitdecode.FitReader(self._fit_path(activity)) as stream:
                for message in stream:
                    if not isinstance(message, fitdecode.FitDataMessage):
                        continue
                    if message.name == "event" and message.get_value("event", fallback=None) == "timer":
                        stamp = pd.to_datetime(message.get_value("timestamp", fallback=None), utc=True, errors="coerce")
                        if pd.notna(stamp) and stamp <= end:
                            events.append((stamp, str(message.get_value("event_type", fallback=""))))
                    elif message.name == "record":
                        stamp = pd.to_datetime(message.get_value("timestamp", fallback=None), utc=True, errors="coerce")
                        if pd.isna(stamp) or stamp < start or stamp > end or (next_start is not None and stamp >= next_start):
                            continue
                        lat = _number(message.get_value("position_lat", fallback=None)) if positions else None
                        lon = _number(message.get_value("position_long", fallback=None)) if positions else None
                        points.append((stamp, lat, lon))
        return points, sorted(events, key=lambda item: item[0])

    @staticmethod
    def _pause_intervals(events: list, start: pd.Timestamp, end: pd.Timestamp) -> list[tuple[float, float]]:
        stopped = None
        intervals = []
        for stamp, kind in events:
            if stamp > end:
                break
            if kind in {"stop", "stop_all", "stop_disable", "stop_disable_all"}:
                if stopped is None:
                    stopped = stamp
            elif kind == "start" and stopped is not None:
                if stamp > start:
                    intervals.append((max(0.0, (stopped - start).total_seconds()), min((end - start).total_seconds(), (stamp - start).total_seconds())))
                stopped = None
        if stopped is not None and stopped < end:
            intervals.append((max(0.0, (stopped - start).total_seconds()), (end - start).total_seconds()))
        return [(a, b) for a, b in intervals if b > a]

    def segments(self, activity_id: str) -> dict:
        activity = self._activity(activity_id)
        empty = {"items": [], "limitations": SEGMENT_LIMITATIONS.copy()}
        try:
            ruptures = importlib.import_module("ruptures")
        except ImportError:
            return _unavailable("ruptures n'est pas installé.", **empty)
        profile = self._catalog().get("profiles", {}).get(activity_id, [])
        if not profile:
            return {"status": "no_data", **empty}
        # The recorded profile schema is [elapsed minutes, km/h, bpm, W, cadence].
        valid = [point for point in profile if isinstance(point, list) and len(point) >= 4 and _number(point[0]) is not None]
        power_count = sum(_number(point[3]) is not None for point in valid)
        field = 3 if activity.get("sport") == "cycling" and power_count >= 0.75 * len(valid) else 1
        signal, unit = ("power", "W") if field == 3 else ("speed", "km/h")
        try:
            records, events = self._fit_data(activity)
            pauses = self._pause_intervals(events, _stamp(activity["start_utc"]), _stamp(activity["end_utc"]))
        except (OSError, ValueError, ImportError) as exc:
            # A segmentation without timer evidence would silently bridge pauses.
            return _unavailable(f"Lecture des pauses FIT impossible ({type(exc).__name__}).", **empty)
        elapsed = float(activity["elapsed_min"]) * 60
        start = _stamp(activity["start_utc"])
        # A mean in a 15-second bin can conceal a long partial recording gap.
        # Consult original timestamps too, without inventing one-Hz sampling.
        recording_gaps = [((previous[0] - start).total_seconds(), (current[0] - start).total_seconds())
                          for previous, current in zip(records, records[1:])
                          if (current[0] - previous[0]).total_seconds() > 15]
        blocks, current = [], []
        missing_bins = 0
        for point in valid:
            left = float(point[0]) * 60
            right = min(left + 15.0, elapsed)
            value = _number(point[field])
            crosses_pause = any(left < stop and right > pause for pause, stop in pauses)
            crosses_gap = any(left < end_gap and right > start_gap for start_gap, end_gap in recording_gaps)
            if value is None or value < 0 or crosses_pause or crosses_gap or right <= 0 or left >= elapsed:
                missing_bins += 1
                if current:
                    blocks.append(current)
                    current = []
                continue
            if current and (left <= current[-1][0] or left - current[-1][0] > 22.5):
                blocks.append(current)
                current = []
            current.append((max(0.0, left), right, value))
        if current:
            blocks.append(current)
        items = []
        for block_index, block in enumerate(blocks):
            values = np.array([point[2] for point in block], dtype=float)
            # Unit variance gives the penalty the same meaning across sports.
            # IQR scaling would suppress even a noiseless two-level change in
            # short blocks because its residual cost can fall below 3*ln(n).
            scale = max(float(np.std(values)), 1e-6)
            normalized = ((values - np.median(values)) / scale).reshape(-1, 1)
            ends = [len(block)]
            if len(block) >= 8 and np.ptp(values) > 1e-6:
                ends = ruptures.Pelt(model="l2", min_size=4, jump=1).fit(normalized).predict(pen=3 * math.log(len(block)))
            previous = 0
            for boundary in ends:
                segment = block[previous:boundary]
                if not segment:
                    continue
                begin, finish = segment[0][0] / 60, segment[-1][1] / 60
                items.append({"start_min": begin, "end_min": finish, "duration_min": finish - begin,
                              "mean_value": float(np.mean([item[2] for item in segment])), "n_points": len(segment), "block_index": block_index})
                previous = boundary
        return {"status": "ok" if items else "no_data", "method": "ruptures PELT (L2)", "signal": signal, "unit": unit,
                "items": items, "pauses": [{"start_min": a / 60, "end_min": b / 60} for a, b in pauses],
                "recording_gaps": [{"start_min": a / 60, "end_min": b / 60} for a, b in recording_gaps],
                "excluded_bins": missing_bins, "parameters": {"minimum_samples": 4, "bin_seconds": 15, "penalty": "3 × ln(n), signal centré et réduit par bloc"},
                "limitations": SEGMENT_LIMITATIONS.copy()}

    def explanation(self, activity_id: str) -> dict:
        activity = self._activity(activity_id)
        limitations = MODEL_LIMITATIONS.copy()
        if activity.get("sport") != "running" or int(activity.get("session_index", 1)) != 1:
            return {"status": "out_of_scope", "message": "Le modèle existant concerne uniquement les courses de son jeu de données d'origine.", "limitations": limitations}
        required = [self.model_dir / "model.joblib", self.model_dir / "metrics.json", self.dataset_dir / "dataset.csv", self.dataset_dir / "manifest.json"]
        if any(not path.is_file() for path in required):
            return _unavailable("Modèle gelé ou jeu de données d'origine absent.", limitations=limitations)
        metrics = json.loads(required[1].read_text(encoding="utf-8-sig"))
        manifest = json.loads(required[3].read_text(encoding="utf-8-sig"))
        digest = hashlib.sha256(required[2].read_bytes()).hexdigest()
        if digest != metrics.get("dataset_sha256") or digest != manifest.get("dataset_sha256"):
            return _unavailable("Le jeu de données a changé depuis l'apprentissage ; explication refusée.", limitations=limitations)
        frame = pd.read_csv(required[2])
        if not set(FEATURE_LABELS).union({"filename", "fit_sha256", "split"}).issubset(frame.columns):
            return _unavailable("Variables ou provenance manquantes dans le jeu de données.", limitations=limitations)
        selected = frame.loc[frame.filename.eq(activity["filename"])]
        if len(selected) != 1:
            return {"status": "out_of_scope", "message": "Séance absente du jeu de données d'origine ; aucune variable n'est reconstruite avec une autre méthode.", "limitations": limitations}
        row = selected.iloc[0]
        fit_path = self._fit_path(activity)
        if not fit_path.is_file() or hashlib.sha256(fit_path.read_bytes()).hexdigest() != row.get("fit_sha256"):
            return _unavailable("Le FIT d'origine est absent ou modifié ; association au modèle refusée.", limitations=limitations)
        try:
            shap = importlib.import_module("shap")
            joblib = importlib.import_module("joblib")
        except ImportError:
            return _unavailable("SHAP et ses dépendances sont nécessaires pour expliquer le modèle.", limitations=limitations)
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.impute import SimpleImputer
        from sklearn.pipeline import Pipeline

        # Only the project's already trusted, local artifact is loaded. Never load
        # a user-uploaded pickle/joblib. This method performs no fitting.
        artifact = joblib.load(required[0])
        model, features = artifact.get("model"), artifact.get("features")
        if artifact.get("dataset_id") != manifest.get("dataset_id") or features != list(FEATURE_LABELS):
            return _unavailable("Contrat de variables du modèle différent ; explication non compatible.", limitations=limitations)
        if not isinstance(model, Pipeline) or len(model.steps) != 2 or not isinstance(model.steps[0][1], SimpleImputer) or not isinstance(model.steps[-1][1], RandomForestClassifier):
            return _unavailable("Cette explication est limitée au pipeline imputation + forêt sauvegardé.", limitations=limitations)
        values = selected[features]
        transformed = model[:-1].transform(values)
        classifier = model.steps[-1][1]
        probabilities = model.predict_proba(values)[0]
        # For sklearn RandomForestClassifier, raw tree outputs are probabilities.
        # Path-dependent SHAP uses training counts stored in the trees, no test
        # observations are used as a background or to fit preprocessing.
        explainer = shap.TreeExplainer(classifier, feature_perturbation="tree_path_dependent", model_output="raw")
        explanation = np.asarray(explainer.shap_values(transformed, check_additivity=True))
        if explanation.shape != (1, len(features), len(classifier.classes_)):
            return _unavailable("Dimensions SHAP inattendues ; aucun résultat affiché.", limitations=limitations)
        baseline = np.asarray(explainer.expected_value)
        reconstructed = baseline + explanation[0].sum(axis=0)
        if not np.allclose(reconstructed, probabilities, rtol=1e-5, atol=1e-6):
            return _unavailable("Contrôle d'additivité SHAP échoué ; aucun résultat affiché.", limitations=limitations)
        chosen = int(np.argmax(probabilities))
        contributions = [{"feature": feature, "label": FEATURE_LABELS[feature], "value": _number(row[feature]),
                          "imputed_value": float(transformed[0, index]), "imputed": _number(row[feature]) is None,
                          "contribution": float(explanation[0, index, chosen])} for index, feature in enumerate(features)]
        contributions.sort(key=lambda item: abs(item["contribution"]), reverse=True)
        return {"status": "ok", "method": "Tree SHAP, modèle gelé", "predicted_objective": str(classifier.classes_[chosen]),
                "probabilities": {str(name): float(probabilities[i]) for i, name in enumerate(classifier.classes_)},
                "baseline_probability": float(baseline[chosen]), "contributions": contributions,
                "additivity_error": float(np.max(np.abs(reconstructed - probabilities))),
                "split": str(row["split"]), "training_n": metrics.get("train_n"), "test_n": metrics.get("test_n"),
                "model_sha256": hashlib.sha256(required[0].read_bytes()).hexdigest(), "limitations": limitations}

    def analyze(self, activity_id: str) -> dict:
        self._activity(activity_id)
        return {"activity_id": activity_id, "segments": self.segments(activity_id), "explanation": self.explanation(activity_id)}

    def route(self, activity_id: str) -> dict:
        """Private, on-demand GeoJSON. No map tiles or third-party requests."""
        activity = self._activity(activity_id)
        metadata = {"activity_id": activity_id, "status": "ok", "max_gap_seconds": 15,
                    "limitations": ["Trace GPS brute, sans correction de précision. Les pauses et trous séparent les lignes.", "Trace chargée uniquement à la demande ; aucune tuile ni donnée envoyée à un fournisseur de carte."]}
        try:
            points, events = self._fit_data(activity, positions=True)
        except (OSError, ValueError, ImportError) as exc:
            metadata.update(status="unavailable", message=f"Lecture GPS impossible ({type(exc).__name__}).")
            return {"type": "FeatureCollection", "features": [], "metadata": metadata}
        start, end = _stamp(activity["start_utc"]), _stamp(activity["end_utc"])
        pauses = self._pause_intervals(events, start, end)
        blocks, current = [], []
        for stamp, raw_lat, raw_lon in points:
            elapsed = (stamp - start).total_seconds()
            coordinate = None
            if raw_lat is not None and raw_lon is not None:
                lat, lon = raw_lat * 180 / 2**31, raw_lon * 180 / 2**31
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    coordinate = [lon, lat]
            is_paused = any(a <= elapsed < b for a, b in pauses)
            split = coordinate is None or is_paused
            if current and coordinate is not None:
                previous = current[-1][0]
                split |= (stamp - previous).total_seconds() > 15 or stamp <= previous or abs(coordinate[0] - current[-1][1][0]) > 180
                split |= any((previous - start).total_seconds() < b and elapsed >= a for a, b in pauses)
            if split and current:
                blocks.append(current)
                current = []
            if coordinate is not None and not is_paused:
                current.append((stamp, coordinate))
        if current:
            blocks.append(current)
        count = sum(len(block) for block in blocks)
        step = max(1, math.ceil(count / 4000))
        features = []
        for block in blocks:
            if len(block) < 2:
                continue
            selected = block[::step]
            if selected[-1] != block[-1]:
                selected.append(block[-1])
            features.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": [item[1] for item in selected]},
                             "properties": {"start_utc": block[0][0].isoformat(), "end_utc": block[-1][0].isoformat(), "original_points": len(block)}})
        metadata.update(status="ok" if features else "no_gps", original_points=count, displayed_points=sum(len(item["geometry"]["coordinates"]) for item in features), downsampled=step > 1)
        return {"type": "FeatureCollection", "features": features, "metadata": metadata}

    def export_parquet(self, output: Path | None = None) -> dict:
        """Export a new derived table through DuckDB, confined to analytics/."""
        try:
            duckdb = importlib.import_module("duckdb")
        except ImportError:
            return _unavailable("DuckDB n'est pas installé.")
        output = (output or self.export_dir / "sessions.parquet").resolve()
        if not output.is_relative_to(self.export_dir.resolve()) or output.suffix != ".parquet":
            raise ValueError("L'export Parquet doit rester dans data/processed/analytics.")
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(output.name + "." + uuid.uuid4().hex + ".tmp")
        frame = self._table()
        try:
            with duckdb.connect(":memory:") as connection:
                connection.from_df(frame).write_parquet(str(temporary), compression="zstd")
                rows = connection.execute("SELECT count(*) FROM read_parquet(?)", [str(temporary)]).fetchone()[0]
            if rows != len(frame):
                raise ValueError("Nombre de lignes Parquet incohérent.")
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)
        return {"status": "ok", "rows": rows, "path": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "source_sha256": hashlib.sha256(self.catalog_path.read_bytes()).hexdigest()}

    def register_model(self) -> dict:
        """Log the frozen experiment once to local MLflow; no training or deployment."""
        try:
            client_module = importlib.import_module("mlflow.tracking")
            importlib.import_module("mlflow.store.tracking.sqlalchemy_store")
        except ImportError:
            return _unavailable("MLflow et son stockage SQLAlchemy/Alembic sont requis ; aucun registre distant utilisé.")
        model_path = self.model_dir / "model.joblib"
        metrics_path = self.model_dir / "metrics.json"
        dataset_path = self.dataset_dir / "dataset.csv"
        manifest_path = self.dataset_dir / "manifest.json"
        if not all(path.is_file() for path in [model_path, metrics_path, dataset_path, manifest_path]):
            return _unavailable("Modèle, bilan, jeu de données et manifeste d'origine requis.")
        model_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
        metrics = json.loads(metrics_path.read_text(encoding="utf-8-sig"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        dataset_hash = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
        metrics_hash = hashlib.sha256(metrics_path.read_bytes()).hexdigest()
        if dataset_hash != metrics.get("dataset_sha256") or dataset_hash != manifest.get("dataset_sha256"):
            return _unavailable("Le jeu de données a changé depuis l'apprentissage ; inscription MLflow refusée.")
        directory = self.export_dir / "mlflow"
        directory.mkdir(parents=True, exist_ok=True)
        tracking_uri = "sqlite:///" + (directory / "tracking.db").as_posix()
        client = client_module.MlflowClient(tracking_uri=tracking_uri, registry_uri=tracking_uri)
        name = "SessionDNA — modèle sportif gelé"
        with self._lock:
            experiment = client.get_experiment_by_name(name)
            experiment_id = experiment.experiment_id if experiment else client.create_experiment(name, artifact_location=(directory / "artifacts").as_uri())
            existing = client.search_runs([experiment_id], filter_string=f"tags.model_sha256 = '{model_hash}' AND tags.metrics_sha256 = '{metrics_hash}' AND attributes.status = 'FINISHED'", max_results=1)
            if existing:
                return {"status": "ok", "existing": True, "run_id": existing[0].info.run_id, "tracking_uri": tracking_uri, "model_sha256": model_hash}
            run = client.create_run(experiment_id, tags={"model_sha256": model_hash, "metrics_sha256": metrics_hash, "dataset_sha256": dataset_hash, "scope": "frozen-exploratory", "mlflow.runName": "Forêt sportive existante"})
            try:
                for key in ["train_n", "test_n", "chosen", "dataset_sha256", "labels_sha256"]:
                    if key in metrics:
                        client.log_param(run.info.run_id, key, metrics[key])
                for key, value in {"test_accuracy": metrics.get("metrics", {}).get("accuracy"), "test_f1_macro": metrics.get("metrics", {}).get("macro avg", {}).get("f1-score")}.items():
                    if _number(value) is not None:
                        client.log_metric(run.info.run_id, key, float(value))
                for path in [model_path, metrics_path, manifest_path, self.model_dir / "validation.csv", self.model_dir / "confusion_matrix.csv"]:
                    if path.is_file():
                        client.log_artifact(run.info.run_id, str(path), artifact_path="frozen")
                client.set_terminated(run.info.run_id, status="FINISHED")
            except Exception:
                client.set_terminated(run.info.run_id, status="FAILED")
                raise
        return {"status": "ok", "existing": False, "run_id": run.info.run_id, "tracking_uri": tracking_uri, "model_sha256": model_hash}
