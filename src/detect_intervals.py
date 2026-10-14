"""Détecter des passages rapides prolongés par des règles, puis comparer aux étapes FIT."""

from pathlib import Path
import argparse
import hashlib
import json

import fitdecode
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# Première référence simple, définie avant d'examiner ses scores. Pas d'optimisation sur le lot.
PARAMETERS = dict(smoothing_s=15, min_samples=7, baseline_quantile=0.25,
                  moving_min_kmh=5.0, relative_increase=1.18, absolute_increase_kmh=1.5,
                  bridge_s=15, min_interval_s=120)
INTERVAL_COLUMNS = ['interval', 'start_utc', 'end_utc', 'duration_s']


def read_speed(path):
    """Ne lire ni lap, ni workout_step : la détection reçoit uniquement les mesures."""
    rows, starts, sports = [], [], []
    with fitdecode.FitReader(path) as fit:
        for msg in fit:
            if not isinstance(msg, fitdecode.FitDataMessage):
                continue
            if msg.name == 'session':
                starts.append(msg.get_value('start_time', fallback=None))
                sports.append(msg.get_value('sport', fallback=None))
            elif msg.name == 'record':
                speed = msg.get_value('enhanced_speed', fallback=None)
                if speed is None:
                    speed = msg.get_value('speed', fallback=None)
                rows.append((msg.get_value('timestamp', fallback=None),
                             speed * 3.6 if speed is not None else np.nan))
    if sports != ['running']:
        raise ValueError('Une unique session de course est attendue.')
    frame = pd.DataFrame(rows, columns=['timestamp', 'speed_kmh'])
    frame['timestamp'] = pd.to_datetime(frame.timestamp, utc=True, errors='coerce')
    if frame.empty or frame.timestamp.isna().any() or not frame.timestamp.is_monotonic_increasing or frame.timestamp.duplicated().any():
        raise ValueError('Horodatages absents, dupliqués ou désordonnés.')
    start = pd.to_datetime(starts[0], utc=True)
    if pd.isna(start):
        raise ValueError('Début de session absent.')
    return frame.set_index('timestamp').speed_kmh, start


def runs(mask):
    """Bornes [début, fin exclue] des plages True sur une grille à une seconde."""
    edges = np.diff(np.r_[False, np.asarray(mask, dtype=bool), False].astype(int))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def detect(speed, params=None):
    """Fonction pure : aucune entrée Garmin de programme et aucun accès aux fichiers."""
    p = PARAMETERS if params is None else params
    if not isinstance(speed.index, pd.DatetimeIndex) or speed.empty or speed.index.hasnans or not speed.index.is_monotonic_increasing or speed.index.has_duplicates:
        raise ValueError('Série temporelle non vide et strictement croissante requise.')
    if speed.index[-1] - speed.index[0] > pd.Timedelta(days=1):
        raise ValueError('Session dépassant un jour : vérifier avant rééchantillonnage.')
    numeric = pd.to_numeric(speed, errors='coerce')
    numeric = numeric.where(np.isfinite(numeric) & numeric.ge(0))
    # Les secondes absentes restent NaN : on ne fabrique aucune vitesse pendant les trous.
    raw = numeric.resample('1s').median()
    smooth = pd.Series(np.nan, index=raw.index)
    for left, right in runs(raw.notna()):
        smooth.iloc[left:right] = raw.iloc[left:right].rolling(
            f"{p['smoothing_s']}s", center=True, min_periods=p['min_samples']).median()
    moving = smooth[smooth > p['moving_min_kmh']]
    baseline = float(moving.quantile(p['baseline_quantile'])) if len(moving) else np.nan
    threshold = max(baseline * p['relative_increase'], baseline + p['absolute_increase_kmh']) if np.isfinite(baseline) else np.nan
    above = smooth.ge(threshold).to_numpy()
    joined = above.copy()
    for left, right in runs(~above):
        bounded = left > 0 and right < len(above)
        usable = raw.iloc[left:right].notna().all() and smooth.iloc[left:right].gt(p['moving_min_kmh']).all()
        if bounded and right - left <= p['bridge_s'] and usable:
            joined[left:right] = True
    predicted = np.zeros(len(raw), dtype=bool)
    intervals = []
    for left, right in runs(joined):
        if right - left >= p['min_interval_s']:
            predicted[left:right] = True
            intervals.append(dict(interval=len(intervals) + 1, start_utc=raw.index[left],
                end_utc=raw.index[right - 1] + pd.Timedelta(seconds=1), duration_s=right-left))
    signal = pd.DataFrame(dict(speed_kmh=raw, smoothed_kmh=smooth, above_threshold=above, predicted=predicted))
    signal.index.name = 'timestamp'
    return signal, pd.DataFrame(intervals, columns=INTERVAL_COLUMNS), dict(baseline_kmh=baseline, threshold_kmh=threshold)


def reference_masks(index, blocks):
    """Référence partielle : étapes liées, non ambiguës ; répétitions actives >= 120 s."""
    known, target = np.zeros(len(index), dtype=bool), np.zeros(len(index), dtype=bool)
    references = []
    if blocks.empty:
        return known, target, blocks.copy()
    required = {'linked', 'ambiguous_fragmentation', 'repeated_active', 'timer_s', 'start_utc', 'end_utc'}
    if not required.issubset(blocks.columns):
        raise ValueError('Référence incomplète : relancer analyze_structure.py.')
    blocks = blocks.copy()
    for column in ['linked', 'ambiguous_fragmentation', 'repeated_active']:
        converted = blocks[column].astype(str).str.lower().map({'true': True, 'false': False})
        if converted.isna().any():
            raise ValueError(f'Booléen invalide dans {column}.')
        blocks[column] = converted
    for row in blocks.itertuples():
        if not row.linked or row.ambiguous_fragmentation:
            continue
        begin, end = pd.to_datetime(row.start_utc, utc=True), pd.to_datetime(row.end_utc, utc=True)
        if pd.isna(begin) or pd.isna(end) or end < begin:
            raise ValueError('Bornes de référence invalides.')
        inside = (index >= begin) & (index < end)
        known |= inside
        if row.repeated_active and row.timer_s >= PARAMETERS['min_interval_s']:
            target |= inside
            references.append(row._asdict())
    return known, target, pd.DataFrame(references)


def score(signal, known, target):
    evaluated = known & signal.speed_kmh.notna().to_numpy()
    pred = signal.predicted.to_numpy()
    tp = int((evaluated & pred & target).sum())
    fp = int((evaluated & pred & ~target).sum())
    fn = int((evaluated & ~pred & target).sum())
    return dict(evaluated_s=int(evaluated.sum()), tp_s=tp, fp_s=fp, fn_s=fn,
        precision=tp/(tp+fp) if tp+fp else np.nan,
        recall=tp/(tp+fn) if tp+fn else np.nan,
        f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else np.nan)


def plot_result(signal, intervals, references, start, settings, filename, destination):
    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    x = (signal.index-start).total_seconds()/60
    axes[0].plot(x, signal.speed_kmh, color='#a6b7c1', lw=.65, label='Vitesse brute')
    axes[0].plot(x, signal.smoothed_kmh, color='#246b93', lw=1, label='Médiane sur 15 s')
    if np.isfinite(settings['threshold_kmh']):
        axes[0].axhline(settings['threshold_kmh'], color='#905bb4', ls='--', lw=1, label='Seuil de détection')
    for table, y, color in [(intervals, .05, '#267daa'), (references, 1.1, '#d59030')]:
        for row in table.itertuples():
            begin, end = pd.to_datetime(row.start_utc, utc=True), pd.to_datetime(row.end_utc, utc=True)
            axes[1].broken_barh([((begin-start).total_seconds()/60, (end-begin).total_seconds()/60)],
                                (y, .8), facecolors=color)
    axes[0].set_title(f'{filename}\nPassages rapides détectés depuis la vitesse — règles v1')
    axes[0].set_ylabel('Vitesse (km/h)')
    axes[0].legend(loc='upper left', fontsize=8, ncol=3)
    axes[0].grid(alpha=.2)
    axes[1].set_yticks([.45, 1.5], ['Détection', 'Référence FIT'])
    axes[1].set_ylim(-.1, 2.1)
    axes[1].set_xlabel('Minutes écoulées depuis le début de la session')
    axes[1].grid(axis='x', alpha=.2)
    fig.text(.5, .012, 'Référence : répétitions actives enregistrées ≥ 2 min · Ni zone physiologique ni vérité exhaustive', ha='center', fontsize=8)
    fig.tight_layout(rect=(0, .035, 1, 1))
    fig.savefig(destination, dpi=140)
    plt.close(fig)


def main():
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, default=project/'data/raw')
    parser.add_argument('--features', type=Path, default=project/'data/processed/batch/running_features.csv')
    parser.add_argument('--reference', type=Path, default=project/'data/processed/structure')
    parser.add_argument('--output', type=Path, default=project/'data/processed/detection')
    args = parser.parse_args()
    files = pd.read_csv(args.features).filename.tolist()
    if not files or len(files) != len(set(files)) or any(not isinstance(f, str) or Path(f).name != f for f in files):
        raise ValueError('Inventaire vide ou noms de fichiers invalides/dupliqués.')
    args.output.mkdir(parents=True, exist_ok=True)
    plt.switch_backend('Agg')
    summaries, coverage_rows, manifest = [], [], []
    for filename in files:
        print(f'Détection : {filename}', flush=True)
        row = dict(filename=filename, status='ok', reference_status='missing', notes='')
        try:
            raw_path = args.raw/filename
            speed, start = read_speed(raw_path)
            signal, intervals, settings = detect(speed)
            folder = args.output/'activities'/Path(filename).stem
            folder.mkdir(parents=True, exist_ok=True)
            # Enregistrer les prédictions AVANT d'ouvrir la référence Garmin.
            intervals.to_csv(folder/'detected_intervals.csv', index=False)
            signal.to_csv(folder/'signal.csv', index=True)
            row.update(settings, n_detected=len(intervals), detected_s=int(intervals.duration_s.sum()),
                       observed_s=int(signal.speed_kmh.notna().sum()), missing_s=int(signal.speed_kmh.isna().sum()))
            ref_path = args.reference/'activities'/Path(filename).stem/'observed_blocks.csv'
            manifest.append(dict(filename=filename, fit_sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                reference_sha256=hashlib.sha256(ref_path.read_bytes()).hexdigest() if ref_path.exists() else None))
            known, target = np.zeros(len(signal), dtype=bool), np.zeros(len(signal), dtype=bool)
            references = pd.DataFrame()
            if ref_path.exists():
                try:
                    blocks = pd.read_csv(ref_path)
                    known, target, references = reference_masks(signal.index, blocks)
                    row['reference_status'] = 'available' if known.any() else 'unusable'
                    row.update(score(signal, known, target), n_reference=len(references))
                    for ref in references.itertuples():
                        begin, end = pd.to_datetime(ref.start_utc, utc=True), pd.to_datetime(ref.end_utc, utc=True)
                        mask = (signal.index >= begin) & (signal.index < end) & signal.speed_kmh.notna()
                        count = int(mask.sum())
                        coverage_rows.append(dict(filename=filename, block=ref.block, start_utc=begin, end_utc=end,
                            observed_s=count, covered_s=int(signal.loc[mask, 'predicted'].sum()),
                            coverage=float(signal.loc[mask, 'predicted'].mean()) if count else np.nan))
                except Exception as exc:
                    row.update(reference_status='error', notes=f'{type(exc).__name__}: {exc}')
            pd.DataFrame(dict(timestamp=signal.index, reference_known=known, reference_target=target)).to_csv(folder/'reference_mask.csv', index=False)
            plot_result(signal, intervals, references, start, settings, filename, folder/'comparison.png')
        except Exception as exc:
            row.update(status='error', notes=f'{type(exc).__name__}: {exc}')
        summaries.append(row)
    summary = pd.DataFrame(summaries)
    summary.to_csv(args.output/'detection_summary.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(coverage_rows).to_csv(args.output/'reference_coverage.csv', index=False)
    # Seules les séances avec une référence positive contribuent au bilan principal.
    eligible = summary.loc[summary.status.eq('ok') & summary.reference_status.eq('available') & summary.get('n_reference', pd.Series(0, index=summary.index)).gt(0)]
    totals = {key: int(eligible[key].sum()) if key in eligible else 0 for key in ['tp_s', 'fp_s', 'fn_s']}
    tp, fp, fn = [totals[key] for key in ['tp_s', 'fp_s', 'fn_s']]
    aggregate = dict(sessions=len(eligible), **totals, precision=tp/(tp+fp) if tp+fp else None,
                     recall=tp/(tp+fn) if tp+fn else None, f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None)
    (args.output/'experiment.json').write_text(json.dumps(dict(parameters=PARAMETERS, aggregate=aggregate,
        evaluation='Exploratoire sur le lot déjà connu, référence partielle ; aucun test indépendant.',
        offline=True, input_files=manifest), ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# SessionDNA — Première détection depuis la vitesse', '',
        f"{len(summary)} courses examinées ; {int(summary.status.eq('error').sum())} erreurs de détection ; {int(summary.reference_status.eq('error').sum())} erreurs de lecture des références.", '',
        '## Ce que cherche cette version', '',
        'Des passages sensiblement plus rapides que la base de la séance, durant au moins deux minutes. La détection ne lit ni les tours, ni les étapes du programme. Elle ne prédit pas une zone physiologique et ne cherche pas les accélérations brèves.', '',
        '## Règles fixées pour cette expérience', '',
        'Grille à une seconde, trous conservés. Médiane centrée sur 15 secondes, au moins 7 mesures, sans traverser les trous. Base = quantile 25 % des vitesses lissées supérieures à 5 km/h. Seuil = maximum(base × 1,18 ; base + 1,5 km/h). On rejoint les baisses de 15 s maximum uniquement si les mesures restent présentes et la vitesse lissée dépasse 5 km/h. On conserve les blocs de 120 s minimum.', '',
        'Ces paramètres sont des choix de départ, pas des constantes universelles. Le calcul utilise toute la séance et des points futurs : analyse après la course, pas alerte en direct.', '',
        '## Comparaison avec les métadonnées', '',
        f"Bilan sur **{len(eligible)} séances avec au moins une répétition active enregistrée de deux minutes ou plus**, en excluant les étapes fragmentées ambiguës et les secondes sans mesure. La référence est imparfaite et ne décrit pas tous les efforts possibles.", '']
    for key, title in [('precision', 'Précision temporelle'), ('recall', 'Rappel temporel'), ('f1', 'F1 temporel')]:
        value = aggregate[key]
        lines.append(f'- {title} : {value:.1%}.' if value is not None else f'- {title} : non défini.')
    lines += ['', 'Précision = secondes détectées recouvrant la référence / secondes détectées évaluables. Rappel = secondes de référence retrouvées / secondes de référence observées. Les durées sont cumulées sur ces séances : les longs blocs pèsent davantage. Un score temporel élevé ne garantit pas le bon nombre de blocs.', '',
        '**Évaluation exploratoire sur des séances déjà examinées. Aucun jeu de test indépendant et aucune conclusion de généralisation.** Les séances sans répétition enregistrée ne sont pas des négatifs sportifs validés ; leurs détections restent à examiner.', '',
        '## Séances', '', '| Séance | Blocs détectés | Blocs de référence | Précision | Rappel |', '|---|---:|---:|---:|---:|']
    for item in summary.to_dict('records'):
        name = item['filename']
        link = f"[{name}](activities/{Path(name).stem}/comparison.png)" if item['status'] == 'ok' else name
        def pct(key):
            value = item.get(key, np.nan)
            return f'{value:.1%}' if pd.notna(value) and item.get('n_reference', 0) > 0 else '—'
        lines.append(f"| {link} | {item.get('n_detected', '—')} | {item.get('n_reference', '—')} | {pct('precision')} | {pct('recall')} |")
    reference_name = '24311406124_ACTIVITY.fit'
    if reference_name in files:
        lines += ['', '## Exemple connu : deux fois quinze minutes', '',
                  f'![Comparaison sur la séance repère](activities/{Path(reference_name).stem}/comparison.png)', '',
                  'Comparer les débuts et les fins des deux frises. Des durées voisines peuvent cacher un léger décalage des frontières. Les accélérations brèves ne sont pas recherchées.']
    fragmented = eligible.loc[eligible.n_detected > eligible.n_reference] if len(eligible) else pd.DataFrame()
    if not fragmented.empty:
        example = fragmented.iloc[0]
        lines += ['', '## Un cas où le nombre de blocs diffère', '',
                  f"{example.filename} : {int(example.n_detected)} blocs détectés pour {int(example.n_reference)} blocs enregistrés de référence.", '',
                  f'![Exemple à examiner](activities/{Path(example.filename).stem}/comparison.png)', '',
                  'Examiner les trous de données et les passages sous le seuil. Les scores de durée excluent les secondes sans mesure et peuvent rester élevés malgré une fragmentation : ils ne suffisent pas à valider le découpage.']
    lines += ['', '## Limites à examiner', '',
        '- Un échauffement progressif ou une descente peut être détecté sans appartenir aux répétitions du programme.',
        '- Une séance rapide et uniforme, des côtes ou des récupérations rapides peuvent échapper à cette règle relative de vitesse.',
        '- Une pause coupe la détection ; aucune vitesse ne remplit un trou de données.',
        '- Le programme enregistré sert uniquement à évaluer après la détection. Il ne fournit aucun seuil au détecteur.',
        '- Avant une optimisation ou un apprentissage, réserver de nouvelles séances pour une évaluation indépendante.', '',
        '## Fichiers', '', '`detected_intervals.csv` : bornes UTC et durée des blocs. `signal.csv` : étapes du calcul. `reference_mask.csv` : référence séparée. `reference_coverage.csv` : couverture de chaque bloc de référence. `experiment.json` : paramètres, scores et empreintes des sources.', '',
        'Sources : [fenêtres temporelles pandas](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.rolling.html), [métriques scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html).']
    (args.output/'report.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(aggregate, ensure_ascii=False))
    print(summary.status.value_counts().to_string())
    if summary.status.eq('error').any():
        raise SystemExit(1)


if __name__ == '__main__':
    main()
