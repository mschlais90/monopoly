import tkinter as tk
from tkinter import ttk, messagebox
from game.constants import COLOR_HEX
from game.trade import TradeProposal, trade_balance


class TradeDialog(tk.Toplevel):
    """Modal trade editor. Allows any player to propose a trade with any other player.
    If recipient is AI the trade is auto-evaluated; if Human an Accept/Decline prompt appears."""

    def __init__(self, parent, engine, proposer=None):
        super().__init__(parent)
        self.engine = engine
        self.result = None  # set to TradeProposal if executed
        self.title("Trade Proposal")
        self.grab_set()
        self.resizable(False, False)
        self.configure(bg="#1a1a2e")

        active = engine.active_players
        if not active:
            self.destroy()
            return

        self._proposer_var = tk.StringVar(
            value=(proposer.name if proposer else active[0].name))
        self._recipient_var = tk.StringVar(
            value=(active[1].name if len(active) > 1 else active[0].name))

        # Track selected properties and cash for each side
        self._off_vars = {}   # pos -> BooleanVar  (proposer offers)
        self._req_vars = {}   # pos -> BooleanVar  (proposer requests)
        self._off_cash = tk.StringVar(value="0")
        self._req_cash = tk.StringVar(value="0")

        self._build()
        self._refresh_lists()

        # Centre on parent
        self.update_idletasks()
        pw = parent.winfo_rootx() + parent.winfo_width() // 2
        ph = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{pw - self.winfo_width()//2}+{ph - self.winfo_height()//2}")

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        # Title
        tk.Label(self, text="TRADE PROPOSAL", font=("Georgia", 14, "bold italic"),
                 fg="#FFD700", bg="#1a1a2e").pack(pady=(10, 4))

        players = [p.name for p in self.engine.active_players]

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(padx=12, pady=4, fill="both", expand=True)

        # ── Left: Proposer ──
        left = tk.LabelFrame(main, text=" OFFERING ", bg="#16213e", fg="#e0e0e0",
                              font=("Arial", 10, "bold"), padx=8, pady=6)
        left.grid(row=0, column=0, padx=(0, 6), sticky="nsew")

        tk.Label(left, text="Proposer:", bg="#16213e", fg="#aaa",
                 font=("Arial", 9)).pack(anchor="w")
        self._prop_cb = ttk.Combobox(left, textvariable=self._proposer_var,
                                      values=players, state="readonly", width=16)
        self._prop_cb.pack(anchor="w", pady=(0, 6))
        self._prop_cb.bind("<<ComboboxSelected>>", lambda _: self._refresh_lists())

        tk.Label(left, text="Properties to offer (no houses):",
                 bg="#16213e", fg="#ccc", font=("Arial", 8)).pack(anchor="w")
        self._off_frame = self._scrollable_check_frame(left)
        self._off_frame.pack(fill="both", expand=True)

        tk.Label(left, text="Cash to include:", bg="#16213e", fg="#ccc",
                 font=("Arial", 8)).pack(anchor="w", pady=(6, 0))
        cash_f = tk.Frame(left, bg="#16213e")
        cash_f.pack(anchor="w")
        tk.Label(cash_f, text="$", bg="#16213e", fg="#e0e0e0",
                 font=("Arial", 10)).pack(side="left")
        tk.Entry(cash_f, textvariable=self._off_cash, width=8,
                 bg="#0f3460", fg="white", insertbackground="white",
                 font=("Arial", 10)).pack(side="left")

        self._off_val_label = tk.Label(left, text="Est. value: —", bg="#16213e",
                                        fg="#4CAF50", font=("Arial", 8))
        self._off_val_label.pack(anchor="w", pady=(4, 0))

        # ── Right: Recipient ──
        right = tk.LabelFrame(main, text=" IN EXCHANGE FOR ", bg="#16213e", fg="#e0e0e0",
                               font=("Arial", 10, "bold"), padx=8, pady=6)
        right.grid(row=0, column=1, padx=(6, 0), sticky="nsew")

        tk.Label(right, text="Recipient:", bg="#16213e", fg="#aaa",
                 font=("Arial", 9)).pack(anchor="w")
        self._recv_cb = ttk.Combobox(right, textvariable=self._recipient_var,
                                      values=players, state="readonly", width=16)
        self._recv_cb.pack(anchor="w", pady=(0, 6))
        self._recv_cb.bind("<<ComboboxSelected>>", lambda _: self._refresh_lists())

        tk.Label(right, text="Properties to request (no houses):",
                 bg="#16213e", fg="#ccc", font=("Arial", 8)).pack(anchor="w")
        self._req_frame = self._scrollable_check_frame(right)
        self._req_frame.pack(fill="both", expand=True)

        tk.Label(right, text="Cash to include:", bg="#16213e", fg="#ccc",
                 font=("Arial", 8)).pack(anchor="w", pady=(6, 0))
        cash_f2 = tk.Frame(right, bg="#16213e")
        cash_f2.pack(anchor="w")
        tk.Label(cash_f2, text="$", bg="#16213e", fg="#e0e0e0",
                 font=("Arial", 10)).pack(side="left")
        tk.Entry(cash_f2, textvariable=self._req_cash, width=8,
                 bg="#0f3460", fg="white", insertbackground="white",
                 font=("Arial", 10)).pack(side="left")

        self._req_val_label = tk.Label(right, text="Est. value: —", bg="#16213e",
                                        fg="#FF7043", font=("Arial", 8))
        self._req_val_label.pack(anchor="w", pady=(4, 0))

        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        # ── Balance bar ──
        self._balance_label = tk.Label(self, text="", bg="#1a1a2e", fg="#e0e0e0",
                                        font=("Arial", 10, "bold"), pady=4)
        self._balance_label.pack()

        # ── Buttons ──
        btn_frame = tk.Frame(self, bg="#1a1a2e", pady=8)
        btn_frame.pack()
        tk.Button(btn_frame, text="Propose Trade", command=self._propose,
                  bg="#27AE60", fg="white", font=("Arial", 11, "bold"),
                  relief="flat", padx=20, pady=6, cursor="hand2").pack(side="left", padx=8)
        tk.Button(btn_frame, text="Cancel", command=self.destroy,
                  bg="#7f8c8d", fg="white", font=("Arial", 11),
                  relief="flat", padx=16, pady=6, cursor="hand2").pack(side="left", padx=8)

        # Update value labels whenever selections change
        self._off_cash.trace_add("write", lambda *_: self._update_balance())
        self._req_cash.trace_add("write", lambda *_: self._update_balance())

    def _scrollable_check_frame(self, parent):
        container = tk.Frame(parent, bg="#16213e")
        canvas = tk.Canvas(container, bg="#0f0f1a", highlightthickness=0,
                            width=200, height=160)
        sb = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg="#0f0f1a")
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win_id, width=canvas.winfo_width())
        inner.bind("<Configure>", _on_configure)
        container._inner = inner
        return container

    # ── Data helpers ─────────────────────────────────────────────────────────

    def _get_player(self, name):
        for p in self.engine.all_players:
            if p.name == name:
                return p
        return None

    def _refresh_lists(self):
        proposer = self._get_player(self._proposer_var.get())
        recipient = self._get_player(self._recipient_var.get())

        self._off_vars.clear()
        self._req_vars.clear()

        self._populate_list(self._off_frame._inner, proposer,
                            self._off_vars, side="offer")
        self._populate_list(self._req_frame._inner, recipient,
                            self._req_vars, side="request")
        self._update_balance()

    def _populate_list(self, frame, player, var_dict, side):
        for w in frame.winfo_children():
            w.destroy()
        if player is None or player.bankrupt:
            tk.Label(frame, text="No properties", bg="#0f0f1a",
                     fg="#666").pack(anchor="w", padx=4)
            return
        tradeable = [p for p in sorted(player.properties, key=lambda x: x.pos)
                     if p.houses == 0]
        if not tradeable:
            tk.Label(frame, text="No tradeable properties", bg="#0f0f1a",
                     fg="#666", font=("Arial", 8)).pack(anchor="w", padx=4)
            return
        for prop in tradeable:
            var = tk.BooleanVar(value=False)
            var_dict[prop.pos] = var
            color = COLOR_HEX.get(prop.color, "#aaaaaa") if prop.type == "property" else "#bbbbbb"
            row = tk.Frame(frame, bg="#0f0f1a")
            row.pack(fill="x", padx=2, pady=1)
            tk.Label(row, text="■", fg=color, bg="#0f0f1a",
                     font=("Arial", 9)).pack(side="left")
            cb = tk.Checkbutton(row, variable=var, bg="#0f0f1a", fg="#e0e0e0",
                                 activebackground="#0f0f1a", selectcolor="#0f3460",
                                 text=f"{prop.name}  ${prop.price}",
                                 font=("Arial", 8), anchor="w",
                                 command=self._update_balance)
            cb.pack(side="left", fill="x", expand=True)
            if prop.mortgaged:
                tk.Label(row, text="[M]", fg="#FF7043", bg="#0f0f1a",
                         font=("Arial", 7)).pack(side="right")

    def _selected_props(self, player, var_dict):
        bp = self.engine.board_properties
        return [bp[pos] for pos, var in var_dict.items()
                if var.get() and pos in bp]

    def _update_balance(self):
        proposer = self._get_player(self._proposer_var.get())
        recipient = self._get_player(self._recipient_var.get())
        if not proposer or not recipient or proposer == recipient:
            self._balance_label.config(text="Select two different players")
            return
        try:
            off_cash = max(0, int(self._off_cash.get() or 0))
            req_cash = max(0, int(self._req_cash.get() or 0))
        except ValueError:
            off_cash = req_cash = 0

        off_props = self._selected_props(proposer, self._off_vars)
        req_props = self._selected_props(recipient, self._req_vars)

        off_total = off_cash + sum(p.price for p in off_props)
        req_total = req_cash + sum(p.price for p in req_props)
        self._off_val_label.config(text=f"Est. value: ${off_total:,}")
        self._req_val_label.config(text=f"Est. value: ${req_total:,}")

        diff = off_total - req_total
        if abs(diff) < 20:
            txt, col = "Approximately fair", "#4CAF50"
        elif diff > 0:
            txt, col = f"{recipient.name} gains ~${diff:,}", "#4CAF50"
        else:
            txt, col = f"{proposer.name} gains ~${-diff:,}", "#FF7043"
        self._balance_label.config(text=txt, fg=col)

    # ── Propose / execute ─────────────────────────────────────────────────────

    def _propose(self):
        proposer = self._get_player(self._proposer_var.get())
        recipient = self._get_player(self._recipient_var.get())

        if not proposer or not recipient:
            messagebox.showerror("Error", "Select valid players.", parent=self)
            return
        if proposer == recipient:
            messagebox.showerror("Error", "Proposer and recipient must be different.", parent=self)
            return

        try:
            off_cash = max(0, int(self._off_cash.get() or 0))
            req_cash = max(0, int(self._req_cash.get() or 0))
        except ValueError:
            messagebox.showerror("Error", "Cash values must be whole numbers.", parent=self)
            return

        if off_cash > proposer.money:
            messagebox.showerror("Error",
                f"{proposer.name} only has ${proposer.money}.", parent=self)
            return
        if req_cash > recipient.money:
            messagebox.showerror("Error",
                f"{recipient.name} only has ${recipient.money}.", parent=self)
            return

        off_props = self._selected_props(proposer, self._off_vars)
        req_props = self._selected_props(recipient, self._req_vars)

        if not off_props and off_cash == 0 and not req_props and req_cash == 0:
            messagebox.showwarning("Empty Trade", "Add something to the trade first.", parent=self)
            return

        proposal = TradeProposal(proposer, recipient, off_props, off_cash,
                                 req_props, req_cash)

        if isinstance(recipient.strategy, __import__(
                "strategies.human", fromlist=["HumanStrategy"]).HumanStrategy):
            self._human_review(proposal)
        else:
            self._ai_review(proposal)

    def _ai_review(self, proposal):
        recipient = proposal.recipient
        accepted = recipient.strategy.evaluate_trade(recipient, proposal, self.engine)
        r_net, p_net = trade_balance(proposal, self.engine)
        if accepted:
            self.engine.execute_trade(proposal)
            self.result = proposal
            op = ", ".join(p.name for p in proposal.offered_props) or "—"
            rp = ", ".join(p.name for p in proposal.requested_props) or "—"
            messagebox.showinfo("Trade Accepted",
                f"{recipient.name} accepted the trade!\n\n"
                f"{proposal.proposer.name} gave: {op} + ${proposal.offered_cash:,}\n"
                f"{recipient.name} gave: {rp} + ${proposal.requested_cash:,}",
                parent=self)
            self.destroy()
        else:
            messagebox.showinfo("Trade Declined",
                f"{recipient.name} declined the trade.\n\n"
                f"({recipient.strategy.name} strategy requires a more favourable deal.)",
                parent=self)

    def _human_review(self, proposal):
        p, r = proposal.proposer, proposal.recipient
        op = ", ".join(pr.name for pr in proposal.offered_props) or "nothing"
        rp = ", ".join(pr.name for pr in proposal.requested_props) or "nothing"
        r_net, _ = trade_balance(proposal, self.engine)
        fair = "gain" if r_net >= 0 else "lose"
        diff = abs(int(r_net))
        msg = (f"{p.name} proposes:\n\n"
               f"  They give you: {op}  +  ${proposal.offered_cash:,}\n"
               f"  You give them: {rp}  +  ${proposal.requested_cash:,}\n\n"
               f"You would {fair} approximately ${diff:,} in strategic value.")
        accepted = messagebox.askyesno("Incoming Trade Offer", msg, parent=self)
        if accepted:
            self.engine.execute_trade(proposal)
            self.result = proposal
            self.destroy()
