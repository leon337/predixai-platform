# PredixAI BR — Estado Oficial do Projeto

## Projeto

PredixAI Platform

Primeiro produto: PredixAI Trader.

## Fase atual

Fase 2 — Vision.

A Fase 0 foi concluída, a Fase 1 foi criada e validada, e a base atual já possui Perception Engine foundation, Capture Engine foundation, captura manual e primeira execução local validada no Windows 10.

## Último PTP aprovado

PTP-008 — Arquivos de Governança do Projeto.

## Próximo PTP pendente

PTP-009 — Preparar validação de compatibilidade no Linux Mint sem OCR, IA, estratégia, automação ou interação com corretora.

## Status geral

V1 congelada.

A plataforma executa localmente no Windows 10, inicializa Core, Perception e Capture Engine, e realiza captura manual em PNG quando solicitada por linha de comando.

## Ambiente principal atual

Windows 10.

Python validado: 3.12.10.

Linux Mint será validado depois da base Windows estar estável.

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
- A primeira execução local no Windows 10 foi validada.
- A próxima validação técnica planejada é compatibilidade no Linux Mint.
