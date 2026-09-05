"""
BlockWorldNeo Launcher - GUI
-----------------------------
Eigener Minecraft-Launcher, optisch angelehnt an den Norisk Client:
dunkles Theme, grüner Akzent, Sidebar-Navigation.

Tabs:
- Play      : Version wählen, installieren, starten
- Servers   : eigene Serverliste (schreibt echte servers.dat)
- Worlds    : Singleplayer-Welten anzeigen / löschen / Ordner öffnen
- Mods      : mods-Ordner verwalten (aktivieren/deaktivieren/hinzufügen)
- Account   : Offline-Name oder Microsoft-Login
- Settings  : RAM, Java-Pfad, Spielordner
"""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

import customtkinter as ctk

import launcher_core as core

# ---------------------------------------------------------------------------
# Theme (Norisk-inspiriert: dunkles Grau + kräftiges Grün)
# ---------------------------------------------------------------------------

ctk.set_appearance_mode("dark")

BG_DARK = "#0d0a0a"
BG_PANEL = "#161010"
BG_SIDEBAR = "#0a0808"
ACCENT = "#e0223a"
ACCENT_HOVER = "#b81b30"
TEXT_MUTED = "#9a8a8a"

ctk.set_default_color_theme("dark-blue")


class BlockWorldNeoLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config_data = core.load_config()

        self.title(core.APP_NAME)
        self.geometry("1040x660")
        self.minsize(900, 580)
        self.configure(fg_color=BG_DARK)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content_area()

        self.frames = {}
        for name, builder in [
            ("Play", self._build_play_tab),
            ("Servers", self._build_servers_tab),
            ("Worlds", self._build_worlds_tab),
            ("Mods", self._build_mods_tab),
            ("Account", self._build_account_tab),
            ("Settings", self._build_settings_tab),
        ]:
            frame = ctk.CTkFrame(self.content_area, fg_color=BG_PANEL, corner_radius=14)
            builder(frame)
            self.frames[name] = frame

        self.show_tab("Play")

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=210, fg_color=BG_SIDEBAR, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nswe")
        sidebar.grid_propagate(False)

        logo = ctk.CTkLabel(
            sidebar, text="SXMIR",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=ACCENT,
        )
        logo.pack(pady=(28, 4), padx=20, anchor="w")

        sub = ctk.CTkLabel(sidebar, text="Launcher", font=ctk.CTkFont(size=12),
                            text_color=TEXT_MUTED)
        sub.pack(pady=(0, 24), padx=20, anchor="w")

        self.nav_buttons = {}
        for name in ["Play", "Servers", "Worlds", "Mods", "Account", "Settings"]:
            btn = ctk.CTkButton(
                sidebar, text=name, anchor="w",
                fg_color="transparent", hover_color="#20222a",
                text_color="#d6d8de",
                font=ctk.CTkFont(size=14),
                height=40, corner_radius=8,
                command=lambda n=name: self.show_tab(n),
            )
            btn.pack(fill="x", padx=14, pady=3)
            self.nav_buttons[name] = btn

        status = ctk.CTkLabel(sidebar, text="", text_color=TEXT_MUTED,
                               font=ctk.CTkFont(size=11), wraplength=180, justify="left")
        status.pack(side="bottom", padx=16, pady=16, anchor="w")
        self.sidebar_status = status
        self._refresh_sidebar_status()

    def _refresh_sidebar_status(self):
        mode = self.config_data.get("account_mode", "offline")
        name = self.config_data.get("username", "Spieler")
        mode_label = {
            "offline": "offline",
            "microsoft": "online (Microsoft)",
            "launcher_session": "online (Launcher-Session)",
        }.get(mode, mode)
        self.sidebar_status.configure(text=f"Account: {name}\nModus: {mode_label}")

    def _build_content_area(self):
        self.content_area = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        self.content_area.grid(row=0, column=1, sticky="nswe", padx=24, pady=24)
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)

    def show_tab(self, name: str):
        for frame in self.frames.values():
            frame.grid_forget()
        self.frames[name].grid(row=0, column=0, sticky="nswe")
        for n, btn in self.nav_buttons.items():
            btn.configure(fg_color=("#20222a" if n == name else "transparent"),
                          text_color=(ACCENT if n == name else "#d6d8de"))
        if name == "Servers":
            self._reload_server_list()
        elif name == "Worlds":
            self._reload_world_list()
        elif name == "Mods":
            self._reload_mod_list()

    # ------------------------------------------------------------------
    # Tab: Play
    # ------------------------------------------------------------------

    def _build_play_tab(self, frame: ctk.CTkFrame):
        frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(frame, text="Spielen", font=ctk.CTkFont(size=22, weight="bold"))
        title.grid(row=0, column=0, sticky="w", padx=28, pady=(24, 4))

        subtitle = ctk.CTkLabel(frame, text="Version wählen, installieren und starten",
                                 text_color=TEXT_MUTED)
        subtitle.grid(row=1, column=0, sticky="w", padx=28, pady=(0, 20))

        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.grid(row=2, column=0, sticky="we", padx=28)
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Version:").grid(row=0, column=0, sticky="w", pady=8)
        installed = core.list_installed_versions(self.config_data["game_dir"])
        remote = core.list_remote_versions()[:60]  # neueste 60 Releases
        combined = sorted(set(installed) | set(remote),
                           key=lambda v: (v not in installed, remote.index(v) if v in remote else 999))
        self.version_var = tk.StringVar(value=self.config_data.get("selected_version") or (combined[0] if combined else ""))
        self.version_menu = ctk.CTkComboBox(form, values=combined, variable=self.version_var, width=260)
        self.version_menu.grid(row=0, column=1, sticky="w", pady=8, padx=(10, 0))

        self.fabric_var = tk.BooleanVar(value=self.config_data.get("use_fabric", False))
        fabric_check = ctk.CTkCheckBox(form, text="Fabric-Loader installieren (für Mods)",
                                        variable=self.fabric_var, fg_color=ACCENT, hover_color=ACCENT_HOVER)
        fabric_check.grid(row=1, column=1, sticky="w", pady=(4, 8), padx=(10, 0))

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=3, column=0, sticky="w", padx=28, pady=(12, 4))

        self.install_btn = ctk.CTkButton(btn_row, text="Installieren", width=140,
                                          fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#0b0c0e",
                                          command=self._on_install_clicked)
        self.install_btn.pack(side="left", padx=(0, 10))

        self.play_btn = ctk.CTkButton(btn_row, text="▶  Spielen", width=140,
                                       fg_color="#2a2d36", hover_color="#363a45",
                                       command=self._on_play_clicked)
        self.play_btn.pack(side="left")

        self.progress = ctk.CTkProgressBar(frame, width=500, progress_color=ACCENT)
        self.progress.set(0)
        self.progress.grid(row=4, column=0, sticky="w", padx=28, pady=(20, 4))

        self.progress_label = ctk.CTkLabel(frame, text="Bereit.", text_color=TEXT_MUTED)
        self.progress_label.grid(row=5, column=0, sticky="w", padx=28)

    def _on_install_clicked(self):
        version = self.version_var.get().strip()
        if not version:
            messagebox.showwarning(core.APP_NAME, "Bitte eine Version auswählen.")
            return
        use_fabric = self.fabric_var.get()
        self.install_btn.configure(state="disabled")

        def worker():
            try:
                game_dir = self.config_data["game_dir"]

                def cb(status, current, total):
                    self.after(0, self._update_progress, status, current, total)

                core.install_vanilla(version, game_dir, cb)
                final_version = version
                fabric_failed_msg = None
                if use_fabric:
                    self.after(0, self._update_progress, "Installiere Fabric...", 0, 1)
                    try:
                        final_version = core.install_fabric_for(version, game_dir, cb)
                    except core.FabricUnsupportedError as e:
                        fabric_failed_msg = str(e)
                        final_version = version  # Vanilla bleibt nutzbar, nur ohne Fabric

                self.config_data["selected_version"] = final_version
                self.config_data["use_fabric"] = use_fabric and fabric_failed_msg is None
                core.save_config(self.config_data)

                if fabric_failed_msg:
                    self.after(0, self._update_progress,
                               f"Vanilla {version} installiert (ohne Fabric)", 1, 1)
                    self.after(0, messagebox.showwarning, core.APP_NAME,
                               f"{fabric_failed_msg}\n\nDie Version {version} selbst wurde "
                               f"erfolgreich installiert und ist ohne Mods spielbar.")
                else:
                    self.after(0, self._update_progress, f"Installiert: {final_version}", 1, 1)
            except Exception as e:
                self.after(0, messagebox.showerror, core.APP_NAME, f"Installation fehlgeschlagen:\n{e}")
            finally:
                self.after(0, lambda: self.install_btn.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _update_progress(self, status, current, total):
        self.progress_label.configure(text=status or "...")
        if total:
            self.progress.set(min(1.0, current / total))
        else:
            self.progress.set(0)

    def _resolve_account(self) -> dict:
        """
        Ermittelt die Account-Optionen für den Start, abhängig vom gewählten Modus.
        Bei "launcher_session" wird IMMER frisch aus dem offiziellen Launcher gelesen
        (nicht aus config_data gecacht), da der Access-Token dort ablaufen kann.
        """
        mode = self.config_data.get("account_mode", "offline")

        if mode == "launcher_session":
            account = core.read_official_launcher_account()
            if account:
                return account
            messagebox.showwarning(
                core.APP_NAME,
                "Die Launcher-Session ist nicht mehr verfügbar (abgelaufen oder ausgeloggt).\n"
                "Bitte im offiziellen Minecraft Launcher neu einloggen und auf der Account-Seite "
                "erneut \"Von offiziellem Launcher übernehmen\" klicken.\n\n"
                "Starte vorerst offline.",
            )
            return core.offline_options(self.config_data.get("username", "Spieler"))

        if mode == "microsoft" and self.config_data.get("_ms_account"):
            return self.config_data["_ms_account"]

        return core.offline_options(self.config_data.get("username", "Spieler"))

    def _on_play_clicked(self):
        version = self.config_data.get("selected_version") or self.version_var.get().strip()
        if not version:
            messagebox.showwarning(core.APP_NAME, "Bitte zuerst eine Version installieren.")
            return

        account = self._resolve_account()

        try:
            core.launch(
                version, self.config_data["game_dir"], account,
                ram_mb=self.config_data.get("ram_mb", 4096),
                java_path=self.config_data.get("java_path", ""),
                performance_mode=self.config_data.get("performance_mode", True),
            )
            self.progress_label.configure(text=f"Minecraft {version} gestartet.")
        except Exception as e:
            messagebox.showerror(core.APP_NAME, f"Start fehlgeschlagen:\n{e}")

    # ------------------------------------------------------------------
    # Tab: Servers
    # ------------------------------------------------------------------

    def _build_servers_tab(self, frame: ctk.CTkFrame):
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(frame, text="Server", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=28, pady=(24, 4))
        ctk.CTkLabel(frame, text="Wird direkt in deine echte servers.dat geschrieben",
                     text_color=TEXT_MUTED).grid(row=1, column=0, sticky="w", padx=28, pady=(0, 16))

        add_row = ctk.CTkFrame(frame, fg_color="transparent")
        add_row.grid(row=1, column=0, sticky="e", padx=28)
        self.new_server_name = ctk.CTkEntry(add_row, placeholder_text="Name", width=120)
        self.new_server_name.pack(side="left", padx=4)
        self.new_server_addr = ctk.CTkEntry(add_row, placeholder_text="IP / Adresse:Port", width=190)
        self.new_server_addr.pack(side="left", padx=4)
        ctk.CTkButton(add_row, text="+ Merken", width=90, fg_color="#2a2d36", hover_color="#363a45",
                      command=self._on_add_server).pack(side="left", padx=4)
        ctk.CTkButton(add_row, text="▶ Starten & Verbinden", width=170, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      text_color="#0b0c0e", command=self._on_quick_connect).pack(side="left", padx=4)

        self.server_list_frame = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.server_list_frame.grid(row=2, column=0, sticky="nswe", padx=28, pady=(4, 20))
        self.server_list_frame.grid_columnconfigure(0, weight=1)

    def _reload_server_list(self):
        for w in self.server_list_frame.winfo_children():
            w.destroy()
        servers = core.read_servers(self.config_data["game_dir"])
        if not servers:
            for fav in self.config_data.get("favorite_servers", []):
                servers.append(fav)
            if servers:
                core.write_servers(self.config_data["game_dir"], servers)
        for i, s in enumerate(servers):
            row = ctk.CTkFrame(self.server_list_frame, fg_color=BG_SIDEBAR, corner_radius=10)
            row.grid(row=i, column=0, sticky="we", pady=5)
            row.grid_columnconfigure(0, weight=1)
            text = ctk.CTkLabel(row, text=f"{s['name']}", font=ctk.CTkFont(weight="bold"), anchor="w")
            text.grid(row=0, column=0, sticky="w", padx=14, pady=(10, 0))
            addr = ctk.CTkLabel(row, text=s["address"], text_color=TEXT_MUTED, anchor="w")
            addr.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))
            connect_btn = ctk.CTkButton(row, text="▶ Verbinden", width=110, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                         text_color="#0b0c0e",
                                         command=lambda addr=s["address"]: self._launch_direct_connect(addr))
            connect_btn.grid(row=0, column=1, rowspan=2, padx=(10, 4))
            del_btn = ctk.CTkButton(row, text="Entfernen", width=90, fg_color="#3a2020", hover_color="#4a2828",
                                     command=lambda addr=s["address"]: self._on_remove_server(addr))
            del_btn.grid(row=0, column=2, rowspan=2, padx=(0, 10))

    def _on_add_server(self):
        name = self.new_server_name.get().strip() or "Server"
        addr = self.new_server_addr.get().strip()
        if not addr:
            messagebox.showwarning(core.APP_NAME, "Bitte eine Adresse eingeben.")
            return
        core.add_favorite_server(self.config_data["game_dir"], name, addr)
        self.new_server_name.delete(0, "end")
        self.new_server_addr.delete(0, "end")
        self._reload_server_list()

    def _on_remove_server(self, address: str):
        servers = [s for s in core.read_servers(self.config_data["game_dir"]) if s["address"] != address]
        core.write_servers(self.config_data["game_dir"], servers)
        self._reload_server_list()

    def _on_quick_connect(self):
        """IP-Feld oben: direkt starten & verbinden, ohne zwingend zu speichern."""
        addr = self.new_server_addr.get().strip()
        if not addr:
            messagebox.showwarning(core.APP_NAME, "Bitte eine IP/Adresse eingeben.")
            return
        name = self.new_server_name.get().strip()
        if name:
            core.add_favorite_server(self.config_data["game_dir"], name, addr)
            self.new_server_name.delete(0, "end")
            self.new_server_addr.delete(0, "end")
            self._reload_server_list()
        self._launch_direct_connect(addr)

    def _launch_direct_connect(self, address: str):
        version = self.config_data.get("selected_version")
        if not version:
            messagebox.showwarning(core.APP_NAME, "Bitte zuerst im Tab 'Play' eine Version installieren.")
            return

        account = self._resolve_account()

        try:
            core.launch(
                version, self.config_data["game_dir"], account,
                ram_mb=self.config_data.get("ram_mb", 4096),
                java_path=self.config_data.get("java_path", ""),
                direct_connect=address,
                performance_mode=self.config_data.get("performance_mode", True),
            )
            messagebox.showinfo(core.APP_NAME, f"Minecraft startet und verbindet sich mit {address} ...")
        except Exception as e:
            messagebox.showerror(core.APP_NAME, f"Start fehlgeschlagen:\n{e}")

    # ------------------------------------------------------------------
    # Tab: Worlds
    # ------------------------------------------------------------------

    def _build_worlds_tab(self, frame: ctk.CTkFrame):
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(frame, text="Welten", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=28, pady=(24, 4))
        ctk.CTkLabel(frame, text="Deine Singleplayer-Welten", text_color=TEXT_MUTED).grid(
            row=1, column=0, sticky="w", padx=28, pady=(0, 16))

        ctk.CTkButton(frame, text="Ordner öffnen", width=140, fg_color="#2a2d36", hover_color="#363a45",
                      command=lambda: core.open_folder(core.saves_dir(self.config_data["game_dir"]))
                      ).grid(row=1, column=0, sticky="e", padx=28)

        self.world_list_frame = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.world_list_frame.grid(row=2, column=0, sticky="nswe", padx=28, pady=(4, 20))
        self.world_list_frame.grid_columnconfigure(0, weight=1)

    def _reload_world_list(self):
        for w in self.world_list_frame.winfo_children():
            w.destroy()
        worlds = core.list_worlds(self.config_data["game_dir"])
        if not worlds:
            ctk.CTkLabel(self.world_list_frame, text="Keine Welten gefunden.", text_color=TEXT_MUTED).grid(
                row=0, column=0, sticky="w", pady=10)
            return
        for i, w in enumerate(worlds):
            row = ctk.CTkFrame(self.world_list_frame, fg_color=BG_SIDEBAR, corner_radius=10)
            row.grid(row=i, column=0, sticky="we", pady=5)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=w["name"], font=ctk.CTkFont(weight="bold"), anchor="w").grid(
                row=0, column=0, sticky="w", padx=14, pady=(10, 0))
            ctk.CTkLabel(row, text=w["folder"], text_color=TEXT_MUTED, anchor="w").grid(
                row=1, column=0, sticky="w", padx=14, pady=(0, 10))
            del_btn = ctk.CTkButton(row, text="Löschen", width=90, fg_color="#3a2020", hover_color="#4a2828",
                                     command=lambda folder=w["folder"]: self._on_delete_world(folder))
            del_btn.grid(row=0, column=1, rowspan=2, padx=10)

    def _on_delete_world(self, folder: str):
        if messagebox.askyesno(core.APP_NAME, f"Welt '{folder}' wirklich unwiderruflich löschen?"):
            core.delete_world(self.config_data["game_dir"], folder)
            self._reload_world_list()

    # ------------------------------------------------------------------
    # Tab: Mods
    # ------------------------------------------------------------------

    def _build_mods_tab(self, frame: ctk.CTkFrame):
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(frame, text="Mods", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=28, pady=(24, 4))
        ctk.CTkLabel(frame, text="Benötigt Fabric (siehe Tab 'Play')", text_color=TEXT_MUTED).grid(
            row=1, column=0, sticky="w", padx=28, pady=(0, 16))

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=1, column=0, sticky="e", padx=28)
        ctk.CTkButton(btn_row, text="+ .jar hinzufügen", width=140, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      text_color="#0b0c0e", command=self._on_add_mod).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="Ordner öffnen", width=120, fg_color="#2a2d36", hover_color="#363a45",
                      command=lambda: core.open_folder(core.mods_dir(self.config_data["game_dir"]))
                      ).pack(side="left", padx=4)

        self.mod_list_frame = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.mod_list_frame.grid(row=2, column=0, sticky="nswe", padx=28, pady=(4, 20))
        self.mod_list_frame.grid_columnconfigure(0, weight=1)

    def _reload_mod_list(self):
        for w in self.mod_list_frame.winfo_children():
            w.destroy()
        mods = core.list_mods(self.config_data["game_dir"])
        if not mods:
            ctk.CTkLabel(self.mod_list_frame, text="Keine Mods installiert.", text_color=TEXT_MUTED).grid(
                row=0, column=0, sticky="w", pady=10)
            return
        for i, m in enumerate(mods):
            row = ctk.CTkFrame(self.mod_list_frame, fg_color=BG_SIDEBAR, corner_radius=10)
            row.grid(row=i, column=0, sticky="we", pady=5)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=m["filename"], anchor="w").grid(row=0, column=0, sticky="w", padx=14, pady=10)

            enabled_var = tk.BooleanVar(value=m["enabled"])
            toggle = ctk.CTkSwitch(row, text="Aktiv", variable=enabled_var, progress_color=ACCENT,
                                    command=lambda fn=m["filename"], var=enabled_var: self._on_toggle_mod(fn, var))
            toggle.grid(row=0, column=1, padx=10)

            del_btn = ctk.CTkButton(row, text="Entfernen", width=90, fg_color="#3a2020", hover_color="#4a2828",
                                     command=lambda fn=m["filename"], en=m["enabled"]: self._on_remove_mod(fn, en))
            del_btn.grid(row=0, column=2, padx=10)

    def _on_add_mod(self):
        path = filedialog.askopenfilename(filetypes=[("Mod-Datei (.jar)", "*.jar")])
        if path:
            core.add_mod_file(self.config_data["game_dir"], path)
            self._reload_mod_list()

    def _on_toggle_mod(self, filename: str, var: tk.BooleanVar):
        core.toggle_mod(self.config_data["game_dir"], filename, var.get())
        self._reload_mod_list()

    def _on_remove_mod(self, filename: str, currently_enabled: bool):
        core.remove_mod(self.config_data["game_dir"], filename, currently_enabled)
        self._reload_mod_list()

    # ------------------------------------------------------------------
    # Tab: Account
    # ------------------------------------------------------------------

    def _build_account_tab(self, frame: ctk.CTkFrame):
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Account", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=28, pady=(24, 4))
        ctk.CTkLabel(frame, text="Offline-Name für deinen eigenen Server, oder Microsoft-Login für Premium-Server",
                     text_color=TEXT_MUTED, wraplength=520, justify="left").grid(
            row=1, column=0, sticky="w", padx=28, pady=(0, 20))

        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.grid(row=2, column=0, sticky="w", padx=28)

        ctk.CTkLabel(form, text="Anzeigename (offline):").grid(row=0, column=0, sticky="w", pady=8)
        self.username_entry = ctk.CTkEntry(form, width=220)
        self.username_entry.insert(0, self.config_data.get("username", "Spieler"))
        self.username_entry.grid(row=0, column=1, padx=10)

        ctk.CTkButton(form, text="Speichern", width=100, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      text_color="#0b0c0e", command=self._on_save_username).grid(row=0, column=2, padx=10)

        sep = ctk.CTkFrame(frame, height=1, fg_color="#2a2d36")
        sep.grid(row=3, column=0, sticky="we", padx=28, pady=20)

        ctk.CTkLabel(frame, text="Vom offiziellen Launcher übernehmen (empfohlen)",
                     font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, sticky="w", padx=28)
        ctk.CTkLabel(frame,
                     text="Logge dich einmal im offiziellen Minecraft Launcher (minecraft.net) ein.\n"
                          "Danach kann SXMIR diese Session übernehmen - kein eigener Microsoft-Login nötig.",
                     text_color=TEXT_MUTED, wraplength=520, justify="left").grid(
            row=5, column=0, sticky="w", padx=28, pady=(4, 10))

        launcher_row = ctk.CTkFrame(frame, fg_color="transparent")
        launcher_row.grid(row=6, column=0, sticky="w", padx=28)
        ctk.CTkButton(launcher_row, text="Von offiziellem Launcher übernehmen", width=260,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#0b0c0e",
                      command=self._on_use_launcher_session).grid(row=0, column=0)
        self.launcher_session_status = ctk.CTkLabel(launcher_row, text="", text_color=TEXT_MUTED)
        self.launcher_session_status.grid(row=0, column=1, padx=(14, 0))

        sep2 = ctk.CTkFrame(frame, height=1, fg_color="#2a2d36")
        sep2.grid(row=7, column=0, sticky="we", padx=28, pady=20)

        ctk.CTkLabel(frame, text="Eigener Microsoft-Login (aktuell nicht nutzbar)",
                     font=ctk.CTkFont(weight="bold")).grid(row=8, column=0, sticky="w", padx=28)
        ctk.CTkLabel(frame,
                     text="Benötigt eine offizielle ID@Xbox-Registrierung, sonst Fehler AzureAppNotPermitted.\n"
                          "Bis dahin bitte oben \"Vom offiziellen Launcher übernehmen\" nutzen.",
                     text_color=TEXT_MUTED, wraplength=520, justify="left").grid(
            row=9, column=0, sticky="w", padx=28, pady=(4, 10))

        ms_form = ctk.CTkFrame(frame, fg_color="transparent")
        ms_form.grid(row=10, column=0, sticky="w", padx=28)
        self.ms_client_id_entry = ctk.CTkEntry(ms_form, width=300, placeholder_text="Azure Client-ID")
        self.ms_client_id_entry.insert(0, self.config_data.get("ms_client_id", ""))
        self.ms_client_id_entry.grid(row=0, column=0, padx=(0, 10))
        ctk.CTkButton(ms_form, text="Mit Microsoft anmelden", width=180, fg_color="#2a2d36", hover_color="#363a45",
                      command=self._on_microsoft_login).grid(row=0, column=1)

    def _on_save_username(self):
        self.config_data["username"] = self.username_entry.get().strip() or "Spieler"
        self.config_data["account_mode"] = "offline"
        core.save_config(self.config_data)
        self._refresh_sidebar_status()
        messagebox.showinfo(core.APP_NAME, "Gespeichert.")

    def _on_use_launcher_session(self):
        account = core.read_official_launcher_account()
        if not account:
            self.launcher_session_status.configure(text="Kein Login gefunden", text_color=ACCENT)
            messagebox.showwarning(
                core.APP_NAME,
                "Es wurde keine aktive Session des offiziellen Minecraft Launchers gefunden.\n\n"
                "Bitte öffne den offiziellen Minecraft Launcher (minecraft.net), logge dich dort "
                "einmal ein, und versuche es danach hier erneut.",
            )
            return

        self.config_data["_launcher_account"] = account
        self.config_data["account_mode"] = "launcher_session"
        self.config_data["username"] = account["username"]
        core.save_config({k: v for k, v in self.config_data.items() if k != "_launcher_account"})
        self._refresh_sidebar_status()
        self.launcher_session_status.configure(text=f"Übernommen: {account['username']}", text_color="#4caf50")
        messagebox.showinfo(core.APP_NAME, f"Angemeldet als {account['username']} (Launcher-Session).")

    def _on_microsoft_login(self):
        client_id = self.ms_client_id_entry.get().strip()
        if not client_id:
            messagebox.showwarning(core.APP_NAME, "Bitte zuerst eine Azure Client-ID eintragen (siehe README.md).")
            return
        self.config_data["ms_client_id"] = client_id
        core.save_config(self.config_data)
        try:
            login_url, state, verifier = core.microsoft_login_url(client_id)
        except Exception as e:
            messagebox.showerror(core.APP_NAME, f"Login-URL konnte nicht erstellt werden:\n{e}")
            return

        import webbrowser
        webbrowser.open(login_url)

        dialog = ctk.CTkInputDialog(
            text="Nach dem Login öffnet sich eine leere/weiße Seite.\n"
                 "Kopiere die komplette URL aus der Adresszeile hier hinein:",
            title=core.APP_NAME,
        )
        redirected_url = dialog.get_input()
        if not redirected_url:
            return
        try:
            import urllib.parse as up
            query = up.parse_qs(up.urlparse(redirected_url).query)
            auth_code = query["code"][0]
            account = core.microsoft_complete_login(
                client_id, None, auth_code,
                "https://login.microsoftonline.com/common/oauth2/nativeclient", verifier,
            )
        except Exception as e:
            messagebox.showerror(core.APP_NAME, f"Login fehlgeschlagen:\n{e}")
            return

        self.config_data["_ms_account"] = account
        self.config_data["account_mode"] = "microsoft"
        self.config_data["username"] = account["username"]
        core.save_config({k: v for k, v in self.config_data.items() if k != "_ms_account"})
        self._refresh_sidebar_status()
        messagebox.showinfo(core.APP_NAME, f"Angemeldet als {account['username']}.")

    # ------------------------------------------------------------------
    # Tab: Settings
    # ------------------------------------------------------------------

    def _build_settings_tab(self, frame: ctk.CTkFrame):
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Einstellungen", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=28, pady=(24, 4))

        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.grid(row=1, column=0, sticky="we", padx=28, pady=(16, 0))
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Spielordner:").grid(row=0, column=0, sticky="w", pady=8)
        self.game_dir_entry = ctk.CTkEntry(form, width=380)
        self.game_dir_entry.insert(0, self.config_data["game_dir"])
        self.game_dir_entry.grid(row=0, column=1, sticky="w", padx=10)
        ctk.CTkButton(form, text="...", width=40, command=self._on_browse_game_dir).grid(row=0, column=2)

        ctk.CTkLabel(form, text="Java-Pfad (leer = automatisch):").grid(row=1, column=0, sticky="w", pady=8)
        self.java_path_entry = ctk.CTkEntry(form, width=380)
        self.java_path_entry.insert(0, self.config_data.get("java_path", ""))
        self.java_path_entry.grid(row=1, column=1, sticky="w", padx=10)
        ctk.CTkButton(form, text="...", width=40, command=self._on_browse_java).grid(row=1, column=2)

        ctk.CTkLabel(form, text="Arbeitsspeicher (MB):").grid(row=2, column=0, sticky="w", pady=8)
        self.ram_slider = ctk.CTkSlider(form, from_=1024, to=16384, number_of_steps=30,
                                         progress_color=ACCENT, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
                                         command=self._on_ram_change)
        self.ram_slider.set(self.config_data.get("ram_mb", 4096))
        self.ram_slider.grid(row=2, column=1, sticky="we", padx=10)
        self.ram_value_label = ctk.CTkLabel(form, text=f"{self.config_data.get('ram_mb', 4096)} MB")
        self.ram_value_label.grid(row=2, column=2)

        self.performance_var = tk.BooleanVar(value=self.config_data.get("performance_mode", True))
        perf_check = ctk.CTkCheckBox(
            form, text="Performance-Modus (optimierte JVM-Flags für flüssigeres Spiel)",
            variable=self.performance_var, fg_color=ACCENT, hover_color=ACCENT_HOVER,
        )
        perf_check.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

        ctk.CTkButton(frame, text="Speichern", width=120, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      text_color="#0b0c0e", command=self._on_save_settings).grid(
            row=2, column=0, sticky="w", padx=28, pady=24)

    def _on_browse_game_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.game_dir_entry.delete(0, "end")
            self.game_dir_entry.insert(0, path)

    def _on_browse_java(self):
        path = filedialog.askopenfilename()
        if path:
            self.java_path_entry.delete(0, "end")
            self.java_path_entry.insert(0, path)

    def _on_ram_change(self, value):
        self.ram_value_label.configure(text=f"{int(value)} MB")

    def _on_save_settings(self):
        self.config_data["game_dir"] = self.game_dir_entry.get().strip() or core.DEFAULT_CONFIG["game_dir"]
        self.config_data["java_path"] = self.java_path_entry.get().strip()
        self.config_data["ram_mb"] = int(self.ram_slider.get())
        self.config_data["performance_mode"] = self.performance_var.get()
        core.save_config(self.config_data)
        messagebox.showinfo(core.APP_NAME, "Einstellungen gespeichert. Bitte Launcher neu starten.")


def main():
    app = BlockWorldNeoLauncher()
    app.mainloop()


if __name__ == "__main__":
    main()
