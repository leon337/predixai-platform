# POLÍTICA OFICIAL DE EXECUÇÃO — PREDIXAI BR

## Objetivo

Maximizar produtividade, reduzir retrabalho, preservar arquitetura, registrar erros/acertos e manter o GitHub como memória técnica ativa.

## 1. Política atualizada

A política antiga de publicar apenas no fim da milestone fica substituída por:

    Debater → Aprovar plano → Script all-in-one → Executar → Validar → Registrar → Publicar → Abrir relatório

## 2. Script all-in-one

Cada script deve:

1. Entrar no repositório.
2. Ler estado real.
3. Criar backup quando necessário.
4. Executar auditoria/correção/validação.
5. Rodar testes mínimos.
6. Gerar relatório TXT em `reports/`.
7. Gerar Markdown histórico em `docs/history/ptp/`.
8. Atualizar `docs/reports_index.md` quando aplicável.
9. Fazer sanity check contra arquivos sensíveis.
10. Fazer `git add` apenas de arquivos permitidos.
11. Fazer commit.
12. Fazer push.
13. Abrir automaticamente o relatório TXT.

## 3. Fluxo OpenClaw/Agents

Todo script deve seguir:

    INVESTIGAR
    PLANEJAR
    CONSTRUIR
    VALIDAR
    REGISTRAR
    PUBLICAR
    ENTREGAR

## 4. Falha também é registro

Se falhar:

- gerar relatório FAIL/WARN/AUDIT/PAUSE;
- gerar Markdown histórico;
- versionar registro;
- fazer commit;
- fazer push;
- abrir relatório.

## 5. Segurança

Não versionar:

- `.env`
- tokens
- senhas
- cookies
- credenciais
- `.pyc`
- `__pycache__/`
- caches inúteis
- temporários irrelevantes

## 6. Condição para avançar

Só avançar etapa quando:

- relatório foi colado no chat;
- resultado foi analisado;
- GitHub recebeu commit/push;
- roadmap foi atualizado;
- próxima etapa foi confirmada.
