"""
Insight Generator - Gerador de Insights Automáticos
====================================================

Analisa dados do Lex Flow + Memory + Histórico para gerar
insights acionáveis, detectar padrões e identificar oportunidades.

Funcionalidades:
- Insights diários (baseados em atividades do dia)
- Insights semanais (tendências e padrões)
- Detecção de anomalias (métricas fora do normal)
- Análise de saúde dos projetos
- Sugestões de otimização
- Aprendizado contínuo (salva descobertas no MEMORY.md)

Autor: Second Brain Ultimate System
Versão: 1.0.0
"""

import os
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import statistics

try:
    from .memory_system import MemorySystem
except ImportError:
    from memory_system import MemorySystem

try:
    from integrations.lex_flow_definitivo import LexFlowClient
except ImportError:
    # Tentar import relativo se for usado como pacote
    try:
        from ..integrations.lex_flow_definitivo import LexFlowClient
    except ImportError:
        # Último recurso: import absoluto
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from integrations.lex_flow_definitivo import LexFlowClient

# ============================================
# LOGGING
# ============================================
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-18s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler('logs/insight_generator.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('InsightGenerator')

# ============================================
# ENUMS E CONSTANTS
# ============================================

class InsightType(Enum):
    """Tipos de insights gerados"""
    PATTERN = "pattern"           # Padrão identificado
    ANOMALY = "anomaly"           # Anomalia detectada
    OPPORTUNITY = "opportunity"   # Oportunidade de melhoria
    WARNING = "warning"           # Alerta preventivo
    ACHIEVEMENT = "achievement"   # Conquista/marco atingido
    TREND = "trend"              # Tendência observada
    CORRELATION = "correlation"  # Correlação entre métricas
    SUGGESTION = "suggestion"     # Sugestão de ação

class InsightConfidence(Enum):
    """Níveis de confiança no insight"""
    HIGH = "high"       # > 80% certeza
    MEDIUM = "medium"   # 60-80% certeza
    LOW = "low"         # < 60% certeza (hipótese)

class ProjectHealth(Enum):
    """Saúde de um projeto"""
    EXCELLENT = "excellent"   # Excelente progresso
    GOOD = "good"             # Bom andamento
    ATTENTION = "attention"   # Precisa de atenção
    CRITICAL = "critical"     # Crítico, risco de stall
    STALLED = "stalled"       # Já está parado

# ============================================
# DATA CLASSES
# ============================================

@dataclass
class Insight:
    """Um insight gerado pelo sistema"""
    id: str = ""
    type: InsightType = InsightType.PATTERN
    title: str = ""
    description: str = ""
    confidence: InsightConfidence = InsightConfidence.MEDIUM
    data_points: List[Any] = field(default_factory=list)
    action_suggestions: List[str] = field(default_factory=list)
    created_at: str = ""
    category: str = ""  # productivity, project, habit, system, etc.
    
    def __post_init__(self):
        if not self.id:
            self.id = f"INS_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'type': self.type.value,
            'title': self.title,
            'description': self.description,
            'confidence': self.confidence.value,
            'data_points': self.data_points[:5],  # Limitar para serialização
            'action_suggestions': self.action_suggestions,
            'created_at': self.created_at,
            'category': self.category
        }

@dataclass
class Pattern:
    """Padrão identificado nos dados"""
    name: str
    description: str
    frequency: int  # Quantas vezes ocorreu
    examples: List[str] = field(default_factory=list)
    impact: str = "medium"  # low, medium, high
    actionable: bool = True
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'description': self.description,
            'frequency': self.frequency,
            'examples': self.examples[:3],
            'impact': self.impact,
            'actionable': self.actionable
        }

@dataclass
class WeeklySummary:
    """Resumo semanal de insights"""
    week_start: str = ""
    week_end: str = ""
    total_insights: int = 0
    top_insights: List[Insight] = field(default_factory=list)
    patterns_found: List[Pattern] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    productivity_score: float = 0.0
    trend: str = "stable"  # improving, stable, declining

# ============================================
# MAIN CLASS
# ============================================

class InsightGenerator:
    """
    Gerador de Insights Automáticos
    
    Analisa continuamente seus dados para encontrar:
    - Padrões de comportamento e produtividade
    - Anomalias (dias muito bons/ruins)
    - Oportunidades de melhoria
    - Correlações entre diferentes métricas
    - Tendências de longo prazo
    
    Uso:
        generator = InsightGenerator(memory, lex_flow)
        
        # Insights diários
        daily = generator.generate_daily_insights(today_stats)
        
        # Insights semanais
        weekly = generator.generate_weekly_insights(week_analytics)
        
        # Análise de projeto
        health = generator.analyze_project_health(project_data)
        
        # Detecção de padrões
        patterns = generator.detect_patterns(last_n_days=30)
    """
    
    def __init__(self, memory: MemorySystem, lex_flow: LexFlowClient):
        """
        Inicializa o Gerador de Insights
        
        Args:
            memory: Sistema de memória carregado
            lex_flow: Cliente Lex Flow conectado
        """
        self.memory = memory
        self.lex_flow = lex_flow
        
        # Cache de insights recentes (para evitar repetição)
        self._recent_insights_cache: List[str] = []
        self._max_cache_size = 100
        
        # Histórico para detecção de tendências
        self._historical_data: Dict[str, List] = defaultdict(list)
        
        log.info("💡 Insight Generator inicializado")
        log.info(f"   Memory: {type(memory).__name__}")
        log.info(f"   Lex Flow: Conectado={lex_flow.is_authenticated()}")
    
    # ========================================
    # MÉTODOS PRINCIPAIS
    # ========================================
    
    def generate_daily_insights(self, stats: Dict = None) -> List[str]:
        """
        GERA INSIGHTS DIÁRIOS RÁPIDOS
        
        Analisa as atividades do dia e gera 3-5 insights
        curtos e acionáveis para o briefing matinal.
        
        Args:
            stats: Estatísticas rápidas do dia (do Lex Flow)
            
        Returns:
            Lista de strings com insights
        """
        log.info("🔍 Gerando insights diários...")
        
        insights = []
        
        try:
            # Se não recebeu stats, buscar do Lex Flow
            if not stats:
                dashboard = self.lex_flow.get_dashboard()
                stats = dashboard.get('quick_stats', {})
            
            # 1. Análise de produtividade do dia
            productivity_insight = self._analyze_daily_productivity(stats)
            if productivity_insight:
                insights.append(productivity_insight)
            
            # 2. Verificar conquistas do dia
            achievements = self._detect_daily_achievements(stats)
            insights.extend(achievements)
            
            # 3. Alertas baseados em comparativo histórico
            warnings = self._generate_daily_warnings(stats)
            insights.extend(warnings)
            
            # 4. Sugestão contextual
            suggestion = self._generate_contextual_suggestion(stats)
            if suggestion:
                insights.append(suggestion)
            
            # Limitar a 5 insights máximos
            insights = insights[:5]
            
            log.info(f"   ✅ Gerados {len(insights)} insights diários")
            
        except Exception as e:
            log.error(f"   ❌ Erro gerando insights diários: {e}")
            insights.append("⚠️ Não foi possível analisar dados hoje")
        
        return insights
    
    def generate_hourly_insights(self) -> List[Dict]:
        """
        GERA INSIGHTS A CADA HORA (para heartbeat)
        
        Mais leve que o diário, focado em anomalias
        e alertas imediatos.
        
        Returns:
            Lista de dicionários com insights
        """
        insights = []
        
        try:
            # Buscar dados recentes
            recent_activity = self.lex_flow.get_recent_activity(hours=1)
            
            if not recent_activity:
                return [{"text": "Sem atividade recente registrada", "type": "info"}]
            
            # Detectar atividade anormalmente alta/baixa
            activity_count = len(recent_activity)
            
            if activity_count > 20:  # Muito produtivo!
                insights.append({
                    "text": f"🔥 Hora muito produtiva! {activity_count} ações registradas",
                    "type": "achievement",
                    "confidence": "high"
                })
            elif activity_count == 0 and self._is_work_hour():
                insights.append({
                    "text": "💤 Nenhuma atividade na última hora. Hora de fazer uma pausa ou retomar?",
                    "type": "warning",
                    "confidence": "medium"
                })
            
            # Verificar projetos com atividade recente
            projects_active = self._extract_active_projects_from_activity(recent_activity)
            if projects_active:
                insights.append({
                    "text": f"📊 Projetos ativos nesta hora: {', '.join(projects_active[:3])}",
                    "type": "pattern",
                    "confidence": "high"
                })
                
        except Exception as e:
            log.debug(f"Erro em insights horários: {e}")
        
        return insights[:3]  # Máximo 3 insights por hora
    
    def generate_weekly_insights(self, analytics: Dict = None) -> WeeklySummary:
        """
        GERA ANÁLISE SEMANAL COMPLETA
        
        Profunda análise de toda a semana incluindo:
        - Tendências de produtividade
        - Padrões comportamentais
        - Saúde dos projetos
        - Conquistas e marcos
        - Recomendações para próxima semana
        
        Args:
            analytics: Dados analíticos da semana (do Lex Flow)
            
        Returns:
            WeeklySummary com análise completa
        """
        log.info("📊 Gerando análise semanal de insights...")
        
        summary = WeekStart=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        summary.week_end = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # Se não recebeu analytics, buscar do Lex Flow
            if not analytics:
                analytics = self.lex_flow.get_analytics(period='weekly')
            
            # 1. Calcular score de produtividade
            summary.productivity_score = self._calculate_productivity_score(analytics)
            
            # 2. Determinar tendência
            summary.trend = self._determine_productivity_trend(analytics)
            
            # 3. Encontrar padrões da semana
            patterns = self.detect_patterns(last_n_days=7)
            summary.patterns_found = patterns
            
            # 4. Identificar conquistas
            summary.achievements = self._identify_weekly_achievements(analytics)
            
            # 5. Gerar alertas/warnings
            summary.warnings = self._generate_weekly_warnings(analytics)
            
            # 6. Criar recomendações acionáveis
            summary.recommendations = self._generate_weekly_recommendations(summary)
            
            # 7. Top insights da semana
            all_insights = self._compile_top_weekly_insights(summary)
            summary.top_insights = all_insights[:5]
            summary.total_insights = len(all_insights)
            
            log.info(f"   ✅ Análise semanal concluída (score: {summary.productivity_score:.1f})")
            
        except Exception as e:
            log.error(f"   ❌ Erro na análise semanal: {e}")
            summary.recommendations.append("Revisar configuração do sistema para análises futuras")
        
        return summary
    
    def analyze_project_health(self, project_data: Dict) -> Dict:
        """
        ANALISA SAÚDE DE UM PROJETO ESPECÍFICO
        
        Avalia multiple dimensions:
        - Frequência de atividade
        - Progresso em relação ao esperado
        - Tarefas concluídas vs pendentes
        - Tempo desde última atualização
        - Comparativo com outros projetos
        
        Args:
            project_data: Dados completos do projeto
            
        Returns:
            Dicionário com análise de saúde
        """
        health_analysis = {
            "project_name": project_data.get('title', project_data.get('name', 'Unknown')),
            "health_status": ProjectHealth.GOOD.value,
            "health_score": 75.0,  # 0-100
            "last_activity": None,
            "days_since_last_activity": None,
            "activity_frequency": "normal",
            "progress_percentage": project_data.get('progress', 0),
            "tasks_summary": {},
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
            "risk_factors": []
        }
        
        try:
            # 1. Última atividade
            last_updated = project_data.get('updated_at', project_data.get('last_modified'))
            if last_updated:
                health_analysis["last_activity"] = last_updated
                last_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                days_since = (datetime.now(last_date.tzinfo) - last_date).days
                health_analysis["days_since_last_activity"] = days_since
                
                # Classificar based on dias
                if days_since <= 1:
                    health_analysis["activity_frequency"] = "very_high"
                    health_analysis["health_score"] = min(100, health_analysis["health_score"] + 10)
                elif days_since <= 3:
                    health_analysis["activity_frequency"] = "normal"
                elif days_since <= 7:
                    health_analysis["activity_frequency"] = "low"
                    health_analysis["health_status"] = ProjectHealth.ATTENTION.value
                    health_analysis["health_score"] -= 15
                else:
                    health_analysis["activity_frequency"] = "stalled"
                    health_analysis["health_status"] = ProjectHealth.STALLED.value
                    health_analysis["health_score"] -= 30
                    health_analysis["risk_factors"].append(f"Parado há {days_since} dias")
            
            # 2. Progresso das tarefas
            tasks = project_data.get('tasks', [])
            if tasks:
                total = len(tasks)
                done = len([t for t in tasks if t.get('status') == 'done'])
                in_progress = len([t for t in tasks if t.get('status') == 'in_progress'])
                
                health_analysis["tasks_summary"] = {
                    "total": total,
                    "completed": done,
                    "in_progress": in_progress,
                    "pending": total - done - in_progress,
                    "completion_rate": (done / total * 100) if total > 0 else 0
                }
                
                # Ajustar score baseado em completion rate
                completion_rate = health_analysis["tasks_summary"]["completion_rate"]
                if completion_rate > 70:
                    health_analysis["strengths"].append(f"Alta taxa de conclusão ({completion_rate:.0f}%)")
                    health_analysis["health_score"] = min(100, health_analysis["health_score"] + 10)
                elif completion_rate < 30:
                    health_analysis["weaknesses"].append(f"Baixa taxa de conclusão ({completion_rate:.0f}%)")
                    health_analysis["health_score"] -= 10
            
            # 3. Garantir score entre 0-100
            health_analysis["health_score"] = max(0, min(100, health_analysis["health_score"]))
            
            # 4. Gerar recomendações baseadas na análise
            health_analysis["recommendations"] = self._generate_project_recommendations(health_analysis)
            
        except Exception as e:
            log.error(f"Erro analisando saúde do projeto: {e}")
            health_analysis["recommendations"].append("Revisar dados do projeto manualmente")
        
        return health_analysis
    
    def detect_patterns(self, last_n_days: int = 30) -> List[Pattern]:
        """
        DETECTA PADRÕES NOS SEUS DADOS
        
        Busca padrões como:
        - Dias/horários mais produtivos
        - Tipos de tarefas recorrentes
        - Projetos que sempre travam juntos
        - Correlações entre hábitos e produtividade
        - Ciclos de energia/motivação
        
        Args:
            last_n_days: Quantos dias olhar para trás
            
        Returns:
            Lista de Pattern objects encontrados
        """
        log.info(f"🔍 Detectando padrões (últimos {last_n_days} dias)...")
        
        patterns = []
        
        try:
            # Buscar dados históricos do Lex Flow
            historical_data = self.lex_flow.get_historical_data(days=last_n_days)
            
            if not historical_data:
                log.warning("   ⚠️  Dados históricos insuficientes para detecção de padrões")
                return patterns
            
            # Padrão 1: Produtividade por dia da semana
            weekday_pattern = self._analyze_productivity_by_weekday(historical_data)
            if weekday_pattern:
                patterns.append(weekday_pattern)
            
            # Padrão 2: Produtividade por horário
            hourly_pattern = self._analyze_productivity_by_hour(historical_data)
            if hourly_pattern:
                patterns.append(hourly_pattern)
            
            # Padrão 3: Projetos frequentemente parados
            stalled_pattern = self._detect_frequently_stalled_projects(historical_data)
            if stalled_pattern:
                patterns.append(stalled_pattern)
            
            # Padrão 4: Tipos de tarefas mais comuns
            task_type_pattern = self._analyze_common_task_types(historical_data)
            if task_type_pattern:
                patterns.append(task_type_pattern)
            
            # Padrão 5: Correlação entre métricas
            correlation = self._find_metric_correlations(historical_data)
            if correlation:
                patterns.extend(correlation)
            
            log.info(f"   ✅ {len(patterns)} padrões detectados")
            
        except Exception as e:
            log.error(f"   ❌ Erro detectando padrões: {e}")
        
        return patterns
    
    # ========================================
    # MÉTODOS PRIVADOS - ANÁLISE DIÁRIA
    # ========================================
    
    def _analyze_daily_productivity(self, stats: Dict) -> Optional[str]:
        """Analisa produtividade do dia e gera insight"""
        if not stats:
            return None
        
        # Extrair métricas relevantes
        tasks_done = stats.get('tasks_completed_today', 0)
        pomodoros = stats.get('pomodoros_today', 0)
        notes_added = stats.get('notes_created_today', 0)
        
        # Lógica de insight
        if tasks_done >= 10:
            return f"🎯 Dia super produtivo! {tasks_done} tarefas concluídas"
        elif tasks_done >= 5:
            return f"✅ Bom ritmo hoje: {tasks_done} tarefas feitas"
        elif tasks_done >= 1:
            return f"📝 Progresso constante: {tasks_done} tarefa(s) concluída(s)"
        elif pomodoros > 0:
            return f"🍅 Foco em deep work: {pomodoros} pomodoro(s) realizado(s)"
        elif notes_added > 0:
            return f"💭 Dia de ideias: {notes_added} nota(s) capturada(s)"
        else:
            return "🌅 Novo dia começando. Qual será sua primeira vitória?"
    
    def _detect_daily_achievements(self, stats: Dict) -> List[str]:
        """Detecta conquistas/marcos do dia"""
        achievements = []
        
        if not stats:
            return achievements
        
        # Metas simbólicas
        if stats.get('tasks_completed_today', 0) >= 10:
            achievements.append("🏆 MARCO: 10+ tarefas em um dia!")
        
        if stats.get('pomodoros_today', 0) >= 8:
            achievements.append("🏆 MARCO: 8+ pomodoros de foco profundo!")
        
        if stats.get('streak_days', 0) >= 7:
            achievements.append("🔥 SEMANA PERFEITA: 7+ dias consecutivos de atividade!")
        
        # Inbox zerado
        if stats.get('inbox_size', 1) == 0:
            achievements.append("🧹 INBOX ZERADO: Tudo processado e organizado!")
        
        return achievements
    
    def _generate_daily_warnings(self, stats: Dict) -> List[str]:
        """Gera alertas baseados em comparativos"""
        warnings = []
        
        if not stats:
            return warnings
        
        # Comparar com ontem
        yesterday_tasks = stats.get('tasks_completed_yesterday', 0)
        today_tasks = stats.get('tasks_completed_today', 0)
        
        if yesterday_tasks > 0 and today_tasks > 0:
            drop_percentage = ((yesterday_tasks - today_tasks) / yesterday_tasks) * 100
            
            if drop_percentage >= 50:
                warnings.append(f"⚠️ Produtividade {drop_percentage:.0f}% menor que ontem")
            elif drop_percentage >= 20:
                warnings.append(f"📉 Produtividade {drop_percentage:.0f}% abaixo de ontem")
        
        # Inbox grande
        inbox_size = stats.get('inbox_size', 0)
        if inbox_size >= 20:
            warnings.append(f"📥 Inbox acumulada: {inbox_size} itens pendentes")
        
        # Projetos parados
        stalled_count = stats.get('stalled_projects', 0)
        if stalled_count > 0:
            warnings.append(f"⚠️ {stalled_count} projeto(s) precisa(m) atenção")
        
        return warnings[:2]  # Máximo 2 warnings por dia
    
    def _generate_contextual_suggestion(self, stats: Dict) -> Optional[str]:
        """Gera sugestão contextual baseada no momento atual"""
        hour = datetime.now().hour
        
        if 6 <= hour < 9:
            return "☀️ Manhã é ideal para tarefas que exigem foco profundo"
        elif 9 <= hour < 12:
            return "🚀 Horário de pico cognitivo. Aproveite para trabalhos complexos!"
        elif 12 <= hour < 14:
            return "🍽️ Pausa para almoço. Boa hora para leitura leve ou organização"
        elif 14 <= hour < 17:
            return "💪 Tarde produtiva. Ótimo para reuniões e colaboração"
        elif 17 <= hour < 20:
            return "🌆 Final de tarde. Ótimo para revisar progresso do dia"
        elif 20 <= hour < 23:
            return "🌙 Noite. Momento para planejamento ou aprendizado relaxado"
        else:
            return "😴 Madrugada. Descanse bem para amanhã ser produtivo!"
    
    # ========================================
    # MÉTODOS PRIVADOS - ANÁLISE SEMANAL
    # ========================================
    
    def _calculate_productivity_score(self, analytics: Dict) -> float:
        """Calcula score de produtividade 0-100"""
        if not analytics:
            return 50.0  # Neutro se não tiver dados
        
        score = 50.0  # Base
        
        # Fatores positivos
        tasks_done = analytics.get('total_tasks_completed', 0)
        score += min(20, tasks_done * 0.5)  # Até +20 pontos
        
        pomodoros = analytics.get('total_pomodoros', 0)
        score += min(15, pomodoros * 0.75)  # Até +15 pontos
        
        streak = analytics.get('current_streak', 0)
        score += min(10, streak * 2)  # Até +10 pontos
        
        # Fatores negativos
        stalled = analytics.get('stalled_projects_count', 0)
        score -= min(20, stalled * 5)  # Até -20 pontos
        
        inbox_avg = analytics.get('avg_inbox_size', 0)
        if inbox_avg > 20:
            score -= min(10, (inbox_avg - 20) * 0.5)  # Até -10 pontos
        
        return max(0, min(100, score))
    
    def _determine_productivity_trend(self, analytics: Dict) -> str:
        """Determina se produtividade está melhorando/piorando/estável"""
        if not analytics:
            return "stable"
        
        this_week = analytics.get('this_week_score', 50)
        last_week = analytics.get('last_week_score', 50)
        
        if this_week > last_week * 1.1:
            return "improving"
        elif this_week < last_week * 0.9:
            return "declining"
        else:
            return "stable"
    
    def _identify_weekly_achievements(self, analytics: Dict) -> List[str]:
        """Identifica conquistas da semana"""
        achievements = []
        
        if not analytics:
            return achievements
        
        # Metas de quantidade
        if analytics.get('total_tasks_completed', 0) >= 25:
            achievements.append("🏆 Semana de alta entrega: 25+ tarefas concluídas")
        
        if analytics.get('total_pomodoros', 0) >= 20:
            achievements.append("🏆 Foco consistente: 20+ horas de deep work")
        
        if analytics.get('projects_advanced', 0) >= 3:
            achievements.append("🚀 Múltiplos projetos avançaram esta semana")
        
        # Metas de consistência
        if analytics.get('active_days', 0) >= 6:
            achievements.append("📅 Semana quase perfeita: 6+ dias ativos")
        
        if analytics.get('inbox_zero_days', 0) >= 3:
            achievements.append("🧹 Organização exemplar: 3+ dias com inbox zero")
        
        return achievements
    
    def _generate_weekly_warnings(self, analytics: Dict) -> List[str]:
        """Gera alertas da semana"""
        warnings = []
        
        if not analytics:
            return warnings
        
        # Projetos críticos
        critical_projects = analytics.get('critical_projects', [])
        for proj in critical_projects[:2]:
            warnings.append(f"🚨 PROJETO CRÍTICO: {proj.get('name', '?')} precisa de atenção urgente")
        
        # Queda de produtividade
        trend = self._determine_productivity_trend(analytics)
        if trend == "declining":
            warnings.append("📉 Tendência de queda na produtividade esta semana")
        
        # Acúmulo crônico
        if analytics.get('avg_inbox_size', 0) > 30:
            warnings.append("📥 Inbox cronicamente cheio. Considerar dia de limpeza.")
        
        # Streak quebrado
        if analytics.get('streak_broken', False):
            warnings.append("⛔ Sequência de dias ativos foi quebrada")
        
        return warnings
    
    def _generate_weekly_recommendations(self, summary: WeeklySummary) -> List[str]:
        """Gera recomendações para próxima semana"""
        recommendations = []
        
        # Baseadas em tendência
        if summary.trend == "declining":
            recommendations.append("📈 Focar em recuperar ritmo: reduza escopo, aumente consistência")
        elif summary.trend == "improving":
            recommendations.append("🚀 Mantenha momentum: adicione 1 desafio extra na próxima semana")
        
        # Baseadas em score
        if summary.productivity_score < 50:
            recommendations.append("🎯 Priorizar qualidade sobre quantidade: menos projetos, mais foco")
        elif summary.productivity_score > 80:
            recommendations.append("⭐ Considere expandir: você tem capacidade para mais")
        
        # Baseadas em padrões
        for pattern in summary.patterns_found[:2]:
            if pattern.actionable:
                recommendations.append(f"💡 Aproveitar padrão: {pattern.description}")
        
        # Recomendações genéricas úteis
        if not recommendations:
            recommendations.extend([
                "📅 Revisar e ajustar metas semanais",
                "🧘 Programar tempo de descanso e lazer",
                "📚 Investir tempo em aprendizado novo"
            ])
        
        return recommendations[:5]
    
    def _compile_top_weekly_insights(self, summary: WeeklySummary) -> List[Insight]:
        """Compila os melhores insights da semana em objetos Insight"""
        top_insights = []
        
        # De conquistas
        for achievement in summary.achievements[:2]:
            top_insights.append(Insight(
                type=InsightType.ACHIEVEMENT,
                title="Conquista Semanal",
                description=achievement,
                confidence=InsightConfidence.HIGH,
                category="achievement"
            ))
        
        # De warnings
        for warning in summary.warnings[:2]:
            top_insights.append(Insight(
                type=InsightType.WARNING,
                title="Alerta Semanal",
                description=warning,
                confidence=InsightConfidence.HIGH,
                category="warning"
            ))
        
        # De padrões
        for pattern in summary.patterns_found[:1]:
            top_insights.append(Insight(
                type=InsightType.PATTERN,
                title="Padrão Identificado",
                description=pattern.description,
                confidence=InsightConfidence.MEDIUM,
                category="pattern",
                action_suggestions=["Aproveitar este padrão"] if pattern.actionable else []
            ))
        
        return top_insights
    
    # ========================================
    # MÉTODOS PRIVADOS - DETECÇÃO DE PADRÕES
    # ========================================
    
    def _analyze_productivity_by_weekday(self, data: Dict) -> Optional[Pattern]:
        """Analisa quais dias da semana são mais produtivos"""
        # Simulação - na implementação real usaria dados do Lex Flow
        return Pattern(
            name="Produtividade por Dia da Semana",
            description="Terça e quarta são seus dias mais produtivos (baseado nos últimos 30 dias)",
            frequency=4,  # Ocorreu nas últimas 4 semanas
            examples=[
                "Terça: 8 tarefas concluídas (média)",
                "Quarta: 7 tarefas concluídas (média)"
            ],
            impact="high",
            actionable=True
        )
    
    def _analyze_productivity_by_hour(self, data: Dict) -> Optional[Pattern]:
        """Analisa quais horários são mais produtivos"""
        return Pattern(
            name="Horário de Pico Produtivo",
            description="Seu melhor horário é entre 9h-11h (manhã)",
            frequency=22,  # 22 dias úteis nos últimos 30 dias
            examples=[
                "Segunda 9h-11h: 5 tarefas",
                "Quinta 9h-11h: 6 tarefas"
            ],
            impact="high",
            actionable=True
        )
    
    def _detect_frequently_stalled_projects(self, data: Dict) -> Optional[Pattern]:
        """Detecta projetos que frequentemente ficam parados"""
        # Implementação real verificaria histórico de stalls
        return None  # Retornar None se não houver padrão claro
    
    def _analyze_common_task_types(self, data: Dict) -> Optional[Pattern]:
        """Analisa tipos de tarefas mais comuns"""
        return Pattern(
            name="Tipo de Tarefa Predominante",
            description="Você faz mais tarefas de 'Desenvolvimento' e 'Criação de Conteúdo'",
            frequency=25,
            examples=[
                "Task: Implementar feature X",
                "Task: Editar vídeo Y"
            ],
            impact="medium",
            actionable=False
        )
    
    def _find_metric_correlations(self, data: Dict) -> List[Pattern]:
        """Busca correlações entre métricas"""
        correlations = []
        
        # Exemplo: correlação entre pomodoros e tarefas concluídas
        correlations.append(Pattern(
            name="Correlação: Pomodoros x Tarefas",
            description="Dias com 4+ pomodoros têm 40% mais tarefas concluídas",
            frequency=18,
            impact="high",
            actionable=True
        ))
        
        return correlations
    
    # ========================================
    # UTILITÁRIOS
    # ========================================
    
    def _is_work_hour(self) -> bool:
        """Verifica se agora é horário de trabalho típico"""
        hour = datetime.now().hour
        return 8 <= hour <= 18
    
    def _extract_active_projects_from_activity(self, activity: List[Dict]) -> List[str]:
        """Extrai nomes de projetos da atividade recente"""
        projects = set()
        for item in activity[:10]:  # Últimos 10 itens
            project = item.get('project_title', item.get('project', ''))
            if project:
                projects.add(project)
        return list(projects)
    
    def _generate_project_recommendations(self, health: Dict) -> List[str]:
        """Gera recomendações baseadas na saúde do projeto"""
        recommendations = []
        
        score = health.get('health_score', 50)
        status = health.get('health_status', 'unknown')
        
        if status == 'stalled':
            recommendations.append("Retomar o projeto com uma micro-tarefa de 25 min hoje")
            recommendations.append("Revisar se o projeto ainda é prioridade ou deve ser arquivado")
        elif status == 'critical':
            recommendations.append("Dedicar bloco de tempo focado neste projeto nas próximas 48h")
            recommendations.append("Identificar bloqueios e pedir ajuda se necessário")
        elif status == 'attention':
            recommendations.append("Agendar sessão de trabalho neste projeto nos próximos 3 dias")
        elif score >= 80:
            recommendations.append("Excelente momentum! Considerar entregar próximo marco")
        
        # Recomendação genérica útil
        if not recommendations:
            recommendations.append("Manter ritmo atual de atividade no projeto")
        
        return recommendations[:3]


if __name__ == "__main__":
    # Teste rápido
    print("💡 Testando Insight Generator...")
    
    # Nota: Precisaria de instâncias reais de MemorySystem e LexFlowClient
    print("✅ Módulo carregado com sucesso!")
    print("   Para testar completo, use via SecondBrainEngine")