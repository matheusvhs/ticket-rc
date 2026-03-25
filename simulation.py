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

        # Lista que armazenará os objetos Thread criados para esta simulação.
        # Cada thread representa um grupo de compradores rodando em paralelo.
        self._threads: list[threading.Thread] = []

        # Pré-atribui assentos: round-robin garante que cada ingresso receba
        # ceil(b/n) compradores. Ex: 30 compradores, 20 ingressos →
        # ingressos 0–9 recebem 2 compradores cada, 10–19 recebem 1.
        assigned = list(range(b))
        random.shuffle(assigned)
        assigned_seats = [k % n for k in assigned]

        # Divide os compradores igualmente entre as t threads.
        # Se a divisão não for exata, as primeiras threads recebem um comprador extra.
        base, extra = divmod(b, t)
        buyers_per_thread = [base + (1 if i < extra else 0) for i in range(t)]

        offset = 0
        for count in buyers_per_thread:
            seats = assigned_seats[offset:offset + count]
            offset += count

            # Cria uma thread para cada grupo de compradores.
            # - target: função que a thread executará (_worker)
            # - args: argumentos passados ao _worker (delay e lista de assentos)
            # - daemon=True: a thread é encerrada automaticamente se o programa principal fechar,
            #   evitando que threads "fantasma" fiquem rodando em segundo plano.
            self._threads.append(threading.Thread(
                target=self._worker,
                args=(delay_s, seats),
                daemon=True,
            ))

    def start(self) -> None:
        # Inicia todas as threads ao mesmo tempo.
        # A partir daqui elas rodam concorrentemente — sem ordem garantida entre si.
        for th in self._threads:
            th.start()

    def is_running(self) -> bool:
        # Verifica se ainda há alguma thread viva (em execução).
        # th.is_alive() retorna True enquanto a thread não terminou seu _worker.
        return any(th.is_alive() for th in self._threads)

    def _worker(self, delay_s: float, seats: list[int]) -> None:
        # Esta função roda dentro de cada thread, independentemente das outras.
        # Múltiplas threads executam este mesmo código ao mesmo tempo.
        for seat in seats:
            if self.tickets[seat] == 0:        # CHECK — sem proteção: outra thread pode ler
                                               # o mesmo valor "0" antes de qualquer uma escrever
                time.sleep(delay_s)            # Simula latência (ex.: consulta ao banco).
                                               # time.sleep() libera o GIL (trava interna do Python),
                                               # permitindo que outra thread entre e leia tickets[seat]
                                               # antes desta thread concluir a escrita — isso cria
                                               # a janela de tempo onde a race condition ocorre.
                self.tickets[seat] += 1        # ACT — sem proteção: se duas threads passaram pelo
                                               # CHECK acima, ambas incrementam aqui, resultando
                                               # em tickets[seat] == 2 (ingresso vendido duas vezes)
