# Explicação do Projeto — Simulador de Race Condition

## O que é o problema que ele demonstra?

Imagine uma bilheteria online. Dois compradores veem que o ingresso 7 ainda está disponível. Os dois clicam em "comprar" ao mesmo tempo. Se o sistema não tomar cuidado, os dois conseguem comprar o **mesmo** ingresso — e aí você tem dois donos do assento 7. Isso é uma **race condition** (condição de corrida): duas "corridas" acontecendo ao mesmo tempo, e o resultado depende de quem chega primeiro.

---

## O que o programa faz

Ele abre uma janela gráfica onde você pode ver isso acontecendo na prática:

- Cada **bolinha** na tela representa um ingresso
- **Cinza** = ingresso disponível
- **Verde** = vendido corretamente (só 1 comprador)
- **Vermelho** = vendido com erro! (2+ compradores compraram o mesmo ingresso — race condition!)

Você configura:
- Quantos **ingressos** existem
- Quantos **compradores** tentam comprar
- Quantas **threads** (linhas de execução paralela) rodam ao mesmo tempo
- Um **delay** (pausa artificial entre verificar e comprar, que aumenta a chance do erro acontecer)

Clica em **SIMULAR** e assiste as bolinhas ficarem verdes ou vermelhas em tempo real.

---

## Por que o erro acontece intencionalmente?

O código faz isso de propósito, sem nenhuma proteção:

```
1. Thread A verifica: "ingresso 7 está livre?" → SIM
2. Thread B verifica: "ingresso 7 está livre?" → SIM  ← ambas viram "livre"!
3. Thread A compra o ingresso 7
4. Thread B compra o ingresso 7  ← vendido duas vezes!
```

---

## Para que serve?

É uma **ferramenta educacional** — provavelmente para aulas ou apresentações sobre programação concorrente, mostrando visualmente o que acontece quando múltiplas "tarefas" acessam o mesmo recurso sem sincronização.