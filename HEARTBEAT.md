# 💓 HEARTBEAT.md - Checklist de Monitoramento Proativo

**Executa:** A cada 30 minutos (8:00 AM - 10:00 PM)  
**Custo estimado:** ~$0.05/execução (API calls)  
**Ação:** Gather APIs → Claude Reasoning → Notify (Telegram/Dashboard)  
**Status:** [CONFIGURAÇÃO INICIAL - Ajustar thresholds após 1 semana de uso]

---

## 🎯 PROPÓSITO DO HEARTBEAT

O Heartbeat é o sistema nervoso autônomo do seu Second Brain. Enquanto você trabalha, dorme ou descansa, ele monitora proativamente:

- ✅ Saúde dos projetos (estão parados? avançando?)
- ✅ Cumprimento de metas (conteúdo postado? hábitos mantidos?)
- ✅ Métricas de performance (canais crescendo? caindo?)
- ✅ Organização do sistema (inbox explodiu? arquivos perdidos?)
- ✅ Oportunidades (tendências? ideias para explorar?)

**Filosofia:** Prevenir é melhor que remediar. O Heartbeat detecta problemas ANTES que eles se tornem crises.

---

## ⚙️ CONFIGURAÇÃO TÉCNICA

### Frequência e Janela de Operação
- **Intervalo:** 30 minutos
- **Horario_Inicio:** "07:00" (Começa de manhã)
- **Horario_Termino:** "21:00" (Para à noite - respeita descanso)
- **Timezone:** "America/Sao_Paulo"
- **Dias_Ativos:** Segunda a Domingo (todos os dias)
- **Excecoes:**
  - Feriados: [Reduzir para 1h intervalo]
  - Férias: [Modo baixa atividade - só críticos]

### Método de Execução

**Ambiente_Local (MacOS/Windows):**
- Ferramenta: Task Scheduler (Windows) / launchd (MacOS)
- Script: `heartbeat.py` (Python)
- Trigger: A cada 30 minutos
  
**Ambiente_Remoto (VM Ubuntu - Futuro):**
- Ferramenta: Cron jobs
- Script: `heartbeat_remote.py`
- Trigger: `*/30 * * * *`
  
**Log_de_Execucao:**
- Arquivo: `logs/heartbeat_[DATE].log`
- Level: INFO (normal) / WARNING (alerts) / ERROR (falhas)
- Retencao: 7 dias (rotacionar)

---

## 🔍 CHECKLIST DE MONITORAMENTO (O QUE VERIFICAR)

### 📊 CATEGORIA 1: PROJETOS ATIVOS (CRÍTICO - Prioridade Máxima)

#### [ ] 1.1 Verificar Projetos Parados (Stalled Projects Detection)

**Threshold:** 
- Amarelo: Parado 3-5 dias (WARNING)
- Vermelho: Parado > 5 dias (CRITICAL)
  
**O_que_verificar:**
- Data da última modificação em cada pasta de projeto ativo
- Última entrada no diario/log do projeto
- Tasks marcadas como "doing" há muito tempo
  
**Acao_se_detectado:**
- **Amarelo:**
  - Log no daily: "Projeto [X] parado há Y dias"
  - Sugestão: "Próxima ação possível: [baseado no plano.md do projeto]"
  - Notificação: No próximo heartbeat summary (não imediato)
- **Vermelho:**
  - ALERTA IMEDIATO via notification preferida
  - Mensagem: "🚨 PROJETO PARADO: [NOME] está sem atividade há X dias!"
  - Contexto: "Última ação: [data]. Plano diz: [próximo passo]"
  - Call-to-action: "Quer que eu te ajude a retomar agora? (Sim/Não)"
    
**Exclusoes:**
- Projetos deliberadamente pausados (marcar como "paused" no status)
- Projetos esperando dependência externa (marcar como "blocked")
- Férias/ausência programada do Lex

#### [ ] 1.2 Verificar Deadlines Próximas (Upcoming Deadlines)

**Threshold:**
- Vermelho: < 24 horas restantes
- Amarelo: 24-48 horas restantes
- Azul: 48-72 horas restantes (info only)
  
**Fontes_de_deadlines:**
- Tags em projetos: `#deadline:[DATA]`
- Calendário Google (quando integrado)
- Tarefas com due date no Lex Flow
- Métricas de posting (ex: "vídeo toda sexta")
  
**Acao_se_detectado:**
- **"< 24h":**
  - "🔴 URGENTE: Deadline [PROJETO/TAREFA] vence em X horas!"
  - Checklist: "O que falta para entregar? [listar]"
  - Sugestão de priorização: "Focar nisto AGORA e pausar resto"
- **"24-48h":**
  - "⚠️ ATENÇÃO: Deadline [PROJETO] em X horas"
  - "Status atual: Y%. Quer revisar prioridades?"

#### [ ] 1.3 Verificar Progresso Semanal (Weekly Velocity)

**Metrica:** Compara Progresso segunda-feira vs. hoje (dia atual)
  
**Threshold:**
- Bom: > 20% de avanço em projetos prioritários na semana
- Atenção: 10-20% de avanço
- Crítico: < 10% de avanço (semana estagnada)
  
**Acao_se_baixo:**
- "📉 ALERTA: Progresso esta semana está abaixo do esperado."
- "Avançamos X% (meta era Y%)."
- "Possíveis causas:"
  - "- Muitos projetos simultâneos? (WIP limit exceeded)"
  - "- Bloqueios não resolvidos?"
  - "- Falta de foco/procrastinação?"
- "Sugestão: Quer que eu te ajude a repriorizar?"

---

### 🎬 CATEGORIA 2: CANAIS DARK E INFLUENCER (PRIORITÁRIA)

#### [ ] 2.1 Métricas de YouTube (Canal Dark Principal)

**Requer:** YouTube Data API habilitada (status: AGUARDANDO - canal não monetizado ainda)

**Metricas_monitorar:**
- **Inscritos:**
  - Threshold_Amarelo: Crescimento < 5/semana (abaixo do baseline)
  - Threshold_Vermelho: Perda líquida de inscritos (unsubs > subs)
- **Views (últimos 7 dias):**
  - Threshold_Amarelo: Queda > 20% vs. média 4 semanas anteriores
  - Threshold_Vermelho: Queda > 40% vs. média
- **Watch Time (horas):**
  - Threshold: Monitorar tendência (subindo/estável/caindo)
- **Performance_Videos_Recentes:**
  - Top 3 vídeos últimos 30 dias:
    - Comparar CTR (click-through rate) vs. canal average
    - Comparar Retention (audiência retention) vs. average
      
**Acao_se_anomalia:**
- "📺 MÉTRICA ALERTA: [métrica] apresentou [queda/aumento] de X%"
- "Contexto: [comparação histórica]"
- "Possíveis causas:"
  - "- Algoritmo sazonal?"
  - "- Thumbnail/título fraco?"
  - "- Nicho saturado?"
  - "- Falta de consistência posting?"
- "Sugestão: [ação baseada em causa provável]"
  
**Frequencia:** Verificar métricas 2x ao dia (manhã + tarde) quando API disponível

#### [ ] 2.2 Métricas de Instagram (Influencer)
**Requer:** Instagram Graph API (status: COMPLEXO - requer Facebook Business verification)

**Metricas_monitorar (quando disponíveis):**
- **Seguidores:**
  - Threshold: Crescimento líquido positivo (meta: +50/semana)
- **Engagement Rate:**
  - Threshold_Bom: > 3% (saudável para niche)
  - Threshold_Atencao: 1-3%
  - Threshold_Baixo: < 1%
- **Reach (Alcance orgânico):**
  - Threshold: Monitorar vs. posts anteriores
- **Stories/Reels performance:**
  - Metricas: Completion rate, taps back, shares
    
**Alternativa_enquanto_sem_API:**
- Check manual periódico (pedir ao Lex verificar 1x/semana)
- Screenshots salvas no Inbox para análise posterior
- Estimativas baseadas em likes/comments (impreciso mas melhor que nada)

#### [ ] 2.3 Calendário Editorial (Content Schedule Compliance)

**Regras_posting:**
- **Canal_Dark_YouTube:**
  - Frequencia: Mínimo 1 vídeo/semana
  - Dia_preferido: [Definir - sexta? sábado?]
  - Horario_preferido: [Definir baseado em dados]
- **Influencer_Instagram:**
  - Frequencia: 3x posts/semana (mínimo)
  - Distribuicao: [Segunda/Quarta/Sexta? ou outro padrão]
  - Stories: Diário (1-3 por dia em horários variados)
    
**Verificacao:**
- **Hoje_tem_conteudo_programado?**
  - Sim: ✅ Ok (nada a fazer)
  - Não: 
    - Se deadline hojé: 🔴 URGENTE - "Conteúdo [TIPO] não postado!"
    - Se deadline amanhã: 🟡 ATENÇÃO - "Amanhã: [CONTEÚDO] previsto"
    - Se deadline > 48h: ℹ️ Info only - "Lembrete: [DATA] - [CONTEÚDO]"
      
**Acao_se_atrasado:**
- "📅 CONTEÚDO ATRASADO: [Tipo] para [Plataforma]"
- "Deveria ter sido postado: [Data/Hora]"
- "Usar template: [link para template correspondente]"
- "Tempo estimado para produzir: [X min/horas]"
- "Quer que eu te ajude a criar agora? (Sim/Não/Depois)"

---

### 💻 CATEGORIA 3: APPS E DESENVOLVIMENTO

#### [ ] 3.1 Commit Activity (Atividade de Código)
**O_que_verificar:**
- Último commit em cada repositório de app ativo
- Issues/PRs abertos sem atividade recente
- Branches "feature" paradas há muito tempo
  
**Threshold:**
- Amarelo: Sem commit > 2 dias (para apps em desenvolvimento ativo)
- Vermelho: Sem commit > 5 dias (app possivelmente abandonado)
  
**Acao_se_detectado:**
- "💻 APP [NOME]: Sem atividade de código há X dias"
- "Último commit: [message] - [data]"
- "Issues abertas: [número] (destacar se > 3)"
- "Branch ativas: [listar]"
- "Bloqueio identificado?"
  - "- Sim: Qual? [se souber]"
  - "- Não: Sugestão: 'Fazer 1 commit pequeno agora (25 min)'"

#### [ ] 3.2 Issues e Bugs

**Verificar:**
- Issues_abertas: Quantidade total
- Bugs_criticos: Prioridade high/urgent sem resolução > 24h
- Stale_issues: Abertas > 7 dias sem comentários
  
**Threshold:**
- Critico: Bug em produção (se app published) > 4h sem atenção
- Alto: Bug crítico em dev > 24h sem atenção
- Medio: Issue qualquer > 7 dias sem update
  
**Acao:**
- "🐛 ISSUE #[N]: '[Título]' está sem atenção há X horas"
- "Prioridade: [alta/media/baixa]"
- "Sugestão: [se óbvio, senão perguntar]"

---

### 🖥️ CATEGORIA 4: INFRAESTRUTURA TI (SUPERMERCADO)

#### [ ] 4.1 Saúde Servidores (Proxmox)

**Requer:** Proxmox API (status: BAIXA PRIORIDADE - configurar depois)

**Metricas_se_integrado:**
- VMs_status: Todas running? (alguma down?)
- CPU/Memory/Disco: Usage > 80%? (alerta capacity)
- Backups: Último backup executado com sucesso? (24h)
- Network: Latency/packet loss anormal?
  
**Alternativa_se_sem_API:**
- Check manual pelo Lex (pedir 1x/dia ou 1x/semana)
- Monitoramento básico via ping/simple scripts
- Alertas por email do próprio Proxmox (se configurado)
  
**Acao_se_problema:**
- "🖥️ INFRA ALERTA: [Servidor/VM] apresentando [problema]"
- "Detalhes: [métricas específicas]"
- "Impacto: [usuários afetados? serviços críticos?]"
- "Ação sugerida: [passos para diagnosticar/resolver]"

#### [ ] 4.2 Tickets e Pendências TI

**Fontes:**
- Sistema de tickets do supermercado (se tiver)
- Email de suporte
- Lista manual no Obsidian/Lex Flow
  
**Verificar:**
- Tickets_abertos: Quantidade
- Tickets_criticos: SLA prestes a vencer (< 4h)
- Tickets_velhos: Abertos > 48h sem resolução
  
**Acao_se_crítico:**
- "🎫 TICKET CRÍTICO: #[N] - '[Assunto]'"
- "SLA vence em: X horas"
- "Atribuído a: [se applicable]"
- "Sugestão: Priorizar agora"

---

### 📥 CATEGORIA 5: ORGANIZAÇÃO E HIGIENE DO SISTEMA

#### [ ] 5.1 Tamanho do Inbox

**Threshold:**
- Verde: < 10 itens (ótimo)
- Amarelo: 10-20 itens (aceitável, processar em breve)
- Vermelho: 20-30 itens (processar URGENTE)
- Crítico: > 30 itens (system overload - parar tudo e processar)
  
**Acao_se_threshold:**
- **"10-20":** 
  - "📥 Inbox com X itens. Sugestão: Processar nos próximos 30 min."
- **"20-30":**
  - "📥📥 Inbox CHEIO: X itens! Hora de processar (15-30 min)."
  - "Aplicar regra 2-minutos: se rápido, faça agora."
- **"> 30":**
  - "🚨📥📥 INBOX CRÍTICO: X itens! Sistema sobrecarregado!"
  - "AÇÃO OBRIGATÓRIA: Pausar tudo e processar inbox AGORA."
  - "Tempo estimado: 45-60 min para zerar."

#### [ ] 5.2 Arquivos Órfãos (Fora de Estrutura)

**Verificar:**
- Arquivos na raiz do vault que não deveriam estar lá
- Pastas soltas sem pertencer a P/A/R/A
- Duplicatas de documentos
  
**Acao:**
- "📁 ARQUIVO ÓRFÃO detectado: '[nome]' em [local]"
- "Sugestão de destino: [Projetos/Áreas/Recursos/Arquivo]"
- "Quer que eu mova? (Sim/Não/Mostrar opções)"

#### [ ] 5.3 Integridade dos Arquivos Core

**Verificar_diariamente:**
- `SOUL.md` existe e não está corrompido?
- `USER.md` atualizado (última edição < 30 dias)?
- `MEMORY.md` tamanho razoável (< 100KB)?
- `HEARTBEAT.md` sendo executado (last run < 1h)?
  
**Acao_se_problema:**
- "⚠️ ARQUIVO CORE PROBLEMA: [arquivo]"
- "Issue: [corrompido/grande demais/atualizado antigo]"
- "Ação: [backup restore/compactar/atualizar]"

---

### 📚 CATEGORIA 6: APRENDIZADO E CRESCIMENTO PESSOAL

#### [ ] 6.1 Hábitos Diários (Habit Tracking)

**Habitos_para_monitorar** (personalizar conforme Lex definir):
*(Exemplos genéricos - SUBSTITUIR pelos reais)*
  
```yaml
habit_leitura:
  Nome: "Leitura/Estudo"
  Meta_diaria: 30 min
  Tracking: [Sim/Não] + duração se sim
  
habit_exercicio:
  Nome: "Exercício Físico"
  Meta_diaria: Feito (binary)
  Tracking: Checkbox
  
habit_meditacao:
  Nome: "Meditação/Descanso Mental"
  Meta_diaria: 10 min
  Tracking: [Sim/Não]
  
habit_escrita_livro:
  Nome: "Escrita do Livro"
  Meta_diaria: 250 words
  Tracking: Contagem de palavras
  
habit_coding:
  Nome: "Vibe Coding (Apps)"
  Meta_diaria: 1 pomodoro (25 min)
  Tracking: Duração ou commits
```
    
**Threshold_para_alerta:**
- Habito_nao_cumprido: 1 dia → Info only (log)
- Habito_nao_cumprido: 2 dias → Warning (lembrar gentilmente)
- Habito_nao_cumprido: 3+ dias → Attention (possível padrão problemático)
  
**Apos_3_dias_seguidos:**
- "💪 HÁBITO EM RISCO: '[Nome]' não praticado há 3 dias"
- "Meta: [meta diária]"
- "Benefício de manter: [por que é importante]"
- "Barreira identificada: [se souber - tempo, energia, esquecimento?]"
- "Sugestão: Micro-versão hoje? (ex: 5 min ao invés de 30 min)"

#### [ ] 6.2 Meta de Aprendizado (Learning Goals)

**Meta_atual** (exemplo - SUBSTITUIR):
- Curso/Skill: [Nome]
- Plataforma: [Udemy/Coursera/Livro/YouTube]
- Progresso_alvo: % ou módulos por mês
- Progresso_atual: [trackar]
  
**Verificacao:** Semanal (não diário - evitar overload)
  
**Acao_se_atrasado:**
- "📚 APRENDIZADO ATRASADO: [Curso/Skill]"
- "Meta mensal: X% | Atual: Y%"
- "Sugestão: Bloco de 30 min hoje? (Sim/Agendar para semana)"

---

## 🔔 SISTEMA DE NOTIFICAÇÕES

### Níveis de Urgência e Canais

**NIVEL_1_CRITICO (Vermelho 🔴):**
- **Condicoes:**
  - Servidor/produto down
  - Deadline vencida ou < 4h
  - Perda de dados risco iminente
  - Security breach
  - Inbox > 30 itens (system paralysis)
- **Canais_notificacao:**
  - IMEDIATO: Todas as interfaces ativas
    - Telegram (se bot ativo)
    - Toast notification (desktop)
    - Dashboard Lex Flow (badge vermelho)
    - Email (se crítico extremo)
- **Frequencia:** Imediata (na mesma execução do heartbeat)
- **Repeticao:** A cada heartbeat até resolvido (max 6x, depois escalation)

**NIVEL_2_ALTO (Amarelo 🟡):**
- **Condicoes:**
  - Projeto parado > 5 dias
  - Métricas canal -30%+
  - Deadline 24-48h
  - Bug crítico em produção
  - Inbox 20-30 itens
  - Hábito 3+ dias sem practicing
- **Canais_notificacao:**
  - PRINCIPAL: Telegram (summary batch)
  - SECUNDARIO: Dashboard Lex Flow
  - OPÇÃO: Toast (se no PC)
- **Frequencia:** Na próxima execução do heartbeat (até 30 min delay)
- **Repeticao:** Max 2x por dia (não spam)

**NIVEL_3_MEDIO (Verde 🟢):**
- **Condicoes:**
  - Projeto parado 3-5 dias
  - Métricas -15 a -20%
  - Conteúdo atrasado 1 dia
  - Inbox 15-20 itens
  - Issue sem atenção 2-3 dias
- **Canais_notificacao:**
  - Dashboard Lex Flow (log only)
  - Daily summary (incluído no briefing 8AM ou 18PM)
- **Frequencia:** Incluir no próximo resumo diário
- **Repeticao:** Não repetir (só no summary)

**NIVEL_4_BAIXO (Azul 🔵):**
- **Condicoes:**
  - Hábito não cumprido 1-2 dias
  - Progresso levemente abaixo
  - Sugestões de otimização
  - Insights interessantes (não urgentes)
  - Informações puramente informativas
- **Canais_notificacao:**
  - Log file only (`heartbeat.log`)
  - Disponível se perguntado (`/log heartbeat`)
- **Frequencia:** Registrar, não notificar proativamente
- **Repeticao:** Nunca (a menos que solicitado)

### Formato das Mensagens de Notificação

**Template_ALERTA_CRITICA:**
```text
🚨 [CATEGORIA] - [TÍTULO CURTO]

📊 Detalhes: [dados específicos]
⏰ Detectado: [timestamp]
📍 Contexto: [informação relevante]
➡️ Ação sugerida: [passo concreto]
❓ Precisa de ajuda? Responda 'sim' ou ignore.
```

**Template_RESUMO_DIARIO (8 AM / 6 PM):**
```text
☀️🌙 [Manhã/Noite] Briefing - [DATA]

📌 PRIORIDADES HOJE:
1. [Prioridade 1]
2. [Prioridade 2]
3. [Prioridade 3]

📈 MÉTRICAS RÁPIDAS:
• Projetos ativos: [X] ([Y] parados)
• Inbox: [Z] itens
• Hábitos: [cumpridos]/[total]

⚠️ ALERTAS (se houver):
- [Alerta 1 se existir]
- [Alerta 2 se existir]

💡 INSIGHT DO DIA:
[Insight interessante ou motivação]

🎯 Foco no que importa. Você consegue! 💪
```

---

## 📊 RELATÓRIO DE EXEMPLO (Output Format do Heartbeat)

```json
{
  "heartbeat_id": 142,
  "timestamp": "2025-06-17T14:30:00",
  "execution_time_ms": 1250,
  "status": "success",
  
  "checks_performed": {
    "projects_stalled": {
      "total_projects_active": 5,
      "projects_stalled_3_5_days": 1,
      "projects_stalled_over_5_days": 0,
      "details": [
        {
          "project": "PROJ_Livro_Escrita",
          "days_stalled": 4,
          "last_activity": "2025-06-13",
          "severity": "yellow",
          "suggested_action": "Escrever 250 words do Capítulo 3 (ver plano.md)"
        }
      ]
    },
    
    "upcoming_deadlines": {
      "deadlines_24h": 1,
      "deadlines_48h": 0,
      "details": [
        {
          "item": "Vídeo Canal Dark #1",
          "deadline": "2025-06-18T20:00:00",
          "hours_remaining": 29.5,
          "project": "PROJ_CanalDark_01",
          "severity": "red"
        }
      ]
    },
    
    "content_schedule": {
      "youtube_due_today": true,
      "youtube_status": "overdue",
      "instagram_posts_this_week": 2,
      "instagram_target": 3,
      "instagram_status": "behind"
    },
    
    "metrics_youtube": {
      "status": "api_not_available",
      "message": "Aguardando habilitação YouTube API"
    },
    
    "development_activity": {
      "app1_last_commit": "2025-06-16",
      "app1_days_since_commit": 1,
      "app2_last_commit": "2025-06-14",
      "app2_days_since_commit": 3,
      "app2_stalled_warning": true
    },
    
    "inbox_size": {
      "total_items": 17,
      "status": "yellow",
      "message": "Processar nos próximos 30 min"
    },
    
    "habits_today": {
      "reading": {"done": true, "duration_min": 35},
      "exercise": {"done": false},
      "coding": {"done": true, "duration_min": 45},
      "writing_book": {"done": false, "words_written": 0}
    }
  },
  
  "alerts_generated": [
    {
      "level": "red",
      "type": "content_overdue",
      "channel": "youtube",
      "message": "Vídeo Canal Dark #1 atrasado (deadline amanhã 20h)",
      "suggested_action": "Usar template roteiro-dark-template.md para agilizar"
    },
    {
      "level": "yellow",
      "type": "project_stalled",
      "project": "PROJ_Livro_Escrita",
      "message": "Livro parado há 4 dias",
      "suggested_action": "Micro-commitment: 250 words agora (15 min)"
    },
    {
      "level": "yellow",
      "type": "development_slow",
      "project": "App 2",
      "message": "App 2 sem commit há 3 dias",
      "suggested_action": "Fazer 1 small commit ou issue update"
    }
  ],
  
  "actions_taken": [
    "Logged to heartbeat_2025-06-17.log",
    "Updated project statuses in memory",
    "Sent critical alert to Telegram (1 message)",
    "Updated Lex Flow dashboard badges (3 items)",
    "Queued yellow alerts for next daily summary"
  ],
  
  "next_scheduled_run": "2025-06-17T15:00:00",
  "recommendation": "Focar no vídeo do canal dark (deadline crítico). Livro pode esperar 1 dia."
}
```

---

## ⚙️ AJUSTES E CALIBRAÇÃO (Pós-Setup)

### Primeira Semana de Uso (Calibração)

- **Dia_1-2:**
  - Observar falsos positivos (alertas desnecessários)
  - Ajustar thresholds se muitas notificações
  - Verificar se está detectando o que deveria
- **Dia_3-4:**
  - Avaliar se frequência de 30min é adequada (muito? pouco?)
  - Testar diferentes níveis de urgência (sentiu falta de algum alerta?)
  - Verificar consumo de API/custos
- **Dia_5-7:**
  - Consolidar configuração final
  - Documentar o que funcionou/não funcionou
  - Preparar para segunda semana (operação normal)

### Sinais de que Precisa Ajustar

- **Muitas_Notificacoes (Alarm Fatigue):**
  - Sintoma: Começando a ignorar alerts
  - Acao: Aumentar thresholds ou reduzir frequency
- **Poucas_Notificacoes (False Security):**
  - Sintoma: Problemas acontecem sem ser detectados
  - Acao: Diminuir thresholds ou adicionar checks
- **Alertas_Irrelevantes:**
  - Sintoma: Mesmo tipo de alerta repetido que ignora
  - Acao: Adicionar exceção ou ajustar lógica de detecção
- **Custo_Alto:**
  - Sintoma: Consumo de API acima do esperado
  - Acao: Otimizar queries, cache results, reduzir frequency

---

## 🔧 MANUTENÇÃO E TROUBLESHOOTING

### Problemas Comuns

- **Heartbeat_nao_roda:**
  - Verificar: Task Scheduler / Cron job ativo?
  - Verificar: Python environment correto?
  - Verificar: Logs de erro em `logs/`
  - Solucao: Reiniciar serviço, verificar permissões
- **Falsos_positivos_frequentes:**
  - Causa: Thresholds muito apertados
  - Solucao: Aumentar limites em 20-50%
- **API_errors:**
  - Causa: Rate limit, network, auth expired
  - Solucao: Retry logic, exponential backoff, refresh tokens
- **Performance_lenta:**
  - Causa: Muitos checks, queries pesadas
  - Solucao: Paralelizar, cache, reduzir scope

### Backup e Restore

- **Backup_configuracao:**
  - Arquivo: `config/heartbeat_config.yaml`
  - Frequency: Semanal (parte do backup geral)
  - Versionar: Git (junto com todo o segundo cérebro)
- **Restore_se_necessario:**
  - Parar heartbeat atual
  - Restaurar config do backup
  - Reiniciar serviço
  - Verificar logs pós-restart

---

> Este arquivo define o sistema nervoso autônomo do seu Second Brain.
> Ajuste os thresholds com cuidado: muito sensível = spam, pouco = cego.
> Após 1 semana de uso, revise e calibre baseado em experiência real.
>
**Meta do Heartbeat:** Você só deve ser notificado quando REALMENTE importar. Tudo o resto é ruído.
