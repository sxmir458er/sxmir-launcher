# SXMIR Launcher

Ein eigener Minecraft-Launcher – optisch angelehnt an den **Norisk Client** (dunkles Theme,
Sidebar-Navigation, grüner Akzent), funktional an den offiziellen Launcher.

## Funktionen

- **Play**: Minecraft-Version wählen, herunterladen/installieren, optional mit Fabric-Loader, starten
- **Servers**: eigene Serverliste – schreibt direkt in die echte `servers.dat`, dein Server
  (`d2t76sy.eu.hostdservers.com`) ist standardmäßig vorgetragen
- **Worlds**: alle Singleplayer-Welten anzeigen, öffnen, löschen
- **Mods**: `mods`-Ordner verwalten – Mods hinzufügen, aktivieren/deaktivieren, entfernen
- **Account**: Offline-Name (für deinen eigenen Server) oder Microsoft-Login (für Premium-Server)
- **Settings**: Spielordner, Java-Pfad, RAM-Zuteilung

## Installation

Voraussetzung: **Python 3.10+** und **Java** (für Minecraft selbst) müssen auf deinem PC installiert sein.

```bash
cd blockworldneo-launcher
pip install -r requirements.txt
python main.py
```

## Erster Start

1. Tab **Account** öffnen, deinen Anzeigenamen eintragen (offline) und speichern.
   Das reicht für deinen eigenen Server, solange dort `online-mode: false` in der
   `server.properties` steht (bei selbst gehosteten Servern meist Standard).
2. Tab **Play** öffnen, eine Version wählen (z.B. `1.21.11`, passend zu deinem Paper-Server),
   ggf. "Fabric-Loader installieren" aktivieren, wenn du Client-Mods nutzen willst,
   auf **Installieren** klicken und warten.
3. Auf **Spielen** klicken.
4. Tab **Servers**: dein Server ist schon eingetragen. Weitere Server über die Felder oben
   hinzufügen ("+ Hinzufügen") – sie erscheinen sofort in der Serverliste im Spiel.

## Mods hinzufügen

1. In **Play** einmal "Fabric-Loader installieren" aktivieren und installieren
   (Fabric ist die Voraussetzung für die meisten Client-Mods).
2. In **Mods** auf "+ .jar hinzufügen" klicken und die Mod-Datei (von z.B. Modrinth/CurseForge)
   auswählen. Mods lassen sich einzeln per Schalter an/aus stellen, ohne sie zu löschen.

## Microsoft-Login für Premium-Server einrichten (optional)

Ein echter Minecraft-Login läuft über Microsoft OAuth. Das erfordert eine **eigene, kostenlose
Azure-App-Registrierung** (das macht jeder Drittanbieter-Launcher, inkl. Norisk, so):

1. Gehe zu https://portal.azure.com → "App registrations" → "New registration"
2. Name: z.B. "SXMIR Launcher", Redirect-URI (Typ "Public client/native"):
   `https://login.microsoftonline.com/common/oauth2/nativeclient`
3. Nach dem Erstellen: "Application (client) ID" kopieren
4. Unter "Authentication" → "Allow public client flows" auf **Yes** setzen
5. Diese Client-ID im Launcher-Tab **Account** eintragen und auf "Mit Microsoft anmelden" klicken

Ohne diesen Schritt funktioniert der Launcher trotzdem vollständig im Offline-Modus
(passend für deinen eigenen Server).

## Als richtiges Programm installieren (.exe + Installer)

Willst du den Launcher wie ein normales Programm installieren (Startmenü, Desktop-Icon,
Deinstallation über Windows), statt ihn immer mit `python main.py` zu starten:

### Schritt 1: Eigenständige .exe bauen

Im Ordner `blockworldneo-launcher` einfach **`build_exe.bat` doppelklicken**
(oder im Terminal `build_exe.bat` eingeben). Das installiert PyInstaller und
erzeugt `dist\SXMIRLauncher.exe` – eine einzelne Datei, die auf jedem
Windows-PC läuft, **ohne dass Python installiert sein muss**.

Diese .exe kannst du bereits jetzt einfach kopieren/verschieben und per
Doppelklick starten – fertig.

### Schritt 2 (optional): Echten Installer mit Startmenü & Desktop-Icon erstellen

1. Inno Setup herunterladen und installieren (kostenlos): https://jrsoftware.org/isdl.php
2. Die Datei `installer.iss` mit Inno Setup öffnen
3. Auf **Build → Compile** klicken (oder F9)
4. Fertig liegt in `installer_output\SXMIRLauncher-Setup.exe`

Diese Setup.exe ist ein ganz normaler Windows-Installer: Doppelklick, durchklicken,
fertig – mit Eintrag im Startmenü, optionalem Desktop-Icon und sauberer
Deinstallation über "Apps installieren/deinstallieren".

## Konfiguration

Alle Einstellungen liegen in `~/.blockworldneo_launcher/config.json` (bzw. unter Windows im
Benutzerverzeichnis). Die Datei kann man löschen, um alles zurückzusetzen.

## Bekannte Grenzen

- Skin-Wechsel ist bewusst nicht enthalten, da er einen echten Premium-Account (Microsoft-Login)
  voraussetzt. Kann bei Bedarf nachgerüstet werden.
- Forge-Unterstützung ist vorbereitet (über `minecraft_launcher_lib.forge`), im UI aber noch nicht
  verdrahtet – bei Bedarf einfach sagen, dann bau ich den Fabric-Switch zu Fabric/Forge aus.
