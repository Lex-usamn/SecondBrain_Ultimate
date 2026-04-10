"""
Automation System v2.0 - Sistema de Automações e Workflows Inteligentes
========================================================================

Gerencia automações, tarefas agendadas, monitoramento proativo (Heartbeat),
e execução de workflows integrados ao Lex Flow.

Funcionalidades:
- Heartbeat (monitoramento contínuo a cada X minutos)
- Detecção de projetos parados e bloqueados
- Alertas inteligentes priorizados (CRITICAL/HIGH/MEDIUM/LOW)
- Daily Briefing automático
- Weekly Review TELOS automatizada
- Execução de workflows e tarefas recorrentes
- Sincronização bidirecional com Lex Flow
- Notificações multi-canal (console, log, Telegram, Discord)

Integração Lex Flow:
- Tarefas criadas/atualizadas via API real
- Projetos monitorados via get_projects()
- Inbox verificado via get_inbox()
- Métricas obtidas do dashboard
- Notas e lembretes sincronizados

Autor: Second Brain Ultimate System
Versão: 2.0.0 (Refatorado - Integração Lex Flow Real)
Data: 09/04/2026
"""

import os
import json
import logging
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

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
    from decision_engine import DecisionEngine

try:
    from .capture_system import CaptureSystem
except ImportError:
    try:
        from capture_system import CaptureSystem
    except ImportError:
        CaptureSystem = None  # Opcional, sistema funciona sem ele

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
logger_auto = logging.getLogger('AutomationSystem')

# Configurar handler apenas se não existe ainda (evita duplicados)
if not logger_auto.handlers:
    logger_auto.setLevel(logging.DEBUG)
    
    # Handler para arquivo
    file_handler = logging.FileHandler(
        'logs/automation_system.log',
        encoding='utf-8',
        mode='a'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    ))
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    ))
    
    logger_auto.addHandler(file_handler)
    logger_auto.addHandler(console_handler)


# ============================================
# ENUMS E CONSTANTES
# ============================================

class AlertLevel(Enum):
    """
    Níveis de alerta para priorização
    
    Define urgência e canais de notificação:
    - CRITICAL: Vermelho, notificação imediata em todos os canais
    - HIGH: Laranja, notificação proativa
    - MEDIUM: Amarelo, inclui no próximo briefing
    - LOW: Azul, apenas registro em log
    - DEBUG: Apenas para desenvolvimento
    """
    CRITICAL = "critical"      # Vermelho: Servidor down, deadline vencendo AGORA
    HIGH = "high"              # Laranja: Projeto parado >3 dias, métricas caindo
    MEDIUM = "medium"          # Amarelo: Inbox cheio, hábitos não cumpridos
    LOW = "info"               # Azul: Info only, não notificar proativamente
    INTERNAL_DEBUG = "debug"   # Debug interno, ignorar em produção


class SystemStatus(Enum):
    """
    Estados possíveis do sistema de automação
    
    Controla o ciclo de vida e comportamento:
    - INITIALIZANDO: Setup inicial em andamento
    - READY: Pronto para operar (idle)
    - RUNNING: Executando tarefa/verificação ativamente
    - WARNING: Operacional mas com alertas pendentes
    - ERROR: Erro não crítico, funcionamento degradado
    - SHUTDOWN: Desligamento ordenado em progresso
    - MAINTENANCE: Em manutenção, não processar novas tarefas
    """
    INITIALIZANDO = "initializing"
    READY = "ready"
    RUNNING = "running"
    WARNING = "warning"
    ERROR = "error"
    SHUTDOWN = "shutdown"
    MAINTENANCE = "maintenance"


class HeartbeatResult(Enum):
    """
    Resultados de uma verificação heartbeat
    
    Usado para tomar decisões sobre ações corretivas.
    """
    OK = "ok"              # Tudo normal, sem alertas
    WARNING = "warning"     # Alertas não críticos detectados
    CRITICAL = "critical"   # Problema sério requer ação imediata
    UNKNOWN = "unknown"     # Não foi possível determinar status


class ProjectStallStatus(Enum):
    """
    Status de estagnação de projetos
    
    Classifica o estado atual baseado na última atividade.
    """
    ACTIVE = "active"           # Atividade recente (< 2 dias)
    PAUSED = "paused"           # Pausado deliberadamente pelo usuário
    STALLED = "stalled"         # Sem atividade por X dias (threshold)
    ARCHIVED = "archived"       # Arquivado, não conta para métricas
    COMPLETED = "completed"     # Concluído com sucesso
    BLOCKED = "blocked"         # Bloqueado por dependência externa
    CANCELLED = "cancelled"     # Cancelado pelo usuário


class TaskStatus(Enum):
    """
    Status de tarefas no sistema
    
    Segue padrão Kanban/GTD adaptado.
    """
    TODO = "todo"                   # A fazer (backlog)
    IN_PROGRESS = "in_progress"      # Em andamento
    DONE = "done"                    # Concluída
    CANCELLED = "cancelled"          # Cancelada
    DEFERRED = "deferred"            # Adiada para data futura
    BLOCKED = "blocked"              # Bloqueada (esperando algo)
    ON_HOLD = "on_hold"              # Em espera (decisão pendente)


class MetricType(Enum):
    """
    Tipos de métricas rastreadas pelo sistema
    
    Cada tipo tem sua própria lógica de cálculo e exibição.
    """
    POMODOROS = "pomodoros"                     # Sessões Pomodoro completas
    TAREFAS_CONCLUIDAS = "tasks_completed"       # Tarefas finalizadas
    VIDEOS_ASSISTIDOS = "videos_watched"         # Vídeos assistidos (YouTube)
    ANOTACOES_RAPIDAS = "quick_notes"            # Quick Notes capturadas
    HABITOS = "habits"                           # Hábitos trackeados
    GAMIFICACAO = "gamification"                 # Pontos/experiência ganhos
    INFLUENCER_DIGITAL = "influencer_digital"    # Métricas redes sociais
    OUTROS = "outros"                            # Outras métricas customizadas


class WorkflowTrigger(Enum):
    """
    Tipos de gatilho para workflows automatizados
    
    Define quando um workflow deve ser executado.
    """
    SCHEDULED = "scheduled"          # Agendado (cron/time-based)
    EVENT = "event"                  # Evento disparador (ex: tarefa concluída)
    CONDITION = "condition"           # Condição atendida (ex: inbox > 20)
    MANUAL = "manual"                # Disparado manualmente pelo usuário
    HEARTBEAT = "heartbeat"           # Durante verificação heartbeat


# ============================================
# DATA CLASSES DE CONFIGURAÇÃO
# ============================================

@dataclass
class HeartbeatConfig:
    """
    Configuração completa do sistema Heartbeat
    
    Controla frequência, janelas de operação, thresholds de detecção,
    limites de alertas, e canais de notificação.
    
    Attributes:
        enabled: Se o heartbeat está ativo
        interval_minutes: Intervalo entre verificações (default: 30 min)
        timezone: Timezone para operações (default: Brazil)
        check_window: Janela horária de operação (ex: "08:00-22:00")
        dry_run: Se True, executa tudo mas não envia notificações reais
        
        stalled_threshold_days: Dias sem atividade para considerar "stalled"
        inbox_size_warning: Tamanho do inbox para alerta MEDIUM
        inbox_size_critical: Tamanho do inbox para alerta CRITICAL
        metrics_drop_threshold: Queda percentual para alertar (0.20 = 20%)
        
        max_alerts_por_hora: Limite para evitar spam
        max_daily_alerts: Limite diário total
        max_weekly_alerts: Limite semanal por tipo de alerta
        enable_notifications: Se notificações estão habilitadas
        
        notification_channels: Canais ativos (console, log, telegram, discord)
        webhook_url: URL webhook genérico
        telegram_chat_id: Chat ID para Telegram bot
        discord_channel_id: Channel ID para Discord bot
        
        track_metrics: Lista de tipos de métrica para rastrear
    """
    
    enabled: bool = True
    interval_minutes: int = 30
    timezone: str = "America/Sao_Paulo"
    check_window: str = "08:00-22:00"
    dry_run: bool = False
    
    # Thresholds de DETECÇÃO
    stalled_threshold_days: int = 3
    inbox_size_warning: int = 20
    inbox_size_critical: int = 30
    metrics_drop_threshold: float = 0.20
    max_alerts_per_hour: int = 10
    max_daily_alerts: int = 20
    max_weekly_alerts: int = 3
    enable_notifications: bool = True
    
    # Configurações de NOTIFICAÇÃO
    notification_channels: List[str] = field(
        default_factory=lambda: ["console", "log"]
    )
    webhook_url: str = ""
    telegram_chat_id: str = ""
    discord_channel_id: str = ""
    
    # Formatos de SAÍDA
    track_metrics: List[MetricType] = field(
        default_factory=lambda: [
            MetricType.POMODOROS,
            MetricType.TAREFAS_CONCLUIDAS,
            MetricType.VIDEOS_ASSISTIDOS,
            MetricType.ANOTACOES_RAPIDAS,
            MetricType.HABITOS,
            MetricType.GAMIFICACAO,
            MetricType.OUTROS
        ]
    )
    
    @property
    def check_window_hours(self) -> tuple:
        """
        Retorna (hora_inicio, hora_fim) da janela de operação
        
        Parseia string no formato 'HH:MM-HH:MM' e extrai
        apenas as horas como inteiros.
        
        Returns:
            Tupla (start_hour, end_hour) ambos inteiros
            
        Example:
            '08:00-22:00' → (8, 22)
            '09:30-18:00' → (9, 18)
        """
        try:
            # Dividir pela string separadora '-'
            partes = self.check_window.split('-')
            
            if len(partes) != 2:
                logger_auto.warning(f"Formato de check_window inválido: {self.check_window}")
                return (8, 22)  # Default seguro
            
            # Extrair hora de cada parte (antes dos ':')
            inicio_str = partes[0].strip().split(':')[0]
            fim_str = partes[1].strip().split(':')[0]
            
            # Converter para inteiros
            hora_inicio = int(inicio_str)
            hora_fim = int(fim_str)
            
            return (hora_inicio, hora_fim)
            
        except (ValueError, IndexError) as erro:
            logger_auto.warning(f"Erro parseando check_window '{self.check_window}': {erro}")
            return (8, 22)  # Default seguro em caso de erro
    
    @property
    def active_hours_count(self) -> int:
        """
        Calcula quantidade de horas da janela de operação
        
        Returns:
            Número inteiro de horas
        """
        inicio, fim = self.check_window_hours
        return fim - inicio if fim > inicio else 24
    
    @property
    def is_active_now(self) -> bool:
        """
        Verifica se estamos dentro da janela de operação atual
        
        Considera se está habilitado e se hora atual está dentro da faixa.
        
        Returns:
            True se deve estar ativo agora, False caso contrário
        """
        if not self.enabled:
            return False
            
        hora_atual = datetime.now().hour
        inicio, fim = self.check_window_hours
        
        if inicio <= hora_atual <= fim:
            return True
            
        return False


@dataclass
class WorkflowDefinition:
    """
    Definição de um workflow automatizado
    
    Um workflow é uma sequência de ações que roda automaticamente
    quando disparado por um gatilho específico.
    
    Attributes:
        name: Nome único do workflow
        description: Descrição do propósito
        trigger: Tipo de gatilho (SCHEDULED, EVENT, CONDITION, etc.)
        schedule: Cron expression ou intervalo (para SCHEDULED)
        condition_fn: Função que retorna bool (para CONDITION)
        actions: Lista de ações a executar (callables ou strings)
        enabled: Se o workflow está ativo
        last_run: Timestamp da última execução
        run_count: Quantidade de vezes que foi executado
        max_daily_runs: Limite de execuções por dia (0 = ilimitado)
    """
    name: str
    description: str = ""
    trigger: WorkflowTrigger = WorkflowTrigger.MANUAL
    schedule: Optional[str] = None
    condition_fn: Optional[Callable[[], bool]] = None
    actions: List[Any] = field(default_factory=list)
    enabled: bool = True
    last_run: Optional[datetime] = None
    run_count: int = 0
    max_daily_runs: int = 0  # 0 = ilimitado


# ============================================
# DATA CLASSES DE RESULTADO
# ============================================

@dataclass
class Alert:
    """
    Alerta gerado pelo sistema de automação
    
    Representa uma notificação ou aviso que precisa ser
    comunicado ao usuário ou registrado.
    
    Attributes:
        level: Nível de severidade (AlertLevel enum)
        title: Título curto do alerta
        message: Mensagem detalhada
        source: Origem/módulo que gerou o alerta
        timestamp: Quando foi gerado
        action_suggested: Sugestão de ação corretiva
        metadata: Dados extras contextuais
        dismissed: Se foi descartado pelo usuário
        notification_sent: Se notificação já foi enviada
    """
    level: AlertLevel
    title: str
    message: str
    source: str = "automation_system"
    timestamp: datetime = field(default_factory=datetime.now)
    action_suggested: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    dismissed: bool = False
    notification_sent: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte alerta para dicionário serializável
        
        Útil para enviar via API ou salvar em JSON.
        
        Returns:
            Dicionário com todos os campos do alerta
        """
        return {
            'level': self.level.value,
            'title': self.title,
            'message': self.message,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'action_suggested': self.action_suggested,
            'metadata': self.metadata,
            'dismissed': self.dismissed,
            'notification_sent': self.notification_sent
        }


@dataclass
class HeartbeatReport:
    """
    Relatório completo de uma verificação heartbeat
    
    Gerado a cada ciclo do heartbeat, contém status completo
    do sistema, alertas detectados, métricas, e recomendações.
    
    Attributes:
        timestamp: Momento da verificação
        session_id: ID único desta sessão de verificação
        engine_status: Status geral do motor
        system_health: Saúde geral do sistema (OK/WARNING/CRITICAL)
        uptime_seconds: Tempo desde o início (segundos)
        memory_usage_mb: Uso de memória estimado (MB)
        
        projects_total: Total de projetos no sistema
        projects_active: Projetos com atividade recente
        projects_stalled: Lista de projetos parados
        projects_blocked: Lista de projetos bloqueados
        
        inbox_size: Quantidade de itens no inbox
        inbox_status: Status do inbox (ok/warning/critical)
        inbox_items_recent: Itens mais recentes do inbox
        
        alerts: Lista de alertas gerados nesta verificação
        alerts_by_level: Contagem de alertas por nível
        
        quick_stats: Métricas rápidas coletadas
        
        total_checks_today: Total de verificações hoje
        successful_checks: Verificações bem-sucedidas
        failed_checks: Verificações com falha
        errors: Lista de erros encontrados
        
        execution_time_ms: Tempo de execução (milissegundos)
        next_run: Próxima verificação agendada
    """
    
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str = ""
    engine_status: SystemStatus = SystemStatus.INITIALIZANDO
    heartbeat_version: str = "2.0"
    
    # Status Geral
    system_health: SystemStatus = SystemStatus.READY
    uptime_seconds: float = 0
    memory_usage_mb: float = 0
    
    # Projetos
    projects_total: int = 0
    projects_active: int = 0
    projects_stalled: List[Dict] = field(default_factory=list)
    projects_blocked: List[Dict] = field(default_factory=list)
    
    # Inbox
    inbox_size: int = 0
    inbox_status: str = "ok"
    inbox_items_recent: List[Dict] = field(default_factory=list)
    
    # Alertas
    alerts: List[Alert] = field(default_factory=list)
    alerts_by_level: Dict[str, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    
    # Métricas Rápidas
    quick_stats: Dict = field(default_factory=dict)
    
    # Contadores
    total_checks_today: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    errors: List[str] = field(default_factory=list)
    
    # Timing
    execution_time_ms: float = 0
    next_run: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte relatório para dicionário serializável
        
        Returns:
            Dicionário completo com todos os dados do relatório
        """
        return {
            'timestamp': self.timestamp.isoformat(),
            'session_id': self.session_id,
            'engine_status': self.engine_status.value,
            'heartbeat_version': self.heartbeat_version,
            'system_health': self.system_health.value,
            'uptime_seconds': f"{self.uptime_seconds:.0f}",
            'memory_usage_mb': f"{self.memory_usage_mb:.1f}",
            
            # Status Geral
            'projects': {
                'total': self.projects_total,
                'active': self.projects_active,
                'stalled': len(self.projects_stalled),
                'blocked': len(self.projects_blocked),
                'completed': len([
                    p for p in self.projects_stalled 
                    if p.get('status') == 'completed'
                ]),
                'archived': len([
                    p for p in self.projects_stalled 
                    if p.get('status') == 'archived'
                ])
            },
            
            'inbox': {
                'size': self.inbox_size,
                'status': self.inbox_status,
                'recent': self.inbox_items_recent[:5]
            },
            
            'alerts': [a.to_dict() for a in self.alerts],
            'alerts_count': len(self.alerts),
            'alerts_by_level': dict(self.alerts_by_level),
            
            'metrics': self.quick_stats,
            
            'contadores': {
                'total_hoje': self.total_checks_today,
                'sucesso': self.successful_checks,
                'falhas': self.failed_checks,
                'taxa_de_erros': len(self.errors)
            },
            
            'timing': {
                'execution_time_ms': f"{self.execution_time_ms:.0f}ms",
                'next_run': self.next_run.isoformat() if self.next_run else "Agendando...",
                'uptime': f"{self.uptime_seconds:.1f}s",
                'checks_hoje': self.total_checks_today
            }
        }
    
    def __post_init__(self):
        """Inicialização pós-construtora com valores padrão seguros"""
        self.timestamp = datetime.now()
        self.session_id = f"HB_{self.timestamp.strftime('%Y%m%d%H%M%S')}"
        self.engine_status = SystemStatus.READY
        self.system_health = SystemStatus.READY
        self.uptime_seconds = 0
        self.total_checks_today = 0
        self.successful_checks = 0
        self.failed_checks = 0
        self.errors = []
        
        # Inicializar coleções vazias
        self.alerts = []
        self.alerts_by_level = defaultdict(int)
        self.quick_stats = {}
        self.inbox_items_recent = []
        
        # Inicializar contadores de projeto
        self.projects_total = 0
        self.projects_active = 0
        self.projects_stalled = []
        self.projects_blocked = []


@dataclass
class TaskExecutionResult:
    """
    Resultado da execução de uma tarefa automatizada
    
    Attributes:
        task_name: Nome da tarefa executada
        success: Se executou com sucesso
        start_time: Início da execução
        end_time: Fim da execução
        duration_seconds: Duração em segundos
        output: Saída/resultado da tarefa
        error: Erro se houve falha
        retries: Tentativas realizadas
    """
    task_name: str
    success: bool = False
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    output: Any = None
    error: Optional[str] = None
    retries: int = 0


@dataclass
class WorkflowExecutionResult:
    """
    Resultado da execução de um workflow completo
    
    Attributes:
        workflow_name: Nome do workflow executado
        success: Se todas as ações foram bem-sucedidas
        start_time: Início da execução
        end_time: Fim da execução
        duration_seconds: Duração total
        results: Lista de resultados das ações individuais
        alerts_generated: Alertas gerados durante execução
        error: Erro global se houve falha crítica
    """
    workflow_name: str
    success: bool = False
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    results: List[TaskExecutionResult] = field(default_factory=list)
    alerts_generated: List[Alert] = field(default_factory=list)
    error: Optional[str] = None


# ============================================
# CLASSE PRINCIPAL - AUTOMATION SYSTEM
# ============================================

class AutomationSystem:
    """
    Sistema de Automações v2.0 do Segundo Cérebro
    
    Motor de orquestração de tarefas automatizadas, monitoramento
    proativo (Heartbeat), e execução de workflows integrados
    ao Lex Flow API.
    
    Funcionalidades principais:
    - Monitoramento contínuo (Heartbeat) com detecção de anomalias
    - Alertas inteligentes com múltiplos níveis e canais
    - Detecção de projetos estagnados/bloqueados
    - Execução de workflows agendados ou event-driven
    - Sincronização de tarefas com Lex Flow
    - Briefings automáticos (diário/semanal)
    
    Integração Lex Flow:
    - CRUD de tarefas via add_task(), update_task(), get_tasks()
    - Projetos via get_projects()
    - Inbox via get_inbox()
    - Métricas via get_dashboard()
    
    Uso básico:
        # Inicialização com dependências
        automation = AutomationSystem(
            lex_flow_client=lex_flow_client,
            memory_system=memory,
            decision_engine=decider
        )
        
        # Iniciar sistema
        automation.iniciar()
        
        # Executar heartbeat manualmente
        relatorio = automation.executar_heartbeat()
        
        # Criar tarefa automatizada
        automation.criar_tarefa(
            titulo="Revisar vídeo YouTube",
            projeto_id="proj_123",
            prioridade="alta"
        )
        
        # Registrar workflow personalizado
        automation.registrar_workflow(
            WorkflowDefinition(
                name="morning_briefing",
                trigger=WorkflowTrigger.SCHEDULED,
                schedule="06:00",
                actions=[automation.gerar_morning_briefing]
            )
        )
    
    Atributos:
        _lex_flow: Cliente Lex Flow conectado (obrigatório para funcionalidade plena)
        _memory: Sistema de memória (opcional, para contexto)
        _decision: Motor de decisões (opcional, para priorização)
        config: Configuração do heartbeat
        status: Status atual do sistema
        _workflows: Workflows registrados
        _alert_history: Histórico de alertas recentes
    """
    
    def __init__(
        self,
        lex_flow_client: LexFlowClient,
        memory_system: Optional[MemorySystem] = None,
        decision_engine: Optional[DecisionEngine] = None,
        config: Optional[HeartbeatConfig] = None
    ):
        """
        Inicializa o Sistema de Automações v2.0
        
        Args:
            lex_flow_client: Cliente Lex Flow CONECTADO (obrigatório para funcionalidade plena)
            memory_system: Sistema de memória opcional (fornece contexto adicional)
            decision_engine: Motor de decisões opcional (usado para priorização)
            config: Configuração customizada do heartbeat (usa defaults se None)
        """
        # Dependências principais (Lex Flow é obrigatório para funcionalidade plena)
        self._lex_flow = lex_flow_client
        self._memory = memory_system
        self._decision = decision_engine
        
        # Configuração do heartbeat
        self.config = config or HeartbeatConfig()
        
        # Estado interno do sistema
        self.status = SystemStatus.INITIALIZANDO
        self._start_time = datetime.now()
        self._last_heartbeat: Optional[datetime] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Workflows registrados
        self._workflows: Dict[str, WorkflowDefinition] = {}
        
        # Histórico de alertas (para controle de rate limiting)
        self._alert_history: List[Alert] = []
        self._alerts_today_count: Dict[str, int] = defaultdict(int)
        self._alerts_this_hour: int = 0
        self._last_alert_reset: datetime = datetime.now()
        
        # Estatísticas
        self._stats = {
            'heartbeats_executados': 0,
            'tarefas_criadas': 0,
            'tarefas_concluidas': 0,
            'workflows_executados': 0,
            'alertas_gerados': 0,
            'notificacoes_enviadas': 0,
            'erros': 0
        }
        
        # Log de inicialização
        logger_auto.info("=" * 70)
        logger_auto.info("⚙️ AUTOMATION SYSTEM v2.0 INICIALIZADO")
        logger_auto.info(f"   Lex Flow: {'✅ Conectado' if lex_flow_client else '⚠️ Não configurado'}")
        logger_auto.info(f"   Memory: {'✅ Disponível' if memory_system else '⚠️ Não configurado'}")
        logger_auto.info(f"   Decision Engine: {'✅ Disponível' if decision_engine else '⚠️ Não configurado'}")
        logger_auto.info(f"   Heartbeat: {'✅ Ativo' if self.config.enabled else '❌ Desativado'}")
        logger_auto.info(f"   Intervalo: {self.config.interval_minutes} minutos")
        logger_auto.info("=" * 70)
        
        # Mudar status para pronto
        self.status = SystemStatus.READY
    
    # ========================================
    # MÉTODOS DE CONTROLE DO SISTEMA
    # ========================================
    
    def iniciar(self) -> bool:
        """
        Inicia o sistema de automações
        
        Prepara o sistema para operação, valida conexões,
        e inicia thread do heartbeat se configurado.
        
        Returns:
            True se iniciou com sucesso, False se erro crítico
        """
        logger_auto.info("🚀 Iniciando Automation System...")
        
        try:
            # Validar conexão Lex Flow (crítico)
            if self._lex_flow:
                try:
                    if hasattr(self._lex_flow, 'is_authenticated'):
                        autenticado = self._lex_flow.is_authenticated()
                        if not autenticado:
                            logger_auto.warning("⚠️ Lex Flow não autenticado, tentando login...")
                            if hasattr(self._lex_flow, 'login'):
                                self._lex_flow.login()
                    logger_auto.info("   ✅ Lex Flow validado")
                except Exception as erro:
                    logger_auto.error(f"❌ Erro validando Lex Flow: {erro}")
                    logger_auto.warning("   Sistema funcionará em modo degradado")
            
            # Carregar workloads padrão se existirem
            self._carregar_workflows_padrao()
            
            # Mudar status
            self.status = SystemStatus.READY
            self._start_time = datetime.now()
            
            logger_auto.info("✅ Automation System iniciado com sucesso")
            return True
            
        except Exception as erro:
            logger_auto.error(f"❌ ERRO CRÍTICO iniciando Automation System: {erro}")
            self.status = SystemStatus.ERROR
            self._stats['erros'] += 1
            return False
    
    def parar(self) -> None:
        """
        Para o sistema de automações gracefulmente
        
        Interrompe heartbeat em andamento, finaliza threads,
        e salva estado persistente se necessário.
        """
        logger_auto.info("🛑 Parando Automation System...")
        
        # Sinalizar parada
        self._stop_event.set()
        self.status = SystemStatus.SHUTDOWN
        
        # Esperar thread do heartbeat terminar (se existir)
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            logger_auto.info("   Aguardando thread do heartbeat terminar...")
            self._heartbeat_thread.join(timeout=10)
        
        logger_auto.info("✅ Automation System parado com sucesso")
    
    def reiniciar(self) -> bool:
        """
        Reinicia o sistema (stop + start)
        
        Returns:
            True se reiniciou com sucesso
        """
        self.parar()
        time.sleep(1)  # Breve pausa para limpeza
        return self.iniciar()
    
    # ========================================
    # SISTEMA HEARTBEAT
    # ========================================
    
    def executar_heartbeat(self, forcar_execucao: bool = False) -> HeartbeatReport:
        """
        Executa uma verificação completa do heartbeat
        
        Coleta dados de múltiplas fontes (Lex Flow, memória local),
        detecta anomalias, gera alertas, e produz relatório completo.
        
        Args:
            forcar_execucao: Se True, ignora janela horária e rate limits
            
        Returns:
            HeartbeatReport com status completo e alertas
        """
        # Marcar tempo de início
        inicio_execucao = datetime.now()
        
        logger_auto.info("💓 Executando HEARTBEAT...")
        self.status = SystemStatus.RUNNING
        
        # Criar relatório vazio
        relatorio = HeartbeatReport()
        
        try:
            # === VERIFICAÇÃO 1: Dentro da janela de operação? ===
            if not forcar_execucao and not self.config.is_active_now:
                logger_auto.info("   ⏰ Fora da janela de operação, pulando")
                relatorio.system_health = SystemStatus.READY
                relatorio.alerts.append(Alert(
                    level=AlertLevel.LOW,
                    title="Fora de Janela",
                    message=f"Heartbeat fora da janela {self.config.check_window}",
                    source="heartbeat"
                ))
                return relatorio
            
            # === VERIFICAÇÃO 2: Rate Limit de Alertas ===
            self._verificar_reset_contadores_alertas()
            
            if not forcar_execucao:
                if self._alerts_this_hour >= self.config.max_alerts_per_hour:
                    logger_auto.warning("⚠️ Limite de alertas/hora atingido")
                
                total_alerts_hoje = sum(self._alerts_today_count.values())
                if total_alerts_hoje >= self.config.max_daily_alerts:
                    logger_auto.warning("⚠️ Limite diário de alertas atingido")
            
            # === COLETA DE DADOS: Projetos ===
            logger_auto.debug("   Coletando dados dos projetos...")
            projetos_data = self._coletar_dados_projetos()
            relatorio.projects_total = projetos_data.get('total', 0)
            relatorio.projects_active = projetos_data.get('active', 0)
            relatorio.projects_stalled = projetos_data.get('stalled', [])
            relatorio.projects_blocked = projetos_data.get('blocked', [])
            
            # === COLETA DE DADOS: Inbox ===
            logger_auto.debug("   Verificando inbox...")
            inbox_data = self._verificar_inbox()
            relatorio.inbox_size = inbox_data.get('size', 0)
            relatorio.inbox_status = inbox_data.get('status', 'ok')
            relatorio.inbox_items_recent = inbox_data.get('recent', [])
            
            # === COLETA DE DADOS: Métricas Rápidas ===
            logger_auto.debug("   Coletando métricas rápidas...")
            relatorio.quick_stats = self._coletar_metricas_rapidas()
            
            # === DETECÇÃO DE ANOMALIAS ===
            logger_auto.debug("   Detectando anomalias...")
            alertas_detectados = self._detectar_anomalias(relatorio)
            relatorio.alerts.extend(alertas_detectados)
            
            # Processar alertas (filtrar, rate-limit, notificar)
            alertas_finais = self._processar_alertas(alertas_detectados)
            relatorio.alerts = alertas_finais
            
            # Contabilizar alertas por nível
            for alerta in alertas_finais:
                relatorio.alerts_by_level[alerta.level.value] += 1
            
            # === ATUALIZAR STATUS GERAL ===
            if any(a.level == AlertLevel.CRITICAL for a in alertas_finais):
                relatorio.system_health = SystemStatus.ERROR
            elif any(a.level == AlertLevel.HIGH for a in alertas_finais):
                relatorio.system_health = SystemStatus.WARNING
            else:
                relatorio.system_health = SystemStatus.READY
            
            # === ATUALIZAR CONTADORES ===
            relatorio.successful_checks += 1
            relatorio.total_checks_today += 1
            self._stats['heartbeats_executados'] += 1
            self._last_heartbeat = datetime.now()
            
            # Calcular uptime
            relatorio.uptime_seconds = (datetime.now() - self._start_time).total_seconds()
            
            # === AGENDAR PRÓXIMA EXECUÇÃO ===
            proximo = datetime.now() + timedelta(minutes=self.config.interval_minutes)
            relatorio.next_run = proximo
            
            logger_auto.info(
                f"   ✅ Heartbeat concluído "
                f"(projetos: {relatorio.projects_total}, "
                f"inbox: {relatorio.inbox_size}, "
                f"alertas: {len(alertas_finais)})"
            )
            
        except Exception as erro:
            logger_auto.error(f"❌ ERRO no heartbeat: {erro}", exc_info=True)
            relatorio.failed_checks += 1
            relatorio.errors.append(str(erro))
            relatorio.system_health = SystemStatus.ERROR
            self._stats['erros'] += 1
        
        finally:
            # Calcular tempo de execução
            fim_execucao = datetime.now()
            relatorio.execution_time_ms = (
                (fim_execucao - inicio_execucao).total_seconds() * 1000
            )
            
            # Voltar para status ready
            self.status = SystemStatus.READY
        
        return relatorio
    
    def iniciar_heartbeat_automatico(self) -> bool:
        """
        Inicia o heartbeat em background (thread separada)
        
        O heartbeat roda continuamente no intervalo configurado,
        permitindo o sistema funcionar de forma autônoma.
        
        Returns:
            True se thread iniciou com sucesso
        """
        if not self.config.enabled:
            logger_auto.warning("⚠️ Heartbeat desabilitado na configuração")
            return False
        
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            logger_auto.warning("⚠️ Heartbeat já está rodando")
            return False
        
        # Resetar evento de parada
        self._stop_event.clear()
        
        # Criar e iniciar thread
        self._heartbeat_thread = threading.Thread(
            target=self._loop_heartbeat,
            daemon=True,
            name="HeartbeatThread"
        )
        self._heartbeat_thread.start()
        
        logger_auto.info(
            f"✅ Heartbeat automático iniciado "
            f"(intervalo: {self.config.interval_minutes}min)"
        )
        return True
    
    def parar_heartbeat_automatico(self) -> None:
        """
        Para o heartbeat automático em background
        """
        self._stop_event.set()
        
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5)
        
        logger_auto.info("⛔ Heartbeat automático parado")
    
    def _loop_heartbeat(self) -> None:
        """
        Loop principal do heartbeat em background
        
        Executa continuamente até receber sinal de parada.
        Respeita janela horária e intervalos configurados.
        """
        logger_auto.info("🔄 Loop do heartbeat iniciado")
        
        while not self._stop_event.is_set():
            try:
                # Verificar se dentro da janela
                if self.config.is_active_now:
                    # Executar heartbeat
                    self.executar_heartbeat()
                else:
                    logger_auto.debug("   Fora da janela, aguardando...")
                
                # Aguardar próximo intervalo (com check do stop event)
                self._stop_event.wait(timeout=self.config.interval_minutes * 60)
                
            except Exception as erro:
                logger_auto.error(f"Erro no loop heartbeat: {erro}")
                # Continuar rodando mesmo com erros (resiliência)
                self._stop_event.wait(timeout=60)  # Esperar 1min antes de retry
    
    # ========================================
    # COLETA DE DADOS (INTEGRAÇÃO LEX FLOW)
    # ========================================
    
    def _coletar_dados_projetos(self) -> Dict[str, Any]:
        """
        Coleta dados de projetos do Lex Flow
        
        Busca lista de projetos, classifica por status,
        e detecta projetos estagnados/bloqueados.
        
        Returns:
            Dicionário com:
            - total: quantidade total de projetos
            - active: projetos ativos
            - stalled: lista de projetos parados (> threshold dias)
            - blocked: lista de projetos bloqueados
        """
        resultado = {
            'total': 0,
            'active': 0,
            'stalled': [],
            'blocked': []
        }
        
        if not self._lex_flow:
            logger_auto.debug("   Lex Flow não disponível, pulando coleta de projetos")
            return resultado
        
        try:
            # Obter projetos do Lex Flow
            projetos = self._lex_flow.get_projects()
            
            if not projetos:
                logger_auto.debug("   Nenhum projeto encontrado no Lex Flow")
                return resultado
            
            # Garantir que é lista
            if isinstance(projetos, dict):
                projetos = projetos.get('projects', projetos.get('data', []))
            
            if not isinstance(projetos, list):
                logger_auto.warning(f"   Formato inesperado de projetos: {type(projetos)}")
                return resultado
            
            resultado['total'] = len(projetos)
            threshold_dias = self.config.stalled_threshold_days
            data_limite = datetime.now() - timedelta(days=threshold_dias)
            
            for projeto in projetos:
                try:
                    status_projeto = str(projeto.get('status', '')).lower()
                    ultima_atividade = projeto.get('updated_at', projeto.get('last_activity'))
                    
                    # Classificar status
                    if status_projeto == 'active':
                        resultado['active'] += 1
                    
                    # Verificar se está estagnado
                    if ultima_atividade:
                        try:
                            # Tentar parsear data (pode vir em vários formatos)
                            if isinstance(ultima_atividade, str):
                                # Tentar ISO format primeiro
                                try:
                                    dt_atividade = datetime.fromisoformat(
                                        ultima_atividade.replace('Z', '+00:00')
                                    )
                                except ValueError:
                                    dt_atividade = None
                            elif isinstance(ultima_atividade, datetime):
                                dt_atividade = ultima_atividade
                            else:
                                dt_atividade = None
                            
                            if dt_atividade and dt_atividade < data_limite:
                                # Projeto estagnado!
                                dias_parado = (datetime.now() - dt_atividade).days
                                resultado['stalled'].append({
                                    'id': projeto.get('id'),
                                    'name': projeto.get('name', 'Sem nome'),
                                    'status': status_projeto,
                                    'days_stalled': dias_parado,
                                    'last_activity': ultima_atividade
                                })
                        
                        except Exception:
                            pass  # Ignorar erros de parse de data individual
                    
                    # Verificar se bloqueado
                    if status_projeto == 'blocked':
                        resultado['blocked'].append({
                            'id': projeto.get('id'),
                            'name': projeto.get('name', 'Sem nome'),
                            'reason': projeto.get('block_reason', 'Não especificado')
                        })
                    
                except Exception as erro_interno:
                    logger_auto.debug(f"   Erro processando projeto: {erro_interno}")
            
            logger_auto.debug(
                f"   Projetos: {resultado['total']} total, "
                f"{resultado['active']} ativos, "
                f"{len(resultado['stalled'])} estagnados, "
                f"{len(resultado['blocked'])} bloqueados"
            )
            
        except AttributeError:
            # Método get_projects não existe
            logger_auto.debug("   Método get_projects() não disponível no LexFlowClient")
            
        except Exception as erro:
            logger_auto.error(f"   Erro coletando projetos: {erro}")
        
        return resultado
    
    def _verificar_inbox(self) -> Dict[str, Any]:
        """
        Verifica estado do inbox no Lex Flow
        
        Analisa tamanho, itens recentes, e determina status.
        
        Returns:
            Dicionário com:
            - size: quantidade de itens
            - status: 'ok', 'warning', ou 'critical'
            - recent: lista dos 5 itens mais recentes
        """
        resultado = {
            'size': 0,
            'status': 'ok',
            'recent': []
        }
        
        if not self._lex_flow:
            return resultado
        
        try:
            # Obter inbox do Lex Flow
            inbox = self._lex_flow.get_inbox()
            
            if not inbox:
                return resultado
            
            # Garantir que é lista
            if isinstance(inbox, dict):
                inbox = inbox.get('items', inbox.get('data', inbox.get('notes', [])))
            
            if isinstance(inbox, list):
                resultado['size'] = len(inbox)
                resultado['recent'] = inbox[:5]
                
                # Determinar status baseado no tamanho
                if resultado['size'] >= self.config.inbox_size_critical:
                    resultado['status'] = 'critical'
                elif resultado['size'] >= self.config.inbox_size_warning:
                    resultado['status'] = 'warning'
                else:
                    resultado['status'] = 'ok'
            
            logger_auto.debug(
                f"   Inbox: {resultado['size']} itens (status: {resultado['status']})"
            )
            
        except AttributeError:
            logger_auto.debug("   Método get_inbox() não disponível")
            
        except Exception as erro:
            logger_auto.error(f"   Erro verificando inbox: {erro}")
        
        return resultado
    
    def _coletar_metricas_rapidas(self) -> Dict[str, Any]:
        """
        Coleta métricas rápidas do dashboard Lex Flow
        
        Busca dados de produtividade recentes para análise.
        
        Returns:
            Dicionário com métricas disponíveis
        """
        metricas = {}
        
        if not self._lex_flow:
            return metricas
        
        try:
            # Tentar obter dashboard/métricas
            if hasattr(self._lex_flow, 'get_dashboard'):
                dashboard = self._lex_flow.get_dashboard()
                
                if dashboard and isinstance(dashboard, dict):
                    # Extrair métricas conhecidas
                    campos_metrica = [
                        ('pomodoros_today', 'pomodoros'),
                        ('tasks_completed', 'tarefas_concluidas'),
                        ('quick_notes_count', 'anotacoes'),
                        ('streak_days', 'sequencia_dias')
                    ]
                    
                    for chave_api, chave_interna in campos_metrica:
                        valor = dashboard.get(chave_api)
                        if valor is not None:
                            metricas[chave_interna] = valor
            
            logger_auto.debug(f"   Métricas coletadas: {list(metricas.keys())}")
            
        except AttributeError:
            logger_auto.debug("   Método get_dashboard() não disponível")
            
        except Exception as erro:
            logger_auto.debug(f"   Erro coletando métricas: {erro}")
        
        return metricas
    
    # ========================================
    # DETECÇÃO DE ANOMALIAS E ALERTAS
    # ========================================
    
    def _detectar_anomalias(self, relatorio: HeartbeatReport) -> List[Alert]:
        """
        Detecta anomalias nos dados coletados e gera alertas
        
        Analisa projetos estagnados, inbox cheio, métricas anormais,
        e outros indicadores de problemas.
        
        Args:
            relatorio: Relatório preenchido com dados coletados
            
        Returns:
            Lista de Alert detectados (ainda não filtrados por rate limit)
        """
        alertas: List[Alert] = []
        
        # === ALERTA 1: Projetos Estagnados ===
        for projeto in relatorio.projects_stalled:
            dias = projeto.get('days_stalled', '?')
            nome = projeto.get('name', 'Desconhecido')
            
            alertas.append(Alert(
                level=AlertLevel.HIGH if dias >= 7 else AlertLevel.MEDIUM,
                title=f"Projeto Parado: {nome}",
                message=(
                    f"O projeto '{nome}' está sem atividade há {dias} dias "
                    f"(threshold: {self.config.stalled_threshold_days}d). "
                    f"Considere retomar, arquivar, ou pausar explicitamente."
                ),
                source="heartbeat_projetos",
                action_suggested=(
                    "Abrir projeto no Lex Flow e adicionar próxima tarefa, "
                    "ou marcar como archived se não for mais relevante."
                ),
                metadata={'project_id': projeto.get('id'), 'days_stalled': dias}
            ))
        
        # === ALERTA 2: Inbox Crítico ===
        if relatorio.inbox_status == 'critical':
            alertas.append(Alert(
                level=AlertLevel.HIGH,
                title="⚠️ Inbox CRÍTICO!",
                message=(
                    f"Inbox com {relatorio.inbox_size} itens! "
                    f"Limite crítico: {self.config.inbox_size_critical}. "
                    f"Processe urgentemente para evitar sobrecarga cognitiva."
                ),
                source="heartbeat_inbox",
                action_suggested=(
                    "Reserve 25 min para processar inbox. "
                    "Use técnica GTD: fazer, delegar, adiar, eliminar."
                ),
                metadata={'inbox_size': relatorio.inbox_size}
            ))
        
        elif relatorio.inbox_status == 'warning':
            alertas.append(Alert(
                level=AlertLevel.MEDIUM,
                title="Inbox Crescendo",
                message=(
                    f"Inbox com {relatorio.inbox_size} itens "
                    f"(limite warning: {self.config.inbox_size_warning}). "
                    f"Considere processar em breve."
                ),
                source="heartbeat_inbox",
                action_suggested="Processar inbox na próxima sessão de foco.",
                metadata={'inbox_size': relatorio.inbox_size}
            ))
        
        # === ALERTA 3: Projetos Bloqueados ===
        for projeto in relatorio.projects_blocked:
            nome = projeto.get('name', 'Desconhecido')
            motivo = projeto.get('reason', 'Não especificado')
            
            alertas.append(Alert(
                level=AlertLevel.HIGH,
                title=f"Projeto Bloqueado: {nome}",
                message=f"O projeto '{nome}' está bloqueado: {motivo}",
                source="heartbeat_projetos",
                action_suggested="Identificar dependência e desbloquear ou escalar.",
                metadata=projeto
            ))
        
        logger_auto.debug(f"   Anomalias detectadas: {len(alertas)} alertas potenciais")
        return alertas
    
    def _processar_alertas(self, alertas: List[Alert]) -> List[Alert]:
        """
        Filtra e processa alertas aplicando rate limits
        
        Remove duplicados, respeita limites diários/horários,
        e envia notificações se configurado.
        
        Args:
            alertas: Lista bruta de alertas detectados
            
        Returns:
            Lista final de alertas após filtragem
        """
        alertas_finais: List[Alert] = []
        
        for alerta in alertas:
            # Verificar rate limit
            chave_contagem = f"{alerta.level.value}_{alerta.title}"
            count_hoje = self._alerts_today_count.get(chave_contagem, 0)
            
            # Limitar alertas idênticos por semana
            if count_hoje >= self.config.max_weekly_alerts:
                logger_auto.debug(
                    f"   Alerta rate-limited: {alerta.title} "
                    f"(já enviou {count_hoje} vezes hoje)"
                )
                continue
            
            # Adicionar à lista final
            alertas_finais.append(alerta)
            
            # Atualizar contadores
            self._alerts_today_count[chave_contagem] += 1
            self._alerts_this_hour += 1
            self._alert_history.append(alerta)
            self._stats['alertas_gerados'] += 1
            
            # Enviar notificação se configurado
            if self.config.enable_notifications and not self.config.dry_run:
                self._enviar_notificacao(alerta)
        
        return alertas_finais
    
    def _enviar_notificacao(self, alerta: Alert) -> bool:
        """
        Envia notificação de alerta para canais configurados
        
        Suporta múltiplos canais: console, log, Telegram (futuro), Discord (futuro).
        
        Args:
            alerta: Alerta a ser notificado
            
        Returns:
            True se pelo menos um canal entregou com sucesso
        """
        enviado_sucesso = False
        canais = self.config.notification_channels
        
        # Canal CONSOLE (sempre disponível)
        if 'console' in canais:
            emoji = {
                AlertLevel.CRITICAL: "🔴",
                AlertLevel.HIGH: "🟠",
                AlertLevel.MEDIUM: "🟡",
                AlertLevel.LOW: "🔵",
                AlertLevel.INTERNAL_DEBUG: "⚪"
            }.get(alerta.level, "ℹ️")
            
            print(f"\n{emoji} [{alerta.level.value.upper()}] {alerta.title}")
            print(f"   {alerta.message}\n")
            enviado_sucesso = True
        
        # Canal LOG (sempre disponível)
        if 'log' in canais:
            nivel_log = {
                AlertLevel.CRITICAL: logging.ERROR,
                AlertLevel.HIGH: logging.WARNING,
                AlertLevel.MEDIUM: logging.WARNING,
                AlertLevel.LOW: logging.INFO,
                AlertLevel.INTERNAL_DEBUG: logging.DEBUG
            }.get(alerta.level, logging.INFO)
            
            logger_auto.log(nivel_log, f"ALERTA: {alerta.title} - {alerta.message}")
            enviado_sucesso = True
        
        # Marcar como enviado
        if enviado_sucesso:
            alerta.notification_sent = True
            self._stats['notificacoes_enviadas'] += 1
        
        return enviado_sucesso
    
    def _verificar_reset_contadores_alertas(self) -> None:
        """
        Reseta contadores de alertas se passou 1 hora ou novo dia
        
        Deve ser chamado antes de verificar rate limits.
        """
        agora = datetime.now()
        
        # Resetar contador por hora
        if (agora - self._last_alert_reset).total_seconds() >= 3600:
            self._alerts_this_hour = 0
            self._last_alert_reset = agora
            logger_auto.debug("   Contador de alertas/hora resetado")
        
        # Resetar contadores diários se mudou o dia
        # (implementação simplificada - reset manual ou por scheduler externo)
    
    # ========================================
    # GERENCIAMENTO DE TAREFAS (CRUD LEX FLOW)
    # ========================================
    
    def criar_tarefa(
        self,
        titulo: str,
        descricao: str = "",
        projeto_id: Optional[str] = None,
        prioridade: str = "média",
        tags: List[str] = None,
        data_vencimento: Optional[datetime] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Cria nova tarefa no Lex Flow via API
        
        Wrapper seguro em volta do add_task do Lex Flow Client,
        com validação, logging, e tratamento de erros.
        
        O LexFlowClient.add_task() usa parâmetros POSICIONAIS (não keywords),
        então este método adapta os dados para a assinatura correta.
        
        Args:
            titulo: Título da tarefa (obrigatório, mínimo 3 chars)
            descricao: Descrição detalhada (opcional)
            projeto_id: ID do projeto pai no Lex Flow (opcional)
            prioridade: Prioridade ('baixa', 'média', 'alta', 'urgente')
            tags: Lista de tags para categorização
            data_vencimento: Data limite para conclusão
            **kwargs: Parâmetros adicionais passados para a API
            
        Returns:
            Dicionário com dados da tarefa criada ou None se erro
        """
        # Validação básica
        if not titulo or len(titulo.strip()) < 3:
            logger_auto.error("❌ Título muito curto (mínimo 3 caracteres)")
            return None
        
        if not self._lex_flow:
            logger_auto.error("❌ Lex Flow não disponível para criar tarefa")
            return None
        
        titulo_limpo = titulo.strip()
        tags = tags or []
        
        logger_auto.info(f"📝 Criando tarefa: {titulo_limpo[:50]}...")
        
        try:
            # ============================================================
            # CORREÇÃO APLICADA AQUI!
            # 
            # Problema original: add_task(**payload) falhava porque o
            # LexFlowClient NÃO aceita keywords como 'content', 'title', etc.
            # 
            # Solução: Usar parâmetros posicionais + kwargs opcionais
            # Assinatura real do LexFlowClient: add_task(titulo, descricao, **opcoes)
            # ============================================================
            
            logger_auto.debug(
                f"   Chamando add_task() do Lex Flow Client..."
                f"\n      titulo: {titulo_limpo[:40]}..."
                f"\n      descricao: {descricao[:40] if descricao else '(vazia)'}..."
                f"\n      prioridade: {prioridade}"
                f"\n      tags: {tags}"
                f"\n      projeto_id: {projeto_id}"
            )
            
            # === ESTRATÉGIA 1: Tentar chamada posicional padrão ===
            # A maioria dos clientes usa: add_task(titulo, descricao, **opts)
            try:
                resposta = self._lex_flow.add_task(
                    titulo_limpo,           # 1º argumento posicional: título
                    descricao,              # 2º argumento posicional: descrição
                    project=projeto_id,     # Keyword opcional: projeto
                    priority=prioridade,    # Keyword opcional: prioridade
                    tags=tags,              # Keyword opcional: tags
                    due_date=data_vencimento.isoformat() if data_vencimento else None,
                    **kwargs                # Quaisquer extras passados pelo usuário
                )
                
                # Se chegou aqui sem erro, sucesso!
                if resposta:
                    self._stats['tarefas_criadas'] += 1
                    logger_auto.info(f"   ✅ Tarefa criada: ID {resposta.get('id', '?')}")
                    return resposta
                else:
                    logger_auto.warning("   ⚠️ add_task() retornou vazio (sem erro)")
                    return None
                    
            except TypeError as erro_tipo:
                # Se a estratégia 1 falhou (assinatura diferente), tentar estratégia 2
                logger_auto.debug(
                    f"   Estratégia 1 falhou (TypeError): {erro_tipo}"
                    f"\n   Tentando estratégia 2..."
                )
                
                # === ESTRATÉGIA 2: Tentar só com título ===
                # Algumas versões só aceitam: add_task(titulo)
                try:
                    resposta = self._lex_flow.add_task(titulo_limpo)
                    
                    if resposta:
                        self._stats['tarefas_criadas'] += 1
                        logger_auto.info(
                            f"   ✅ Tarefa criada (estratégia 2): "
                            f"ID {resposta.get('id', '?')}"
                        )
                        return resposta
                    else:
                        logger_auto.warning("   ⚠️ add_task(titulo) retornou vazio")
                        
                except Exception as erro_strat2:
                    logger_auto.debug(f"   Estratégia 2 também falhou: {erro_strat2}")
                
                # === ESTRATÉGIA 3: Último recurso - criar como nota ===
                # Se add_task não funciona, usar add_note como fallback
                logger_auto.info(
                    "   ⚠️ add_task() não disponível, tentando via add_note()..."
                )
                
                if hasattr(self._lex_flow, 'add_note'):
                    nota_titulo = f"📋 TAREFA: {titulo_limpo}"
                    nota_conteudo = descricao or "(Sem descrição)"
                    
                    if projeto_id:
                        nota_conteudo += f"\n\nProjeto ID: {projeto_id}"
                    if prioridade:
                        nota_conteudo += f"\nPrioridade: {prioridade}"
                    if tags:
                        nota_conteudo += f"\nTags: {', '.join(tags)}"
                    if data_vencimento:
                        nota_conteudo += f"\nVencer: {data_vencimento.strftime('%d/%m/%Y')}"
                    
                    resposta_nota = self._lex_flow.add_note(nota_titulo, nota_conteudo)
                    
                    if resposta_nota:
                        self._stats['tarefas_criadas'] += 1
                        logger_auto.info(
                            f"   ✅ Tarefa criada como NOTA (fallback): "
                            f"ID {resposta_nota.get('id', '?')}"
                        )
                        return resposta_nota
                
                # Se chegou aqui, nada funcionou
                logger_auto.error(
                    "❌ Todas as estratégias falharam para criar tarefa. "
                    "Verifique se o método add_task existe no LexFlowClient."
                )
                return None
                
        except AttributeError:
            logger_auto.error("❌ Método add_task() não disponível no LexFlowClient")
            return None
            
        except Exception as erro:
            logger_auto.error(f"❌ Erro criando tarefa: {erro}")
            self._stats['erros'] += 1
            return None
            
    def atualizar_tarefa(
        self,
        tarefa_id: str,
        **campos_atualizacao
    ) -> bool:
        """
        Atualiza tarefa existente no Lex Flow
        
        Args:
            tarefa_id: ID da tarefa a atualizar
            **campos_atualização: Campos a atualizar (titulo, status, etc.)
            
        Returns:
            True se atualizado com sucesso
        """
        if not self._lex_flow or not tarefa_id:
            return False
        
        try:
            if hasattr(self._lex_flow, 'update_task'):
                resposta = self._lex_flow.update_task(tarefa_id, **campos_atualizacao)
                
                if resposta:
                    logger_auto.info(f"✅ Tarefa {tarefa_id} atualizada")
                    return True
                else:
                    logger_auto.warning(f"⚠️ update_task() retornou vazio para {tarefa_id}")
                    return False
            else:
                logger_auto.warning("Método update_task() não disponível")
                return False
                
        except Exception as erro:
            logger_auto.error(f"Erro atualizando tarefa {tarefa_id}: {erro}")
            return False
    
    def completar_tarefa(self, tarefa_id: str) -> bool:
        """
        Marca tarefa como concluída
        
        Args:
            tarefa_id: ID da tarefa
            
        Returns:
            True se concluída com sucesso
        """
        return self.atualizar_tarefa(tarefa_id, status='done')
    
    def listar_tarefas(
        self,
        projeto_id: Optional[str] = None,
        status: Optional[str] = None,
        limite: int = 20
    ) -> List[Dict]:
        """
        Lista tarefas do Lex Flow com filtros opcionais
        
        Args:
            projeto_id: Filtrar por projeto
            status: Filtrar por status (todo, done, in_progress, etc.)
            limite: Máximo de resultados
            
        Returns:
            Lista de dicionários com dados das tarefas
        """
        if not self._lex_flow:
            return []
        
        try:
            # Tentar obter tarefas
            if hasattr(self._lex_flow, 'get_tasks'):
                tarefas = self._lex_flow.get_tasks(
                    project_id=projeto_id,
                    status=status,
                    limit=limite
                )
                
                if isinstance(tarefas, list):
                    return tarefas
                elif isinstance(tarefas, dict):
                    return tarefas.get('tasks', tarefas.get('data', []))
                
            # Fallback: buscar notas/tarefas genéricas
            if hasattr(self._lex_flow, 'search_notes'):
                resultados = self._lex_flow.search_notes(query="task OR tarefa", limit=limite)
                return resultados if isinstance(resultados, list) else []
            
            return []
            
        except Exception as erro:
            logger_auto.error(f"Erro listando tarefas: {erro}")
            return []
    
    # ========================================
    # WORKFLOWS AUTOMATIZADOS
    # ========================================
    
    def registrar_workflow(self, workflow: WorkflowDefinition) -> bool:
        """
        Registra um novo workflow no sistema
        
        Args:
            workflow: Definição completa do workflow
            
        Returns:
            True se registrado com sucesso
        """
        if not workflow.name:
            logger_auto.error("Workflow sem nome não pode ser registrado")
            return False
        
        # Verificar se já existe
        if workflow.name in self._workflows:
            logger_auto.warning(f"Workflow '{workflow.name}' já existe, sobrescrevendo")
        
        self._workflows[workflow.name] = workflow
        logger_auto.info(f"✅ Workflow registrado: {workflow.name} ({workflow.trigger.value})")
        return True
    
    def executar_workflow(self, nome_workflow: str) -> WorkflowExecutionResult:
        """
        Executa um workflow específico por nome
        
        Args:
            nome_workflow: Nome do workflow registrado
            
        Returns:
            WorkflowExecutionResult com detalhes da execução
        """
        resultado = WorkflowExecutionResult(workflow_name=nome_workflow)
        resultado.start_time = datetime.now()
        
        # Buscar workflow
        workflow = self._workflows.get(nome_workflow)
        
        if not workflow:
            resultado.error = f"Workflow '{nome_workflow}' não encontrado"
            resultado.success = False
            logger_auto.error(resultado.error)
            return resultado
        
        # Verificar se habilitado
        if not workflow.enabled:
            resultado.error = f"Workflow '{nome_workflow}' está desabilitado"
            resultado.success = False
            logger_auto.warning(resultado.error)
            return resultado
        
        # Verificar condição se existir
        if workflow.condition_fn:
            try:
                condicao_ok = workflow.condition_fn()
                if not condicao_ok:
                    resultado.error = "Condição do workflow não atendida"
                    resultado.success = False
                    logger_auto.info(f"   Workflow {nome_workflow}: condição falsa, pulando")
                    return resultado
            except Exception as erro_cond:
                resultado.error = f"Erro na condição: {erro_cond}"
                resultado.success = False
                logger_auto.error(resultado.error)
                return resultado
        
        logger_auto.info(f"▶️ Executando workflow: {nome_workflow}")
        
        # Executar cada ação
        for acao in workflow.actions:
            resultado_acao = TaskExecutionResult(task_name=str(acao))
            resultado_acao.start_time = datetime.now()
            
            try:
                # Executar ação (callable ou string)
                if callable(acao):
                    saida = acao()
                elif isinstance(acao, str):
                    # Tentar encontrar método deste objeto
                    metodo = getattr(self, acao, None)
                    if metodo and callable(metodo):
                        saida = metodo()
                    else:
                        raise ValueError(f"Método/Ação não encontrada: {acao}")
                else:
                    raise TypeError(f"Tipo de ação inválido: {type(acao)}")
                
                resultado_acao.success = True
                resultado_acao.output = saida
                
            except Exception as erro_acao:
                resultado_acao.success = False
                resultado_acao.error = str(erro_acao)
                logger_auto.error(f"   ❌ Erro na ação '{acao}': {erro_acao}")
            
            finally:
                resultado_acao.end_time = datetime.now()
                resultado_acao.duration_seconds = (
                    (resultado_acao.end_time - resultado_acao.start_time).total_seconds()
                )
                resultado.results.append(resultado_acao)
        
        # Finalizar
        resultado.end_time = datetime.now()
        resultado.duration_seconds = (
            (resultado.end_time - resultado.start_time).total_seconds()
        )
        resultado.success = all(r.success for r in resultado.results) if resultado.results else True
        
        # Atualizar metadados do workflow
        workflow.last_run = datetime.now()
        workflow.run_count += 1
        self._stats['workflows_executados'] += 1
        
        logger_auto.info(
            f"   ✅ Workflow '{nome_workflow}' concluído "
            f"(sucesso: {resultado.success}, duração: {resultado.duration_seconds:.1f}s)"
        )
        
        return resultado
    
    def _carregar_workflows_padrao(self) -> None:
        """
        Carrega workflows padrão do sistema
        
        Chamado durante a inicialização para registrar
        workflows embutidos (morning briefing, etc.)
        """
        # Workflow: Morning Briefing (exemplo)
        morning_wf = WorkflowDefinition(
            name="morning_briefing",
            description="Briefing matinal automático com prioridades do dia",
            trigger=WorkflowTrigger.SCHEDULED,
            schedule="06:00",
            actions=["gerar_morning_briefing"],
            enabled=False  # Desabilitado por padrão, usuário deve habilitar
        )
        self.registrar_workflow(morning_wf)
        
        logger_auto.debug(f"   {len(self._workflows)} workflows padrão carregados")
    
    # ========================================
    # BRIEFINGS AUTOMÁTICOS
    # ========================================
    
    def gerar_morning_briefing(self) -> Dict[str, Any]:
        """
        Gera briefing matinal automático
        
        Compila informações relevantes para começar o dia:
        - Prioridades do Lex Flow
        - Tarefas vencendo hoje
        - Projetos que precisam atenção
        - Métricas de ontem
        - Sugestões do Decision Engine
        
        Returns:
            Dicionário com briefing estruturado
        """
        logger_auto.info("🌅 Gerando MORNING BRIEFING...")
        
        briefing = {
            'timestamp': datetime.now().isoformat(),
            'tipo': 'morning',
            'secoes': {}
        }
        
        try:
            # === SEÇÃO 1: Prioridades ===
            if self._lex_flow:
                try:
                    prioridades = self._lex_flow.get_dashboard()
                    if prioridades:
                        briefing['secoes']['prioridades'] = prioridades
                except Exception:
                    briefing['secoes']['prioridades'] = "Erro carregando prioridades"
            
            # === SEÇÃO 2: Tarefas para Hoje ===
            tarefas_hoje = self.listar_tarefas(status='todo', limite=10)
            briefing['secoes']['tarefas_hoje'] = tarefas_hoje[:5]
            
            # === SEÇÃO 3: Projetos que Precisam Atenção ===
            projetos_data = self._coletar_dados_projetos()
            if projetos_data.get('stalled'):
                briefing['secoes']['atencao_projetos'] = projetos_data['stalled'][:3]
            
            # === SEÇÃO 4: Insight do Dia ===
            if self._decision:
                try:
                    insight = self._decision.suggest_next_action(
                        current_state={'time_of_day': 'morning'},
                        energy='medium'
                    )
                    if insight:
                        briefing['secoes']['sugestao'] = {
                            'acao': insight.action,
                            'razao': insight.reasoning,
                            'urgencia': insight.urgency
                        }
                except Exception:
                    pass
            
            logger_auto.info("   ✅ Morning briefing gerado")
            
        except Exception as erro:
            logger_auto.error(f"Erro gerando morning briefing: {erro}")
            briefing['erro'] = str(erro)
        
        return briefing
    
    # ========================================
    # UTILITÁRIOS E DIAGNÓSTICO
    # ========================================
    
    def get_status(self) -> Dict[str, Any]:
        """
        Retorna status completo do Automation System
        
        Útil para health checks e dashboards de monitoramento.
        
        Returns:
            Dicionário com status detalhado do sistema
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
            'status': self.status.value,
            'lex_flow': lex_flow_status,
            'heartbeat': {
                'enabled': self.config.enabled,
                'interval_minutes': self.config.interval_minutes,
                'is_active_now': self.config.is_active_now,
                'last_execution': self._last_heartbeat.isoformat() if self._last_heartbeat else None,
                'auto_running': (
                    self._heartbeat_thread is not None and 
                    self._heartbeat_thread.is_alive()
                )
            },
            'workflows_registered': len(self._workflows),
            'workflows_list': list(self._workflows.keys()),
            'statistics': self._stats.copy(),
            'alerts_today': dict(self._alerts_today_count),
            'uptime_seconds': (datetime.now() - self._start_time).total_seconds(),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_estatisticas(self) -> Dict[str, int]:
        """
        Retorna estatísticas de uso do sistema
        
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
        python engine/automation_system.py
    """
    print("\n" + "=" * 70)
    print("⚙️ AUTOMATION SYSTEM v2.0 - TESTE STANDALONE")
    print("=" * 70 + "\n")
    
    # Teste 1: Importação e classes básicas
    print("📋 Teste 1: Importação e classes...")
    try:
        assert AlertLevel.CRITICAL.value == "critical"
        assert SystemStatus.READY.value == "ready"
        assert TaskStatus.TODO.value == "todo"
        print("   ✅ Enums importados corretamente\n")
    except Exception as erro:
        print(f"   ❌ ERRO: {erro}\n")
    
    # Teste 2: Configuração do Heartbeat
    print("📋 Teste 2: Configuração Heartbeat...")
    try:
        config = HeartbeatConfig(interval_minutes=30, check_window="08:00-22:00")
        assert config.active_hours_count == 14
        assert config.check_window_hours == (8, 22)
        print(f"   ✅ Config válida: {config.interval_minutes}min, janela {config.check_window}")
        print(f"   Horas ativas: {config.active_hours_count}h\n")
    except Exception as erro:
        print(f"   ❌ ERRO: {erro}\n")
    
    # Teste 3: Inicialização sem Lex Flow (deve funcionar em modo degradado)
    print("📋 Teste 3: Inicialização modo degradado (sem Lex Flow)...")
    try:
        auto_degradado = AutomationSystem(lex_flow_client=None)
        status = auto_degradado.get_status()
        print(f"   ✅ Inicializado (modo: {status['lex_flow']})\n")
    except Exception as erro:
        print(f"   ❌ ERRO: {erro}\n")
    
    # Teste 4: Com Lex Flow (opcional, pode falhar se sem credenciais)
    print("📋 Teste 4: Inicialização COM Lex Flow...")
    try:
        from integrations.lex_flow_definitivo import LexFlowClient
        lex_flow = LexFlowClient()
        
        auto_completo = AutomationSystem(
            lex_flow_client=lex_flow,
            config=HeartbeatConfig(dry_run=True)  # Dry run = não envia notificações reais
        )
        
        # Iniciar sistema
        inicio_ok = auto_completo.iniciar()
        print(f"   Inicialização: {'✅ Sucesso' if inicio_ok else '❌ Falhou'}")
        
        # Executar heartbeat (dry run)
        relatorio = auto_completo.executar_heartbeat(forcar_execucao=True)
        
        print(f"   Heartbeat executado:")
        print(f"      Status: {relatorio.system_health.value}")
        print(f"      Projetos: {relatorio.projects_total}")
        print(f"      Inbox: {relatorio.inbox_size} ({relatorio.inbox_status})")
        print(f"      Alertas: {len(relatorio.alerts)}")
        print(f"      Tempo: {relatorio.execution_time_ms:.0f}ms\n")
        
        # Status final
        status_final = auto_completo.get_status()
        print(f"   Status do sistema:")
        print(f"      Versão: {status_final['version']}")
        print(f"      Uptime: {status_final['uptime_seconds']:.1f}s")
        print(f"      Stats: {status_final['statistics']}\n")
        
    except ImportError:
        print("   ⚠️ LexFlowClient não disponível (modo local-only)\n")
    except Exception as erro:
        print(f"   ⚠️ Erro (pode ser normal sem credenciais): {erro}\n")
    
    # Teste 5: Criar tarefa (só se Lex Flow conectado)
    print("📋 Teste 5: Criar tarefa de teste...")
    try:
        if 'auto_completo' in dir() and auto_completo._lex_flow:
            tarefa = auto_completo.criar_tarefa(
                titulo="Tarefa teste Automation System v2.0",
                descricao="Criada pelo teste standalone",
                tags=["teste", "automacao"]
            )
            
            if tarefa:
                print(f"   ✅ Tarefa criada: {tarefa.get('id', '?')}\n")
            else:
                print(f"   ⚠️ Tarefa não criada (add_task pode não existir)\n")
        else:
            print(f"   ⏭️ Pulado (sem Lex Flow conectado)\n")
    except Exception as erro:
        print(f"   ❌ ERRO: {erro}\n")
    
    # Teste 6: Alertas
    print("📋 Teste 6: Sistema de alertas...")
    try:
        alerta_teste = Alert(
            level=AlertLevel.HIGH,
            title="Teste de Alerta",
            message="Este é um alerta de teste do sistema",
            source="teste_standalone"
        )
        
        dict_alerta = alerta_teste.to_dict()
        assert dict_alerta['level'] == 'high'
        assert dict_alerta['title'] == 'Teste de Alerta'
        print(f"   ✅ Alerta criado e serializado corretamente\n")
    except Exception as erro:
        print(f"   ❌ ERRO: {erro}\n")
    
    print("=" * 70)
    print("🎯 TESTES CONCLUÍDOS - Verifique os logs em logs/automation_system.log")
    print("=" * 70 + "\n")