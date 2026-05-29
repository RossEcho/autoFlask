import tkinter as tk
from tkinter import ttk
from monitor_logic import FastBarMonitor
from queue import Empty, Queue


class BarMonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("POE Auto Flask")
        self.geometry("560x640")
        self.minsize(520, 560)

        self.log_queue = Queue()
        self.coord_session = None
        self.monitor = FastBarMonitor(self.update_log)

        self.configure(bg="#101820")
        self.create_styles()
        self.create_widgets()
        self.after(80, self.flush_log_queue)

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
        shell.rowconfigure(4, weight=1)

        header = ttk.Frame(shell)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="POE Auto Flask", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.status_label = ttk.Label(header, text="Idle", style="Status.TLabel")
        self.status_label.grid(row=0, column=1, sticky="e")

        self.hp_threshold_value = tk.StringVar(value=f"{self.monitor.hp_threshold:.0f}%")
        self.mana_threshold_value = tk.StringVar(value=f"{self.monitor.mana_threshold:.0f}%")
        self.poll_interval_value = tk.StringVar(value=f"{int(self.monitor.poll_interval * 1000)} ms")
        self.debug_logging_var = tk.BooleanVar(value=self.monitor.debug_logging)

        self.hp_threshold_scale, self.hp_key_entry = self.create_bar_panel(
            shell, 1, "HP", "red", self.monitor.hp_threshold, self.monitor.hp_key,
            self.hp_threshold_value, self.set_hp_bar, self.update_hp_threshold, self.update_hp_key
        )
        self.mana_threshold_scale, self.mana_key_entry = self.create_bar_panel(
            shell, 2, "Mana", "blue", self.monitor.mana_threshold, self.monitor.mana_key,
            self.mana_threshold_value, self.set_mana_bar, self.update_mana_threshold, self.update_mana_key
        )

        performance_frame = ttk.LabelFrame(shell, text="Performance", padding=12)
        performance_frame.grid(row=3, column=0, sticky="ew", pady=(0, 12))
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

        log_frame = ttk.LabelFrame(shell, text="Log", padding=12)
        log_frame.grid(row=4, column=0, sticky="nsew", pady=(0, 12))
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

        controls_frame = ttk.Frame(shell)
        controls_frame.grid(row=5, column=0, sticky="ew")
        controls_frame.columnconfigure(0, weight=1)
        self.start_pause_button = ttk.Button(
            controls_frame,
            text="Start Monitoring",
            style="Accent.TButton",
            command=self.toggle_monitoring
        )
        self.start_pause_button.grid(row=0, column=0, sticky="ew")

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

    def set_hp_bar(self):
        self.start_coord_capture("HP")
    
    def set_mana_bar(self):
        self.start_coord_capture("Mana")

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
        else:
            self.monitor.mana_coords = bar_coords

        self.status_label.config(text="Idle")
        self.update_log(f"{bar_type} bar coordinates set successfully.")

    def update_hp_threshold(self):
        """Update HP threshold from the scale."""
        self.monitor.hp_threshold = self.hp_threshold_scale.get()
        self.hp_threshold_value.set(f"{self.monitor.hp_threshold:.0f}%")
        self.update_log(f"HP Threshold updated to {self.monitor.hp_threshold:.0f}%")

    def update_mana_threshold(self):
        """Update Mana threshold from the scale."""
        self.monitor.mana_threshold = self.mana_threshold_scale.get()
        self.mana_threshold_value.set(f"{self.monitor.mana_threshold:.0f}%")
        self.update_log(f"Mana Threshold updated to {self.monitor.mana_threshold:.0f}%")

    def update_hp_key(self):
        """Update HP flask key from the entry."""
        self.monitor.hp_key = self.hp_key_entry.get().strip() or self.monitor.hp_key
        self.hp_key_entry.delete(0, tk.END)
        self.hp_key_entry.insert(0, self.monitor.hp_key)
        self.update_log(f"HP Flask Key updated to '{self.monitor.hp_key}'")

    def update_mana_key(self):
        """Update Mana flask key from the entry."""
        self.monitor.mana_key = self.mana_key_entry.get().strip() or self.monitor.mana_key
        self.mana_key_entry.delete(0, tk.END)
        self.mana_key_entry.insert(0, self.monitor.mana_key)
        self.update_log(f"Mana Flask Key updated to '{self.monitor.mana_key}'")

    def update_poll_interval(self):
        interval_ms = int(self.poll_interval_scale.get())
        self.monitor.poll_interval = interval_ms / 1000
        self.poll_interval_value.set(f"{interval_ms} ms")
        self.update_log(f"Poll interval updated to {interval_ms} ms")

    def update_debug_logging(self):
        self.monitor.debug_logging = self.debug_logging_var.get()
        state = "enabled" if self.monitor.debug_logging else "disabled"
        self.update_log(f"Verbose debug log {state}.")

    def toggle_monitoring(self):
        self.monitor.toggle_monitoring()
        is_monitoring = self.monitor.monitoring
        self.start_pause_button.config(
            text="Pause Monitoring" if is_monitoring else "Start Monitoring",
            style="Danger.TButton" if is_monitoring else "Accent.TButton"
        )
        self.status_label.config(text="Monitoring" if is_monitoring else "Idle")



if __name__ == "__main__":
    app = BarMonitorApp()
    app.mainloop()
