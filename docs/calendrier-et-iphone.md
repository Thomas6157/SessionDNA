# Cours, entraînements et accès mobile

## Ce qui fonctionne

Le calendrier MyDevinci exporté le 28 septembre 2026 est importé : 563 événements, dont 15 du 28 septembre au 4 octobre. Chaque cours conserve son horaire et sa salle. Les dates sont converties en Europe/Paris, y compris pour les changements d'heure. Les événements annulés sont exclus ; les doublons strictement identiques sont supprimés.

Dans l'application, le lien **Cours et horaires** ouvre une vue réunissant cours et séances de la semaine sélectionnée. Renseigner les heures de disponibilité, le trajet des cours par sens, les marges avant/après le sport et le temps supplémentaire nécessaire en piscine. Rien n'est prérempli à partir de suppositions.

Le bouton **Proposer des créneaux libres** cherche par pas de 15 minutes, sur la date prévue de chaque séance. Les horaires déjà saisis sont conservés. Il vérifie cours + trajets, limites de journée et autres séances déjà placées. L'heure préférée du programme est essayée en premier lorsqu'elle existe. C'est une recherche simple, pas un planning optimal : un placement manuel différent peut libérer de la place. Les séances liées restent manuelles pour ne pas inventer leur ordre ou la récupération nécessaire.

Les consignes textuelles restent à lire : horaires de piscine, repas, lumière, état de fatigue et prescription sportive ne sont pas interprétés automatiquement. Les marges sont communes aux jours et sports, sauf le supplément piscine. La disponibilité doit commencer et finir le même jour ; le coucher après minuit n'est pas géré. La marge des cours est appliquée aussi aux cours en ligne. Un jour vide dans un export ne garantit pas l'absence réelle de cours.

Les horaires choisis apparaissent aussi sur les fiches de **Ma semaine** et dans le bilan hebdomadaire. Les retours et l'organisation sont stockés dans ce navigateur. Le bouton **Synchroniser les saisies enregistrées** les sauvegarde sur le PC et récupère les changements d'autres navigateurs. Cliquer sur chaque appareil puis recharger. Les changements indépendants sont fusionnés ; deux modifications différentes du même champ interrompent la synchronisation sans écraser les versions. Il faut alors exporter les deux versions et résoudre le conflit explicitement. Après enregistrement, une sauvegarde automatique est tentée. Si des données distantes doivent être récupérées, la synchronisation reste manuelle pour ne pas écraser une saisie en cours.

La sauvegarde serveur est dans `data/app_state/current.json`, hors du dossier servi et de Git, avec un historique dans `data/app_state/history`. Seuls les retours de séances et l'organisation sont transférés : aucun identifiant Garmin. La version est contrôlée avant écriture atomique. Les sauvegardes JSON séparées restent disponibles. La restauration d'organisation complète les horaires absents et conserve les contraintes valides existantes. Elle nécessite la même version du programme.

## Actualiser les cours

Télécharger un nouvel export MyDevinci puis, depuis le dossier du projet :

```powershell
.\.venv\Scripts\python.exe src/import_calendar.py "$env:USERPROFILE\Downloads\mon_calendrier.ics"
.\.venv\Scripts\python.exe src/build_triathlon_app.py
```

Recharger la page. Le nouvel export remplace la liste des cours plutôt que de s'y ajouter : un cours supprimé du nouvel export disparaît. Les horaires sportifs restent conservés, et les conflits sont recalculés. Les exports bruts sont archivés par empreinte dans `data/calendar/sources`, hors Git. Un export invalide n'écrase pas le calendrier actif. Les calendriers récurrents sont refusés explicitement ; l'export MyDevinci reçu contient des événements ponctuels.

## iPhone : étape encore à activer

Le serveur actuel écoute seulement sur le PC : `127.0.0.1:8765` ne fonctionne pas depuis l'iPhone. Aucun accès réseau externe n'a été activé.

Option proposée : accès privé HTTPS avec Tailscale sur le PC et l'iPhone, connectés au même réseau personnel. L'installation Tailscale a été tentée puis interrompue (code 1602) ; elle reste à terminer. Le choix de l'accès et la connexion du téléphone restent à faire avec l'utilisateur. Le PC devra être allumé et le serveur actif.

Après installation, connexion et vérification des appareils autorisés, Tailscale Serve peut publier le serveur local dans le réseau privé :

```powershell
tailscale serve --bg http://127.0.0.1:8765
```

Cette étape n'a PAS été exécutée. Ne pas utiliser Funnel pour ces données personnelles. La portée d'accès dépend des membres et règles du réseau Tailscale. Documentation : https://tailscale.com/docs/features/tailscale-serve

Après obtention de l'adresse HTTPS exacte, relancer le serveur avec cette origine autorisée (remplacer l'exemple, qui n'est pas une adresse réelle) :

```powershell
.\.venv\Scripts\python.exe src/serve_sessiondna.py --public-origin "https://NOM-DU-PC.NOM-DU-RESEAU.ts.net"
```

Le serveur continue à écouter uniquement sur localhost ; Tailscale assure l'accès distant privé. N'ajouter que l'origine de son réseau privé. Ce serveur personnel ne doit pas être déployé sur Internet sans une véritable authentification et une revue de déploiement.

Une fois l'adresse HTTPS opérationnelle, l'ouvrir dans Safari puis utiliser Partager → Sur l'écran d'accueil. Un essai sur l'iPhone reste nécessaire. Synchroniser depuis l'ancien navigateur PC puis depuis l'application du téléphone permet de récupérer les saisies : les stockages de Safari et d'une application installée peuvent être distincts.

## Vérifications réalisées

- Six tests Python : fuseau été/hiver, UTC, lignes repliées, dates entières, doublons, annulations, rejet des récurrences et fins invalides.
- Tests du moteur JavaScript : marges, sommeil, chevauchements, cours sur plusieurs jours, supplément piscine.
- Prévisualisation distincte : enregistrement de contraintes fictives, propositions, conflit volontaire avec un cours, conservation après rechargement. Aucun essai enregistré dans l'origine habituelle du site.
- Aucun horaire de train en direct : la gare finale et les durées réelles restent à préciser.
- Sauvegarde et récupération testées entre deux origines navigateur distinctes, avec un dossier serveur de test séparé des données réelles. Contrôle HTTP des origines et versions, archives et refus des clés inconnues testés.
