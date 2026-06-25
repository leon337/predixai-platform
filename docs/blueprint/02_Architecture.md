# PredixAI BR — Arquitetura Oficial v1.0

## 1. Visão geral

A PredixAI Platform é composta por módulos independentes conectados ao PredixAI Core.

## 2. Estrutura principal sugerida

```text
predixai-platform/
├── docs/
│   └── blueprint/
├── src/
│   └── predixai/
│       ├── core/
│       ├── security/
│       ├── vision/
│       ├── auditor/
│       ├── strategy/
│       ├── ai_provider/
│       ├── dashboard/
│       ├── broker_adapter/
│       └── trader/
├── tests/
├── data/
├── logs/
├── captures/
├── config/
├── predixai_context.json
├── requirements.txt
├── README.md
├── ROADMAP.md
├── CHANGELOG.md
└── .gitignore
```

## 3. PredixAI Core

Responsável por:

- inicialização do sistema;
- carregamento de configurações;
- comunicação entre módulos;
- registro de módulos ativos;
- controle de versão;
- gerenciamento de eventos.

## 4. PredixAI Security

Responsável por:

- licença local na V1;
- validação básica de máquina;
- proteção de chaves;
- integridade de arquivos;
- preparação para validação em nuvem futura.

## 5. PredixAI Vision

Responsável por:

- capturar tela;
- localizar janela da corretora;
- identificar gráfico;
- identificar saldo;
- identificar ativo;
- identificar payout;
- identificar tempo;
- identificar valor de entrada;
- identificar RSI 15, RSI 30 e RSI 60.

## 6. PredixAI Auditor

Responsável por registrar tudo:

- data;
- hora;
- screenshot;
- ativo;
- saldo;
- payout;
- tempo;
- RSI;
- sinal;
- motivo;
- status da leitura.

## 7. PredixAI Strategy

Responsável por executar a lógica da estratégia ativa.

Na V1 terá apenas:

- Rebote Triplo

## 8. PredixAI AI Provider

Responsável por conectar o sistema a provedores de IA.

Na V1:

- Google Gemini

No futuro:

- DeepSeek
- OpenAI
- OpenRouter
- Ollama
- modelos locais

## 9. PredixAI Dashboard

Interface visual do usuário.

Na V1 deve mostrar:

- status do robô;
- última captura;
- dados detectados;
- RSI detectados;
- sinal sugerido;
- motivo do sinal;
- logs recentes.

## 10. PredixAI Broker Adapter

Camada que representa a corretora.

Na V1:

- Olymp Trade / Fixed Time

No futuro:

- Quotex
- IQ Option
- Exnova
- outras plataformas

## 11. PredixAI Trader

Produto inicial que une:

- Vision
- Strategy
- Auditor
- Dashboard
- AI Provider

## 12. Regra arquitetural

Nenhum módulo deve acessar diretamente outro módulo de forma desorganizada.

O Core coordena a comunicação.
