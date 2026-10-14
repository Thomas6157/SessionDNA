"""Inventorier des fichiers FIT et comparer les courses, sans inventer de catégories."""

from pathlib import Path
import argparse
import hashlib
import warnings

import fitdecode
import matplotlib.pyplot as plt
import pandas as pd


def read_activity(path):
    """Lire les résumés session et les points record ; ne jamais modifier le FIT."""
    sessions, rows = [], []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with fitdecode.FitReader(path) as fit_file:
            for message in fit_file:
                if not isinstance(message, fitdecode.FitDataMessage):
                    continue
                if message.name == "session":
                    sessions.append({name: message.get_value(name, fallback=None) for name in (
                        "sport", "sub_sport", "start_time", "total_elapsed_time",
                        "total_timer_time", "total_distance",
                    )})
                elif message.name == "record":
                    speed = message.get_value("enhanced_speed", fallback=None)
                    if speed is None:
                        speed = message.get_value("speed", fallback=None)
                    rows.append({
                        "timestamp": message.get_value("timestamp", fallback=None),
                        "speed_kmh": speed * 3.6 if speed is not None else None,
                        "heart_rate_bpm": message.get_value("heart_rate", fallback=None),
                        "power_w": message.get_value("power", fallback=None),
                    })
    warning_text = " | ".join(sorted({str(item.message) for item in caught}))
    return sessions, pd.DataFrame(rows), warning_text


def summarize_activity(path, sessions, df, warning_text):
    """Une ligne par fichier : identité, mesures descriptives et contrôles."""
    row = {
        "filename": path.name, "status": "ok", "issues": warning_text,
        "session_count": len(sessions), "n_records": len(df),
        "sport": "/".join(sorted({str(s["sport"]) for s in sessions})),
        "duplicate_of": "", "possible_duplicate_of": "",
        "user_description": "2 x 15 min au seuil (déclaration utilisateur)"
        if path.name == "24311406124_ACTIVITY.fit" else "",
    }
    if len(sessions) != 1:
        row.update(status="excluded", issues="Nombre de sessions différent de 1 : traitement spécifique requis.")
        return row, df
    session = sessions[0]
    row["sub_sport"] = session["sub_sport"]
    row["start_utc"] = pd.to_datetime(session["start_time"], utc=True)
    # Les durées et la distance ci-dessous proviennent du résumé Garmin.
    for field, target, divisor in (
        ("total_elapsed_time", "elapsed_min", 60),
        ("total_timer_time", "timer_min", 60),
        ("total_distance", "distance_km", 1000),
    ):
        row[target] = session[field] / divisor if session[field] is not None else float("nan")
    row["paused_min"] = row["elapsed_min"] - row["timer_min"]
    if len(df) < 2:
        row.update(status="excluded", issues="Moins de deux points record.")
        return row, df
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    row["missing_timestamps"] = int(df["timestamp"].isna().sum())
    gaps = df["timestamp"].diff().dt.total_seconds()
    row["non_increasing_timestamps"] = int((gaps <= 0).sum())
    if row["missing_timestamps"] or row["non_increasing_timestamps"]:
        row.update(status="excluded", issues="Horodatages manquants, invalides, répétés ou désordonnés.")
        return row, df
    if pd.isna(row["start_utc"]):
        row["start_utc"] = df["timestamp"].iloc[0]
        row["issues"] += " | Début obtenu depuis le premier point (résumé incomplet)."
    df["elapsed_min"] = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds() / 60
    row["record_span_min"] = df["elapsed_min"].iloc[-1]
    row["median_interval_s"] = gaps.median()
    row["max_interval_s"] = gaps.max()
    row["gaps_over_1s"] = int((gaps > 1).sum())
    # Statistiques par point présent : ni interpolation ni pondération temporelle.
    for column, prefix in (("speed_kmh", "speed"), ("heart_rate_bpm", "hr"), ("power_w", "power")):
        values = pd.to_numeric(df[column], errors="coerce")
        df[column] = values
        row[f"{prefix}_missing_pct"] = values.isna().mean() * 100
        row[f"{prefix}_negative_count"] = int((values < 0).sum())
        row[f"{prefix}_zero_count"] = int((values == 0).sum())
        row[f"{prefix}_mean"] = values.mean()
        row[f"{prefix}_median"] = values.median()
        row[f"{prefix}_std"] = values.std()  # Écart-type d'échantillon, ddof=1.
        row[f"{prefix}_max"] = values.max()
    row["speed_cv"] = row["speed_std"] / row["speed_mean"] if row["speed_mean"] > 0 else float("nan")
    if warning_text:
        row["status"] = "review"
    if any(row[f"{prefix}_negative_count"] for prefix in ("speed", "hr", "power")):
        row["status"] = "review"
        row["issues"] += " | Valeurs négatives à examiner."
    if row["speed_missing_pct"] == 100:
        row["status"] = "review"
        row["issues"] += " | Aucune vitesse disponible."
    if row["hr_zero_count"]:
        row["status"] = "review"
        row["issues"] += " | Fréquence cardiaque nulle à examiner."
    if row["paused_min"] < 0:
        row["status"] = "review"
        row["issues"] += " | Durées Garmin incohérentes."
    return row, df


def save_activity_plot(df, row, path):
    """Courbes de repérage, sans étiqueter automatiquement la séance."""
    fig, axes = plt.subplots(2, 1, figsize=(11, 5.8), sharex=True)
    groups = (df["timestamp"].diff().dt.total_seconds() > 1).cumsum()
    for _, segment in df.groupby(groups):
        axes[0].plot(segment["elapsed_min"], segment["speed_kmh"], color="#2367a1", linewidth=0.8)
        axes[1].plot(segment["elapsed_min"], segment["heart_rate_bpm"], color="#b74145", linewidth=0.8)
    for ax in axes:
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("Vitesse (km/h)")
    axes[1].set_ylabel("FC (bpm)")
    axes[1].set_xlabel("Minutes depuis le premier point (pauses comprises)")
    date = row["start_utc"].strftime("%d/%m/%Y %H:%M UTC")
    fig.suptitle(f"{row['filename']}\n{date} — {row['distance_km']:.2f} km — {row['timer_min']:.1f} min chronométrées")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def save_comparison(runs, path):
    labels = [f"{r.start_utc:%d/%m} · {r.filename.split('_')[0]}" for r in runs.itertuples()]
    fig, axes = plt.subplots(1, 3, figsize=(14, max(5, len(runs) * 0.42 + 1.5)), sharey=True)
    for ax, column, title, color in zip(axes,
            ["timer_min", "speed_mean", "speed_std"],
            ["Durée chronométrée (min)", "Vitesse moyenne des points (km/h)", "Écart-type de vitesse (km/h)"],
            ["#427b84", "#2367a1", "#b87833"]):
        ax.barh(range(len(runs)), runs[column], color=color)
        ax.set_title(title, fontsize=10)
        ax.grid(axis="x", alpha=0.2)
        ax.set_axisbelow(True)
    axes[0].set_yticks(range(len(runs)), labels=labels)
    axes[0].invert_yaxis()
    fig.suptitle("SessionDNA — Une ligne par séance de course à pied", fontsize=14)
    fig.text(0.5, 0.015, "Comparaison descriptive : aucune catégorie prédite. Dates UTC. Pics et arrêts conservés.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def make_report(inventory, runs, output):
    def number(value):
        return f"{value:.2f}" if pd.notna(value) else "—"
    lines = ["# SessionDNA — Inventaire et comparaison des activités", "",
        f"Fichiers inventoriés : **{len(inventory)}**. Courses retenues pour la comparaison : **{len(runs)}**.", "",
        "Les dates sont en UTC. Le type précis de séance reste inconnu sauf description déjà fournie par l'utilisateur.", "",
        "| Fichier | Départ UTC | Sport | Distance km | Temps chronométré min | Temps écoulé min | Statut |",
        "|---|---|---|---:|---:|---:|---|"]
    for _, row in inventory.iterrows():
        date = row.get("start_utc")
        date = date.strftime("%d/%m/%Y %H:%M") if pd.notna(date) else "—"
        lines.append(f"| {row['filename']} | {date} | {row.get('sport', '—')} | {number(row.get('distance_km'))} | {number(row.get('timer_min'))} | {number(row.get('elapsed_min'))} | {row['status']} |")
    lines += ["", "## Contrôles", "",
        "Les statuts `error`, `excluded`, `duplicate` et `review` sont exclus de la comparaison automatique. Les autres sports sont inventoriés séparément.", ""]
    for _, row in inventory.iterrows():
        lines.append(f"- **{row['filename']}** : {row['status']}; {row.get('n_records', 0)} points; "
                     f"{row.get('gaps_over_1s', '—')} intervalles > 1 s; "
                     f"puissance manquante {number(row.get('power_missing_pct'))} %. "
                     f"{row.get('issues', '')}")
    lines += ["", "## Comment lire les résultats", "",
        "- `inventory.csv` : tous les fichiers, leur identité et leurs contrôles ; un échec ne bloque pas les autres fichiers.",
        "- `running_features.csv` : une ligne par course retenue, avec des caractéristiques numériques descriptives.",
        "- `activity_profiles/` : les courbes de chaque course retenue, nommées comme le FIT.",
        "- La durée chronométrée exclut les pauses du chronomètre ; elle n'est pas nécessairement le temps en mouvement.",
        "- L'écart-type mesure la dispersion des vitesses autour de leur moyenne. Une valeur élevée peut venir d'intervalles, du terrain, d'arrêts ou d'erreurs de mesure.",
        "- `speed_cv` est l'écart-type divisé par la moyenne, sans unité. Il ne décrit pas l'ordre des efforts.",
        "- Moyennes et écarts-types sont calculés par point présent. Les zéros et pics sont conservés ; les valeurs absentes sont exclues des statistiques.",
        "- Les intervalles > 1 s sont signalés sans être assimilés automatiquement à des données perdues : pauses et enregistrement irrégulier sont possibles.",
        "- Doublons exacts repérés par SHA-256 ; même sport et même début UTC signalés comme doublons possibles à vérifier.",
        "- Aucune catégorie inventée, aucune phase manuelle du premier fichier appliquée aux autres, aucun modèle entraîné.",
        "- Ce petit échantillon sert à l'exploration ; il ne permet pas de revendiquer un classifieur fiable.",
        "", "Référence sur les durées FIT : [Garmin](https://developer.garmin.com/fit/cookbook/durations/).", ""]
    if not runs.empty:
        lines += ["## Vue comparative", "", "![Comparaison](running_comparison.png)", "", "## Courbes pour retrouver les séances", ""]
        for row in runs.itertuples():
            lines += [f"### {row.start_utc:%d/%m/%Y %H:%M UTC} — {row.filename}", "",
                      f"![Profil](activity_profiles/{Path(row.filename).stem}.png)", ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=project / "data/raw")
    parser.add_argument("--output", type=Path, default=project / "data/processed/batch")
    args = parser.parse_args()
    paths = sorted(p for p in args.input.iterdir() if p.is_file() and p.suffix.lower() == ".fit")
    if not paths:
        raise SystemExit("Aucun fichier FIT dans le dossier d'entrée.")
    plt.switch_backend("Agg")
    args.output.mkdir(parents=True, exist_ok=True)
    profiles = args.output / "activity_profiles"
    profiles.mkdir(exist_ok=True)
    rows, seen_hashes, seen_starts = [], {}, {}
    for path in paths:
        print(f"Lecture : {path.name}", flush=True)
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest in seen_hashes:
                rows.append({"filename": path.name, "status": "duplicate", "sha256": digest,
                             "duplicate_of": seen_hashes[digest], "issues": "Contenu identique : non recompté."})
                continue
            seen_hashes[digest] = path.name
            sessions, df, warning_text = read_activity(path)
            row, df = summarize_activity(path, sessions, df, warning_text)
            row["sha256"] = digest
            if pd.notna(row.get("start_utc")):
                key = (row["sport"], row["start_utc"])
                if key in seen_starts:
                    row["possible_duplicate_of"] = seen_starts[key]
                    row["status"] = "review"
                    row["issues"] += " | Même sport et même début UTC qu'un autre fichier."
                else:
                    seen_starts[key] = path.name
            if row["status"] == "ok" and row["sport"] == "running":
                save_activity_plot(df, row, profiles / f"{path.stem}.png")
            rows.append(row)
        except Exception as exc:
            # Conserver le nom et l'erreur ; continuer les autres fichiers.
            rows.append({"filename": path.name, "status": "error", "issues": f"{type(exc).__name__}: {exc}"})
    inventory = pd.DataFrame(rows)
    for name in ("sport", "start_utc"):
        if name not in inventory:
            inventory[name] = None
    inventory = inventory.sort_values(["start_utc", "filename"], na_position="last").reset_index(drop=True)
    runs = inventory.loc[(inventory["status"] == "ok") & (inventory["sport"] == "running")].copy()
    feature_columns = ["filename", "start_utc", "timer_min", "elapsed_min", "distance_km", "n_records",
        "speed_mean", "speed_median", "speed_std", "speed_cv", "hr_mean", "hr_std", "power_mean",
        "speed_missing_pct", "hr_missing_pct", "power_missing_pct", "gaps_over_1s", "max_interval_s"]
    inventory.to_csv(args.output / "inventory.csv", index=False, encoding="utf-8-sig")
    runs.reindex(columns=feature_columns).to_csv(args.output / "running_features.csv", index=False, encoding="utf-8-sig")
    if not runs.empty:
        save_comparison(runs, args.output / "running_comparison.png")
    make_report(inventory, runs, args.output)
    print(f"\nTerminé : {len(paths)} fichiers, {len(runs)} courses retenues.")
    print(inventory["status"].value_counts().to_string())
    print(f"Résultats : {args.output.resolve()}")


if __name__ == "__main__":
    main()
