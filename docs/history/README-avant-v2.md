# SessionDNA

Un carnet triathlon personnel pour importer, analyser et comprendre tes séances, tout en apprenant la data science.

## Réglages du 29 septembre

Sommeil proposé : **22 h 30–7 h**, fin des activités à 22 h (30 min avant le coucher). Ces valeurs remplissent les réglages de disponibilité vides, sans remplacer des réglages déjà saisis.

Les horaires du **bassin sportif du Centre aquatique de Levallois** sont vérifiés sur la page officielle au 29 septembre et intégrés au calcul des créneaux pour la semaine du 28 septembre au 4 octobre. Sortie de l'eau 30 min avant fermeture ; 15 min de vestiaire retenues avant la nage. Les horaires futurs restent à revérifier, notamment pendant les vacances. Source : https://www.ville-levallois.fr/sports-loisirs/centre-aquatique-de-levallois/

Tailscale est maintenant installé et connecté sur le PC ; un iPhone du même compte est enregistré. L'activation Serve/HTTPS demandée par Tailscale reste à terminer. L'origine privée est préparée dans `data/app_state/access.json` et sera reprise aux prochains lancements. Le serveur doit rester lancé sur le PC. Les durées de trajet et marges personnelles restent à renseigner avant de proposer les horaires sportifs.

## Actualisation et sauvegarde — état du 28 septembre au soir

- Historique actualisé : **411 activités**, soit 161 courses, 147 vélos, 101 natations et 2 randonnées. Sept nouveaux FIT importés, sans erreur.
- Actualisation quotidienne configurée à **8 h dans Codex**, tâche « Actualiser SessionDNA ». Le PC et Codex doivent pouvoir exécuter cette tâche ; aucune exécution lorsque le PC est éteint n'est garantie.
- Les nouveaux exports `mon_calendrier*.ics` dans Téléchargements sont repérés lors de l'actualisation. Le téléchargement sur MyDevinci reste manuel tant qu'un lien d'abonnement n'est pas disponible.
- Après enregistrement d'un retour ou d'un horaire, une sauvegarde sur le PC est tentée automatiquement. Lire le statut dans **Mes données entre appareils**. Les données distantes nouvelles et conflits nécessitent une synchronisation manuelle ; aucune saisie en cours n'est rechargée automatiquement.
- Accès iPhone **non activé** : l'installation Tailscale a été interrompue (code 1602). Les contraintes réelles de sommeil, transports et piscine restent à fournir. Les essais réalisés sont techniques ; une semaine d'utilisation réelle reste à valider.

Pour lancer toutes les actualisations maintenant : `python src/update_triathlon.py --sync --calendar-downloads`. Puis recharger l'application. Le serveur reste `python src/serve_sessiondna.py`.

[Ce qu'il reste à faire avec l'utilisateur et protocole d'essai](docs/validation-quotidienne.md).

## Calendrier et organisation — 28 septembre 2026

**Les cours sont intégrés : 563 événements, dont 15 pour la semaine du 28 septembre.** Dans l’application, ouvrir **Cours et horaires** : renseigner ses contraintes, proposer des créneaux ou saisir ses horaires, puis vérifier les conflits. Les séances liées restent à placer manuellement ; le programme sportif ne change pas.

Les saisies sont enregistrées dans le navigateur, puis une sauvegarde sur le PC est tentée automatiquement. Le bouton **Synchroniser les saisies enregistrées** permet aussi de récupérer les retours et horaires, avec un historique et une détection des modifications concurrentes. Recharger après récupération. L’accès iPhone reste à activer : il nécessite l'installation Tailscale et la configuration du téléphone.

[Guide du calendrier, des limites et de l’accès iPhone](docs/calendrier-et-iphone.md).

## Planning Ironman — 28 septembre 2026

La semaine fournie est maintenant consultable en haut de l'application : **15 séances**, **21 h 06 d'endurance** et **1 h 35 de renforcement**. Les fiches affichent les blocs répétés, les récupérations, les cibles disponibles et toutes les consignes du JSON. Le programme source est conservé sans modification.

Tu peux saisir un retour par séance et préparer le bilan à transmettre dans IRON MAN. **Enregistrer le formulaire puis synchroniser pour sauvegarder sur le PC ; conserver aussi des exports JSON.** L’accès réel depuis l’iPhone et l’envoi automatique à la conversation ne sont pas configurés.

[Guide du planning et des retours](data/processed/triathlon/training_guide.md). Le calendrier MyDevinci est importé ; les réglages de trajets et de disponibilité se trouvent dans Cours et horaires. Les durées réelles restent à renseigner.

Pour ouvrir : `python src/serve_sessiondna.py`, puis http://127.0.0.1:8765. Pour importer une autre semaine :

```powershell
python src/import_training_week.py "CHEMIN\semaine.json"
python src/build_triathlon_app.py
```

L'import identique est ignoré ; une modification crée une version distincte. Les retours sont attachés à la version exacte du programme. Les durées de nage annoncées sont actives et ne couvrent pas tout le créneau nécessaire.

## État des analyses — 25 septembre 2026

L'inventaire multisport contient **404 sessions** : 158 courses, 145 vélos, 99 séances de natation et 2 randonnées. Consulter [le rapport triathlon](data/processed/triathlon/report.md) pour le détail et les contrôles.

| Partie | État réel | Résultat |
|---|---|---|
| Import Garmin | Session locale réutilisée, doublons évités ; actualisation à la demande | `src/sync_garmin.py` |
| Analyse multisport | Course, vélo, longueurs de piscine et liens vélo-course candidats | [Inventaire](data/processed/triathlon/inventory.csv) |
| Détection des répétitions et pauses | Expériences précédentes conservées sur les lots de course | [Rapport v2](data/processed/detection_pauses/report.md) |
| Annotations | 28 annotations sportives exploitables sur 73 fiches | [Fiches](data/processed/supervised/annotation.html) |
| Modèle supervisé | Première forêt entraînée : 20 apprentissages, 8 tests, 7 bonnes réponses | [Rapport du modèle](data/processed/sport_model/report.md) |
| Application | Tableau de bord local, filtres, courbes, observations et suggestions sur le jeu initial | [Ouvrir la version statique](data/processed/triathlon_app/index.html) |
| iPhone | Interface mobile et fichiers PWA préparés ; accès privé HTTPS et essai sur appareil à faire | [Guide complet](data/processed/triathlon/guide.md) |

**Le modèle est exploratoire.** Il distingue seulement EF, endurance soutenue et seuil. Brick est un contexte distinct, repéré par les horaires puis à confirmer. Les classifieurs vélo/natation et les autres objectifs de course ne sont pas encore entraînés. Le test de 8 séances ne suffit pas à établir une fiabilité générale.

## Reprendre et tout lancer

Depuis le dossier du projet dans PowerShell :

```powershell
.\.venv\Scripts\Activate.ps1
python src/update_triathlon.py
python src/serve_sessiondna.py
```

Ouvrir **http://127.0.0.1:8765** dans le navigateur. Garder le terminal ouvert ; `Ctrl+C` arrête le serveur. Pour importer les séances Garmin manquantes avant l'analyse, remplacer la commande d'actualisation par :

```powershell
python src/update_triathlon.py --sync
```

Cette commande ne réentraîne pas le modèle. Elle actualise les analyses et l'application ; recharger ensuite la page. L'import quotidien est configuré dans Codex, comme indiqué en début de README.

## Comprendre ce qui a été fait

Lire [le guide pédagogique de la version triathlon](data/processed/triathlon/guide.md). Il explique les six variables du modèle, les votes de la forêt, la séparation apprentissage/test, les pauses, les bricks, le traitement de la natation et les limites de l'application.

Les nouvelles analyses sont séparées des expériences antérieures : le jeu initial de 73 courses, ses annotations et ses lots train/test restent conservés. Les nouvelles activités importées ne sont pas ajoutées automatiquement à l'apprentissage.

## Ce qu'il reste avant de clôturer une V1 validée

1. Contrôler le rendu dans un navigateur et sur iPhone ; choisir un accès privé HTTPS. Aucun hébergement n'a été créé et le serveur actuel écoute uniquement sur le PC.
2. Confirmer les candidats bricks et enrichir les objectifs rares avec tes annotations.
3. Définir puis réaliser un test prospectif sur de nouvelles séances, sans ajuster le modèle après lecture du test.
4. Annoter les sports vélo/natation avant d'entraîner leurs catégories ; leurs analyses descriptives sont disponibles.
5. Selon ton usage, programmer la synchronisation et enrichir les retours comparatifs. Les conseils personnalisés et une reformulation par IA générative restent des extensions à évaluer.

## Historique pédagogique

Les sections suivantes décrivent les étapes précédentes et leurs résultats à l'époque. Les anciens effectifs et mentions « à entraîner » ne décrivent pas l'état actuel, résumé ci-dessus.

## Installation et exécution sous Windows PowerShell

Python utilisé : 3.13.9. Depuis la racine du projet :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src/inspect_fit.py
```

La création et l'installation ne sont nécessaires qu'au premier démarrage. Les fois suivantes, activer l'environnement suffit.

Le fichier de référence local doit se trouver dans `data/raw/24311406124_ACTIVITY.fit`. Les données personnelles ne sont pas fournies dans Git.

Pour sauvegarder sans ouvrir de fenêtre :

```powershell
python src/inspect_fit.py --no-show
```

Pour analyser un autre fichier (sans appliquer les phases manuelles de la séance de référence) :

```powershell
python src/inspect_fit.py --file "data/raw/autre_activite.fit" --no-show
```

Les chemins passés explicitement sont relatifs au dossier du terminal ; les chemins par défaut sont calculés à partir du script.

## Résultats

Les résultats sont enregistrés dans `data/processed/<nom_du_fichier>/` :

- `records.csv` : mesures sélectionnées, temps écoulé et vitesse convertie en km/h.
- `summary.csv` : nombre de valeurs, moyenne, médiane, minimum et maximum.
- `gaps.csv` : intervalles supérieurs à une seconde.
- `manual_phases.csv` : comparaison des phases manuelles, uniquement pour la séance de référence.
- `session.png` : vitesse et fréquence cardiaque, avec les deux efforts colorés et le trou signalé.
- `report.md` : bilan des contrôles, résultats et limites.

Une nouvelle exécution remplace les résultats de la même activité. Le fichier FIT brut reste inchangé. `data/` est ignoré par Git.

## Résultat de la première exploration

La séance de référence contient 4 503 points sur 75 min 15 s entre premier et dernier point, un intervalle de 14 secondes et une puissance manquante. Les horodatages sont présents, uniques et croissants. Aucune baisse de distance cumulée ni valeur négative n'a été trouvée dans les colonnes contrôlées.

| Phase manuelle | Vitesse moyenne des points | FC moyenne des points |
|---|---:|---:|
| Effort 1, 27 à 42 min | 15,21 km/h | 160,93 bpm |
| Effort 2, 45 à 60 min | 15,19 km/h | 161,15 bpm |

Ces résultats décrivent les mesures disponibles ; ils ne constituent pas une évaluation physiologique.

## Comprendre le script

Le fichier `src/inspect_fit.py` est organisé en sept blocs commentés :

1. **Entrée et sortie** : `Path` construit les chemins. `argparse` permet les options `--file`, `--output` et `--no-show` dans le terminal.
2. **Lecture** : `fitdecode` décode le FIT. La boucle retient les messages `record`. Chaque dictionnaire associe des noms de colonnes à leurs valeurs ; la liste `rows` recueille ces lignes.
3. **Contrôles et transformations** : Pandas forme le tableau `df`. `diff()` calcule les écarts de temps. Des erreurs explicites arrêtent l'analyse si les horodatages sont invalides. La conversion en km/h multiplie les m/s par 3,6.
4. **Statistiques et filtrage** : `agg()` applique plusieurs calculs aux colonnes. Les conditions sur `elapsed_min` sélectionnent les phases. Une valeur absente n'est pas remplacée par zéro.
5. **Export** : `to_csv()` écrit les tableaux dans des fichiers texte structurés réutilisables, sans toucher au FIT.
6. **Graphique** : Matplotlib trace vitesse et fréquence cardiaque sur un axe temporel commun. Les zones vertes sont manuelles. Les lignes sont interrompues aux trous plutôt que de dessiner une continuité artificielle.
7. **Bilan** : un fichier Markdown rassemble observations et limites.

`main()` regroupe l'exécution. La condition finale `if __name__ == "__main__"` lance cette fonction lorsque le fichier est exécuté directement, sans la lancer automatiquement si ce fichier est importé par un autre programme.

## Limites

- Les limites des phases sont approximatives et propres à une séance identifiée par son nom de fichier.
- « Seuil » est la description donnée par le sportif ; aucune reconnaissance automatique ni validation du seuil.
- Moyennes par point, sans pondération selon le temps ni reconstitution des trous.
- Temps écoulé différent possible du temps chronométré ou du temps en mouvement Garmin.
- Les valeurs extrêmes restent présentes ; les contrôles réalisés ne prouvent pas l'exactitude des capteurs.
- La classification de plusieurs séances et l'apprentissage automatique sont des étapes futures.


## Partie 2 — Inventorier plusieurs activités

Le script `src/analyze_activities.py` parcourt tous les fichiers `.fit` directement présents dans `data/raw`, y compris les extensions en majuscules. Il sauvegarde ses résultats sans ouvrir de fenêtre :

```powershell
python src/analyze_activities.py
```

Autres dossiers possibles :

```powershell
python src/analyze_activities.py --input "data/raw" --output "data/processed/batch"
```

Il conserve les fichiers bruts et utilise uniquement les bibliothèques déjà installées.

### Résultats de cette partie

Dans `data/processed/batch` :

- `inventory.csv` : correspondance entre nom du FIT, date UTC, sport, distance, durées, mesures et contrôles. Les fichiers en erreur figurent aussi dans l'inventaire.
- `running_features.csv` : une ligne par course retenue et des premières caractéristiques descriptives ; ce n'est pas encore une matrice prête pour entraîner un modèle.
- `running_comparison.png` : comparaison des durées, vitesses moyennes et écarts-types de vitesse.
- `activity_profiles/` : une image vitesse/FC par course retenue pour faciliter son identification dans Garmin.
- `report.md` : inventaire lisible, contrôles, comparaison et galerie de courbes.

Chaque exécution remplace les résultats des mêmes noms. Les anciens profils correspondant à des fichiers retirés du dossier peuvent rester sur le disque : le rapport généré liste uniquement les profils de l'exécution actuelle. Pour retrouver une activité, comparer sa date UTC, sa durée et sa distance à Garmin (dont l'heure peut être locale).

### Ce qui change par rapport à la première partie

Avant : **une ligne = un point de mesure** dans une seule séance.

Maintenant : **une ligne = une activité**, décrite par plusieurs caractéristiques. Les points servent à calculer ces caractéristiques, puis on compare les activités.

Le code est organisé en fonctions :

1. `read_activity()` décode les points `record` et le résumé `session` de chaque FIT.
2. `summarize_activity()` contrôle et résume une activité.
3. `save_activity_plot()` produit ses courbes.
4. `save_comparison()` compare les courses retenues.
5. `make_report()` construit le bilan.
6. `main()` orchestre la boucle sur les fichiers et les sauvegardes.

Une fonction permet de nommer une tâche et de la réutiliser. Ici, nous appliquons la même lecture et les mêmes contrôles à chacun des fichiers, sans copier le code onze fois.

### Lire les colonnes

| Colonne | Signification |
|---|---|
| `filename` | Nom d'origine permettant de retrouver le FIT |
| `start_utc` | Début de séance, en UTC |
| `sport`, `sub_sport` | Sport déclaré dans le résumé FIT, pas une prédiction |
| `timer_min` | Minutes de chronomètre actif dans le résumé Garmin |
| `elapsed_min` | Minutes totales écoulées dans le résumé Garmin |
| `paused_min` | Différence entre les deux durées ; pas un calcul du temps en mouvement |
| `distance_km` | Distance du résumé Garmin, convertie de mètres en kilomètres |
| `record_span_min` | Temps séparant premier et dernier point, parfois légèrement différent du résumé |
| `speed_mean`, `speed_median`, `speed_std`, `speed_max` | Statistiques de vitesse, en km/h |
| `hr_mean`, `hr_std`, etc. | Statistiques de fréquence cardiaque, en bpm |
| `power_mean`, `power_std`, etc. | Statistiques de puissance, en watts |
| `speed_cv` | Écart-type de vitesse divisé par la moyenne : dispersion relative, sans unité |
| `*_missing_pct` | Pourcentage de mesures manquantes parmi les points |
| `gaps_over_1s`, `max_interval_s` | Nombre d'intervalles > 1 seconde et plus grand intervalle en secondes |
| `user_description` | Description déjà fournie, laissée vide pour les séances inconnues |

L'écart-type mesure la dispersion autour de la moyenne : deux séances peuvent avoir la même moyenne, mais des écarts-types différents. Par exemple, les vitesses 10, 10, 10 et 5, 10, 15 ont la même moyenne de 10, mais la seconde série varie davantage. Le calcul utilise l'écart-type d'échantillon de Pandas (`ddof=1`).

Ces mesures ne disent pas dans quel ordre les efforts ont eu lieu. Les arrêts, erreurs de capteur et variations de terrain influencent également l'écart-type : il ne reconnaît pas à lui seul une séance d'intervalles.

### Contrôles et limites

- Les points sont analysés sans coordonnées GPS ni informations d'identité du dispositif dans les exports.
- Les statistiques portent sur les points présents, sans pondération temporelle ; zéros et pics restent inclus.
- Un fichier identique est repéré par son empreinte SHA-256 et n'est pas recompté. Même début UTC et même sport sont signalés comme doublon possible, même si les fichiers diffèrent.
- Les activités multi-sessions sont inventoriées mais exclues de cette première comparaison.
- Les horodatages invalides ou non croissants empêchent l'analyse temporelle de l'activité concernée.
- Un fichier illisible produit une ligne `error` ; les autres restent traités.
- Les statuts `review`, `excluded`, `duplicate` et `error` ne sont pas inclus dans le tableau des courses retenues. Les contrôles ne garantissent pas l'exactitude des capteurs.
- L'intervalle > 1 seconde signale une irrégularité ; il peut venir d'une pause ou d'un mode d'enregistrement, pas forcément d'une perte de données.
- Aucune catégorie n'est inventée. Les limites manuelles 27–42 et 45–60 minutes de la première séance ne sont pas transférées aux autres.
- Aucun clustering ni classifieur n'est encore entraîné. Onze activités servent à explorer et préparer les données, pas à démontrer une performance prédictive fiable.

Référence : [durées FIT, documentation Garmin](https://developer.garmin.com/fit/cookbook/durations/).


## Partie 3 — Premier clustering exploratoire

```powershell
python src/cluster_activities.py
```

Le script lit `data/processed/batch/running_features.csv`, compare K-means avec 2, 3 et 4 groupes et détaille par défaut la partition à 3 groupes. Pour regarder une autre partition :

```powershell
python src/cluster_activities.py --k 2 --output "data/processed/clustering_k2"
```

Relancer d'abord `analyze_activities.py` si les fichiers FIT ont changé. Aucun modèle supervisé ni service de prédiction n'est créé à ce stade.

### Les trois caractéristiques choisies

- `timer_min` : durée chronométrée, en minutes.
- `speed_mean` : vitesse moyenne des points, en km/h.
- `speed_cv` : écart-type de vitesse divisé par sa moyenne, sans unité.

Nous commençons avec peu de variables pour pouvoir expliquer les regroupements. La distance ferait en partie double emploi avec la durée et la vitesse. La fréquence cardiaque et la puissance pourront être explorées ensuite. Le nom du fichier, la date, la description utilisateur et les groupes manuels ne participent pas au calcul des distances.

### Standardisation

Les échelles numériques sont différentes : environ 35–120 pour la durée, 11–13 pour la vitesse et 0,06–0,17 pour le CV. K-means utilise des distances ; sans mise à l'échelle, les minutes risquent de dominer le calcul.

`StandardScaler` transforme chaque colonne selon `(valeur - moyenne) / écart-type`. Une valeur transformée de 0 correspond à la moyenne du lot, +1 à un écart-type au-dessus. Ce changement d'échelle ne modifie pas les fichiers d'origine et n'élimine pas les valeurs extrêmes. L'écart-type du scaler utilise `ddof=0`, tandis que le CV de l'exploration utilisait l'écart-type d'échantillon de Pandas (`ddof=1`).

### K-means

K-means rapproche les séances de centres de groupes. Il alterne l'attribution au centre le plus proche et le recalcul des centres (moyennes des points attribués), pour réduire les distances au carré à l'intérieur des groupes. Il cherche une solution, pas nécessairement le minimum global.

`n_clusters` est le nombre de groupes demandé. `n_init=30` essaie 30 initialisations et conserve celle avec la plus petite inertie. `random_state=42` fixe l'aléatoire pour rendre l'expérience reproductible dans le même environnement.

Les groupes 1, 2, 3 sont des numéros arbitraires, sans ordre sportif. La partition à 3 groupes est une vue exploratoire : le script conserve aussi celles à 2 et 4 groupes, sans prétendre connaître le vrai nombre de types de séance.

### Évaluer sans catégories connues

- **Silhouette** : mesure interne de compacité et de séparation, de -1 à 1. Ce n'est ni une précision ni une probabilité. Le calcul utilise les trois variables standardisées.
- **Inertie** : somme des distances au carré aux centres. Elle tend à diminuer quand on augmente le nombre de groupes : cette baisse seule ne suffit pas à choisir k.
- **Retrait d'une séance** : retirer successivement chaque ligne, réapprendre le scaler et K-means sur les lignes restantes, puis comparer les groupes à ceux du lot complet sur ces mêmes lignes.
- **ARI** : mesure cet accord, indépendamment des numéros de groupes. 1 = même partition, 0 = accord attendu par hasard ; il peut être négatif. Ici, c'est un diagnostic de sensibilité, pas un score contre des catégories vraies et pas une validation prédictive.

### Fichiers produits dans data/processed/clustering

| Fichier | Contenu |
|---|---|
| `assignments.csv` | Correspondance A01…A11, nom FIT, date, caractéristiques et groupes pour chaque k |
| `group_profiles.csv` | Centres des groupes en unités d'origine et effectifs |
| `k_comparison.csv` | Silhouette, inertie, tailles et résumé de stabilité pour k=2,3,4 |
| `leave_one_out.csv` | Résultat de chaque retrait individuel |
| `standardized_features.csv` | Les trois caractéristiques après changement d'échelle |
| `clusters.png` | Trois vues des groupes, deux variables à la fois, en unités d'origine |
| `standardized_features.png` | Tableau coloré des caractéristiques standardisées |
| `experiment.json` | Paramètres, versions, échelles et empreinte du fichier d'entrée |
| `report.md` | Méthode, résultats, affectations et limites |

Les scripts n'imputent pas de caractéristiques absentes : une entrée incomplète ou invalide provoque une erreur explicite. Au moins six séances et cinq profils distincts sont requis pour les comparaisons prévues ici ; ce seuil technique ne garantit aucune fiabilité statistique.

### Ce qu'il faut retenir

Il s'agit d'apprentissage non supervisé : aucun exemple étiqueté n'a été donné à K-means. Nous pouvons interpréter les différences entre groupes après calcul, sans les assimiler automatiquement à endurance, seuil ou VO2max. Une forte silhouette ou une bonne stabilité sur onze activités d'un sportif ne démontre pas une capacité à reconnaître de nouvelles séances.

Sources : [K-means](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html), [StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html), [silhouette](https://scikit-learn.org/stable/auto_examples/cluster/plot_kmeans_silhouette_analysis), [ARI](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.adjusted_rand_score.html).

## Import des activités depuis Garmin Connect

## Ce qui est prêt

Le script `src/sync_garmin.py` récupère les exports originaux FIT manquants de Garmin Connect et les enregistre dans `data/raw` sous le nom `<identifiant>_ACTIVITY.fit`.

Il utilise la bibliothèque communautaire `garminconnect==0.3.10`, pas l'API officielle réservée au programme développeur Garmin pour les entreprises. Le fonctionnement peut changer si Garmin modifie son service. La connexion réelle doit être validée lors du premier lancement par l'utilisateur ; les tests réalisés jusqu'ici sont hors ligne.

## Première connexion — à faire par l'utilisateur dans VS Code

Depuis le terminal PowerShell, dans SessionDNA, avec `.venv` activé :

```powershell
python src/sync_garmin.py --login --max-new 5
```

Le programme demande l'adresse e-mail et le mot de passe Garmin. La saisie du mot de passe est invisible : il est normal de ne voir aucun caractère ni astérisque. Si Garmin demande un code de double authentification, le saisir également dans ce terminal. Ne transmettre ni mot de passe, ni code, ni fichier de session dans la conversation.

La limite de cinq nouveaux fichiers sert à vérifier la connexion avant de récupérer tout l'historique. Les fichiers déjà présents ne comptent pas dans cette limite et ne sont pas remplacés. Cette commande importe les activités disponibles, tous sports confondus.

## Imports suivants

```powershell
python src/sync_garmin.py
```

Le programme restaure la session locale, parcourt l'historique et télécharge seulement les fichiers absents. La première récupération complète peut prendre plusieurs minutes pour plusieurs centaines de séances. Les exécutions suivantes vérifient l'historique sans retélécharger les FIT existants.

Pour ne récupérer que la course à pied :

```powershell
python src/sync_garmin.py --sport running
```

Les autres valeurs sont `cycling`, `swimming` et `all` (par défaut). Il n'y a pas encore de tâche quotidienne installée : « automatique » désigne ici le téléchargement et le tri réalisés par la commande.

## Réutiliser les nouvelles données

Après un import réussi :

```powershell
python src/analyze_activities.py
python src/cluster_activities.py
```

La première commande reconstruit l'inventaire et les caractéristiques. La seconde refait le clustering à partir du nouveau tableau. Il est normal que les groupes et leurs numéros changent avec de nouvelles activités. Les autres sports restent inventoriés ; la comparaison et le clustering actuels sont réservés aux courses admissibles.

## Où sont les fichiers ?

- `data/raw` : les exports FIT.
- `data/sync/sync_state.json` : le catalogue des identifiants déjà rencontrés, noms, dates, sports et états d'import.
- `data/sync/sync_report.json` : le résultat du dernier lancement, erreurs et raison de l'arrêt éventuel.
- `%LOCALAPPDATA%\SessionDNA\GarminTokens` : les jetons de session locaux, normalement hors de OneDrive et du dépôt Git. Ces jetons sont sensibles et ne doivent pas être partagés. Le script ne sauvegarde pas le mot de passe ; la bibliothèque gère la session et son renouvellement tant que Garmin l'accepte.

Le dossier `data/` est ignoré par Git ; des exclusions supplémentaires couvrent les noms usuels de fichiers de jetons pour éviter leur ajout accidentel au projet.

## Fonctionnement et notions apprises

1. **Authentification** : prouver à Garmin que l'accès au compte est autorisé. Les jetons permettent de reprendre la session sans ressaisir le mot de passe à chaque commande.
2. **Pagination** : demander les activités par pages de 50, plutôt que supposer que toute la liste arrive en une réponse.
3. **Import incrémental** : comparer les identifiants aux fichiers locaux pour récupérer les activités manquantes, même anciennes.
4. **Idempotence** : relancer la commande ne crée pas de copies des mêmes séances et n'écrase pas les fichiers déjà nommés `<id>_ACTIVITY.fit`.
5. **Validation** : accepter un FIT direct ou lire celui d'un ZIP, vérifier le décodage et les CRC avant de l'enregistrer.
6. **Reprise** : enregistrer l'état progressivement ; un arrêt ne supprime pas les imports réussis.
7. **Gestion des erreurs** : signaler les exports sans FIT, refuser les archives ambiguës et interrompre les requêtes si Garmin limite l'accès ou devient inaccessible.

Les noms contenus dans le ZIP ne sont jamais utilisés comme chemins de destination. Le nom final est construit à partir de l'identifiant numérique Garmin. Le script ne modifie et ne supprime aucune activité sur Garmin.

## Dépannage

- **Première connexion nécessaire ou session expirée** : relancer avec `--login` dans un vrai terminal interactif.
- **Garmin limite les requêtes ou refuse l'accès** : attendre avant de relancer ; ne pas multiplier les tentatives.
- **Export sans FIT** : une activité ajoutée manuellement ou provenant d'un autre format peut ne pas fournir de FIT. Elle est signalée, pas convertie en faux FIT. Utiliser `--retry-unavailable` pour réessayer ultérieurement.
- **Import interrompu** : relancer la commande. Les fichiers présents sont conservés.
- **Verrou `sync.lock` présent** : vérifier qu'aucun import ne tourne encore. Après un arrêt brutal seulement, retirer le verrou résiduel avant de relancer ; ne pas le retirer pendant un import.
- **État invalide** : ne pas effacer automatiquement `sync_state.json` ; examiner la cause.
- **Fichier local modifié ou renommé** : l'idempotence repose sur le nom `<id>_ACTIVITY.fit`. Un fichier existant n'est pas rafraîchi si l'activité a changé sur Garmin ; ce cas demandera une action explicite ultérieure.

Diagnostic sans connexion ni accès aux jetons :

```powershell
python src/sync_garmin.py --check
```

## Vérifications réalisées

Tests hors ligne avec réponses simulées et un FIT local existant : import direct/ZIP, reprise après limite, absence de retéléchargement, refus d'écrasement, export sans FIT, fichier invalide, archive multi-FIT, nom de ZIP malveillant ignoré et arrêt sur limitation Garmin. Les dépendances installées sont compatibles selon `pip check`.

Connexion réelle, restauration de session et téléchargement vérifiés par les imports effectués dans le terminal. La double authentification reste dépendante des demandes de Garmin.

Sources : [Garmin Developer Program](https://developer.garmin.com/gc-developer-program/program-faq/), [python-garminconnect](https://github.com/cyberjunky/python-garminconnect), [exemple de connexion](https://github.com/cyberjunky/python-garminconnect/blob/master/example.py).

## Mise à jour du 19 septembre 2026 — 53 courses

Après synchronisation Garmin, le lot comporte 56 FIT : 53 courses, 2 activités vélo et 1 de natation. Les 53 courses passent les contrôles utilisés ; elles couvrent le 5 juillet au 18 septembre 2026 (UTC).

Les sorties de référence sont maintenant dans `data/processed/batch` et `data/processed/clustering`. Les résultats précédents sont conservés dans `data/processed/history/before_53_20260919`. Les sections qui décrivent onze séances ci-dessus documentent l'expérience initiale.

Avec k=3 : 31 séances plus courtes (45,42 min en moyenne), 11 plus rapides et variables (71,33 min), et 11 plus longues (109,51 min). Les moyennes de vitesse sont respectivement 11,02, 12,71 et 11,36 km/h. Il s'agit de descriptions, pas de catégories sportives validées.

Silhouettes pour k=2,3,4 : 0,628 ; 0,727 ; 0,617. Les 11 séances d'origine gardent le même regroupement entre elles à k=3 (ARI=1), malgré les nouveaux numéros. Les 159 essais de retrait conservent aussi les partitions restantes pour ces configurations. Cela ne constitue pas une évaluation prédictive.

Les identifiants courts A01… sont réattribués par ordre chronologique à chaque lot : comparer les expériences par nom de fichier FIT. Sur les graphiques de plus de 20 séances, les étiquettes individuelles sont omises pour rester lisibles ; `assignments.csv` conserve la correspondance complète.

Les deux activités vélo présentent un écart d'une seconde entre leurs durées déclarées ; la natation n'a pas de vitesse dans les points lus. Ces fichiers restent signalés pour une analyse propre à leur sport.

## Partie 4 — Retrouver la structure enregistrée des séances

Jusqu'ici, chaque course était résumée par quelques nombres pour comparer les séances avec KMeans. Cette partie revient à l'intérieur de chaque séance : quelles étapes se succèdent, combien de fois et pendant combien de temps ?

```powershell
python src/analyze_structure.py
```

La commande utilise les courses de `data/processed/batch/running_features.csv` et leurs FIT dans `data/raw`. Elle fonctionne hors ligne et ne demande pas de connexion Garmin. Après de nouveaux imports, relancer d'abord `python src/analyze_activities.py` pour actualiser cet inventaire.

À ouvrir dans `data/processed/structure` :

- `report.md` : résultats et limites, avec un lien vers chaque graphique.
- `structure_summary.csv` : une ligne par course, état et répétitions observées.
- `repeated_steps.csv` : nombre de répétitions et durées minimale, médiane et maximale par étape répétée.
- `activities/<identifiant>/structure.png` : vitesse et frise des étapes.
- `activities/<identifiant>/planned_steps.csv`, `linked_laps.csv`, `observed_blocks.csv` : données intermédiaires pour comprendre le calcul.
- `method.json` : paramètres de reconstruction.

### Ce que fait le code

1. **Lire trois types de données.** Les `record` donnent les mesures successives ; les `lap` donnent les tours enregistrés ; les `workout_step` décrivent le programme embarqué dans le FIT.
2. **Faire une jointure.** La colonne `wkt_step_index` d'un tour désigne le `message_index` de son étape. `merge(..., validate="many_to_one")` associe plusieurs tours à une seule étape et refuse des clés de programme dupliquées.
3. **Regrouper selon l'ordre temporel.** Plusieurs tours d'un kilomètre peuvent appartenir au même effort de quinze minutes. Le code fusionne seulement les tours consécutifs compatibles. Il garde deux occurrences séparées par une récupération distinctes.
4. **Comparer prévu et réalisé.** Une durée programmée n'est pas nécessairement celle exécutée. `planned_duration_s` conserve la consigne et `timer_s` additionne les durées chronométrées réellement enregistrées.
5. **Tracer et contrôler.** Le graphique superpose les étapes à la vitesse pour permettre un examen visuel. Les pauses et les étapes fragmentées demandent un traitement prudent.

### Exemple concret : la séance du 10 septembre

Dans `24311406124_ACTIVITY.fit`, la reconstruction retrouve les deux occurrences de l'étape E6 : **900 secondes chacune**, démarrant à **27 et 45 minutes**. Elle retrouve aussi quatre occurrences de l'étape E2 de **20 secondes**. Chaque effort de quinze minutes rassemble plusieurs tours, ce qui explique pourquoi compter simplement les tours aurait donné une mauvaise réponse.

Les identifiants E2, E6, etc. sont propres au programme de chaque séance. E6 ne veut pas dire « seuil » pour toutes les activités.

### Ce que ces résultats permettent de conclure

Nous savons exploiter la structure enregistrée par Garmin. Nous n'avons pas encore construit un algorithme qui reconnaît les intervalles uniquement à partir de la vitesse ou de la fréquence cardiaque. Le code `active` du FIT ne prouve pas un effort au seuil : il peut aussi qualifier un échauffement ou un retour au calme.

Les fusions s'arrêtent aux frontières `time`/`session_end` et aux écarts de continuité supérieurs à deux secondes. Si la même étape subsiste dans plusieurs blocs successifs, elle est marquée `ambiguous_fragmentation` et exclue du comptage des répétitions. C'est un choix conservateur : mieux vaut signaler une ambiguïté que fabriquer des répétitions. Les tours sans lien restent séparés ; sans programme embarqué, cette méthode ne peut pas retrouver toute la structure.

Le seuil de soixante secondes utilisé dans les graphiques distingue seulement les répétitions longues des accélérations brèves. Il ne définit aucune zone physiologique.

Cette expérience est réalisée dans la partie 5 ci-dessous : les changements d'effort sont recherchés depuis la vitesse puis comparés aux étapes Garmin. Les consignes Garmin restent hors des entrées du détecteur pour éviter une **fuite d'information**.

### Vérifications

Tests ciblés : regroupement de tours en deux blocs de 900 s séparés par une récupération ; conservation des ruptures temporelles ; absence de fausses répétitions sur des fragments successifs ; tours inconnus ; absence de programme ; refus des indices dupliqués ; contrôle sur la séance réelle 2 × 15 min et 4 × 20 s. Les 53 courses du lot ont été traitées sans erreur et des graphiques ont été examinés visuellement.

Sources du format : [Garmin FIT Activity](https://developer.garmin.com/fit/articles/file-types/activity.html), [Garmin FIT Workout](https://developer.garmin.com/fit/articles/file-types/workout.html).


## Partie 5 — Détecter les passages rapides depuis la vitesse

Le projet sait maintenant produire une hypothèse à partir d'un signal, puis mesurer ses écarts par rapport à une référence. C'est une première méthode à règles, souvent appelée **baseline** : elle servira de point de comparaison pour les méthodes suivantes.

### Relancer cette partie

Dans le terminal PowerShell du projet, avec l'environnement activé :

```powershell
python src/detect_intervals.py
```

Les résultats sont déjà générés dans `data/processed/detection`. Aucune installation supplémentaire n'est nécessaire. Ouvrir `report.md`, puis le lien d'une séance pour voir son graphique.

Après de nouveaux imports, l'ordre complet est :

```powershell
python src/sync_garmin.py --sport running --max-new 40
python src/analyze_activities.py
python src/cluster_activities.py
python src/analyze_structure.py
python src/detect_intervals.py
```

Attendre la fin de chaque commande et examiner toute erreur avant de poursuivre. Le clustering est une analyse parallèle : le détecteur n'utilise pas ses groupes. La commande de synchronisation récupère jusqu'à 40 fichiers absents, y compris anciens ; elle n'est pas limitée aux séances récentes.

### Le raisonnement, étape par étape

**1. Conserver une mesure par seconde.** Le programme place la vitesse sur une grille temporelle régulière. Si une seconde n'a pas de mesure, elle reste vide. Cela permet de compter des durées sans confondre nombre de lignes et temps écoulé.

**2. Atténuer les pics isolés.** On remplace chaque vitesse par la médiane d'une fenêtre centrée de quinze secondes. La médiane est la valeur du milieu après tri : un point très élevé isolé la perturbe moins qu'une moyenne. Le calcul exige au moins sept mesures et ne traverse pas les trous du signal.

**3. Définir « plus rapide » pour cette séance.** On prend le quantile à 25 % des vitesses lissées supérieures à 5 km/h comme allure de base. Un quart de ces valeurs est inférieur ou égal à ce quantile. Ce n'est pas une mesure de ta zone d'endurance.

Le seuil vaut le plus grand de ces deux nombres : `base × 1,18` et `base + 1,5 km/h`. Par exemple, avec une base de 10 km/h, le seuil vaut 11,8 km/h. Ces paramètres sont des choix d'expérience, pas des constantes sportives universelles.

**4. Former des blocs.** Les secondes au-dessus du seuil constituent des passages candidats. Une petite baisse de quinze secondes maximum peut être réunie aux passages qui l'entourent si les données restent présentes et la vitesse lissée dépasse 5 km/h. On garde ensuite les blocs durant au moins deux minutes. Les accélérations de vingt secondes sont donc volontairement hors de l'objectif de cette version.

**5. Comparer après avoir prédit.** Les prédictions sont enregistrées avant de lire les étapes Garmin. Celles-ci servent ensuite à construire une référence partielle : les étapes actives répétées de deux minutes ou plus, liées et non ambiguës. L'absence de telles étapes ne prouve pas l'absence d'effort dans une séance.

### Comprendre les scores

Les scores portent sur les secondes observées dont la référence est exploitable :

- **Précision** : parmi les secondes détectées, quelle proportion appartient aux blocs de référence ? Elle diminue lorsque le programme ajoute des passages hors référence.
- **Rappel** : parmi les secondes des blocs de référence, quelle proportion est retrouvée ? Il diminue lorsque le programme en manque.
- **F1** : moyenne harmonique de la précision et du rappel ; un seul des deux scores élevé ne suffit pas.

Exemple : une référence contient 900 secondes. Si le détecteur en retrouve 810 et ajoute 90 secondes ailleurs, sa précision et son rappel valent tous deux 90 %. Ces chiffres ne prouvent pas qu'il a retrouvé les bonnes frontières ni le bon nombre de blocs : il faut aussi regarder le graphique.

Le bilan principal cumule les secondes sur les séances avec au moins un bloc de référence. Les séances longues pèsent davantage. Les autres séances restent visibles dans le rapport, sans devenir artificiellement un jeu de « vrais négatifs ».

### Ce qu'on apprend des erreurs

Une accélération progressive à l'échauffement peut franchir le seuil et être détectée. Une côte peut demander un effort élevé sans augmentation de vitesse. Une course rapide et uniforme peut ne contenir aucun passage assez rapide par rapport à sa propre base. Ces cas expliquent pourquoi la vitesse seule ne suffit pas à reconnaître toute la nature sportive d'une séance.

Le détecteur travaille après la course : sa médiane centrée utilise des points futurs et son seuil utilise l'ensemble de la séance. On ne peut pas le présenter tel quel comme un outil d'alerte en direct.

Les paramètres ont été fixés pour cette première expérience, sans recherche automatique du meilleur score. Le lot avait déjà été exploré : **ce n'est pas un test indépendant**. Avant d'optimiser les règles ou d'entraîner un modèle, on réservera de nouvelles séances pour vérifier la généralisation. Donner les étapes Garmin en entrée au détecteur reviendrait à lui donner les réponses : c'est une fuite d'information.

### Se repérer dans les fichiers

- `src/detect_intervals.py` : lecture des vitesses, règles, comparaison et graphiques.
- `detection_summary.csv` : paramètres calculés pour chaque séance, nombres de blocs, états et scores.
- `reference_coverage.csv` : proportion retrouvée de chaque bloc de référence.
- `activities/<identifiant>/comparison.png` : vitesse brute, vitesse lissée, seuil et deux frises à comparer.
- `activities/<identifiant>/detected_intervals.csv` : débuts, fins exclusives et durées des blocs détectés.
- `activities/<identifiant>/signal.csv` : signal et résultats intermédiaires, sans étiquette Garmin.
- `activities/<identifiant>/reference_mask.csv` : référence séparée de la prédiction.
- `experiment.json` : paramètres, bilan et empreintes SHA-256 des fichiers utilisés pour retrouver les conditions de l'expérience.

Vérifications automatisées : deux blocs synthétiques, course uniforme, pic isolé, accélération brève, interruption de mesures, baisse brève, arrêt, vitesses absentes, horodatages invalides, références ambiguës, reproductibilité de la détection et calcul des scores.

Documentation : [fenêtres pandas](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.rolling.html), [précision, rappel et F1](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html).


## Partie 6 — Comprendre et exploiter les pauses de la montre

### Ce qui a changé

Le nouveau script `src/detect_pauses.py` complète le détecteur v1 sans remplacer ses résultats. Il lit les événements du chronomètre, repère les arrêts suivis de reprises et propose, sous conditions, de regrouper des fragments rapides séparés par une pause connue.

```powershell
python src/detect_pauses.py
```

Après de nouveaux imports : actualiser d'abord le lot avec `analyze_activities.py`, puis les références avec `analyze_structure.py`. Le script des pauses recalcule v1 et v2 sur les mêmes entrées. Il utilise aussi `data/processed/detection/experiment.json` pour identifier les fichiers déjà examinés pendant l'expérience v1. Aucune nouvelle bibliothèque n'est nécessaire.

### Trois temps différents

**Le temps écoulé** suit l'horloge, pauses comprises. **Le temps chronométré** avance lorsque le chronomètre fonctionne. **Le temps détecté** additionne les fragments que notre règle considère comme rapides. Ces durées ne sont pas interchangeables.

Exemple : 8 minutes rapides, 1 minute avec la montre en pause, puis 7 minutes rapides représentent 16 minutes écoulées et 15 minutes au chronomètre. La nouvelle version peut proposer un même bloc interrompu, mais elle ne transforme jamais la minute de pause en minute d'effort.

### Lire les événements : une petite machine à états

Le programme suit un état : chronomètre démarré ou arrêté. Un événement `stop` ou `stop_all` après un `start` ouvre un arrêt. Le `start` suivant ferme la pause. Le dernier arrêt, sans reprise, correspond à la fin de l'enregistrement et n'ajoute pas une pause fictive.

Si la succession des événements est incohérente, le script la signale et désactive les regroupements par pause pour cette séance. Un trou de mesures sans arrêt/reprise confirmé reste un trou inexpliqué. Les événements ne permettent pas à eux seuls de savoir si la pause était manuelle ou automatique.

### Regrouper sans effacer l'incertitude

Le traitement de vitesse reste celui de v1 : médiane glissante et seuil relatif à la séance. Les mesures enregistrées pendant les pauses confirmées sont exclues. Les fragments sont formés avant d'appliquer la durée minimale de deux minutes.

Deux fragments voisins peuvent être réunis seulement si leur séparation contient une pause confirmée, totalisant au plus 180 secondes, avec au plus dix secondes de transition hors pause, au plus deux secondes manquantes hors pause et des vitesses de bord dans un rapport d'au plus 1,20. La petite tolérance hors pause tient compte des transitions d'enregistrement ; elle est explicite et exportée dans les décisions.

Ces valeurs sont des choix de départ documentés, pas des lois sportives. Une reprise lente ou un trou important non expliqué empêche la fusion. Même lorsque les critères sont remplis, `merge_hypothesis=True` signifie **regroupement proposé**, pas continuité de l'effort démontrée. Une récupération passée montre arrêtée peut correspondre à deux efforts différents : c'est la limite qui rend ton retour utile.

### Évaluer autre chose que le nombre de secondes

Les deux versions sont comparées sur les mêmes secondes mesurées hors pauses confirmées. La précision et le rappel mesurent toujours le recouvrement temporel avec les références Garmin.

On ajoute une comparaison des blocs : le script associe au plus un bloc détecté à un bloc de référence, en choisissant d'abord les meilleurs recouvrements. Le recouvrement **IoU** est le temps commun divisé par le temps couvert par l'un ou l'autre bloc, sur les secondes évaluables. Le minimum retenu est 0,5. Cet appariement glouton est transparent ; il n'est pas présenté comme une optimisation globale.

Pour les paires associées, on mesure les erreurs de début et de fin. Par exemple, une erreur de début de +8 secondes signifie que le détecteur commence huit secondes après la référence. Les blocs non associés sont comptés séparément : une moyenne sur les seuls bons appariements ne doit pas masquer des blocs oubliés.

### Quoi ouvrir ?

- `data/processed/detection_pauses/report.md` : bilan avant/après et graphiques.
- `comparison.csv` : une ligne par course, pauses, nombres de blocs et scores.
- `activities/<identifiant>/comparison.png` : référence Garmin, v1 et v2. Les zones grises montrent les pauses ; les traits sous les fragments indiquent les regroupements proposés.
- `pauses.csv` et `timer_events.csv` : pauses confirmées et événements sources.
- `intervals.csv` et `fragments.csv` : blocs logiques et morceaux mesurés qui les composent.
- `merge_decisions.csv` : critères de fusion et décision retenue, y compris les refus.
- `matches_v1.csv` et `matches_v2.csv` : appariements, IoU et écarts de frontières.
- `experiment.json` : règles et empreintes des fichiers de cette expérience.

### Ce qui reste nécessaire pour un vrai test indépendant

Les 53 courses actuelles ont déjà servi à explorer le problème. La v2 a été conçue après examen de certaines de leurs erreurs. Les résultats avant/après mesurent donc un progrès sur le lot de développement, pas une performance garantie sur de nouvelles séances.

Pour la suite, conserver le code et les paramètres de cette version, importer des courses jamais examinées et évaluer ces courses avant d'ajuster les règles. Séparer les données par séance complète : des secondes voisines de la même course ne doivent pas se retrouver de part et d'autre d'une séparation apprentissage/test. Les deux vélos et la natation ne constituent pas un jeu de test valide pour ce détecteur de course.

Nous n'avons pas entraîné de nouveau modèle supervisé pendant cette étape. Nous avons amélioré la préparation des données, une règle de détection et son évaluation. K-means reste la partie d'apprentissage non supervisé déjà réalisée.

Documentation du format : [événements et durées FIT](https://developer.garmin.com/fit/articles/file-types/activity.html).

### Résultat de cette exécution

Les 53 courses ont été traitées sans erreur ; leurs événements timer ne présentent pas d'incohérence détectée. Sur les onze séances comportant des références longues : 31 blocs proposés par v1, 29 par v2, pour 29 blocs de référence. Les deux versions apparient 29 références ; v1 avait donc deux fragments supplémentaires. La précision temporelle reste à environ 98,9 %, et le rappel passe de 98,2 % à 98,8 % sur les mêmes secondes évaluables.

Pour la séance du 17 septembre, v1 proposait quatre blocs ; v2 en propose deux. Le second réunit quatre fragments autour de trois pauses totalisant 137 secondes. Il couvre 1 041 secondes écoulées, soit 904 secondes hors pauses, dont 896 secondes de fragments détectés comme rapides. Il ne faut pas confondre ces trois durées avec les 900 secondes de consigne Garmin.

Tu as confirmé que les pauses servent à interrompre temporairement un effort. Cette information rend l'hypothèse de regroupement cohérente avec ton usage, tout en conservant les critères de vérification.

Aucune course locale inédite n'est disponible pour le test indépendant : les trois fichiers hors manifeste v1 sont les deux vélos et la natation. `evaluation_protocol.json` fixe le protocole et les empreintes du code ; `frozen_version/` conserve une copie de la version évaluée. Il reste à importer de nouvelles courses avant de pouvoir annoncer un résultat de test indépendant.

Les tests automatisés couvrent l'appariement arrêt/reprise, l'arrêt final, les trous sans événements, les reprises lentes, les pauses trop longues, les vitesses trop différentes, les fragments courts, les événements invalides, l'absence de prédiction pendant les pauses et l'appariement des blocs. Ils se relancent avec `python src/tests/test_pauses.py`.


## Partie 7 — Premier test sur des courses inédites

Les vingt premières courses absentes renvoyées par Garmin ont été importées, fixées dans un manifeste, contrôlées et analysées avec le code figé de la v2. Aucun seuil n'a été ajusté après lecture de leurs résultats. Les résultats sont dans [data/processed/test_20/report.md](data/processed/test_20/report.md).

Trois des vingt courses contiennent neuf blocs de référence longue. Les deux versions retrouvent ces neuf blocs, avec environ 98,6 % de précision et de rappel temporels sur ces trois séances. Une sortie progressive produit un bloc supplémentaire de 132 secondes sans référence correspondante : l’utilisateur a confirmé après le test une accélération volontaire. Cette annotation ne modifie pas les scores du test. Les dix-sept autres séances ne constituent pas un ensemble de négatifs sportifs validés.

Les deux versions ont les mêmes résultats ici : ce petit test ne démontre pas un bénéfice de la fusion des fragments autour des pauses. Les anciens rapports batch, clustering et detection_pauses restent ceux du développement sur 53 courses ; ne pas les confondre avec les résultats de test. Les paragraphes des parties précédentes qui demandaient encore de nouvelles courses décrivent l'état avant ce test.

Ce lot est désormais connu. Toute amélioration utilisant ses erreurs devra être testée sur un autre lot intact. Aucun nouveau modèle supervisé n'a été entraîné à cette étape.


## Partie 8 — Annotation et premier classifieur

Les 73 fiches sont dans [annotation.html](data/processed/supervised/annotation.html). L'interface fonctionne localement, sans serveur ; exporter régulièrement annotations.json. Les catégories proposées décrivent la structure : régulière, progressive, intervalles longs ; autre/incertain sont exclus du premier entraînement.

`src/prepare_supervised.py` prépare le lot depuis les résultats des 53 + 20 courses. `src/train_classifier.py` contrôle les annotations et compare les modèles. `src/predict_activity.py` appliquera un modèle sauvegardé à une nouvelle course FIT. Aucun de ces scripts n'invente les étiquettes manquantes. Les tests techniques utilisent des données synthétiques et ne constituent pas des résultats sur les séances sportives.

Le [guide de fin de projet](data/processed/supervised/guide.md) détaille les commandes et les étapes encore nécessaires. L'entraînement attend tes annotations ; le rendu de la page dans un vrai navigateur reste à confirmer.


## Annotation sportive v2 — catégories révisées

Les consignes v1 à trois classes dans les sections historiques sont remplacées par les nouvelles fiches. Objectif principal : récupération, footing/EF, endurance soutenue, seuil, VO₂max, vitesse/sprints, compétition, autre ou incertain. Format : continu, progressif, intervalles courts, intervalles longs, mixte ou incertain. Caractéristiques séparées : sortie longue, brick run, côtes ; chacune peut être Oui, Non, Incertain ou non renseignée.

Exemple : seuil long = objectif Seuil et format Intervalles longs. Une sortie longue ou une brick run peut être en EF ou contenir du travail intense. Le format ne démontre pas l'objectif physiologique.

La page cherche les réponses déjà sauvegardées dans le même navigateur et au même emplacement. Les anciens exports JSON peuvent aussi être importés. Leur ancien label reste visible dans un champ de contexte, sans remplir arbitrairement le nouvel objectif. Le stockage v1 est conservé séparément du stockage v2. Exporter régulièrement annotations_sport.json.

Le prochain entraînement demande de choisir une cible (objectif ou format, par exemple) et de vérifier les effectifs. Les tags demandent des tâches distinctes ; la reconnaissance d'une brick run nécessitera notamment le contexte vélo. Aucun nouveau modèle n'a été entraîné dans cette révision.
