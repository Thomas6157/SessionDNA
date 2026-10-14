# Validation de SessionDNA V2 — 13 octobre 2026

## Résultats confirmés

- **71 tests Python réussis** : import FIT (CRC et doublons), programmes immuables, sauvegardes, conflits, calendrier, analyse, SHAP, MLflow et bilan.
- **30 tests de l’interface réussis** : stockage, fusion, récupération, planning, version des programmes, séances liées, anciens retours et durées en secondes.
- Construction TypeScript / Vite réussie. **42 fichiers** de l’interface finale comparés à la version testée après installation.
- Ruff : aucun défaut dans les modules de la V2 contrôlés. `pip check` : aucune incompatibilité de dépendances détectée.
- Les scripts de contrôle historiques du planning et de synchronisation JavaScript réussissent également.
- Tests internes HTTP avec FastAPI TestClient sur le catalogue réel : page construite, manifeste PWA, service worker, état, données initiales, agrégations, technologies et archive répondent tous **200**.
- Chargement initial des données : **239,201 octets**, sans les profils ni la liste complète des activités ; ceux-ci sont chargés à la demande. Le service worker met aussi les bibliothèques de l’interface en cache au premier accès.

## Données réelles contrôlées

Le catalogue contient **413 activités : 162 courses, 148 vélos, 101 natations et 2 randonnées**. DuckDB et l’export Parquet concordent. Le registre MLflow local conserve l’expérience existante sans réentraînement.

Une activité de chaque sport a été lue via l’API. Le découpage fonctionne sur les exemples course et vélo. L’exemple natation n’a pas de profil segmentable ni de GPS : ces absences sont renvoyées explicitement. Une explication SHAP sur la séance du jeu d’origine reconstruisait la sortie de la forêt avec une erreur de 6.11e-16.

Le bilan de la semaine du **2026-09-28** reprend **15 séances**, leurs sources et les informations disponibles. Export Markdown : 12,632 octets. L’option générative renvoie bien « désactivée » sans requête à un modèle externe.

**24 fichiers protégés identiques à la sauvegarde précédant la V2** : programmes sources, annotations et artefacts du modèle. Les fichiers Garmin n’ont pas été réimportés pour ce contrôle. Aucune séance, aucun ressenti ou horaire fictif n’a été ajouté aux données réelles.

## Limites de cette validation

L’ouverture dans le navigateur n’a pas pu être validée dans l’environnement d’exécution : refus ou expiration de connexion à la boucle locale. Le serveur a atteint son état de démarrage dans le diagnostic, mais cela ne constitue pas une validation visuelle ou une preuve d’accès depuis l’iPhone. Les serveurs de diagnostic ont été arrêtés avant la dernière tentative de lancement local.

Le lanceur `Lancer-SessionDNA.cmd` est prêt à être ouvert directement sur le PC. Il faut encore valider dans le navigateur : navigation entre les cinq écrans, fiche d’une activité, courbes, tracé GPS, retour sauvegardé, export du bilan et absence de débordement sur écran étroit. L’accès privé HTTPS/Tailscale, l’installation Safari et la synchronisation depuis un vrai iPhone restent à vérifier.

Les tests ne valident pas la qualité physiologique d’un programme, la justesse des annotations ni la capacité du modèle à généraliser. Le test du modèle reste celui de 8 séances d’origine. L’inférence Ollama réelle, les trains en direct et une connexion continue MyDevinci ne sont pas activés.

Trois avertissements de dépréciation proviennent des couleurs de SHAP/Matplotlib ; ils n’ont pas fait échouer les tests.

Les résultats structurés sont conservés dans `data/processed/analytics/validation_v2.json`. Les données personnelles de ce dossier sont exclues de Git.

Dernière tentative : le serveur de test a été lancé dans un terminal isolé, mais la connexion locale a expiré. Son arrêt interactif a ensuite été refusé par la politique d’approbation ; ce processus peut encore être actif. Aucun réglage de pare-feu ni accès public n’a été modifié.
