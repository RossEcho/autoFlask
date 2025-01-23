import tkinter as tk
from tkinter import ttk
from monitor_logic import FastBarMonitor
import threading


class BarMonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bar Monitor Setup")
        self.geometry("500x600")
        self.monitor = FastBarMonitor(self.update_log)
        self.monitoring = False

        # Create UI components
        self.create_widgets()

    def create_widgets(self):
        # HP Settings
        hp_frame = ttk.LabelFrame(self, text="HP Settings", padding=10)
        hp_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(hp_frame, text="Set HP Bar", command=self.set_hp_bar).pack(pady=5)
        ttk.Label(hp_frame, text="Set HP Threshold (%):").pack()
        self.hp_threshold_scale = ttk.Scale(hp_frame, from_=0, to=100, orient="horizontal", length=200)
        self.hp_threshold_scale.set(self.monitor.hp_threshold)
        self.hp_threshold_scale.pack()
        self.hp_threshold_scale.bind("<ButtonRelease-1>", lambda event: self.update_hp_threshold())

        ttk.Label(hp_frame, text="Set HP Flask Key:").pack()
        self.hp_key_entry = ttk.Entry(hp_frame)
        self.hp_key_entry.insert(0, self.monitor.hp_key)
        self.hp_key_entry.pack()
        self.hp_key_entry.bind("<FocusOut>", lambda event: self.update_hp_key())

        # Mana Settings
        mana_frame = ttk.LabelFrame(self, text="Mana Settings", padding=10)
        mana_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(mana_frame, text="Set Mana Bar", command=self.set_mana_bar).pack(pady=5)
        ttk.Label(mana_frame, text="Set Mana Threshold (%):").pack()
        self.mana_threshold_scale = ttk.Scale(mana_frame, from_=0, to=100, orient="horizontal", length=200)
        self.mana_threshold_scale.set(self.monitor.mana_threshold)
        self.mana_threshold_scale.pack()
        self.mana_threshold_scale.bind("<ButtonRelease-1>", lambda event: self.update_mana_threshold())

        ttk.Label(mana_frame, text="Set Mana Flask Key:").pack()
        self.mana_key_entry = ttk.Entry(mana_frame)
        self.mana_key_entry.insert(0, self.monitor.mana_key)
        self.mana_key_entry.pack()
        self.mana_key_entry.bind("<FocusOut>", lambda event: self.update_mana_key())

        # Log Window
        log_frame = ttk.LabelFrame(self, text="Log", padding=10)
        log_frame.pack(fill="both", padx=10, pady=5, expand=True)
        self.log_text = tk.Text(log_frame, height=10, state="disabled", wrap="word", relief="groove", bd=2)
        self.log_text.pack(fill="both", expand=True)

        # Control Button
        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill="x", padx=10, pady=10)

        self.start_pause_button = ttk.Button(controls_frame, text="Start Monitoring", command=self.toggle_monitoring)
        self.start_pause_button.pack(side="left", padx=10)

    def update_log(self, message):
        """Update the log window with new messages."""
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def set_hp_bar(self):
        """Set up the HP bar by capturing coordinates."""
        on_f2, on_f3, coords = self.monitor.get_coords("HP")

        # Bind keys to capture coordinates
        self.bind("<F2>", lambda event: on_f2())
        self.bind("<F3>", lambda event: on_f3())

        # Wait until both points are captured
        while len(coords) < 2:
            self.update()

        # Unbind keys after capturing coordinates
        self.unbind("<F2>")
        self.unbind("<F3>")

        if len(coords) == 2:
            self.monitor.hp_coords = (coords[0][0], coords[0][1], coords[1][0], coords[1][1])
            self.log("HP bar coordinates set successfully.")
    
    def set_mana_bar(self):
        """Set up the Mana bar by capturing coordinates."""
        on_f2, on_f3, coords = self.monitor.get_coords("Mana")

        # Bind keys to capture coordinates
        self.bind("<F2>", lambda event: on_f2())
        self.bind("<F3>", lambda event: on_f3())

        # Wait until both points are captured
        while len(coords) < 2:
            self.update()

        # Unbind keys after capturing coordinates
        self.unbind("<F2>")
        self.unbind("<F3>")

        if len(coords) == 2:
            self.monitor.mana_coords = (coords[0][0], coords[0][1], coords[1][0], coords[1][1])
            self.log("Mana bar coordinates set successfully.")

    
    def log(self, message):
        """Update the log window with a new message."""
        print(message)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)  # Auto-scroll to the latest log
        self.log_text.config(state=tk.DISABLED)
        

    def update_hp_threshold(self):
        """Update HP threshold from the scale."""
        self.monitor.hp_threshold = self.hp_threshold_scale.get()
        self.update_log(f"HP Threshold updated to {self.monitor.hp_threshold}%")

    def update_mana_threshold(self):
        """Update Mana threshold from the scale."""
        self.monitor.mana_threshold = self.mana_threshold_scale.get()
        self.update_log(f"Mana Threshold updated to {self.monitor.mana_threshold}%")

    def update_hp_key(self):
        """Update HP flask key from the entry."""
        self.monitor.hp_key = self.hp_key_entry.get()
        self.update_log(f"HP Flask Key updated to '{self.monitor.hp_key}'")

    def update_mana_key(self):
        """Update Mana flask key from the entry."""
        self.monitor.mana_key = self.mana_key_entry.get()
        self.update_log(f"Mana Flask Key updated to '{self.monitor.mana_key}'")

    def toggle_monitoring(self):
        self.monitor.toggle_monitoring()
        self.start_pause_button.config(
            text="Pause Monitoring" if self.monitor.monitoring else "Start Monitoring"
        )



if __name__ == "__main__":
    app = BarMonitorApp()
    app.mainloop()
