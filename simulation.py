import random
import threading
import time


class Simulation:
    """
    Encapsula a lógica de venda de ingressos com race condition intencional.
    Sem nenhum mecanismo de sincronização — acesso direto ao array tickets[].
    """

    def __init__(self, n: int, b: int, t: int, delay_s: float):
        self.tickets: list[int] = [0] * n
        self._threads: list[threading.Thread] = []

        # Pré-atribui assentos: round-robin garante que cada ingresso receba
        # ceil(b/n) compradores. Ex: 30 compradores, 20 ingressos →
        # ingressos 0–9 recebem 2 compradores cada, 10–19 recebem 1.
        assigned = list(range(b))
        random.shuffle(assigned)
        assigned_seats = [k % n for k in assigned]

        # Distribui compradores entre as threads
        base, extra = divmod(b, t)
        buyers_per_thread = [base + (1 if i < extra else 0) for i in range(t)]

        offset = 0
        for count in buyers_per_thread:
            seats = assigned_seats[offset:offset + count]
            offset += count
            self._threads.append(threading.Thread(
                target=self._worker,
                args=(delay_s, seats),
                daemon=True,
            ))

    def start(self) -> None:
        for th in self._threads:
            th.start()

    def is_running(self) -> bool:
        return any(th.is_alive() for th in self._threads)

    def _worker(self, delay_s: float, seats: list[int]) -> None:
        for seat in seats:
            if self.tickets[seat] == 0:        # CHECK — sem proteção
                time.sleep(delay_s)            # libera GIL → janela para race condition
                self.tickets[seat] += 1        # ACT   — sem proteção
