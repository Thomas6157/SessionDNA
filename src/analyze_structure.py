"""Reconstruire les étapes enregistrées dans les FIT, sans les confondre avec une prédiction."""

from pathlib import Path
import argparse
import json

import fitdecode
import matplotlib.pyplot as plt
import pandas as pd


LAP_FIELDS = ["start_time", "total_timer_time", "total_elapsed_time", "total_distance",
              "intensity", "lap_trigger", "wkt_step_index"]
STEP_FIELDS = ["message_index", "duration_type", "duration_time", "duration_distance",
               "duration_step", "repeat_steps", "intensity", "target_type"]
REFERENCE = "24311406124_ACTIVITY.fit"


def read_structure(path):
    laps, steps, records, sessions = [], [], [], []
    with fitdecode.FitReader(path) as reader:
        for message in reader:
            if not isinstance(message, fitdecode.FitDataMessage):
                continue
            if message.name == "lap":
                lap = {key: message.get_value(key, fallback=None) for key in LAP_FIELDS}
                lap["lap_order"] = len(laps)
                laps.append(lap)
            elif message.name == "workout_step":
                steps.append({key: message.get_value(key, fallback=None) for key in STEP_FIELDS})
            elif message.name == "session":
                sessions.append({key: message.get_value(key, fallback=None) for key in ("sport", "start_time")})
            elif message.name == "record":
                speed = message.get_value("enhanced_speed", fallback=None)
                if speed is None:
                    speed = message.get_value("speed", fallback=None)
                records.append({"timestamp": message.get_value("timestamp", fallback=None),
                                "speed_kmh": speed * 3.6 if speed is not None else None})
    if len(sessions) != 1 or sessions[0]["sport"] != "running":
        raise ValueError("Une seule session de course à pied est attendue.")
    return pd.DataFrame(laps, columns=LAP_FIELDS + ["lap_order"]), pd.DataFrame(steps, columns=STEP_FIELDS), pd.DataFrame(records), sessions[0]


def reconstruct_blocks(laps, steps, start):
    """Joindre les étapes aux tours puis fusionner uniquement les tours consécutifs compatibles."""
    if steps["message_index"].isna().any() or steps["message_index"].duplicated().any():
        raise ValueError("Indices d'étapes absents ou dupliqués.")
    laps = laps.copy()
    laps["start_time"] = pd.to_datetime(laps["start_time"], utc=True, errors="coerce")
    if laps["start_time"].isna().any():
        raise ValueError("Début de tour absent ou invalide.")
    for column in ["total_timer_time", "total_elapsed_time"]:
        laps[column] = pd.to_numeric(laps[column], errors="raise")
        if laps[column].isna().any() or (laps[column] < 0).any():
            raise ValueError("Durée de tour absente ou négative.")
    if (laps["start_time"].diff().dt.total_seconds().dropna() < 0).any():
        raise ValueError("Tours désordonnés ; vérifier avant de reconstruire les étapes.")
    # La clé du côté lap se nomme wkt_step_index ; côté plan, message_index.
    plan = steps.rename(columns={key: f"planned_{key}" for key in STEP_FIELDS})
    linked = laps.merge(plan, how="left", left_on="wkt_step_index", right_on="planned_message_index",
                        sort=False, validate="many_to_one", indicator=True)
    blocks = []
    for row in linked.to_dict("records"):
        matched = row["_merge"] == "both"
        end = row["start_time"] + pd.to_timedelta(row["total_elapsed_time"], unit="s")
        current = blocks[-1] if blocks else None
        same_step = bool(current and matched and current["linked"] and current["step_index"] == row["wkt_step_index"])
        contiguous = bool(current and abs((row["start_time"] - current["end_utc"]).total_seconds()) <= 2)
        # Un tour terminé par la fin d'une étape reste une frontière, même si l'indice se répète.
        ended_step = bool(current and current["last_trigger"] in ("time", "session_end"))
        if same_step and contiguous and not ended_step:
            current["timer_s"] += row["total_timer_time"]
            current["elapsed_sum_s"] += row["total_elapsed_time"]
            current["end_utc"] = end
            current["lap_count"] += 1
            current["last_trigger"] = row["lap_trigger"]
        else:
            blocks.append({"block": len(blocks) + 1, "step_index": row["wkt_step_index"],
                "linked": matched, "start_utc": row["start_time"], "end_utc": end,
                "timer_s": row["total_timer_time"], "elapsed_sum_s": row["total_elapsed_time"],
                "lap_count": 1, "last_trigger": row["lap_trigger"],
                "intensity": row["planned_intensity"] if matched else row["intensity"],
                "planned_duration_type": row["planned_duration_type"],
                "planned_duration_s": row["planned_duration_time"]})
    result = pd.DataFrame(blocks)
    if result.empty:
        return linked, result
    result["start_min"] = (result["start_utc"] - start).dt.total_seconds() / 60
    result["end_min"] = (result["end_utc"] - start).dt.total_seconds() / 60
    result["timer_min"] = result["timer_s"] / 60
    result["time_difference_s"] = result["timer_s"] - result["planned_duration_s"]
    result.loc[result["planned_duration_type"] != "time", "time_difference_s"] = float("nan")
    result["repeated_active"] = False
    # Deux fragments successifs d'une même étape (pause, auto-lap au temps)
    # ne suffisent pas à prouver une répétition de l'exercice.
    adjacent = result["step_index"].eq(result["step_index"].shift())
    fragmented_ids = result.loc[adjacent, "step_index"].dropna().unique()
    result["ambiguous_fragmentation"] = result["step_index"].isin(fragmented_ids)
    active = result["linked"] & (result["intensity"] == "active") & ~result["ambiguous_fragmentation"]
    counts = result.loc[active, "step_index"].value_counts()
    repeated_ids = counts[counts >= 2].index
    result.loc[active & result["step_index"].isin(repeated_ids), "repeated_active"] = True
    return linked, result


def plot_structure(records, blocks, filename, start, output):
    records = records.copy()
    records["timestamp"] = pd.to_datetime(records["timestamp"], utc=True)
    records["elapsed_min"] = (records["timestamp"] - start).dt.total_seconds() / 60
    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    for _, group in records.groupby((records["timestamp"].diff().dt.total_seconds() > 1).cumsum()):
        axes[0].plot(group["elapsed_min"], group["speed_kmh"], color="#316a95", linewidth=0.8)
    for row in blocks.itertuples():
        long_repeat = row.repeated_active and row.timer_s >= 60
        color = "#da922f" if long_repeat else "#67a1ae" if row.intensity == "recovery" else "#ce6562" if row.repeated_active else "#b5b8bb"
        axes[1].broken_barh([(row.start_min, max(0, row.end_min - row.start_min))], (0, 1), facecolors=color, edgecolors="white", linewidth=0.6)
        if long_repeat:
            axes[0].axvspan(row.start_min, row.end_min, color=color, alpha=0.17)
            axes[0].text((row.start_min + row.end_min) / 2, 0.96, f"{row.timer_min:.1f} min",
                         transform=axes[0].get_xaxis_transform(), ha="center", va="top", fontsize=9)
        if row.timer_s >= 120:
            label = f"E{int(row.step_index)}" if pd.notna(row.step_index) else "?"
            axes[1].text((row.start_min + row.end_min) / 2, 0.5, label, ha="center", va="center", fontsize=8)
    axes[0].set_ylabel("Vitesse (km/h)")
    axes[0].grid(alpha=0.2)
    axes[0].set_title(f"{filename}\nÉtapes reconstruites depuis les métadonnées Garmin — aucune prédiction")
    axes[1].set_yticks([])
    axes[1].set_ylabel("Étapes FIT")
    axes[1].set_xlabel("Minutes écoulées depuis le début de la session")
    fig.text(0.5, 0.015, "Orange : étapes actives répétées ≥ 60 s · Rouge : répétées < 60 s · Bleu : récupération déclarée · Gris : autres", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(output, dpi=150)
    plt.close(fig)


def main():
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=project / "data/raw")
    parser.add_argument("--features", type=Path, default=project / "data/processed/batch/running_features.csv")
    parser.add_argument("--output", type=Path, default=project / "data/processed/structure")
    args = parser.parse_args()
    files = pd.read_csv(args.features)["filename"].tolist()
    if len(files) != len(set(files)):
        raise ValueError("Fichiers dupliqués dans l'inventaire des courses.")
    args.output.mkdir(parents=True, exist_ok=True)
    details = args.output / "activities"
    details.mkdir(exist_ok=True)
    plt.switch_backend("Agg")
    summaries, repeated_rows = [], []
    for filename in files:
        if Path(filename).name != filename:
            raise ValueError("Nom de fichier inattendu dans l'inventaire.")
        print(f"Structure : {filename}", flush=True)
        try:
            laps, steps, records, session = read_structure(args.raw / filename)
            start = pd.to_datetime(session["start_time"], utc=True)
            if pd.isna(start):
                raise ValueError("Début de session absent.")
            linked, blocks = reconstruct_blocks(laps, steps, start)
            activity_dir = details / Path(filename).stem
            activity_dir.mkdir(exist_ok=True)
            steps.to_csv(activity_dir / "planned_steps.csv", index=False)
            linked.to_csv(activity_dir / "linked_laps.csv", index=False)
            blocks.to_csv(activity_dir / "observed_blocks.csv", index=False)
            n_linked = int((linked["_merge"] == "both").sum())
            summary = {"filename": filename, "start_utc": start, "status": "ok" if n_linked else "no_linked_structure",
                "n_laps": len(laps), "n_planned_steps": len(steps), "n_linked_laps": n_linked,
                "n_observed_blocks": len(blocks), "n_repeated_active_blocks": 0,
                "n_repeated_active_blocks_ge60s": 0, "repetition_summary": "", "notes": ""}
            if not blocks.empty:
                active = blocks.loc[blocks["repeated_active"]]
                summary["n_repeated_active_blocks"] = len(active)
                summary["n_repeated_active_blocks_ge60s"] = int((active["timer_s"] >= 60).sum())
                text = []
                for step_index, group in active.groupby("step_index"):
                    durations = group["timer_s"]
                    text.append(f"E{int(step_index)} : {len(group)} x {durations.median():.0f} s (médiane)")
                    repeated_rows.append({"filename": filename, "step_index": int(step_index), "observed_repetitions": len(group),
                        "duration_median_s": durations.median(), "duration_min_s": durations.min(), "duration_max_s": durations.max()})
                summary["repetition_summary"] = "; ".join(text)
                if n_linked < len(laps):
                    summary["notes"] = "Certains tours sans lien : conservés séparément."
                if blocks["ambiguous_fragmentation"].any():
                    summary["notes"] += " Étape fragmentée : exclue du comptage des répétitions."
                plot_structure(records, blocks, filename, start, activity_dir / "structure.png")
            summaries.append(summary)
        except Exception as exc:
            summaries.append({"filename": filename, "status": "error", "notes": f"{type(exc).__name__}: {exc}"})
    summary = pd.DataFrame(summaries)
    repeated = pd.DataFrame(repeated_rows, columns=["filename", "step_index", "observed_repetitions", "duration_median_s", "duration_min_s", "duration_max_s"])
    summary.to_csv(args.output / "structure_summary.csv", index=False, encoding="utf-8-sig")
    repeated.to_csv(args.output / "repeated_steps.csv", index=False, encoding="utf-8-sig")
    config = {"source": "Garmin FIT workout_step + lap", "boundary_tolerance_s": 2,
        "long_display_min_s": 60, "predictions": False, "files": files,
        "merge_rule": "Tours consécutifs liés à la même étape, continuité <= 2 s, sans frontière time/session_end."}
    (args.output / "method.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# SessionDNA — Structure enregistrée des séances", "",
        f"**{len(summary)} courses examinées.** Reconstruction des métadonnées Garmin ; aucun détecteur de seuil ni classifieur.", "",
        "## Méthode", "",
        "Un tour d'un kilomètre n'est pas nécessairement un intervalle d'effort. Les laps sont reliés aux workout_steps par wkt_step_index → message_index. Les tours consécutifs compatibles d'une même étape sont réunis ; des occurrences séparées par une récupération restent distinctes.",
        "Les durées réalisées sont les sommes de total_timer_time des tours. Les positions dans le graphique utilisent start_time et total_elapsed_time ; elles peuvent différer des durées chronométrées à cause des pauses. Le champ timestamp des laps n'est pas utilisé comme fin, car il est incohérent dans certains exports observés.", "",
        "## Résultats", "", "| Fichier | État | Tours | Blocs | Répétitions actives observées |", "|---|---|---:|---:|---|"]
    for row in summary.to_dict("records"):
        stem = Path(row["filename"]).stem
        title = f"[{row['filename']}](activities/{stem}/structure.png)" if row["status"] != "error" else row["filename"]
        lines.append(f"| {title} | {row['status']} | {row.get('n_laps', '—')} | {row.get('n_observed_blocks', '—')} | {row.get('repetition_summary', '')} |")
    if REFERENCE in files and (details / Path(REFERENCE).stem / "structure.png").exists():
        lines += ["", "## Séance repère — 2 × 15 minutes déclarées par l'utilisateur", "",
                  f"![Structure repère](activities/{Path(REFERENCE).stem}/structure.png)", ""]
    lines += ["## Limites et apprentissages", "",
        "- Les étapes du programme décrivent une intention ; les laps enregistrent les durées réalisées. On conserve les deux au lieu de supposer qu'elles sont identiques.",
        "- active n'est pas synonyme de seuil : échauffement et retour au calme portent parfois aussi ce code.",
        "- Une répétition est identifiée par plusieurs blocs actifs liés au même indice d'étape. L'absence de répétition identifiée ne prouve pas une séance sans intervalles.",
        "- Les tours sans lien restent séparés. Un FIT sans workout_steps exige une méthode fondée sur les signaux ; nous n'inventons pas sa structure.",
        "- La fusion conservatrice s'arrête aux déclencheurs time/session_end et aux ruptures de continuité > 2 s. Des auto-laps au temps ou des métadonnées inhabituelles peuvent produire une fragmentation à examiner.",
        "- Si plusieurs blocs successifs portent le même indice, cette étape est marquée ambiguous_fragmentation et exclue du comptage des répétitions. Une pause ne doit pas devenir un nouvel intervalle.",
        "- Le seuil de 60 secondes sert seulement à distinguer les répétitions brèves dans les sorties et le graphique ; il n'a pas de sens physiologique.",
        "- Ces références issues du programme doivent rester séparées des caractéristiques d'un futur détecteur fondé uniquement sur les capteurs, pour éviter une fuite d'information.",
        "- Les anciens résultats de clustering sont conservés : cette étape ne remplace pas automatiquement leurs caractéristiques.",
        "", "Sources : [structure FIT Activity](https://developer.garmin.com/fit/articles/file-types/activity.html), [Workout](https://developer.garmin.com/fit/articles/file-types/workout.html)."]
    (args.output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(summary["status"].value_counts().to_string())
    print(f"Résultats : {args.output.resolve()}")


if __name__ == "__main__":
    main()
