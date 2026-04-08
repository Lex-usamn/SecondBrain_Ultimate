"""
Automation System - Sistema de Monitoramento e Automações
============================================

Monitoramento proativo (Heartbeat), alertas inteligentes,
rotinas automáticas e sincronização contínua.

Funcionalidades:
- Heartbeat (cada X minutos)
- Detecção de projetos parados
- Alertas priorizadas
- Daily briefing automático
- Weekly review (TELOS)
- Sync comuns
- Notificações multi-canal

Autor: Second Brain Ultimate System
Versão: 1.0.0
"""

import os
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import threading
import time

try:
    from .memory_system import MemorySystem
    from .decision_engine import DecisionEngine
    from .capture_system import CaptureSystem
except ImportError:
    from memory_system import MemorySystem
    from decision_engine import DecisionEngine
    from capture_system import CaptureSystem

# ============================================
# LOGGING
# ============================================
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler('logs/automation_system.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger('AutomationSystem')

# ============================================
# ENUMS E CONSTANTES
# ============================================

class AlertLevel(Enum):
    """Níveis de alerta"""
    CRITICAL = "critical"    # Vermelho: Servidor down, deadline vencendo
    HIGH = "high"          # Amarela: Projeto parado, métricas caindo
    MEDIUM = "medium"        # Amarela: Inbox cheio, hábitos não cumpridos
    LOW = "info"              # Info only, não notificar proativamente
    INTERNAL_DEBUG = "debug"       # Debug interno

class Status(Enum):
    """Estados possíveis do sistema"""
    INITIALIZANDO = "initializing"
    READY = "ready"
    RUNNING = "running"
    WARNING = "warning"
    ERROR = "error"
    SHUTDOWN = "shutdown"
    MAINTENANCE = "maintenance"

class HeartbeatResult(Enum):
    """Resultados de uma verificação heartbeat"""
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

class ProjectStallStatus(Enum):
    """Status de projetos"""
    ACTIVE = "active"
    PAUSED = "paused"
    STALLED = "stalled"  # Parado há X dias
    ARCHIVED = "archived"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

class TaskStatus(Enum):
    """Status de tarefas"""
    TODO = "todo"
    IN_PROGRESS = "in_progresso"
    DONE = "done"
    CANCELLED = "cancelled"
    DEFERRED = "deferred"
    BLOCKED = "blocked"
    ON_HOLD = "on_hold"

class MetricType(Enum):
    """Tipos de métricas"""
    POMODOROS = "pomodoros"
    TAREFAS_CONCLUIDAS = "tasks_completed"
    VÍDEOS_ASSISTIDOS = "videos_watched"
    ANOTAÇÕES_RÁPIDAS = "quick_notes"
    HABITOS = "habits"
    GAMIFICAÇÃO = "gamification"
    INFLUENCER_DIGITAL = "influencer_digital"
    OUTROS_GERA = "outros_g era"
    
    TIME_UNITS = {
        'minutes': 'minutos',
        'hours': 'horas',
        'days': 'dias',
        'weeks': 'semanas',
        'months': 'meses'
    }

# ============================================
# DATA CLASSES
# ============================================

@dataclass
class HeartbeatConfig:
    """Configuração do Heartbeat"""
    
    enabled: bool = True
    interval_minutes: int = 30  # Intervalo entre verificações
    timezone: str = "America/Sao_Paulo"
    check_window: str = "08:00-22:00"  # Horário de operação
    dry_run: bool = False  # Executar mesmo sem outputs?
    
    # Thresholds de DETECÇÃO
    stalled_threshold_days: int = 3  # Dias sem atividade = STALLED
    inbox_size_warning: int = 20  # Amareça = WARNING
    inbox_size_critical: int = 30  # Amareza = CRÍTICO
    metrics_drop_threshold: float = 0.20  # Queda de queda = ALERTA
    max_alerts_per_hour: int = 10  # Máximo de alerts/hora
    max_daily_alerts: int = 20  # Máximo diário
    max_weekly_alerts: int = 3  # Máximo semanalise
    enable_notifications: bool = True  # Enviar notificações?
    
    # Configurações de NOTIFICAÇÃO
    notification_channels: List[str] = field(default_factory=lambda: ["console", "log"])
    webhook_url: str = ""  # Webhook para receber callbacks
    telegram_chat_id: str = ""  # Chat ID Telegram
    discord_channel_id: str = ""  # Canal Discord
    
    # Formatos de SAÍDA
    track_metrics: List[MetricType] = field(default_factory=lambda: [
        MetricType.POMODOROS,
        MetricType.TAREFAS_CONCLUÍDAS,
        MetricType.VÍDEOS_ASSISTIDOS,
        MetricType.ANOTAÇÕES_RÁPIDAS,
        MetricType.HABITOS,
        MetricType.GAMIFICAÇÃO,
        MetricType.OUTROS_GERA
    ])
    
    @property
    def check_window_hours(self) -> tuple:
        """Retorna (start_hour, end_hour) da janela"""
        start_str = self.check_window.split('-')[0].strip()
        end_str = self.check_window.split('-')[1].strip()
        return (int(start_str), int(end_str))
    
    @property
    def active_hours_count(self) -> int:
        """Quantidade de horas de operação"""
        start, end = self.check_window_hours
        return end - start if end > start else 24
    
    @property
    def is_active_now(self) -> bool:
        """Verifica se estamos dentro da janela de operação"""
        if not self.enabled:
            return False
            
        now = datetime.now().time().hour
        start, end = self.check_window_hours()
        
        if start <= now <= end:
            return True
            
        return False

# ============================================
# DATA CLASSES RESULTADO
# ============================================

@dataclass
class HeartbeatReport:
    """Relatório completo de uma verificação heartbeat"""
    
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str = ""
    engine_status: Status = Status.INITIALIZADO
    heartbeat_version: str = "2.0"
    
    # Status Geral
    system_health: Status = Status.UNKNOWN
    uptime_seconds: float = 0
    memory_usage_mb: float = 0
    
    # Projetos
    projects_total: int = 0
    projects_active: int = 0
    projects_stalled: List[Dict] = field(default_factory=list)
    projects_blocked: List[Dict] = field(default_factory=list)
    
    # Inbox
    inbox_size: int = 0
    inbox_status: str = HeartbeatResult.OK
    inbox_items_recent: List[Dict] = field(default_factory=list)
    
    # Alertas
    alerts: List[Dict] = field(default_factory=list)
    alerts_by_level: Dict[str, int] = defaultdict(int)
    
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
    
    def to_dict(self) -> Dict:
        """Converte relatório para dicionário serializável"""
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
                'completed': len([p for p in self.projects_stalled if p.get('status') == 'completed']),
                'archivados': len([p for p in self.projects_stalled if p.get('status') == 'archived'])
            },
            
            'inbox': {
                'size': self.inbox_size,
                'status': self.inbox_status,
                'recent': self.inbox_items_recent[:5]
            },
            
            'alerts': self.alerts,
            'alerts_count': len(self.alerts),
            'alerts_by_level': dict(self.alerts_by_priority),
            
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
        """Inicialização pós-construtora"""
        self.timestamp = datetime.now()
        self.session_id = f"HB_{self.timestamp.strftime('%Y%m%d%H%M%S')}"
        self.engine_status = Status.READY
        self.system_health = Status.OK
        self.uptime_seconds = 0
        self.total_checks_today = 0
        self.successful_checks = 0
        self.failed_checks = 0
        self.errors = []
        
        # Inicializar contadores
        self.alerts = []
        self.alerts_by_priority = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'info': 0,
            'low': 0
        }
        
        # Inicializar métricas
        self.quick_stats = {}
        self.inbox_items_recent = []
        
        # Inicializar projetos
        self.projects_total = 0
        self.projects_active = 0
        self.projects_stalled = []
        self.projects_blocked = []
        
        return self

@dataclass
class Alerta:
    """Alerta individual"""
    
    id: str = ""
    level: str = "info"  # critical/high/medium/low/info
    type: str = ""      # tipo: stalled/project/inbox/metrica/alerta
    title: str = ""      # Título curto
    message: str = ""     # Mensagem completa
    source: str = ""     # O que gerou o alerta
    suggestion: str = ""     # Sugestão de ação
    timestamp: str = ""    # Quando foi criado
    acknowledged: bool = False  # Usário já viu?
    resolved: bool = False  # Problema resolvido?
    resolved_at: str = ""   # Quando foi resolvido
    action_taken: str = ""   # Que ação foi tomada?
    
    def to_dict(self) -> Dict:
        """Converte alerta em dicionário"""
        return {
            'id': self.id,
            'level': self.level,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'source': self.source,
            'suggestion': self.suggestion,
            'acknowledged': self.acknowledged,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at,
            'action_taken': self.action_taken,
            'timestamp': self.timestamp
        }

@dataclass
class StalledProject:
    """Projeto identificado como parado"""
    
    id: str = ""
    name: str = ""
    project_id: int = 0
    days_stalled: int = 0
    last_activity: str = ""
    status: str = "stalled"
    blocked: bool = False
    reason: str = ""
    tasks_pending: int = 0
    progress: float = 0.0
    url: str = ""
    metrics: Dict = {}
    
    def to_dict(self) -> Dict:
        return {
        'id': self.id,
        'name': self.name,
        'project_id': self.project_id,
        'days_stalled': self.days_stalled,
        'last_activity': self.last_activity,
        'status': self.status,
        'blocked': self.blocked,
        'reason': self.reason,
        'tasks_pending': self.tasks_pending,
        'progress': f"{self.progress:.1%}" if self.progress else "0%",
        'url': self.url,
        'metrics': self.metrics
    }

@dataclass
class InboxItem:
    """Item do Inbox para tracking"""
    
    id: str = ""
    title: str = ""
    content: str = ""
    created_at: str = ""
    updated_at: str = ""
    source: str = ""
    type: str = "idea"
    tags: List[str] = []
    status: str = "new"
    project_id: Optional[int] = None
    area_id: Optional[int] = None
    converted_to_task: bool = False
    archived: bool = False
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content[:200],
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'source': self.source,
            'type': self.type,
            'tags': self.tags,
            'status': self.status,
            'project_id': self.project_id,
            'area_id': self.area_id,
            'converted_to_task': self.converted_to_task,
            'archived': self.archived
        }
    
    def __post_init__(self):
        if not self.id:
            self.id = f"inbox_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.created_at = self.created_at or datetime.now().isoformat()
            self.updated_at = self.updated_at or self.created_at

@dataclass
class DailyLog:
    """Log diário de atividades"""
    
    date: str = ""
    entries: List[Dict] = []
    
    total_pomodoros: int = 0
    tarefas_concluidas: int = 0
    videos_estudados: int = 0
    anotacoes_rápidas: int = 0
    
    def __post_init__(self):
        self.date = datetime.now().strftime('%Y-%m-%d')
        self.entries = []
        self.total_pomodoros = 0
        self.tarefas_concluidas = 0
        self.videos_estudados = 0
        self.anotacoes_rápidas = 0
        
    def add_entry(self, entry: Dict):
        """Adiciona entrada ao log"""
        self.entries.append({**entry, 'added_at': datetime.now().isoformat()})
        
    @property
    def pomodoros_hoje(self) -> int:
        """Incrementa contador de pomodoros"""
        self.total_pomodoros += 1
        self.tarefas_concluidas += 1
        return self.total_pomodoros
    
    @property
    def tarefas_concluidas(self) -> int:
        """Incrementa contador de tarefas"""
        self.tarefas_concluidas += 1
        return self.tarefas_concluidas
    
    @property
    def videos_estudados(self) -> int:
        """Incrementa contador de vídeos assistidos"""
        self.videos_estudados += 1
        return self.videos_estudados
    
    @property
    def anotacoes_rapidas(self) -> int:
        # Incrementa contador de anotacoes
        self.anotacoes_rápidas += 1
        return self.anotacoes_rápidas
    
    @property
    def total_entries(self) -> int:
        return len(self.entries)
    
    def __repr__(self):
        return f"DailyLog(date={self.date}, entries={len(self.entries)}, pomodoros={self.total_pomodoros}, tarefas={self.tarefas_concluidas}, vídeos={self.videos_estudados}, anotacoes={self.anotacoes_rapidas})"
    
    def to_dict(self) -> Dict:
        return {
            'date': self.date,
            'entries_count': len(self.entries),
            'pomodoros': self.total_pomodoros,
            'tarefas_concluidas': self.tarefas_concluidas,
            'vídeos_estudados': self.videos_estudados,
            'anotacoes_rápidas': self.anotacoes_rapidas,
            'total_entries': self.total_entries
        }

@dataclass
class WeekReview:
    """Revisão semanalítica semanal"""
    
    week_number: int = 0
    date_range: str = ""
    start_date: str = ""
    end_date: str = ""
    
    completed: int = 0
    pending: int = 0
    insights: List[Dict] = []
    tasks_completed: List[Dict] = []
    metrics: Dict = {}
    
    def __post_init__(self):
        self.week_number = self.week_number
        self.date_range = f"{datetime.now().strftime('%Y%m%d')}"
        self.start_date = datetime.now().strftime('%Y-%m-%d')
        self.end_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        self.completed = 0
        self.pending = 0
        self.insights = []
        self.tasks_completed = []
        self.metrics = {}
        
    def add_insight(self, insight: Dict):
        """Adiciona insight à revisão"""
        self.insights.append({**insight, 'added_at': datetime.now().isoformat()})
        
    def add_task_completed(self, task: Dict):
        """Registra tarefa completada"""
        self.tasks_completed.append({**task, 'completed_at': datetime.now().isoformat()})
        self.completed += 1
    
    def add_pending(self, item: Dict):
        """Adiciona item pendente"""
        self.pending += 1
    
    @property
    def completion_rate(self) -> float:
        """Taxa de conclusão (0.0 a 1.0)"""
        if self.completed + self.pending == 0:
            return 0.0
        return self.completed / (self.completed + self.pending) if self.completed + self.pending > 0 else 0.0
    
    @property
    def status(self) -> str:
        if self.completed >= self.pending:
            return "Concluído ✅"
        elif self.pending > 0:
            return "Em andamento ⏳"
        elif self.pending == 0:
            return "Sem atividades pendentes ✓"
        else:
            return "Não iniciado ◻️"
    
    def __repr__(self):
        return (f"Week #{self.week_number}: {self.date_range} ({self.start_date} → {self.end_date})\n"
                f"Concluídos: {self.completed} | Pendentes: {self.pending} | Insights: {len(self.insights)}")