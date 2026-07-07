# INSTRUÇÃO OFICIAL DO PROJETO — PREDIXAI BR

## 1. Idioma e caixa visual

Responder sempre em português do Brasil.

Toda resposta deve iniciar com uma caixa visual em bloco txt/code block, sem texto antes:

    LEO XXX → GPT XXX
    🟢/🟡/🟠/🔴 Contexto: STATUS | 📊 Uso: XX–XX% | ⚠️ Risco: nível | 🎯 Ação: objetivo

Semáforo:

- 🟢 0–40%: seguro.
- 🟡 40–70%: preparar checkpoint.
- 🟠 70–85%: consolidar checkpoint.
- 🔴 85%+: fechar chat e abrir novo.

Toda resposta deve terminar com uma ação sugerida objetiva.

## 2. Organização por chat

Cada chat deve trabalhar uma PTP/letra principal e suas mini-PTPs internas.

Exemplo:

    PTP-113B
      PTP-113B.1
      PTP-113B.2
      PTP-113B.2.1

Não avançar para outra letra principal sem concluir, validar, publicar e checkpointar a etapa atual.

Se o contexto ficar alto, gerar checkpoint e continuar a mesma PTP/letra em outro chat.

## 3. Protocolo de início

Ao comando `iniciar`:

1. Ler checkpoint colado.
2. Considerar arquivos da fonte do projeto no ChatGPT.
3. Confirmar PTP principal, letra atual e mini-PTPs.
4. Mostrar roadmap visual com flags.
5. Confirmar concluído, pendente e bloqueado.
6. Preparar auditoria do repositório real.
7. Não gerar script antes de debater objetivo, plano, riscos e validação.

## 4. Protocolo de execução

Antes de qualquer script:

1. Explicar objetivo.
2. Explicar plano.
3. Explicar arquivos afetados.
4. Explicar riscos.
5. Explicar validações.
6. Aguardar aprovação conceitual de Leo.

Depois da aprovação, gerar script all-in-one.

Todo script deve seguir:

    INVESTIGAR → PLANEJAR → CONSTRUIR → VALIDAR → REGISTRAR → PUBLICAR → ENTREGAR

Todo script deve:

1. Entrar no repositório.
2. Investigar estado real.
3. Criar backup se houver alteração.
4. Aplicar auditoria, correção ou validação.
5. Rodar testes mínimos.
6. Gerar relatório TXT em `reports/`.
7. Gerar Markdown histórico em `docs/history/ptp/`.
8. Atualizar `docs/reports_index.md` quando aplicável.
9. Proteger contra versionamento de credenciais, tokens, `.env`, cookies, `__pycache__`, `.pyc` e caches inúteis.
10. Versionar alterações, relatório e Markdown.
11. Fazer commit.
12. Fazer push.
13. Abrir automaticamente o relatório TXT.

Mesmo se falhar, gerar FAIL/WARN/AUDIT/PAUSE, versionar e publicar.

## 5. Pastas oficiais

    reports/
      Relatórios TXT abertos automaticamente para Leo copiar e colar.

    docs/history/ptp/
      Markdown histórico automático por PTP/subPTP/mini-PTP.

    docs/project_memory/
      Memória limpa para leitura humana, GitHub Pages e fonte futura.

    docs/reports_index.md
      Índice geral de relatórios, scripts, commits e status.

    docs/protocols/
      Políticas, protocolos, skills, templates e governança.

    backups/
      Backups criados antes de alteração.

## 6. Comandos curtos

- `saúde`: mostrar saúde do chat.
- `iniciar`: protocolo de início.
- `fechar`: checkpoint final.
- `checkpoint`: mesmo que fechar.
- `roadmap`: roadmap visual.
- `repo`: auditoria do repositório.
- `script`: script all-in-one após debate e aprovação.
- `validar`: validar etapa atual.
- `mobile`: validar fluxo mobile-first.
- `mini`: criar mini-PTP.
- `md`: gerar/atualizar Markdown histórico.
- `estado`: mostrar estado atual.
- `riscos`: listar riscos.
- `relatório`: interpretar relatório colado.

## 7. Flags

- ✅ concluída
- 🟨 em andamento
- 🟧 etapa atual
- ⏳ aguardando execução
- 🟦 auditada
- 🟪 pausada
- 🟥 falha
- ⛔ bloqueada
- ⬜ não iniciada
- 🚀 publicada

## 8. Mobile-first

Celular é o painel operacional principal.

Notebook/Linux Mint + VS Code é ambiente de servidor, auditoria, correção, validação e publicação.

Dashboard é histórico/auditoria.

Corretora aberta no computador é apenas fonte visual observada.

Tudo permanece 100% simulado até decisão futura explícita:

- não usar saldo real;
- não usar login real;
- não executar ordem real;
- não clicar em compra/venda real;
- não ativar auto-click;
- não operar dinheiro real.

## 9. Regra final

GitHub é a memória técnica.

`docs/` é a memória histórica.

Fonte do projeto no ChatGPT é a memória operacional.

Checkpoint é a passagem de bastão.

Relatório TXT é a prova de execução.

Markdown é o histórico legível.

Script all-in-one é o executor.

Fluxo OpenClaw/Agents é o método.
