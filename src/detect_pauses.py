"""Comparer le détecteur v1 à une version qui interprète les pauses du chronomètre."""
from pathlib import Path
import argparse
import hashlib
import json
import fitdecode
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from detect_intervals import read_speed, detect, PARAMETERS, reference_masks, score, runs

RULES = dict(max_pause_s=180, max_transition_s=10, max_unknown_s=2, max_speed_ratio=1.20,
             min_interval_s=120, matching_iou=.5)


def read_events(path):
    events = []
    with fitdecode.FitReader(path) as fit:
        for msg in fit:
            if isinstance(msg, fitdecode.FitDataMessage) and msg.name == 'event' and msg.get_value('event', fallback=None) == 'timer':
                events.append(dict(timestamp=msg.get_value('timestamp', fallback=None),
                                   event_type=msg.get_value('event_type', fallback=None)))
    return pd.DataFrame(events, columns=['timestamp', 'event_type'])


def pair_pauses(events):
    """Un arrêt devient une pause seulement si une reprise suit. Fin finale exclue."""
    pauses, issues = [], []
    if events.empty:
        return pd.DataFrame(columns=['start_utc', 'end_utc', 'duration_s']), ['Événements timer absents.']
    events = events.copy()
    events.timestamp = pd.to_datetime(events.timestamp, utc=True, errors='coerce')
    if events.timestamp.isna().any() or not events.timestamp.is_monotonic_increasing:
        raise ValueError('Événements timer invalides ou désordonnés.')
    state, stopped = None, None
    for row in events.itertuples():
        if row.event_type == 'start':
            if state == 'stopped':
                duration = (row.timestamp-stopped).total_seconds()
                if duration > 0:
                    pauses.append(dict(start_utc=stopped, end_utc=row.timestamp, duration_s=duration))
            elif state == 'running':
                issues.append('Deux démarrages successifs : vérifier les événements.')
            state, stopped = 'running', None
        elif row.event_type in ('stop', 'stop_all'):
            if state == 'running':
                state, stopped = 'stopped', row.timestamp
            else:
                issues.append('Arrêt sans démarrage associé : non interprété.')
                state, stopped = None, None
        else:
            issues.append(f'Événement non pris en charge : {row.event_type}.')
            state, stopped = None, None
    return pd.DataFrame(pauses, columns=['start_utc', 'end_utc', 'duration_s']), sorted(set(issues))


def pause_mask(index, pauses):
    mask = np.zeros(len(index), dtype=bool)
    for row in pauses.itertuples():
        mask |= (index >= row.start_utc) & (index < row.end_utc)
    return mask


def detect_with_pauses(speed, pauses):
    """Joindre sous conditions des fragments rapides ; jamais utiliser les étapes Garmin."""
    masked = speed.copy()
    masked.loc[pause_mask(masked.index, pauses)] = np.nan
    # On diffère le filtre de durée pour récupérer un fragment court après une pause.
    signal, candidates, settings = detect(masked, {**PARAMETERS, 'min_interval_s': 1})
    paused = pause_mask(signal.index, pauses)
    groups, decisions = [], []
    for candidate in candidates.to_dict('records'):
        merge = False
        if groups:
            previous = groups[-1]
            left, right = previous[-1]['end_utc'], candidate['start_utc']
            gap = (signal.index >= left) & (signal.index < right)
            inside_pauses = pauses.loc[(pauses.end_utc > left) & (pauses.start_utc < right)]
            nonpaused = gap & ~paused
            unknown = nonpaused & signal.speed_kmh.isna().to_numpy()
            # Comparer les vitesses des fragments de part et d'autre de la coupure.
            before = signal.loc[(signal.index >= previous[-1]['start_utc']) & (signal.index < left), 'smoothed_kmh'].tail(10).median()
            after = signal.loc[(signal.index >= right) & (signal.index < candidate['end_utc']), 'smoothed_kmh'].head(10).median()
            ratio = max(before, after)/min(before, after) if min(before, after) > 0 else np.inf
            merge = bool(len(inside_pauses) and inside_pauses.duration_s.sum() <= RULES['max_pause_s']
                and nonpaused.sum() <= RULES['max_transition_s'] and unknown.sum() <= RULES['max_unknown_s']
                and np.isfinite(ratio) and ratio <= RULES['max_speed_ratio'])
            if len(inside_pauses):
                decisions.append(dict(gap_start=left, gap_end=right, merged=merge,
                    pause_s=int((gap & paused).sum()), transition_s=int(nonpaused.sum()),
                    unknown_s=int(unknown.sum()), speed_ratio=ratio))
        if merge:
            groups[-1].append(candidate)
        else:
            groups.append([candidate])
    signal['paused'] = paused
    signal['predicted'] = False
    signal['logical_interval'] = 0
    intervals, fragments = [], []
    for group in groups:
        detected_s = sum(item['duration_s'] for item in group)
        if detected_s < RULES['min_interval_s']:
            continue
        identity = len(intervals)+1
        begin, end = group[0]['start_utc'], group[-1]['end_utc']
        span = (signal.index >= begin) & (signal.index < end)
        intervals.append(dict(interval=identity, start_utc=begin, end_utc=end,
            detected_s=detected_s, elapsed_s=(end-begin).total_seconds(),
            timer_span_s=int((span & ~paused).sum()), pause_s=int((span & paused).sum()),
            n_fragments=len(group), merge_hypothesis=len(group)>1))
        for item in group:
            mask = (signal.index >= item['start_utc']) & (signal.index < item['end_utc']) & ~paused
            signal.loc[mask, 'predicted'] = True
            signal.loc[mask, 'logical_interval'] = identity
            fragments.append(dict(interval=identity, **{k:v for k,v in item.items() if k != 'interval'}))
    return signal, pd.DataFrame(intervals, columns=['interval','start_utc','end_utc','detected_s','elapsed_s','timer_span_s','pause_s','n_fragments','merge_hypothesis']), pd.DataFrame(fragments, columns=['interval','start_utc','end_utc','duration_s']), pd.DataFrame(decisions, columns=['gap_start','gap_end','merged','pause_s','transition_s','unknown_s','speed_ratio']), settings


def match_intervals(signal, intervals, references, evaluated):
    """Appariement un-à-un glouton par IoU décroissante sur les secondes évaluables."""
    possibilities, matches = [], []
    for i, pred in enumerate(intervals.itertuples()):
        pmask = (signal.index >= pred.start_utc) & (signal.index < pred.end_utc) & evaluated
        for j, ref in enumerate(references.itertuples()):
            begin, end = pd.to_datetime(ref.start_utc, utc=True), pd.to_datetime(ref.end_utc, utc=True)
            rmask = (signal.index >= begin) & (signal.index < end) & evaluated
            union = int((pmask | rmask).sum())
            iou = int((pmask & rmask).sum())/union if union else 0
            if iou >= RULES['matching_iou']:
                possibilities.append((iou, i, j, (pred.start_utc-begin).total_seconds(), (pred.end_utc-end).total_seconds()))
    used_pred, used_ref = set(), set()
    for iou, i, j, start_error, end_error in sorted(possibilities, reverse=True):
        if i not in used_pred and j not in used_ref:
            used_pred.add(i); used_ref.add(j)
            matches.append(dict(predicted_interval=i+1, reference_block=int(references.iloc[j]['block']),
                iou=iou, start_error_s=start_error, end_error_s=end_error))
    return pd.DataFrame(matches, columns=['predicted_interval','reference_block','iou','start_error_s','end_error_s'])


def draw(signal, old, intervals, fragments, refs, pauses, start, name, output):
    fig, axes = plt.subplots(2,1,figsize=(12,7),sharex=True,gridspec_kw={'height_ratios':[3,1.7]})
    x=(signal.index-start).total_seconds()/60
    axes[0].plot(x,signal.speed_kmh,color='#96adbc',lw=.6,label='Vitesse hors pauses')
    axes[0].plot(x,signal.smoothed_kmh,color='#17618b',lw=1,label='Vitesse lissée')
    for row in pauses.itertuples():
        for ax in axes:
            ax.axvspan((row.start_utc-start).total_seconds()/60,(row.end_utc-start).total_seconds()/60,color='#888888',alpha=.22)
    for table,y,color in [(refs,2.2,'#d59433'),(old,1.2,'#a55f80'),(fragments,.2,'#218582')]:
        for row in table.itertuples():
            begin,end=pd.to_datetime(row.start_utc,utc=True),pd.to_datetime(row.end_utc,utc=True)
            axes[1].broken_barh([((begin-start).total_seconds()/60,(end-begin).total_seconds()/60)],(y,.6),facecolors=color)
    for row in intervals.itertuples():
        a,b=(row.start_utc-start).total_seconds()/60,(row.end_utc-start).total_seconds()/60
        axes[1].plot([a,b],[.12,.12],color='#165d5b',lw=1)
        axes[1].text((a+b)/2,-.02,f'B{row.interval}',ha='center',va='top',fontsize=8)
    axes[0].set_title(f'{name}\nPauses du chronomètre et regroupement prudent des fragments')
    axes[0].set_ylabel('Vitesse (km/h)'); axes[0].legend(fontsize=8); axes[0].grid(alpha=.2)
    axes[1].set_yticks([.5,1.5,2.5],['v2 avec pauses','v1 initiale','Référence FIT'])
    axes[1].set_ylim(-.4,3); axes[1].set_xlabel('Temps écoulé (minutes)'); axes[1].grid(axis='x',alpha=.2)
    fig.text(.5,.015,'Gris : chronomètre arrêté · B1, B2… : blocs proposés ; traits sous les fragments = regroupement hypothétique',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.035,1,1)); fig.savefig(output,dpi=140); plt.close(fig)


def main():
    project=Path(__file__).resolve().parent.parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw',type=Path,default=project/'data/raw')
    parser.add_argument('--features',type=Path,default=project/'data/processed/batch/running_features.csv')
    parser.add_argument('--reference',type=Path,default=project/'data/processed/structure')
    parser.add_argument('--baseline',type=Path,default=project/'data/processed/detection')
    parser.add_argument('--output',type=Path,default=project/'data/processed/detection_pauses')
    args=parser.parse_args(); args.output.mkdir(parents=True,exist_ok=True); plt.switch_backend('Agg')
    files=pd.read_csv(args.features).filename.tolist()
    if len(files)!=len(set(files)) or any(Path(f).name!=f for f in files): raise ValueError('Inventaire invalide.')
    rows=[]; manifests=[]
    for filename in files:
        print(filename,flush=True)
        folder=args.output/'activities'/Path(filename).stem; folder.mkdir(parents=True,exist_ok=True)
        try:
            path=args.raw/filename; speed,start=read_speed(path)
            events=read_events(path); pauses,issues=pair_pauses(events)
            # En présence d'événements incohérents, aucune fusion par pause n'est autorisée.
            usable_pauses=pauses if not issues else pauses.iloc[:0]
            original,old,_=detect(speed)
            signal,intervals,fragments,decisions,settings=detect_with_pauses(speed,usable_pauses)
            for table,name in [(events,'timer_events'),(pauses,'pauses'),(intervals,'intervals'),(fragments,'fragments'),(decisions,'merge_decisions')]: table.to_csv(folder/f'{name}.csv',index=False)
            signal.to_csv(folder/'signal.csv')
            ref_path=args.reference/'activities'/Path(filename).stem/'observed_blocks.csv'
            ref_blocks=pd.read_csv(ref_path)
            known,target,refs=reference_masks(signal.index,ref_blocks)
            active_known=known & ~signal.paused.to_numpy()
            v1=score(original,active_known,target); v2=score(signal,active_known,target)
            evaluated=active_known & signal.speed_kmh.notna().to_numpy()
            m1=match_intervals(signal,old,refs,evaluated); m2=match_intervals(signal,intervals,refs,evaluated)
            m1.to_csv(folder/'matches_v1.csv',index=False); m2.to_csv(folder/'matches_v2.csv',index=False)
            row=dict(filename=filename,status='ok',n_pauses=len(pauses),pause_s=pauses.duration_s.sum(),
                timer_issues=' | '.join(issues),n_reference=len(refs),n_v1=len(old),n_v2=len(intervals),
                matches_v1=len(m1),matches_v2=len(m2),merged_intervals=int(intervals.merge_hypothesis.sum()),
                unknown_missing_s=int((signal.speed_kmh.isna() & ~signal.paused).sum()),**settings)
            for label,metrics in [('v1',v1),('v2',v2)]: row.update({f'{label}_{k}':v for k,v in metrics.items()})
            for label,table in [('v1',m1),('v2',m2)]:
                row[f'{label}_start_mae_s']=table.start_error_s.abs().mean(); row[f'{label}_end_mae_s']=table.end_error_s.abs().mean()
            draw(signal,old,intervals,fragments,refs,usable_pauses,start,filename,folder/'comparison.png')
            manifests.append(dict(filename=filename,fit_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),reference_sha256=hashlib.sha256(ref_path.read_bytes()).hexdigest()))
            rows.append(row)
        except Exception as exc:
            rows.append(dict(filename=filename,status='error',timer_issues=f'{type(exc).__name__}: {exc}'))
    summary=pd.DataFrame(rows); summary.to_csv(args.output/'comparison.csv',index=False,encoding='utf-8-sig')
    eligible=summary.loc[summary.status.eq('ok') & summary.get('n_reference',pd.Series(0,index=summary.index)).gt(0)]
    totals={}
    for version in ['v1','v2']:
        tp,fp,fn=[int(eligible[f'{version}_{k}_s'].sum()) if len(eligible) else 0 for k in ['tp','fp','fn']]
        totals[version]=dict(tp_s=tp,fp_s=fp,fn_s=fn,precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,
            matched=int(eligible[f'matches_{version}'].sum()),predicted=int(eligible[f'n_{version}'].sum()),reference=int(eligible.n_reference.sum()))
    baseline_manifest=json.loads((args.baseline/'experiment.json').read_text(encoding='utf-8'))
    used={entry['fit_sha256'] for entry in baseline_manifest['input_files']}
    unseen=[p.name for p in args.raw.glob('*.fit') if hashlib.sha256(p.read_bytes()).hexdigest() not in used]
    experiment=dict(rules=RULES,detector_parameters=PARAMETERS,totals=totals,eligible_sessions=len(eligible),
        input_files=manifests,files_not_in_v1_manifest=unseen,
        evaluation='Comparaison sur le lot de développement connu ; fichiers hors manifeste à trier par sport avant tout test indépendant.')
    (args.output/'experiment.json').write_text(json.dumps(experiment,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Détection v2 — Pauses du chronomètre','',f'{len(summary)} courses examinées ; {int(summary.status.eq("error").sum())} erreurs.','',
        'Les arrêts suivis de reprises définissent des pauses confirmées. Un arrêt final sans reprise ne devient pas une pause. Les événements incohérents désactivent la fusion pour la séance. Les trous inexpliqués restent distincts.', '',
        '## Méthode','',
        'Même détecteur de vitesse que v1, mais vitesses pendant les pauses exclues. Le filtre de 120 s est appliqué après regroupement des fragments. Fusion hypothétique seulement si pause confirmée ≤ 180 s, transition hors pause ≤ 10 s, au plus 2 s de mesures manquantes hors pause et vitesses de bord dans un rapport ≤ 1,20. Aucun programme Garmin en entrée. Ces paramètres sont des choix de développement, pas une preuve que les deux fragments appartiennent au même effort.', '',
        'Les pauses restent vides sur le signal. Un groupe peut contenir plusieurs fragments : les minutes d’arrêt ne sont pas comptées comme de l’effort. timer_span_s mesure la durée entre les bornes hors pauses connues ; detected_s somme les fragments rapides.', '',
        '## Avant / après sur les mêmes secondes évaluables','',f'{len(eligible)} séances avec références longues. Les deux versions sont évaluées hors pauses confirmées et hors secondes sans mesure. Les scores v1 recalculés ici peuvent donc différer du rapport historique.', '',
        '| Version | Précision temporelle | Rappel temporel | Blocs proposés | Appariements / références |','|---|---:|---:|---:|---:|']
    for name,t in totals.items():
        lines.append(f"| {name} | {t['precision']:.1%} | {t['recall']:.1%} | {t['predicted']} | {t['matched']} / {t['reference']} |" if t['precision'] is not None and t['recall'] is not None else f'| {name} | — | — | {t["predicted"]} | {t["matched"]} / {t["reference"]} |')
    lines+=['','Appariement un-à-un glouton par recouvrement IoU décroissant, seuil 0,5. IoU = secondes communes / secondes de l’union, sur le domaine évaluable. Les écarts de début/fin sont en temps écoulé UTC, pour les seules paires appariées. Ils sont exportés dans matches_v1.csv et matches_v2.csv. Un appariement n’est pas une validation sportive.', '',
        '## Séances','', '| Fichier | Pauses | Blocs v1 → v2 | Références | Événements à vérifier |','|---|---:|---:|---:|---|']
    for row in summary.to_dict('records'):
        name=row['filename']; stem=Path(name).stem
        lines.append(f"| [{name}](activities/{stem}/comparison.png) | {row.get('n_pauses','—')} | {row.get('n_v1','—')} → {row.get('n_v2','—')} | {row.get('n_reference','—')} | {row.get('timer_issues','')} |")
    for name in ['24398594261_ACTIVITY','24311406124_ACTIVITY']:
        if (args.output/'activities'/name/'comparison.png').exists(): lines+=['',f'## Exemple {name}','',f'![Comparaison](activities/{name}/comparison.png)']
    lines+=['','## Limites et prochain test','',
        'Le regroupement est une hypothèse explicite, pas une mesure de continuité physiologique. Une récupération montre arrêtée peut ressembler à une interruption au milieu d’un effort. Les seuils sont fixés pour cette version, développée après examen de ces séances : aucun résultat de généralisation indépendant.', '',
        f'{len(unseen)} fichiers FIT locaux ne figurent pas dans le manifeste v1. Cela ne garantit pas de nouvelles courses : il faut vérifier leur sport et leur historique avant de constituer un jeu de test.', '',
        'Conserver cette version et ses paramètres avant de regarder de nouvelles courses. Ne pas mélanger aléatoirement les secondes d’une même séance entre apprentissage et test. Les anciens résultats sont conservés dans detection/.', '',
        'Sources : [événements et durées FIT](https://developer.garmin.com/fit/articles/file-types/activity.html).']
    (args.output/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(totals)); print(summary.status.value_counts().to_string())
    if summary.status.eq('error').any(): raise SystemExit(1)


if __name__=='__main__': main()
