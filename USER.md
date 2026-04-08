# 👤 USER.md - Perfil Operacional do Usuário (Lex Usamn)

**Última atualização:** 2026-04-05 por Lex Usamn  
**Próxima revisão programada:** 2026-05-05  

---

## Informações Básicas

| Campo | Valor |
| :--- | :--- |
| **Nome completo** | Lex Usamn |
| **Nome preferido** | Lex |
| **Email principal** | lex.usamn@gmail.com |
| **Fuso horário** | America/Sao_Paulo (UTC-3) |
| **Idioma nativo** | Português Brasileiro (pt-BR) |
| **Idioma técnico** | Inglês (termos TI/programação) |

---

## Preferências de Comunicação

### ✅ PREFERÊNCIAS (em ordem de prioridade):

1. **DIRETO E ACIONÁVEL (favorito)**
   - Vá direto ao ponto
   - Sempre inclua "próximo passo"
   - Use bullets/lists (não parágrafos enormes)
   - *Exemplo de formato ideal:*
     - ✓ Ideia capturada em: [local]
     - 🏷️ Tags: [tags]
     - ➡️ Próxima ação: [o que fazer agora]
2. **VISUAL/DIAGRÂMATICO (quando complexo)**
   - Use ASCII art ou mermaid diagrams se ajudar
   - Tabelas para comparar opções
   - Fluxogramas para processos
3. **EXEMPLOS PRÁTICOS (sempre que possível)**
   - Mostrar, não apenas contar
   - Código comentado
   - Templates prontos para copiar/colar
4. **CONTEXTO ANTES DE PERGUNTAR**
   - Forneça background antes de solicitar decisão
   - Apresente opções com prós/contras
   - Minimize carga cognitiva para tomada de decisão

### ❌ EVITAR:
- Parágrafos > 5 linhas (a menos que necessário)
- Linguagem ambígua ou vaga
- Perguntas abertas sem contexto
- Repetição de informações já conhecidas

### Tom e Personalidade Esperados

🗣️ **COMO QUERO QUE VOCÊ FALE COMIGO:**

**Situação normal:**
> "Lex, aqui estão suas 3 prioridades hoje:
> 1. Finalizar edição vídeo Canal Dark (2h estimado)
> 2. Responder tickets TI pendentes (45 min)
> 3. Escrever 500 words do Capítulo 3 (1 pomodoro)
>
> Sugestão: Começar pelo vídeo (deadline quinta). Quer que eu prepare o projeto no Obsidian para você?"

**Situação de urgência/crise:**
> "🚨 ALERTA: Deadline do vídeo é amanhã e você só tem 50% pronto!
> Opções:
> A) Cancelar tudo e focar só no vídeo (recomendado)
> B) Pedir extensão (arriscado)
> C) Publicar versão menor (compromisso qualidade)
> 
> Qual escolhe? Preciso de resposta em 10 min."

**Situação de celebração/vitória:**
> "🎉 PARABÉNS! Você concluiu [PROJETO]!
> Isso é progresso real. Registrando no log de conquistas...
> Quer compartilhar com alguém ou seguir para próxima tarefa?"

**Situação quando estou frustrado:**
> "Vejo que você está sob pressão. Vamos respirar.
> O que é REALMENTE importante agora? Podemos:
> • Pausar tudo por 15 min (reset mental)
> • Focar em UMA coisa só (reduzir overwhelm)
> • Delegar/adiar o que não é crítico
> 
> O que faz sentido para você agora?"

---

## Stack Tecnológico Detalhado

### Ferramentas de IA (Configuração Atual)

#### 1. Claude (Anthropic) - USO PRINCIPAL

```yaml
Modelo_Preferido: 
  - Claude 3.5 Sonnet (raciocínio complexo, coding)
  - Claude 3 Haiku (tarefas rápidas, resumos)
  - Nvidia Api gml 5 (raciocínio complexo, coding)

Uso_Principal:
  - Vibe Coding (desenvolvimento com IA)
  - Análise complexa de problemas
  - Escrita e roteirização
  - Tomada de decisões estratégicas

Integrações:
  - Claude Code CLI (terminal)
  - [API direta? Web interface?]

Prompts_Testados_Efetivos:
  - [Listar prompts que deram bom resultado]
  - [Padrões identificados]

Limitações_Observadas:
  - [Se houver]
```

#### 2. Gemini (Google) - USO SECUNDÁRIO

```yaml
Modelo_Preferido:
  - Gemini 2.5 Pro (contexto longo, multimodal)
  - Gemini Flash (rápido, barato)

Uso_Principal:
  - Pesquisa de informações
  - Análise de imagens/vídeos (multimodal)
  - Google Workspace integrations (Docs, Sheets)
  - Sumarização de conteúdos longos

Integrações:
  - [Google AI Studio? API? Vertex AI?]

Vantagens_sobre_Claude:
  - [Context window maior? Multimodal melhor?]

Quando_Preferir_Gemini:
  - [Situações específicas]
```

### Ferramentas de Produtividade

#### Obsidian (Second Brain Base)

- **Versão:** [Instalada recentemente? Qual versão?]
- **Vault_Path:** `SecondBrain_Ultimate/`
- **Plugins_Instalados:**
  - [ ] Templater (templates dinâmicos)
  - [ ] Dataview (queries em notas)
  - [ ] Obsidian Git (versionamento)
  - [ ] Local REST API (integração externa)
  - [ ] Daily Note Editor (notas diárias)
  - [ ] Calendar (visualização temporal)
- **Uso_Atual:**
  - Base de conhecimento pessoal
  - Documentação de projetos
  - Templates padronizados
- **Desejos_Futuros:**
  - [Mais plugins? Integrações?]

#### Lex Flow (Dashboard Principal)

- **URL:** https://flow.lex-usamn.com.br/
- **Tipo:** Web application (backend próprio)
- **Backend:** VM Ubuntu em servidor Proxmox
- **Funcionalidades_Utilizadas:**
  - Dashboard com métricas
  - Sistema P.A.R.A. (Projetos, Áreas, Recursos, Arquivo)
  - Caixa de Entrada (Inbox)
  - Pomodoro / Timer
  - Assistente IA integrado
  - Gamificação
  - TELOS Review (revisão sistemática)
  - Visão Gráfica (grafo de conexões)
  - Nuvem/Sync multi-dispositivo
- **Funcionalidades_Desejadas:**
  - [O que gostaria que tivesse?]
- **API_Disponível:**
  - Documentação: [Enviou .md - vou analisar]
  - Autenticação: [OAuth? Token? Session?]
  - Endpoints: [REST? GraphQL? WebSocket?]

### Ferramentas de Desenvolvimento

#### Vibe Coding Stack

- **IDE_Preferido:**
  - VS Code (atualmente em uso)
  - [Cursor? Outro?]
- **Linguagens_Principais:**
  - JavaScript/TypeScript? (frontend)
  - Python? (backend/Automation)
  - [Outras?]
- **Frameworks_Conhecidos:**
  - React/Next.js? (web frontend)
  - FastAPI/Flask? (Python backend)
  - [Outros?]
- **Versionamento:**
  - Git/GitHub? [Perfil GitHub?]
  - Branch strategy: [GitFlow? Trunk based?]
- **Deploy:**
  - Apps: [Vercel? Railway? Render? Próprio servidor?]
  - Backend Lex Flow: VM Ubuntu (Proxmox)
- **Banco_de_Dados:**
  - Desenvolvimento: SQLite (leve, local)
  - Produção: [PostgreSQL? MongoDB? Outro?]

### Ferramentas de Criação de Conteúdo

#### Edição de Vídeo

- **Software_Principal:**
  - [DaVinci Resolve]
  - [CapCut]
  
- **Formatos_Produzidos:**
  - YouTube Long-form (10-20 min)
  - Shorts/Reels (< 60 seg, vertical)
  - Twitch Clips (destaques de stream)
- **Workflow_Típico:**
  1. [Roteiro/Script]
  2. [Gravação/B-Roll]
  3. [Edição no software]
  4. [Thumbnail design]
  5. [SEO/Descrição/Tags]
  6. [Upload e programação]
- **Tempo_Medio_Por_Video:**
  - Simples: [2 horas]
  - Complexo: [4 horas]

#### Design e Imagens

- **Ferramentas:**
  - [Photoshop,Canva]
  - [nano banana, Stable Diffusion, outra IA]
  - [nehuma para UI/UX]
- **Tipos_de_Criacao:**
  - Thumbnails YouTube (clique alta conversão)
  - Posts Instagram (feed, stories)
  - Banner/Arte para canais
  - Overlays para Twitch

### Plataformas de Publicação

- **YouTube:**
  - **Canal_Atual:** https://www.youtube.com/channel/UC7naxii3igMnnYW8oMHK0jA
  - **Nicho:** Dark
  - **Subscritos_Atuais:** [4]
  - **Monetização:** [Em processo]
  - **Upload_Frequência:** 1x/semana (meta mínima)
  - **Melhor_Horário_Postar:** [Descobrir com dados]
- **Instagram:**
  - **Perfil_Influencer:** [@cerne.das.coisas]
  - **Nicho:** [noticias geek]
  - **Seguidores_Atuais:** [0]
  - **Post_Frequência:** 3x/semana
  - **Formatos:** Feed posts, Stories, Reels
- **Twitch:**
  - **Canal:** [O cerne das Coias]
  - **Stream_Frequência:** [1]
  - **Horário_Típico:** [quarta 20:00]
  - **Conteúdo:** [reacty]

---

## Metas e OKRs (Próximos 6 Meses)

### Visão Geral Estratégica (Junho - Dezembro 2026)

🎯 **VISÃO:** Transformar de "Gerente TI que cria conteúdo" para "Empresário digital com múltiplas fontes de renda"

📍 **ONDE ESTOU AGORA (Junho 2025):**
- 1 canal dark em crescimento inicial
- Influencer digital em fase de estruturação
- 2 apps em desenvolvimento (não publicados)
- Livro em rascunho inicial
- Emprego TI estável (renda principal)

🎯 **ONDE QUERO ESTAR (Dezembro 2025):**
- 3+ canais dark monetizando (renda secundária)
- Influencer digital operando com automação IA (semi-passivo)
- 2 apps publicados e com usuários (portfolio/portfólio)
- Livro com manuscrito completo (pronto para editora/self-publish)
- TI como "segurança" (não única fonte de renda)

### OKR 1: Monetização Canais Dark (PRIORIDADE MÁXIMA)

**Objetivo_OKR1:** "Ter 3+ canais dark gerando receita consistente através do YouTube Partner Program e afiliados"

**Key_Results:**
- **KR1.1:** 
  - Estratégia: "Canal 1 atingir 1,000 inscritos + 4,000 watch hours"
  - Target: "31 de Dezembro 2025"
  - Status: "Em Progresso"
  - Current_Value: "[Preencher com valor atual]"
- **KR1.2:**
  - Estratégia: "Canal 2 lançado com 10 vídeos publicados"
  - Target: "30 de Setembro 2025"
  - Status: "Em Planejamento"
- **KR1.3:**
  - Estratégia: "Canal 3 em desenvolvimento com branding definido"
  - Target: "30 de Novembro 2025"
  - Status: "Ideação"
- **KR1.4:**
  - Estratégia: "RPM médio de $2-5 por 1,000 views (benchmark nicho)"
  - Target: "Monitorar mensalmente"
  - Status: "Aguardando monetização"

**Initiatives_Planejadas:**
- Produção consistente (1 vídeo/semana mínimo)
- SEO otimizado (títulos, thumbnails, descriptions)
- Estratégia de Shorts para algoritmo
- Análise competitiva (top 10 canais nicho similar)
- Teste A/B de thumbnails e títulos
- Comunidade engajada (comments, call-to-actions)

**Bloqueios_Potenciais:**
- Tempo limitado para edição (solução: templates/batches)
- Algoritmo YouTube volátil (solução: diversificar plataformas)
- Burnout criativo (solução: banco de ideias + repurposing)

**Métricas_Chave_Acompanhar:**
- Views por vídeo (tendência)
- Taxa de retenção (audience retention)
- CTR (click-through rate) de thumbnails
- Inscritos ganhos por vídeo
- Watch time total (horas)

### OKR 2: Influencer Digital Escalável (SEGUNDA PRIORIDADE)

**Objetivo_OKR2:** "Estruturar negócio da influencer digital com automação de IA, permitindo escala sem depender 100% do tempo do Lex"

**Key_Results:**
- **KR2.1:**
  - Estratégia: "Sistema de postagem automatizada funcionando (3x/semana)"
  - Target: "31 de Agosto 2025"
  - Status: "Em Desenvolvimento"
- **KR2.2:**
  - Estratégia: "Engajamento médio de 4%+ (benchmark saudável)"
  - Target: "Monitorar mensalmente"
  - Status: "Em Progresso"
  - Current_Value: "[Valor atual se tiver]"
- **KR2.3:**
  - Estratégia: "Primeira parceria/patrocínio fechada"
  - Target: "31 de Dezembro 2025"
  - Status: "Em Planejamento"
- **KR2.4:**
  - Estratégia: "10,000 seguidores orgânicos"
  - Target: "31 de Dezembro 2025"
  - Status: "Em Progresso"
  - Current_Value: "[Valor atual]"

**Initiatives_Planejadas:**
- Definir persona e tom de voz únicos
- Criar banco de templates de posts
- Automatizar calendário editorial
- Engajar ativamente com comunidade (comments, DMs)
- Colaborar com outros creators (cross-promoção)
- Testar formatos diferentes (carrossel, reel, story)

**Bloqueios_Potenciais:**
- Algoritmo Instagram favorito a consistência (manter 3x/semana)
- Saturação de mercado de influencers (diferenciação crucial)
- Tempo de criação vs. qualidade (automatizar sem perder autenticidade)

**Métricas_Chave_Acompanhar:**
- Reach (alcance orgânico)
- Engagement rate (likes + comments + saves / reach)
- Profile visits (tráfego para bio)
- Link clicks (se tiver link em bio)
- Story views e completion rate

### OKR 3: Apps em Desenvolvimento (TERCEIRA PRIORIDADE)

**Objetivo_OKR3:** "Publicar 2+ aplicações funcionais, demonstrando capacidade técnica e gerando portfolio/portfólio"

**Key_Results:**
- **KR3.1:**
  - Estratégia: "App 1 em produção com usuários reais"
  - Target: "30 de Setembro 2025"
  - Status: "Em Desenvolvimento"
  - App_Name: "[Nome do app 1]"
  - Descricao: "[O que faz? Para quem?]"
  - Tech_Stack: "[Tecnologias usadas]"
- **KR3.2:**
  - Estratégia: "App 2 em beta testing com feedback initial"
  - Target: "30 de Novembro 2025"
  - Status: "Em Desenvolvimento"
  - App_Name: "[Nome do app 2]"
  - Descricao: "[O que faz? Para quem?]"
  - Tech_Stack: "[Tecnologias usadas]"

**Initiatives_Planejadas:**
- Definir MVP mínimo viável para cada app
- Implementar com Vibe Coding (Claude como pair programmer)
- Testes intensivos (unitários + integração + user)
- Deploy em plataforma acessível (free tier inicial)
- Coletar feedback early adopters
- Iterar rapidamente baseado em uso real

**Bloqueios_Potenciais:**
- Scope creep (feature creep - controlar adição de features)
- Perfectionism (lançar imperfeito > perfeito nunca)
- Tempo limitado (dedicar blocos específicos para coding)

**Métricas_Chave_Acompanhar:**
- Features completas vs. planejadas (%)
- Bugs abertos vs. resolvidos
- Uptime/disponibilidade (se online)
- Users ativos (se aplicável)
- Performance (tempo de resposta)

### OKR 4: Livro Escrito (QUARTA PRIORIDADE)

**Objetivo_OKR4:** "Completar manuscrito do livro com qualidade publicável"

**Key_Results:**
- **KR4.1:**
  - Estratégia: "Estrutura completa (sumário, capítulos definidos)"
  - Target: "31 de Julho 2025"
  - Status: "Em Progresso"
- **KR4.2:**
  - Estratégia: "80% dos capítulos com primeiro rascunho"
  - Target: "31 de Outubro 2025"
  - Status: "Em Progresso"
  - Current_Value: "[X% completo]"
- **KR4.3:**
  - Estratégia: "Manuscrito completo pronto para revisão"
  - Target: "15 de Dezembro 2025"
  - Status: "Em Progresso"

**Informações_do_Livro:**
- **Título_Provisório:** "[Título?]"
- **Gênero:** "[Ficção/Não-ficção/Técnico?]"
- **Tema_Central:** "[Sobre o que é?]"
- **Público_Alvo:** ["[Quem leria?]"]
- **Palavras_Estimadas:** "[40k? 60k? 80k?]"
- **Capítulos_Planejados:** "[Número?]"

**Initiatives_Planejadas:**
- Definir estrutura e sumário detalhado
- Estabelecer rotina de escrita (ex: 500 words/dia)
- Usar IA como coautor (brainstorming, expansão, revisão)
- Escrever em sprints (bloco focado, não esporádico)
- Revisar por seções (não esperar terminar tudo)

**Bloqueios_Potenciais:**
- Bloqueio de escritor (writer's block)
- Priorização baixa vs. outros projetos urgentes
- Perfeccionismo (editar enquanto escreve)

**Métricas_Chave_Acompanhar:**
- Palavras escritas por sessão
- Capítulos completos (rascunho vs. revisado)
- Dias consecutivos escrevendo (streak)
- Meta mensal de palavras atingida

### OKR 5: Excelência em TI (MANUTENÇÃO - Não inovação)

**Objetivo_OKR5:** "Manter excelência na gestão de TI do supermercado, garantindo estabilidade sem comprometer outros projetos"

**Key_Results:**
- **KR5.1:**
  - Estratégia: "99% uptime de servidores críticos"
  - Target: "Mensal contínuo"
  - Status: "Operacional"
- **KR5.2:**
  - Estratégia: "Tickets resolvidos em < 24h (críticos < 4h)"
  - Target: "Mensal contínuo"
  - Status: "Operacional"
- **KR5.3:**
  - Estratégia: "Zero security incidents graves"
  - Target: "Trimestral"
  - Status: "Operacional"

**Observações:**
> Este OKR é de MANUTENÇÃO, não crescimento.
> O objetivo é manter padrão alto sem drenar energia mental.
> Automatizar o máximo possível (monitoramento, backups, alerts).

**Métricas_Chave_Acompanhar:**
- Server uptime %
- Ticket resolution time
- Security audit results
- Backup success rate

---

## Integrações e Automações Desejadas

### Monitoramento Proativo (Heartbeat System)

**Alertas_Configurados:**

- **CRÍTICOS (Notificação Imediata):**
  - Servidor Proxmox down ou crítico
  - Deadline vencida ou < 4 horas restantes
  - Perda de dados risco (backup falhou)
  - Security breach detectado
  - App em produção com erro crítico

- **ALTOS (Notificação < 1 hora):**
  - Projeto parado > 5 dias (qualquer projeto ativo)
  - Métricas canal caindo > 30% (views, inscritos)
  - Inbox com > 30 itens não processados
  - Bug crítico reportado por usuário (se app publicado)

- **MÉDIOS (Próximo Heartbeat - 30min):**
  - Projeto parado 3-5 dias
  - Métricas canal caindo 15-30%
  - Conteúdo atrasado 1-2 dias
  - Inbox 15-30 itens
  - Hábito não cumprido 2-3 dias seguidos

- **BAIXOS (Log only, não notificar):**
  - Hábito não cumprido 1 dia
  - Progresso levemente abaixo do esperado
  - Sugestões de otimização/oportunidade
  - Insights interessantes (mas não urgentes)

### Rotinas Automáticas Programadas

**Diárias (Daily Routines):**
- **08:00 - Daily Reflection**:
  - **Ação:** Curadoria de memórias, extrair lições
  - **Output:** Atualiza MEMORY.md, daily log
- **09:00 - Morning Briefing**:
  - **Ação:** Resumo do dia, prioridades, agenda
  - **Output:** Mensagem no Telegram/Dashboard
- **13:00 - Midday Check**:
  - **Ação:** Verificar progresso manhã, ajustar tarde
  - **Output:** Breve update se necessário
- **18:00 - End of Day Summary**:
  - **Ação:** Resumo conquistas, pendências para amanhã
  - **Output:** Log diário completo
- **22:00 - Tomorrow Planning**:
  - **Ação:** Preparar plano para amanhã, capturar ideias late
  - **Output:** Lista de tarefas priorizada

**Semanais (Weekly - TELOS Review adaptado):**
- **Domingo 10:00 - Weekly Review**:
  - **Ação:** Revisão completa semana, ajuste prioridades
  - **Output:** Relatório semanal, plano próxima semana

**Mensais (Monthly):**
- **Dia 1 - Monthly Archive**:
  - **Ação:** Arquivar projetos concluídos, limpar obsolete
  - **Output:** Sistema limpo e otimizado

**Trimestrais (Quarterly):**
- **Início trimestre - Strategic Review**:
  - **Ação:** Revisar OKRs, avaliar sistema, planejar evolução
  - **Output:** Documento estratégico atualizado

---

## Restrições e Limitações Claras

### O que o Second Brain NUNCA Deve Fazer Autonomamente

**Finanças:**
- NÃO realizar gastos em nome do Lex
- NÃO tomar decisões de investimento
- PODE sugerir baseado em dados, mas SEMPRE pedir aprovação

**Conteúdo_Publicável:**
- NÃO publicar nada sem revisão prévia do Lex
- PODE criar rascunhos, drafts, sugestões
- DEVE aguardar explícita aprovação antes de postar/upload

**Infraestrutura_Crítica:**
- NÃO alterar configurações de produção sem alertar
- NÃO deletar dados ou backups
- PODE sugerir mudanças, mas implementar só com confirmação

**Comunicação_Externa:**
- NÃO enviar emails/mensagens em nome do Lex
- PODE preparar rascunhos para Lex revisar e enviar
- EXCEÇÃO: Mensagens operacionais do próprio sistema (logs, alerts)

**Privacidade:**
- NÃO expor dados pessoais em logs públicos
- NÃO compartilhar informações sensíveis (TI supermercado)
- NÃO armazenar credenciais em texto plano

### Preferências de Privacidade

**Dados_Que_Podem_Ser_Armazenados:**
- Ideias e notas pessoais (no vault local)
- Métricas de performance (anônimas/agregadas)
- Histórico de decisões e lições aprendidas
- Templates e pads personalizados

**Dados_Que_Devem_Ser_Protegidos:**
- Credenciais de acesso (senhas, tokens, API keys)
- Informações corporativas (TI supermercado)
- Dados pessoais identificáveis (PII)
- Informações financeiras específicas
- Conversas privadas (DMs, emails pessoais)

**Local_de_Armazenamento_Preferido:**
- PRIMEIRA opção: Local (Obsidian vault, SQLite)
- SEGUNDA opção: VM própria (Lex Flow backend)
- TERCEIRA opção: Criptografado na nuvem (se necessário sync)
- NUNCA: Serviços de terceiros sem criptografia

---

## Gatilhos e Comportamentos a Monitorar

### Sinais de Produtividade Alta (Reforçar Positivamente)

✅ **Detectar quando:**
- Múltiplas tarefas concluídas em sequência
- Projeto avançou significativamente (> 10% em um dia)
- Bloom de ideias criativas (muitas capturas em pouco tempo)
- Feedback positivo recebido (clientes, audience, chefe)

**AÇÃO:** 
- Celebrar e registrar vitória
- Identificar o que possibilitou (replicar)
- Sugerir pausa merecida após maratona produtiva

### Sinais de Procrastinação (Intervenção Gentil)

⚠️ **Detectar quando:**
- Projeto principal sem atividade > 3 dias
- Muitas capturas no inbox mas nenhum processamento
- Início de novos projetos sem fechar antigos
- Padrão de "vou fazer amanhã" recorrente

**AÇÃO:**
- Perguntar gentilmente: "O que está impedindo avanço em [PROJETO]?"
- Oferecer quebrar em micro-tarefa absurdamente pequena
- Sugerir técnica Pomodoro (25 min só)
- Lembrar o "porquê" (motivação conectada à meta maior)

---

## Evolução e Manutenção deste Arquivo

### Quando Atualizar

**ATUALIZAR IMEDIATAMENTE SE:**
- Mudança de emprego ou função principal
- Novo projeto significativo iniciado
- Mudança em stack tecnológica principal
- Alteração em metas/OKRs
- Mudança em preferências de comunicação
- Nova ferramenta crítica adotada

**REVISAR MENSALMENTE:**
- Ainda reflete quem você é?
- Preferências mudaram?
- Metas ainda relevantes?
- Alguma integração nova disponível?

**ARQUIVAR/VERSIONAR:**
- Manter histórico de versões (git)
- Permitir rollback se necessário
- Documentar razão de mudanças grandes

### Como Solicitar Alterações

Para atualizar este arquivo, Lex pode:

1. **Dizer explicitamente:**
   *"Atualize meu USER.md: agora uso X ao invés de Y"*

2. **Corrigir quando eu errar:**
   *"Errado, prefiro que você faça Z"*

3. **Adicionar informações novas:**
   *"Adicione ao meu perfil: [nova info]"*

Eu (O Second Brain) devo:
- Confirmar a alteração
- Implementar no arquivo
- Registrar data e motivo da mudança
- Ajustar comportamento futuro baseado na nova info
