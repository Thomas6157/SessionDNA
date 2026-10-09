"""Build local, derived analytics artifacts without training or changing inputs.

Run from the project: python src/build_analytics.py --register-model
An optional --activity ID adds a pause-aware analysis and frozen-model explanation.
All outputs stay under data/processed/analytics. No service is started.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sessiondna_analytics import AnalyticsService


def _snapshot(root: Path) -> dict[str, str]:
    paths = [root / "data/processed/triathlon/catalog.json"]
    for folder in ["data/processed/supervised", "data/processed/sport_model", "data/training/weeks"]:
        directory = root / folder
        if directory.exists():
            paths.extend(path for path in directory.rglob("*") if path.is_file()
                         and (path.suffix in {".csv", ".joblib"} or path.name in {"manifest.json", "metrics.json", "source.json"}
                              or path.name.startswith("annotations")))
    return {str(path.relative_to(root)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(set(paths)) if path.is_file()}


def _write(path: Path, content: str) -> None:
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def _report(result: dict) -> str:
    overview = result["overview"]
    lines = ["# SessionDNA — analyses locales", "", f"Généré le {result['generated_utc']} (UTC).", "",
             "Les résultats ci-dessous proviennent du catalogue FIT existant. Aucun modèle n'a été réentraîné ; "
             "aucune annotation ni semaine Ironman n'a été modifiée.", ""]
    if overview["status"] == "ok":
        totals = overview["totals"]
        lines.extend([f"**{overview['counts']['activities']} séances** dans le catalogue.", "",
                      "| Mesure | Total des valeurs présentes |", "|---|---:|",
                      f"| Durée chronométrée | {_display(totals['duration_hours'])} h |",
                      f"| Distance multisport | {_display(totals['distance_km'])} km |", "",
                      f"Données manquantes : durée {overview['missing']['duration']}, distance {overview['missing']['distance']}, date {overview['missing']['date']}.", "",
                      "Les distances additionnent des sports différents : elles ne mesurent pas une charge physiologique.", "",
                      "## Répartition par sport", "", "| Sport | Séances |", "|---|---:|"])
        for sport, count in overview["counts"].items():
            if sport != "activities":
                lines.append(f"| {sport} | {count} |")
        lines.extend(["", "## Semaines civiles (Europe/Paris)", "",
                      "| Début de semaine | Sport | Séances | Heures | km | Durées / distances absentes |", "|---|---|---:|---:|---:|---:|"])
        for week in reversed(overview["weekly"]):
            lines.append(f"| {week['week']} | {week['sport']} | {week['sessions']} | {_display(week['duration_hours'])} | {_display(week['distance_km'])} | {week['missing_duration']} / {week['missing_distance']} |")
    else:
        lines.extend([f"Agrégations indisponibles : {overview.get('message', overview['status'])}", ""])
    lines.extend(["", "## Fichiers générés", "", "- `overview.json` : totaux et historique hebdomadaire.",
                  "- `build_manifest.json` : état de génération et empreintes des entrées."])
    if result["parquet"]["status"] == "ok":
        lines.append(f"- `sessions.parquet` : {result['parquet']['rows']} lignes, export vérifié après lecture avec DuckDB.")
    else:
        lines.append(f"- Parquet indisponible : {result['parquet'].get('message', result['parquet']['status'])}")
    registry = result["model_registry"]
    lines.extend(["", "## Expérience MLflow locale", ""])
    if registry["status"] == "ok":
        lines.extend([f"Expérience existante réutilisée : {'oui' if registry['existing'] else 'non, copie créée'}. "
                      f"Identifiant : `{registry['run_id']}`.", "",
                      "Le registre SQLite et ses artefacts sont dans `mlflow/`. Il conserve une copie du modèle et du bilan existants, "
                      "leurs empreintes et les résultats déjà calculés ; il ne réalise aucun nouvel entraînement ni test."])
    elif registry["status"] == "not_requested":
        lines.append("Inscription non demandée. Ajouter `--register-model` pour archiver le modèle gelé dans MLflow local.")
    else:
        lines.append(f"Inscription indisponible : {registry.get('message', registry['status'])}")
    if result["analyses"]:
        lines.extend(["", "## Analyses demandées", "", "| Séance | Découpage | Explication SHAP | Résultat |", "|---|---|---|---|"])
        for analysis in result["analyses"]:
            lines.append(f"| {analysis['activity_id']} | {analysis['segments']} | {analysis['explanation']} | `{analysis['file']}` |")
    lines.extend(["", "## Interprétation", "",
                  "Le découpage ruptures signale des changements statistiques de vitesse ou de puissance. Les pauses de montre et les trous "
                  "séparent les blocs ; ils ne sont pas assimilés automatiquement à une récupération.", "",
                  "SHAP explique uniquement le modèle de course existant, sur les séances présentes dans son jeu de données d'origine. "
                  "L'imputation sauvegardée et la forêt sont réutilisées, sans ajustement. Le contrôle d'additivité doit réussir avant affichage. "
                  "Une explication n'est ni une cause physiologique, ni une probabilité calibrée, ni une validation médicale.", "",
                  "Les tracés GPS restent chargés à la demande par l'application ; ce script n'en exporte aucun.", "",
                  f"Empreintes des entrées inchangées pendant la génération : {'oui' if result['source_files_unchanged'] else 'NON — régénérer après stabilisation des sources'}.", ""])
    return "\n".join(lines)


def _display(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "indisponible"


def build_analytics(root: Path, *, register_model: bool = False, activity_ids: tuple[str, ...] = ()) -> dict:
    root = root.resolve()
    service = AnalyticsService(root)
    before = _snapshot(root)
    # Fail before creating outputs for nonexistent IDs or malformed catalogs.
    for activity_id in activity_ids:
        service._activity(activity_id)
    overview = service.overview()
    parquet = service.export_parquet()
    registry = service.register_model() if register_model else {"status": "not_requested"}
    output = service.export_dir
    output.mkdir(parents=True, exist_ok=True)
    analyses = []
    for activity_id in dict.fromkeys(activity_ids):
        analysis = service.analyze(activity_id)
        filename = "activity-" + hashlib.sha256(activity_id.encode()).hexdigest()[:16] + ".json"
        _write(output / filename, _json(analysis))
        analyses.append({"activity_id": activity_id, "segments": analysis["segments"]["status"],
                         "explanation": analysis["explanation"]["status"], "file": filename})
    unchanged = before == _snapshot(root)
    statuses = [overview["status"], parquet["status"]]
    if register_model:
        statuses.append(registry["status"])
    statuses.extend(item["segments"] for item in analyses)
    statuses.extend(item["explanation"] for item in analyses)
    result = {"schema_version": "sessiondna.analytics_build.v1", "generated_utc": datetime.now(timezone.utc).isoformat(),
              "status": "ok" if unchanged and "unavailable" not in statuses else "partial",
              "overview": overview, "parquet": parquet, "model_registry": registry, "analyses": analyses,
              "source_files_unchanged": unchanged, "source_sha256": before}
    _write(output / "overview.json", _json(overview))
    _write(output / "report.md", _report(result))
    _write(output / "build_manifest.json", _json(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--register-model", action="store_true", help="Copier l'expérience gelée dans le registre MLflow SQLite local")
    parser.add_argument("--activity", action="append", default=[], help="Identifiant exact du catalogue ; option répétable")
    args = parser.parse_args()
    try:
        result = build_analytics(args.root, register_model=args.register_model, activity_ids=tuple(args.activity))
    except Exception as exc:
        print(f"Génération interrompue ({type(exc).__name__}) : {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": result["status"], "report": str(args.root.resolve() / "data/processed/analytics/report.md"),
                      "sources_unchanged": result["source_files_unchanged"], "parquet": result["parquet"]["status"],
                      "mlflow": result["model_registry"]["status"]}, ensure_ascii=False))
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
