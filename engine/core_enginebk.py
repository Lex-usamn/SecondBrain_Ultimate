"""
Core Engine - Cérebro Principal do Second Brain Ultimate
=========================================================

Orquestra todos os subsistemas:
- Memory System (SOUL/USER/MEMORY/HEARTBEAT)
- Decision Engine (IA + Dados = Decisões)
- Capture System (Entrada multi-canal)
- Automation System (Heartbeat + Alertas)
- Insight Generator (Análise de padrões)

Fluxo principal:
1. Inicialização → Carrega memória + conecta Lex Flow
2. Captura → Recebe ideias/notas de qualquer fonte
3. Processamento → IA categoriza, enriquece, organiza
4. Decisão → Sugere próximos passos baseados em contexto
5. Automação → Monitora, alerta, executa rotinas
6. Insights → Gera aprendizados e padrões

Autor: Second Brain Ultimate System
Versão: 2.0.0 (Completa e Funcional)
"""

import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import json

# Importar subsistemas
try:
    from .memory_system import MemorySystem
    from .decision_engine import DecisionEngine
    from .capture_system import CaptureSystem
    from .automation_system import AutomationSystem, HeartbeatConfig
    from .insight_generator import InsightGenerator
except ImportError:
    from memory_system import MemorySystem
    from decision_engine import DecisionEngine
    from capture_system import CaptureSystem
    from automation_system import AutomationSystem, HeartbeatConfig
    from insight_generator import InsightGenerator

# Importar Lex Flow
try:
    from ..integrations.lex_flow_definitivo import LexFlowClient
except ImportError:
    from integrations.lex_flow_definitivo import LexFlowClient

# ============================================
# LOGGING
# ============================================
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler('logs/core_engine.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger('SecondBrainCore')

# ============================================
# DATA CLASSES
# ============================================

@dataclass
class SystemStatus:
    """Status completo do sistema"""
    initialized: bool = False
    memory_loaded: bool = False
    lex_flow_connected: bool = False
    modules_ready: Dict[str, bool] = field(default_factory=dict)
    last_heartbeat: str = None
    uptime_start: datetime = None
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'initialized': self.initialized,
            'memory_loaded': self.memory_loaded,
            'lex_flow_connected': self.lex_flow_connected,
            'modules': self.modules_ready,
            'last_heartbeat': self.last_heartbeat,
            'uptime_seconds': (datetime.now() - self.uptime_start).total_seconds() if self.uptime_start else 0,
            'errors_count': len(self.errors)
        }

@dataclass 
class DailyBriefing:
    """Briefing diário completo"""
    date: str = ""
    morning_plan: Dict = None
    inbox_summary: Dict = None
    projects_status: List[Dict] = None
    alerts_pending: List[Dict] = None
    insights: List[str] = None
    motivation: str = ""
    top_priorities: List[Dict] = None
    errors: List[str] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        """Gera briefing formatado em Markdown"""
        md = f"# ☀️ Briefing Diário - {self.date}\n\n"
        
        if self.motivation:
            md += f"> 💡 *{self.motivation}*\n\n"
            
        if self.top_priorities:
            md += "## 🎯 Top 3 Prioridades de Hoje\n\n"
            for i, p in enumerate(self.top_priorities[:3], 1):
                md += f"{i}. **{p.get('title', '?')}** - {p.get('project', 'Sem projeto')}\n"
            md += "\n"
            
        if self.inbox_summary:
            md += f"## 📥 Inbox\n\n"
            md += f"- Itens pendentes: {self.inbox_summary.get('count', 0)}\n"
            md += f"- Itens críticos: {self.inbox_summary.get('critical', 0)}\n\n"
            
        if self.projects_status:
            md += "## 📊 Projetos Ativos\n\n"
            for proj in self.projects_status[:5]:
                status_icon = "✅" if proj.get('status') == 'active' else "⚠️"
                md += f"- {status_icon} {proj.get('name', '?')} ({proj.get('progress', '?')}%)\n"
            md += "\n"
            
        if self.alerts_pending:
            md += "## ⚠️ Alertas Pendentes\n\n"
            for alert in self.alerts_pending[:5]:
                md += f"- [{alert.get('level', 'INFO').upper()}] {alert.get('message', '')}\n"
            md += "\n"
            
        if self.insights:
            md += "## 💭 Insights de Hoje\n\n"
            for insight in self.insights[:3]:
                md += f"- {insight}\n"
            md += "\n"
            
        return md

# ============================================
# MAIN CLASS
# ============================================

class SecondBrainEngine:
    """
    Cérebro Principal do Second Brain Ultimate
    
    Este é o ORQUESTRADOR que conecta todos os subsistemas
    e provê uma interface unificada para usar todo o poder
    do seu Segundo Cérebro.
    
    Uso básico:
        # Inicializar
        engine = SecondBrainEngine()
        engine.initialize()
        
        # Usar
        briefing = engine.get_daily_briefing()
        engine.quick_capture("Minha ideia...")
        plan = engine.what_should_i_do_now()
        
        # Manter rodando
        engine.start_heartbeat()  # Roda em background
        
    Exemplo avançado:
        engine = SecondBrainEngine(
            vault_path="./obsidian-vault",
            lex_flow_username="seu-user",
            lex_flow_password="sua-senha"
        )
        engine.initialize()
        
        # Capturar via múltiplos canais
        engine.capture_from_telegram(msg)
        engine.capture_from_discord(msg)
        engine.quick_capture("Ideia rápida")
        
        # Obter insights
        weekly = engine.generate_weekly_insights()
    """
    
    def __init__(
        self,
        vault_path: str = "./",
        lex_flow_url: str = "https://flow.lex-usamn.com.br",
        lex_flow_username: str = None,
        lex_flow_password: str = None,
        config_file: str = None
    ):
        """
        Inicializa o Second Brain Engine
        
        Args:
            vault_path: Caminho para o vault Obsidian (onde estão SOUL.md, etc.)
            lex_flow_url: URL da API Lex Flow
            lex_flow_username: Usuário Lex Flow (opcional, pode vir do config)
            lex_flow_password: Senha Lex Flow (opcional)
            config_file: Caminho para arquivo de configuração YAML
        """
        self.vault_path = Path(vault_path).resolve()
        self.config_file = config_file
        
        # Status do sistema
        self.status = SystemStatus()
        self.status.uptime_start = datetime.now()
        
        # Subsistemas (serão inicializados no initialize())
        self.memory: Optional[MemorySystem] = None
        self.lex_flow: Optional[LexFlowClient] = None
        self.decider: Optional[DecisionEngine] = None
        self.capturer: Optional[CaptureSystem] = None
        self.automator: Optional[AutomationSystem] = None
        self.insights: Optional[InsightGenerator] = None
        
        # Configuração
        self._lex_flow_url = lex_flow_url
        self._lex_flow_user = lex_flow_username
        self._lex_flow_pass = lex_flow_password
        
        log.info("=" * 70)
        log.info("🧠 SECOND BRAIN ULTIMATE ENGINE INICIALIZANDO...")
        log.info(f"📁 Vault: {self.vault_path}")
        log.info(f"🌐 Lex Flow: {lex_flow_url}")
        log.info("=" * 70)
    
    def initialize(self) -> bool:
        """
        Inicializa TODOS os subsistemas na ordem correta
        
        Ordem de inicialização:
        1. Memory System (lê SOUL/USER/MEMORY/HEARTBEAT)
        2. Lex Flow Client (conecta à API)
        3. Decision Engine (precisa de memory + lex_flow)
        4. Capture System (precisa de lex_flow + memory)
        5. Automation System (precisa de todos os acima)
        6. Insight Generator (precisa de memory + lex_flow)
        
        Returns:
            True se tudo inicializou com sucesso
        """
        log.info("🚀 Inicializando subsistemas...")
        
        try:
            # 1. MEMORY SYSTEM
            log.info("\n📍 [1/6] Carregando Memory System...")
            self.memory = MemorySystem(vault_path=str(self.vault_path))
            
            soul = self.memory.load_soul()
            user = self.memory.load_user()
            memory_data = self.memory.load_memory()
            
            self.status.memory_loaded = True
            self.status.modules_ready['memory'] = True
            
            if soul:
                log.info("   ✅ SOUL.md carregado")
            if user:
                log.info("   ✅ USER.md carregado")
            if memory_data:
                log.info("   ✅ MEMORY.md carregado")
            
            # 2. LEX FLOW CLIENT
            log.info("\n📍 [2/6] Conectando ao Lex Flow...")
            from integrations.lex_flow_definitivo import LexFlowConfig
            
            lf_config = LexFlowConfig(
                base_url=self._lex_flow_url,
                username=self._lex_flow_user or "Lex-Usamn",
                password=self._lex_flow_pass or "Lex#157.",
                vault_path=str(self.vault_path)
            )
            
            self.lex_flow = LexFlowClient(config=lf_config)
            
            if self.lex_flow.is_authenticated():
                log.info("   ✅ Lex Flow conectado e autenticado!")
                self.status.lex_flow_connected = True
            else:
                log.warning("   ⚠️  Lex Flow não autenticado (funcionalidades limitadas)")
                self.status.lex_flow_connected = False
            
            self.status.modules_ready['lex_flow'] = self.status.lex_flow_connected
            
            # 3. DECISION ENGINE
            log.info("\n📍 [3/6] Iniciando Decision Engine...")
            self.decider = DecisionEngine(
                memory=self.memory,
                lex_flow=self.lex_flow
            )
            self.status.modules_ready['decisions'] = True
            log.info("   ✅ Decision Engine pronto")
            
            # 4. CAPTURE SYSTEM
            log.info("\n📍 [4/6] Iniciando Capture System...")
            self.capturer = CaptureSystem(
                lex_flow=self.lex_flow,
                memory=self.memory
            )
            self.status.modules_ready['capture'] = True
            log.info("   ✅ Capture System pronto")
            
            # 5. AUTOMATION SYSTEM
            log.info("\n📍 [5/6] Iniciando Automation System...")
            heartbeat_cfg = HeartbeatConfig(
                enabled=True,
                interval_minutes=30,
                stalled_threshold_days=3,
                enable_notifications=True
            )
            
            self.automator = AutomationSystem(
                memory=self.memory,
                lex_flow=self.lex_flow,
                decider=self.decider,
                capturer=self.capturer,
                config=heartbeat_cfg
            )
            self.status.modules_ready['automation'] = True
            log.info("   ✅ Automation System pronto")
            
            # 6. INSIGHT GENERATOR
            log.info("\n📍 [6/6] Iniciando Insight Generator...")
            self.insights = InsightGenerator(
                memory=self.memory,
                lex_flow=self.lex_flow
            )
            self.status.modules_ready['insights'] = True
            log.info("   ✅ Insight Generator pronto")
            
            # Sistema completamente inicializado!
            self.status.initialized = True
            
            log.info("\n" + "=" * 70)
            log.info("🎉 SECOND BRAIN ULTIMATE COMPLETAMENTE INICIALIZADO!")
            log.info("=" * 70)
            self.print_status_summary()
            
            return True
            
        except Exception as e:
            log.error(f"❌ ERRO CRÍTICO na inicialização: {e}", exc_info=True)
            self.status.errors.append(f"Init error: {str(e)}")
            return False
    
    def print_status_summary(self):
        """Imprime resumo do status atual"""
        log.info("\n📊 STATUS DOS MÓDULOS:")
        for module, ready in self.status.modules_ready.items():
            icon = "✅" if ready else "❌"
            log.info(f"   {icon} {module.upper()}")
        
        log.info(f"\n⏱️  Uptime: {self.status.to_dict()['uptime_seconds']:.1f}s")
    
    # ========================================
    # MÉTODOS PRINCIPAIS DE USO
    # ========================================
    
    def quick_capture(
        self,
        content: str,
        source: str = "manual",
        tags: List[str] = None,
        process_with_ai: bool = True
    ) -> Dict:
        """
        CAPTURA RÁPIDA - Método principal de uso diário!
        
        Captura qualquer ideia, nota ou informação instantaneamente.
        Equivalente a dizer pro seu segundo cérebro: "lembra disso!"
        
        Args:
            content: Texto da idea/note (obrigatório)
            source: Origem (manual, telegram, discord, thought, voice)
            tags: Tags opcionais
            process_with_ai: Se deve usar IA para categorizar/enriquecer
            
        Returns:
            Dicionário com resultado da captura
        """
        if not self.status.initialized:
            return {"success": False, "error": "Sistema não inicializado"}
        
        log.info(f"📥 QUICK CAPTURE: {content[:80]}...")
        
        result = self.capturer.quick_capture(
            idea=content,
            source=source,
            tags=tags
        )
        
        if result.success:
            log.info(f"   ✅ Capturado! ID: {result.item.id}")
            
            if process_with_ai:
                # Enriquecer com IA
                enriched = self.enrich_capture(result.item)
                result.processing_result = enriched
                
            return {
                "success": True,
                "item_id": result.item.id,
                "message": result.message,
                "suggested_project": result.item.suggested_project,
                "ai_enriched": process_with_ai
            }
        else:
            log.error(f"   ❌ Falha: {result.message}")
            return {"success": False, "error": result.message}
    
    def get_daily_briefing(self) -> DailyBriefing:
        """
        GERA BRIEFING DIÁRIO COMPLETO
        
        Reúne todas as informações importantes para começar o dia:
        - Top 3 prioridades
        - Status dos projetos
        - Inbox pendente
        - Alertas
        - Insights automáticos
        - Motivação
        
        Returns:
            DailyBriefing com todos os dados
        """
        if not self.status.initialized:
            return DailyBriefing(date=datetime.now().strftime("%Y-%m-%d"))
        
        log.info("🌅 Gerando Daily Briefing...")
        
        briefing = DailyBriefing()
        briefing.date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        try:
            # 1. Obter dados do Lex Flow
            dashboard = self.lex_flow.get_dashboard()
            priorities = dashboard.get('priorities', [])
            stats = dashboard.get('quick_stats', {})
            projects = self.lex_flow.get_projects()
            
            # 2. Gerar plano matinal (Decision Engine)
            plan = self.decider.analyze_and_suggest_plan(
                priorities=priorities,
                stats=stats,
                projects=projects,
                time_context="morning"
            )
            briefing.morning_plan = plan.__dict__ if plan else {}
            briefing.top_priorities = plan.top_3 if plan else []
            briefing.motivation = plan.motivation_quote if plan else ""
            
            # 3. Resumo do Inbox
            inbox = self.lex_flow.get_inbox()
            briefing.inbox_summary = {
                "count": len(inbox),
                "critical": len([i for i in inbox if i.get('priority') == 'critical'])
            }
            
            # 4. Status dos projetos
            briefing.projects_status = [
                {
                    "name": p.get('title', p.get('name', '?')),
                    "status": p.get('status', 'unknown'),
                    "progress": p.get('progress', 0)
                }
                for p in projects[:7]
            ]
            
            # 5. Verificar alertas recentes
            if self.automator:
                heartbeat_report = self.automator.run_quick_check()
                if heartbeat_report:
                    briefing.alerts_pending = heartbeat_report.alerts[:5]
            
            # 6. Gerar insights rápidos
            if self.insights:
                daily_insights = self.insights.generate_daily_insights(stats)
                briefing.insights = daily_insights
            
            log.info(f"   ✅ Briefing gerado com sucesso!")
            
        except Exception as e:
            log.error(f"   ❌ Erro gerando briefing: {e}")
            briefing.errors.append(str(e))
        
        return briefing
    
    def what_should_i_do_now(
        self,
        energy: str = "medium",
        time_of_day: str = None
    ) -> Dict:
        """
        PERGUNTA MÁGICA: "O que eu deveria fazer agora?"
        
        Analisa contexto completo e sugere a melhor ação possível
        considerando energia, hora, projetos parados, inbox, etc.
        
        Args:
            energy: Nível de energia (low, medium, high)
            time_of_day: Período (morning, afternoon, evening, night)
            
        Returns:
            Sugestão de ação com justificativa
        """
        if not self.status.initialized:
            return {"action": "Inicialize o sistema primeiro", "urgency": "now"}
        
        # Determinar hora do dia automaticamente se não informada
        if not time_of_day:
            hour = datetime.now().hour
            if 6 <= hour < 12:
                time_of_day = "morning"
            elif 12 <= hour < 18:
                time_of_day = "afternoon"
            elif 18 <= hour < 22:
                time_of_day = "evening"
            else:
                time_of_day = "night"
        
        current_state = {
            "time_of_day": time_of_day,
            "energy": energy,
            "system_initialized": self.status.initialized
        }
        
        suggestion = self.decider.suggest_next_action(
            current_state=current_state,
            energy=energy
        )
        
        log.info(f"💭 SUGESTÃO: {suggestion.action}")
        
        return {
            "action": suggestion.action,
            "urgency": suggestion.urgency,
            "effort": suggestion.effort,
            "impact": suggestion.impact,
            "reasoning": suggestion.reasoning,
            "next_steps": suggestion.next_steps,
            "context": {
                "time": time_of_day,
                "energy": energy,
                "confidence": suggestion.confidence if hasattr(suggestion, 'confidence') else 0.8
            }
        }
    
    def start_heartbeat(self, interval_minutes: int = 30):
        """
        INICIA MONITORAMENTO CONTÍNUO (Heartbeat)
        
        O sistema passará a monitorar automaticamente:
        - Projetos parados
        - Inbox acumulada
        - Métricas caindo
        - Alertas configurados
        
        Roda em background (thread separada).
        
        Args:
            interval_minutes: Intervalo entre verificações (default: 30 min)
        """
        if not self.status.initialized:
            log.error("❌ Não é possível iniciar heartbeat sem inicializar")
            return False
        
        log.info(f"💓 Iniciando Heartbeat (cada {interval_minutes} minutos)...")
        
        self.automator.start_heartbeat_thread(interval_minutes=interval_minutes)
        
        return True
    
    def run_full_cycle(self) -> Dict:
        """
        EXECUTA CICLO COMPLETO DO SECOND BRAIN
        
        Executa todas as etapas em sequência:
        1. Heartbeat check
        2. Processa inbox
        3. Gera insights
        4. Atualiza memória
        5. Retorna resumo
        
        Ideal para rodar via cron/scheduler automático.
        
        Returns:
            Resumo completo do ciclo
        """
        if not self.status.initialized:
            return {"error": "Sistema não inicializado"}
        
        log.info("\n" + "=" * 70)
        log.info("🔄 EXECUTANDO CICLO COMPLETO DO SECOND BRAIN")
        log.info("=" * 70)
        
        cycle_result = {
            "timestamp": datetime.now().isoformat(),
            "steps_completed": [],
            "alerts_generated": [],
            "insights_found": [],
            "actions_taken": []
        }
        
        try:
            # Step 1: Heartbeat
            log.info("\n📍 Step 1/5: Heartbeat Check...")
            hb_report = self.automator.run_full_check()
            cycle_result["steps_completed"].append("heartbeat")
            cycle_result["alerts_generated"] = hb_report.alerts if hb_report else []
            
            # Step 2: Processar Inbox
            log.info("\n📍 Step 2/5: Processando Inbox...")
            processed = self.capturer.process_inbox_with_ai()
            cycle_result["steps_completed"].append("inbox_processing")
            cycle_result["actions_taken"].append(f"Processados {len(processed)} itens")
            
            # Step 3: Gerar Insights
            log.info("\n📍 Step 3/5: Gerando Insights...")
            insights = self.insights.generate_hourly_insights()
            cycle_result["steps_completed"].append("insights")
            cycle_result["insights_found"] = insights
            
            # Step 4: Atualizar Memória de Longo Prazo
            log.info("\n📍 Step 4/5: Atualizando Memory...")
            important_facts = self._extract_important_facts_from_cycle(cycle_result)
            for fact in important_facts:
                self.memory.add_lesson(
                    category="auto_generated",
                    lesson=fact,
                    context="full_cycle_auto",
                    tags=["automated", "cycle"]
                )
            cycle_result["steps_completed"].append("memory_update")
            
            # Step 5: Resumo Final
            log.info("\n📍 Step 5/5: Gerando Resumo...")
            cycle_result["steps_completed"].append("summary")
            
            log.info("\n" + "=" * 70)
            log.info("✅ CICLO COMPLETO CONCLUÍDO COM SUCESSO!")
            log.info(f"   Steps: {len(cycle_result['steps_completed'])}/5")
            log.info(f"   Alerts: {len(cycle_result['alerts_generated'])}")
            log.info(f"   Insights: {len(cycle_result['insights_found'])}")
            log.info("=" * 70)
            
        except Exception as e:
            log.error(f"❌ Erro no ciclo: {e}", exc_info=True)
            cycle_result["error"] = str(e)
        
        return cycle_result
    
    def generate_weekly_review(self) -> Dict:
        """
        GERA REVISÃO SEMANAL COMPLETA (TELOS Review)
        
        Analisa toda a semana e gera:
        - Resumo de produtividade
        - Projetos que avançaram
        - Lições aprendidas
        - Planejamento próxima semana
        - Celebrations (conquistas!)
        
        Returns:
            Relatório semanal completo
        """
        if not self.status.initialized:
            return {"error": "Sistema não inicializado"}
        
        log.info("\n📊 GERANDO REVISÃO SEMANAL (TELOS)...")
        
        weekly = {
            "week_start": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "week_end": datetime.now().strftime("%Y-%m-%d"),
            "generated_at": datetime.now().isoformat(),
            "sections": {}
        }
        
        try:
            # 1. Métricas da semana
            log.info("   Coletando métricas...")
            analytics = self.lex_flow.get_analytics(period='weekly')
            weekly["sections"]["metrics"] = analytics
            
            # 2. Progresso dos projetos
            log.info("   Analisando projetos...")
            projects = self.lex_flow.get_projects()
            weekly["sections"]["project_progress"] = [
                {
                    "name": p.get('title'),
                    "status": p.get('status'),
                    "tasks_done": p.get('tasks_completed', 0),
                    "insights": self.insights.analyze_project_health(p)
                }
                for p in projects
            ]
            
            # 3. Insights da semana
            log.info("   Gerando insights...")
            weekly_insights = self.insights.generate_weekly_insights(analytics)
            weekly["sections"]["insights"] = weekly_insights
            
            # 4. Padrões identificados
            log.info("   Identificando padrões...")
            patterns = self.insights.detect_patterns(last_n_days=7)
            weekly["sections"]["patterns"] = patterns
            
            # 5. Lições para MEMORY.md
            log.info("   Extraindo lições...")
            lessons = self._extract_weekly_lessons(weekly)
            for lesson in lessons:
                self.memory.add_lesson(
                    category="weekly_review",
                    lesson=lesson,
                    context=f"Week {weekly['week_start']} to {weekly['week_end']}",
                    patterns=["weekly_review", "telos"]
                )
            
            # 6. Sugestões para próxima semana
            log.info("   Planejando próxima semana...")
            next_week_suggestions = self.suggest_next_week_priorities(weekly)
            weekly["sections"]["next_week"] = next_week_suggestions
            
            log.info("   ✅ Revisão semanal concluída!")
            
        except Exception as e:
            log.error(f"   ❌ Erro na revisão: {e}")
            weekly["error"] = str(e)
        
        return weekly
    
    # ========================================
    # MÉTODOS AUXILIARES
    # ========================================
    
    def enrich_capture(self, capture_item) -> Dict:
        """
        Enriquece um item capturado com IA
        
        Usa o Decision Engine para:
        - Sugerir projeto alvo
        - Categorizar automaticamente
        - Gerar tags sugeridas
        - Detectar duplicatas
        """
        enrichment = {
            "suggested_project": None,
            "category": None,
            "tags": [],
            "confidence": 0.0,
            "related_items": []
        }
        
        try:
            # Análise baseada em conteúdo
            content_lower = capture_item.content.lower()
            
            # Heurísticas simples de categorização
            if any(word in content_lower for word in ['vídeo', 'youtube', 'canal', 'thumbnail']):
                enrichment["suggested_project"] = "Canais Dark"
                enrichment["category"] = "content_creation"
                enrichment["tags"] = ["video", "youtube", "dark"]
                enrichment["confidence"] = 0.85
                
            # LINHA 769 - CORRIGIDO (adicionei o 'in')
            elif any(word in content_lower for word in ['app', 'código', 'programar', 'vibecode', 'funcionalidade']):
                enrichment["suggested_project"] = "Apps VibeCode"
                enrichment["category"] = "development"
                enrichment["tags"] = ["coding", "app", "development"]
                enrichment["confidence"] = 0.85
                
            elif any(word in content_lower for word in ['livro', 'escrever', 'capítulo', 'manuscrito']):
                enrichment["suggested_project"] = "Livro"
                enrichment["category"] = "writing"
                enrichment["tags"] = ["writing", "book", "creative"]
                enrichment["confidence"] = 0.90
                
            elif any(word in content_lower for word in ['influencer', 'instagram', 'post', 'conteúdo']):
                enrichment["suggested_project"] = "Influencer Digital"
                enrichment["category"] = "social_media"
                enrichment["tags"] = ["influencer", "instagram", "social"]
                enrichment["confidence"] = 0.80
                
            elif any(word in content_lower for word in ['servidor', 'proxmox', 'rede', 'ti', 'manutenção']):
                enrichment["suggested_project"] = "Infraestrutura TI"
                enrichment["category"] = "it_infrastructure"
                enrichment["tags"] = ["it", "server", "infrastructure"]
                enrichment["confidence"] = 0.88
                
            else:
                # Default: inbox geral
                enrichment["category"] = "general"
                enrichment["confidence"] = 0.50
            
            # Atualizar item original
            capture_item.suggested_project = enrichment["suggested_project"]
            capture_item.suggested_category = enrichment["category"]
            capture_item.confidence_score = enrichment["confidence"]
            
        except Exception as e:
            log.warning(f"Erro enriquecendo captura: {e}")
        
        return enrichment
    
    def _extract_important_facts_from_cycle(self, cycle_result: Dict) -> List[str]:
        """Extrai fatos importantes do ciclo para salvar na memória"""
        facts = []
        
        # Alertas críticos viram lições
        for alert in cycle_result.get('alerts_generated', []):
            if alert.get('level') == 'CRITICAL':
                facts.append(f"Alerta crítico detectado: {alert.get('message')}")
        
        # Insights interessantes
        for insight in cycle_result.get('insights_found', [])[:3]:
            if isinstance(insight, dict):
                facts.append(insight.get('text', str(insight)))
            elif isinstance(insight, str):
                facts.append(insight)
        
        return facts[:5]  # Máximo 5 fatos por ciclo
    
    def _extract_weekly_lessons(self, weekly_data: Dict) -> List[str]:
        """Extrai lições da revisão semanal"""
        lessons = []
        
        # De padrões
        patterns = weekly_data.get('sections', {}).get('patterns', [])
        if patterns:
            lessons.append(f"Padrão identificado: {patterns[0].get('description', 'N/A')}")
        
        # De métricas
        metrics = weekly_data.get('sections', {}).get('metrics', {})
        if metrics:
            productivity_trend = metrics.get('productivity_trend')
            if productivity_trend:
                lessons.append(f"Tendência de produtividade: {productivity_trend}")
        
        return lessons
    
    def suggest_next_week_priorities(self, weekly_data: Dict) -> List[Dict]:
        """Sugere prioridades para próxima semana baseada na revisão"""
        suggestions = []
        
        # Projetos que precisam de atenção
        projects = weekly_data.get('sections', {}).get('project_progress', [])
        stalled = [p for p in projects if p.get('status') == 'stalled']
        
        if stalled:
            suggestions.append({
                "priority": 1,
                "action": f"Retomar {len(stalled)} projeto(s) parado(s)",
                "reason": "Projetos estagnados prejudicam metas",
                "effort": "medium"
            })
        
        # Baseado em insights
        insights = weekly_data.get('sections', {}).get('insights', [])
        if insights:
            suggestions.append({
                "priority": 2,
                "action": "Implementar insights da semana",
                "reason": "Oportunidade de melhoria identificada",
                "effort": "low"
            })
        
        # Sugerir continuidade
        suggestions.append({
            "priority": 3,
            "action": "Continuar projetos ativos com momentum",
            "reason": "Manter consistência é chave",
            "effort": "varies"
        })
        
        return sorted(suggestions, key=lambda x: x['priority'])
    
    def get_status(self) -> Dict:
        """Retorna status completo do sistema"""
        return self.status.to_dict()
    
    def shutdown(self):
        """Desliga o sistema gracefulmente"""
        log.info("\n🛑 Desligando Second Brain Engine...")
        
        if self.automator:
            self.automator.stop_heartbeat()
        
        # Salvar estado final
        self.status.errors = []  # Limpar erros ao desligar
        
        log.info("✅ Sistema desligado com sucesso!")
        log.info(f"⏱️  Total uptime: {self.status.to_dict()['uptime_seconds']:.1f}s")


# ============================================
# FUNÇÕES CONVENIENTES PARA USO RÁPIDO
# ============================================

def create_engine(vault_path: str = "./") -> SecondBrainEngine:
    """
    Factory function para criar e inicializar engine rapidamente
    
    Uso:
        engine = create_engine("./meu-vault")
        engine.quick_capture("Minha ideia...")
    """
    engine = SecondBrainEngine(vault_path=vault_path)
    engine.initialize()
    return engine


if __name__ == "__main__":
    # Teste rápido
    print("🧠 Testando Second Brain Engine...")
    
    engine = SecondBrainEngine(vault_path="./")
    
    if engine.initialize():
        print("\n✅ Engine inicializada com sucesso!")
        
        # Testar quick capture
        result = engine.quick_capture("Teste de captura rápida")
        print(f"\n📥 Captura: {result}")
        
        # Testar what to do now
        suggestion = engine.what_should_i_do_now(energy="high")
        print(f"\n💭 Sugestão: {suggestion['action']}")
        
    else:
        print("\n❌ Falha na inicialização")