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

- [x] Criar estrutura do projeto
- [x] Criar README.md
- [x] Criar docs/blueprint
- [x] Criar predixai_context.json
- [x] Criar config.json
- [x] Criar requirements.txt
- [x] Criar CHANGELOG.md
- [x] Criar ROADMAP.md

## Core

- [x] Inicializar aplicação
- [x] Carregar configurações
- [x] Inicializar módulos
- [x] Registrar status do sistema
- [x] Exibir versão atual

## Config

- [x] Definir intervalo de captura padrão de 10 segundos
- [x] Definir plataforma inicial como Olymp Trade
- [x] Definir mercado inicial como Fixed Time
- [x] Definir estratégia inicial como Rebote Triplo
- [x] Definir modo inicial como Observador

## Logs

- [x] Criar logs técnicos
- [x] Registrar inicialização
- [x] Registrar erros
- [ ] Registrar falhas de leitura
- [ ] Registrar chamadas de IA
- [ ] Separar logs técnicos do Auditor

## Perception Engine

- [x] Criar estrutura src/predixai/perception
- [x] Identificar sistema operacional
- [x] Identificar resolução do monitor
- [x] Identificar escala do sistema
- [x] Identificar quantidade de monitores
- [x] Identificar monitor principal
- [x] Identificar área útil da tela
- [x] Listar janelas por título, posição, largura e altura
- [x] Identificar janela ativa
- [x] Criar default_screen_profile.json sem coordenadas
- [x] Criar arquitetura inicial de calibração sem interface gráfica
- [ ] Detectar corretora
- [ ] Interpretar imagem
- [ ] Usar OCR

## Capture Engine

- [x] Criar estrutura src/predixai/capture
- [x] Criar contrato técnico do Capture Engine
- [x] Criar CaptureSession com ID único por sessão
- [x] Criar CaptureStorage para definir diretório de futuras capturas
- [x] Criar CaptureValidator para diretório existente, permissão de escrita e formato PNG
- [x] Adicionar configuração capture em config/config.json
- [x] Inicializar Capture Engine no Core apenas se enabled=true
- [x] Registrar logs de inicialização, diretório, formato e compressão
- [x] Criar captura manual via linha de comando
- [x] Salvar uma captura manual em PNG no diretório captures
- [x] Registrar sessão, horário, resolução, caminho e tamanho da captura manual
- [ ] Realizar captura automática
- [ ] Interpretar imagem capturada
- [ ] Usar OCR
- [ ] Usar IA
- [ ] Acionar estratégia

## Security básico

- [ ] Criar license.local.json local de teste
- [ ] Validar licença local
- [ ] Criar proteção básica para API Key
- [x] Criar .gitignore para arquivos sensíveis
- [x] Ignorar .env, license.local.json e secrets.local.json
- [x] Não expor segredos no GitHub

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
