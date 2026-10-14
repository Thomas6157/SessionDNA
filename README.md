# SessionDNA — ton carnet triathlon personnel

SessionDNA réunit tes activités Garmin, ton programme IRON MAN, tes cours et tes retours. Il aide à comprendre les séances et à préparer le bilan de la semaine. C’est aussi ton projet d’apprentissage en DIA.

## Ouvrir l’application

Dans le dossier SessionDNA, double-clique sur **Lancer-SessionDNA.cmd**, puis ouvre **http://127.0.0.1:8765**. Garde la fenêtre du serveur ouverte. Aucun besoin de réactiver l’environnement à la main.

Ou, depuis PowerShell dans le projet :

```powershell
.\.venv\Scripts\python.exe src/serve_sessiondna.py
```

Le serveur est privé et écoute sur le PC. Pour le téléphone, utiliser l’adresse HTTPS privée une fois Tailscale Serve configuré, puis Safari → Partager → Sur l’écran d’accueil. `127.0.0.1` sur l’iPhone désigne l’iPhone, pas le PC. L’essai sur l’iPhone reste à réaliser.

## Ce que tu peux faire

| Écran | Utilité |
|---|---|
| Aujourd’hui | Séances du programme sélectionné, cours, volume et ressenti du jour. |
| Semaine | Blocs détaillés, horaires, marges de transport, conflits et retours par séance. |
| Activités | Historique filtrable, courbes, annotations, pauses, segmentation et tracés GPS. |
| Bilan | Faits sourcés, informations manquantes et rapport Markdown à envoyer dans IRON MAN. |
| Réglages | Imports FIT / JSON / ICS, actualisation Garmin, contraintes et sauvegardes. |

Le parcours recommandé : importer la semaine → vérifier les contraintes → placer les séances → remplir les retours → exporter le bilan. L’envoi dans la conversation IRON MAN reste manuel.

## Où nous en sommes

La V2 comprend une interface React, une API FastAPI et une sauvegarde SQLite avec détection des conflits entre appareils. Les analyses ajoutent DuckDB/Parquet, une segmentation par ruptures, des explications SHAP et un archivage local MLflow du modèle existant.

Le modèle de course reste exploratoire : **20 séances d’apprentissage, 8 de test, 7 réponses correctes**, sur les classes disponibles. Ce petit test ne prouve pas une fiabilité générale. Il n’existe pas encore de classifieur validé pour vélo et natation. Les annotations nouvelles ne réentraînent rien automatiquement.

Les programmes importés sont conservés avec leur empreinte. Le calendrier est un **export ICS**, pas une connexion continue à MyDevinci. Les horaires piscine enregistrés pour le 28 septembre au 4 octobre 2026 sont à revérifier pour les semaines suivantes. Les trains ne sont pas connectés en direct. L’IA générative est optionnelle et désactivée par défaut.

- [Guide : utiliser et comprendre la V2](docs/GUIDE_V2.md)
- [Dépôts intégrés et décision pour les 174 favoris](docs/INTEGRATIONS.md)
- [Compte rendu de validation](docs/VALIDATION_V2.md)
- [Historique du projet et des apprentissages](docs/history/README-avant-v2.md)
- [Résultats analytiques actuels](data/processed/analytics/report.md)

## Actualiser les activités

Le bouton dans Réglages permet de reconstruire les analyses et, si coché, d’importer Garmin avec la session locale existante. Il ne demande aucun secret dans le navigateur. Un import déjà en cours empêche le démarrage d’un second.

```powershell
.\.venv\Scripts\python.exe src/update_triathlon.py --sync --calendar-downloads
```

Les nouveaux `mon_calendrier*.ics` de Téléchargements sont importés lorsqu’ils existent. Il faut toujours les télécharger depuis MyDevinci. Retirer `--sync` pour travailler sans accéder à Garmin. Une connexion expirée se renouvelle localement avec `src/sync_garmin.py --login` ; aucun mot de passe ou jeton à envoyer dans la conversation.

## Reproduire et développer

Python 3.13 et Node.js 24+ sont nécessaires à la construction. La version construite de l’interface est déjà dans `app/dist` sur ce PC.

```powershell
# Dépendances Python verrouillées (uv installé)
uv sync --frozen --group dev
# Variante sans uv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# Interface : depuis app/
npm ci
npm test
npm run build

# Depuis la racine du projet
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src/sessiondna_api.py src/sessiondna_store.py src/sessiondna_analytics.py src/sessiondna_insights.py src/build_analytics.py
.\.venv\Scripts\python.exe src/build_analytics.py --register-model
```

`npm run dev` sert à développer ; pour l’usage personnel, utiliser le serveur Python et la version construite. Le registre MLflow et les analyses restent dans `data/processed/analytics`. Aucune commande ci-dessus ne réentraîne le modèle.

## Retrouver ses données

Les saisies sont conservées dans le navigateur et synchronisées vers `data/app_state/sessiondna.sqlite3`. La première ouverture reprend la sauvegarde historique `current.json` sans l’effacer. Les divergences sont présentées avant remplacement ; utiliser Réglages → Exporter mes saisies régulièrement.

L’archive serveur contient les saisies, programmes, calendriers et annotations exportables ; elle ne contient ni FIT bruts ni session Garmin. Les FIT restent dans `data/raw`. La sauvegarde précédant la V2 est dans `data/backups/before_v2_20260930T101329Z`.

La version précédente reste consultable à `/legacy/`. Elle a son propre stockage historique : éviter de saisir alternativement dans les deux versions. Son lancement dédié est `python src/serve_sessiondna.py --legacy`.
