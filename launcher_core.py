"""
BlockWorldNeo Launcher - Core Logic
------------------------------------
Kapselt alles, was nichts mit der GUI zu tun hat:
- Konfiguration laden/speichern
- Minecraft-Versionen auflisten/installieren (Vanilla + Fabric)
- Minecraft starten
- Serverliste (servers.dat) lesen/schreiben
- Mod-Verwaltung (mods-Ordner)
"""

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import minecraft_launcher_lib as mll
import nbtlib
from nbtlib.tag import Compound, List, String, Byte

import minecraft_auth_from_launcher as launcher_auth

# ---------------------------------------------------------------------------
# Pfade & Konfiguration
# ---------------------------------------------------------------------------

APP_NAME = "SXMIR Launcher"

def default_game_dir() -> Path:
    """Plattform-typischer .minecraft Ordner."""
    home = Path.home()
    if sys.platform.startswith("win"):
        return Path(os.environ.get("APPDATA", home)) / ".minecraft"
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "minecraft"
    return home / ".minecraft"


CONFIG_DIR = Path.home() / ".sxmir_launcher"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "username": "Spieler",
    "account_mode": "offline",       # "offline" oder "microsoft"
    "game_dir": str(default_game_dir()),
    "java_path": "",                 # leer = automatisch ermitteln
    "ram_mb": 4096,
    "selected_version": "",
    "use_fabric": False,
    "favorite_servers": [
        {"name": "BlockWorldNeo", "address": "d2t76sy.eu.hostdservers.com"}
    ],
    "ms_client_id": "",              # eigene Azure-App-ID für Microsoft-Login
    "performance_mode": True,        # optimierte JVM-Flags (G1GC) für flüssigeres Spiel
}


def load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_CONFIG)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Versionen
# ---------------------------------------------------------------------------

def list_remote_versions(release_only: bool = True) -> list[str]:
    """Alle von Mojang verfügbaren Versionen (neueste zuerst)."""
    versions = mll.utils.get_version_list()
    if release_only:
        versions = [v for v in versions if v["type"] == "release"]
    return [v["id"] for v in versions]


def list_installed_versions(game_dir: str) -> list[str]:
    try:
        return [v["id"] for v in mll.utils.get_installed_versions(game_dir)]
    except Exception:
        return []


def install_vanilla(version: str, game_dir: str, progress_cb=None):
    """Installiert eine Vanilla-Version. progress_cb(status:str, current:int, total:int)."""
    callback = _build_callback(progress_cb)
    mll.install.install_minecraft_version(version, game_dir, callback=callback)


class FabricUnsupportedError(Exception):
    """Fabric bietet für diese Minecraft-Version (noch) keinen Loader an."""
    pass


def install_fabric_for(version: str, game_dir: str, progress_cb=None) -> str:
    """
    Installiert den Fabric-Loader für eine bestehende Vanilla-Version.
    Gibt die Versions-ID zurück, die zum Starten verwendet werden muss.

    Wirft FabricUnsupportedError, falls Fabric diese Minecraft-Version
    (noch) nicht unterstützt - das entscheidet FabricMC selbst und lässt
    sich nicht durch Code erzwingen. Die Vanilla-Installation bleibt davon
    unberührt und ist weiterhin normal spielbar (nur ohne Mod-Unterstützung).
    """
    if not mll.fabric.is_minecraft_version_supported(version):
        raise FabricUnsupportedError(
            f"Fabric unterstützt Minecraft {version} (noch) nicht. "
            f"Das kommt bei ganz neuen Versionen vor, bis FabricMC einen "
            f"passenden Loader veröffentlicht hat."
        )

    callback = _build_callback(progress_cb)
    mll.fabric.install_fabric(version, game_dir, callback=callback)
    # Fabric erzeugt eine eigene Versions-ID à la "fabric-loader-<x>-<mc-version>"
    installed = mll.utils.get_installed_versions(game_dir)
    for v in installed:
        if v["id"].startswith("fabric-loader") and version in v["id"]:
            return v["id"]
    raise RuntimeError("Fabric wurde installiert, aber die Versions-ID wurde nicht gefunden.")


def _build_callback(progress_cb):
    if progress_cb is None:
        return {}
    state = {"status": "", "max": 0, "value": 0}

    def set_status(text):
        state["status"] = text
        progress_cb(state["status"], state["value"], state["max"])

    def set_progress(value):
        state["value"] = value
        progress_cb(state["status"], state["value"], state["max"])

    def set_max(value):
        state["max"] = value
        progress_cb(state["status"], state["value"], state["max"])

    return {
        "setStatus": set_status,
        "setProgress": set_progress,
        "setMax": set_max,
    }


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

def offline_options(username: str) -> dict:
    """Erzeugt die Optionen für einen Offline-Account (kein echtes Mojang-Login)."""
    return {
        "username": username,
        "uuid": str(uuid.uuid3(uuid.NAMESPACE_DNS, username)),
        "token": "0",
        "user_type": "legacy",
    }


def read_official_launcher_account() -> dict | None:
    """
    Liest den aktiven Account aus dem OFFIZIELLEN Minecraft Launcher aus
    (Workaround, solange der eigene Microsoft-Login wegen fehlender
    XboxLive.signin-Berechtigung nicht funktioniert).

    Rückgabe: dict mit "username", "uuid", "token" oder None, falls der
    Nutzer sich nie im offiziellen Launcher eingeloggt hat / die Datei
    nicht gefunden/gelesen werden konnte.
    """
    return launcher_auth.get_active_account()


def microsoft_login_url(client_id: str, redirect_uri: str = "https://login.microsoftonline.com/common/oauth2/nativeclient"):
    """
    Liefert (login_url, state, code_verifier) für den Microsoft-OAuth-Flow.
    Erfordert eine eigene Azure-App-Registrierung (siehe README).
    """
    return mll.microsoft_account.get_login_url(client_id, redirect_uri)


def microsoft_complete_login(client_id: str, client_secret_or_none, auth_code: str,
                              redirect_uri: str, code_verifier: str) -> dict:
    login_data = mll.microsoft_account.complete_login(
        client_id, client_secret_or_none, redirect_uri, auth_code, code_verifier
    )
    return {
        "username": login_data["name"],
        "uuid": login_data["id"],
        "token": login_data["access_token"],
        "user_type": "msa",
    }


# ---------------------------------------------------------------------------
# Starten
# ---------------------------------------------------------------------------

def _supports_quick_play(version_id: str) -> bool:
    """
    Ab Minecraft 1.20 gibt es 'Quick Play' (--quickPlayMultiplayer) für Direct-Connect.
    Ältere Versionen nutzen die klassischen --server/--port Argumente.
    Extrahiert die zugrunde liegende MC-Version auch aus IDs wie
    'fabric-loader-0.15.0-1.20.1'.
    """
    import re
    match = re.search(r"(\d+)\.(\d+)(?:\.\d+)?$", version_id)
    if not match:
        return False
    major, minor = int(match.group(1)), int(match.group(2))
    return (major, minor) >= (1, 20)


def _performance_jvm_flags(ram_mb: int) -> list[str]:
    """
    Bekannt als "Aikar's Flags" - eine bewährte G1GC-Konfiguration, die
    Ruckler/Lag-Spikes durch bessere Garbage-Collection-Pausen deutlich
    reduziert. Verändert keine Spielinhalte, nur wie die JVM Speicher verwaltet.
    """
    # Bei wenig RAM lieber konservativ bleiben, sonst kann die JVM selbst stottern.
    region_size = "16M" if ram_mb >= 8192 else "8M" if ram_mb >= 4096 else "4M"
    return [
        "-XX:+UseG1GC",
        "-XX:+ParallelRefProcEnabled",
        "-XX:MaxGCPauseMillis=200",
        "-XX:+UnlockExperimentalVMOptions",
        "-XX:+DisableExplicitGC",
        "-XX:+AlwaysPreTouch",
        f"-XX:G1NewSizePercent=30",
        f"-XX:G1MaxNewSizePercent=40",
        f"-XX:G1HeapRegionSize={region_size}",
        "-XX:G1ReservePercent=20",
        "-XX:G1HeapWastePercent=5",
        "-XX:G1MixedGCCountTarget=4",
        "-XX:InitiatingHeapOccupancyPercent=15",
        "-XX:G1MixedGCLiveThresholdPercent=90",
        "-XX:G1RSetUpdatingPauseTimePercent=5",
        "-XX:SurvivorRatio=32",
        "-XX:+PerfDisableSharedMem",
        "-XX:MaxTenuringThreshold=1",
    ]


def launch(version_id: str, game_dir: str, account_options: dict,
           ram_mb: int = 4096, java_path: str = "",
           direct_connect: str | None = None,
           performance_mode: bool = True) -> subprocess.Popen:
    """
    direct_connect: optional "host" oder "host:port" - Minecraft startet und
    verbindet sich automatisch mit diesem Server (kein manuelles Verbinden im Spiel nötig).
    performance_mode: setzt optimierte JVM-Flags (G1GC-Tuning) für flüssigeres,
    stotterfreieres Spiel. Ersetzt keine Grafik-Mods (z.B. Sodium) - die JVM-Flags
    wirken auf die Java-Ebene (Speicherverwaltung), nicht auf die Render-Engine.
    """
    jvm_args = [f"-Xmx{ram_mb}M", f"-Xms{max(512, ram_mb // 2)}M"]
    if performance_mode:
        jvm_args += _performance_jvm_flags(ram_mb)

    options = {
        "username": account_options["username"],
        "uuid": account_options["uuid"],
        "token": account_options["token"],
        # Entscheidend für echte Microsoft-Accounts (Launcher-Session/Microsoft-Login):
        # ohne "msa" versucht Minecraft, den Token über die veraltete Mojang-Legacy-Prüfung
        # zu validieren, was bei echten MSA-Tokens zu "Ungültige Sitzung" führt.
        "userType": account_options.get("user_type", "msa"),
        "jvmArguments": jvm_args,
    }
    if java_path:
        options["executablePath"] = java_path

    if direct_connect:
        host, _, port = direct_connect.partition(":")
        port = port or "25565"
        if _supports_quick_play(version_id):
            options["quickPlayMultiplayer"] = f"{host}:{port}"
        else:
            options["server"] = host
            options["port"] = port

    command = mll.command.get_minecraft_command(version_id, game_dir, options)
    return subprocess.Popen(command, cwd=game_dir)


# ---------------------------------------------------------------------------
# Serverliste (servers.dat)
# ---------------------------------------------------------------------------

def _servers_dat_path(game_dir: str) -> Path:
    return Path(game_dir) / "servers.dat"


def read_servers(game_dir: str) -> list[dict]:
    path = _servers_dat_path(game_dir)
    if not path.exists():
        return []
    try:
        nbt_file = nbtlib.load(str(path))
        entries = nbt_file.get("servers", [])
        return [{"name": str(e.get("name", "")), "address": str(e.get("ip", ""))} for e in entries]
    except Exception:
        return []


def write_servers(game_dir: str, servers: list[dict]) -> None:
    """Schreibt die komplette Serverliste (ersetzt servers.dat)."""
    path = _servers_dat_path(game_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    entries = List[Compound]([
        Compound({"name": String(s["name"]), "ip": String(s["address"]), "hidden": Byte(0)})
        for s in servers
    ])
    root = Compound({"servers": entries})
    nbt_file = nbtlib.File(root)
    nbt_file.save(str(path))


def add_favorite_server(game_dir: str, name: str, address: str) -> None:
    servers = read_servers(game_dir)
    if not any(s["address"] == address for s in servers):
        servers.insert(0, {"name": name, "address": address})
        write_servers(game_dir, servers)


# ---------------------------------------------------------------------------
# Mod-Verwaltung
# ---------------------------------------------------------------------------

def mods_dir(game_dir: str) -> Path:
    d = Path(game_dir) / "mods"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_mods(game_dir: str) -> list[dict]:
    """Liste aller Mods im mods-Ordner. Deaktivierte Mods enden auf .jar.disabled."""
    result = []
    for f in sorted(mods_dir(game_dir).iterdir()):
        if f.suffix == ".jar":
            result.append({"filename": f.name, "enabled": True, "path": str(f)})
        elif f.name.endswith(".jar.disabled"):
            result.append({"filename": f.name[:-9], "enabled": False, "path": str(f)})
    return result


def toggle_mod(game_dir: str, filename: str, enable: bool) -> None:
    base = mods_dir(game_dir)
    if enable:
        src = base / f"{filename}.disabled"
        dst = base / filename
    else:
        src = base / filename
        dst = base / f"{filename}.disabled"
    if src.exists():
        src.rename(dst)


def add_mod_file(game_dir: str, source_path: str) -> None:
    import shutil
    src = Path(source_path)
    dst = mods_dir(game_dir) / src.name
    shutil.copy2(src, dst)


def remove_mod(game_dir: str, filename: str, currently_enabled: bool) -> None:
    base = mods_dir(game_dir)
    target = base / (filename if currently_enabled else f"{filename}.disabled")
    if target.exists():
        target.unlink()


# ---------------------------------------------------------------------------
# Singleplayer-Welten
# ---------------------------------------------------------------------------

def saves_dir(game_dir: str) -> Path:
    d = Path(game_dir) / "saves"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_worlds(game_dir: str) -> list[dict]:
    """Liste aller Singleplayer-Welten (Ordnername + hübscher Name aus level.dat, falls lesbar)."""
    worlds = []
    for d in sorted(saves_dir(game_dir).iterdir()):
        if not d.is_dir():
            continue
        level_dat = d / "level.dat"
        display_name = d.name
        if level_dat.exists():
            try:
                nbt_file = nbtlib.load(str(level_dat), gzipped=True)
                data = nbt_file.get("Data", {})
                name = data.get("LevelName")
                if name:
                    display_name = str(name)
            except Exception:
                pass
        worlds.append({"folder": d.name, "name": display_name, "path": str(d)})
    return worlds


def delete_world(game_dir: str, folder: str) -> None:
    import shutil
    target = saves_dir(game_dir) / folder
    if target.exists():
        shutil.rmtree(target)


def open_folder(path: str) -> None:
    path = str(path)
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])
