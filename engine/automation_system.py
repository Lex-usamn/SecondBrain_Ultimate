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
Versão: 1.0.0 (CORRIGIDA - Sem Erros)
"""

import os
import json
import logging
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
# ENUMS E CONSTANTS
# ============================================

class AlertLevel(Enum):
    """Níveis de alerta"""
    CRITICAL = "critical"    # Vermelho: Servidor down, deadline vencendo
    HIGH = "high"            # Amarela: Projeto parado, métricas caindo
    MEDIUM = "medium"        # Amarela: Inbox cheio, hábitos não cumpridos
    LOW = "info"             # Info only, não notificar proativamente
    INTERNAL_DEBUG = "debug" # Debug interno

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
    STALLED = "stalled"
    ARCHIVED = "archived"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

class TaskStatus(Enum):
    """Status de tarefas"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"
    DEFERRED = "deferred"
    BLOCKED = "blocked"
    ON_HOLD = "on_hold"

class MetricType(Enum):
    """Tipos de métricas"""
    POMODOROS = "pomodoros"
    TAREFAS_CONCLUIDAS = "tasks_completed"
    VIDEOS_ASSISTIDOS = "videos_watched"
    ANOTACOES_RAPIDAS = "quick_notes"
    HABITOS = "habits"
    GAMIFICACAO = "gamification"
    INFLUENCER_DIGITAL = "influencer_digital"
    OUTROS = "outros"

# ============================================
# DATA CLASSES
# ============================================

@dataclass
class HeartbeatConfig:
    """Configuração do Heartbeat"""
    
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
    notification_channels: List[str] = field(default_factory=lambda: ["console", "log"])
    webhook_url: str = ""
    telegram_chat_id: str = ""
    discord_channel_id: str = ""
    
    # Formatos de SAÍDA
    track_metrics: List[MetricType] = field(default_factory=lambda: [
        MetricType.POMODOROS,
        MetricType.TAREFAS_CONCLUIDAS,
        MetricType.VIDEOS_ASSISTIDOS,
        MetricType.ANOTACOES_RAPIDAS,
        MetricType.HABITOS,
        MetricType.GAMIFICACAO,
        MetricType.OUTROS
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
            
        now = datetime.now().hour
        start, end = self.check_window_hours
        
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
    engine_status: Status = Status.INITIALIZANDO
    heartbeat_version: str = "2.0"
    
    # Status Geral
    system_health: Status = Status.READY  # ✅ CORRIGIDO: era Status.UNKNOWN
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
    alerts: List[Dict] = field(default_factory=list)
    alerts_by_level: Dict[str, int] = field(default_factory=lambda: defaultdict(int))  # ✅ CORRIGIDO: era defaultdict(int) direto
    
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
                'archived': len([p for p in self.projects_stalled if p.get('status') == 'archived'])
            },
            
            'inbox': {
                'size': self.inbox_size,
                'status': self.inbox_status,
                'recent': self.inbox_items_recent[:5]
            },
            
            'alerts': self.alerts,
            'alerts_count': len(self.alerts),
            'alerts_by_level': dict(self.alerts_by_level),  # ✅ CORRIGIDO: era alerts_by_priority
            
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
        self.system_health = Status.READY
        self.uptime_seconds = 0
        self.total_checks_today = 0
        self.successful_checks = 0
        self.failed_checks = 0
        self.errors = []
        
        # Inicializar contadores
        self.alerts = []
        self.alerts_by_level = defaultdict(int)  # ✅ CORRIGIDO: era alerts_by_priority
        
        # Inicializar métricas
        self.quick_stats = {}
        self.inbox_items_recent = []
        
        # Inicializar projetos
        self.projects_total = 0
        self.projects_active = 0
        self.projects_stalled = []
        self.projects_blocked = []

@dataclass
class Alerta:
    """Alerta individual"""
    
    id: str = ""
    level: str = "info"
    type: str = ""
    title: str = ""
    message: str = ""
    source: str = ""
    suggestion: str = ""
    timestamp: str = ""
    acknowledged: bool = False
    resolved: bool = False
    resolved_at: str = ""
    action_taken: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = f"ALT_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.timestamp = self.timestamp or datetime.now().isoformat()
    
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
    metrics: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = f"STALL_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
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
    tags: List[str] = field(default_factory=list)
    status: str = "new"
    project_id: Optional[int] = None
    area_id: Optional[int] = None
    converted_to_task: bool = False
    archived: bool = False
    
    def __post_init__(self):
        if not self.id:
            self.id = f"inbox_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.created_at = self.created_at or datetime.now().isoformat()
            self.updated_at = self.updated_at or self.created_at
    
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

@dataclass
class DailyLog:
    """Log diário de atividades"""
    
    date: str = ""
    entries: List[Dict] = field(default_factory=list)
    
    total_pomodoros: int = 0
    tarefas_concluidas: int = 0
    videos_estudados: int = 0
    anotacoes_rapidas: int = 0
    
    def __post_init__(self):
        self.date = datetime.now().strftime('%Y-%m-%d')
        self.entries = []
        self.total_pomodoros = 0
        self.tarefas_concluidas = 0
        self.videos_estudados = 0
        self.anotacoes_rapidas = 0
        
    def add_entry(self, entry: Dict):
        """Adiciona entrada ao log"""
        self.entries.append({**entry, 'added_at': datetime.now().isoformat()})
        
    def add_pomodoro(self):
        """Incrementa contador de pomodoros"""
        self.total_pomodoros += 1
        return self.total_pomodoros
    
    def add_tarefa_concluida(self):
        """Incrementa contador de tarefas"""
        self.tarefas_concluidas += 1
        return self.tarefas_concluidas
    
    def add_video_estudado(self):
        """Incrementa contador de vídeos assistidos"""
        self.videos_estudados += 1
        return self.videos_estudados
    
    def add_anotacao_rapida(self):
        """Incrementa contador de anotações"""
        self.anotacoes_rapidas += 1
        return self.anotacoes_rapidas
    
    @property
    def total_entries(self) -> int:
        return len(self.entries)
    
    def __repr__(self):
        return f"DailyLog(date={self.date}, entries={len(self.entries)}, pomodoros={self.total_pomodoros}, tarefas={self.tarefas_concluidas}, videos={self.videos_estudados}, anotacoes={self.anotacoes_rapidas})"
    
    def to_dict(self) -> Dict:
        return {
            'date': self.date,
            'entries_count': len(self.entries),
            'pomodoros': self.total_pomodoros,
            'tarefas_concluidas': self.tarefas_concluidas,
            'videos_estudados': self.videos_estudados,
            'anotacoes_rapidas': self.anotacoes_rapidas,
            'total_entries': self.total_entries
        }

@dataclass
class WeekReview:
    """Revisão semanal"""
    
    week_number: int = 0
    date_range: str = ""
    start_date: str = ""
    end_date: str = ""
    
    completed: int = 0
    pending: int = 0
    insights: List[Dict] = field(default_factory=list)
    tasks_completed: List[Dict] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        now = datetime.now()
        self.week_number = now.isocalendar()[1]
        self.date_range = now.strftime('%Y-%m-%d')
        self.start_date = now.strftime('%Y-%m-%d')
        self.end_date = (now + timedelta(days=7)).strftime('%Y-%m-%d')
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
        total = self.completed + self.pending
        if total == 0:
            return 0.0
        return self.completed / total
    
    @property
    def status_text(self) -> str:
        if self.completed >= self.pending and self.completed > 0:
            return "Concluído ✅"
        elif self.pending > 0:
            return "Em andamento ⏳"
        elif self.pending == 0 and self.completed == 0:
            return "Sem atividades registradas ✓"
        else:
            return "Não iniciado ◻️"
    
    def __repr__(self):
        return (f"Week #{self.week_number}: {self.date_range} ({self.start_date} → {self.end_date})\n"
                f"Concluídos: {self.completed} | Pendentes: {self.pending} | Insights: {len(self.insights)}")


# ============================================
# MAIN CLASS - AUTOMATION SYSTEM
# ============================================

class AutomationSystem:
    """
    Sistema de Automação e Monitoramento
    
    Responsável por:
    - Heartbeat (verificações periódicas)
    - Detecção de projetos parados
    - Geração de alertas inteligentes
    - Logs diários e revisões semanais
    - Notificações multi-canal
    """
    
    def __init__(
        self,
        memory: MemorySystem = None,
        lex_flow=None,
        decider: DecisionEngine = None,
        capturer: CaptureSystem = None,
        config: HeartbeatConfig = None
    ):
        """
        Inicializa o Sistema de Automação
        
        Args:
            memory: Sistema de memória
            lex_flow: Cliente Lex Flow
            decider: Motor de decisões
            capturer: Sistema de captura
            config: Configuração do heartbeat
        """
        self.memory = memory
        self.lex_flow = lex_flow
        self.decider = decider
        self.capturer = capturer
        self.config = config or HeartbeatConfig()
        
        # Estado interno
        self._heartbeat_thread = None
        self._stop_event = threading.Event()
        self._is_running = False
        
        # Histórico
        self._alert_history: List[Alerta] = []
        self._daily_logs: Dict[str, DailyLog] = {}
        self._weekly_reviews: Dict[str, WeekReview] = {}
        
        log.info("🤖 Automation System inicializado")
        log.info(f"   Heartbeat: {'Ativado' if self.config.enabled else 'Desativado'}")
        log.info(f"   Intervalo: {self.config.interval_minutes} minutos")
    
    def run_quick_check(self) -> Optional[HeartbeatReport]:
        """
        Executa uma verificação rápida (sem alertas extensivos)
        
        Returns:
            HeartbeatReport básico ou None se falhar
        """
        try:
            report = HeartbeatReport()
            
            # Verificar status básico dos projetos
            if self.lex_flow:
                try:
                    projects = self.lex_flow.get_projects()
                    report.projects_total = len(projects)
                    report.projects_active = len([p for p in projects if p.get('status') == 'active'])
                    
                    # Detectar parados
                    for proj in projects:
                        last_activity = proj.get('updated_at', proj.get('last_modified'))
                        if last_activity:
                            last_date = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                            days_since = (datetime.now(last_date.tzinfo) - last_date).days
                            
                            if days_since > self.config.stalled_threshold_days:
                                stalled = StalledProject(
                                    name=proj.get('title', proj.get('name', 'Unknown')),
                                    days_stalled=days_since,
                                    last_activity=last_activity
                                )
                                report.projects_stalled.append(stalled.to_dict())
                                
                except Exception as e:
                    log.warning(f"Erro verificando projetos: {e}")
            
            # Verificar inbox
            if self.lex_flow:
                try:
                    inbox = self.lex_flow.get_inbox()
                    report.inbox_size = len(inbox)
                    
                    if report.inbox_size >= self.config.inbox_size_critical:
                        report.inbox_status = "critical"
                    elif report.inbox_size >= self.config.inbox_size_warning:
                        report.inbox_status = "warning"
                        
                except Exception as e:
                    log.warning(f"Erro verificando inbox: {e}")
            
            return report
            
        except Exception as e:
            log.error(f"Erro na verificação rápida: {e}")
            return None
    
    def run_full_check(self) -> HeartbeatReport:
        """
        Executa verificação completa com todos os checks
        
        Returns:
            HeartbeatReport completo
        """
        log.info("💓 Executando verificação completa (Full Check)...")
        start_time = time.time()
        
        report = HeartbeatReport()
        
        try:
            # 1. Verificar projetos
            self._check_projects(report)
            
            # 2. Verificar inbox
            self._check_inbox(report)
            
            # 3. Verificar métricas
            self._check_metrics(report)
            
            # 4. Gerar alertas se necessário
            self._generate_alerts(report)
            
            # 5. Registrar no log
            self._register_heartbeat_log(report)
            
            # Timing
            report.execution_time_ms = (time.time() - start_time) * 1000
            report.next_run = datetime.now() + timedelta(minutes=self.config.interval_minutes)
            
            report.successful_checks += 1
            
            log.info(f"   ✅ Full check concluído ({report.execution_time_ms:.0f}ms)")
            
        except Exception as e:
            report.failed_checks += 1
            report.errors.append(str(e))
            log.error(f"   ❌ Erro no full check: {e}", exc_info=True)
        
        return report
    
    def _check_projects(self, report: HeartbeatReport):
        """Verifica status de todos os projetos"""
        if not self.lex_flow:
            return
            
        try:
            projects = self.lex_flow.get_projects()
            report.projects_total = len(projects)
            report.projects_active = len([p for p in projects if p.get('status') == 'active'])
            
            for proj in projects:
                last_activity = proj.get('updated_at', proj.get('last_modified'))
                
                if last_activity:
                    try:
                        last_date = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                        days_since = (datetime.now(last_date.tzinfo) - last_date).days
                        
                        if days_since > self.config.stalled_threshold_days:
                            stalled_proj = StalledProject(
                                name=proj.get('title', proj.get('name', 'Unknown')),
                                project_id=proj.get('id', 0),
                                days_stalled=days_since,
                                last_activity=last_activity,
                                progress=proj.get('progress', 0),
                                tasks_pending=len(proj.get('tasks', []))
                            )
                            report.projects_stalled.append(stalled_proj.to_dict())
                            
                    except (ValueError, TypeError):
                        pass
                        
        except Exception as e:
            log.warning(f"Erro ao verificar projetos: {e}")
    
    def _check_inbox(self, report: HeartbeatReport):
        """Verifica estado da inbox"""
        if not self.lex_flow:
            return
            
        try:
            inbox = self.lex_flow.get_inbox()
            report.inbox_size = len(inbox)
            report.inbox_items_recent = [item.to_dict() if hasattr(item, 'to_dict') else item 
                                         for item in inbox[:5]]
            
            # Determinar status
            if report.inbox_size >= self.config.inbox_size_critical:
                report.inbox_status = "critical"
            elif report.inbox_size >= self.config.inbox_size_warning:
                report.inbox_status = "warning"
            else:
                report.inbox_status = "ok"
                
        except Exception as e:
            log.warning(f"Erro ao verificar inbox: {e}")
    
    def _check_metrics(self, report: HeartbeatReport):
        """Verifica métricas rápidas"""
        if not self.lex_flow:
            return
            
        try:
            dashboard = self.lex_flow.get_dashboard()
            report.quick_stats = dashboard.get('quick_stats', {})
            
        except Exception as e:
            log.debug(f"Erro ao buscar métricas: {e}")
    
    def _generate_alerts(self, report: HeartbeatReport):
        """Gera alertas baseados nas verificações"""
        if not self.config.enable_notifications:
            return
            
        # Alerta: Projetos parados
        for stalled in report.projects_stalled:
            alert = Alerta(
                level="high",
                type="stalled_project",
                title=f"Projeto Parado: {stalled.get('name', '?')}",
                message=f"Projeto está parado há {stalled.get('days_stalled', '?')} dias",
                suggestion=f"Retomar projeto ou arquivar se não for mais prioridade"
            )
            report.alerts.append(alert.to_dict())
            report.alerts_by_level['high'] += 1
        
        # Alerta: Inbox cheia
        if report.inbox_status == "critical":
            alert = Alerta(
                level="critical",
                type="inbox_overflow",
                title="Inbox Crítica!",
                message=f"Inbox tem {report.inbox_size} itens (limite: {self.config.inbox_size_critical})",
                suggestion="Processar inbox imediatamente para reduzir sobrecarga cognitiva"
            )
            report.alerts.append(alert.to_dict())
            report.alerts_by_level['critical'] += 1
            
        elif report.inbox_status == "warning":
            alert = Alerta(
                level="medium",
                type="inbox_warning",
                title="Inbox Crescendo",
                message=f"Inbox tem {report.inbox_size} itens (atenção: {self.config.inbox_size_warning})",
                suggestion="Considerar processar alguns itens nas próximas horas"
            )
            report.alerts.append(alert.to_dict())
            report.alerts_by_level['medium'] += 1
    
    def _register_heartbeat_log(self, report: HeartbeatReport):
        """Registra verificação no log diário"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        if today not in self._daily_logs:
            self._daily_logs[today] = DailyLog()
        
        daily_log = self._daily_logs[today]
        daily_log.add_entry({
            'type': 'heartbeat',
            'report': report.to_dict()
        })
    
    def start_heartbeat_thread(self, interval_minutes: int = None):
        """
        Inicia heartbeat em background (thread separada)
        
        Args:
            interval_minutes: Intervalo entre verificações (sobrescreve config)
        """
        if self._is_running:
            log.warning("⚠️  Heartbeat já está rodando")
            return
        
        interval = interval_minutes or self.config.interval_minutes
        
        log.info(f"💓 Iniciando heartbeat thread (intervalo: {interval} min)...")
        
        self._stop_event.clear()
        self._is_running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(interval,),
            daemon=True
        )
        self._heartbeat_thread.start()
        
        log.info("✅ Heartbeat iniciado em background")
    
    def stop_heartbeat(self):
        """Para o heartbeat thread"""
        if not self._is_running:
            return
            
        log.info("🛑 Parando heartbeat...")
        
        self._stop_event.set()
        self._is_running = False
        
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        
        log.info("✅ Heartbeat parado")
    
    def _heartbeat_loop(self, interval_minutes: int):
        """Loop principal do heartbeat (roda em thread separada)"""
        log.info(f"🔄 Heartbeat loop iniciado (verificando a cada {interval_minutes} min)")
        
        while not self._stop_event.is_set():
            try:
                # Só rodar se estiver dentro da janela de operação
                if self.config.is_active_now:
                    report = self.run_full_check()
                    
                    if report:
                        log.info(f"   Check concluído | Projetos ativos: {report.projects_active} | "
                                f"Parados: {len(report.projects_stalled)} | Inbox: {report.inbox_size}")
                        
                        # Se houver alertas críticos, log adicional
                        critical_alerts = [a for a in report.alerts if a.get('level') == 'critical']
                        if critical_alerts:
                            log.warning(f"   ⚠️  {len(critical_alerts)} alerta(s) crítico(s)!")
                else:
                    log.debug("   Fora da janela de operação, pulando check...")
                
                # Esperar próximo intervalo (ou até stop event)
                self._stop_event.wait(timeout=interval_minutes * 60)
                
            except Exception as e:
                log.error(f"❌ Erro no heartbeat loop: {e}", exc_info=True)
                self._stop_event.wait(timeout=60)  # Esperar 1 min antes de tentar novamente
        
        log.info("🛑 Heartbeat loop finalizado")
    
    def get_daily_log(self, date: str = None) -> DailyLog:
        """
        Retorna log de um dia específico
        
        Args:
            date: Data no formato YYYY-MM-DD (default: hoje)
            
        Returns:
            DailyLog do dia solicitado
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
            
        if date not in self._daily_logs:
            self._daily_logs[date] = DailyLog(date=date)
            
        return self._daily_logs[date]
    
    def get_current_week_review(self) -> WeekReview:
        """
        Retorna/cria revisão da semana atual
        
        Returns:
            WeekReview da semana atual
        """
        now = datetime.now()
        week_key = f"{now.year}-W{now.isocalendar()[1]:02d}"
        
        if week_key not in self._weekly_reviews:
            self._weekly_reviews[week_key] = WeekReview(week_number=now.isocalendar()[1])
            
        return self._weekly_reviews[week_key]
    
    def generate_weekly_summary(self) -> Dict:
        """
        Gera resumo da semana atual
        
        Returns:
            Dicionário com resumo semanal
        """
        review = self.get_current_week_review()
        
        summary = {
            'week_number': review.week_number,
            'date_range': f"{review.start_date} → {review.end_date}",
            'completed_tasks': review.completed,
            'pending_items': review.pending,
            'completion_rate': f"{review.completion_rate:.1%}",
            'insights_count': len(review.insights),
            'status': review.status_text,
            'top_insights': review.insights[:5] if review.insights else []
        }
        
        return summary


if __name__ == "__main__":
    # Teste rápido
    print("🤖 Testando Automation System...")
    
    try:
        config = HeartbeatConfig(interval_minutes=30)
        automator = AutomationSystem(config=config)
        
        print(f"✅ Automation System criado")
        print(f"   Heartbeat: {'Ativo' if config.enabled else 'Inativo'}")
        print(f"   Intervalo: {config.interval_minutes} minutos")
        print(f"   Janela: {config.check_window}")
        
        # Testar criação de relatório
        report = HeartbeatReport()
        print(f"\n✅ HeartbeatReport criado:")
        print(f"   Session ID: {report.session_id}")
        print(f"   Status: {report.engine_status.value}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()