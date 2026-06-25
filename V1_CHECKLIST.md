# PredixAI Trader V1 — Checklist Oficial

## Objetivo da V1

Validar se o sistema consegue observar a tela da corretora, identificar informações importantes, registrar tudo no banco e gerar sinais explicáveis usando a estratégia Rebote Triplo.

## Regras congeladas

- [ ] Não executar cliques
- [ ] Não enviar ordens
- [ ] Não usar conta real
- [ ] Não implementar Forex
- [ ] Não implementar múltiplas estratégias
- [ ] Não implementar marketplace
- [ ] Não permitir IA operar
- [ ] Não prometer lucro

## Fundação

- [ ] Criar estrutura do projeto
- [x] Criar README.md
- [x] Criar docs/blueprint
- [x] Criar predixai_context.json
- [ ] Criar config.json
- [ ] Criar requirements.txt
- [x] Criar CHANGELOG.md
- [x] Criar ROADMAP.md

## Core

- [ ] Inicializar aplicação
- [ ] Carregar configurações
- [ ] Inicializar módulos
- [ ] Registrar status do sistema
- [ ] Exibir versão atual

## Config

- [ ] Definir intervalo de captura padrão de 10 segundos
- [ ] Definir plataforma inicial como Olymp Trade
- [ ] Definir mercado inicial como Fixed Time
- [ ] Definir estratégia inicial como Rebote Triplo
- [ ] Definir modo inicial como Observador

## Logs

- [ ] Criar logs técnicos
- [ ] Registrar inicialização
- [ ] Registrar erros
- [ ] Registrar falhas de leitura
- [ ] Registrar chamadas de IA
- [ ] Separar logs técnicos do Auditor

## Security básico

- [ ] Criar license.local.json local de teste
- [ ] Validar licença local
- [ ] Criar proteção básica para API Key
- [ ] Criar .gitignore para arquivos sensíveis
- [ ] Ignorar .env, license.local.json e secrets.local.json
- [ ] Não expor segredos no GitHub

## Vision

- [ ] Capturar tela a cada 10 segundos
- [ ] Salvar screenshot
- [ ] Detectar janela da corretora
- [ ] Detectar área do gráfico
- [ ] Detectar ativo
- [ ] Detectar saldo
- [ ] Detectar payout
- [ ] Detectar tempo da operação
- [ ] Detectar valor da entrada
- [ ] Detectar RSI 15
- [ ] Detectar RSI 30
- [ ] Detectar RSI 60
- [ ] Registrar status da leitura

## Auditor

- [ ] Criar banco SQLite
- [ ] Criar tabela de capturas
- [ ] Registrar data e hora
- [ ] Registrar caminho do screenshot
- [ ] Registrar ativo
- [ ] Registrar saldo
- [ ] Registrar payout
- [ ] Registrar tempo
- [ ] Registrar valor de entrada
- [ ] Registrar RSI 15
- [ ] Registrar RSI 30
- [ ] Registrar RSI 60
- [ ] Registrar sinal sugerido
- [ ] Registrar motivo do sinal
- [ ] Registrar status da leitura

## Strategy — Rebote Triplo

- [ ] Criar motor de estratégias
- [ ] Registrar estratégia ativa
- [ ] Implementar Rebote Triplo
- [ ] Gerar sinal COMPRA
- [ ] Gerar sinal VENDA
- [ ] Gerar sinal AGUARDAR
- [ ] Explicar motivo do sinal
- [ ] Não executar operação

## AI Provider Gemini

- [ ] Criar camada AI Provider
- [ ] Configurar Gemini como provedor inicial
- [ ] Ler API Key de arquivo local seguro
- [ ] Enviar dados resumidos do Auditor
- [ ] Gerar relatório simples
- [ ] Registrar resposta da IA
- [ ] Não permitir que IA opere

## Dashboard

- [ ] Criar interface simples
- [ ] Mostrar status observando
- [ ] Mostrar última captura
- [ ] Mostrar ativo detectado
- [ ] Mostrar saldo detectado
- [ ] Mostrar payout detectado
- [ ] Mostrar RSI 15/30/60
- [ ] Mostrar sinal sugerido
- [ ] Mostrar motivo
- [ ] Mostrar últimas leituras
- [ ] Mostrar logs recentes

## Critério de sucesso da V1

- [ ] A PredixAI consegue observar a tela da corretora, registrar dados, gerar sinal explicável e exibir tudo no dashboard sem executar nenhuma operação.

## Próximo passo depois da V1

Somente após validar a visão e auditoria:

- V2 poderá testar simulação em demo
- V3 poderá estudar execução assistida
- V4 poderá estudar execução automática
