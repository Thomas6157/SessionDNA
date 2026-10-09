"""Première exploration d'une séance FIT, sans apprentissage automatique."""

from pathlib import Path
import argparse

import fitdecode
import matplotlib.pyplot as plt
import pandas as pd


def main():
    # 1. Choisir l'entrée et le dossier des résultats.
    project_dir = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=project_dir / "data/raw/24311406124_ACTIVITY.fit")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--no-show", action="store_true", help="Sauvegarder sans ouvrir de fenêtre")
    args = parser.parse_args()
    if args.no_show:
        plt.switch_backend("Agg")
    output_dir = args.output or project_dir / "data/processed" / args.file.stem

    # 2. Un message record devient une ligne du tableau.
    rows = []
    with fitdecode.FitReader(args.file) as fit_file:
        for message in fit_file:
            if isinstance(message, fitdecode.FitDataMessage) and message.name == "record":
                speed = message.get_value("enhanced_speed", fallback=None)
                if speed is None:
                    speed = message.get_value("speed", fallback=None)
                rows.append({
                    "timestamp": message.get_value("timestamp", fallback=None),
                    "heart_rate_bpm": message.get_value("heart_rate", fallback=None),
                    "speed_m_s": speed,
                    "distance_m": message.get_value("distance", fallback=None),
                    "power_w": message.get_value("power", fallback=None),
                })

    if len(rows) < 2:
        raise ValueError("Il faut au moins deux points record pour cette exploration.")
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    if df["timestamp"].isna().any():
        raise ValueError("Horodatage absent ou invalide : vérifier avant de poursuivre.")
    gaps_s = df["timestamp"].diff().dt.total_seconds()
    if (gaps_s <= 0).any():
        raise ValueError("Horodatages répétés ou désordonnés : vérifier avant de poursuivre.")

    # 3. Conserver les mesures brutes et ajouter des unités pratiques.
    df["elapsed_min"] = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds() / 60
    df["speed_kmh"] = df["speed_m_s"] * 3.6
    missing = df.isna().sum()
    gap_table = pd.DataFrame({
        "before_utc": df["timestamp"].shift(),
        "after_utc": df["timestamp"],
        "gap_s": gaps_s,
        "after_elapsed_min": df["elapsed_min"],
    }).loc[gaps_s > 1]

    # 4. Chaque mesure présente a le même poids ; aucune valeur n'est imputée.
    metrics = ["speed_kmh", "heart_rate_bpm", "power_w"]
    summary = df[metrics].agg(["count", "mean", "median", "min", "max"])

    # Ces limites MANUELLES ne concernent que notre première séance.
    # Elles ne constituent ni une détection automatique ni des étiquettes validées.
    phases = [
        ("Échauffement", 0, 27),
        ("Effort 1", 27, 42),
        ("Récupération", 42, 45),
        ("Effort 2", 45, 60),
        ("Retour au calme", 60, None),
    ]
    phase_rows = []
    reference_session = args.file.name == "24311406124_ACTIVITY.fit"
    if reference_session:
        for label, start, end in phases:
            mask = df["elapsed_min"] >= start
            if end is not None:
                mask = mask & (df["elapsed_min"] < end)
            part = df.loc[mask]
            if part.empty:
                continue
            phase_rows.append({
                "phase_manuelle": label,
                "start_min": start,
                "end_min": end if end is not None else df["elapsed_min"].iloc[-1],
                "n_records": len(part),
                "speed_mean_kmh": part["speed_kmh"].mean(),
                "heart_rate_mean_bpm": part["heart_rate_bpm"].mean(),
                "power_mean_w": part["power_w"].mean(),
            })
    phase_summary = pd.DataFrame(phase_rows)

    # 5. Sauvegarder les tableaux dérivés, sans modifier le fichier FIT.
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / "records.csv", index=False)
    summary.to_csv(output_dir / "summary.csv", index_label="statistic")
    gap_table.to_csv(output_dir / "gaps.csv", index=False)
    if not phase_summary.empty:
        phase_summary.to_csv(output_dir / "manual_phases.csv", index=False)

    # 6. Dessiner sans relier artificiellement les points séparés par un trou.
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    for _, segment in df.groupby((gaps_s > 1).cumsum()):
        axes[0].plot(segment["elapsed_min"], segment["speed_kmh"], color="tab:blue", linewidth=1)
        axes[1].plot(segment["elapsed_min"], segment["heart_rate_bpm"], color="tab:red", linewidth=1)
    for ax in axes:
        if reference_session:
            ax.axvspan(27, 42, color="tab:green", alpha=0.12, label="Efforts repérés manuellement")
            ax.axvspan(45, 60, color="tab:green", alpha=0.12)
        for idx in gap_table.index:
            ax.axvspan(df.loc[idx - 1, "elapsed_min"], df.loc[idx, "elapsed_min"], color="black", alpha=0.2)
        ax.grid(True, alpha=0.25)
    axes[0].set_ylabel("Vitesse (km/h)")
    axes[0].set_title("SessionDNA — Exploration de la séance")
    if reference_session:
        axes[0].legend(loc="upper left")
    axes[1].set_ylabel("Fréquence cardiaque (bpm)")
    axes[1].set_xlabel("Temps écoulé depuis le premier point (minutes, pauses comprises)")
    fig.tight_layout()
    fig.savefig(output_dir / "session.png", dpi=160)

    # 7. Un bilan lisible qui conserve aussi les limites de cette analyse.
    duration_min = df["elapsed_min"].iloc[-1]
    negative_counts = (df[["speed_kmh", "heart_rate_bpm", "power_w", "distance_m"]] < 0).sum()
    distance_decreases = int((df["distance_m"].diff() < 0).sum())
    phase_text = phase_summary.round(2).to_string(index=False) if not phase_summary.empty else "Non appliqué : limites réservées à la séance de référence."
    report = f"""# SessionDNA — Bilan de la première exploration

Fichier : {args.file.name}
Points : {len(df)}
Temps écoulé entre premier et dernier point : {duration_min:.2f} minutes.
Intervalles supérieurs à une seconde : {len(gap_table)}.
Baisses de distance cumulée : {distance_decreases}.

## Valeurs manquantes
```text
{missing.to_string()}
```

## Valeurs négatives à examiner
```text
{negative_counts.to_string()}
```

## Statistiques des points présents
```text
{summary.round(2).to_string()}
```

## Phases repérées manuellement — limites approximatives
```text
{phase_text}
```

## Limites et interprétation
- Aucun modèle entraîné ; les phases ne sont pas détectées automatiquement.
- Le mot « seuil » provient de la description de l'utilisateur, pas d'une mesure validée du seuil.
- Moyennes des points présents : pas de pondération temporelle ni d'interpolation du trou.
- Temps écoulé : ne représente pas nécessairement le temps du chronomètre Garmin.
- Valeurs manquantes conservées ; les zéros restent des valeurs et ne sont pas supprimés.
- Les pics sont conservés : ces contrôles ne garantissent pas l'exactitude des capteurs.
- Le graphique coupe les lignes aux trous supérieurs à une seconde.
- Les statistiques globales masquent l'ordre des efforts : leur structure devra être décrite ensuite.
"""
    (output_dir / "report.md").write_text(report, encoding="utf-8")
    print(report)
    print(f"\nRésultats sauvegardés dans : {output_dir}")
    if not args.no_show:
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
