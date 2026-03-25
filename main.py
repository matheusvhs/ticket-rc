import math
import random
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

# --- Defaults ---
DEFAULT_TICKETS = 20
DEFAULT_BUYERS = 30
DEFAULT_THREADS = 4
DEFAULT_DELAY_MS = 10

# --- Visual ---
CANVAS_H = 560  # altura fixa do canvas (scroll para o resto)

COLOR_UNSOLD   = "#9E9E9E"
COLOR_SOLD_OK  = "#4CAF50"
COLOR_OVERSOLD = "#F44336"
COLOR_TEXT     = "#FFFFFF"


def _grid_params(n: int) -> tuple[int, int, int]:
    """Retorna (colunas, raio, padding) para n ingressos."""
    if n <= 100:
        return 10, 18, 10
    if n <= 300:
        return 15, 12,  6
    if n <= 500:
        return 20,  9,  5
    if n <= 1000:
        return 25,  6,  4
    if n <= 2000:
        return 40,  5,  3
    return 50, 4, 2


class TicketApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Race Condition — Venda de Ingressos")
        self.resizable(True, True)

        self.num_tickets = tk.IntVar(value=DEFAULT_TICKETS)
        self.num_buyers = tk.IntVar(value=DEFAULT_BUYERS)
        self.num_threads = tk.IntVar(value=DEFAULT_THREADS)
        self.delay_ms = tk.IntVar(value=DEFAULT_DELAY_MS)

        self.stat_corretos = tk.StringVar(value="0")
        self.stat_duplos = tk.StringVar(value="0")
        self.stat_restantes = tk.StringVar(value=str(DEFAULT_TICKETS))
        self.stat_total = tk.StringVar(value="0")

        self.canvas_ids: list[int] = []
        self.running = False
        self.btn_simulate: ttk.Button | None = None

        self._build_layout()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_config_panel(left)
        self._build_stats_panel(left)
        self._build_ticket_grid(right)

    def _build_config_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Configuração", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10))

        rows = [
            ("Ingressos:", self.num_tickets, 1, 5000),
            ("Compradores:", self.num_buyers, 1, 5000),
            ("Threads:", self.num_threads, 1, 500),
            ("Delay (ms):", self.delay_ms, 0, 5000),
        ]
        for r, (label, var, lo, hi) in enumerate(rows):
            ttk.Label(frame, text=label).grid(row=r, column=0, sticky=tk.W, pady=2)
            ttk.Spinbox(
                frame, textvariable=var, from_=lo, to=hi, width=7
            ).grid(row=r, column=1, sticky=tk.E, pady=2, padx=(6, 0))

        self.btn_simulate = ttk.Button(
            frame, text="SIMULAR", command=self.on_simulate
        )
        self.btn_simulate.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=(10, 2))

        ttk.Button(frame, text="RESET", command=self.on_reset).grid(
            row=5, column=0, columnspan=2, sticky=tk.EW, pady=2
        )

    def _build_stats_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Resultados", padding=10)
        frame.pack(fill=tk.X)

        stats = [
            ("Corretos:", self.stat_corretos, COLOR_SOLD_OK),
            ("Duplos (race!):", self.stat_duplos, COLOR_OVERSOLD),
            ("Restantes:", self.stat_restantes, COLOR_UNSOLD),
            ("Total ops:", self.stat_total, "#90CAF9"),
        ]
        for r, (label, var, color) in enumerate(stats):
            dot = tk.Canvas(frame, width=14, height=14, highlightthickness=0)
            dot.create_oval(2, 2, 13, 13, fill=color, outline="")
            dot.grid(row=r, column=0, padx=(0, 4))
            ttk.Label(frame, text=label).grid(row=r, column=1, sticky=tk.W, pady=1)
            ttk.Label(frame, textvariable=var, width=5, anchor=tk.E).grid(
                row=r, column=2, sticky=tk.E
            )

    def _build_ticket_grid(self, parent):
        frame = ttk.LabelFrame(parent, text="Ingressos", padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        vbar = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        hbar = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)

        self.canvas = tk.Canvas(
            frame,
            background="#2B2B2B",
            highlightthickness=0,
            height=CANVAS_H,
            yscrollcommand=vbar.set,
            xscrollcommand=hbar.set,
        )
        vbar.config(command=self.canvas.yview)
        hbar.config(command=self.canvas.xview)

        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        vbar.pack(side=tk.RIGHT,  fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self.canvas.bind("<Button-4>",   lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>",   lambda e: self.canvas.yview_scroll( 1, "units"))

        self._draw_tickets()

    # ------------------------------------------------------------------
    # Ticket grid drawing
    # ------------------------------------------------------------------

    def _draw_tickets(self):
        self.canvas.delete("all")
        self.canvas_ids.clear()

        n = self.num_tickets.get()
        cols, r, pad = _grid_params(n)
        cell = 2 * r + pad
        rows = math.ceil(n / cols)
        grid_w = cols * cell + pad
        grid_h = rows * cell + pad

        self.canvas.config(scrollregion=(0, 0, grid_w, grid_h))

        show_numbers = r >= 8

        for i in range(n):
            col = i % cols
            row = i // cols
            cx = pad + col * cell + r
            cy = pad + row * cell + r
            oid = self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=COLOR_UNSOLD, outline="#444444",
            )
            if show_numbers:
                self.canvas.create_text(
                    cx, cy, text=str(i + 1), fill=COLOR_TEXT,
                    font=("Helvetica", max(6, r - 4)),
                )
            self.canvas_ids.append(oid)

        self.stat_restantes.set(str(n))
        self.stat_corretos.set("0")
        self.stat_duplos.set("0")
        self.stat_total.set("0")

    def _redraw_ticket(self, i: int, color: str):
        self.canvas.itemconfig(self.canvas_ids[i], fill=color)

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def on_simulate(self):
        if self.running:
            return
        try:
            n = self.num_tickets.get()
            b = self.num_buyers.get()
            t = self.num_threads.get()
            d = self.delay_ms.get()
        except tk.TclError:
            messagebox.showerror("Erro", "Valores inválidos nos campos de configuração.")
            return

        if n < 1 or b < 1 or t < 1:
            messagebox.showerror("Erro", "Ingressos, Compradores e Threads devem ser pelo menos 1.")
            return

        self.running = True
        self.btn_simulate.config(state="disabled")
        self._draw_tickets()

        threading.Thread(
            target=self._run_simulation,
            args=(n, b, t, d),
            daemon=True,
        ).start()

    def on_reset(self):
        if self.running:
            return
        self.num_tickets.set(DEFAULT_TICKETS)
        self.num_buyers.set(DEFAULT_BUYERS)
        self.num_threads.set(DEFAULT_THREADS)
        self.delay_ms.set(DEFAULT_DELAY_MS)
        self._draw_tickets()

    # ------------------------------------------------------------------
    # Simulation — runs in background thread, never touches tk widgets
    # ------------------------------------------------------------------

    def _run_simulation(self, n: int, b: int, t: int, d: int):
        tickets = [0] * n
        delay_s = d / 1000.0

        # Pré-atribui assentos: round-robin garante que cada ingresso receba
        # ceil(b/n) compradores. Ex: 30 compradores, 20 ingressos →
        # ingressos 0-9 recebem 2 compradores cada, 10-19 recebem 1.
        assigned = list(range(b))
        random.shuffle(assigned)  # embaralha para distribuição aleatória entre threads
        assigned_seats = [k % n for k in assigned]

        # Distribui compradores entre as threads
        base, extra = divmod(b, t)
        buyers_per_thread = [base + (1 if i < extra else 0) for i in range(t)]

        threads = []
        offset = 0
        for count in buyers_per_thread:
            seats = assigned_seats[offset:offset + count]
            offset += count
            thread = threading.Thread(
                target=self._worker_thread,
                args=(tickets, delay_s, seats),
                daemon=True,
            )
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        self.after(0, self._finish_simulation, tickets)

    def _worker_thread(self, tickets: list[int], delay_s: float, seats: list[int]):
        # Uma thread processa seus compradores sequencialmente,
        # cada um indo direto ao assento pré-atribuído
        for seat in seats:
            self._buy_once(tickets, delay_s, seat)

    def _buy_once(self, tickets: list[int], delay_s: float, seat: int):
        # Comprador vai direto ao assento designado
        # → vários compradores no mesmo assento = race condition garantida
        if tickets[seat] == 0:        # CHECK — sem proteção
            time.sleep(delay_s)       # libera GIL → janela para race condition
            tickets[seat] += 1        # ACT   — sem proteção
            color = COLOR_SOLD_OK if tickets[seat] == 1 else COLOR_OVERSOLD
            self.after(0, self._redraw_ticket, seat, color)

    # ------------------------------------------------------------------
    # Result rendering — safe: called on main thread via after()
    # ------------------------------------------------------------------

    def _finish_simulation(self, tickets: list[int]):
        corretos = 0
        duplos = 0
        restantes = 0

        for i, count in enumerate(tickets):
            if count == 0:
                self._redraw_ticket(i, COLOR_UNSOLD)
                restantes += 1
            elif count == 1:
                self._redraw_ticket(i, COLOR_SOLD_OK)
                corretos += 1
            else:
                self._redraw_ticket(i, COLOR_OVERSOLD)
                duplos += 1

        self.stat_corretos.set(str(corretos))
        self.stat_duplos.set(str(duplos))
        self.stat_restantes.set(str(restantes))
        self.stat_total.set(str(sum(tickets)))

        self.running = False
        self.btn_simulate.config(state="normal")


if __name__ == "__main__":
    TicketApp().mainloop()
