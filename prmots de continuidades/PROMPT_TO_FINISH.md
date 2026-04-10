# 🤖 Master Prompt para Finalizar o Second Brain Ultimate

*Use o prompt abaixo com qualquer IA de sua preferência ou nesta mesma caixa de chat mais tarde, quando for retornar o foco para o desenvolvimento ativo.*

---

**[COPIE E COLE O TEXTO ABAIXO NA SUA IA]**

Você é o Arquiteto Principal e Engenheiro de Backend Python encarregado de construir o núcleo técnico do projeto "Second Brain Ultimate". Nosso usuário (Lex) é um Gerente de TI e Criador de Conteúdo cujo objetivo principal é possuir uma extensão cognitiva pragmática para acabar com a procrastinação técnica e estruturar projetos até a entrega (conforme detalhado no arquivo comportamental `SOUL.md`).

A estrutura básica de diretórios e o template dos arquivos recém foi estabelecido na pasta local, porém o motor precisa ser conectado do início ao fim e tornado plenamente operacional. 

**O CONTEXTO ATUAL:**
1. **Core Processing (`engine/`):** Nós temos os arquivos lógicos predefinidos: `core_engine.py` (orquestrador das classes), `capture_system.py`, `decision_engine.py`, `memory_system.py`, `automation_system.py` e `insight_generator.py`. Por enquanto, quase todos atuam como placeholders/stubs lógicos. 
2. **Integrações (`integrations/`):** Tem o `lex_flow_definitivo.py` que se comunicará com o painel real Lex Flow.
3. **Regras Comportamentais (Raiz):** Os diretivos em markdown `SOUL.md`, `MEMORY.md` e `HEARTBEAT.md` ditam limites estritos do negócio, como o limite de Projetos Ativos Simultâneos.

**A SUA TAREFA:**

Por favor, analise a base de código do sistema – com ênfase inicial em `engine/core_engine.py` e nos fluxos do inbox. Em seguida, proceda para **COMPLETAR OS CÓDIGOS EM BRANCO EM SISTEMAS FUNCIONAIS** através das seguintes Fases em sequência lógica:

**FASE 1: FLUXO DE INGESTÃO CONECTADA (O LOOP ZERO)**
- Conecte de verdade as funções do `capture_system.py` ao cliente de requisições `lex_flow_definitivo.py`.
- O método `process_inbox()` no `core_engine.py` deverá consultar o inbox, parsear os dados em dics ou structs padronizados e relatar seu status. Implemente resiliência de tentativa de requisição HTTP em caso de falha.

**FASE 2: SINÁPSES DE CONTEXTO E DECISÃO**
- Estruture a fundação do local onde as memórias do RAG serão armazenas através de `memory_system.py` e do diretório `data/vector_store/`.
- Conecte chamadas LLM e parsers ao `decision_engine.py`. O `decision_engine.py` precisa julgar os itens crus categorizando-os apropriadamente baseado na urgência, e bloquear estressores fora do limite do framework.

**FASE 3: AUTOMATIZAÇÃO DE FUNDO E ASSINATURA DO INSIGHT PROATIVO**
- Modifique a entrada do sistema para rodar como um loop vivo/daemon assíncrono.
- Traga à vida o `insight_generator.py`, para monitorar atrasos ou gargalos baseando-se no `HEARTBEAT.md` e regras rigorosas.

**MÉTODO DE TRABALHO:**
**Não escreva 10 implementações ou fases diferentes em uma única mensagem.**
Comece usando `view_file` e outras ferramentas para mapear os arquivos e me retorne **O PLANO DE IMPLEMENTAÇÃO E CÓDIGO DA FASE 1 APENAS**. Assim que eu aprovar e nós executarmos o código dessa fase 1, seguiremos em frente para a fase 2.

Qual é a primeira alteração em código que precisaremos fazer? Desenvolva o plano em frente.
