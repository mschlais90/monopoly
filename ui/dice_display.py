import tkinter as tk

# Dot grid positions (gx, gy) on a 0-6 normalised grid per die face
_DOTS = {
    1: [(3, 3)],
    2: [(1.5, 1.5), (4.5, 4.5)],
    3: [(1.5, 1.5), (3, 3),     (4.5, 4.5)],
    4: [(1.5, 1.5), (4.5, 1.5), (1.5, 4.5), (4.5, 4.5)],
    5: [(1.5, 1.5), (4.5, 1.5), (3, 3),     (1.5, 4.5), (4.5, 4.5)],
    6: [(1.5, 1),   (4.5, 1),   (1.5, 3),   (4.5, 3),   (1.5, 5),   (4.5, 5)],
}


class DiceDisplay(tk.Frame):
    """Shows two dice faces + total. Call show_roll(d1, d2) to update."""

    def __init__(self, parent, size=44, **kwargs):
        super().__init__(parent, **kwargs)
        self._size = size
        self._build()

    def _build(self):
        bg = self["bg"] if "bg" in self.keys() else "#1a252f"
        self.configure(bg=bg)

        tk.Label(self, text="Last roll:", font=("Arial", 8),
                 fg="#aaa", bg=bg).pack(side="left", padx=(4, 2))

        s = self._size
        self._c1 = tk.Canvas(self, width=s, height=s, bg=bg,
                              highlightthickness=0)
        self._c1.pack(side="left", padx=2)

        self._c2 = tk.Canvas(self, width=s, height=s, bg=bg,
                              highlightthickness=0)
        self._c2.pack(side="left", padx=2)

        self._total = tk.Label(self, text="", font=("Arial", 12, "bold"),
                               fg="#FFD700", bg=bg, width=4)
        self._total.pack(side="left", padx=4)

        self._draw_blank(self._c1)
        self._draw_blank(self._c2)

    def show_roll(self, d1, d2):
        self._draw_die(self._c1, d1)
        self._draw_die(self._c2, d2)
        doubles = " !" if d1 == d2 else ""
        self._total.config(text=f"= {d1 + d2}{doubles}")

    def _draw_blank(self, canvas):
        s = self._size
        canvas.delete("all")
        canvas.create_rectangle(2, 2, s - 2, s - 2,
                                 fill="#f5f5f5", outline="#bbb", width=2)

    def _draw_die(self, canvas, value):
        s = self._size
        canvas.delete("all")
        canvas.create_rectangle(2, 2, s - 2, s - 2,
                                 fill="white", outline="#333", width=2)
        r = max(3, s // 12)
        margin = s * 0.12
        span   = s - 2 * margin
        for gx, gy in _DOTS.get(value, []):
            px = margin + (gx / 6) * span
            py = margin + (gy / 6) * span
            canvas.create_oval(px - r, py - r, px + r, py + r,
                               fill="#222", outline="")
