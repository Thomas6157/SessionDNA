"""Schéma d'annotation sportif : intention, format et contexte restent distincts."""
OBJECTIVES={'recuperation':'Récupération','ef':'Footing / EF','endurance_soutenue':'Endurance soutenue','seuil':'Seuil','vo2max':'VO₂max','vitesse':'Vitesse / sprints','competition':'Compétition','autre':'Autre','incertain':'Incertain'}
FORMATS={'continu':'Continu','progressif':'Progressif','intervalles_courts':'Intervalles courts','intervalles_longs':'Intervalles longs','mixte':'Mixte','incertain':'Incertain'}
TAGS={'sortie_longue':'Sortie longue','brick_run':'Enchaînement après vélo (brick run)','cotes':'Côtes'}

def validate_sports(payload, dataset_id, filenames):
    if payload.get('schema_version')!=2 or payload.get('dataset_id')!=dataset_id:
        raise ValueError('Version ou lot incompatible.')
    if not isinstance(payload.get('annotations'),list): raise ValueError('Liste annotations requise.')
    seen=set()
    for row in payload['annotations']:
        name=row.get('filename')
        if name not in filenames or name in seen: raise ValueError('Séance inconnue ou dupliquée.')
        seen.add(name)
        if row.get('objective','') not in ['',*OBJECTIVES] or row.get('format','') not in ['',*FORMATS]: raise ValueError('Objectif ou format inconnu.')
        tags=row.get('tags',{})
        if not isinstance(tags,dict) or any(k not in TAGS or v not in ['','oui','non','incertain'] for k,v in tags.items()): raise ValueError('Caractéristique invalide.')
        if row.get('legacy_label','') not in ['','reguliere','progressive','intervalles','autre','incertain']: raise ValueError('Ancienne annotation invalide.')
        if not isinstance(row.get('notes',''),str): raise ValueError('Note invalide.')
    return payload['annotations']
