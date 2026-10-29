"""Optional Spotify account connection; all Tk access stays on the UI thread."""

from i18n import tr
from i18n_tk import display_var
import queue
import threading
import tkinter as tk
from tkinter import ttk
import webbrowser

from settings_scroll import SettingsCategory
from spotify_account import REDIRECT_URI, authorize


class SpotifyConnection(tk.Toplevel):
    def __init__(self, page):
        super().__init__(page.app)
        self.page, self.account = page, page.spotify_account
        self.title(tr("Conectar Spotify · Playlists"))
        self.geometry("660x590")
        self.minsize(560, 480)
        self.transient(page.app)
        self.cancel = threading.Event()
        self.events = queue.Queue()
        self.closed = self.busy = False
        self.poll_id = None
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.client_id = tk.StringVar(
            value=self.account.client_id or page.app.spotify_client_id.get()
        )
        self.remember = tk.BooleanVar(value=self.account.remember)
        self.status = tk.StringVar(
            value=self.account.warning
            or (
                "Conta conectada. Cole o link da sua playlist na aba Playlists."
                if self.account.connected
                else "Ainda não conectado."
            )
        )
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        scroll = SettingsCategory(self, background="#10151e")
        scroll.grid(row=0, column=0, sticky="nsew")
        body = scroll.content
        body.columnconfigure(0, weight=1)
        ttk.Label(
            body,
            text=tr("Suas playlists completas"),
            font=("Segoe UI", 18, "bold"),
            anchor="center",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 14))
        explanation = (
            "1. Crie ou abra seu aplicativo no Spotify Developers.\n"
            "2. Nas configurações do aplicativo, cadastre exatamente o endereço de retorno abaixo.\n"
            "3. Cole o Client ID e clique em Conectar. A autorização será feita no navegador. Não é necessário Client Secret."
        )
        ttk.Label(body, text=tr(explanation), wraplength=580, justify="left").grid(
            row=1, column=0, sticky="ew", pady=8
        )
        ttk.Button(
            body,
            text=tr("Abrir Spotify Developers"),
            command=lambda: webbrowser.open("https://developer.spotify.com/dashboard"),
        ).grid(row=2, column=0, sticky="w", pady=8)
        ttk.Label(
            body, text=tr("Endereço de retorno (Redirect URI)"), style="Muted.TLabel"
        ).grid(row=3, column=0, sticky="w", pady=(10, 4))
        redirect = tk.StringVar(value=REDIRECT_URI)
        ttk.Entry(body, textvariable=redirect, state="readonly").grid(
            row=4, column=0, sticky="ew"
        )
        self.redirect = redirect
        ttk.Label(body, text=tr("Client ID"), style="Muted.TLabel").grid(
            row=5, column=0, sticky="w", pady=(12, 4)
        )
        self.entry = ttk.Entry(body, textvariable=self.client_id)
        self.entry.grid(row=6, column=0, sticky="ew")
        ttk.Checkbutton(
            body,
            text=tr("Lembrar conexão neste computador (protegida pelo Windows)"),
            variable=self.remember,
        ).grid(row=7, column=0, sticky="w", pady=12)
        ttk.Label(
            body,
            text=tr(
                "A API permite ler suas playlists e playlists em que você é colaborador. Em modo de desenvolvimento, o dono do app precisa de Premium e sua conta deve estar autorizada no dashboard. Importar CSV não exige conexão no Onda."
            ),
            wraplength=580,
            style="Muted.TLabel",
        ).grid(row=8, column=0, sticky="ew", pady=8)
        ttk.Label(body, textvariable=display_var(self.status), wraplength=580).grid(
            row=9, column=0, sticky="ew", pady=12
        )
        footer = ttk.Frame(self, padding=12)
        footer.grid(row=1, column=0, sticky="ew")
        self.connect_button = ttk.Button(
            footer, text=tr("Conectar"), command=self.connect, style="Accent.TButton"
        )
        self.connect_button.pack(side="left")
        self.disconnect_button = ttk.Button(
            footer,
            text=tr("Desconectar"),
            command=self.disconnect,
            state="normal" if self.account.connected else "disabled",
        )
        self.disconnect_button.pack(side="left", padx=8)
        ttk.Button(footer, text=tr("Fechar / cancelar"), command=self.close).pack(
            side="right"
        )
        self.poll_id = self.after(100, self.poll)

    def connect(self):
        if self.busy:
            return
        client_id = self.client_id.get().strip()
        self.keep = self.remember.get()
        self.cancel.clear()
        self.busy = True
        self.connect_button.configure(state="disabled")
        self.disconnect_button.configure(state="disabled")
        self.entry.configure(state="disabled")
        self.status.set(
            "Autorize no navegador. Você pode fechar esta janela para cancelar. Tempo máximo: 3 minutos."
        )

        def worker():
            try:
                self.events.put(
                    (
                        True,
                        authorize(
                            client_id,
                            self.cancel,
                            translate=tr,
                            language=self.page.app.language.get(),
                        ),
                    )
                )
            except Exception as exc:
                self.events.put((False, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        if self.closed:
            return
        try:
            success, result = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            if success:
                try:
                    self.account.accept(*result, remember=self.keep)
                    self.status.set(
                        "Conta conectada. Volte a Playlists e clique em Carregar playlist. Conexão salva."
                        if self.keep
                        else "Conta conectada nesta sessão. Volte a Playlists e clique em Carregar playlist."
                    )
                    self.page.spotify_button.configure(text=tr("Spotify conectado"))
                except Exception as exc:
                    self.status.set(str(exc))
            else:
                self.status.set(result)
            self.busy = False
            self.connect_button.configure(state="normal")
            self.disconnect_button.configure(
                state="normal" if self.account.connected else "disabled"
            )
            self.entry.configure(state="normal")
        self.poll_id = self.after(100, self.poll)

    def disconnect(self):
        try:
            self.account.disconnect()
        except Exception as exc:
            self.status.set(str(exc))
            return
        self.page.spotify_button.configure(text=tr("Conectar Spotify"))
        self.status.set(
            "Conexão removida deste computador. Você também pode revogar o acesso na sua conta Spotify."
        )
        self.disconnect_button.configure(state="disabled")

    def close(self):
        self.cancel.set()
        self.closed = True
        if self.poll_id:
            self.after_cancel(self.poll_id)
        self.destroy()
