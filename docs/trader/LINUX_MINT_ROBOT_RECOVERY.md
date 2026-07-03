# PTP-108 — Linux Mint Robot Runtime Recovery

Data: 2026-07-03
Ambiente: Linux Mint + VS Code
Repositório: predixai-platform
Status: publicado

## Objetivo

Recuperar o ambiente operacional do PredixAI Trader no Linux Mint para permitir o retorno ao desenvolvimento e aos testes do robô em modo observador.

## Problemas identificados

1. O arquivo requirements.txt estava desatualizado.
2. Dependências reais do robô não estavam instaladas no ambiente virtual.
3. O banco SQLite ainda não existia no ambiente Linux Mint.
4. O módulo principal quebrava no Linux por importar ctypes.windll diretamente.
5. O projeto precisava registrar melhor cada alteração técnica na memória.

## Dependências validadas

- Flask
- Selenium
- Pandas
- Numpy
- OpenCV
- Pillow
- SQLite via biblioteca padrão do Python

## Banco SQLite

Banco inicializado:

data/predixai_trader.sqlite3

Status validado:

- OK=True
- EXISTS=True
- SCHEMA_VERSION=1

Tabelas principais:

- evidence_records
- indicator_snapshots
- market_candles
- market_sessions
- market_ticks
- schema_metadata
- support_resistance_zones
- triple_rebound_observations

## Correção Linux

Arquivo corrigido:

src/predixai/live/broker_window_detector.py

Problema:

ctypes.windll existe no Windows, mas não existe no Linux.

Solução:

A importação passou a ser condicional. No Linux, o detector não quebra a aplicação e retorna estado seguro informando que a detecção automática de janela via windll está disponível apenas no Windows.

## Validações já realizadas

- python -m compileall src scripts
- python -m predixai.main --help
- scripts/predixai_trader_db_status.py --init

## Decisões

1. Esta etapa será registrada como PTP-108.
2. O foco da PTP-108 é recuperar o robô no Linux Mint.
3. Login automático multi-corretora fica para etapa futura.
4. Toda alteração técnica validada deve ser documentada e versionada.
5. O GitHub passa a ser memória viva do desenvolvimento no fluxo Linux Mint + VS Code.

## Próximas etapas

1. Validar dashboard local.
2. Validar robô em modo observador.
3. Atualizar PROJECT_STATE.md, CHANGELOG.md e predixai_context.json.
4. Fazer commit e push da PTP-108.
5. Depois iniciar PTP-109 — Multi-Broker Startup and Auto Login.


## Correção pré-commit do detector de janela

Durante a auditoria pré-commit da PTP-108, foi identificado que a primeira correção Linux evitava a quebra por `ctypes.windll`, mas precisava preservar explicitamente o fluxo Windows dentro do método `detect()`.

Correção aplicada:

- Linux: retorna estado seguro sem quebrar a aplicação.
- Windows: mantém a detecção original via `ctypes.windll`.
- O método `detect()` passa a ter retorno explícito nos dois ambientes.

Status: correção aplicada antes do commit da PTP-108.


## Publicação

Status: publicado
Publicado em: 2026-07-03T12:49:17-03:00

Validações finais:
- python -m compileall src scripts
- python -m predixai.main --help
- python scripts/predixai_trader_db_status.py
- git diff --check

Observação:
O banco `data/predixai_trader.sqlite3` permanece como memória operacional local e não foi incluído como código-fonte.
