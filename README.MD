
🧠 LEX-BRAIN HYBRID v4.0

Sistema de Segundo Cérebro Híbrido com IA

StatusGeminiTelegramPythonLicense

Bot Telegram 100% EM PRODUÇÃO ✅ | Latência ~3-5s ⚡

📌 Sobre o Projeto

O LEX-BRAIN HYBRID é um sistema inteligente de Segundo Cérebro que combina:

🗂️ Obsidian - Base de conhecimento local em Markdown
🌐 Lex Flow Dashboard - Web App para gestão P.A.R.A (Projetos, Áreas, Recursos, Arquivos)
🤖 Engine Python - Motor orquestrador central com Singleton + Lazy Loading
💬 Telegram Bot (@Lex_Cerebro_bot) - Interface conversacional com IA
🧠 Google Gemini 2.5 Flash - Provider de IA ultra-rápido (~3-5s)
🎯 Objetivo Principal

Organizar automaticamente todas as informações, tarefas e notas do usuário através de conversação natural em português.

✨ Funcionalidades Principais

🤖 Telegram Bot (@Lex_Cerebro_bot)

Comando	Descrição
/start	Inicia o bot e mostra menu
/tarefa	Cria nova tarefa
/anota ou /nota	Cria nota rápida
/inbox	Mostra caixa de entrada
/areas	Lista áreas P.A.R.A
/projetos	Lista projetos ativos
/mover	Move nota para área/projeto
/stats	Métricas do sistema*
⚡ Recursos de IA

✅ Comandos Óbvios: "anota: comprar leite" → executa direto!
✅ Detecção de Destino: "na área Saúde" → move automaticamente
✅ Busca por Índice: "item 1", "primeira nota"
✅ Sistema de Clarificação: Pergunta quando não tem certeza
✅ Filtro de Gírias: Ignora "pra mim", "pra gente"
✅ RAG System v2.0: Busca híbrida TF-IDF + Cosseno
🔌 Integrações

✅ Lex Flow API - Gestão completa de notas/tarefas
✅ Google Gemini 2.5 Flash - IA principal (3-5s)
✅ NVIDIA/GLM5 - Fallback automático (23s)
✅ Scheduler System - 5 workflows automatizados
🏗️ Arquitetura do Sistema

 SecondBrain_Ultimate/ │ ├──📁 config/ │ ├── settings.yaml # Configuração completa │ └── .env.example # Template de variáveis │ ├──📁 engine/ # ✅ 12+ MÓDULOS FUNCIONANDO! │ ├── core_engine.py # v2.1 (Singleton + Lazy Loading) │ ├── capture_system.py # v2.0 (Integrado ao Lex Flow) │ ├── decision_engine.py # v2.0 (P.A.R.A., score 0-10) │ ├── memory_system.py # v2.0 (Cache TTL, busca híbrida) │ ├── automation_system.py # v2.0 (Heartbeat, alertas) │ ├── insight_generator.py # v2.0 (TELOS 5D, padrões) │ ├── scheduler.py # v1.0.2 (5 Workflows) │ ├── rag_system.py # v2.0 (TF-IDF + Cosseno + Enum) │ ├── llm_client.py # v1.3 (Gemini + NVIDIA Fallback) │ ├── gemini_client.py # v1.0 (Provider Gemini) │ ├── brain_llm_orchestrator.py # v3.8 (LLM-First + Clarificação) │ ├── brain_acoes.py # v3.9 (Executor de ações) │ └── brain_types.py # Tipos compartilhados │ ├──📁 integrations/ # ✅ 4 MÓDULOS FUNCIONANDO! │ ├── lex_flow_definitivo.py # v3.11 (API Connector) │ ├── telegram_bot.py # v2.1 (~1200 linhas) │ ├── telegram_handlers.py # Handlers de comando │ └── telegram_brain_handler.py # v3.1 (Processamento IA) │ ├──📁 logs/ # ✅ 11 ARQUIVOS DE LOG ATIVOS │ ├── SOUL.md # Identidade do sistema ├── USER.md # Perfil do usuário ├── HEARTBEAT.md # Checklist diário ├── MEMORY.md # Lições aprendidas ├── iniciar_scheduler.py # ✅ Script de BOOT completo └── requirements.txt # Dependências

text


---

## 🚀 Instalação Rápida

### Pré-requisitos
- Python 3.10+
- pip (gerenciador de pacotes Python)
- Conta Google Cloud (para Gemini API key)

### Passo 1: Clonar Repositório
```bash
git clone https://github.com/Lex-usamn/SecondBrain_Ultimate.git
cd SecondBrain_Ultimate
 Passo 2: Ambiente Virtual

bash

python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
 Passo 3: Instalar Dependências

bash

pip install -r requirements.txt
 Passo 4: Configurar Variáveis de Ambiente

bash

export TELEGRAM_BOT_TOKEN=SEU_TELEGRAM_TOKEN
export GEMINI_API_KEY=API_KEY
 Ou crie um arquivo .env:

env

TELEGRAM_BOT_TOKEN=SEU_TELEGRAM_TOKEN
GEMINI_API_KEY=API_KEY
LEX_FLOW_USERNAME=USUARIO
LEX_FLOW_PASSWORD=SENHA
 Passo 5: Iniciar o Sistema

bash

python iniciar_scheduler.py
 Output Esperado

text

[GEMINI] Cliente Gemini 2.5 Flash inicializado!
Cliente LLM criado com sucesso (provedor: gemini, modelo: gemini-2.5-flash)
>>> @Lex_Cerebro_bot está ONLINE e OUVINDO!
BRAIN LLM ORCHESTRATOR v3.8 ATIVO!
   -> IA Conversacional HABILITADA (GEMINI POWERED! ⚡)
   -> Contextos .md CARREGADOS (SOUL, USER, MEMORY, HEARTBEAT)
   -> Sistema de CLARIFICAÇÃO ATIVO
   -> Comandos ÓBVIOS ativados ("anota:" executa direto!)
   -> MOVER NOTAS ativado (PUT /link!)
   -> DETECÇÃO DE DESTINO ativada ("na área X")
   -> INBOX ROBUSTO ATIVO (_get_inbox_robusto com chave 'notes')!
 📊 Fluxo de Mensagem

text

Usuário envia mensagem no Telegram
           ↓
    telegram_bot.py (handler_mensagem_texto)
           ↓
    telegram_brain_handler.py (brain.processar_mensagem())
           ↓
    ├─→ Verifica CLARIFICAÇÃO PENDENTE?
    │    └─→ SIM → Processa resposta
    │
    └─→ NÃO → brain_llm_orchestrator.processar()
              ↓
         Carrega contextos (.md files + Inbox Lex Flow)
              ↓
         Monta prompt mestre → Envia para Gemini
              ↓
         Parseia JSON: {acao, resposta, entidades}
              ↓
         Executa ação via brain_acoes.py:
         • criar_nota / criar_tarefa
         • mover_nota (PUT /link!)
         • buscar_info (áreas/projetos/inbox)
         • conversar (resposta direta)
              ↓
         Formata resposta → Envia ao Usuário 🎉
 🔌 API Endpoints (Lex Flow)

Endpoints Disponíveis

ENDPOINT
 MÉTODO
 DESCRIÇÃO
 /api/auth/login	POST	Autenticação JWT
/api/quicknotes/	GET	Caixa de Entrada (Inbox)
/api/quicknotes/	POST	Criar nova nota
/api/quicknotes/<id>	PUT	Atualizar nota
/api/quicknotes/<id>/link	PUT	⭐ Mover nota para área/projeto
/api/quicknotes/<id>	DELETE	Deletar nota
/api/quicknotes/<id>/convert-to-task	POST	Converter nota em tarefa
/api/areas/	GET	Listar áreas P.A.R.A
/api/collaboration/projects	GET	Listar projetos
/api/analytics/dashboard	GET	Estatísticas completas
 
Exemplo: Mover Nota

http

PUT /api/quicknotes/17/link
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "target_type": "project",
  "target_id": 5
}

Response:
{
  "message": "Anotação movida para project \"Canais Dark\" com sucesso",
  "note": {
    "id": 17,
    "project_id": 5,
    "para_category": "Project"
  }
}
 ⚠️ IMPORTANTE: Sempre usar PUT /{id}/link para mover notas! Nunca usar PATCH!

 📈 Métricas de Performance

MÉTRICA
 VALOR
 STATUS
 Latência Gemini	~3-5 segundos	✅ Excelente
Latência Fallback (NVIDIA)	~23 segundos	⚠️ Aceitável
Provider Ativo	gemini-2.5-flash	✅ Online
Limite Gemini Free Tier	20 req/dia	⚠️ Conhecido
Status Bot	ONLINE	✅ Respondendo
Logs Ativos	11 arquivos	✅ Monitorado
Erros Corrigidos	22+ críticos	✅ Estável
 
Melhorias de Performance

 🎉 GLM5 → Gemini: 26s → 3.5s (86% mais rápido!)
 🎉 Retry Automático: Re-login se token expira
 🎉 Inbox Robusto: 3 estratégias de fallback
 🏆 Conquistas e Marcos

✅ Implementado (99%)

 Engine Python com 12+ módulos funcionando
 Lex Flow Dashboard em produção
 Telegram Bot 100% online e respondendo
 Sistema RAG v2.0 (TF-IDF + Busca Híbrida + Enum)
 LLM Client v1.3 (Gemini + NVIDIA Fallback)
 Brain Orchestrator v3.8 (Clarificação + Comandos Óbvios)
 Brain Ações v3.9 (Mover Notas Corrigido!)
 Scheduler System com 5 workflows ativos
 Sistema de Clarificação (pergunta antes de executar)
 Detecção automática de destino ("na área X")
 Filtro de gíras inválidas
 Busca por índice ("item 1", "primeira nota")
 Listar áreas/projetos do Flow (não do SOUL.md)
 22+ erros críticos corrigidos em 4 sessões
 🔄 Em Progresso (1%)

 Endpoint /filter no Flow (listar notas por área)
 Tornar Lex Flow opcional (boot sem ele)
 Cache de respostas frequentes
 Reduzir tamanho do prompt (71K → 8K chars)
 Dashboard /stats no Telegram
 🔮 Futuro

 Discord Bot
 Multi-Model Support
 Interface Web Própria
 🐛 Bugs Conhecidos e Resolvidos

✅ Corrigidos (Última Sessão 17/04/2026)

BUG
 CAUSA
 SOLUÇÃO
 Mover notas dava 405	Usava PATCH errado	PUT /quicknotes/{id}/link
ID da nota retornava None	resultado.get('id')	Extrair de resultado['note']['id']
"na área X" ignorado	Não detectava destino	Regex + mover automático
"minhas áreas" buscava no RAG	IA decidia buscar_info	Detectar intenção PRIMEIRO
"pra mim" como projeto	Não filtrava gíras	Lista de inválidos
 
⚠️ Limitações Conhecidas

 Gemini Free Tier = 20 requisições/dia (depois dá 429!)
 Endpoint /quicknotes/ só retorna inbox (area_id=NULL)
 Precisa adicionar /filter no Flow para listar notas por área
 🛠️ Stack Tecnológica

TECNOLOGIA
 VERSÃO
 USO
 Python	3.10+	Linguagem principal
FastAPI	Latest	API Framework (Lex Flow)
SQLAlchemy	Latest	ORM Database
Google Gemini	2.5 Flash	IA Principal
NVIDIA	GLM5	Fallback IA
Telegram	Bot API	Interface Chat
SQLite	3.x	Banco Local
PyYAML	Latest	Configuração
 
📁 Estrutura de Contexto (.md Files)

ARQUIVO
 TAMANHO
 DESCRIÇÃO
 SOUL.md	~17KB	Identidade, personalidade e comportamento do sistema
USER.md	~21KB	Perfil completo do usuário (preferências, metas)
HEARTBEAT.md	~21KB	Checklist diário e rotinas
MEMORY.md	~8KB+	Lições aprendidas e histórico de decisões
ARCHITECTURE.md	~4KB	Documentação técnica da arquitetura
 
🔗 Links Úteis

Aplicações

 Lex Flow Dashboard: https://flow.lex-usamn.com.br
 Telegram Bot: @Lex_Cerebro_bot  ✅ ONLINE
 GitHub Repository: https://github.com/Lex-usamn/SecondBrain_Ultimate
 Canais do Criador

 YouTube (Dark): Canal Dark
 Instagram: @cerne.das.coisas
 APIs Externas

 Google AI Studio: https://aistudio.google.com
 NVIDIA API: https://integrate.api.nvidia.com
 📝 Exemplos de Uso

Criar Nota na Caixa de Entrada

text

Você: anota: comprar leite pão e manteiga
Bot: ✅ Nota criada na Caixa de Entrada!
   ID: 42
   Título: comprar leite pão e manteiga
 Criar Nota com Destino Automático

text

Você: anota: revisar script do vídeo na área Canais Dark
Bot: ✅ Nota criada e movida para área "Canais Dark"!
   ID: 43
   Destino: Canais Dark (Área)
 Mover Nota Existente

text

Você: move item 1 para projeto Vlog Diário
Bot: ✅ Nota movida com sucesso!
   "homem aranha noir" → Projeto "Vlog Diário"
 Ver Caixa de Entrada

text

Você: me mostra a caixa de entrada
Bot: 📥 CAIXA DE ENTRADA (7 notas):
   
   [1] comprar leite pão e manteiga
   [2] revisar script do vídeo
   [3] ideia para thumbnail novo
   ...
   
   Total: 7 notas
 Conversa Casual

text

Você: tá por ai mago?
Bot: Estou aqui! 😊 Pronto para ajudar.
   
   O que você precisa organizar hoje?
 🤝 Contribuição

Contribuições são bem-vindas! Por favor:

Fork o projeto
Crie uma branch (git checkout -b feature/AmazingFeature)
Commit suas mudanças (git commit -m 'Add AmazingFeature')
Push para a branch (git push origin feature/AmazingFeature)
Abra um Pull Request
Regras de Código

 Manter padrão pt-BR em nomes de métodos/variáveis
 Usar type hints em todas as funções
 Logging estruturado com módulo logging
 Variáveis de instância sempre no __init__()
 Sempre usar Enum para RAG (EstrategiaBusca.HIBRIDA)
 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE  para mais detalhes.

👨‍💻 Autor

Lex-Usamn
Gerente de TI | Creator Digital | Desenvolvedor

 📧 GitHub: @Lex-usamn
 🎬 YouTube: Canal Dark
 📸 Instagram: @cerne.das.coisas
 💬 Telegram: @Lex_Cerebro_bot
 🙏 Agradecimentos

 Google - Gemini 2.5 Flash API
 NVIDIA - GLM5 Fallback API
 Telegram - Bot Platform
 Python Community - Bibliotecas incríveis
   
⭐ Se este projeto foi útil, deixe uma star! ⭐

Feito com ❤️ e ☕ por Lex-Usamn

Star History Chart

Status: ~99% Completo ✨ | Última atualização: 17/04/2026

 ```  
📋 O que está incluído neste README:

SEÇÃO
 CONTEÚDO
 Header	Badges de status, provider, bot, python
Sobre	Descrição clara do projeto
Features	Tabela de comandos e recursos IA
Arquitetura	Diagrama em ASCII da estrutura de pastas
Instalação	Passo a passo completo (clone → rodar)
Fluxo	Diagrama de processamento de mensagens
API Endpoints	Tabela completa com exemplos
Métricas	Performance atual com badges
Conquistas	Checklist visual de progresso
Bugs	Tabela de problemas resolvidos
Stack	Badges coloridos das tecnologias
Links	Todos os URLs importantes
Exemplos	Conversas reais bot ↔ usuário
Contribuição	Guia para devs
Autor	Seus links e redes sociais
 
✅ Pronto para usar!

Copie todo o código acima e salve como README.md na raiz do repositório.

O README inclui:

 ✅ Badges profissionais (status, tech stack)
 ✅ Emojis para melhor visualização
 ✅ Tabelas organizadas
 ✅ Código blocos destacados
 ✅ Links clicáveis
 ✅ Seção de exemplos práticos
 ✅ Checklist de progresso visual
 ✅ Créditos e agradecimentos
 Quer que eu faça alguma alteração? Por exemplo:

 Adicionar mais seções?
 Mudar o estilo dos badges?
 Adicionar GIFs/imagens?
 Traduzir para inglês (README.en.md)?