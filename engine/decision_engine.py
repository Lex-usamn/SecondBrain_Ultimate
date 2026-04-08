"""
Decision Engine - Motor de Decisões Inteligente
================================================

Combina dados reais do Lex Flow + IA (Claude/Gemini) para tomar
decisões informadas sobre prioridades, próximos passos e otimizações.

Funcionalidades:
- Análise de contexto completo
- Sugestões acionáveis priorizadas
- Scoring de tarefas
- Explicação de raciocínio

Autor: Second Brain Ultimate System
Versão: 1.0.0
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    from .memory_system import MemorySystem
except ImportError:
    from memory_system import MemorySystem

try:
    from ..integrations.lex_flow_definitivo import LexFlowClient
except ImportError:
    from integrations.lex_flow_definitivo import LexFlowClient

# ============================================
# LOGGING
# ============================================
import os
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler('logs/decision_engine.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('DecisionEngine')


# ============================================
# DATA CLASSES
# ============================================

@dataclass
class Decision:
    """Uma decisão sugerida pelo engine"""
    action: str
    reason: str
    confidence: float  # 0.0 a 1.0
    context_used: Dict = field(default_factory=dict)
    alternatives: List[str] = field(default_factory=list)


@dataclass
class MorningPlan:
    """Plano matinal sugerido"""
    top_3: List[Dict] = field(default_factory=list)
    daily_insight: str = ""
    suggested_routine: str = ""
    motivation_quote: str = ""
    context_data: Dict = field(default_factory=dict)


@dataclass
class ActionSuggestion:
    """Sugestão de ação imediata"""
    action: str
    urgency: str  # now, soon, later, someday
    effort: str    # quick, medium, heavy
    impact: str     # high, medium, low
    reasoning: str
    next_steps: List[str] = field(default_factory=list)


# ============================================
# MAIN CLASS
# ============================================

class DecisionEngine:
    """
    Motor de Decisões do Segundo Cérebro
    
    Analisa múltiplas fontes de dados (Lex Flow, Memory, Contexto)
    e gera sugestões inteligentes e acionáveis.
    
    Não substitui o usuário, mas acelera e melhora a qualidade
    das decisões através de análise de dados e padrões.
    
    Uso:
        decider = DecisionEngine(memory, lex_flow)
        plan = decider.suggest_morning_plan(context)
        what_now = decider.what_to_do_now(energy='high')
    """
    
    def __init__(self, memory: MemorySystem, lex_flow: LexFlowClient):
        """
        Inicializa o Motor de Decisões
        
        Args:
            memory: Sistema de memória carregado
            lex_flow: Cliente Lex Flow conectado
        """
        self.memory = memory
        self.lex_flow = lex_flow
        
        log.info("⚖️  Decision Engine inicializado")
        log.info(f"   Memory: {type(memory).__name__}")
        log.info(f"   Lex Flow: Conectado={lex_flow.is_authenticated()}")
    
    def analyze_and_suggest_plan(
        self,
        priorities: List[Dict],
        stats: Dict,
        projects: List[Dict],
        soul: Dict = None,
        user: Dict = None,
        time_context: str = "morning",
        extra_context: Dict = None
    ) -> MorningPlan:
        """
        Analisa contexto completo e sugere plano matinal
        
        Considera:
        - Prioridades oficiais do Lex Flow
        - Métricas de produtividade
        - Metas e objetivos (da Memory)
        - Energia disponível
        - Histórico de padrões
        
        Args:
            priorities: Prioridades do dashboard Lex Flow
            stats: Estatísticas rápidas
            projects: Projetos ativos
            soul: Dados do SOUL.md
            user: Dados do USER.md
            time_context: Período do dia
            extra_context: Contexto adicional
            
        Returns:
            MorningPlan com top 3 e insights
        """
        log.info(f"🌅 Gerando plano matinal (contexto: {time_context})")
        
        plan = MorningPlan()
        plan.context_data = {
            'time_context': time_context,
            'priorities_count': len(priorities),
            'stats': stats,
            'projects_active': len([p for p in projects if p.get('status') == 'active'])
        }
        
        # 1. Enriquecer prioridades com dados da Memory
        enriched_priorities = self._enrich_priorities(priorities, projects)
        plan.top_3 = enriched_priorities[:3]
        
        # 2. Gerar insight diário
        plan.daily_insight = self._generate_daily_insight(stats, time_context)
        
        # 3. Sugerir rotina
        plan.suggested_routine = self._suggest_routine(time_context, stats)
        
        # 4. Motivação
        plan.motivation_quote = self._get_motivation_quote(time_context)
        
        log.info(f"   Plano gerado com {len(plan.top_3)} prioridades")
        
        return plan
    
    def suggest_next_action(
        self,
        current_state: Dict,
        recent_actions: List[str] = None,
        energy: str = "medium"
    ) -> ActionSuggestion:
        """
        Pergunta: "O que eu deveria fazer agora?"
        
        Analisa estado atual e sugere a melhor ação possível
        considerando energia, contexto e histórico recente.
        
        Args:
            current_state: Estado atual (time_of_day, energy, etc.)
            recent_actions: Últimas ações realizadas
            energy: Nível de energia (low/medium/high)
            
        Returns:
            ActionSuggestion com ação e justificativa
        """
        log.info("💭 Analisando o que fazer agora...")
        
        time_day = current_state.get('time_of_day', 'unknown')
        energy_level = energy or current_state.get('energy', 'medium')
        
        # Lógica de decisão baseada em contexto
        suggestion = ActionSuggestion()
        
        # Verificar projetos parados (CRÍTICO)
        stalled = self._check_stalled_projects()
        if stalled:
            suggestion.action = f"Retomar projeto parado: {stalled[0].get('name', '?')}"
            suggestion.urgency = "now"
            suggestion.effort = "medium"
            suggestion.impact = "high"
            suggestion.reasoning = f"Projeto está parado há {stalled[0].get('days_stalled', '?')} dias"
            suggestion.next_steps = [
                "Abrir projeto no Lex Flow",
                "Ver última tarefa realizada",
                "Fazer próxima micro-ação (25 min)"
            ]
            return suggestion
        
        # Verificar inbox
        inbox_size = len(self.lex_flow.get_inbox())
        if inbox_size > 10:
            suggestion.action = f"Processar Inbox ({inbox_size} itens pendentes)"
            suggestion.urgency = "soon"
            suggestion.effort = "medium"
            suggestion.impact = "high"
            suggestion.reasoning = "Inbox acumulada prejudica foco"
            return suggestion
        
        # Baseado em energia e hora
        if energy_level == 'low' and time_day in ['afternoon', 'evening']:
            suggestion.action = "Descanso ativo ou tarefa leve"
            suggestion.urgency = "now"
            suggestion.effort = "light"
            suggestion.impact = "medium"
            suggestion.reasoning = "Energia baixa + final de dia"
            return suggestion
        
        if energy_level == 'high':
            if time_day == 'morning':
                suggestion.action = "Trabalhar em projeto prioritário (Deep Work)"
            elif time_day == 'afternoon':
                suggestion.action = "Continuar projeto em andamento ou revisar"
            else:
                suggestion.action = "Planejar/próximos passos ou aprender algo novo"
            suggestion.urgency = "now"
            suggestion.effort = "heavy"
            suggestion.impact = "high"
            suggestion.reasoning = "Energia alta = aproveitar para trabalho profundo"
            return suggestion
        
        # Default: sugerir baseado em prioridades do Lex Flow
        priorities = self.lex_flow.get_today_priorities()
        if priorities:
            top = priorities[0]
            suggestion.action = f"[{top.get('project_title', '?')}] {top.get('title', 'Tarefa')}"
            suggestion.urgency = "now"
            suggestion.effort = "medium"
            suggestion.impact = "high"
            suggestion.reasoning = "Prioridade #1 definida pelo sistema"
            return suggestion
        
        # Fallback
        suggestion.action = "Revisar suas metas e escolher próxima tarefa"
        suggestion.urgency = "soon"
        suggestion.effort = "light"
        suggestion.impact = "medium"
        suggestion.reasoning = "Sem contexto claro, voltar às metas"
        
        return suggestion
    
    def calculate_task_priority_score(
        self,
        tasks: List[Dict],
        context: Dict = None
    ) -> List[Dict]:
        """
        Calcula scores de prioridade para lista de tarefas
        
        Usa heurística + dados do usuário para ordenar tarefas
        por importância/urgência.
        
        Args:
            tasks: Lista de tarefas com dados básicos
            context: Contexto adicional para scoring
            
        Returns:
            Lista de tarefas ordenadas por score (maior primeiro)
        """
        scored_tasks = []
        
        for task in tasks:
            score = 50  # Base score
            
            # Fator 1: Deadline (tarefas com deadline próximas sobem mais)
            due_date = task.get('due_date')
            if due_date:
                # Simplificado: se tiver deadline, aumenta prioridade
                score += 20
            
            # Fator 2: Prioridade declarada
            priority_map = {'urgent': 30, 'high': 20, 'medium': 10, 'low': 5, 'someday': 0}
            declared_priority = task.get('priority', 'medium').lower()
            score += priority_map.get(declared_priority, 10)
            
            # Fator 3: Projeto estratégico (canais dark = prioridade)
            project_title = task.get('project_title', '').lower()
            if any(kw in project_title for kw in ['dark', 'canal', 'youtube']):
                score += 15  # Canais dark são prioridade máxima
            
            # Fator 4: Tarefa bloqueando outros
            if task.get('blocks_others'):
                score += 10
            
            task['_priority_score'] = score
            scored_tasks.append(task)
        
        # Ordenar por score descendente
        scored_tasks.sort(key=lambda x: x.get('_priority_score', 0), reverse=True)
        
        return scored_tasks
    
    def suggest_follow_ups(
        self,
        current_summary: Dict,
        recent_actions: List[str],
        count: int = 3
    ) -> List[str]:
        """
        Sugere próximos passos baseado no estado atual
        
        Args:
            current_summary: Resumo da sessão atual
            recent_actions: Ações recentes realizadas
            count: Quantidade de sugestões
            
        Returns:
            Lista de strings com sugestões acionáveis
        """
        suggestions = []
        
        # Analisar o que foi feito
        ideas_captured = current_summary.get('ideas_captured', 0)
        decisions_made = current_summary.get('decisions_made', 0)
        
        if ideas_captured > 0 and decisions_made == 0:
            suggestions.append(
                "🎯 Escolha UMA ideia capturada e defina próximo passo concreto"
            )
        
        if ideas_captured >= 3:
            suggestions.append(
                "🔄 Processe seu Inbox (organize as ideias capturadas)"
            )
        
        suggestions.append(
            "📊 Verifique seu Dashboard Lex Flow para métricas atualizadas"
        )
        
        # Sugestões baseadas em projetos
        projects = self.lex_flow.get_projects()
        active_projects = [p for p in projects if p.get('status') == 'active']
        
        if len(active_projects) > 1:
            suggestions.append(
                f"🎯 Foco: Escolha UM projeto principal para esta semana"
            )
        
        if any('dark' in p.get('name', '').lower() for p in active_projects):
            suggestions.append(
                "🎬 Produza conteúdo para canal dark (meta: monetização)"
            )
        
        # Sempre adicionar sugestão de descanso
        suggestions.append(
            "😴 Reserve 15 min para respirar e reavaliar prioridades"
        )
        
        return suggestions[:count]
    
    # ========================================
    # MÉTODOS PRIVADOS (HELPERS)
    # ========================================
    
    def _enrich_priorities(self, priorities: List[Dict], 
                          projects: List[Dict]) -> List[Dict]:
        """Enriquece prioridades com dados adicionais"""
        enriched = []
        
        for i, prio in enumerate(priorities[:5], 1):  # Top 5
            project_title = prio.get('project_title', f'Projeto {i}')
            title = prio.get('title', 'Tarefa sem nome')
            
            # Encontrar projeto correspondente
            matching_project = None
            for p in projects:
                if project_title.lower() in p.get('name', '').lower() or \
                   project_title.lower() in p.get('description', '').lower():
                    matching_project = p
                    break
            
            enriched.append({
                'rank': i,
                'project': project_title,
                'task': title,
                'project_obj': matching_project,
                'estimated_time': self._estimate_time(title, project_title),
                'why_important': self._generate_why_important(project_title, title),
                'next_action_if_chosen': self._suggest_next_action(title)
            })
        
        return enriched
    
    def _estimate_time(self, task: str, project: str = "") -> str:
        """Estima tempo necessário para tarefa"""
        task_lower = task.lower()
        project_lower = project.lower()
        
        # Heurísticas simples
        if any(w in task_lower for w in ['estudar', 'aprender', 'learn', 'ler']):
            return "45-60 min"
        elif any(w in task_lower for w in ['escrever', 'redigir', 'conteúdo', 'post']):
            return "30-45 min"
        elif any(w in task_lower for w in ['editar', 'cortar', 'vídeo', 'video']):
            return "1-2 horas"
        elif any(w in task_lower for w in ['codar', 'desenvolver', 'implementar', 'bug']):
            return "1-3 horas"
        elif 'dark' in project_lower or 'canal' in project_lower:
            return "2-4 horas"
        else:
            return "30 min"
    
    def _generate_why_important(self, project: str, task: str) -> str:
        """Gera explicação de porquê é importante"""
        reasons = {
            'Projeto: 4Live': 'Primeiro passo para dominar SASS e construir portfolio',
            'Canais Dark': 'Diretamente ligado à meta de monetização (3+ canais)',
            'Influencer': 'Escala do negócio depende disso',
            'Livro': 'Meta pessoal importante de legado',
            'App': 'Entrega concreta de valor'
        }
        
        for key, reason in reasons.items():
            if key.lower() in project.lower():
                return reason
        
        return "Contribui para progresso das metas estabelecidas"
    
    def _suggest_next_action(self, task: str) -> str:
        """Sugere próximo passo após escolher tarefa"""
        if 'estudar' in task.lower():
            return "Definir tópicos específicos e tempo dedicado"
        elif 'vídeo' in task.lower() or 'video' in task.lower():
            return "Criar roteiro ou outline do vídeo"
        elif 'post' in task.lower():
            return "Escolher imagem/hook e escrever copy"
        else:
            return "Dividir em micro-tarefas (< 30 min cada)"
    
    def _check_stalled_projects(self) -> List[Dict]:
        """Verifica projetos que podem estar parados"""
        projects = self.lex_flow.get_projects()
        stalled = []
        
        # Lógica simplificada - na implementação real verificar datas
        for p in projects:
            # Se não tiver atividade recente, marcar como possivelmente parado
            last_activity = p.get('updated_at', p.get('created_at'))
            status = p.get('status', '')
            
            # Heurística: se não tem tasks ou status não é active
            if status != 'active':
                stalled.append({
                    'name': p.get('name'),
                    'status': status,
                    'days_staled': 'N/A (verificar)'
                })
        
        return stalled
    
    def _generate_daily_insight(self, stats: Dict, time_context: str) -> str:
        """Gera insight motivacional do dia"""
        insights_morning = [
            "☀️ Cada tarefa concluída é um passo rumo à liberdade financeira",
            "🔥 O momento perfeito para começar é agora (não quando sentir vontade)",
            "🎯 Foco profundo por 90 minutos > 3 horas fragmentadas",
            "💡 Suas canais dark precisam de consistência, não perfeição",
            "⚡️ Automatize o que puder - seu tempo é muito valioso",
        ]
        
        insights_afternoon = [
            "🌤 Tarde é para revisar progresso, não começar coisas novas",
            "🍃 Uma pausa estratégica vale mais que 10 horas de força bruta",
            "📝 Documente o que aprendeu hoje (memória de longo prazo)",
            "🎯 Conecte com pessoas (networking > coding solitário)",
        ]
        
        insights_evening = [
            "🌙 Prepare o amanhã enquanto sua mente ainda está fresca",
            "📋 Revise o que funcionou hoje e o que pode melhorar",
            "🙏️ Gratidão: 3 coisas que você é grato hoje",
        ]
        
        if time_context == 'morning':
            return insights_morning[0] if insights_morning else "Bom dia! Vamos conquistar juntos."
        elif time_context == 'afternoon':
            return insights_afternoon[0] if insights_afternoon else "Boa tarde! Revisão de meio-dia."
        elif time_context == 'evening':
            return insights_evening[0] if insights_evening else "Boa noite! Hora de encerrar."
        else:
            return "💫 Mantenha o foco. Você está construindo algo incrível!"
    
    def _suggest_routine(self, time_context: str, stats: Dict) -> str:
        """Sugere rotina baseada no contexto"""
        routines = {
            'morning': (
                "🌅 **Rotina Matinal Sugerida:**\n"
                "08:00 - 08:15: Briefing matinal (este script!)\n"
                "08:15 - 09:45: Deep Work Bloco 1 (projeto PRIORITÁRIO)\n"
                "09:45 - 10:00: Pausa + Hidratação\n"
                "10:00 - 11:30: Deep Work Bloco 2 (continuação ou segundo projeto)\n"
                "11:30 - 12:30: Almoço + Revisão da manhã\n"
                "12:30 - 13:30: Almoço\n"
                "13:30 - 15:30: Deep Work Bloco 3 (criatividade/tarefas leves)\n"
                "15:30 - 16:00: Organização / Admin (email, Slack, etc)\n"
                "16:00 - 17:00: Revisão do dia + Planejamento amanhã"
            ),
            'afternoon': (
                "🌆 **Rotana de Tarde Sugerida:**\n"
                "14:00 - 14:30: Briefing da tarde\n"
                "14:30 - 16:30: Deep Work (execução focada)\n"
                "16:30 - 17:00: Pausa + Caminhada curta\n"
                "17:00 - 18:30: Trabalho leve (emails, organização)\n"
                "18:30 - 19:00: Preparação para encerramento\n"
            ),
            'evening': (
                "🌙 **Rotina de Noite Sugerida:**\n"
                "19:00 - 20:00: Tempo livre / Família / Descanso\n"
                "20:00 - 21:30: Criatividade (sem pressão de entrega)\n"
                "21:30 - 22:00: Leitura / Aprendizado\n"
                "22:00 - 23:00: Relaxamento / Desconexão digital\n"
            )
        }
        
        return routines.get(time_context, routines.get('morning')[0])
    
    def _get_motivation_quote(self, time_context: str) -> str:
        """Retorna citação motivacional"""
        quotes = {
            "morning": [
                '"A disciplina é a ponte entre seus objetivos e suas realizações." - Jim Rohn',
                '"O segredo do sucesso é fazer o que os outros não fazem." - Will Smith',
                '"Comece onde você está. Use o que você tem. Faça o que você pode." - Arthur Ashe'
            ],
            "afternoon": [
                '"O sucesso é a soma de pequenos esforços repetidos dia após dia." - Robert Collier',
                '"A consistência vence talento." - Unknown',
                '"Você não precisa ser perfeito. Precisa apenas começar." - Unknown'
            ],
            "evening": [
                '"O futuro pertence àqueles que acreditam nos seus sonhos." - Eleanor Roosevelt',
                '"Cada dia é uma nova chance de mudar sua vida." - Unknown',
                '"O único modo de fazer um ótimo trabalho é amar o que você faz." - Steve Jobs'
            ]
        }
        
        import random
        return random.choice(quotes.get(time_context, quotes['morning']))


# ============================================
# TESTE
# ============================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("⚖️  TESTE DO DECISION ENGINE")
    print("=" * 60 + "\n")
    
    # Setup simplificado para teste
    try:
        from integrations.lex_flow_definitivo import LexFlowClient, LexFlowConfig
        
        lf = LexFlowClient(LexFlowConfig())
        memory = MemorySystem(vault_path="./")
        
        decider = DecisionEngine(memory=memory, lex_flow=lf)
        
        print("✅ Decision Engine criado!")
        
        # Teste 1: O que fazer agora?
        print("\n💭 PERGUNTA: O que fazer agora?")
        suggestion = decider.what_to_do_now(energy="high", time_context="morning")
        print(f"\n   ➡️  AÇÃO SUGERIDA: {suggestion.action}")
        print(f"   ⏱️  URGÊNCIA: {suggestion.urgency}")
        print(f"   💪 ESFORÇO: {suggestion.effort}")
        print(f"   🎯 IMPACTO: {suggestion.impact}")
        print(f"   💭 PORQUÊ: {suggestion.reasoning}")
        if suggestion.next_steps:
            print(f"\n   PRÓXIMOS PASSOS:")
            for step in suggestion.next_steps:
                print(f"      → {step}")
        
        # Teste 2: Sugerir follow-ups
        print("\n🔮 SUGESTÕES DE SEGUIMENTO:")
        follows = decider.suggest_follow_ups(
            current_summary={'ideas_captured': 2, 'decisions_made': 1},
            recent_actions=['capture', 'plan'],
            count=3
        )
        for i, s in enumerate(follows, 1):
            print(f"   {i}. {s}")
        
        print("\n" + "=" * 60)
        print("✅ DECISION ENGINE FUNCIONANDO!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()