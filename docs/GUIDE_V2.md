# Utiliser et comprendre SessionDNA V2

## 1. Ce que fait concrètement l’application

Tu disposes d’un carnet de préparation triathlon. Le programme indique ce qui était prévu ; Garmin décrit ce qui a été enregistré ; tes retours expliquent ce qui s’est réellement passé et comment tu l’as vécu. L’application garde ces trois informations distinctes, puis les rassemble dans le bilan de la semaine.

L’interface ne construit pas un nouveau programme sportif à ta place. Tu demandes la semaine suivante dans ta conversation IRON MAN et importes son JSON dans Réglages. Une semaine déjà importée est reconnue ; une version différente est conservée séparément.

## 2. Ta routine

1. **Réglages → Programme IRON MAN** : choisir le fichier JSON reçu. Sélectionner ensuite la semaine en haut de l’écran.
2. **Réglages → Emploi du temps** : importer le fichier ICS de MyDevinci. Vérifier début/fin de journée, transport, préparation et vestiaire. Les durées de trajet sont des estimations que tu peux modifier.
3. **Semaine** : lire les séances et leurs blocs ; choisir les horaires. Un conflit signale un chevauchement avec cours, transport, sommeil ou une autre séance. La date prescrite et le contenu sportif ne sont pas réécrits.
4. Après l’entraînement, ouvrir la séance et enregistrer son statut, sa durée, son RPE, ses sensations et, si pertinent, son lien avec l’activité Garmin. « Pas de retour » ne signifie pas « séance ratée ».
5. **Réglages → Actualiser** : importer les activités manquantes puis recalculer les analyses. Sans la case Garmin, seuls les fichiers déjà présents sont traités.
6. **Bilan → Exporter pour IRON MAN** : synchroniser les retours, télécharger le Markdown et le transmettre à la conversation. Aucun message n’est envoyé automatiquement.

Le ressenti du jour est conservé dans un journal distinct. Le bilan hebdomadaire utilise actuellement les retours des séances ; ne pas supposer que chaque note du journal y figure.

## 3. Comprendre les analyses

**Une activité n’est pas seulement sa fréquence cardiaque moyenne.** Le catalogue rassemble sport, chronologie, durée active et écoulée, distance, vitesse, puissance et fréquence cardiaque disponibles. Un lien vélo-course peut suggérer un brick ; c’est un contexte à confirmer, pas une conclusion fondée sur un BPM faible.

**Pauses.** Mettre la montre en pause interrompt temporairement l’effort enregistré. Les événements de chronomètre et les trous séparent les segments. Ils ne sont pas transformés automatiquement en récupération entre deux répétitions. La durée écoulée et la durée chronométrée restent distinctes.

**Segmentation avec ruptures.** L’algorithme PELT recherche des changements dans la vitesse ou la puissance. La pénalisation règle le compromis entre détails et surdécoupage. Un changement statistique peut venir du terrain ou d’une mesure : il ne garantit pas un bloc VO2max ou seuil.

**Le modèle de course.** La forêt existante utilise six variables : durée chronométrée, vitesse moyenne, variabilité de vitesse, rapport vitesse fin/début, fréquence cardiaque moyenne et variabilité cardiaque. Les valeurs manquantes passent par l’imputation apprise initialement. Le modèle est gelé : ses paramètres ne changent pas lorsque tu ouvres l’application.

**SHAP.** Pour une séance du jeu d’origine, les contributions montrent comment les variables déplacent la sortie de la forêt par rapport à sa valeur de référence. Leur somme est vérifiée. Une contribution n’est pas une cause physiologique ni une probabilité médicalement interprétable. Une séance hors du jeu d’origine peut ne pas avoir d’explication ; l’interface l’indique.

**DuckDB et Parquet.** SQL calcule les totaux par semaine et sport. Parquet stocke les données en colonnes pour les réutiliser efficacement. Les dates sont regroupées en Europe/Paris et les valeurs absentes restent explicites.

**MLflow.** Le registre local conserve le modèle, les métriques existantes et les empreintes des fichiers de l’expérience. Il assure la traçabilité ; il ne crée pas de nouveaux résultats de performance. Le modèle et les annotations initiaux restent inchangés.

**GPS.** Le tracé est décodé lorsque tu le demandes et affiché sur un fond neutre. Aucun fond de carte externe n’est configuré. Sa longueur géométrique peut différer de la distance Garmin, notamment après réduction du nombre de points.

## 4. Pourquoi une API et une base de données ?

Le navigateur affiche les écrans ; FastAPI lit les résultats et valide les imports ; SQLite conserve les saisies avec une révision. Si ton PC et ton téléphone changent des champs différents, ils peuvent être fusionnés. S’ils changent le même champ différemment, l’application te présente le conflit avant de choisir.

Les retours restent liés à l’empreinte exacte du programme. La migration initiale lit `current.json`, sans modifier cet ancien fichier. Le serveur n’accepte les écritures que depuis son origine locale ou l’origine HTTPS privée configurée. Cela ne constitue pas une authentification adaptée à un serveur public : ne pas exposer ce service directement sur Internet.

Le projet est actuellement dans OneDrive. SQLite doit être utilisé par un seul serveur sur ce PC, jamais comme fichier ouvert simultanément par plusieurs PC via OneDrive. Pour une installation permanente, privilégier un dossier local pour la base et des sauvegardes exportées vers OneDrive.

## 5. Sauvegarde et connexion interrompue

Exporter les saisies fournit un JSON restaurable. L’archive serveur contient un `state.json` du même format à extraire avant restauration. La restauration remplace les sections présentes et exporte la version précédente. Les conflits sont sauvegardés avant résolution.

Le cache de l’application rend disponibles les écrans et activités déjà chargés sur cet appareil. Les saisies restent locales en attendant le serveur. Un premier accès hors connexion, des analyses jamais ouvertes, une actualisation Garmin et un bilan serveur récent ne sont pas disponibles sans connexion. Le cache contient des données personnelles : utiliser ton propre appareil.

## 6. IA optionnelle

Le bilan principal est calculé et fonctionne sans IA générative. Le connecteur Pydantic AI est présent et testé sans requête externe, mais désactivé par défaut. Il autorise le modèle à sélectionner des identifiants de faits vérifiés et de questions ; l’application restitue les textes sources. Il ne peut pas inventer des valeurs, prescrire une semaine ni modifier le programme.

Pour un modèle déjà disponible dans Ollama sur ce PC, configurer les variables suivantes avant de démarrer le serveur (remplacer la valeur de modèle par un nom réellement installé) :

```powershell
$env:SESSIONDNA_AI_ENABLED='1'
$env:SESSIONDNA_AI_PROVIDER='ollama'
$env:SESSIONDNA_AI_MODEL='NOM_DU_MODELE_INSTALLE'
$env:SESSIONDNA_AI_BASE_URL='http://127.0.0.1:11434/v1'
.\.venv\Scripts\python.exe src/serve_sessiondna.py
```

Aucun modèle n’est téléchargé par l’application. Un fournisseur distant compatible est une autre option à configurer explicitement ; il recevrait les informations du bilan. Le fonctionnement livré n’envoie pas ces données à un fournisseur externe.

## 7. Ce qui demande encore ton usage ou de nouvelles données

- Installer le raccourci sur l’iPhone après activation de l’accès privé HTTPS et vérifier un vrai retour entre téléphone et PC.
- Importer les prochaines semaines et nouveaux exports de cours ; revérifier les horaires de piscine au-delà de leur période de validité.
- Confirmer tes durées de trajet. Les horaires et perturbations des RER A / ligne L ne sont pas reliés.
- Annoter davantage de séances, surtout les catégories rares, vélo et natation, puis définir un nouveau protocole d’évaluation avant de réentraîner.
- Vérifier le programme et l’organisation sur une semaine réelle. L’application signale des contraintes, elle ne connaît pas encore tous tes impératifs personnels.

Ce sont des limites explicites de la version livrée, pas des fonctions supposées actives.
