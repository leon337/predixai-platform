# CHAT_CONTEXT

Todo novo chat da PredixAI BR deve consultar este arquivo antes de responder sobre estado do projeto, Milestone, PTP, arquitetura ou próximo passo.

## Repositório oficial

https://github.com/leon337/predixai-platform

## Visão geral

PredixAI BR.
Primeiro produto: PredixAI Trader.
V1 em modo Observador.
Sem cliques, sem ordens, sem automação operacional, sem interação com corretora.
Estratégia V1: Rebote Triplo.
Mercado inicial: Fixed Time.
Broker inicial: Olymp Trade.

## Histórico resumido das Milestones

Milestones 001 a 014: fundações de arquitetura, OCR, visão, semântica, mercado, padrões, inteligência e readiness estratégico.
Milestone 015: Live Market Validation Foundation.
Milestone 016: Live Candle Analyzer.
Milestone 017: Dashboard Visual Inicial da PredixAI BR, em andamento.

## Estado atual

Última Milestone oficialmente concluída: Milestone 016.
Milestone atual em andamento: Milestone 017.
Foco da Milestone 017: transformar a PredixAI de aplicação de terminal em aplicação visual com dashboard, estado runtime, histórico de preço, gráfico e loop de leitura observadora.

## PTPs concluídas na Milestone 017

- PTP-017A: criou dashboard visual inicial.
- PTP-017B: conectou dashboard com última leitura real do live-once.
- PTP-017C: criou estado runtime oficial em `data/runtime/last_live_reading.json`.
- PTP-017D: criou histórico de preço, gráfico e estatísticas de mínima, máxima, média e amplitude.
- PTP-017E: criou comando `--live-loop` para múltiplas leituras observadoras.

## Último commit conhecido

`ea6539e` - Add live reading loop command

## Comandos validados

- `python -m predixai.main --live-calibrate`
- `python -m predixai.main --live-once`
- `python -m predixai.main --dashboard`
- `python -m predixai.main --live-loop --loop-count 3 --loop-interval 5`

## Estado funcional atual

A PredixAI lê a Olymp Trade em modo observador, salva última leitura, grava histórico de preço, exibe dashboard visual, mostra gráfico, estatísticas e suporta loop de leitura.

## Próximo foco recomendado

Antes da PTP-017F visual, resolver governança de continuidade entre chats e garantir que o GitHub seja fonte oficial de verdade.
Depois disso, seguir para melhorias visuais do dashboard ou refinamento do loop.

## Regras críticas

Não operar.
Não clicar.
Não automatizar corretora.
Não prometer lucro.
Não criar previsão ainda.
Agora o foco é memória, histórico, auditoria e visualização.

## Instrução para novos chats

Todo novo chat da PredixAI BR deve primeiro consultar o repositório oficial no GitHub e ler `CHAT_CONTEXT.md`, `PROJECT_STATE.md` e `predixai_context.json` antes de responder sobre Milestone, PTP, arquitetura, estado atual ou próximo passo.
