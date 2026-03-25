# Race Condition — Venda de Ingressos

PoC desenvolvida para a disciplina de **Sistemas Operacionais**. O programa demonstra visualmente o problema de *race condition* (condição de corrida) usando o cenário de venda de ingressos com múltiplas threads concorrentes.

---

## Como executar

```bash
.venv/bin/python3 main.py
```

Requisitos: Python 3.14+ com tkinter (incluso na instalação padrão).

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

---

## Arquitetura do programa

```
on_simulate()
    └── thread de orquestração
            └── _run_simulation()
                    ├── pré-atribui assentos aos compradores
                    ├── cria N threads de trabalho
                    │       └── _worker_thread()
                    │               └── _buy_once()  ← lógica com race condition
                    ├── aguarda todas as threads (.join())
                    └── agenda atualização final da UI (after())
```

A interface gráfica (tkinter) roda inteiramente na thread principal. As threads de simulação **nunca tocam diretamente nos widgets** — toda atualização visual é agendada via `self.after(0, ...)`, que coloca a chamada na fila de eventos da thread principal.

---

## Uso de threads

### Modelo de thread pool

Ao clicar em **SIMULAR**, o programa cria exatamente `T` threads (onde `T` é o valor configurado). Os `B` compradores são distribuídos entre essas threads usando divisão inteira:

```
base  = B // T          # compradores base por thread
extra = B %  T          # sobra distribuída nas primeiras threads

Exemplo: B=30, T=4 → [8, 8, 7, 7]
```

Cada thread processa seus compradores **sequencialmente**, mas as `T` threads rodam **em paralelo** entre si. É essa execução paralela que cria a janela para race conditions.

### Por que race conditions ocorrem mesmo com o GIL do Python?

O CPython possui o **GIL (Global Interpreter Lock)**, que garante que apenas uma thread execute bytecode Python por vez. Mesmo assim, race conditions ocorrem porque:

1. `time.sleep()` é uma chamada de sistema bloqueante que **libera o GIL explicitamente**
2. Durante o sleep, o SO pode agendar outra thread para executar
3. Múltiplas threads podem estar no "meio" da operação de compra ao mesmo tempo

O efeito prático é demonstrado abaixo.

---

## A decisão de venda: padrão CHECK-SLEEP-ACT

O núcleo da race condition está em `_buy_once()`:

```python
def _buy_once(self, tickets, delay_s, seat):
    if tickets[seat] == 0:     # (1) CHECK — sem proteção
        time.sleep(delay_s)    # (2) SLEEP — libera o GIL
        tickets[seat] += 1     # (3) ACT   — sem proteção
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

O problema é o intervalo entre o CHECK e o ACT. Sem um mecanismo de exclusão mútua (mutex), nada impede que outra thread leia o mesmo valor antes que a primeira finalize a escrita.

---

## Pré-atribuição de assentos

Para maximizar as races visíveis, cada comprador recebe um assento fixo **antes** da simulação começar, usando round-robin:

```
comprador k  →  assento  k % n
```

Com `B=30` compradores e `n=20` ingressos:

```
Ingressos 0–9:  recebem 2 compradores cada  (garantia de colisão)
Ingressos 10–19: recebem 1 comprador cada
```

A lista de atribuições é então embaralhada aleatoriamente antes de ser dividida entre as threads. Isso garante que compradores do mesmo assento possam cair em threads diferentes, criando a concorrência necessária para a race condition.

A proporção `compradores / ingressos` controla a intensidade das races:

| Proporção | Comportamento esperado |
|-----------|----------------------|
| 1:1 | Poucas ou nenhuma race |
| 2:1 | Races moderadas (~30–50% dos ingressos) |
| 3:1 | Races frequentes (~50–70% dos ingressos) |
| 5:1+ | Quase todos os ingressos ficam vermelhos |

---

## O que NÃO existe neste programa (intencionalmente)

Esta PoC **não usa nenhum mecanismo de sincronização**:

- Sem `threading.Lock` / `threading.RLock`
- Sem `threading.Semaphore`
- Sem `threading.Barrier`
- Sem `queue.Queue`
- Sem `threading.Event`

A ausência desses mecanismos é o que permite que as races ocorram. Em um sistema real, a solução seria proteger o bloco CHECK-ACT com um mutex:

```python
# Versão correta (NÃO usada nesta PoC)
with lock:
    if tickets[seat] == 0:
        tickets[seat] += 1
```

Com o mutex, apenas uma thread executa o bloco por vez, eliminando completamente as races — e nenhum ingresso ficaria vermelho.
