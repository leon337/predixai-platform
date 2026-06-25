# PredixAI BR — Guia de Desenvolvimento v1.0

## 1. Objetivo

Este guia define como o Codex deve trabalhar no projeto.

## 2. Regras obrigatórias para o Codex

- Não alterar arquitetura sem aprovação.
- Não implementar funcionalidades fora da fase atual.
- Não criar arquivos gigantes.
- Não misturar responsabilidades.
- Não colocar API Key no código.
- Não remover documentação.
- Sempre atualizar predixai_context.json.
- Sempre atualizar CHANGELOG.md em mudanças relevantes.
- Sempre explicar o que foi alterado.

## 3. Estilo de código

- Python 3.11+
- Código limpo
- Funções pequenas
- Classes com responsabilidade clara
- Tratamento de erros
- Logs obrigatórios
- Testes sempre que possível

## 4. Organização

Cada módulo deve ficar em sua pasta.

Exemplo:

```text
src/predixai/vision/
src/predixai/auditor/
src/predixai/security/
```

## 5. Configuração

Configurações devem ficar em arquivos próprios.

Nunca fixar valores importantes dentro do código.

## 6. Segurança

Nunca salvar segredos no GitHub.

Arquivos sensíveis devem ser ignorados pelo Git.

Exemplo:

```text
.env
secrets.json
license.local.json
```

## 7. Fluxo de trabalho

1. ChatGPT define tarefa.
2. Leo envia tarefa ao Codex.
3. Codex implementa.
4. Codex atualiza contexto.
5. Leo testa.
6. ChatGPT revisa.

## 8. Critério de conclusão

Uma tarefa só estará concluída quando:

- código funcionar;
- documentação estiver atualizada;
- contexto estiver atualizado;
- logs não apresentarem erro crítico;
- Leo conseguir testar.
