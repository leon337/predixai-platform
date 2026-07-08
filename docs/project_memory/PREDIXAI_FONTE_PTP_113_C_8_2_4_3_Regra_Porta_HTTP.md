# PREDIXAI FONTE — PTP 113 C.8.2.4.3
## Regra de Porta HTTP em Auditorias

Data: 2026-07-08 08:19:01 -0300  
Projeto: PredixAI BR  
Produto: PredixAI Trader  
Tipo: Fonte operacional / Governança técnica  
Status: Regra registrada

---

## 1. Identificação

```txt
PTP: PTP 113 C.8.2.4.3
Nome curto: registrar_regra_porta_http
Tipo: DOCUMENTAÇÃO / GOVERNANÇA
Código alterado: NÃO
```

---

## 2. Contexto

Na `PTP 113 C.8.2.4`, a auditoria estrutural testou endpoints em:

```txt
http://127.0.0.1:8766
```

Essa porta veio do histórico anterior do projeto, mas não era a porta real ativa naquele momento.

Leo informou que o serviço real estava em:

```txt
http://127.0.0.1:5001/mobile
```

Na `PTP 113 C.8.2.4.2`, a validação HTTP na porta `5001` retornou PASS_VALIDATION.

---

## 3. Regra oficial

```txt
Nunca assumir porta pelo histórico.
```

Antes de qualquer validação HTTP:

```txt
1. Detectar porta ativa quando possível.
2. Aceitar BASE_URL configurável.
3. Registrar BASE_URL no relatório.
4. Testar a porta real informada pelo Leo.
5. Se houver dúvida, testar portas candidatas, como 5001 e 8766.
6. Se nenhuma porta responder, classificar como SERVER_NOT_RUNNING ou PORTA_NAO_CONFIRMADA.
7. Não classificar como falha do app sem servidor confirmado.
```

---

## 4. Classificação correta de falhas HTTP

```txt
HTTP 000 / conexão recusada:
  SERVER_NOT_RUNNING ou PORTA_NAO_CONFIRMADA

HTTP 4xx:
  rota, método, payload ou contrato possivelmente incorreto

HTTP 5xx:
  possível falha interna do app

HTTP 200/201:
  endpoint saudável
```

---

## 5. Aplicação obrigatória

Esta regra deve ser aplicada em:

```txt
- auditorias HTTP;
- validações de endpoint;
- scripts all-in-one;
- validações mobile;
- validações pré e pós-patch;
- próximas etapas da C.8.3.
```

---

## 6. Próxima ação

Replanejar a C.8.3 usando:

```txt
BASE_URL configurável
porta confirmada ou detectada
validação HTTP segura
sem assumir 8766
sem classificar porta errada como bug do app
```

FIM DA FONTE.
