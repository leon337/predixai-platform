# PredixAI BR — Estado Oficial do Projeto

## Projeto

PredixAI Platform

Primeiro produto: PredixAI Trader.

## Fase atual

Fase 2 — Vision.

A Fase 0 foi concluída, a Fase 1 foi criada e validada, e a base atual já possui Perception Engine foundation, Capture Engine foundation, captura manual e primeira execução local validada no Windows 10 do ambiente do Codex.

## Último PTP aprovado

PTP-009 — Validação Real no Windows 10 do Leo.

## Próximo PTP pendente

PTP-010 — Registrar o resultado da validação real no Windows 10 do Leo.

## Status geral

V1 congelada.

A plataforma executa localmente no Windows 10 do ambiente do Codex, inicializa Core, Perception e Capture Engine, e realiza captura manual em PNG quando solicitada por linha de comando.

A validação no computador Windows 10 do Leo ainda está pendente.

## Ambiente principal atual

Windows 10.

Python validado: 3.12.10.

Windows 10 no ambiente do Codex: validado.

Windows 10 do Leo: pendente de validação.

Linux Mint será validado depois da validação real no Windows 10 do Leo.

## Regra de auditoria

Nenhum PTP é aprovado sem commit, push para `origin/main` e auditoria posterior.

Toda mudança relevante deve atualizar:

- `CHANGELOG.md`
- `predixai_context.json`
- documentos oficiais relacionados

## Resumo do estado atual

- A arquitetura oficial da V1 está congelada.
- A V1 opera em modo Observador.
- A IA é analista, não operadora.
- A V1 não executa cliques, ordens ou automação.
- A estratégia única da V1 é Rebote Triplo.
- O mercado inicial é Fixed Time.
- O Core inicializa configuração, módulos, logs e eventos.
- O Perception Engine identifica ambiente de tela e lista janelas, sem OCR e sem leitura visual.
- O Capture Engine possui sessão, storage, validação e captura manual em PNG.
- A primeira execução local no Windows 10 do ambiente do Codex foi validada.
- A validação real no computador Windows 10 do Leo está pendente.
- O guia para Leo executar a validação real está em `docs/setup/Leo_Windows10_Validation.md`.
- A próxima validação técnica planejada é registrar o resultado da execução real no Windows 10 do Leo.
