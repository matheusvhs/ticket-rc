# --- Defaults ---
DEFAULT_TICKETS = 20
DEFAULT_BUYERS  = 30
DEFAULT_THREADS = 4
DEFAULT_DELAY_MS = 10

# --- Visual ---
CANVAS_H = 560  # altura fixa do canvas (scroll para o resto)

COLOR_UNSOLD   = "#9E9E9E"
COLOR_SOLD_OK  = "#4CAF50"
COLOR_OVERSOLD = "#F44336"
COLOR_TEXT     = "#FFFFFF"


def grid_params(n: int) -> tuple[int, int, int]:
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
