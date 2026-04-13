import tkinter as tk
from tkinter import ttk

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, settings, **kwargs):
        super().__init__(parent, **kwargs)
        self.settings = settings
        self.title("Settings")
        self.configure(bg="#1a1a2e")
        self.resizable(False, False)
        self.grab_set()
        self._show_dice_var = tk.BooleanVar(value=settings.show_dice)
        self._animate_var   = tk.BooleanVar(value=settings.animate_movement)
        self._build()
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width()  // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{px - self.winfo_width()//2}+{py - self.winfo_height()//2}")

    def _build(self):
        tk.Label(self, text="SETTINGS", font=("Georgia", 14, "bold italic"),
                 fg="#FFD700", bg="#1a1a2e").pack(pady=(16, 8))

        card = tk.Frame(self, bg="#16213e", padx=24, pady=16)
        card.pack(padx=24, pady=4, fill="x")

        def row(var, text, sub):
            f = tk.Frame(card, bg="#16213e")
            f.pack(fill="x", pady=6)
            tk.Checkbutton(f, variable=var, bg="#16213e",
                           fg="#e0e0e0", selectcolor="#0f3460",
                           activebackground="#16213e",
                           font=("Arial", 11, "bold"), text=text,
                           anchor="w").pack(anchor="w")
            tk.Label(f, text=sub, bg="#16213e", fg="#888",
                     font=("Arial", 9), anchor="w").pack(anchor="w", padx=22)

        row(self._show_dice_var,
            "Show dice after each roll",
            "Displays both dice faces and total in the controls bar.")
        row(self._animate_var,
            "Animate token movement  (2 seconds per turn)",
            "Moves the player token step-by-step across the board.\n"
            "Skipped automatically at speed 4–5 in auto-run mode.")

        btn = tk.Frame(self, bg="#1a1a2e")
        btn.pack(pady=14)
        tk.Button(btn, text="Save", command=self._save,
                  bg="#27AE60", fg="white", font=("Arial", 11, "bold"),
                  relief="flat", padx=20, pady=6, cursor="hand2").pack(side="left", padx=8)
        tk.Button(btn, text="Cancel", command=self.destroy,
                  bg="#7f8c8d", fg="white", font=("Arial", 11),
                  relief="flat", padx=16, pady=6, cursor="hand2").pack(side="left", padx=8)

    def _save(self):
        self.settings.show_dice         = self._show_dice_var.get()
        self.settings.animate_movement  = self._animate_var.get()
        self.destroy()
