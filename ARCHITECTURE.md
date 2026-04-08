# 🧠 Second Brain Ultimate - System Architecture

## Visão Geral do Sistema
O **Second Brain Ultimate** é um sistema inteligente de extensão cognitiva baseado em Python, estruturado para atuar como um "motor de processamento de vida". Ele é fortemente influenciado pelo framework P.A.R.A e é projetado para integração com um LLM core (Claude/Gemini) e a plataforma "Lex Flow".

## 🏗️ Estrutura de Diretórios e Módulos

### 1. ⚙️ `engine/` (O Cérebro)
Este é o núcleo de processamento do sistema.
- **`core_engine.py`**: O orquestrador principal que liga os módulos, gerencia o ciclo de vida e lida com a inicialização sistêmica.
- **`capture_system.py`**: Responsável por receber dados não estruturados de múltiplas fontes (Lex Flow inbox, Telegram, etc.) e padronizá-los.
- **`decision_engine.py`**: A camada de raciocínio lógico baseada em regras e chamadas ao LLM. Avalia prioridades, processa o contexto de negócio e decide fluxos e classificação (P.A.R.A).
- **`memory_system.py`**: O sistema de persistência inteligente para memórias e contexto RAG de longo prazo. Arquitetado para se apoiar na pasta `data/vector_store/`.
- **`automation_system.py`**: O executor de tarefas. Aplica rotinas de fundo, executa os workflows lógicos ditados pela decisão e move blocos pela arquitetura de maneira automatizada.
- **`insight_generator.py`**: Motor analítico (crítico para a prevenção do acúmulo e procrastinação pontuada no SOUL.md). Identifica projetos estagnados (WIP limit).

### 2. 🔌 `integrations/` (Os Sentidos)
Responsável pela comunicação do motor com o ecossistema exterior (Lex Flow, Obsidian).
- **`lex_flow_definitivo.py`**: O cliente principal de comunicação ao dashboard web Lex Flow. Lê a "Caixa de Entrada" (inbox) e atualiza o status de cards/projetos na plataforma original.
- **`econd_brain_engine.py` / Integrações futuras**: Comunicação paralela de serviços.

### 3. 🧬 Documentação de Metacognição (Raiz da Pasta)
Arquivos Markdown que balizam as regras comportamentais dos prompts do LLM, servindo como o "Contrato de Identidade":
- **`SOUL.md`**: Os valores essenciais, tom de voz (direto, pragmático), regras absolutas e restrições. Define limites de Work in Progress (WIP) ativos (4-7 projetos).
- **`USER.md`**: O ecossistema estritamente relacionado ao usuário e suas nuances.
- **`HEARTBEAT.md`**: O estado pulsante do projeto e as mecânicas de loops operacionais (o que revisar no dia, o que checar na semana).
- **`MEMORY.md`**: O registro histórico e contínuo dos aprendizados do sistema sobre o projeto.

### 4. 🗄️ Infraestrutura Geral
- **`config/` e `.env`**: Centralização de chaves da API e tokens de conexão para Lex Flow.
- **`data/` e `logs/`**: Armazenamento local das informações processadas.
- **`skills/`**: Pasta plug e play de extensibilidade de capacidades (ações atômicas mapeadas).
- **`setup.sh` e `requirements.txt`**: Automação de instanciamento do ambiente Python e suas bibliotecas base (dotenv, requests).

## 🚀 Fluxo de Dados Ideal

1. **Ingestão**: Ideias chegam ao inbox da interface Lex Flow.
2. **Captura**: O motor periodicamente desperta, `capture_system.py` lê os dados brutos novos via API (via `lex_flow_definitivo.py`).
3. **Refinamento & Decisão**: O `core_engine.py` repassa aos cérebros lógicos. `decision_engine.py` classifica e sugere qual é o próximo passo acionável de cada ideia usando os limites definidos em `SOUL.md`. `memory_system.py` alimenta o contexto.
4. **Execução/Ação**: `automation_system.py` categoriza as ideias via API novamente para seus respectivos locais corretos.
5. **Insights Proativos**: Nas reuniões com o dev (matinais), `insight_generator.py` sumariza estressores ou projetos que quebram limites predefinidos de prazo.

## 🛠️ Próximos Passos de Desenvolvimento para o Usuário
1. **Costurar a Carga**: Conectar apropriadamente as simulações no `core_engine.py` às bibliotecas finalizadas (processamento real em vez de logs inertes).
2. **Persistência das Memórias**: Implementar banco vetorial ou simples para o `memory_system.py`.
3. **Orquestrador Temporizado**: Implementar agendamento (cron ou loop de sleep asyncio) para que as requisições API chequem os inboxes em plano de fundo de maneira resiliente.
