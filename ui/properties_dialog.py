import tkinter as tk
from tkinter import ttk, messagebox
from game.constants import COLOR_GROUPS, COLOR_HEX


def _can_mortgage(prop, engine):
    if prop.mortgaged or prop.houses > 0:
        return False
    if prop.type == "property":
        group = COLOR_GROUPS.get(prop.color, [])
        if any(engine.board_properties[p].houses > 0
               for p in group if engine.board_properties[p].owner == prop.owner):
            return False
    return True


def _can_unmortgage(prop):
    return prop.mortgaged and prop.owner and prop.owner.money >= prop.unmortgage_cost


def _can_buy_house(prop, engine):
    if prop.type != "property" or prop.mortgaged or prop.houses >= 5:
        return False
    player = prop.owner
    if not player:
        return False
    group = COLOR_GROUPS.get(prop.color, [])
    bp = engine.board_properties
    if not all(bp[p].owner == player for p in group):
        return False
    if any(bp[p].mortgaged for p in group):
        return False
    min_h = min(bp[p].houses for p in group)
    if prop.houses > min_h:
        return False
    return player.money >= prop.house_cost


class PropertiesDialog(tk.Toplevel):
    def __init__(self, parent, engine, refresh_callback=None):
        super().__init__(parent)
        self.engine = engine
        self.refresh_callback = refresh_callback
        self.title("Property Management")
        self.configure(bg="#1a1a2e")
        self.resizable(True, True)
        self.grab_set()
        self.geometry("820x580")
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._centre(parent)

    def _centre(self, parent):
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{px - self.winfo_width()//2}+{py - self.winfo_height()//2}")

    def _on_close(self):
        if self.refresh_callback:
            self.refresh_callback()
        self.destroy()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        tk.Label(self, text="PROPERTY MANAGEMENT",
                 font=("Georgia", 14, "bold italic"),
                 fg="#FFD700", bg="#1a1a2e").pack(pady=(10, 4))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=4)
        self._populate_tabs()

        tk.Button(self, text="Close", command=self._on_close,
                  bg="#7f8c8d", fg="white", font=("Arial", 11),
                  relief="flat", padx=20, pady=6,
                  cursor="hand2").pack(pady=8)

    def _populate_tabs(self):
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        for player in self.engine.all_players:
            if player.bankrupt:
                continue
            tab = tk.Frame(self.notebook, bg="#16213e")
            self.notebook.add(tab, text=f"  {player.name}  ")
            self._build_tab(tab, player)

    def _build_tab(self, tab, player):
        from strategies.human import HumanStrategy
        is_human = isinstance(player.strategy, HumanStrategy)

        # ── Header ──
        hdr = tk.Frame(tab, bg=player.color)
        hdr.pack(fill="x")
        tk.Label(hdr,
                 text=f"  {player.name}   Cash: ${player.money:,}   Net Worth: ${player.net_worth():,}",
                 bg=player.color, fg="white",
                 font=("Arial", 10, "bold"), pady=5).pack(side="left")
        if is_human:
            tk.Label(hdr, text="[Human — manage your properties here]  ",
                     bg=player.color, fg="#dddddd",
                     font=("Arial", 8)).pack(side="right")

        # ── Column headers ──
        col_hdr = tk.Frame(tab, bg="#0f3460")
        col_hdr.pack(fill="x", padx=4, pady=(4, 0))
        for text, width in [("", 3), ("Property", 22), ("Status", 11),
                             ("Rent", 9), ("Mtg.$", 8), ("Actions", 0)]:
            tk.Label(col_hdr, text=text, bg="#0f3460", fg="#aaa",
                     font=("Arial", 8, "bold"),
                     width=width, anchor="w").pack(side="left", padx=3)

        # ── Scrollable property list ──
        canvas = tk.Canvas(tab, bg="#16213e", highlightthickness=0)
        sb = tk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg="#16213e")
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _resize(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win_id, width=canvas.winfo_width())

        inner.bind("<Configure>", _resize)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))

        if not player.properties:
            tk.Label(inner, text="No properties owned.",
                     bg="#16213e", fg="#666",
                     font=("Arial", 10), pady=20).pack()
            return

        for prop in sorted(player.properties, key=lambda p: p.pos):
            self._property_row(inner, prop, player, is_human)

    # ── Property row ──────────────────────────────────────────────────────────

    def _property_row(self, parent, prop, player, is_human):
        row_bg = "#1a1a2e" if (prop.pos % 2 == 0) else "#16213e"
        if prop.mortgaged:
            row_bg = "#2d1515"

        row = tk.Frame(parent, bg=row_bg, pady=4)
        row.pack(fill="x", padx=4, pady=1)

        # Colour swatch
        if prop.type == "property":
            swatch_color = COLOR_HEX.get(prop.color, "#888")
        elif prop.type == "railroad":
            swatch_color = "#bbbbbb"
        else:
            swatch_color = "#aaddff"
        tk.Label(row, text="■", fg=swatch_color, bg=row_bg,
                 font=("Arial", 13), width=2).pack(side="left", padx=(4, 0))

        # Name
        name_fg = "#777" if prop.mortgaged else "#e0e0e0"
        tk.Label(row, text=prop.name, bg=row_bg, fg=name_fg,
                 font=("Arial", 9), width=22, anchor="w").pack(side="left", padx=4)

        # Status
        if prop.mortgaged:
            st_txt, st_fg = "MORTGAGED", "#FF7043"
        elif prop.type == "property":
            h = prop.houses
            if h == 5:
                st_txt, st_fg = "Hotel", "#E74C3C"
            elif h > 0:
                st_txt, st_fg = f"{h} House{'s' if h!=1 else ''}", "#4CAF50"
            else:
                st_txt, st_fg = "No houses", "#888"
        else:
            st_txt, st_fg = "—", "#888"
        tk.Label(row, text=st_txt, bg=row_bg, fg=st_fg,
                 font=("Arial", 8), width=11, anchor="w").pack(side="left", padx=4)

        # Rent summary
        rent = self._rent_text(prop)
        tk.Label(row, text=rent, bg=row_bg, fg="#ccc",
                 font=("Arial", 8), width=9, anchor="w").pack(side="left", padx=4)

        # Mortgage value
        if prop.mortgaged:
            mv_txt = f"Lift: ${prop.unmortgage_cost:,}"
        else:
            mv_txt = f"${prop.mortgage_value:,}"
        tk.Label(row, text=mv_txt, bg=row_bg, fg="#aaa",
                 font=("Arial", 8), width=10, anchor="w").pack(side="left", padx=4)

        # Action buttons (human players only)
        if is_human:
            btn_f = tk.Frame(row, bg=row_bg)
            btn_f.pack(side="left", padx=6)
            self._action_buttons(btn_f, prop, player, row_bg)

    def _rent_text(self, prop):
        if prop.mortgaged:
            return "—"
        if prop.type == "railroad":
            return "$25–200"
        if prop.type == "utility":
            return "4x / 10x"
        if prop.type == "property" and prop.rent_table:
            h = prop.houses
            if h == 5:
                return f"${prop.rent_table[6]:,}"
            elif h > 0:
                return f"${prop.rent_table[h + 1]:,}"
            else:
                return f"${prop.rent_table[0]:,}"
        return "—"

    def _action_buttons(self, parent, prop, player, row_bg):
        # Mortgage / Unmortgage
        if not prop.mortgaged:
            ok = _can_mortgage(prop, self.engine)
            tk.Button(parent, text="Mortgage",
                      command=lambda p=prop: self._do_mortgage(p),
                      state="normal" if ok else "disabled",
                      bg="#c0392b" if ok else "#444", fg="white",
                      font=("Arial", 7), relief="flat",
                      padx=5, pady=2,
                      cursor="hand2" if ok else "arrow").pack(side="left", padx=2)
        else:
            ok = _can_unmortgage(prop)
            tk.Button(parent, text=f"Unmortgage (${prop.unmortgage_cost:,})",
                      command=lambda p=prop: self._do_unmortgage(p),
                      state="normal" if ok else "disabled",
                      bg="#27AE60" if ok else "#444", fg="white",
                      font=("Arial", 7), relief="flat",
                      padx=5, pady=2,
                      cursor="hand2" if ok else "arrow").pack(side="left", padx=2)

        # Buy House / Hotel (properties only, not mortgaged)
        if prop.type == "property" and not prop.mortgaged and prop.houses < 5:
            ok = _can_buy_house(prop, self.engine)
            label = (f"+Hotel (${prop.house_cost:,})"
                     if prop.houses == 4
                     else f"+House (${prop.house_cost:,})")
            tk.Button(parent, text=label,
                      command=lambda p=prop: self._do_buy_house(p),
                      state="normal" if ok else "disabled",
                      bg="#2980B9" if ok else "#444", fg="white",
                      font=("Arial", 7), relief="flat",
                      padx=5, pady=2,
                      cursor="hand2" if ok else "arrow").pack(side="left", padx=2)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _do_mortgage(self, prop):
        player = prop.owner
        prop.mortgaged = True
        player.receive(prop.mortgage_value)
        self.engine._log(
            f"  {player.name} mortgaged {prop.name} for ${prop.mortgage_value:,} "
            f"(Property Manager).")
        self._refresh()

    def _do_unmortgage(self, prop):
        player = prop.owner
        cost = prop.unmortgage_cost
        if player.money < cost:
            messagebox.showwarning("Insufficient Cash",
                f"You need ${cost:,} but only have ${player.money:,}.",
                parent=self)
            return
        player.pay(cost)
        prop.mortgaged = False
        self.engine._log(
            f"  {player.name} unmortgaged {prop.name} for ${cost:,} "
            f"(Property Manager).")
        self._refresh()

    def _do_buy_house(self, prop):
        player = prop.owner
        cost = prop.house_cost
        if player.money < cost:
            messagebox.showwarning("Insufficient Cash",
                f"You need ${cost:,} but only have ${player.money:,}.",
                parent=self)
            return
        player.pay(cost)
        prop.houses += 1
        label = "hotel" if prop.houses == 5 else f"{prop.houses} house(s)"
        self.engine._log(
            f"  {player.name} built on {prop.name} ({label}) for ${cost:,} "
            f"(Property Manager).")
        self._refresh()

    def _refresh(self):
        current = self.notebook.index(self.notebook.select()) if self.notebook.tabs() else 0
        self._populate_tabs()
        try:
            self.notebook.select(min(current, len(self.notebook.tabs()) - 1))
        except Exception:
            pass
        if self.refresh_callback:
            self.refresh_callback()
