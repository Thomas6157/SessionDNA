# Mise en service de SessionDNA

## Réalisé et vérifié

- Historique Garmin actualisé : 411 activités, sept nouvelles importées sans erreur. La reconstruction a abouti.
- Calendrier : 563 événements, 15 créneaux dans la semaine du 28 septembre.
- Détection des conflits, marges, propositions et conservation des horaires testées.
- Retours : essai fictif d'un footing, génération du bilan, durée et commentaire présents, absences de retours correctement marquées comme inconnues.
- Sauvegarde automatique après enregistrement vérifiée sur un serveur de test séparé. Aucune séance fictive ajoutée à la version habituelle.
- Récupération entre deux origines navigateur testée précédemment. Les modifications concurrentes sont vérifiées par tests ; un conflit ne doit pas être résolu par écrasement silencieux.
- Actualisation quotidienne à 8 h configurée dans Codex : « Actualiser SessionDNA ». Pas de notification en cas de fonctionnement normal ; intervention demandée en cas d'échec. Ce n'est pas un service indépendant de Codex.

## À compléter avec les informations réelles

Les horaires de sommeil, le temps de trajet porte-à-porte, les créneaux de piscine et la gare finale ne sont pas connus. Les champs sont donc laissés vides. Les horaires proposés ne seront pertinents qu'après leur saisie. Le programme n'a pas été déplacé arbitrairement.

## Accès iPhone : blocage concret

L'installation du paquet officiel Tailscale 1.102.4 via winget a commencé, son téléchargement a été vérifié, puis l'installateur a renvoyé 1602 : installation annulée. Elle n'a pas été relancée de force.

1. Installer Tailscale depuis https://tailscale.com/download/windows sur le PC et depuis l'App Store sur l'iPhone.
2. Se connecter personnellement au même compte sur les deux appareils. Ne pas envoyer de mot de passe dans la conversation.
3. Vérifier les membres autorisés dans le réseau privé, puis terminer la configuration HTTPS privée avec Codex. Le serveur n'est pas publié sur Internet.
4. Ouvrir l'adresse privée obtenue dans Safari, puis Partager → Sur l'écran d'accueil.
5. Vérifier l'affichage, enregistrer un vrai retour puis vérifier sa récupération sur le PC. Faire aussi un essai hors Wi-Fi domestique si l'accès privé distant est choisi.

L'installation sur l'iPhone et l'essai réel ne peuvent pas être remplacés par une simulation navigateur. Le PC devra rester allumé et SessionDNA lancé pour répondre aux requêtes.

## Une semaine d'usage réel

La semaine d'essai n'est pas déclarée terminée à l'avance. Chaque jour :

- Comparer les cours affichés avec MyDevinci ; télécharger un nouvel ICS si nécessaire.
- Vérifier le placement et les enchaînements ; ajuster les créneaux si la piscine, les repas ou les transports l'exigent.
- Après l'entraînement, enregistrer le ressenti et vérifier le message de sauvegarde sur le PC.
- Sur l'autre appareil, utiliser la synchronisation pour récupérer les nouvelles données et recharger après la récupération.

En fin de semaine : préparer le bilan, vérifier les séances modifiées/manquées et les champs inconnus, puis le copier personnellement dans IRON MAN. L'application n'envoie pas de message à cette conversation. Conserver un export des retours et de l'organisation.

## Limites restantes

Pas de synchronisation directe MyDevinci ni de transports en temps réel. Pas de disponibilité du serveur lorsque le PC est éteint. Les annotations supplémentaires et modèles vélo/natation sont hors de cette mise en service. L'accès mobile reste bloqué par l'installation/connexion décrite ci-dessus.
