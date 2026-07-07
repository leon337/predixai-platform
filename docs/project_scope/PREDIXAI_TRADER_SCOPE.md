# PTP-113 — Escopo Mestre do PredixAI Trader

## 1. Objetivo do produto

Criar o primeiro protótipo funcional do **PredixAI Trader** em modo **mobile-first simulado**, capaz de:

- configurar uma sessão simulada pelo celular;
- observar dados da tela da corretora aberta no notebook;
- capturar preço/ticks, ativo e payout;
- gerar sinais simulados com justificativa;
- calcular resultado simulado;
- atualizar banca simulada;
- registrar histórico;
- exibir auditoria no dashboard.

## 2. Regra principal

O PredixAI Trader deve funcionar primeiro como protótipo simulado consistente.

Até decisão futura explícita:

- não usar dinheiro real;
- não usar saldo real;
- não usar login real;
- não executar ordem real;
- não clicar em compra/venda real;
- não ativar auto-click;
- não operar conta real.

## 3. Fluxo mobile-first

### Celular

O celular é o painel operacional principal.

Deve permitir:

1. abrir `/session/setup`;
2. configurar banca simulada;
3. configurar entrada simulada;
4. configurar meta de lucro;
5. configurar recuperação;
6. iniciar sessão simulada;
7. acompanhar `/mobile`;
8. ver sinal, confiança, risco, banca, resultado e histórico.

### Notebook/Linux Mint + VS Code

O notebook é ambiente técnico.

Deve:

1. rodar servidor mobile;
2. rodar dashboard;
3. manter corretora aberta como fonte visual observada;
4. executar scripts;
5. gerar relatórios;
6. publicar no GitHub;
7. validar endpoints;
8. manter histórico técnico.

### Dashboard

O dashboard é histórico/auditoria.

Deve mostrar:

- histórico de sinais;
- métricas;
- banca simulada;
- logs;
- evidências;
- resultados;
- estado do sistema.

## 4. Escopo do primeiro protótipo funcional

### 4.1 Sessão simulada

- banca inicial;
- valor de entrada;
- meta de lucro;
- stop/limites;
- tipo de recuperação;
- limite máximo de entrada;
- contrato da sessão;
- segurança 100% simulada.

### 4.2 Gestão de recuperação

Opções planejadas:

- sem recuperação;
- mão fixa / entrada fixa;
- Soros / anti-martingale;
- 1 Martingale;
- 2 Martingales;
- SmartGale simulado.

Cada modo deve mostrar:

- próxima entrada;
- entrada máxima;
- exposição máxima;
- risco estimado;
- alerta visual.

### 4.3 Observação visual

O sistema deve capturar, quando tecnicamente estável:

- preço/ticks;
- ativo observado;
- payout;
- horário;
- estado da leitura;
- evidência do dado capturado.

### 4.4 Sinais simulados

Cada sinal deve conter:

- direção: CALL, PUT ou NEUTRO;
- confiança;
- motivo;
- estratégia usada;
- ativo;
- preço de referência;
- expiração sugerida;
- horário de abertura;
- horário de fechamento previsto.

### 4.5 Resultado simulado

Cada operação simulada deve calcular:

- WIN;
- LOSS;
- DRAW;
- entrada;
- retorno estimado;
- lucro/prejuízo;
- saldo atualizado;
- impacto na recuperação.

### 4.6 Histórico

O histórico deve registrar:

- sinais;
- resultados;
- banca;
- recuperação;
- eventos;
- falhas;
- auditorias;
- logs relevantes.

## 5. Fora do escopo agora

Não entra no primeiro protótipo funcional:

- operação real;
- integração com ordem real;
- login em corretora;
- auto-click;
- uso de saldo real;
- execução automática;
- múltiplas corretoras reais;
- estratégia avançada de produção;
- promessa de lucro;
- robô autônomo com dinheiro real;
- monetização;
- painel comercial;
- WhatsApp;
- funil de vendas;
- Instagram;
- CRM.

Esses pontos só podem ser tratados em PTP futura.

## 6. Funções bloqueadas e critérios de desbloqueio

### ⛔ Observador prático

Bloqueado até:

- `/session/setup` estar estável;
- contrato mobile estar correto;
- banca/entrada/meta/recuperação validadas;
- servidor mobile sem bug crítico.

### ⛔ Geração final de sinais

Bloqueada até:

- observador capturar preço/ticks de forma confiável;
- ativo e payout estarem disponíveis ou claramente simulados;
- estratégia mínima estar validada.

### ⛔ Resultado WIN/LOSS/DRAW

Bloqueado até:

- sinal possuir preço de abertura;
- close_time estar definido;
- preço de fechamento ser capturado ou simulado de forma controlada.

### ⛔ Dashboard final

Bloqueado até:

- mobile gerar sinais/resultados consistentes;
- histórico operacional existir;
- banca simulada estar sincronizada.

## 7. Roadmap operacional atual

```txt
✅ PTP-112 — Base arquitetural mobile-first
🟨 PTP-113 — Primeiro teste operacional mobile-first simulado
  ✅ PTP-113A — Prontidão operacional simulada
  🟨 PTP-113B — Ciclo operacional mobile-first
    🟧 PTP-113B.3.1A.5.1A.3 — Stepper BRL
       Nome curto: Stepper BRL
       Objetivo: corrigir botões +/− e limpar hooks monetários duplicados.
    ⛔ PTP-113B.3.1B — Observador prático
    ⛔ PTP-113B.3.1C — Sinal → resultado → saldo → histórico
  ⬜ PTP-113C — Dashboard/histórico
  ⬜ PTP-113D — Auditoria de consistência
  ⬜ PTP-113E — Correções
  ⬜ PTP-113F — Validação cumulativa PTP-112 + PTP-113
  ⬜ PTP-113G — Publicação integrada
```

## 8. Critério de pronto do protótipo

O primeiro protótipo funcional será considerado pronto quando:

1. sessão mobile iniciar corretamente;
2. contrato da sessão estiver consistente;
3. banca simulada aparecer no mobile;
4. recuperação estiver validada;
5. observador capturar dados práticos ou simulados controlados;
6. sinal for gerado com motivo e confiança;
7. resultado for calculado no fechamento;
8. saldo for atualizado;
9. histórico for registrado;
10. dashboard refletir auditoria;
11. relatório PASS for gerado;
12. GitHub estiver atualizado;
13. Leo validar no telefone.

## 9. Critério de sinal consistente

Um sinal só será considerado consistente quando tiver:

- dado de origem rastreável;
- estratégia identificada;
- direção clara;
- confiança calculada;
- justificativa legível;
- tempo de expiração;
- registro no histórico;
- resultado posterior auditável.

## 10. Critério de segurança

O sistema deve manter travas visíveis:

- `simulation_only = true`;
- `orders_enabled = false`;
- `real_money_enabled = false`;
- `auto_click_enabled = false`;
- `broker_login_enabled = false`;
- `credentials_allowed = false`.

Qualquer violação dessas travas bloqueia avanço.

## 11. Governança

Todo avanço deve seguir:

```txt
Debater → Aprovar plano → Script all-in-one → Executar → Validar → Registrar → Publicar → Abrir relatório
```

Todo script deve seguir:

```txt
INVESTIGAR → PLANEJAR → CONSTRUIR → VALIDAR → REGISTRAR → PUBLICAR → ENTREGAR
```

## 12. Próxima ação técnica

Antes de avançar para observador, sinais ou dashboard, resolver:

```txt
PTP-113B.3.1A.5.1A.3 — Stepper BRL
Nome curto: Stepper BRL
Objetivo: auditar e limpar hooks monetários duplicados no servidor mobile.
```
