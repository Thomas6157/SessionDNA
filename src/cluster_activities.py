"""Première expérience de clustering exploratoire sur des séances de course."""

from pathlib import Path
import argparse
import hashlib
import json

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits


FEATURES = ["timer_min", "speed_mean", "speed_cv"]
LABELS = ["Durée chronométrée (min)", "Vitesse moyenne (km/h)", "Variation relative de vitesse (CV)"]
SEED = 42
N_INIT = 30


def fit_groups(values, k):
    """Apprendre les échelles puis les groupes sur les seules lignes fournies."""
    scaler = StandardScaler()
    scaled = scaler.fit_transform(values)
    model = KMeans(n_clusters=k, n_init=N_INIT, random_state=SEED)
    labels = model.fit_predict(scaled)
    if len(np.unique(labels)) != k:
        raise ValueError(f"Impossible de former {k} groupes distincts avec ces observations.")
    return scaler, scaled, model, labels


def compare_choices(values, filenames, candidates):
    """Scores internes et sensibilité au retrait d'une séance (pas un test prédictif)."""
    results, details, fitted = [], [], {}
    for k in candidates:
        scaler, scaled, model, labels = fit_groups(values, k)
        fitted[k] = (scaler, scaled, model, labels)
        stability = []
        for removed in range(len(values)):
            keep = np.arange(len(values)) != removed
            if len(np.unique(values[keep], axis=0)) < k:
                details.append({"k": k, "removed_file": filenames[removed], "ari": np.nan,
                                "status": "Pas assez de points distincts après retrait"})
                continue
            # Recalculer aussi la standardisation après chaque retrait.
            _, _, _, reduced_labels = fit_groups(values[keep], k)
            ari = adjusted_rand_score(labels[keep], reduced_labels)
            stability.append(ari)
            details.append({"k": k, "removed_file": filenames[removed], "ari": ari, "status": "ok"})
        sizes = np.bincount(labels, minlength=k)
        results.append({
            "k": k, "silhouette": silhouette_score(scaled, labels),
            "inertia": model.inertia_, "smallest_group": int(sizes.min()),
            "largest_group": int(sizes.max()), "loo_comparisons": len(stability),
            "loo_ari_min": min(stability) if stability else np.nan,
            "loo_ari_median": float(np.median(stability)) if stability else np.nan,
        })
    return pd.DataFrame(results), pd.DataFrame(details), fitted


def save_plots(data, scaled, labels, k, output):
    colors = ["#2367a1", "#d2842e", "#288174", "#935b9f"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2))
    for ax, (left, right) in zip(axes, [(0, 1), (0, 2), (1, 2)]):
        for group in range(k):
            subset = data.loc[labels == group]
            ax.scatter(subset[FEATURES[left]], subset[FEATURES[right]], s=70,
                       color=colors[group], label=f"Groupe {group + 1}", edgecolor="white")
        # Les étiquettes se chevauchent sur les lots plus grands ; la table donne les identifiants.
        if len(data) <= 20:
            for index, row in enumerate(data.itertuples()):
                ax.annotate(row.activity_id, (getattr(row, FEATURES[left]), getattr(row, FEATURES[right])),
                            xytext=(5, 7 if index % 2 == 0 else -13), textcoords="offset points", fontsize=8)
        ax.set_xlabel(LABELS[left], fontsize=9)
        ax.set_ylabel(LABELS[right], fontsize=9)
        ax.margins(0.15)
        ax.grid(alpha=0.18)
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="lower center", ncol=k, frameon=False)
    fig.suptitle(f"SessionDNA — K-means, {k} groupes exploratoires", fontsize=15)
    fig.tight_layout(rect=(0, 0.08, 1, 0.94))
    fig.savefig(output / "clusters.png", dpi=150)
    plt.close(fig)

    order = np.argsort(labels, kind="stable")
    limit = max(1, float(np.abs(scaled).max()))
    fig, ax = plt.subplots(figsize=(9, max(5, len(data) * 0.4 + 1.5)))
    mesh = ax.imshow(scaled[order], cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks(range(3), ["Durée", "Vitesse moyenne", "Variation relative"])
    ax.set_yticks(range(len(data)), [f"{data.iloc[i]['activity_id']} · G{labels[i] + 1}" for i in order])
    for r, original in enumerate(order):
        for c in range(3):
            ax.text(c, r, f"{scaled[original, c]:.2f}", ha="center", va="center",
                    color="white" if abs(scaled[original, c]) > limit * 0.6 else "black", fontsize=9)
    ax.set_title("Caractéristiques standardisées : 0 = moyenne des 11 séances" if len(data) == 11
                 else "Caractéristiques standardisées : 0 = moyenne du lot")
    fig.colorbar(mesh, ax=ax, label="Écart à la moyenne, en unités d'écart-type")
    fig.tight_layout()
    fig.savefig(output / "standardized_features.png", dpi=150)
    plt.close(fig)


def main():
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=project / "data/processed/batch/running_features.csv")
    parser.add_argument("--output", type=Path, default=project / "data/processed/clustering")
    parser.add_argument("--k", type=int, choices=[2, 3, 4], default=3,
                        help="Nombre de groupes à détailler ; choix exploratoire, 3 par défaut")
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    required = ["filename", "start_utc"] + FEATURES
    if not set(required).issubset(data.columns):
        raise ValueError(f"Colonnes nécessaires : {required}")
    if data["filename"].isna().any() or data["filename"].duplicated().any():
        raise ValueError("Noms de fichiers absents ou répétés : vérifier l'inventaire.")
    data["start_utc"] = pd.to_datetime(data["start_utc"], utc=True, errors="raise")
    data = data.sort_values(["start_utc", "filename"]).reset_index(drop=True)
    data[FEATURES] = data[FEATURES].apply(pd.to_numeric, errors="raise")
    values = data[FEATURES].to_numpy(dtype=float)
    if len(data) < 6:
        raise ValueError("Au moins 6 séances requises pour cette expérience avec retraits.")
    if not np.isfinite(values).all():
        raise ValueError("Caractéristique manquante ou infinie : examiner les données, sans imputation automatique.")
    if (values[:, :2] <= 0).any() or (values[:, 2] < 0).any():
        raise ValueError("Durée/vitesse non positives ou variation négative : vérifier les données.")
    if (np.std(values, axis=0) == 0).any():
        raise ValueError("Une caractéristique est constante : revoir la sélection.")
    if len(np.unique(values, axis=0)) < 5:
        raise ValueError("Pas assez de profils distincts pour comparer 2, 3 et 4 groupes.")
    data.insert(0, "activity_id", [f"A{i + 1:02d}" for i in range(len(data))])
    # Un seul thread suffit pour ce petit lot et évite des coûts inutiles.
    with threadpool_limits(limits=1):
        scores, stability, fitted = compare_choices(values, data["filename"].tolist(), [2, 3, 4])
    scaler, scaled, model, labels = fitted[args.k]
    assignments = data[["activity_id", "filename", "start_utc"] + FEATURES].copy()
    assignments["group"] = labels + 1
    for k, (_, _, _, partition) in fitted.items():
        assignments[f"group_k{k}"] = partition + 1
    centers = pd.DataFrame(scaler.inverse_transform(model.cluster_centers_), columns=FEATURES)
    centers.insert(0, "group", range(1, args.k + 1))
    centers["n_activities"] = np.bincount(labels, minlength=args.k)
    args.output.mkdir(parents=True, exist_ok=True)
    assignments.to_csv(args.output / "assignments.csv", index=False, encoding="utf-8-sig")
    scores.to_csv(args.output / "k_comparison.csv", index=False)
    stability.to_csv(args.output / "leave_one_out.csv", index=False)
    centers.to_csv(args.output / "group_profiles.csv", index=False)
    standardized = pd.DataFrame(scaled, columns=FEATURES)
    standardized.insert(0, "activity_id", data["activity_id"])
    standardized.to_csv(args.output / "standardized_features.csv", index=False)
    plt.switch_backend("Agg")
    save_plots(data, scaled, labels, args.k, args.output)
    config = {"features": FEATURES, "selected_k": args.k, "candidates": [2, 3, 4], "seed": SEED,
              "n_init": N_INIT, "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
              "scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist(),
              "versions": {"scikit-learn": sklearn.__version__, "numpy": np.__version__,
                           "pandas": pd.__version__, "matplotlib": matplotlib.__version__}}
    (args.output / "experiment.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    lines = ["# SessionDNA — Première expérience de clustering", "",
        f"**{len(data)} activités ; {args.k} groupes affichés.** Les essais à 2, 3 et 4 groupes sont tous sauvegardés.", "",
        "Le choix affiché est exploratoire et fixé par --k (3 par défaut), pas une vérité sportive ni un optimum automatique.", "",
        "## Méthode", "",
        "1. Retenir durée chronométrée, vitesse moyenne et variation relative de vitesse (CV).",
        "2. Standardiser chaque colonne : (valeur - moyenne) / écart-type, calculés sur le lot.",
        "3. K-means rapproche les profils dans cet espace à trois dimensions ; 30 initialisations, graine 42.",
        "4. Comparer la silhouette pour 2, 3 et 4 groupes et refaire les partitions après retrait de chaque séance.",
        "5. Interpréter les profils en unités d'origine. Les identifiants, dates et descriptions ne sont pas utilisés comme caractéristiques.", "",
        "## Comparaison des nombres de groupes", "", "```text", scores.round(3).to_string(index=False), "```", "",
        "Silhouette : séparation/compacité interne, de -1 à 1, pas un taux de réussite. Une valeur plus élevée favorise des groupes mieux séparés selon ces caractéristiques.",
        "ARI après retrait : compare la partition des séances restantes à celle du lot complet ; 1 = même regroupement malgré les numéros de groupes, 0 ≈ accord attendu par hasard. La standardisation est réapprise à chaque retrait.",
        "Ce test de sensibilité ne mesure pas une performance sur de nouvelles séances et n'est pas une validation supervisée.", "",
        "## Profils des groupes (unités d'origine)", "", "```text", centers.round(3).to_string(index=False), "```", "",
        "Les numéros de groupes sont arbitraires. Les noms endurance, seuil ou VO2max ne sont pas prédits.", "",
        "## Attribution des activités", "",
        "| Repère | Date UTC | Fichier | Groupe |", "|---|---|---|---:|"]
    for row in assignments.itertuples():
        lines.append(f"| {row.activity_id} | {row.start_utc:%d/%m/%Y %H:%M} | {row.filename} | {row.group} |")
    lines += ["", "![Groupes](clusters.png)", "", "![Standardisation](standardized_features.png)", "",
        "## Limites", "",
        "- Petit échantillon d'un seul sportif ; ne pas généraliser ces groupes à d'autres sportifs ou à tous les types d'entraînement.",
        "- K-means impose un nombre de groupes et privilégie des groupes compacts dans une distance euclidienne.",
        "- Les groupes dépendent du choix des variables et de leur mise à l'échelle ; certaines variables peuvent rester corrélées.",
        "- La distance est laissée de côté pour ne pas répéter durée et vitesse. Fréquence cardiaque et puissance restent disponibles pour une analyse ultérieure.",
        "- StandardScaler reste sensible aux valeurs extrêmes. Aucune suppression de pics, pondération temporelle ou reconstitution des pauses ici.",
        "- Le CV ne capture pas l'ordre ni le nombre des intervalles. Ces groupes ne constituent pas des étiquettes fiables pour entraîner un classifieur.",
        "- Tout le lot sert à l'exploration ; pas de mesure hors échantillon, pas de probabilité de confiance, pas de modèle de production sauvegardé.",
        "- Une stabilité parfaite sur les retraits de ce petit lot ne prouve pas une stabilité sur de futures données.", "",
        "Sources : [K-means](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html), "
        "[StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html), "
        "[silhouette](https://scikit-learn.org/stable/auto_examples/cluster/plot_kmeans_silhouette_analysis), "
        "[ARI](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.adjusted_rand_score.html)."]
    (args.output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(scores.round(3).to_string(index=False))
    print("\nProfils pour k =", args.k)
    print(centers.round(3).to_string(index=False))
    print(f"\nRésultats : {args.output.resolve()}")


if __name__ == "__main__":
    main()
