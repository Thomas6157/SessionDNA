"""Importer les activités Garmin manquantes, sans modifier les originaux existants."""

from pathlib import Path
import argparse
from datetime import datetime, timezone
from getpass import getpass
from importlib.metadata import version
import io
import json
import logging
import os
import re
import sys
import time
import warnings
import zipfile

import fitdecode
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)


MAX_FIT_BYTES = 64 * 1024 * 1024


class ImportProblem(Exception):
    """Message maîtrisé pouvant être affiché sans exposer d'identifiant de session."""


class NoFitExport(ImportProblem):
    pass


def atomic_json(path, data):
    """Remplacer l'état seulement après avoir terminé son écriture."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def validate_fit(payload):
    if len(payload) < 14 or payload[8:12] != b".FIT":
        raise ImportProblem("Le contenu téléchargé n'est pas un fichier FIT.")
    if len(payload) > MAX_FIT_BYTES:
        raise ImportProblem("FIT trop volumineux pour cette première version (64 Mio maximum).")
    # Vérifier le décodage et les CRC avant d'écrire quoi que ce soit dans data/raw.
    has_activity_data = False
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with fitdecode.FitReader(io.BytesIO(payload), check_crc=fitdecode.CrcCheck.RAISE) as reader:
            for message in reader:
                if isinstance(message, fitdecode.FitDataMessage) and message.name in ("record", "session"):
                    has_activity_data = True
    if not has_activity_data:
        raise ImportProblem("Le FIT ne contient pas de données d'activité reconnues.")
    return payload


def extract_fit(payload):
    """Lire un FIT direct ou un FIT dans un ZIP ; ne jamais extraire les chemins du ZIP."""
    if not isinstance(payload, bytes):
        raise ImportProblem("Réponse de téléchargement inattendue.")
    if len(payload) > 2 * MAX_FIT_BYTES:
        raise ImportProblem("Archive reçue trop volumineuse.")
    buffer = io.BytesIO(payload)
    if zipfile.is_zipfile(buffer):
        with zipfile.ZipFile(buffer) as archive:
            fits = [item for item in archive.infolist() if not item.is_dir() and item.filename.lower().endswith(".fit")]
            if not fits:
                raise NoFitExport("L'export original ne contient aucun FIT (activité manuelle ou autre format possible).")
            if len(fits) != 1:
                raise ImportProblem("Plusieurs FIT dans l'archive : import manuel à vérifier.")
            if fits[0].file_size > MAX_FIT_BYTES:
                raise ImportProblem("FIT décompressé trop volumineux.")
            # Le nom contenu dans l'archive n'est jamais utilisé comme destination.
            payload = archive.read(fits[0])
    elif payload[8:12] != b".FIT":
        if payload.lstrip().startswith(b"<?xml") or b"<gpx" in payload[:200].lower():
            raise NoFitExport("L'export original est un autre format que FIT.")
    return validate_fit(payload)


def write_new_file(path, payload):
    """Le mode xb refuse d'écraser un fichier existant."""
    created = False
    complete = False
    try:
        with path.open("xb") as stream:
            created = True
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        complete = True
    finally:
        if created and not complete:
            path.unlink(missing_ok=True)


def connect(token_dir, allow_login):
    # Les identifiants sont saisis par l'utilisateur dans son terminal, jamais en arguments.
    logging.getLogger("garminconnect").setLevel(logging.CRITICAL)
    if allow_login:
        if not sys.stdin.isatty():
            raise ImportProblem("La connexion doit être lancée dans ton terminal interactif VS Code.")
        print("Connexion Garmin locale. Ne partage pas le mot de passe ni le code de validation.")
        email = input("Adresse e-mail Garmin : ").strip()
        password = getpass("Mot de passe Garmin (saisie invisible) : ")
        api = Garmin(email=email, password=password,
                     prompt_mfa=lambda: getpass("Code de double authentification Garmin : ").strip(),
                     retry_attempts=1)
        password = None
        token_dir.mkdir(parents=True, exist_ok=True)
        api.login(str(token_dir))
        print("Connexion réussie. La session est conservée localement pour les prochains imports.")
    else:
        if not token_dir.exists():
            raise ImportProblem("Première connexion nécessaire : relance avec --login.")
        api = Garmin(retry_attempts=1)
        api.login(str(token_dir))
        print("Session Garmin restaurée.")
    return api


def synchronize(api, raw_dir, state_dir, sport="all", max_new=None,
                page_size=50, max_pages=200, delay=1.0, retry_unavailable=False):
    raw_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "sync_state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(state.get("activities"), dict):
            raise ImportProblem("État de synchronisation invalide ; ne pas le remplacer sans examen.")
    else:
        state = {"schema_version": 1, "activities": {}}
    report = {"started_utc": datetime.now(timezone.utc).isoformat(), "sport_filter": sport,
              "downloaded": 0, "existing": 0, "unavailable": 0, "errors": 0,
              "complete_history_scan": False, "stop_reason": "", "items": []}
    existing_ids = {}
    for path in raw_dir.iterdir():
        match = re.fullmatch(r"([0-9]+)_ACTIVITY\.fit", path.name, flags=re.IGNORECASE)
        if path.is_file() and match:
            existing_ids[match.group(1)] = path
    seen = set()

    def checkpoint():
        state["last_run_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_json(state_path, state)
        atomic_json(state_dir / "sync_report.json", report)

    try:
        offset = 0
        for page in range(max_pages):
            activities = api.get_activities(offset, page_size, activitytype=None if sport == "all" else sport)
            if not isinstance(activities, list):
                raise ImportProblem("La liste des activités a changé de format ; bibliothèque à vérifier.")
            if not activities:
                report.update(complete_history_scan=True, stop_reason="Historique parcouru.")
                break
            new_ids_in_page = 0
            for activity in activities:
                activity_id = str(activity.get("activityId", "")) if isinstance(activity, dict) else ""
                if not re.fullmatch(r"[1-9][0-9]*", activity_id):
                    raise ImportProblem("Identifiant d'activité invalide reçu de Garmin.")
                if activity_id in seen:
                    continue
                seen.add(activity_id)
                new_ids_in_page += 1
                filename = f"{activity_id}_ACTIVITY.fit"
                kind = activity.get("activityType") or {}
                entry = {"activity_id": activity_id, "filename": filename,
                         "start_utc": activity.get("startTimeGMT"),
                         "sport": kind.get("typeKey") if isinstance(kind, dict) else None,
                         "activity_name": activity.get("activityName"), "message": ""}
                previous = state["activities"].get(activity_id, {})
                if activity_id in existing_ids:
                    entry["status"] = "existing"
                    report["existing"] += 1
                elif previous.get("status") == "no_fit" and not retry_unavailable:
                    entry.update(status="no_fit", message="Export sans FIT déjà signalé ; --retry-unavailable pour réessayer.")
                    report["unavailable"] += 1
                else:
                    print(f"Téléchargement : {filename}", flush=True)
                    time.sleep(delay)
                    try:
                        payload = api.download_activity(activity_id, dl_fmt=Garmin.ActivityDownloadFormat.ORIGINAL)
                        fit = extract_fit(payload)
                        write_new_file(raw_dir / filename, fit)
                        existing_ids[activity_id] = raw_dir / filename
                        entry["status"] = "downloaded"
                        report["downloaded"] += 1
                    except (GarminConnectAuthenticationError, GarminConnectTooManyRequestsError, GarminConnectConnectionError):
                        # Arrêter le lot : ne pas multiplier les requêtes en cas de refus ou panne.
                        raise
                    except NoFitExport as exc:
                        entry.update(status="no_fit", message=str(exc))
                        report["unavailable"] += 1
                    except ImportProblem as exc:
                        entry.update(status="error", message=str(exc))
                        report["errors"] += 1
                    except FileExistsError:
                        entry.update(status="existing", message="Fichier créé entre-temps, conservé.")
                        report["existing"] += 1
                    except Exception as exc:
                        entry.update(status="error", message=f"Import non effectué ({type(exc).__name__}).")
                        report["errors"] += 1
                state["activities"][activity_id] = entry
                report["items"].append({"activity_id": activity_id, "status": entry["status"], "message": entry["message"]})
                checkpoint()
                if max_new is not None and report["downloaded"] >= max_new:
                    report["stop_reason"] = "Limite de nouveaux fichiers atteinte ; relancer pour poursuivre."
                    return report
            if new_ids_in_page == 0:
                raise ImportProblem("Garmin renvoie une page déjà parcourue ; arrêt pour éviter une boucle.")
            offset += len(activities)
            time.sleep(delay)
        else:
            raise ImportProblem("Limite de pages atteinte ; l'historique n'a pas été entièrement parcouru.")
        return report
    except BaseException:
        report["stop_reason"] = "Import interrompu ; les fichiers déjà enregistrés sont conservés."
        raise
    finally:
        checkpoint()


def main():
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", action="store_true", help="Autoriser la saisie locale des identifiants et du code MFA")
    parser.add_argument("--max-new", type=int, default=None, help="Limiter le nombre de nouveaux FIT, par exemple 5 pour le premier essai")
    parser.add_argument("--sport", choices=["all", "running", "cycling", "swimming"], default="all")
    parser.add_argument("--retry-unavailable", action="store_true", help="Réessayer les exports précédemment sans FIT")
    parser.add_argument("--check", action="store_true", help="Vérifier l'installation, sans connexion ni lecture de jetons")
    args = parser.parse_args()
    if args.max_new is not None and args.max_new < 1:
        parser.error("--max-new doit être supérieur ou égal à 1")
    if args.check:
        print(f"garminconnect {version('garminconnect')} ; fitdecode {version('fitdecode')} : disponibles.")
        print("Aucun accès à Garmin ni aux identifiants pendant cette vérification.")
        return
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise ImportProblem("Cette configuration attend Windows et la variable LOCALAPPDATA.")
    token_dir = Path(local_app_data) / "SessionDNA" / "GarminTokens"
    state_dir = project / "data/sync"
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / "sync.lock"
    try:
        lock = lock_path.open("x", encoding="utf-8")
    except FileExistsError:
        raise ImportProblem("Un import est déjà lancé, ou sync.lock reste après une interruption. Vérifier avant de le retirer.") from None
    try:
        with lock:
            lock.write(str(os.getpid()))
        api = connect(token_dir, args.login)
        report = synchronize(api, project / "data/raw", state_dir, sport=args.sport,
                             max_new=args.max_new, retry_unavailable=args.retry_unavailable)
        print(f"\nNouveaux FIT : {report['downloaded']} ; déjà présents : {report['existing']} ; "
              f"sans FIT : {report['unavailable']} ; erreurs : {report['errors']}.")
        print(report["stop_reason"])
        print("Bilan : data/sync/sync_report.json")
        if report["errors"]:
            raise SystemExit(2)
    finally:
        lock_path.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main()
    except GarminConnectTooManyRequestsError:
        print("Garmin limite les requêtes. Import arrêté ; attendre avant de relancer.", file=sys.stderr)
        raise SystemExit(3)
    except GarminConnectAuthenticationError:
        print("Connexion refusée ou session expirée. Vérifier les identifiants puis relancer avec --login.", file=sys.stderr)
        raise SystemExit(3)
    except GarminConnectConnectionError:
        print("Garmin est inaccessible ou refuse la connexion. Import arrêté ; réessayer plus tard.", file=sys.stderr)
        raise SystemExit(3)
    except ImportProblem as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
    except KeyboardInterrupt:
        print("\nImport interrompu. Les activités déjà importées sont conservées.")
        raise SystemExit(130)
    except Exception as exc:
        # Pas de corps de réponse ni de jeton dans le terminal ou les journaux.
        print(f"Import arrêté ({type(exc).__name__}). Les détails de connexion ne sont pas affichés.", file=sys.stderr)
        raise SystemExit(2)
