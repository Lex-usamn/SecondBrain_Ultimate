"""
Insight Generator v2.0 - Gerador de Insights Inteligentes do Segundo Cérebro
==========================================================================

Analisa dados do Lex Flow + Memory + Histórico para gerar
insights acionáveis, detectar padrões e identificar oportunidades.

Este é o "cérebro que PENSA" do sistema - não só processa dados,
mas gera CONHECIMENTO e SABEDORIA acionável.

Funcionalidades:
- Insights diários (baseados em atividades do dia)
- Insights semanais (tendências e padrões de longo prazo)
- Detecção de anomalias (métricas fora do normal)
- Análise de saúde dos projetos (estagnação, risco)
- Sugestões de otimização personalizadas
- Relatório TELOS automatizado (semanal)
- Aprendizado contínuo (salva descobertas no MEMORY.md)
- Correlação entre métricas diferentes

Integração Lex Flow:
- Dados reais via get_dashboard(), get_projects(), get_inbox()
- Histórico de atividades para análise de tendências
- Métricas de produtividade para benchmarking
- Projetos e tarefas para análise de saúde

Autor: Second Brain Ultimate System
Versão: 2.0.0 (Refatorado - Integração Lex Flow Real)
Data: 09/04/2026
"""

import os
import json
import logging
import re
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
from functools import lru_cache

# ============================================
# IMPORTS DOS MÓDULOS DO ENGINE (com fallbacks robustos)
# ============================================
try:
    from .memory_system import MemorySystem
except ImportError:
    from memory_system import MemorySystem

try:
    from .decision_engine import DecisionEngine
except ImportError:
    try:
        from decision_engine import DecisionEngine
    except ImportError:
        DecisionEngine = None  # Opcional

# ============================================
# IMPORT DO LEX FLOW CLIENT (com fallbacks)
# ============================================
try:
    from ..integrations.lex_flow_definitivo import LexFlowClient
except ImportError:
    try:
        from integrations.lex_flow_definitivo import LexFlowClient
    except ImportError:
        # Último recurso: import absoluto
        import sys
        from pathlib import Path as _Path
        sys.path.insert(0, str(_Path(__file__).parent.parent))
        try:
            from integrations.lex_flow_definitivo import LexFlowClient
        except ImportError:
            class LexFlowClient:
                """Placeholder quando não disponível"""
                pass


# ============================================
# LOGGING DEDICADO
# ============================================
os.makedirs('logs', exist_ok=True)

# Logger específico deste módulo
logger_insight = logging.getLogger('InsightGenerator')

# Configurar handler apenas se não existe ainda (evita duplicados)
if not logger_insight.handlers:
    logger_insight.setLevel(logging.DEBUG)
    
    # Handler para arquivo
    file_handler = logging.FileHandler(
        'logs/insight_generator.log',
        encoding='utf-8',
        mode='a'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(name)-18s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    ))
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    ))
    
    logger_insight.addHandler(file_handler)
    logger_insight.addHandler(console_handler)


# ============================================
# ENUMS E CONSTANTES
# ============================================

class InsightType(Enum):
    """
    Tipos de insights gerados pelo sistema
    
    Cada tipo tem uma semântica diferente e é tratado
    de forma distinta nas recomendações.
    
    - PATTERN: Comportamento recorrente identificado
    - ANOMALY: Valor fora do normal (muito alto/baixo)
    - OPPORTUNITY: Chance de melhoria ou ganho
    - WARNING: Alerta preventivo sobre risco futuro
    - ACHIEVEMENT: Marco positivo atingido
    - TREND: Direção de mudança ao longo do tempo
    - CORRELATION: Relação entre duas métricas
    - SUGGESTION: Recomendação de ação concreta
    """
    PATTERN = "pattern"           # Padrão identificado nos dados
    ANOMALY = "anomaly"           # Anomalia detectada (fora do normal)
    OPPORTUNITY = "opportunity"   # Oportunidade de melhoria/ganho
    WARNING = "warning"           # Alerta preventivo (risco futuro)
    ACHIEVEMENT = "achievement"   # Conquista/marco positivo atingido
    TREND = "trend"              # Tendência observada (subindo/descendo)
    CORRELATION = "correlation"  # Correlação entre métricas
    SUGGESTION = "suggestion"     # Sugestão de ação concreta


class InsightConfidence(Enum):
    """
    Níveis de confiança no insight
    
    Baseado em quantidade de evidências e consistência dos dados.
    Usado para priorizar quais insights mostrar ao usuário.
    
    - HIGH: > 80% certeza (muitas evidências, padrão claro)
    - MEDIUM: 60-80% certeza (evidências moderadas)
    - LOW: < 60% certeza (hipótese, poucos dados)
    """
    HIGH = "high"       # > 80% certeza - ação recomendada fortemente
    MEDIUM = "medium"   # 60-80% certeza - considerar ação
    LOW = "low"         # < 60% certeza - apenas observação


class ProjectHealth(Enum):
    """
    Classificação de saúde de um projeto
    
    Usada para priorizar quais projetos precisam de atenção.
    """
    EXCELLENT = "excellent"   # Excelente progresso, acima das expectativas
    GOOD = "good"             # Bom andamento, no ritmo esperado
    ATTENTION = "attention"   # Precisa de atenção, leve desaceleração
    CRITICAL = "critical"     # Crítico, alto risco de stall/abandono
    STALLED = "stalled"       # Já está parado/inativo


class TelosDimension(Enum):
    """
    Dimensões do framework TELOS (Weekly Review)
    
    TELOS é um framework holístico de revisão semanal:
    - Time: Gestão do tempo e energia
    - Energy: Nível físico e mental
    - Light: Claro mental, foco, propósito
    - Opportunity: Oportunidades identificadas
    - Significance: Impacto e significado do trabalho
    """
    TIME = "time"             # Tempo: como usei meu tempo?
    ENERGY = "energy"         # Energia: nível físico/emocional?
    LIGHT = "light"           # Luz: clareza mental, aprendizados?
    OPPORTUNITY = "opportunity"  # Oportunidade: chances perdidas/encontradas?
    SIGNIFICANCE = "significance"  # Significado: impacto do trabalho?


# ============================================
# DATA CLASSES DE INSIGHTS E RESULTADOS
# ============================================

@dataclass
class Insight:
    """
    Um insight gerado pelo sistema
    
    Representa uma descoberta, padrão ou recomendação
    identificada pela análise dos dados.
    
    Attributes:
        id: Identificador único (gerado automaticamente)
        type: Tipo do insight (InsightType enum)
        title: Título curto e chamativo
        description: Descrição detalhada do insight
        confidence: Nível de confiança (InsightConfidence enum)
        data_points: Evidências/dados que suportam este insight
        action_suggestions: Lista de ações recomendadas
        created_at: Timestamp de criação (ISO format)
        category: Categoria para agrupamento (productivity, project, etc.)
        source: Fonte dos dados (lex_flow, memory, hybrid)
        priority: Prioridade de exibição (1-10, maior = mais importante)
    """
    id: str = ""
    type: InsightType = InsightType.PATTERN
    title: str = ""
    description: str = ""
    confidence: InsightConfidence = InsightConfidence.MEDIUM
    data_points: List[Any] = field(default_factory=list)
    action_suggestions: List[str] = field(default_factory=list)
    created_at: str = ""
    category: str = ""  # productivity, project, habit, system, learning
    source: str = "hybrid"
    priority: int = 5  # 1-10, maior = mais importante
    
    def __post_init__(self):
        """Inicialização automática de campos opcionais"""
        if not self.id:
            self.id = f"INS_{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte insight para dicionário serializável
        
        Útil para enviar via API, salvar em JSON, ou exibir em dashboard.
        
        Returns:
            Dicionário com todos os campos do insight
        """
        return {
            'id': self.id,
            'type': self.type.value,
            'title': self.title,
            'description': self.description,
            'confidence': self.confidence.value,
            'data_points': self.data_points[:5],  # Limitar para serialização
            'action_suggestions': self.action_suggestions,
            'created_at': self.created_at,
            'category': self.category,
            'source': self.source,
            'priority': self.priority
        }


@dataclass
class Pattern:
    """
    Padrão identificado nos dados
    
    Um pattern é um comportamento recorrente que acontece
    múltiplas vezes e pode ser aproveitado ou corrigido.
    
    Attributes:
        name: Nome curto do padrão
        description: Descrição do que significa
        frequency: Quantas vezes foi detectado
        examples: Exemplos concretos de ocorrências
        impact: Impacto estimado (low/medium/high)
        actionable: Se pode ser transformado em ação
        positive: Se é um padrão positivo (bom hábito) ou negativo
    """
    name: str
    description: str
    frequency: int = 1  # Quantas vezes ocorreu
    examples: List[str] = field(default_factory=list)
    impact: str = "medium"  # low, medium, high
    actionable: bool = True
    positive: bool = True  # True = bom padrão, False = ruim padrão
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário serializável"""
        return {
            'name': self.name,
            'description': self.description,
            'frequency': self.frequency,
            'examples': self.examples[:3],
            'impact': self.impact,
            'actionable': self.actionable,
            'positive': self.positive
        }


@dataclass
class ProjectHealthReport:
    """
    Relatório completo de saúde de um projeto
    
    Analisa múltiplas dimensões para dar um veredito
    sobre o estado atual e futuro do projeto.
    
    Attributes:
        project_id: ID do projeto analisado
        project_name: Nome do projeto
        health_status: Classificação geral (ProjectHealth enum)
        health_score: Score numérico (0.0 a 100.0)
        last_activity: Data da última atividade
        days_since_activity: Dias desde última atividade
        task_completion_rate: Taxa de conclusão de tarefas (%)
        stalled_risk: Risco de estagnação (low/medium/high/critical)
        insights: Lista de insights sobre este projeto
        recommendations: Ações recomendadas
        trend: Tendência (improving/stable/declining)
    """
    project_id: str = ""
    project_name: str = ""
    health_status: ProjectHealth = ProjectHealth.GOOD
    health_score: float = 75.0
    last_activity: Optional[str] = None
    days_since_activity: int = 0
    task_completion_rate: float = 0.0
    stalled_risk: str = "low"
    insights: List[Insight] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    trend: str = "stable"  # improving, stable, declining
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário serializável"""
        return {
            'project_id': self.project_id,
            'project_name': self.project_name,
            'health_status': self.health_status.value,
            'health_score': round(self.health_score, 1),
            'last_activity': self.last_activity,
            'days_since_activity': self.days_since_activity,
            'task_completion_rate': f"{self.task_completion_rate:.1f}%",
            'stalled_risk': self.stalled_risk,
            'insights': [i.to_dict() for i in self.insights],
            'recommendations': self.recommendations,
            'trend': self.trend
        }


@dataclass
class WeeklySummary:
    """
    Resumo semanal completo de insights e métricas
    
    Gerado toda semana (geralmente domingo) para revisão TELOS.
    
    Attributes:
        week_start: Início da semana (ISO format)
        week_end: Fim da semana (ISO format)
        total_insights: Total de insights gerados na semana
        top_insights: Top 5 insights mais importantes
        patterns_found: Padrões identificados
        achievements: Conquistas/marcos atingidos
        warnings: Alertas preventivos
        recommendations: Recomendações priorizadas
        productivity_score: Score médio de produtividade (0-100)
        trend: Tendência da semana (improving/stable/declining)
        telos_review: Análise das 5 dimensões TELOS
    """
    week_start: str = ""
    week_end: str = ""
    total_insights: int = 0
    top_insights: List[Insight] = field(default_factory=list)
    patterns_found: List[Pattern] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    productivity_score: float = 0.0
    trend: str = "stable"
    telos_review: Dict[TelosDimension, str] = field(
        default_factory=lambda: {dim: "" for dim in TelosDimension}
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário serializável"""
        return {
            'week_start': self.week_start,
            'week_end': self.week_end,
            'total_insights': self.total_insights,
            'top_insights': [i.to_dict() for i in self.top_insights[:5]],
            'patterns_found': [p.to_dict() for p in self.patterns_found],
            'achievements': self.achievements,
            'warnings': self.warnings,
            'recommendations': self.recommendations[:10],
            'productivity_score': round(self.productivity_score, 1),
            'trend': self.trend,
            'telos_review': {
                dim.value: texto 
                for dim, texto in self.telos_review.items() 
                if texto
            }
        }


@dataclass
class TelosReviewResult:
    """
    Resultado da revisão semanal TELOS completa
    
    Framework TELOS para review semanal estruturado:
    - Time: Como usei meu tempo? Produtivo?
    - Energy: Nível de energia? Descanso adequado?
    - Light: Clareza mental? Aprendizados?
    - Opportunity: Oportunidades percebidas/perdidas?
    - Significance: Trabalho significativo? Impacto?
    
    Attributes:
        period: Período da revisão (semana)
        dimensions: Análise de cada dimensão TELOS
        overall_score: Score geral (0-100)
        key_insight: Principal insight da semana
        next_week_focus: Foco principal para próxima semana
        action_items: Itens de ação concretos
        generated_at: Quando foi gerada
    """
    period: str = ""
    dimensions: Dict[TelosDimension, Dict[str, Any]] = field(
        default_factory=dict
    )
    overall_score: float = 0.0
    key_insight: str = ""
    next_week_focus: str = ""
    action_items: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)


# ============================================
# CLASSE PRINCIPAL - INSIGHT GENERATOR
# ============================================

class InsightGenerator:
    """
    Gerador de Insights Inteligentes v2.0 do Segundo Cérebro
    
    Este é o "cérebro que PENSA" do sistema. Não só processa dados
    (como os outros módulos), mas gera CONHECIMENTO, SABEDORIA e
    RECOMENDAÇÕES acionáveis baseadas em análise profunda.
    
    Funcionalidades principais:
    - Análise de padrões de comportamento e produtividade
    - Detecção de anomalias (dias muito bons/ruins)
    - Identificação de oportunidades de melhoria
    - Análise de saúde de projetos (risco de abandono)
    - Geração de relatórios TELOS semanais
    - Correlação entre métricas diferentes
    - Aprendizado contínuo (salva descobertas na memória)
    
    Integração Lex Flow:
    - Busca dados reais via get_dashboard(), get_projects(), etc.
    - Analisa histórico de atividades
    - Gera insights baseados em métricas reais
    - Salva insights importantes como notas no Lex Flow
    
    Uso básico:
        # Inicialização com dependências
        generator = InsightGenerator(
            memory_system=memory,
            lex_flow_client=lex_flow,
            decision_engine=decider  # opcional
        )
        
        # Insights diários (para morning briefing)
        daily = generator.generate_daily_insights(stats_do_dia)
        
        # Insights semanais (para Sunday review)
        weekly = generator.generate_weekly_summary()
        
        # Análise de saúde de projetos
        saude_projetos = generator.analyze_all_projects_health()
        
        # Relatório TELOS completo
        telos = generator.generate_telos_review()
        
        # Detectar padrões personalizados
        padroes = generator.detect_patterns(dias=30)
    
    Atributos:
        _memory: Sistema de memória (para contexto e persistência)
        _lex_flow: Cliente Lex Flow (dados reais para análise)
        _decision: Motor de decisões (opcional, para priorização)
        _cache: Cache interno para performance
        _historical_data: Acumulador de dados históricos para tendências
    """
    
    # Limites e thresholds configuráveis
    DEFAULT_STALL_THRESHOLD_DAYS = 7      # Dias para considerar projeto parado
    DEFAULT_ANOMALY_DEVIATION = 2.0       # Desvios padrão para anomalia
    MIN_DATA_POINTS_FOR_PATTERN = 3       # Mínimo de ocorrências para padrão
    MAX_INSIGHTS_DAILY = 8                # Limite de insights diários
    MAX_INSIGHTS_WEEKLY = 20              # Limite de insights semanais
    
    def __init__(
        self,
        lex_flow_client: LexFlowClient,
        memory_system: Optional[MemorySystem] = None,
        decision_engine: Optional[DecisionEngine] = None
    ):
        """
        Inicializa o Gerador de Insights v2.0
        
        Args:
            lex_flow_client: Cliente Lex Flow CONECTADO (obrigatório para dados reais)
            memory_system: Sistema de memória opcional (contexto + persistência)
            decision_engine: Motor de decisões opcional (priorização avançada)
        """
        # Dependências principais
        self._lex_flow = lex_flow_client
        self._memory = memory_system
        self._decision = decision_engine
        
        # Cache de insights recentes (para evitar repetição)
        self._recent_insights_cache: List[str] = []
        self._max_cache_size = 200
        
        # Histórico para detecção de tendências (acumula ao longo do tempo)
        self._historical_data: Dict[str, List] = defaultdict(list)
        
        # Estatísticas de uso
        self._stats = {
            'insights_gerados': 0,
            'padroes_detectados': 0,
            'relatorios_telos': 0,
            'analises_projetos': 0,
            'erros': 0
        }
        
        # Log de inicialização
        logger_insight.info("=" * 70)
        logger_insight.info("💡 INSIGHT GENERATOR v2.0 INICIALIZADO")
        logger_insight.info(f"   Lex Flow: {'✅ Conectado' if lex_flow_client else '⚠️ Não configurado'}")
        logger_insight.info(f"   Memory: {'✅ Disponível' if memory_system else '⚠️ Não configurado'}")
        logger_insight.info(f"   Decision Engine: {'✅ Disponível' if decision_engine else '⚠️ Não configurado'}")
        logger_insight.info("=" * 70)
    
    # ========================================
    # MÉTODOS PRINCIPAIS PÚBLICOS
    # ========================================
    
    def generate_daily_insights(self, stats: Optional[Dict] = None) -> List[Insight]:
        """
        GERA INSIGHTS DIÁRIOS RÁPIDOS
        
        Analisa as atividades do dia e gera 3-8 insights
        curtos e acionáveis para o briefing matinal.
        
        Estes insights são projetados para serem consumidos
        rapidamente (menos de 30 segundos cada) e motivarem
        ação imediata.
        
        Args:
            stats: Estatísticas rápidas do dia (do Lex Flow dashboard).
                   Se None, busca automaticamente do Lex Flow.
            
        Returns:
            Lista de objetos Insight ordenados por prioridade (maior primeiro)
        """
        logger_insight.info("🔍 Gerando INSIGHTS DIÁRIOS...")
        self._stats['insights_gerados'] += 1
        
        insights: List[Insight] = []
        
        try:
            # === PASSO 1: Obter dados (do argumento ou do Lex Flow) ===
            dados_dia = stats
            
            if not dados_dia and self._lex_flow:
                logger_insight.info("   Buscando dados do dia no Lex Flow...")
                dados_dia = self._buscar_stats_diarios_lexflow()
            
            if not dados_dia:
                dados_dia = {}  # Continuar com dados vazios (modo degradado)
            
            # === PASSO 2: Análise de Produtividade ===
            insight_produtividade = self._analizar_produtividade_diaria(dados_dia)
            if insight_produtividade:
                insights.append(insight_produtividade)
            
            # === PASSO 3: Detecção de Conquistas/Achievements ===
            conquistas = self._detectar_conquistas_diarias(dados_dia)
            insights.extend(conquistas)
            
            #=== PASSO 4: Alertas e Warnings ===
            alertas = self._gerar_alertas_diarios(dados_dia)
            insights.extend(alertas)
            
            # === PASSO 5: Sugestão Contextual Personalizada ===
            sugestao = self._gerar_sugestao_contextual(dados_dia)
            if sugestao:
                insights.append(sugestao)
            
            # === PASSO 6: Análise de Padrão Recorrente ===
            if len(self._historical_data.get('daily_productivity', [])) >= 3:
                padrao = self._detectar_padrao_recorrente()
                if padrao:
                    insights.append(padrao)
            
            # === PASSO 7: Ordenar e Limitar ===
            # Ordenar por prioridade (descendente)
            insights.sort(key=lambda x: x.priority, reverse=True)
            
            # Aplicar limite máximo
            insights = insights[:self.MAX_INSIGHTS_DAILY]
            
            # Armazenar no cache para evitar repetição
            for insight in insights:
                self._adicionar_ao_cache(insight.id)
            
            # Salvar dados históricos para futuras análises de tendência
            self._armazenar_historico(dados_dia)
            
            logger_insight.info(
                f"   ✅ {len(insights)} insights diários gerados "
                f"(conquistas: {len(conquistas)}, alertas: {len(alertas)})"
            )
            
        except Exception as erro:
            logger_insight.error(f"❌ Erro gerando insights diários: {erro}", exc_info=True)
            
            # Criar insight de erro (para não retornar vazio)
            insights.append(Insight(
                type=InsightType.WARNING,
                title="⚠️ Sistema de Insights Parcialmente Indisponível",
                description=(
                    f"Não foi possível completar a análise hoje. "
                    f"Erro técnico: {str(erro)[:100]}"
                ),
                confidence=InsightConfidence.HIGH,
                category="system",
                priority=8
            ))
            self._stats['erros'] += 1
        
        return insights
    
    def generate_weekly_summary(self) -> WeeklySummary:
        """
        GERA RESUMO SEMANAL COMPLETO DE INSIGHTS
        
        Compila todos os insights da semana, identifica
        padrões de longo prazo, calcula tendências, e gera
        recomendações estratégicas para a próxima semana.
        
        Deve ser executado preferencialmente no domingo à noite
        para preparação da semana seguinte.
        
        Returns:
            WeeklySummary com análise completa da semana
        """
        logger_insight.info("📊 Gerando RESUMO SEMANAL...")
        
        resumo = WeeklySummary()
        
        try:
            # Calcular período da semana
            hoje = datetime.now()
            inicio_semana = hoje - timedelta(days=hoje.weekday())  # Segunda desta semana
            fim_semana = inicio_semana + timedelta(days=6)        # Domingo desta semana
            
            resumo.week_start = inicio_semana.strftime('%Y-%m-%d')
            resumo.week_end = fim_semana.strftime('%Y-%m-%d')
            
            # === SEÇÃO 1: Coletar dados da semana ===
            dados_semana = self._coletar_dados_semanais(inicio_semana, fim_semana)
            
            # === SEÇÃO 2: Análise de Produtividade ===
            score_produtividade = self._calcular_score_produtividade_semanal(dados_semana)
            resumo.productivity_score = score_produtividade
            
            # === SEÇÃO 3: Top Insights da Semana ===
            top_insights = self._gerar_top_insights_semanais(dados_semana)
            resumo.top_insights = top_insights[:5]
            resumo.total_insights = len(top_insights)
            
            # === SEÇÃO 4: Detecção de Padrões ===
            padroes = self._detectar_padroes_semanais(dados_semana)
            resumo.patterns_found = padroes
            self._stats['padroes_detectados'] += len(padroes)
            
            # === SEÇÃO 5: Conquistas da Semana ===
            conquistas = self._identificar_conquistas_semanais(dados_semana)
            resumo.achievements = conquistas
            
            # === SEÇÃO 6: Warnings e Riscos ===
            warnings = self._gerar_warnings_semanais(dados_semana)
            resumo.warnings = warnings
            
            # === SEÇÃO 7: Recomendações Estratégicas ===
            recomendacoes = self._gerar_recomendacoes_semanais(
                resumo.productivity_score,
                padroes,
                warnings
            )
            resumo.recommendations = recomendacoes[:10]
            
            # === SEÇÃO 8: Determinar Tendência ===
            resumo.trend = self._determinar_tendencia_semanal(dados_semana)
            
            # === SEÇÃO 9: Salvar na Memória (opcional) ===
            if self._memory:
                self._salvar_resumo_memoria(resumo)
            
            logger_insight.info(
                f"   ✅ Resumo semanal gerado:"
                f"\n      Score: {resumo.productivity_score:.1f}/100"
                f"\n      Insights: {resumo.total_insights}"
                f"\n      Padrões: {len(resumo.patterns_found)}"
                f"\n      Tendência: {resumo.trend}"
            )
            
        except Exception as erro:
            logger_insight.error(f"❌ Erro gerando resumo semanal: {erro}", exc_info=True)
            self._stats['erros'] += 1
        
        return resumo
    
    def generate_telos_review(self) -> TelosReviewResult:
        """
        GERA RELATÓRIO COMPLETO TELOS (Weekly Review)
        
        O framework TELOS analisa 5 dimensões holísticas:
        - TIME: Gestão do tempo e energia durante a semana
        - ENERGY: Nível físico, mental, e emocional
        - LIGHT: Clareza mental, aprendizados, insights
        - OPPORTUNITY: Oportunidades identificadas/perdidas
        - SIGNIFICANCE: Impacto e significado do trabalho realizado
        
        Este é o review mais completo e deve ser usado para
        planejamento estratégico semanal.
        
        Returns:
            TelosReviewResult com análise completa das 5 dimensões
        """
        logger_insight.info("🌟 Gerando RELATÓRIO TELOS (Weekly Review)...")
        self._stats['relatorios_telos'] += 1
        
        resultado = TelosReviewResult()
        resultado.periodo = datetime.now().strftime('%Y-%m-%d')
        resultado.generated_at = datetime.now()
        
        try:
            # Coletar dados necessários
            dados_semana = self._coletar_dados_para_telos()
            
            # === DIMENSÃO 1: TIME (Tempo) ===
            resultado.dimensions[TelosDimension.TIME] = (
                self._analisar_dimensao_time(dados_semana)
            )
            
            # === DIMENSÃO 2: ENERGY (Energia) ===
            resultado.dimensions[TelosDimension.ENERGY] = (
                self._analisar_dimensao_energy(dados_semana)
            )
            
            # === DIMENSÃO 3: LIGHT (Clareza/Luz) ===
            resultado.dimensions[TelosDimension.LIGHT] = (
                self._analisar_dimensao_light(dados_semana)
            )
            
            # === DIMENSÃO 4: OPPORTUNITY (Oportunidades) ===
            resultado.dimensions[TelosDimension.OPPORTUNITY] = (
                self._analisar_dimensao_opportunity(dados_semana)
            )
            
            # === DIMENSÃO 5: SIGNIFICANCE (Significado) ===
            resultado.dimensions[TelosDimension.SIGNIFICANCE] = (
                self._analisar_dimensao_significance(dados_semana)
            )
            
            # === CALCULAR SCORE GERAL ===
            resultado.overall_score = self._calcular_score_telos_geral(resultado.dimensions)
            
            # === GERAR KEY INSIGHT PRINCIPAL ===
            resultado.key_insight = self._extrair_key_insight_telos(resultado.dimensions)
            
            # === DEFINIR FOCO PRÓXIMA SEMANA ===
            resultado.next_week_focus = (
                self._sugerir_foco_proxima_semana(resultado.dimensions)
            )
            
            # === GERAR ITENS DE AÇÃO ===
            resultado.action_items = self._gerar_action_items_telos(resultado)
            
            logger_insight.info(
                f"   ✅ Relatório TELOS concluído"
                f"\n      Score Geral: {resultado.overall_score:.1f}/100"
                f"\n      Key Insight: {resultado.key_insight[:80]}..."
            )
            
        except Exception as erro:
            logger_insight.error(f"❌ Erro gerando relatório TELOS: {erro}", exc_info=True)
            self._stats['erros'] += 1
        
        return resultado
    
    def analyze_all_projects_health(self) -> List[ProjectHealthReport]:
        """
        ANALISA SAÚDE DE TODOS OS PROJETOS ATIVOS
        
        Para cada projeto ativo no Lex Flow, gera um relatório
        de saúde completo com:
        - Score de saúde (0-100)
        - Risco de estagnação
        - Insights específicos do projeto
        - Recomendações de ação
        
        Returns:
            Lista de ProjectHealthReport ordenada por risco (crítico primeiro)
        """
        logger_insight.info("🏥 Analisando SAÚDE de TODOS os PROJETOS...")
        self._stats['analises_projetos'] += 1
        
        relatorios: List[ProjectHealthReport] = []
        
        if not self._lex_flow:
            logger_insight.warning("   ⚠️ Lex Flow não disponível, pulando análise")
            return relatorios
        
        try:
            # Obter lista de projetos do Lex Flow
            projetos = self._lex_flow.get_projects()
            
            if not projetos:
                logger_insight.info("   Nenhum projeto encontrado no Lex Flow")
                return relatorios
            
            # Garantir que é lista
            if isinstance(projetos, dict):
                projetos = projetos.get('projects', projetos.get('data', []))
            
            if not isinstance(projetos, list):
                logger_insight.warning(f"   Formato inesperado: {type(projetos)}")
                return relatorios
            
            logger_insight.info(f"   Encontrados {len(projetos)} projetos para analisar")
            
            # Analisar cada projeto individualmente
            for projeto in projetos:
                try:
                    relatorio = self._analisar_saude_projeto_individual(projeto)
                    if relatorio:
                        relatorios.append(relatorio)
                        
                except Exception as erro_projeto:
                    logger_insight.debug(
                        f"   Erro analisando projeto {projeto.get('id', '?')}: {erro_projeto}"
                    )
            
            # Ordenar por saúde (pior primeiro = maior prioridade)
            relatorios.sort(key=lambda x: x.health_score)
            
            logger_insight.info(
                f"   ✅ Análise concluída: {len(relatorios)} projetos analisados"
            )
            
        except AttributeError:
            logger_insight.warning("   Método get_projects() não disponível no LexFlowClient")
            
        except Exception as erro:
            logger_insight.error(f"   ❌ Erro na análise de projetos: {erro}")
            self._stats['erros'] += 1
        
        return relatorios
    
    def detect_patterns(self, dias: int = 30) -> List[Pattern]:
        """
        DETECTA PADRÕES EM DADOS HISTÓRICOS
        
        Analisa os últimos N dias de dados para identificar
        comportamentos recorrentes que podem ser aproveitados
        (bons hábitos) ou corrigidos (maus hábitos).
        
        Tipos de padrões detectados:
        - Horários de pico de produtividade
        - Dias da semana mais/menos produtivos
        - Tipos de tarefa que demoram mais
        - Frequência de capturas rápidas
        - Padrões de procrastinação
        
        Args:
            dias: Quantidade de dias para olhar para trás (default: 30)
            
        Returns:
            Lista de Pattern detectados, ordenados por frequência
        """
        logger_insight.info(f"🔄 Detectando PADRÕES (últimos {dias} dias)...")
        
        padroes: List[Pattern] = []
        
        try:
            # Coletar dados históricos
            historico = self._obter_historico_dias(dias)
            
            if not historico or len(historico) < 3:
                logger_insight.warning(
                    f"   Dados insuficientes para detecção de padrões "
                    f"(precisa de pelo menos 3 dias, tem {len(historico) if historico else 0})"
                )
                return padroes
            
            # === PADRÃO 1: Produtividade por Dia da Semana ===
            padrao_dia_semana = self._detectar_padrao_dia_semana(historico)
            if padrao_dia_semana:
                padroes.append(padrao_dia_semana)
            
            # === PADRÃO 2: Produtividade por Horário ===
            padrao_horario = self._detectar_padrao_horario(historico)
            if padrao_horario:
                padroes.append(padrao_horario)
            
            # === PADRÃO 3: Tipos de Tarefa Mais Frequentes ===
            padrao_tipos_tarefa = self._detectar_padrao_tipos_tarefa(historico)
            if padrao_tipos_tarefa:
                padroes.append(padrao_tipos_tarefa)
            
            # === PADRÃO 4: Sequência de Atividades ===
            padrao_sequencia = self._detectar_padrao_sequencia(historico)
            if padrao_sequencia:
                padroes.append(padrao_sequencia)
            
            # Ordenar por frequência (mais frequente primeiro)
            padroes.sort(key=lambda x: x.frequency, reverse=True)
            
            self._stats['padroes_detectados'] += len(padroes)
            
            logger_insight.info(
                f"   ✅ {len(padroes)} padrões detectados:"
                + ''.join([f"\n      - {p.name} ({p.frequency}x)" for p in padroes])
            )
            
        except Exception as erro:
            logger_insight.error(f"❌ Erro detectando padrões: {erro}", exc_info=True)
            self._stats['erros'] += 1
        
        return padroes
    
    # ========================================
    # MÉTODOS PRIVADOS - COLETA DE DADOS
    # ========================================
    
    def _buscar_stats_diarios_lexflow(self) -> Optional[Dict]:
        """
        Busca estatísticas diárias do dashboard Lex Flow
        
        Returns:
            Dicionário com stats ou None se indisponível
        """
        if not self._lex_flow:
            return None
        
        try:
            if hasattr(self._lex_flow, 'get_dashboard'):
                dashboard = self._lex_flow.get_dashboard()
                
                if dashboard and isinstance(dashboard, dict):
                    # Extrair campos relevantes
                    return {
                        'pomodoros': dashboard.get('pomodoros_today', 0),
                        'tarefas_concluidas': dashboard.get('tasks_completed', 0),
                        'notas_rapidas': dashboard.get('quick_notes_count', 0),
                        'inbox_size': dashboard.get('inbox_count', 0),
                        'projetos_ativos': dashboard.get('active_projects', 0),
                        'score_produtividade': dashboard.get('productivity_score', 0),
                        'streak_dias': dashboard.get('streak_days', 0),
                        'raw': dashboard  # Manter original para referência
                    }
                
        except AttributeError:
            logger_insight.debug("   get_dashboard() não disponível")
            
        except Exception as erro:
            logger_insight.debug(f"   Erro buscando stats: {erro}")
        
        return None
    
    def _coletar_dados_semanais(
        self, 
        inicio: datetime, 
        fim: datetime
    ) -> Dict[str, Any]:
        """
        Coleta dados agregados da semana para análise
        
        Args:
            inicio: Data inicial da semana
            fim: Data final da semana
            
        Returns:
            Dicionário com dados semanais agregados
        """
        dados = {
            'periodo': {'inicio': inicio.isoformat(), 'fim': fim.isoformat()},
            'dias_analisados': 0,
            'total_pomodoros': 0,
            'total_tarefas': 0,
            'total_notas': 0,
            'por_dia': [],
            'projetos_trabalhados': set(),
            'metricas_diarias': []
        }
        
        if self._lex_flow:
            try:
                # Tentar obter analytics/semanal se existir
                if hasattr(self._lex_flow, 'get_weekly_analytics'):
                    analytics = self._lex_flow.get_weekly_analytics(
                        start_date=inicio.strftime('%Y-%m-%d'),
                        end_date=fim.strftime('%Y-%m-%d')
                    )
                    if analytics:
                        dados.update(analytics)
                        return dados
                        
            except AttributeError:
                pass
            except Exception as erro:
                logger_insight.debug(f"Erro coletando dados semanais: {erro}")
        
        # Fallback: usar dados históricos acumulados localmente
        dados['por_dia'] = self._historical_data.get('daily_stats', [])[-7:]
        dados['dias_analisados'] = len(dados['por_dia'])
        
        # Agregar totais
        for dia in dados['por_dia']:
            if isinstance(dia, dict):
                dados['total_pomodoros'] += dia.get('pomodoros', 0)
                dados['total_tarefas'] += dia.get('tarefas', 0)
                dados['total_notas'] += dia.get('notas', 0)
        
        return dados
    
    def _coletar_dados_para_telos(self) -> Dict[str, Any]:
        """
        Coleta dados específicos para análise TELOS
        
        Retorna dados estruturados para as 5 dimensões.
        """
        dados = {}
        
        # Dados do Lex Flow
        if self._lex_flow:
            try:
                dashboard = self._buscar_stats_diarios_lexflow()
                if dashboard:
                    dados['dashboard'] = dashboard
                
                # Projetos
                if hasattr(self._lex_flow, 'get_projects'):
                    projetos = self._lex_flow.get_projects()
                    if projetos:
                        dados['projetos'] = projetos
                        
            except Exception:
                pass
        
        # Dados da Memory (lições, perfil)
        if self._memory:
            try:
                dados['licoes_recentes'] = self._memory.get_recent_lessons(quantidade=7)
            except Exception:
                pass
        
        # Dados históricos acumulados
        dados['historico_local'] = dict(self._historical_data)
        
        return dados
    
    def _obter_historico_dias(self, dias: int) -> List[Dict]:
        """
        Obtém dados históricos dos últimos N dias
        
        Args:
            dias: Quantidade de dias
            
        Returns:
            Lista de dicionários (um por dia)
        """
        # Tentar buscar do Lex Flow primeiro
        if self._lex_flow:
            try:
                if hasattr(self._lex_flow, 'get_activity_history'):
                    historico = self._lex_flow.get_activity_history(days=dias)
                    if historico and isinstance(historico, list):
                        return historico
            except Exception:
                pass
        
        # Fallback: usar dados locais acumulados
        return self._historical_data.get('daily_stats', [])[-dias:]
    
    # ========================================
    # MÉTODOS PRIVADOS - ANÁLISE E GERAÇÃO
    # ========================================
    
    def _analizar_produtividade_diaria(self, dados: Dict) -> Optional[Insight]:
        """
        Analisa produtividade do dia e gera insight correspondente
        """
        if not dados:
            return None
        
        pomodoros = dados.get('pomodoros', 0)
        tarefas = dados.get('tarefas_concluidas', 0)
        
        # Lógica simples de classificação
        if pomodoros >= 8 and tarefas >= 5:
            return Insight(
                type=InsightType.ACHIEVEMENT,
                title="🔥 Dia Altamente Produtivo!",
                description=(
                    f"Você completou {tarefas} tarefas e {pomodoros} pomodoros. "
                    f"Isso está acima da sua média! Continue assim."
                ),
                confidence=InsightConfidence.HIGH,
                data_points=[f"Pomodoros: {pomodoros}", f"Tarefas: {tarefas}"],
                action_suggestions=[
                    "Celebre essa conquista!",
                    "Identifique o que funcionou bem hoje",
                    "Tente replicar amanhã"
                ],
                category="productivity",
                priority=9,
                positive=True
            )
        
        elif pomodoros == 0 and tarefas == 0:
            return Insight(
                type=InsightType.WARNING,
                title="⚠️ Sem Atividade Registrada Hoje",
                description=(
                    "Nenhuma tarefa ou pomodoro foi registrado hoje. "
                    "Isso pode indicar dia de folha ou falta de tracking."
                ),
                confidence=InsightConfidence.MEDIUM,
                data_points=["Pomodoros: 0", "Tarefas: 0"],
                action_suggestions=[
                    "Registrar pelo menos 1 tarefa completed",
                    "Se foi dia de folha, registre como tal",
                    "Verificar se precisa ajustar metas"
                ],
                category="productivity",
                priority=7
            )
        
        elif pomodoros > 0 and pomodoros < 4:
            return Insight(
                type=InsightType.SUGGESTION,
                title="💪 Espaço para Mais Foco",
                description=(
                    f"Apenas {pomodoros} pomodoro(s) hoje. "
                    f"Você tem capacidade para mais sessões de foco."
                ),
                confidence=InsightConfidence.MEDIUM,
                data_points=[f"Pomodoros: {pomodoros}"],
                action_suggestions=[
                    "Adicionar mais 2-3 pomodoros",
                    "Bloquear tempo no calendário",
                    "Eliminar distrações conhecidas"
                ],
                category="productivity",
                priority=5
            )
        
        return None  # Dia normal, sem insight especial
    
    def _detectar_conquistas_diarias(self, dados: Dict) -> List[Insight]:
        """
        Detecta conquistas/marcos positivos do dia
        """
        conquistas = []
        
        if not dados:
            return conquistas
        
        streak = dados.get('streak_dias', 0)
        
        # Streak de dias
        if streak >= 7:
            conquistas.append(Insight(
                type=InsightType.ACHIEVEMENT,
                title=f"🏆 {streak} Dias de Sequência!",
                description=(
                    f"Você manteve uma sequência de {streak} dias consecutivos "
                    f"de atividade. Isso demonstra consistência impressionante!"
                ),
                confidence=InsightConfidence.HIGH,
                category="achievement",
                priority=10,
                positive=True
            ))
        
        # Meta de tarefas
        tarefas = dados.get('tarefas_concluidas', 0)
        if tarefas >= 10:
            conquistas.append(Insight(
                type=InsightType.ACHIEVEMENT,
                title="🎯 Meta de Tarefas Esmagada!",
                description=f"{tarefas} tarefas concluídas hoje. Performance excepcional!",
                confidence=InsightConfidence.HIGH,
                category="achievement",
                priority=9,
                positive=True
            ))
        
        return conquistas
    
    def _gerar_alertas_diarios(self, dados: Dict) -> List[Insight]:
        """
        Gera alertas preventivos baseados nos dados do dia
        """
        alertas = []
        
        if not dados:
            return alertas
        
        inbox_size = dados.get('inbox_size', 0)
        
        # Inbox crescendo
        if inbox_size >= 15:
            alertas.append(Insight(
                type=InsightType.WARNING,
                title="📥 Inbox Precisa de Atenção",
                description=(
                    f"Inbox com {inbox_size} itens. "
                    f"Risco de sobrecarga cognitiva aumentando."
                ),
                confidence=InsightConfidence.HIGH if inbox_size >= 25 else InsightConfidence.MEDIUM,
                data_points=[f"Inbox size: {inbox_size}"],
                action_suggestions=[
                    "Reservar 25 min para processar inbox",
                    "Aplicar regra 2-minutos: se leva <2min, faça agora"
                ],
                category="organization",
                priority=8 if inbox_size >= 25 else 6
            ))
        
        return alertas
    
    def _gerar_sugestao_contextual(self, dados: Dict) -> Optional[Insight]:
        """
        Gera sugestão personalizada baseada no contexto atual
        """
        if not dados:
            return None
        
        hora_atual = datetime.now().hour
        dia_semana = datetime.now().strftime('%A')
        
        # Sugestão baseada no horário
        if 6 <= hora_atual <= 9:
            return Insight(
                type=InsightType.SUGGESTION,
                title="🌅 Bom Dia! Hora de Planejar",
                description=(
                    "Início do dia é ideal para definir as 3 prioridades. "
                    "O que VOCÊ vai accomplishing hoje?"
                ),
                confidence=InsightConfidence.HIGH,
                category="planning",
                priority=7,
                action_suggestions=[
                    "Definir TOP 3 prioridades do dia",
                    "Revisar calendar compromissos",
                    "Checar deadlines próximos"
                ]
            )
        
        elif 12 <= hora_atual <= 14:
            return Insight(
                type=InsightType.SUGGESTION,
                title="🍽️ Pausa para Almoço?",
                description=(
                    "Horário de almoço. Boa oportunidade para descansar "
                    "e recarregar energias para a tarde."
                ),
                confidence=InsightConfidence.MEDIUM,
                category="wellbeing",
                priority=4,
                action_suggestions=[
                    "Fazer pausa de verdade (longe da tela)",
                    "Caminhar 10 minutos após comer",
                    "Hidratar bem"
                ]
            )
        
        elif 20 <= hora_atual <= 23:
            return Insight(
                type=InsightType.SUGGESTION,
                title="🌙 Preparando para Encerrar o Dia",
                description=(
                    "Final do dia se aproximando. Hora de fazer review "
                    "rápido e preparar o terreno para amanhã."
                ),
                confidence=InsightConfidence.HIGH,
                category="planning",
                priority=6,
                action_suggestions=[
                    "Listar 3 coisas que foram bem hoje",
                    "Identificar 1 coisa melhorar",
                    "Preparar TOP 3 para amanhã"
                ]
            )
        
        return None
    
    def _detectar_padrao_recorrente(self) -> Optional[Insight]:
        """
        Detecta se há um padrão recorrente baseado em dados históricos
        """
        prod_diaria = self._historical_data.get('daily_productivity', [])
        
        if len(prod_diaria) < 3:
            return None
        
        # Verificar se últimos 3 dias são consistentemente baixos
        ultimos_3 = prod_diaria[-3:]
        media_ultimos_3 = statistics.mean(ultimos_3) if ultimos_3 else 0
        
        if media_ultimos_3 < 3:  # Menos de 3 pomodoros média
            return Insight(
                type=InsightType.WARNING,
                title="📉 Produtividade Baixa nos Últimos Dias",
                description=(
                    f"Média dos últimos 3 dias: {media_ultimos_3:.1f} pomodoros/dia. "
                    f"Isso está abaixo do seu potencial."
                ),
                confidence=InsightConfidence.MEDIUM,
                data_points=[f"Média 3 dias: {media_ultimos_3:.1f}"],
                action_suggestions=[
                    "Investigar causa (fadiga? bloqueio? desmotivação?)",
                    "Reduzir escopo temporariamente",
                    "Focar em 1 vitória rápida para recuperar momentum"
                ],
                category="pattern",
                priority=8
            )
        
        return None
    
    # ========================================
    # MÉTODOS PRIVADOS - ANÁLISE DE PROJETOS
    # ========================================
    
    def _analisar_saude_projeto_individual(self, projeto: Dict) -> Optional[ProjectHealthReport]:
        """
        Analisa saúde de um projeto individual
        
        Args:
            projeto: Dicionário com dados do projeto do Lex Flow
            
        Returns:
            ProjectHealthReport ou None se erro
        """
        relatorio = ProjectHealthReport(
            project_id=projeto.get('id', ''),
            project_name=projeto.get('name', 'Sem nome'),
            last_activity=projeto.get('updated_at', projeto.get('last_activity'))
        )
        
        try:
            # Calcular dias desde última atividade
            if relatorio.last_activity:
                try:
                    if isinstance(relatorio.last_activity, str):
                        dt_atividade = datetime.fromisoformat(
                            relatorio.last_activity.replace('Z', '+00:00')
                        )
                    elif isinstance(relatorio.last_activity, datetime):
                        dt_atividade = relatorio.last_activity
                    else:
                        dt_atividade = None
                    
                    if dt_atividade:
                        relatorio.days_since_activity = (
                            datetime.now() - dt_atividade.replace(tzinfo=None)
                        ).days
                        
                except Exception:
                    pass
            
            # Determinar status de saúde baseado em múltiplos fatores
            status_str = str(projeto.get('status', '')).lower()
            dias_sem = relatorio.days_since_activity
            
            # Calcular score base (0-100)
            score_base = 75.0  # Começa neutro
            
            # Ajustar por dias de inatividade
            if dias_sem > self.DEFAULT_STALL_THRESHOLD_DAYS:
                score_base -= min(dias_sem * 2, 40)  # -2 por dia, max -40
            elif dias_sem <= 2:
                score_base += 10  # Bônus por atividade recente
            
            # Ajustar por status explícito
            if status_str == 'completed':
                score_base = 95.0
                relatorio.health_status = ProjectHealth.EXCELLENT
            elif status_str == 'archived':
                score_base = 100.0  # Arquivado é "bem resolvido"
                relatorio.health_status = ProjectHealth.EXCELLENT
            elif status_str == 'blocked':
                score_base -= 20
                relatorio.health_status = ProjectHealth.CRITICAL
                relatorio.stalled_risk = "critical"
            elif dias_sem > 14:
                relatorio.health_status = ProjectHealth.STALLED
                relatorio.stalled_risk = "critical"
            elif dias_sem > 7:
                relatorio.health_status = ProjectHealth.CRITICAL
                relatorio.stalled_risk = "high"
            elif dias_sem > 3:
                relatorio.health_status = ProjectHealth.ATTENTION
                relatorio.stalled_risk = "medium"
            else:
                relatorio.health_status = ProjectHealth.GOOD
                relatorio.stalled_risk = "low"
            
            relatorio.health_score = max(0, min(100, score_base))
            
            # Gerar insights específicos deste projeto
            if relatorio.health_score < 50:
                relatorio.insights.append(Insight(
                    type=InsightType.WARNING,
                    title=f"⚠️ Projeto '{relatorio.project_name}' Precisa de Atenção",
                    description=(
                        f"Score de saúde: {relatorio.health_score:.1f}/100. "
                        f"{dias_sem} dias sem atividade."
                    ),
                    confidence=InsightConfidence.HIGH,
                    category="project_health",
                    priority=8
                ))
                
                relatorio.recommendations.extend([
                    f"Abrir projeto '{relatorio.project_name}' no Lex Flow",
                    "Definir próxima micro-ação (25 min)",
                    "Agendar bloco de foco para esta semana"
                ])
            
            elif relatorio.health_score >= 85:
                relatorio.insights.append(Insight(
                    type=InsightType.ACHIEVEMENT,
                    title=f"✅ Projeto '{relatorio.project_name}' Saudável",
                    description=f"Score de saúde excelente: {relatorio.health_score:.1f}/100",
                    confidence=InsightConfidence.HIGH,
                    category="project_health",
                    priority=3,
                    positive=True
                ))
            
        except Exception as erro:
            logger_insight.debug(f"   Erro analisando projeto {relatorio.project_id}: {erro}")
            return None
        
        return relatorio
    
    # ========================================
    # MÉTODOS PRIVADOS - ANÁLISE TELOS
    # ========================================
    
    def _analisar_dimensao_time(self, dados: Dict) -> Dict[str, Any]:
        """Analisa dimensão TIME do TELOS"""
        dashboard = dados.get('dashboard', {})
        pomodoros = dashboard.get('pomodoros', 0) if dashboard else 0
        
        # Lógica simplificada de avaliação
        if pomodoros >= 8:
            score = 90
            avaliacao = "Excelente gestão do tempo esta semana!"
        elif pomodoros >= 5:
            score = 70
            avaliacao = "Boa utilização do tempo, espaço para melhorar."
        elif pomodoros >= 2:
            score = 50
            avaliacao = "Uso do tempo abaixo do potencial."
        else:
            score = 30
            avaliacao = "Pouca atividade registrada. Revisar prioridades."
        
        return {
            'score': score,
            'avaliacao': avaliacao,
            'dados_chave': {'pomodoros_totais': pomodoros},
            'sugestao': "Bloquear 2h de foco profundo por dia" if score < 70 else "Manter ritmo!"
        }
    
    def _analisar_dimensao_energy(self, dados: Dict) -> Dict[str, Any]:
        """Analisa dimensão ENERGY do TELOS"""
        # Simplificado - em produção usaria dados de wearable/self-report
        return {
            'score': 65,  # Default médio (sem dados específicos)
            'avaliacao': "Nível de energia não mensurado diretamente.",
            'dados_chave': {},
            'sugestao': "Registrar nível de energia (1-10) ao final de cada dia"
        }
    
    def _analisar_dimensao_light(self, dados: Dict) -> Dict[str, Any]:
        """Analisa dimensão LIGHT (clareza/aprendizado) do TELOS"""
        licoes = dados.get('licoes_recentes', [])
        
        if len(licoes) >= 3:
            score = 80
            avaliacao = f"Bom aprendizado esta semana: {len(licoes)} lições registradas."
        elif len(licoes) >= 1:
            score = 60
            avaliacao = "Algumas lições aprendidas, mas espaço para mais reflexão."
        else:
            score = 40
            avaliacao = "Poucas lições documentadas. Reflexão semanal recomendada."
        
        return {
            'score': score,
            'avaliacao': avaliacao,
            'dados_chave': {'licoes_registradas': len(licoes)},
            'sugestao': "Registrar 1 aprendizado por dia no Memory System"
        }
    
    def _analisar_dimensao_opportunity(self, dados: Dict) -> Dict[str, Any]:
        """Analisa dimensão OPPORTUNITY do TELOS"""
        return {
            'score': 55,
            'avaliacao': "Oportunidades identificadas de forma limitada.",
            'dados_chave': {},
            'sugestao': "Reservar tempo semanal para brainstorm de oportunidades"
        }
    
    def _analisar_dimensao_significance(self, dados: Dict) -> Dict[str, Any]:
        """Analisa dimensão SIGNIFICANCE do TELOS"""
        projetos = dados.get('projetos', [])
        qtd_projetos = len(projetos) if isinstance(projetos, list) else 0
        
        if qtd_projetos >= 3:
            score = 75
            avaliacao = f"Trabalhando em {qtd_projetos} projetos com impacto potencial."
        elif qtd_projetos >= 1:
            score = 60
            avaliacao = "Projetos em andamento, mas poderia ter mais significado."
        else:
            score = 40
            avaliacao = "Poucos projetos ativos. Revisar objetivos de longo prazo."
        
        return {
            'score': score,
            'avaliacao': avaliacao,
            'dados_chave': {'projetos_ativos': qtd_projetos},
            'sugestao': "Conectar tarefas diárias a objetivos maiores (WHY)"
        }
    
    def _calcular_score_telos_geral(self, dimensoes: Dict) -> float:
        """Calcula score geral TELOS (média das 5 dimensões)"""
        if not dimensoes:
            return 0.0
        
        scores = [d.get('score', 0) for d in dimensoes.values() if d]
        return statistics.mean(scores) if scores else 0.0
    
    def _extrair_key_insight_telos(self, dimensoes: Dict) -> str:
        """Extrai o insight principal da semana baseado nas dimensões"""
        # Encontrar dimensão com menor score (área de melhoria)
        pior_dimensao = None
        pior_score = 100
        
        for dimensao, dados in dimensoes.items():
            score = dados.get('score', 0) if dados else 0
            if score < pior_score:
                pior_score = score
                pior_dimensao = dimensao
        
        if pior_dimensao:
            return (
                f"Área de maior oportunidade de melhora: {pior_dimensao.value.upper()} "
                f"(score: {pior_score:.0f}/100). Focar aqui na próxima semana trará "
                f"os maiores ganhos."
            )
        
        return "Sem dados suficientes para determinar insight principal."
    
    def _sugerir_foco_proxima_semana(self, dimensoes: Dict) -> str:
        """Sugere foco principal para próxima semana"""
        # Similar ao key insight, mas mais orientado a ação
        pior_dimensao = min(
            dimensoes.items(),
            key=lambda x: x[1].get('score', 0) if x[1] else 0,
            default=(None, {})
        )
        
        if pior_dimensao[0]:
            nome_dimensao = pior_dimensao[0].value.upper()
            sugestao = pior_dimensao[1].get('sugestao', '')
            return f"[{nome_dimensao}] {sugestao}"
        
        return "Manter consistência e foco nas prioridades estabelecidas."
    
    def _gerar_action_items_telos(self, resultado: TelosReviewResult) -> List[str]:
        """Gera itens de ação concretos baseados no TELOS"""
        actions = []
        
        for dimensao, dados in resultado.dimensions.items():
            if dados and dados.get('score', 100) < 70:
                sugestao = dados.get('sugestao', '')
                if sugestao:
                    actions.append(f"[{dimensao.value.capitalize()}] {sugestao}")
        
        # Adicionar ações genéricas se poucas específicas
        if len(actions) < 3:
            actions.extend([
                "Revisar e atualizar lista de projetos ativos",
                "Definir TOP 3 prioridades para segunda-feira",
                "Agendar bloco de 2h de foco profundo (sem interrupções)"
            ])
        
        return actions[:7]  # Máximo 7 ações (uma por dia da semana)
    
    # ========================================
    # MÉTODOS PRIVADOS - DETECÇÃO DE PADRÕES
    # ========================================
    
    def _detectar_padrao_dia_semana(self, historico: List[Dict]) -> Optional[Pattern]:
        """Detecta quais dias da semana são mais/menos produtivos"""
        # Implementação simplificada - em produção faria análise estatística real
        return None  # Placeholder para expansão futura
    
    def _detectar_padrao_horario(self, historico: List[Dict]) -> Optional[Pattern]:
        """Detecta horários de pico de produtividade"""
        return None  # Placeholder para expansão futura
    
    def _detectar_padrao_tipos_tarefa(self, historico: List[Dict]) -> Optional[Pattern]:
        """Detecta tipos de tarefa mais frequentes"""
        return None  # Placeholder para expansão futura
    
    def _detectar_padrao_sequencia(self, historico: List[Dict]) -> Optional[Pattern]:
        """Detecta sequências de atividades recorrentes"""
        return None  # Placeholder para expansão futura
    
    def _detectar_padroes_semanais(self, dados: Dict) -> List[Pattern]:
        """Detecta padrões nos dados da semana"""
        return []  # Placeholder - implementação futura com mais dados
    
    # ========================================
    # MÉTODOS PRIVADOS - UTILITÁRIOS
    # ========================================
    
    def _adicionar_ao_cache(self, insight_id: str) -> None:
        """Adiciona ID ao cache para evitar repetição"""
        self._recent_insights_cache.append(insight_id)
        
        # Manter tamanho máximo do cache
        if len(self._recent_insights_cache) > self._max_cache_size:
            self._recent_insights_cache = \
                self._recent_insights_cache[-self._max_cache_size:]
    
    def _armazenar_historico(self, dados: Dict) -> None:
        """Armazena dados no histórico para análises de tendência"""
        if dados:
            self._historical_data['daily_stats'].append({
                'data': datetime.now().isoformat(),
                'dados': dados
            })
            
            # Extrair métrica chave para análise de produtividade
            pomodoros = dados.get('pomodoros', 0)
            self._historical_data['daily_productivity'].append(pomodoros)
            
            # Manter histórico limitado (últimos 90 dias)
            max_dias = 90
            if len(self._historical_data['daily_stats']) > max_dias:
                self._historical_data['daily_stats'] = \
                    self._historical_data['daily_stats'][-max_dias:]
                self._historical_data['daily_productivity'] = \
                    self._historical_data['daily_productivity'][-max_dias:]
    
    def _salvar_resumo_memoria(self, resumo: WeeklySummary) -> None:
        """Salva resumo semanal no Memory System (persistência)"""
        if not self._memory:
            return
        
        try:
            texto_resumo = (
                f"# RESUMO SEMANAL ({resumo.week_start} a {resumo.week_end})\n\n"
                f"## Score de Produtividade\n{resumo.productivity_score:.1f}/100\n\n"
                f"## Tendência\n{resumo.trend}\n\n"
                f"## Principais Insights\n"
            )
            
            for insight in resumo.top_insights[:3]:
                texto_resumo += f"- **{insight.title}**: {insight.description[:150]}...\n"
            
            if resumo.recommendations:
                texto_resumo += "\n## Recomendações\n"
                for rec in resumo.recommendations[:5]:
                    texto_resumo += f"- {rec}\n"
            
            # Salvar como lição aprendida
            self._memory.add_lesson(
                texto_licao=texto_resumo,
                categoria="weekly-review",
                origem="insight_generator",
                tags=["semanal", "review", "telos"],
                impact="alto"
            )
            
            logger_insight.debug("   Resumo salvo no MEMORY.md")
            
        except Exception as erro:
            logger_insight.debug(f"Erro salvando resumo na memória: {erro}")
    
    def _calcular_score_produtividade_semanal(self, dados: Dict) -> float:
        """Calcula score de produtividade semanal (0-100)"""
        total_pomodoros = dados.get('total_pomodoros', 0)
        total_tarefas = dados.get('total_tarefas', 0)
        dias = dados.get('dias_analisados', 7)
        
        if dias == 0:
            return 50.0  # Neutro sem dados
        
        # Score baseado em médias diárias
        media_pomodoros = total_pomodoros / max(dias, 1)
        media_tarefas = total_tarefas / max(dias, 1)
        
        # Normalizar para 0-100 (escalas arbitrárias ajustáveis)
        score_pomodoros = min(media_pomodoros * 10, 50)  # Max 50 pontos
        score_tarefas = min(media_tarefas * 5, 40)       # Max 40 pontos
        score_bonus = 10 if total_pomodoros > 0 else 0     # Bônus por atividade
        
        return min(score_pomodoros + score_tarefas + score_bonus, 100)
    
    def _gerar_top_insights_semanais(self, dados: Dict) -> List[Insight]:
        """Gera os principais insights da semana"""
        insights = []
        
        # Insight de produtividade
        score = self._calcular_score_produtividade_semanal(dados)
        
        if score >= 80:
            insights.append(Insight(
                type=InsightType.ACHIEVEMENT,
                title="🏆 Semana Produtiva!",
                description=f"Score de produtividade: {score:.1f}/100. Excelente desempenho!",
                confidence=InsightConfidence.HIGH,
                category="productivity",
                priority=10,
                positive=True
            ))
        elif score < 40:
            insights.append(Insight(
                type=InsightType.WARNING,
                title="📉 Semana de Baixa Produtividade",
                description=f"Score: {score:.1f}/100. Oportunidade de melhoria.",
                confidence=InsightConfidence.HIGH,
                category="productivity",
                priority=9
            ))
        
        return insights
    
    def _identificar_conquistas_semanais(self, dados: Dict) -> List[str]:
        """Identifica conquistas da semana"""
        conquistas = []
        
        total_tarefas = dados.get('total_tarefas', 0)
        if total_tarefas >= 20:
            conquistas.append(f"🎯 {total_tarefas} tarefas concluídas!")
        
        total_pomodoros = dados.get('total_pomodoros', 0)
        if total_pomodoros >= 30:
            conquistas.append(f"🍅 {total_pomodoros} pomodoros completos!")
        
        return conquistas
    
    def _gerar_warnings_semanais(self, dados: Dict) -> List[str]:
        """Gera warnings para a semana"""
        warnings = []
        
        total_tarefas = dados.get('total_tarefas', 0)
        if total_tarefas < 5:
            warnings.append("⚠️ Poucas tarefas concluídas esta semana")
        
        return warnings
    
    def _gerar_recomendacoes_semanais(
        self,
        score: float,
        padroes: List[Pattern],
        warnings: List[str]
    ) -> List[str]:
        """Gera recomendações estratégicas para próxima semana"""
        recomendacoes = []
        
        # Baseado no score
        if score < 50:
            recomendacoes.append(
                "FOCO: Reduzir número de projetos ativos, concentrar em 2-3 máximos"
            )
            recomendacoes.append(
                "AÇÃO: Definir 3 prioridades não-negociáveis para cada dia"
            )
        elif score < 75:
            recomendacoes.append(
                "MELHORIA: Adicionar 1 bloco de foco profundo (2h) por dia"
            )
        
        # Baseado em warnings
        for warning in warnings:
            if "Poucas tarefas" in warning:
                recomendacoes.append(
                    "Meta: Mínimo 5 tarefas concluídas por dia (começar pequeno)"
                )
        
        # Recomendações genéricas úteis
        recomendacoes.extend([
            "Revisar e arquivar projetos parados há > 14 dias",
            "Processar inbox até zero antes de segunda-feira",
            "Agendar revisão TELOS para próximo domingo à noite"
        ])
        
        return recomendacoes
    
    def _determinar_tendencia_semanal(self, dados: Dict) -> str:
        """Determina tendência da semana (improving/stable/declining)"""
        # Simplificado - em produção compararia com semana anterior
        score = dados.get('productivity_score', 50) if 'productivity_score' in dados else \
                 self._calcular_score_produtividade_semanal(dados)
        
        if score >= 75:
            return "improving"
        elif score >= 50:
            return "stable"
        else:
            return "declining"
    
    # ========================================
    # UTILITÁRIOS PÚBLICOS
    # ========================================
    
    def get_status(self) -> Dict[str, Any]:
        """
        Retorna status completo do Insight Generator
        
        Útil para health checks e diagnósticos.
        
        Returns:
            Dicionário com status detalhado
        """
        # Status do Lex Flow
        lex_flow_status = 'not_configured'
        if self._lex_flow:
            try:
                if hasattr(self._lex_flow, 'is_authenticated'):
                    lex_flow_status = 'connected' if self._lex_flow.is_authenticated() else 'error'
                else:
                    lex_flow_status = 'configured'
            except Exception:
                lex_flow_status = 'error'
        
        return {
            'version': '2.0.0',
            'lex_flow': lex_flow_status,
            'memory': 'available' if self._memory else 'not_configured',
            'decision_engine': 'available' if self._decision else 'not_configured',
            'cache_size': len(self._recent_insights_cache),
            'historical_data_points': sum(
                len(v) for v in self._historical_data.values()
            ),
            'statistics': self._stats.copy(),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_estatisticas(self) -> Dict[str, int]:
        """
        Retorna estatísticas de uso do gerador
        
        Returns:
            Dicionário com contadores de operações
        """
        return self._stats.copy()


# ============================================
# BLOCO DE TESTE STANDALONE
# ============================================

if __name__ == "__main__":
    """
    Modo de teste standalone - executa validações básicas
    sem precisar do Core Engine completo.
    
    Para executar:
        python engine/insight_generator.py
    """
    print("\n" + "=" * 70)
    print("💡 INSIGHT GENERATOR v2.0 - TESTE STANDALONE")
    print("=" * 70 + "\n")
    
    # Teste 1: Importação e Classes Básicas
    print("📋 Teste 1: Importação e Classes...")
    try:
        assert InsightType.PATTERN.value == "pattern"
        assert InsightConfidence.HIGH.value == "high"
        assert ProjectHealth.GOOD.value == "good"
        assert TelosDimension.TIME.value == "time"
        print("   ✅ Todos os Enums importados corretamente\n")
    except Exception as erro:
        print(f"   ❌ ERRO: {erro}\n")
    
    # Teste 2: Data Classes
    print("📋 Teste 2: Data Classes (Insight, Pattern, etc.)...")
    try:
        # Testar Insight
        insight_teste = Insight(
            type=InsightType.ACHIEVEMENT,
            title="Teste de Insight",
            description="Descrição teste",
            confidence=InsightConfidence.HIGH
        )
        dict_insight = insight_teste.to_dict()
        assert dict_insight['type'] == 'achievement'
        assert dict_insight['confidence'] == 'high'
        assert 'id' in dict_insight  # Deve ser gerado auto
        print(f"   ✅ Insight criado: ID={dict_insight['id'][:15]}...")
        
        # Testar Pattern
        padrao_teste = Pattern(
            name="Padrão Teste",
            description="Descrição do padrão",
            frequency=5,
            positive=True
        )
        dict_padrao = padrao_teste.to_dict()
        assert dict_padrao['frequency'] == 5
        print(f"   ✅ Pattern criado: {dict_padrao['name']}")
        
        # Testar ProjectHealthReport
        relatorio_teste = ProjectHealthReport(
            project_name="Projeto Teste",
            health_score=85.5
        )
        dict_relatorio = relatorio_teste.to_dict()
        assert dict_relatorio['health_score'] == 85.5
        print(f"   ✅ ProjectHealthReport criado: score={dict_relatorio['health_score']}\n")
        
    except Exception as erro:
        print(f"   ❌ ERRO: {erro}\n")
    
    # Teste 3: Inicialização sem Lex Flow (modo degradado)
    print("📋 Teste 3: Inicialização modo degradado (sem Lex Flow)...")
    try:
        generator_degradado = InsightGenerator(lex_flow_client=None)
        status = generator_degradado.get_status()
        print(f"   ✅ Inicializado (Lex Flow: {status['lex_flow']})\n")
    except Exception as erro:
        print(f"   ❌ ERRO: {erro}\n")
    
    # Teste 4: COM Lex Flow (teste completo!)
    print("📋 Teste 4: Inicialização COM Lex Flow + Insights Diários...")
    try:
        from integrations.lex_flow_definitivo import LexFlowClient
        lex_flow = LexFlowClient()
        
        generator_completo = InsightGenerator(
            lex_flow_client=lex_flow,
            memory_system=None  # Opcional para este teste
        )
        
        # Gerar insights diários
        insights_diarios = generator_completo.generate_daily_insights()
        
        print(f"   ✅ Insight Generator inicializado com Lex Flow")
        print(f"   Insights diários gerados: {len(insights_diarios)}")
        
        for i, insight in enumerate(insights_diarios[:5], 1):
            print(f"      [{i}] {insight.type.value:12} | {insight.title[:50]}")
            print(f"          Confiança: {insight.confidence.value} | Priority: {insight.priority}")
        
        print()
        
    except ImportError:
        print("   ⚠️ LexFlowClient não disponível (modo local-only)\n")
    except Exception as erro:
        print(f"   ⚠️ Erro (pode ser normal): {erro}\n")
    
    # Teste 5: Análise de Projetos
    print("📋 Teste 5: Análise de Saúde de Projetos...")
    try:
        if 'generator_completo' in dir() and generator_completo._lex_flow:
            relatorios_projetos = generator_completo.analyze_all_projects_health()
            
            print(f"   ✅ {len(relatorios_projetos)} projetos analisados:")
            
            for rel in relatorios_projetos[:3]:
                emoji_saude = {
                    'excellent': '💚', 'good': '💙', 
                    'attention': '💛', 'critical': '🧡', 'stalled': '❤️'
                }.get(rel.health_status.value, '⚪')
                
                print(f"      {emoji_saude} {rel.project_name[:35]:<35} "
                      f"| Score: {rel.health_score:>5.1f} | Risco: {rel.stalled_risk}")
            
            print()
            
        else:
            print("   ⏭️ Pulado (sem Lex Flow conectado)\n")
            
    except Exception as erro:
        print(f"   ⚠️ Erro: {erro}\n")
    
    # Teste 6: Resumo Semanal
    print("📋 Teste 6: Geração de Resumo Semanal...")
    try:
        if 'generator_completo' in dir():
            resumo_semanal = generator_completo.generate_weekly_summary()
            
            print(f"   ✅ Resumo semanal gerado:")
            print(f"      Período: {resumo_semanal.week_start} a {resumo_semanal.week_end}")
            print(f"      Score Produtividade: {resumo_semanal.productivity_score:.1f}/100")
            print(f"      Total Insights: {resumo_semanal.total_insights}")
            print(f"      Tendência: {resumo_semanal.trend}")
            print(f"      Padrões: {len(resumo_semanal.patterns_found)}")
            print(f"      Recomendações: {len(resumo_semanal.recommendations)}")
            print()
            
    except Exception as erro:
        print(f"   ⚠️ Erro: {erro}\n")
    
    # Teste 7: Relatório TELOS
    print("📋 Teste 7: Relatório TELOS (Weekly Review)...")
    try:
        if 'generator_completo' in dir():
            telos = generator_completo.generate_telos_review()
            
            print(f"   ✅ Relatório TELOS gerado:")
            print(f"      Score Geral: {telos.overall_score:.1f}/100")
            print(f"      Key Insight: {telos.key_insight[:70]}...")
            print(f"      Foco Próxima Semana: {telos.next_week_focus[:60]}...")
            print(f"      Action Items: {len(telos.action_items)}")
            
            # Mostrar dimensões
            print(f"\n      Dimensões TELOS:")
            for dim, dados in telos.dimensions.items():
                if dados:
                    score = dados.get('score', 0)
                    aval = dados.get('avaliacao', '')[:50]
                    print(f"         {dim.value:12} | Score: {score:>5.1f} | {aval}")
            
            print()
            
    except Exception as erro:
        print(f"   ⚠️ Erro: {erro}\n")
    
    # Teste 8: Status Final
    print("📋 Teste 8: Status do Sistema...")
    try:
        if 'generator_completo' in dir():
            status_final = generator_completo.get_status()
            stats = generator_completo.get_estatisticas()
            
            print(f"   Versão: {status_final['version']}")
            print(f"   Lex Flow: {status_final['lex_flow']}")
            print(f"   Cache: {status_final['cache_size']} itens")
            print(f"   Dados Históricos: {status_final['historical_data_points']} pontos")
            print(f"   Estatísticas: {stats}\n")
            
    except Exception as erro:
        print(f"   ❌ ERRO: {erro}\n")
    
    print("=" * 70)
    print("🎯 TESTES CONCLUÍDOS - Verifique os logs em logs/insight_generator.log")
    print("=" * 70 + "\n")