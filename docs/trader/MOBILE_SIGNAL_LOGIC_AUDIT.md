# Mobile Signal Logic Audit

Data: 2026-07-02

Escopo: PredixAI Trader Mobile Observer. O sistema permanece em modo observador/simulado, sem cliques, sem ordens, sem automacao operacional de corretora e sem promessa de resultado.

## Leitura de preco

O leitor leve do mobile usa `live_price_tick()` em `src/predixai/core/app.py`. A cada ciclo ele detecta a janela ativa, valida se a janela pertence ao contexto da corretora e tenta extrair ativo e preco diretamente do `window_title`.

Quando a janela ativa nao e uma janela valida da corretora, a leitura e registrada como `IGNORED_WINDOW`, com `price_value=null`, e nao alimenta o historico valido nem os sinais.

## Prioridade de fonte

A prioridade atual e:

1. `window_title`, quando o titulo contem ativo/preco valido.
2. `last_detected_price_field`, apenas como fallback recente quando o preco do titulo nao passa na validacao.
3. Rejeicao segura (`PRICE_NOT_FOUND` ou `IGNORED_WINDOW`) quando nao ha preco confiavel.

O painel mobile deve exibir `price_source=window_title` para as leituras principais. OCR completo nao e usado no ciclo leve do mobile; o payload preserva `source_ocr_text` apenas como texto sintetico de evidencia da janela detectada.

## Suporte e resistencia

No servidor mobile, suporte e resistencia sao calculados sobre o historico filtrado da sessao e do ativo atual:

- suporte: menor `price_value` valido da janela analisada.
- resistencia: maior `price_value` valido da janela analisada.

Esse calculo e simples e serve como referencia visual/diagnostica. Ele ainda nao e uma calibracao estatistica de zonas de mercado.

## Decisao do sinal

A funcao de decisao usa os ultimos precos validos da sessao atual:

- menos de 6 precos validos: `AGUARDAR` / `COLETANDO`, confianca 20.
- movimento absoluto dos ultimos 6 pontos menor que 0.35: `AGUARDAR` / `LATERAL`, confianca 35.
- delta positivo suficiente: `OBSERVAR ALTA`.
- delta negativo suficiente: `OBSERVAR BAIXA`.

O sinal e observador. Ele nao autoriza, executa nem automatiza entrada.

## Confianca

A confianca atual e heuristica:

- 20 durante coleta inicial.
- 35 em movimento lateral/fraco.
- 55 quando o movimento curto confirma a direcao do delta principal.
- 45 quando o delta principal existe, mas o ultimo passo curto nao confirma.

Para leituras de preco por `window_title`, a confianca da leitura pode ser 100 porque a fonte do preco foi encontrada. Isso e diferente da confianca do sinal, que continua sendo calculada pela heuristica de movimento.

## Cooldown e ciclo de 3s

O leitor mobile e iniciado por `POST /api/mobile/start?interval=3`. A rota possui lock de processo e retorna `ALREADY_RUNNING` quando ja existe leitor ativo, preservando `active_reader_count=1`.

Novos sinais sao bloqueados quando:

- ja existe sinal pendente para o mesmo ativo/direcao/sessao.
- o ultimo sinal da sessao ainda esta dentro de `SIGNAL_COOLDOWN_SECONDS`.

## Expiracao simulada de 30s

Ao registrar `OBSERVAR ALTA` ou `OBSERVAR BAIXA`, o servidor grava o sinal em SQLite com:

- `entry_price`.
- `created_at`.
- `expires_at = created_at + expiration_seconds`.
- `expiration_seconds`, padrao 30.
- `session_id` da sessao mobile atual.
- `observer_only=true` e `orders_enabled=false` no metadata.

## Validacao WIN/LOSS/DRAW

Depois da expiracao, o servidor procura um preco valido perto do alvo temporal. A janela principal de busca cobre a faixa de 30s a 40s apos a emissao do sinal.

Resultado:

- `ALTA`: WIN se o preco final for maior que a entrada, LOSS se for menor.
- `BAIXA`: WIN se o preco final for menor que a entrada, LOSS se for maior.
- `DRAW`: preco final igual ao preco de entrada.
- `UNKNOWN`: sem preco final confiavel depois da margem.

O resultado continua simulado/observador.

## Como UNKNOWN e evitado

O servidor evita `UNKNOWN` prematuro mantendo sinais em `WAITING_RESULT` ate haver preco final ou ate passar a margem final. A busca tenta usar historico JSON e `price_ticks` SQLite. Se um preco valido for encontrado posteriormente, o backfill pode corrigir sinais antigos marcados como `UNKNOWN`.

`UNKNOWN` so deve permanecer quando nao houver preco valido dentro da margem configurada.

## Session_id e filtro por ativo

`POST /api/mobile/reset-session` cria uma nova sessao em `data/runtime/mobile_current_session.json`, com `session_id` no formato `mobile_YYYYMMDD_HHMMSS_xxxxxxxx`.

O painel filtra historico, sinais e diagnosticos pela sessao atual e pelo ativo atual. Isso evita mistura entre Cafeina Index, LATAM Index, UNKNOWN antigo e sinais de sessoes anteriores.

A limpeza real:

- cria backup em `data/runtime/backups/mobile_reset_YYYYMMDD_HHMMSS/`.
- zera `live_price_history.json`.
- zera `rejected_live_readings.json`.
- registra `SESSION_RESET` em `last_live_reading.json`.
- limpa as tabelas SQLite `signals` e `price_ticks`.

## Calibracao futura

Pontos que ainda precisam evoluir para melhorar acuracia:

- substituir suporte/resistencia min/max por zonas com tolerancia e toques.
- calibrar o limiar fixo de delta `0.35` por ativo.
- separar confianca da leitura e confianca do sinal na UI.
- medir taxa por ativo, horario e volatilidade.
- ampliar criterios de DRAW para tolerancia minima de preco.
- registrar explicacoes de sinal mais detalhadas no metadata.
- validar com amostra maior apos sessoes limpas, sem misturar ativos.
