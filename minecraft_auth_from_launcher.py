"""
minecraft_auth_from_launcher.py
--------------------------------
Liest die bereits bestehende Login-Session des OFFIZIELLEN Minecraft Launchers
(minecraft.net) aus, statt selbst einen Microsoft-OAuth-Flow durchzuführen.

Hintergrund: Ein eigener Azure-App-Login scheitert aktuell an
AzureAppNotPermitted / fehlender XboxLive.signin-Berechtigung, da Microsoft
diese für neue Apps nur noch über eine offizielle ID@Xbox-Registrierung
vergibt. Als Workaround nutzen wir die Zugangsdaten, die der offizielle
Launcher nach einem erfolgreichen Login lokal speichert.

Die Datei liegt unter:
    Windows: %APPDATA%\\.minecraft\\launcher_accounts.json
    macOS:   ~/Library/Application Support/minecraft/launcher_accounts.json
    Linux:   ~/.minecraft/launcher_accounts.json

Voraussetzung: Der Nutzer muss sich MINDESTENS EINMAL im offiziellen
Minecraft Launcher eingeloggt haben. Der Access-Token darin ist zeitlich
begrenzt gültig (üblicherweise recht kurz) - läuft er ab, muss sich der
Nutzer im offiziellen Launcher erneut einloggen, damit die Datei aktualisiert
wird.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional, TypedDict


class LauncherAccount(TypedDict):
    username: str
    uuid: str
    token: str
    user_type: str


def _official_launcher_dir() -> Path:
    """Plattform-typischer Ordner des OFFIZIELLEN Minecraft Launchers."""
    home = Path.home()
    if sys.platform.startswith("win"):
        return Path(os.environ.get("APPDATA", home)) / ".minecraft"
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "minecraft"
    return home / ".minecraft"


def _launcher_accounts_path() -> Path:
    return _official_launcher_dir() / "launcher_accounts.json"


def get_active_account() -> Optional[LauncherAccount]:
    """
    Liest den aktuell im offiziellen Launcher aktiven Account aus.

    Rückgabe:
        dict mit "username", "uuid", "token" - passend zu den Optionen,
        die minecraft_launcher_lib / launcher_core.launch() erwartet.
        None, falls die Datei fehlt, kein aktiver Account gesetzt ist,
        oder die Datei nicht lesbar/erwartungsgemäß aufgebaut ist.
    """
    path = _launcher_accounts_path()
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    accounts = data.get("accounts", {})
    active_id = data.get("activeAccountLocalId")
    if not accounts or not active_id or active_id not in accounts:
        return None

    account = accounts[active_id]

    try:
        username = account["minecraftProfile"]["name"]
        mc_uuid = account["minecraftProfile"]["id"]
        access_token = account["accessToken"]
    except KeyError:
        return None

    return {
        "username": username,
        "uuid": mc_uuid,
        "token": access_token,
        "user_type": "msa",
    }


def has_official_login() -> bool:
    """Kurzer Check, ohne die vollen Kontodaten zu benötigen (für UI-Anzeigen)."""
    return get_active_account() is not None


def _debug_token_info() -> str:
    """Nur für Diagnosezwecke: zeigt, ob der Token laut Datei noch gültig ist (ohne den Token selbst preiszugeben)."""
    path = _launcher_accounts_path()
    if not path.exists():
        return "launcher_accounts.json nicht gefunden."
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return f"Datei nicht lesbar: {e}"

    accounts = data.get("accounts", {})
    active_id = data.get("activeAccountLocalId")
    if not active_id or active_id not in accounts:
        return "Kein aktiver Account in der Datei gesetzt."

    account = accounts[active_id]
    expires_at = account.get("accessTokenExpiresAt", "unbekannt")
    return f"accessTokenExpiresAt (laut Datei): {expires_at}"


def check_token_live(token: str) -> str:
    """
    Fragt den Token DIREKT bei Mojang an (unabhängig vom Spiel), um zu sehen,
    ob der Token selbst gültig ist oder ob Mojang ihn ablehnt.
    Gibt einen kurzen Klartext-Status zurück (kein Token-Inhalt wird ausgegeben).
    """
    import requests
    try:
        resp = requests.get(
            "https://api.minecraftservices.com/minecraft/profile",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.RequestException as e:
        return f"Netzwerkfehler bei der Prüfung: {e}"

    if resp.status_code == 200:
        return f"Token ist bei Mojang GÜLTIG (Status 200). Profil: {resp.json().get('name', '?')}"
    return f"Token wird von Mojang ABGELEHNT (Status {resp.status_code}). Antwort: {resp.text[:200]}"


if __name__ == "__main__":
    acc = get_active_account()
    if acc:
        print(f"Aktiver Account: {acc['username']} ({acc['uuid']})")
        print(_debug_token_info())
        print(check_token_live(acc["token"]))
    else:
        print("Kein aktiver Account im offiziellen Launcher gefunden. "
              "Bitte erst im offiziellen Minecraft Launcher einloggen.")
