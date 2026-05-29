import json
import sys
import tkinter as tk
from tkinter import ttk
from monitor_logic import FastBarMonitor
from pathlib import Path
from queue import Empty, Queue


SETTINGS_FILENAME = "auto_flask_settings.json"


class BarMonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("POE Auto Flask")
        self.geometry("560x640")
        self.minsize(520, 560)

        self.log_queue = Queue()
        self.coord_session = None
        self.monitor = FastBarMonitor(self.update_log)
        self.settings_path = self.get_settings_path()
        self.loaded_bar_settings = self.load_settings()

        self.configure(bg="#101820")
        self.create_styles()
        self.create_widgets()
        self.after(80, self.flush_log_queue)
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        if self.loaded_bar_settings:
            self.update_log("Saved bar settings loaded.")

    def get_settings_path(self):
        app_path = Path(sys.executable if getattr(sys, "frozen", False) else __file__)
        return app_path.resolve().parent / SETTINGS_FILENAME

    def load_settings(self):
        if not self.settings_path.exists():
            return False

        try:
            settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            self.update_log(f"Could not load saved settings: {error}")
            return False

        self.monitor.hp_coords = self.clean_coords(settings.get("hp_coords"))
        self.monitor.mana_coords = self.clean_coords(settings.get("mana_coords"))
        self.monitor.aura_coords = self.clean_coords(settings.get("aura_coords"))
        self.monitor.hp_threshold = float(settings.get("hp_threshold", self.monitor.hp_threshold))
        self.monitor.mana_threshold = float(settings.get("mana_threshold", self.monitor.mana_threshold))
        self.monitor.hp_key = str(settings.get("hp_key", self.monitor.hp_key))
        self.monitor.mana_key = str(settings.get("mana_key", self.monitor.mana_key))
        self.monitor.poll_interval = float(settings.get("poll_interval", self.monitor.poll_interval))
        self.monitor.debug_logging = bool(settings.get("debug_logging", self.monitor.debug_logging))
        return bool(self.monitor.hp_coords or self.monitor.mana_coords or self.monitor.aura_coords)

    def clean_coords(self, coords):
        if not isinstance(coords, list) or len(coords) != 4:
            return None
        try:
            return tuple(int(value) for value in coords)
        except (TypeError, ValueError):
            return None

    def save_settings(self):
        settings = {
            "hp_coords": list(self.monitor.hp_coords) if self.monitor.hp_coords else None,
            "mana_coords": list(self.monitor.mana_coords) if self.monitor.mana_coords else None,
            "aura_coords": list(self.monitor.aura_coords) if self.monitor.aura_coords else None,
            "hp_threshold": self.monitor.hp_threshold,
            "mana_threshold": self.monitor.mana_threshold,
            "hp_key": self.monitor.hp_key,
            "mana_key": self.monitor.mana_key,
            "poll_interval": self.monitor.poll_interval,
            "debug_logging": self.monitor.debug_logging
        }

        try:
            self.settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        except OSError as error:
            self.update_log(f"Could not save settings: {error}")

    def create_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#101820")
        self.style.configure("Panel.TFrame", background="#18242e")
        self.style.configure("TLabel", background="#101820", foreground="#dce6ee", font=("Segoe UI", 10))
        self.style.configure("Muted.TLabel", background="#18242e", foreground="#94a3af", font=("Segoe UI", 9))
        self.style.configure("Panel.TLabel", background="#18242e", foreground="#dce6ee", font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", background="#101820", foreground="#f6f8fb", font=("Segoe UI", 18, "bold"))
        self.style.configure("Status.TLabel", background="#101820", foreground="#8fbf7f", font=("Segoe UI", 10, "bold"))
        self.style.configure("TLabelframe", background="#18242e", foreground="#f6f8fb", bordercolor="#2e3c48")
        self.style.configure("TLabelframe.Label", background="#18242e", foreground="#f6f8fb", font=("Segoe UI", 11, "bold"))
        self.style.configure("TButton", font=("Segoe UI", 10), padding=(12, 8), background="#233241", foreground="#f6f8fb")
        self.style.map("TButton", background=[("active", "#2d4254")], foreground=[("disabled", "#7b8790")])
        self.style.configure("Accent.TButton", background="#2d6cdf", foreground="#ffffff")
        self.style.map("Accent.TButton", background=[("active", "#3b7ff0")])
        self.style.configure("Danger.TButton", background="#8f3f4a", foreground="#ffffff")
        self.style.map("Danger.TButton", background=[("active", "#a64a56")])
        self.style.configure("TEntry", fieldbackground="#0f171f", foreground="#f6f8fb", insertcolor="#f6f8fb")
        self.style.configure("Horizontal.TScale", background="#18242e", troughcolor="#0f171f")
        self.style.configure("TCheckbutton", background="#18242e", foreground="#dce6ee", font=("Segoe UI", 10))

    def create_widgets(self):
        shell = ttk.Frame(self, padding=18)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        header = ttk.Frame(shell)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="POE Auto Flask", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.status_label = ttk.Label(header, text="Idle", style="Status.TLabel")
        self.status_label.grid(row=0, column=2, sticky="e")
        self.aura_nav_button = ttk.Button(header, text="Aura Bot", command=self.show_aura_view)
        self.aura_nav_button.grid(row=0, column=1, sticky="e", padx=(12, 12))

        self.content_frame = ttk.Frame(shell)
        self.content_frame.grid(row=1, column=0, sticky="nsew")
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=1)

        self.flask_frame = ttk.Frame(self.content_frame)
        self.flask_frame.grid(row=0, column=0, sticky="nsew")
        self.flask_frame.columnconfigure(0, weight=1)
        self.flask_frame.rowconfigure(3, weight=1)

        self.aura_frame = ttk.Frame(self.content_frame)
        self.aura_frame.grid(row=0, column=0, sticky="nsew")
        self.aura_frame.columnconfigure(0, weight=1)
        self.aura_frame.rowconfigure(2, weight=1)

        self.hp_threshold_value = tk.StringVar(value=f"{self.monitor.hp_threshold:.0f}%")
        self.mana_threshold_value = tk.StringVar(value=f"{self.monitor.mana_threshold:.0f}%")
        self.poll_interval_value = tk.StringVar(value=f"{int(self.monitor.poll_interval * 1000)} ms")
        self.debug_logging_var = tk.BooleanVar(value=self.monitor.debug_logging)

        self.hp_threshold_scale, self.hp_key_entry = self.create_bar_panel(
            self.flask_frame, 0, "HP", "red", self.monitor.hp_threshold, self.monitor.hp_key,
            self.hp_threshold_value, self.set_hp_bar, self.update_hp_threshold, self.update_hp_key
        )
        self.mana_threshold_scale, self.mana_key_entry = self.create_bar_panel(
            self.flask_frame, 1, "Mana", "blue", self.monitor.mana_threshold, self.monitor.mana_key,
            self.mana_threshold_value, self.set_mana_bar, self.update_mana_threshold, self.update_mana_key
        )

        performance_frame = ttk.LabelFrame(self.flask_frame, text="Performance", padding=12)
        performance_frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        performance_frame.columnconfigure(1, weight=1)
        ttk.Label(performance_frame, text="Poll interval", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        self.poll_interval_scale = ttk.Scale(performance_frame, from_=80, to=400, orient="horizontal")
        self.poll_interval_scale.set(self.monitor.poll_interval * 1000)
        self.poll_interval_scale.grid(row=0, column=1, sticky="ew", padx=12)
        self.poll_interval_scale.bind("<ButtonRelease-1>", lambda event: self.update_poll_interval())
        ttk.Label(performance_frame, textvariable=self.poll_interval_value, style="Muted.TLabel", width=8).grid(row=0, column=2, sticky="e")
        ttk.Checkbutton(
            performance_frame,
            text="Verbose debug log",
            variable=self.debug_logging_var,
            command=self.update_debug_logging
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(10, 0))

        log_frame = ttk.LabelFrame(self.flask_frame, text="Log", padding=12)
        log_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 12))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(
            log_frame,
            height=10,
            state="disabled",
            wrap="word",
            relief="flat",
            bd=0,
            bg="#0b1117",
            fg="#dce6ee",
            insertbackground="#dce6ee",
            selectbackground="#2d6cdf",
            font=("Consolas", 9),
            padx=10,
            pady=10
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        controls_frame = ttk.Frame(self.flask_frame)
        controls_frame.grid(row=4, column=0, sticky="ew")
        controls_frame.columnconfigure(0, weight=1)
        controls_frame.columnconfigure(1, weight=0)
        self.start_pause_button = ttk.Button(
            controls_frame,
            text="Start Monitoring",
            style="Accent.TButton",
            command=self.toggle_monitoring
        )
        self.start_pause_button.grid(row=0, column=0, sticky="ew")
        ttk.Button(
            controls_frame,
            text="Reset Bars",
            command=self.reset_bar_settings
        ).grid(row=0, column=1, sticky="e", padx=(12, 0))

        self.create_aura_view()
        self.show_flask_view()

    def create_aura_view(self):
        aura_header = ttk.Frame(self.aura_frame)
        aura_header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        aura_header.columnconfigure(0, weight=1)
        ttk.Label(aura_header, text="Aura Bot", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(aura_header, text="Flask", command=self.show_flask_view).grid(row=0, column=1, sticky="e")

        aura_settings = ttk.LabelFrame(self.aura_frame, text="Aura Pathing", padding=12)
        aura_settings.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        aura_settings.columnconfigure(0, weight=1)
        ttk.Label(
            aura_settings,
            text="Set the thin green bar with F2 and F3. Aura Bot clicks below its center every second.",
            style="Panel.TLabel",
            wraplength=480
        ).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Button(aura_settings, text="Set Aura Bar", command=self.set_aura_bar).grid(row=1, column=0, sticky="w", pady=(12, 0))
        ttk.Button(aura_settings, text="Reset Aura Bar", command=self.reset_aura_bar).grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(12, 0))
        ttk.Label(aura_settings, text="Ctrl+S stops Aura Bot while this app is focused.", style="Muted.TLabel").grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(12, 0)
        )

        aura_log_frame = ttk.LabelFrame(self.aura_frame, text="Aura Log", padding=12)
        aura_log_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 12))
        aura_log_frame.rowconfigure(0, weight=1)
        aura_log_frame.columnconfigure(0, weight=1)
        self.aura_log_text = tk.Text(
            aura_log_frame,
            height=10,
            state="disabled",
            wrap="word",
            relief="flat",
            bd=0,
            bg="#0b1117",
            fg="#dce6ee",
            insertbackground="#dce6ee",
            selectbackground="#2d6cdf",
            font=("Consolas", 9),
            padx=10,
            pady=10
        )
        self.aura_log_text.grid(row=0, column=0, sticky="nsew")

        aura_controls = ttk.Frame(self.aura_frame)
        aura_controls.grid(row=3, column=0, sticky="ew")
        aura_controls.columnconfigure(0, weight=1)
        self.aura_start_pause_button = ttk.Button(
            aura_controls,
            text="Start Aura Bot",
            style="Accent.TButton",
            command=self.toggle_aura_bot
        )
        self.aura_start_pause_button.grid(row=0, column=0, sticky="ew")
        self.bind_all("<Control-s>", self.stop_aura_bot_shortcut)
        self.bind_all("<Control-S>", self.stop_aura_bot_shortcut)

    def create_bar_panel(self, parent, row, name, color, threshold, key, value_var, set_command, threshold_command, key_command):
        frame = ttk.LabelFrame(parent, text=f"{name} Settings", padding=12)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Threshold", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        scale = ttk.Scale(frame, from_=0, to=100, orient="horizontal")
        scale.set(threshold)
        scale.grid(row=0, column=1, sticky="ew", padx=12)
        scale.bind("<ButtonRelease-1>", lambda event: threshold_command())
        ttk.Label(frame, textvariable=value_var, style="Muted.TLabel", width=6).grid(row=0, column=2, sticky="e")

        ttk.Label(frame, text="Flask key", style="Panel.TLabel").grid(row=1, column=0, sticky="w", pady=(10, 0))
        key_entry = ttk.Entry(frame, width=8)
        key_entry.insert(0, key)
        key_entry.grid(row=1, column=1, sticky="w", padx=12, pady=(10, 0))
        key_entry.bind("<FocusOut>", lambda event: key_command())
        key_entry.bind("<Return>", lambda event: key_command())

        ttk.Button(frame, text=f"Set {name} Bar", command=set_command).grid(row=1, column=2, sticky="e", pady=(10, 0))
        ttk.Label(frame, text=f"Uses {color} bar detection", style="Muted.TLabel").grid(row=2, column=0, columnspan=3, sticky="w", pady=(10, 0))
        return scale, key_entry

    def update_log(self, message):
        """Queue a log message from any thread."""
        self.log_queue.put(message)

    def flush_log_queue(self):
        """Update the Tk log from the UI thread."""
        try:
            while True:
                self.write_log(self.log_queue.get_nowait())
        except Empty:
            pass
        self.after(80, self.flush_log_queue)

    def write_log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        if hasattr(self, "aura_log_text"):
            self.aura_log_text.config(state="normal")
            self.aura_log_text.insert("end", message.rstrip() + "\n")
            self.aura_log_text.see("end")
            self.aura_log_text.config(state="disabled")

    def show_flask_view(self):
        self.flask_frame.tkraise()
        self.aura_nav_button.config(state="normal")

    def show_aura_view(self):
        self.aura_frame.tkraise()
        self.aura_nav_button.config(state="disabled")

    def set_hp_bar(self):
        self.start_coord_capture("HP")
    
    def set_mana_bar(self):
        self.start_coord_capture("Mana")

    def set_aura_bar(self):
        self.start_coord_capture("Aura")

    def start_coord_capture(self, bar_type):
        """Capture bar coordinates without blocking the Tk event loop."""
        if self.coord_session:
            self.finish_coord_capture(cancel=True)

        on_f2, on_f3, coords = self.monitor.get_coords(bar_type)
        self.coord_session = {
            "bar_type": bar_type,
            "coords": coords,
            "on_f2": on_f2,
            "on_f3": on_f3
        }
        self.status_label.config(text=f"Set {bar_type}: F2 then F3")
        self.bind_all("<F2>", self.capture_start_point)
        self.bind_all("<F3>", self.capture_end_point)

    def capture_start_point(self, event=None):
        if self.coord_session:
            self.coord_session["on_f2"]()

    def capture_end_point(self, event=None):
        if not self.coord_session:
            return
        self.coord_session["on_f3"]()
        if len(self.coord_session["coords"]) >= 2:
            self.finish_coord_capture()

    def finish_coord_capture(self, cancel=False):
        session = self.coord_session
        self.unbind_all("<F2>")
        self.unbind_all("<F3>")
        self.coord_session = None

        if cancel or not session:
            self.status_label.config(text="Idle")
            return

        coords = session["coords"]
        bar_type = session["bar_type"]
        bar_coords = (coords[0][0], coords[0][1], coords[1][0], coords[1][1])

        if bar_type == "HP":
            self.monitor.hp_coords = bar_coords
        elif bar_type == "Mana":
            self.monitor.mana_coords = bar_coords
        else:
            self.monitor.aura_coords = bar_coords

        self.save_settings()
        self.status_label.config(text="Idle")
        self.update_log(f"{bar_type} bar coordinates saved successfully.")

    def reset_bar_settings(self):
        self.monitor.hp_coords = None
        self.monitor.mana_coords = None
        self.monitor.hp_buffer.clear()
        self.monitor.mana_buffer.clear()
        self.monitor.previous_hp_percentage = 100
        self.monitor.previous_mana_percentage = 100
        self.save_settings()
        self.status_label.config(text="Monitoring" if self.monitor.monitoring else "Idle")
        self.update_log("Saved bar coordinates reset.")

    def reset_aura_bar(self):
        self.monitor.stop_aura_bot()
        self.monitor.aura_coords = None
        self.save_settings()
        self.update_aura_button()
        self.status_label.config(text="Idle")
        self.update_log("Saved Aura bar coordinates reset.")

    def update_hp_threshold(self):
        """Update HP threshold from the scale."""
        self.monitor.hp_threshold = self.hp_threshold_scale.get()
        self.hp_threshold_value.set(f"{self.monitor.hp_threshold:.0f}%")
        self.save_settings()
        self.update_log(f"HP Threshold updated to {self.monitor.hp_threshold:.0f}%")

    def update_mana_threshold(self):
        """Update Mana threshold from the scale."""
        self.monitor.mana_threshold = self.mana_threshold_scale.get()
        self.mana_threshold_value.set(f"{self.monitor.mana_threshold:.0f}%")
        self.save_settings()
        self.update_log(f"Mana Threshold updated to {self.monitor.mana_threshold:.0f}%")

    def update_hp_key(self):
        """Update HP flask key from the entry."""
        self.monitor.hp_key = self.hp_key_entry.get().strip() or self.monitor.hp_key
        self.hp_key_entry.delete(0, tk.END)
        self.hp_key_entry.insert(0, self.monitor.hp_key)
        self.save_settings()
        self.update_log(f"HP Flask Key updated to '{self.monitor.hp_key}'")

    def update_mana_key(self):
        """Update Mana flask key from the entry."""
        self.monitor.mana_key = self.mana_key_entry.get().strip() or self.monitor.mana_key
        self.mana_key_entry.delete(0, tk.END)
        self.mana_key_entry.insert(0, self.monitor.mana_key)
        self.save_settings()
        self.update_log(f"Mana Flask Key updated to '{self.monitor.mana_key}'")

    def update_poll_interval(self):
        interval_ms = int(self.poll_interval_scale.get())
        self.monitor.poll_interval = interval_ms / 1000
        self.poll_interval_value.set(f"{interval_ms} ms")
        self.save_settings()
        self.update_log(f"Poll interval updated to {interval_ms} ms")

    def update_debug_logging(self):
        self.monitor.debug_logging = self.debug_logging_var.get()
        state = "enabled" if self.monitor.debug_logging else "disabled"
        self.save_settings()
        self.update_log(f"Verbose debug log {state}.")

    def toggle_monitoring(self):
        self.monitor.toggle_monitoring()
        is_monitoring = self.monitor.monitoring
        self.start_pause_button.config(
            text="Pause Monitoring" if is_monitoring else "Start Monitoring",
            style="Danger.TButton" if is_monitoring else "Accent.TButton"
        )
        self.status_label.config(text="Monitoring" if is_monitoring else "Idle")

    def toggle_aura_bot(self):
        self.monitor.toggle_aura_bot()
        self.update_aura_button()
        self.status_label.config(text="Aura Bot" if self.monitor.aura_monitoring else "Idle")

    def stop_aura_bot_shortcut(self, event=None):
        self.monitor.stop_aura_bot()
        self.update_aura_button()
        self.status_label.config(text="Idle")
        return "break"

    def update_aura_button(self):
        is_running = self.monitor.aura_monitoring
        self.aura_start_pause_button.config(
            text="Stop Aura Bot" if is_running else "Start Aura Bot",
            style="Danger.TButton" if is_running else "Accent.TButton"
        )

    def close_app(self):
        if self.monitor.monitoring:
            self.monitor.toggle_monitoring()
        self.monitor.stop_aura_bot()
        self.destroy()



if __name__ == "__main__":
    app = BarMonitorApp()
    app.mainloop()
