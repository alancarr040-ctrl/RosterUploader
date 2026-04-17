import json
import re
import requests
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

API_URL = "https://www.theregs.org/roster/app/api/upload.php"
CHAT_URL = "https://www.theregs.org/roster/app/api/chat_post.php"
RAID_URL = "https://www.theregs.org/roster/app/api/raid_event.php"
API_KEY = "CHANGE_ME"


class WoWUploaderApp:
    BG = "#1e1e1e"
    PANEL = "#252526"
    ENTRY_BG = "#2d2d30"
    BTN = "#3a3d41"
    BTN_ACTIVE = "#4a4d52"
    FG = "#f3f3f3"
    MUTED = "#b8b8b8"
    ACCENT = "#4fc3f7"
    LOG_BG = "#111315"
    LOG_FG = "#d6d6d6"

    SUCCESS = "#7CFC90"
    WARNING = "#FFD166"
    ERROR = "#FF6B6B"
    INFO = "#D6D6D6"

    def __init__(self, root):
        self.root = root
        self.root.title("WoW Guild Roster Uploader")
        self.root.geometry("1020x760")
        self.root.configure(bg=self.BG)

        self.base_dir_var = tk.StringVar()
        self.account_var = tk.StringVar(value="All Accounts")
        self.upload_chat_var = tk.BooleanVar(value=True)
        self.upload_raid_var = tk.BooleanVar(value=True)

        self.detected_accounts = {}
        self.is_uploading = False

        self.build_style()
        self.build_ui()

    def build_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Dark.TCombobox",
            fieldbackground=self.ENTRY_BG,
            background=self.ENTRY_BG,
            foreground=self.FG,
            arrowcolor=self.FG,
            bordercolor="#444",
            lightcolor="#444",
            darkcolor="#444",
        )

        style.configure(
            "Dark.Horizontal.TProgressbar",
            troughcolor="#1a1a1a",
            background=self.ACCENT,
            bordercolor="#333",
            lightcolor=self.ACCENT,
            darkcolor=self.ACCENT
        )

    def build_ui(self):
        main = tk.Frame(self.root, bg=self.BG)
        main.pack(fill="both", expand=True, padx=14, pady=14)

        title = tk.Label(
            main,
            text="WoW Guild Roster Uploader",
            font=("Segoe UI", 16, "bold"),
            bg=self.BG,
            fg=self.FG
        )
        title.pack(anchor="w", pady=(0, 12))

        top_frame = tk.Frame(main, bg=self.PANEL, highlightthickness=1, highlightbackground="#333")
        top_frame.pack(fill="x", pady=(0, 10))

        top_inner = tk.Frame(top_frame, bg=self.PANEL)
        top_inner.pack(fill="x", padx=12, pady=12)

        tk.Label(
            top_inner,
            text="WoW Base Directory",
            font=("Segoe UI", 10, "bold"),
            bg=self.PANEL,
            fg=self.FG
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        entry = tk.Entry(
            top_inner,
            textvariable=self.base_dir_var,
            font=("Consolas", 10),
            bg=self.ENTRY_BG,
            fg=self.FG,
            insertbackground=self.FG,
            relief="flat",
            bd=8
        )
        entry.grid(row=1, column=0, columnspan=3, sticky="we", padx=(0, 8), pady=(0, 6))

        self.browse_btn = self.make_button(top_inner, "Browse", self.browse_base_dir, width=12)
        self.browse_btn.grid(row=1, column=3, padx=4)

        self.auto_btn = self.make_button(top_inner, "Auto Detect", self.auto_detect_base_dir, width=12)
        self.auto_btn.grid(row=1, column=4, padx=4)

        self.scan_btn = self.make_button(top_inner, "Scan Accounts", self.scan_accounts, width=12)
        self.scan_btn.grid(row=1, column=5, padx=4)

        self.upload_btn = self.make_button(top_inner, "Upload", self.start_upload_thread, width=12, accent=True)
        self.upload_btn.grid(row=1, column=6, padx=(8, 0))

        tk.Label(
            top_inner,
            text="Detected Account",
            font=("Segoe UI", 10, "bold"),
            bg=self.PANEL,
            fg=self.FG
        ).grid(row=2, column=0, sticky="w", pady=(10, 6))

        self.account_combo = ttk.Combobox(
            top_inner,
            textvariable=self.account_var,
            state="readonly",
            style="Dark.TCombobox",
            values=["All Accounts"],
            font=("Segoe UI", 10)
        )
        self.account_combo.grid(row=3, column=0, columnspan=3, sticky="we", padx=(0, 8), pady=(0, 2))
        self.account_combo.current(0)

        self.account_status = tk.Label(
            top_inner,
            text="No scan run yet.",
            font=("Segoe UI", 9),
            bg=self.PANEL,
            fg=self.MUTED
        )
        self.account_status.grid(row=3, column=3, columnspan=4, sticky="w", padx=4)

        top_inner.grid_columnconfigure(0, weight=1)

        options_frame = tk.Frame(main, bg=self.PANEL, highlightthickness=1, highlightbackground="#333")
        options_frame.pack(fill="x", pady=(0, 10))

        options_inner = tk.Frame(options_frame, bg=self.PANEL)
        options_inner.pack(fill="x", padx=12, pady=10)

        self.make_checkbox(options_inner, "Upload Chat Data", self.upload_chat_var).pack(side="left", padx=(0, 18))
        self.make_checkbox(options_inner, "Upload Raid Data", self.upload_raid_var).pack(side="left")

        progress_frame = tk.Frame(main, bg=self.PANEL, highlightthickness=1, highlightbackground="#333")
        progress_frame.pack(fill="x", pady=(0, 10))

        progress_inner = tk.Frame(progress_frame, bg=self.PANEL)
        progress_inner.pack(fill="x", padx=12, pady=10)

        self.progress_label = tk.Label(
            progress_inner,
            text="Progress: idle",
            font=("Segoe UI", 10),
            bg=self.PANEL,
            fg=self.FG
        )
        self.progress_label.pack(anchor="w", pady=(0, 6))

        self.progress = ttk.Progressbar(
            progress_inner,
            style="Dark.Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            maximum=100
        )
        self.progress.pack(fill="x")

        log_wrap = tk.Frame(main, bg=self.PANEL, highlightthickness=1, highlightbackground="#333")
        log_wrap.pack(fill="both", expand=True)

        log_header = tk.Frame(log_wrap, bg=self.PANEL)
        log_header.pack(fill="x", padx=12, pady=(10, 0))

        tk.Label(
            log_header,
            text="Log Output",
            font=("Segoe UI", 10, "bold"),
            bg=self.PANEL,
            fg=self.FG
        ).pack(side="left")

        self.clear_btn = self.make_button(log_header, "Clear Log", self.clear_log, width=10)
        self.clear_btn.pack(side="right")

        self.log_box = tk.Text(
            log_wrap,
            wrap="word",
            bg=self.LOG_BG,
            fg=self.LOG_FG,
            insertbackground=self.FG,
            selectbackground="#264f78",
            relief="flat",
            font=("Consolas", 10),
            padx=10,
            pady=10
        )
        self.log_box.pack(fill="both", expand=True, padx=12, pady=12)

        self.log_box.tag_config("info", foreground=self.INFO)
        self.log_box.tag_config("success", foreground=self.SUCCESS)
        self.log_box.tag_config("warning", foreground=self.WARNING)
        self.log_box.tag_config("error", foreground=self.ERROR)

        self.log("Ready.", "success")

    def make_button(self, parent, text, command, width=12, accent=False):
        bg = self.ACCENT if accent else self.BTN
        fg = "#0b0f12" if accent else self.FG
        active = "#81d4fa" if accent else self.BTN_ACTIVE

        return tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            bg=bg,
            fg=fg,
            activebackground=active,
            activeforeground=fg,
            relief="flat",
            bd=0,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            padx=10,
            pady=8
        )

    def make_checkbox(self, parent, text, variable):
        return tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            bg=self.PANEL,
            fg=self.FG,
            selectcolor=self.ENTRY_BG,
            activebackground=self.PANEL,
            activeforeground=self.FG,
            font=("Segoe UI", 10),
            relief="flat",
            bd=0,
            highlightthickness=0
        )

    def run_on_ui(self, fn, *args, **kwargs):
        self.root.after(0, lambda: fn(*args, **kwargs))

    def log(self, message, level="info"):
        def _write():
            self.log_box.insert(tk.END, message + "\n", level)
            self.log_box.see(tk.END)
        self.run_on_ui(_write)

    def clear_log(self):
        self.log_box.delete("1.0", tk.END)

    def set_progress(self, value, text=None):
        def _update():
            self.progress["value"] = max(0, min(100, value))
            if text is not None:
                self.progress_label.config(text=text)
        self.run_on_ui(_update)

    def set_uploading_state(self, uploading):
        self.is_uploading = uploading

        state = "disabled" if uploading else "normal"

        def _update():
            self.browse_btn.config(state=state)
            self.auto_btn.config(state=state)
            self.scan_btn.config(state=state)
            self.upload_btn.config(state=state)
            self.clear_btn.config(state=state)
            self.account_combo.config(state="disabled" if uploading else "readonly")
        self.run_on_ui(_update)

    def browse_base_dir(self):
        folder = filedialog.askdirectory(title="Select World of Warcraft Base Folder")
        if folder:
            self.base_dir_var.set(folder)
            self.log(f"Selected base directory: {folder}", "info")

    def auto_detect_base_dir(self):
        found = self.find_wow_base_dir()
        if found:
            self.base_dir_var.set(found)
            self.log(f"Auto-detected WoW base directory: {found}", "success")
        else:
            messagebox.showwarning("Not Found", "Could not auto-detect the World of Warcraft base folder.")
            self.log("Could not auto-detect WoW base directory", "warning")

    def update_account_dropdown(self, accounts):
        values = ["All Accounts"] + list(accounts.keys())
        self.account_combo["values"] = values
        self.account_var.set("All Accounts")

        if accounts:
            self.account_status.config(text=f"{len(accounts)} account(s) detected")
        else:
            self.account_status.config(text="No accounts detected")

    def scan_accounts(self):
        base_dir = self.base_dir_var.get().strip()

        if not base_dir:
            self.log("No base directory selected. Attempting auto-detect...", "warning")
            base_dir = self.find_wow_base_dir()
            if base_dir:
                self.base_dir_var.set(base_dir)
                self.log(f"Using auto-detected base directory: {base_dir}", "success")
            else:
                messagebox.showerror("Error", "Could not detect World of Warcraft base directory")
                self.log("Scan aborted: no WoW base directory found", "error")
                return

        base_path = Path(base_dir)
        if not base_path.exists() or not base_path.is_dir():
            messagebox.showerror("Error", "Selected base directory does not exist")
            self.log(f"Invalid base directory: {base_dir}", "error")
            return

        accounts = self.find_accounts_from_base(base_dir)
        self.detected_accounts = accounts
        self.update_account_dropdown(accounts)

        if accounts:
            self.log(f"Detected {len(accounts)} account(s):", "success")
            for name, path in accounts.items():
                self.log(f"  {name} -> {path}", "info")
        else:
            self.log("No GuildRosterExporter.lua files found for any account", "warning")

    def start_upload_thread(self):
        if self.is_uploading:
            return
        thread = threading.Thread(target=self.upload_data, daemon=True)
        thread.start()

    def find_wow_base_dir(self):
        candidates = [
            Path(r"C:\Program Files (x86)\World of Warcraft"),
            Path(r"C:\Program Files\World of Warcraft"),
            Path.home() / "Games" / "World of Warcraft",
            Path(r"D:\World of Warcraft"),
            Path(r"E:\World of Warcraft"),
        ]

        for path in candidates:
            if path.exists() and path.is_dir():
                retail = path / "_retail_"
                if retail.exists() and retail.is_dir():
                    return str(path)

        return None

    def find_accounts_from_base(self, base_dir):
        base = Path(base_dir)
        account_dir = base / "_retail_" / "WTF" / "Account"

        if not account_dir.exists():
            self.log(f"Account directory not found: {account_dir}", "warning")
            return {}

        found = {}

        try:
            for acct_dir in account_dir.iterdir():
                if acct_dir.is_dir():
                    candidate = acct_dir / "SavedVariables" / "GuildRosterExporter.lua"
                    if candidate.exists() and candidate.is_file():
                        found[acct_dir.name] = candidate
        except Exception as e:
            self.log(f"Error scanning accounts: {e}", "error")
            return {}

        return dict(sorted(found.items(), key=lambda item: item[0].lower()))

    def extract_saved_json(self, content: str, key_name: str):
        key = f'["{key_name}"] = "'
        start = content.find(key)
        if start == -1:
            return None

        start += len(key)
        i = start
        escaped = False

        while i < len(content):
            c = content[i]
            if c == '"' and not escaped:
                break
            escaped = (c == '\\' and not escaped)
            i += 1

        raw = content[start:i]
        return raw.replace(r'\"', '"')

    def extract_profiles(self, content: str):
        marker = '["profiles"] = {'
        start = content.find(marker)
        if start == -1:
            return []

        start = content.find("{", start)
        if start == -1:
            return []

        depth = 0
        i = start
        while i < len(content):
            ch = content[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    block = content[start:i + 1]
                    break
            i += 1
        else:
            return []

        entries = re.findall(r'\["([^"]+)"]\s*=\s*"((?:\\.|[^"\\])*)"', block)

        profiles = []
        seen = set()

        for key, raw in entries:
            json_str = raw.replace(r'\"', '"')
            try:
                profile = json.loads(json_str)
                dedupe = (
                    str(profile.get("name", "")).strip().lower(),
                    str(profile.get("realm", "")).strip().lower()
                )
                if dedupe not in seen:
                    profiles.append(profile)
                    seen.add(dedupe)
            except Exception as e:
                self.log(f"Profile parse error for {key}: {e}", "error")

        return profiles

    def post_json(self, endpoint: str, payload: dict):
        res = requests.post(
            endpoint,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-API-KEY": API_KEY
            },
            timeout=20,
            allow_redirects=True
        )

        self.log(f"POST {endpoint}", "info")
        self.log(f"HTTP: {res.status_code}", "info")

        body_preview = repr(res.text[:500])
        if 200 <= res.status_code < 300:
            self.log(f"BODY: {body_preview}", "success")
        elif 400 <= res.status_code < 500:
            self.log(f"BODY: {body_preview}", "warning")
        else:
            self.log(f"BODY: {body_preview}", "error")

        try:
            return res.json()
        except Exception:
            return {
                "status": "error",
                "http_status": res.status_code,
                "raw": res.text
            }

    def upload_single_file(self, file_path):
        self.log("-" * 72, "info")
        self.log(f"Reading Lua file: {file_path}", "info")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            self.log(f"Failed to read file {file_path}: {e}", "error")
            return False

        guild_json = self.extract_saved_json(content, "guild_json")
        legacy_profile_json = self.extract_saved_json(content, "profile_json")
        chat_json = self.extract_saved_json(content, "chat_json")
        raid_json = self.extract_saved_json(content, "raid_json")

        profiles = self.extract_profiles(content)

        if not profiles and legacy_profile_json:
            try:
                profiles = [json.loads(legacy_profile_json)]
                self.log("Using legacy profile_json fallback", "warning")
            except Exception as e:
                self.log(f"Legacy profile JSON error: {e}", "error")

        payload = {}

        if guild_json:
            try:
                payload["guild"] = json.loads(guild_json)
                self.log(f"Guild count: {len(payload['guild'])}", "success")
            except Exception as e:
                self.log(f"Guild JSON error: {e}", "error")
        else:
            self.log("No guild_json found", "warning")

        if profiles:
            payload["profiles"] = profiles
            self.log(f"Profile count: {len(profiles)}", "success")
            for p in profiles:
                self.log(
                    f"PROFILE: {p.get('name')} | {p.get('realm')} | "
                    f"{p.get('spec_name')} | ilvl {p.get('ilvl_equipped')}",
                    "info"
                )
        else:
            self.log("No profiles found", "warning")

        ok = True

        if payload:
            try:
                result = self.post_json(API_URL, payload)
                self.log(f"Upload result: {result}", "success")
            except Exception as e:
                self.log(f"Main upload failed: {e}", "error")
                ok = False
        else:
            self.log("Nothing to upload", "warning")
            ok = False

        if self.upload_chat_var.get() and chat_json:
            try:
                chat_items = json.loads(chat_json)
                self.log(f"Chat items: {len(chat_items)}", "success")
                for item in chat_items:
                    self.post_json(CHAT_URL, item)
            except Exception as e:
                self.log(f"Chat JSON error: {e}", "error")
                ok = False
        elif self.upload_chat_var.get():
            self.log("No chat_json found", "warning")

        if self.upload_raid_var.get() and raid_json:
            try:
                raid_items = json.loads(raid_json)
                self.log(f"Raid items: {len(raid_items)}", "success")
                for item in raid_items:
                    self.post_json(RAID_URL, item)
            except Exception as e:
                self.log(f"Raid JSON error: {e}", "error")
                ok = False
        elif self.upload_raid_var.get():
            self.log("No raid_json found", "warning")

        return ok

    def get_selected_files(self):
        if not self.detected_accounts:
            base_dir = self.base_dir_var.get().strip()
            if base_dir:
                self.detected_accounts = self.find_accounts_from_base(base_dir)
                self.run_on_ui(self.update_account_dropdown, self.detected_accounts)

        selected = self.account_var.get().strip()

        if not self.detected_accounts:
            return []

        if selected == "All Accounts":
            return list(self.detected_accounts.items())

        if selected in self.detected_accounts:
            return [(selected, self.detected_accounts[selected])]

        return []

    def upload_data(self):
        self.set_uploading_state(True)
        self.set_progress(0, "Progress: starting...")

        try:
            base_dir = self.base_dir_var.get().strip()

            if not base_dir:
                self.log("No base directory selected. Attempting auto-detect...", "warning")
                base_dir = self.find_wow_base_dir()
                if base_dir:
                    self.base_dir_var.set(base_dir)
                    self.log(f"Using auto-detected base directory: {base_dir}", "success")
                else:
                    self.log("Upload aborted: no WoW base directory found", "error")
                    self.run_on_ui(messagebox.showerror, "Error", "Could not detect World of Warcraft base directory")
                    self.set_progress(0, "Progress: failed")
                    return

            base_path = Path(base_dir)
            if not base_path.exists() or not base_path.is_dir():
                self.log(f"Invalid base directory: {base_dir}", "error")
                self.run_on_ui(messagebox.showerror, "Error", "Selected base directory does not exist")
                self.set_progress(0, "Progress: failed")
                return

            self.detected_accounts = self.find_accounts_from_base(base_dir)
            self.run_on_ui(self.update_account_dropdown, self.detected_accounts)

            selected_files = self.get_selected_files()

            if not selected_files:
                self.log("No matching account files found to upload", "error")
                self.run_on_ui(
                    messagebox.showerror,
                    "Error",
                    "No GuildRosterExporter.lua files were found for the selected account(s)."
                )
                self.set_progress(0, "Progress: failed")
                return

            total = len(selected_files)
            self.log(f"Uploading {total} account(s)...", "success")

            success_count = 0

            for index, (account_name, lua_file) in enumerate(selected_files, start=1):
                pct = ((index - 1) / total) * 100
                self.set_progress(pct, f"Progress: uploading {index}/{total} - {account_name}")

                self.log(f"Starting account: {account_name}", "info")
                ok = self.upload_single_file(lua_file)

                if ok:
                    success_count += 1
                    self.log(f"Finished account: {account_name}", "success")
                else:
                    self.log(f"Finished account with issues: {account_name}", "warning")

                pct = (index / total) * 100
                self.set_progress(pct, f"Progress: completed {index}/{total} - {account_name}")

            self.log("-" * 72, "info")
            self.log(f"Done. Successful uploads: {success_count}/{total}", "success" if success_count == total else "warning")
            self.set_progress(100, f"Progress: complete ({success_count}/{total} successful)")

            self.run_on_ui(
                messagebox.showinfo,
                "Finished",
                f"Upload complete.\nSuccessful uploads: {success_count}/{total}"
            )

        finally:
            self.set_uploading_state(False)


if __name__ == "__main__":
    root = tk.Tk()
    app = WoWUploaderApp(root)
    root.mainloop()