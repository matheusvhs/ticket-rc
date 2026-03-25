# Race Condition — Venda de Ingressos

PoC desenvolvida para a disciplina de **Sistemas Operacionais**. O programa demonstra visualmente o problema de *race condition* (condição de corrida) usando o cenário de venda de ingressos com múltiplas threads concorrentes, **sem nenhum mecanismo de sincronização**.

---

## Como executar

```bash
.venv/bin/python3 main.py
```

Requisitos: Python 3.14+ com tkinter (incluso na instalação padrão).

---

## Estrutura do projeto

```
ticket-rc/
├── main.py        # entrada — instancia e inicia o app
├── app.py         # TicketApp: interface tkinter e polling
├── simulation.py  # Simulation: threads workers e array tickets[]
└── config.py      # constantes, cores e grid_params()
```

### `config.py`

Centraliza todas as constantes do projeto:

- Valores padrão dos campos (`DEFAULT_TICKETS`, `DEFAULT_BUYERS`, `DEFAULT_THREADS`, `DEFAULT_DELAY_MS`)
- Cores da grade (`COLOR_UNSOLD`, `COLOR_SOLD_OK`, `COLOR_OVERSOLD`, `COLOR_TEXT`)
- Função `grid_params(n)` — retorna `(colunas, raio, padding)` de acordo com a quantidade de ingressos, ajustando o tamanho das bolinhas automaticamente

| Ingressos | Colunas | Raio | Padding |
|-----------|---------|------|---------|
| ≤ 100 | 10 | 18px | 10px |
| ≤ 300 | 15 | 12px | 6px |
| ≤ 500 | 20 | 9px | 5px |
| ≤ 1000 | 25 | 6px | 4px |
| ≤ 2000 | 40 | 5px | 3px |
| > 2000 | 50 | 4px | 2px |

### `simulation.py`

Classe `Simulation` — contém toda a lógica de concorrência, isolada da interface.

Responsabilidades:
- Recebe `n` (ingressos), `b` (compradores), `t` (threads) e `delay_s`
- Pré-atribui assentos aos compradores via round-robin
- Cria e mantém as threads workers
- Expõe `tickets[]` (array compartilhado) e `is_running()` para o polling da UI

### `app.py`

Classe `TicketApp(tk.Tk)` — constrói e gerencia a interface gráfica.

Responsabilidades:
- Painéis de configuração e resultados
- Grade visual de ingressos com scroll
- Instancia `Simulation` e inicia as threads
- Polling a cada 50ms lendo `sim.tickets[]` diretamente para atualizar a grade

### `main.py`

Ponto de entrada — 3 linhas:

```python
from app import TicketApp

if __name__ == "__main__":
    TicketApp().mainloop()
```

---

## Interface

A janela é dividida em dois painéis:

**Painel esquerdo — Configuração e Resultados**

| Campo | Descrição | Padrão |
|-------|-----------|--------|
| Ingressos | Total de assentos disponíveis | 20 |
| Compradores | Total de pessoas tentando comprar | 30 |
| Threads | Número de threads do SO a criar | 4 |
| Delay (ms) | Atraso artificial entre CHECK e ACT | 10 |

**Painel direito — Grade de ingressos**

Cada bolinha representa um ingresso. A cor muda em tempo real conforme os compradores atuam:

| Cor | Significado |
|-----|-------------|
| Cinza | Ingresso ainda não vendido |
| Verde | Vendido exatamente uma vez (correto) |
| Vermelho | Vendido mais de uma vez — *race condition* detectada |

A grade suporta até 5000 ingressos. O tamanho das bolinhas se ajusta automaticamente e a grade possui scroll vertical e horizontal.

---

## Arquitetura e fluxo de execução

```
main.py
└── TicketApp().mainloop()          [thread principal — event loop do tkinter]
        │
        └── on_simulate()
                ├── Simulation(n, b, t, delay_s)
                │       ├── pré-atribui assentos (round-robin)
                │       └── cria T threads workers
                │
                ├── sim.start()     → inicia as T threads
                │       └── _worker()  [thread de trabalho — sem sincronismo]
                │               └── CHECK → SLEEP → ACT em tickets[]
                │
                └── after(50, _poll, sim)
                        └── _poll()  [thread principal — a cada 50ms]
                                ├── lê sim.tickets[] diretamente
                                ├── atualiza cores e estatísticas
                                └── repete até sim.is_running() == False
```

As threads workers **não se comunicam com a interface**. Elas apenas escrevem em `tickets[]` e terminam. A thread principal observa esse array via polling periódico, sem nenhuma coordenação com as workers.

---

## Uso de threads

### Thread pool

Ao clicar em **SIMULAR**, a classe `Simulation` cria exatamente `T` threads. Os `B` compradores são distribuídos entre elas usando divisão inteira:

```
base  = B // T
extra = B %  T

Exemplo: B=30, T=4 → threads recebem [8, 8, 7, 7] compradores cada
```

Cada thread processa seus compradores **sequencialmente**, mas as `T` threads rodam **em paralelo** entre si. É essa execução paralela que cria a janela para race conditions.

### Por que race conditions ocorrem mesmo com o GIL do Python?

O CPython possui o **GIL (Global Interpreter Lock)**, que garante que apenas uma thread execute bytecode Python por vez. Mesmo assim, race conditions ocorrem porque:

1. `time.sleep()` é uma chamada de sistema bloqueante que **libera o GIL explicitamente**
2. Durante o sleep, o SO pode escalonar outra thread para executar
3. Múltiplas threads podem estar simultaneamente no intervalo entre o CHECK e o ACT

---

## A decisão de venda: padrão CHECK-SLEEP-ACT

O núcleo da race condition está no método `_worker()` de `Simulation`:

```python
def _worker(self, delay_s: float, seats: list[int]) -> None:
    for seat in seats:
        if self.tickets[seat] == 0:     # (1) CHECK — sem proteção
            time.sleep(delay_s)         # (2) SLEEP — libera o GIL
            self.tickets[seat] += 1     # (3) ACT   — sem proteção
```

### Cenário sem race condition (1 thread)

```
Thread A:  CHECK tickets[5] == 0  → True
Thread A:  SLEEP 10ms
Thread A:  ACT   tickets[5] = 1   ✓ vendido
```

Resultado: `tickets[5] == 1` → bolinha verde.

### Cenário com race condition (2+ threads, mesmo assento)

```
Thread A:  CHECK tickets[5] == 0  → True   (vê disponível)
           ← GIL liberado pelo sleep →
Thread B:  CHECK tickets[5] == 0  → True   (também vê disponível!)
           ← GIL liberado pelo sleep →
Thread A:  ACT   tickets[5] += 1  → tickets[5] = 1
Thread B:  ACT   tickets[5] += 1  → tickets[5] = 2  ← RACE!
```

Resultado: `tickets[5] == 2` → bolinha vermelha. O ingresso foi "vendido" duas vezes.

O problema é o intervalo entre o CHECK e o ACT. Sem exclusão mútua, nada impede que outra thread leia o mesmo valor antes que a primeira finalize a escrita.

---

## Pré-atribuição de assentos

Para maximizar as races visíveis, cada comprador recebe um assento fixo antes da simulação começar, usando round-robin:

```
comprador k  →  assento  k % n
```

Com `B=30` compradores e `n=20` ingressos:

```
Ingressos 0–9:   recebem 2 compradores cada  → colisão garantida
Ingressos 10–19: recebem 1 comprador cada
```

A lista de atribuições é embaralhada aleatoriamente antes de ser dividida entre as threads, garantindo que compradores do mesmo assento possam cair em threads diferentes.

A proporção `compradores / ingressos` controla a intensidade das races:

| Proporção | Comportamento esperado |
|-----------|----------------------|
| 1:1 | Poucas ou nenhuma race |
| 2:1 | Races moderadas (~30–50% dos ingressos) |
| 3:1 | Races frequentes (~50–70% dos ingressos) |
| 5:1+ | Quase todos os ingressos ficam vermelhos |

---

## Ausência total de sincronismo

Este programa **não usa nenhum mecanismo de sincronização**:

| Primitiva | Presente? |
|-----------|:---------:|
| `threading.Lock` / `threading.RLock` | Não |
| `threading.Semaphore` | Não |
| `threading.Barrier` | Não |
| `threading.Event` | Não |
| `queue.Queue` | Não |
| `thread.join()` | Não |
| `after(0, callback)` chamado de threads workers | Não |

### Como a UI é atualizada sem sincronismo

As threads workers apenas escrevem em `tickets[]` e terminam, sem qualquer comunicação com a interface.

A thread principal usa `after(50, ...)` — chamado de dentro dela mesma — para executar `_poll()` a cada 50ms. Em cada ciclo, ela lê `sim.tickets[]` diretamente e redesenha a grade:

```python
def _poll(self, sim: Simulation):
    for i, count in enumerate(sim.tickets):
        if count == 0:
            color = COLOR_UNSOLD    # cinza
        elif count == 1:
            color = COLOR_SOLD_OK   # verde
        else:
            color = COLOR_OVERSOLD  # vermelho
        self.canvas.itemconfig(self.canvas_ids[i], fill=color)

    if sim.is_running():
        self.after(50, self._poll, sim)
    else:
        self.running = False
```

Como a leitura de `tickets[]` é feita sem coordenação com as writers, a UI pode mostrar estados intermediários — um ingresso pode aparecer verde e depois mudar para vermelho quando outra thread incrementa o mesmo slot. Isso é proposital e faz parte da demonstração.

### A solução correta (não usada nesta PoC)

Em um sistema real, a solução seria proteger o bloco CHECK-ACT com um mutex:

```python
with lock:
    if tickets[seat] == 0:
        tickets[seat] += 1
```

Com o mutex, apenas uma thread executa o bloco por vez, eliminando completamente as races — e nenhum ingresso ficaria vermelho.
