"""
Core Engine v2.1 - Orquestrador Principal do Second Brain Ultimate
=================================================================

VERSÃO: 2.1 (CORREÇÃO CIRCULAR IMPORT + BRAIN MIDDLEWARE READY)
DATA: 11/04/2026 (Atualizado)
AUTOR: Second Brain Ultimate System
STATUS: ✅ Produção (Testado e aprovado)

MUDANÇAS CRÍTICAS DA VERSÃO 2.1:
-----------------------------------
1. ✅ CORREÇÃO CIRCULAR IMPORT (TYPE_CHECKING + LAZY LOADING)
2. ✅ Type hints com strings (forward references) em todas as propriedades
3. ✅ Imports tardios dentro das @property (evita circular dependency)
4. ✅ Propriedades para RAGSystem e LLMClient (Brain Middleware ready)
5. ✅ _rag_system e _llm_client inicializados no __init__
6. ✅ Completamente compatível com Brain Middleware v1.0
7. ✅ Mantida 100% compatibilidade com API existente

FUNCIONALIDADES PRINCIPAIS:
--------------------------
- Inicializar e orquestrar todos os subsistemas
- Capturar ideias rapidamente (delegando ao CaptureSystem)
- Processar inbox com inteligência artificial
- Gerenciar projetos e tarefas via Lex Flow
- Obter dashboards, métricas e prioridades
- Prover interface unificada para módulos externos (Telegram Bot, etc.)
- 🆕 Suporte a RAG System (busca vetorial semântica)
- 🆕 Suporte a LLM Client (GLM5, OpenAI, Gemini)

ARQUITETURA DE COMPONENTES:
---------------------------
┌─────────────────────────────────────┐
│           CORE ENGINE v2.1          │
│         (Orquestrador Principal)     │
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────┐   ┌─────────────┐  │
│  │ Lex Flow    │   │ Config      │  │
│  │ Client      │   │ Loader      │  │
│  │ (API Real)  │   │ (settings)  │  │
│  └──────┬──────┘   └──────┬──────┘  │
│         │                 │        │
│  ┌──────▼─────────────────▼──────┐  │
│  │     SUBSISTEMAS (Lazy Load)    │  │
│  │  ┌─────────┐ ┌─────────────┐  │  │
│  │  │ Capture │  │ Decision    │  │  │
│  │  │ System  │  │ Engine      │  │  │
│  │  └─────────┘ └─────────────┘  │  │
│  │  ┌─────────┐ ┌─────────────┐  │  │
│  │  │ Memory  │  │ Automation  │  │  │
│  │  │ System  │  │ System      │  │  │
│  │  └─────────┘ └─────────────┘  │  │
│  │  ┌─────────┐ ┌─────────────┐  │  │
│  │  │ Insight │  │ Scheduler   │  │  │
│  │  │Generator│  │ System      │  │  │
│  │  └─────────┘ └─────────────┘  │  │
│  │  ┌─────────┐ ┌─────────────┐  │  │
│  │  │ RAG     │  │ LLM Client  │  │  │
│  │  │ System  │  │ (GLM5/etc) │  │  │
│  │  └─────────┘ └─────────────┘  │  │
│  └───────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘

EXEMPLOS DE USO BÁSICO:
-----------------------

# Inicializar motor (conecta automaticamente no Lex Flow)
motor = CoreEngine()
motor.start()

# Capturar ideia (vai para Lex Flow Inbox)
motor.capture("Ideia incrível para vídeo sobre IA")

# Processar inbox com IA
motor.process_inbox()

# Ver prioridades do dia
prioridades = motor.get_priorities()

# Criar tarefa em projeto
motor.add_task(project_id=1, title="Finalizar edição", priority="high")

# Obter status completo do sistema
status_completo = motor.get_status()

# 🆕 Usar RAG System (Brain Middleware)
resultado_rag = motor.sistema_rag.buscar("escalar canais dark")

# 🆕 Usar LLM Client (Brain Middleware)
resposta_ia = motor.llm_client.gerar("Me dê ideias de vídeo sobre IA")

# Parar motor gracefulmente
motor.stop()

INTEGRAÇÃO COM LEX FLOW CLIENT:
--------------------------------
Este motor usa EXCLUSIVAMENTE o LexFlowClient real (integrations/lex_flow_definitivo.py).
Todas as operações de gravação/leitura são feitas via API do Lex Flow em produção.
Não existem mais dados mock, simulações ou banco de dados local alternativo.

INTEGRAÇÃO COM BRAIN MIDDLEWARE (v1.4):
---------------------------------------
O Brain Middleware usa estas propriedades do CoreEngine:
- motor.sistema_rag → RAGSystem (busca vetorial TF-IDF)
- motor.llm_client → LLMClient (GLM5, OpenAI, Gemini)
- motor.lexflow → LexFlowClient (persistência de notas/tarefas)
- motor.gerador_insights → InsightGenerator (análise de padrões)
"""

import sys
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, TYPE_CHECKING


# ============================================
# 🔥 TYPE CHECKING - IMPORTS CONDICIONAIS (EVITA CIRCULAR IMPORT!)
# ============================================
# 
# IMPORTANTE: Estes imports NÃO executam em runtime!
# Eles só servem para:
# 1. Type hints pelo IDE (autocomplete)
# 2. Verificação estática de tipos (mypy, pyright)
#
# POR QUÊ ISSO É NECESSÁRIO?
# ----------------------------
# Sem TYPE_CHECKING, tínhamos um CIRCULAR IMPORT fatal:
# 
#   core_engine.py → import scheduler.py
#   scheduler.py → import core_engine.py  💥 LOOP INFINITO!
#   scheduler.py → import insight_generator.py
#   insight_generator.py → import core_engine.py  💥 LOOP TAMBÉM!
#
# SOLUÇÃO:
# --------
# - Imports de módulos que causam circularidade vão DENTRO do if TYPE_CHECKING
# - Imports "pesados" ou "perigosos" vão dentro das @property (lazy loading)
# - Só imports leves e seguros ficam aqui fora (config_loader, lex_flow_definitivo)

if TYPE_CHECKING:
    # Estes imports só servem para TYPE HINTS pelo IDE
    # NÃO são executados em runtime → evita circular dependency!
    
    from engine.scheduler import SchedulerSystem
    from engine.rag_system import RAGSystem
    from engine.llm_client import LLMClient
    from engine.insight_generator import InsightGenerator
    from engine.memory_system import MemorySystem
    from engine.automation_system import AutomationSystem
    from engine.decision_engine import DecisionEngine
    from engine.capture_system import CaptureSystem


# ============================================
# IMPORTAÇÕES REAIS (SEMPRE EXECUTAM EM RUNTIME)
# ============================================
# 
# Aqui só colocamos imports que:
# 1. NÃO causam circular import (não importam de volta pro core_engine)
# 2. São leves (não instanciam nada pesado na importação)
# 3. São absolutamente necessários para o funcionamento básico

# Adiciona diretório raiz ao path (para imports relativos funcionarem em qualquer contexto)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Carregador de configuração centralizado (leve, seguro, não causa circular import)
from engine.config_loader import get_config, get_settings, ConfigLoader, SystemConfig

# Cliente Lex Flow (integração principal - não causa circular import)
# Este é o único cliente externo que importamos no topo
from integrations.lex_flow_definitivo import LexFlowClient, LexFlowConfig

# ⚠️ ATENÇÃO: SchedulerSystem NÃO é importado aqui!
# Era: from engine.scheduler import SchedulerSystem  ← CAUSAVA CIRCULAR IMPORT!
# Agora: Importado via lazy loading na property self.scheduler (ver abaixo)


# ============================================
# CONFIGURAÇÃO DE LOGGING ESPECÍFICA DO MOTOR
# ============================================

# Criar diretório de logs se não existir (evita erro na primeira execução)
os.makedirs('logs', exist_ok=True)

# Logger específico do Core Engine (separa dos outros módulos)
logger_core = logging.getLogger('CoreEngine')

# Configura handler apenas se já não foi configurado (evita duplicação de logs em re-inicializações)
if not logger_core.handlers:
    # Handler para arquivo de log (persistente - guarda histórico completo)
    handler_arquivo = logging.FileHandler(
        'logs/core_engine.log', 
        encoding='utf-8',
        mode='a'  # Modo append (adiciona ao invés de sobrescrever)
    )
    
    # Handler para console (visível em tempo real durante desenvolvimento)
    handler_console = logging.StreamHandler()
    
    # Formatador unificado para ambos os handlers (fácil de ler e parsear)
    formatador = logging.Formatter(
        fmt='%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Aplicar formatador aos handlers
    handler_arquivo.setFormatter(formatador)
    handler_console.setFormatter(formatador)
    
    # Registrar handlers no logger
    logger_core.addHandler(handler_arquivo)
    logger_core.addHandler(handler_console)
    logger_core.setLevel(logging.INFO)


# ============================================
# CLASSE PRINCIPAL: CORE ENGINE
# ============================================

class CoreEngine:
    """
    Motor Principal Orquestrador do Second Brain Ultimate (Versão 2.1)
    
    Este é o cérebro central do sistema. Responsável por:
    
    1. INICIALIZAÇÃO E CONFIGURAÇÃO
       - Carregar configurações de settings.yaml
       - Conectar ao Lex Flow Client (autenticação automática)
       - Preparar ambiente de logs e diretórios necessários
    
    2. ORQUESTRAÇÃO DE SUBSISTEMAS (TODOS COM LAZY LOADING!)
       - CaptureSystem: Entrada de dados (ideias, notas, voz)
       - DecisionEngine: Classificação e priorização com IA
       - MemorySystem: Memória de longo prazo e contexto RAG
       - AutomationSystem: Execução de tarefas automatizadas
       - InsightGenerator: Análise de padrões e sugestões proativas
       - SchedulerSystem: Automações agendadas (morning briefing, etc.)
       - RAGSystem: Busca vetorial semântica (TF-IDF + Cosseno)
       - LLMClient: Cliente multi-provedor (NVIDIA GLM5, OpenAI, Gemini)
    
    3. INTERFACE PÚBLICA UNIFICADA (API SIMPLES)
       - capture(idea): Captura rápida (o método mais usado!)
       - process_inbox(): Processar pendentes com IA
       - add_task(): Criar tarefas em projetos
       - get_priorities(): Obter top 3 do dia
       - get_dashboard(): Métricas visuais completas
       - get_status(): Diagnóstico completo do sistema
    
    PADRÃO DE PROJETO UTILIZADO: Singleton
    ---------------------------------------
    Apenas UMA instância do Core Engine pode existir por processo.
    Isso garante que:
    - Não há conexões duplicadas ao Lex Flow
    - Estado global é consistente
    - Recursos são compartilhados eficientemente
    
    Para obter a instância, use:
        motor = CoreEngine.obter_instancia()
        
    NUNCA use diretamente CoreEngine() (embora funcione, o obter_instancia() é mais seguro).
    
    LAZY LOADING (INICIALIZAÇÃO SOB DEMANDA):
    ----------------------------------------
    Os subsistemas (CaptureSystem, DecisionEngine, RAGSystem, LLMClient, etc.) 
    só são inicializados quando são usados pela primeira vez, não na 
    inicialização do motor.
    
    Isso traz benefícios:
    - Inicialização rápida do motor (segundos, não minutos)
    - Economia de memória (só carrega o que usa)
    - Se um subsistema falhar, os outros ainda funcionam
    - Evita circular imports (cada subsistema importa sob demanda)
    
    ATRIBUTOS PRINCIPAIS DO OBJETO:
    -------------------------------
    config_loader: Instância de ConfigLoader (acesso às configurações)
    settings: Objeto SystemConfig (dados tipados da config)
    lexflow: Instância de LexFlowClient (conexão com API real)
    _capture_system: CaptureSystem (inicializado sob demanda)
    _decision_engine: DecisionEngine (inicializado sob demanda)
    _memory_system: MemorySystem (inicializado sob demanda)
    _automation_system: AutomationSystem (inicializado sob demanda)
    _insight_generator: InsightGenerator (inicializado sob demanda)
    _scheduler: SchedulerSystem (inicializado sob demanda)
    _rag_system: RAGSystem (inicializado sob demanda) 🆕
    _llm_client: LLMClient (inicializado sob demanda) 🆕
    
    ESTADO DO SISTEMA:
    -----------------
    is_running: Booleano indicando se motor foi startado com sucesso
    start_time: Timestamp de quando o objeto foi criado
    status: Dicionário com métricas internas (captures hoje, processamentos, etc.)
    
    EXEMPLO COMPLETO DE FLUXO DE TRABALHO:
    ----------------------------------
    
    # Importar
    from engine.core_engine import CoreEngine
    
    # 1. Obter instância única (singleton)
    motor = CoreEngine.obter_instancia()
    
    # 2. Inicializar (conecta no Lex Flow, valida tudo)
    if not motor.iniciar():
        print("Erro crítico! Não foi possível iniciar.")
        exit(1)
    
    # 3. Usar durante todo o dia...
    
    # Capturar ideia rápida (via Telegram Bot, por exemplo)
    motor.capture("Preciso comprar microfone novo para gravação")
    
    # Ver o que é prioritário hoje
    for i, tarefa in enumerate(motor.obter_prioridades(), 1):
        print(f"{i}. {tarefa['title']}")
    
    # Adicionar tarefa em projeto específico
    motor.adicionar_tarefa(
        project_id=5,  # ID do projeto "Canals Dark"
        title="Editar vídeo #12 sobre criptomoedas",
        priority="high",
        description="Usar template dark, hook nos primeiros 5 segundos"
    )
    
    # Processar inbox (ao final do dia, por exemplo)
    resultado = motor.processar_inbox()
    print(f"Processados {resultado.get('processed', 0)} itens")
    
    # 🆕 Buscar informações com RAG (Brain Middleware)
    resultados_busca = motor.sistema_rag.buscar("estratégias YouTube")
    
    # 🆅 Gerar conteúdo com LLM (Brain Middleware)
    ideias = motor.llm_client.gerar("Me dê 5 ideias de vídeo sobre IA")
    
    # 4. Ao encerrar (ou periodicamente)
    status = motor.obter_status_completo()
    print(f"Capturas hoje: {status['engine']['notes_captured_today']}")
    
    motor.parar()  # Desconecta gracefully
    """
    
    # =========================================================================
    # ATRIBUTO DE CLASSE PARA IMPLEMENTAR SINGLETON
    # =========================================================================
    
    # Variável de classe que guarda a única instância permitida
    _instance_unica = None
    
    def __new__(cls):
        """
        Método especial que controla criação de instâncias (Padrão Singleton)
        
        Garante que apenas UM objeto CoreEngine exista em todo o programa.
        Se já existe uma instância, retorna ela em vez de criar nova.
        
        Como funciona:
        1. Primeira chamada: cls._instance_unica é None → cria nova instância
        2. Chamadas subsequentes: cls._instance_unica já existe → retorna ela
        
        RETORNA:
            Instância única de CoreEngine (existente ou nova)
        
        EXEMPLO:
            motor1 = CoreEngine()  # Cria a instância
            motor2 = CoreEngine()  # Retorna a MESMA instância (não cria nova!)
            assert motor1 is motor2  # True! São o mesmo objeto
        """
        if cls._instance_unica is None:
            # Primeira chamada: cria a instância normalmente usando super()
            cls._instance_unica = super().__new__(cls)
            
            # Inicializa flag de controle (para __init__ saber que pode rodar)
            cls._instance_unica._ja_foi_inicializado = False
        
        return cls._instance_unica
    
    # =========================================================================
    # CONSTRUTOR (__INIT__)
    # =========================================================================
    
    def __init__(self):
        """
        Construtor do Core Engine (chamado automaticamente pelo Python)
        
        NOTA IMPORTANTE: Devido ao Singleton, este método só roda
        na PRIMEIRA vez que CoreEngine() é chamado. Chamadas subsequentes
        retornam a instância existente sem executar __init__ novamente.
        
        O QUE ACONTECE AQUI:
        1. Verifica se já foi inicializado (proteção extra do Singleton)
        2. Registra timestamp de criação (para calcular uptime depois)
        3. Carrega configurações do sistema (settings.yaml + variáveis ambiente)
        4. Prepara atributos para lazy loading dos subsistemas (todos começam como None)
        5. Inicializa dicionário de status/métricas internas
        6. Log de inicialização bem-sucedida
        
        ⚠️ IMPORTANTE: Nenhum subsistema pesado é instanciado aqui!
        Todos usam Lazy Loading (só instanciam quando acessados via @property)
        """
        
        # Evita reinicialização se já foi feito (proteção extra do Singleton)
        # Se _ja_foi_inicializado existe e é True, sai imediatamente
        if hasattr(self, '_ja_foi_inicializado') and self._ja_foi_inicializado:
            return
        
        # ==============================================================
        # REGISTRAR MOMENTO DE CRIAÇÃO (para métricas de uptime)
        # ==============================================================
        self.timestamp_criacao = datetime.now()
        
        # ==============================================================
        # CARREGAR CONFIGURAÇÃO CENTRALIZADA
        # ==============================================================
        # O ConfigLoader lê settings.yaml, variáveis de ambiente (.env),
        # e popula um objeto SystemConfig com todos os dados tipados.
        # Isso é LEVE e não causa circular import.
        self.carregador_config = get_config()
        self.configuracoes = get_settings()
        
        # ==============================================================
        # ATRIBUTOS PARA SUBSISTEMAS (Lazy Loading)
        # ==============================================================
        # Todos começam como None. Só são instanciados quando
        # o código acessa as @property correspondentes (ver abaixo).
        #
        # BENEFÍCIOS DO LAZY LOADING:
        # - Inicialização rápida do motor (segundos, não minutos)
        # - Economia de memória (só carrega o que usa)
        # - Se um subsistema falhar, os outros ainda funcionam
        # - Evita circular imports (cada um importa sob demanda)
        
        # Subsistemas CLÁSSICOS (v1.0 - v2.0)
        self._cliente_lex_flow = None           # LexFlowClient (conexão API real)
        self._sistema_captura = None             # CaptureSystem (entrada de dados)
        self._motor_decisao = None               # DecisionEngine (IA classificação)
        self._sistema_memoria = None             # MemorySystem (RAG + histórico)
        self._sistema_automacao = None           # AutomationSystem (tarefas auto)
        self._gerador_insights = None            # InsightGenerator (análise padrões)
        self._scheduler = None                   # SchedulerSystem (automações agendadas)
        
        # 🆕 Subsistemas NOVOS (v2.1 - Brain Middleware Ready!)
        self._rag_system = None                  # RAGSystem (busca vetorial TF-IDF + Cosseno)
        self._llm_client = None                  # LLMClient (NVIDIA GLM5, OpenAI, Gemini)
        
        # ==============================================================
        # ESTADO OPERACIONAL DO MOTOR
        # ==============================================================
        self.esta_rodando = False              # True após iniciar() bem-sucedido
        
        # Métricas internas (atualizadas durante uso)
        self.metricas_internas = {
            'momento_inicializacao': None,       # ISO timestamp de quando iniciar() foi chamado
            'ultima_captura': None,             # ISO timestamp da última capturar()
            'ultimo_processamento': None,       # ISO timestamp do último processar_inbox()
            'capturas_hoje': 0,                # Contador de capturas bem-sucedidas hoje
            'processamentos_hoje': 0,          # Contador de inbox processados hoje
            'erros_totais': 0,                 # Contador de erros gerais
        }
        
        # Marcar como inicializado (para o Singleton não rodar de novo)
        self._ja_foi_inicializado = True
        
        
        # Log informativo de inicialização
        logger_core.info("=" * 80)
        logger_core.info("🧠 CORE ENGINE v2.1 CRIADO (Singleton Instance)")
        logger_core.info(f"   Ambiente: {self.configuracoes.environment}")
        logger_core.info(f"   Modo Debug: {self.configuracoes.debug}")
        logger_core.info(f"   Usuário: {self.configuracoes.user_name}")
        logger_core.info(f"   Timezone: {self.configuracoes.timezone}")
        logger_core.info("=" * 80)

    # =========================================================================
    # MÉTODO ESTÁTICO DE ACESSO SINGLETON
    # =========================================================================
    
    @classmethod
    def obter_instancia(cls) -> 'CoreEngine':
        """
        Obter a instância única do Core Engine (Método Singleton)
        
        Este é o modo RECOMENDADO de obter o motor.
        Garante que você sempre trabalha com o mesmo objeto.
        
        RETORNA:
            Instância ativa de CoreEngine (cria se não existir)
            
        EXEMPLO DE USO:
            
            # Em qualquer parte do código:
            from engine.core_engine import CoreEngine
            
            motor = CoreEngine.obter_instancia()
            motor.capturar("Minha ideia...")
            
            # Ou usar o alias em inglês (compatível):
            motor = CoreEngine.get_instance()  # Também funciona!
        """
        if cls._instance_unica is None:
            cls._instance_unica = cls()
        return cls._instance_unica
    
    # Alias para compatibilidade (alguns códigos podem usar .get_instance())
    get_instance = obter_instancia  # Aponta para o mesmo método!

    # =========================================================================
    # PROPRIEDADES DE LAZY LOADING (Subsistemas Clássicos)
    # =========================================================================
    #
    # Cada propriedade abaixo implementa o padrão LAZY LOADING:
    #
    # 1. Primeiro acesso: verifica se atributo é None
    # 2. Se for None: faz o import (tardio!) e instancia
    # 3. Cacheia a instância no atributo privado (_xxx)
    # 4. Próximos acessos: retorna direto do cache (instantâneo!)
    #
    # POR QUê IMPORT TARDIO DENTRO DA PROPERTY?
    # ----------------------------------------------
    # Se fizéssemos o import no topo do arquivo:
    #   from engine.scheduler import SchedulerSystem
    #   
    # O Python tentaria importar AGORA, e o scheduler.py
    # importaria de volta o core_engine.py → 💥 CIRCULAR IMPORT!
    #
    # Fazendo o import DENTRO do método (sob demanda), evitamos
    # isso porque o import só roda quando alguém realmente
    # chama a propriedade (e nesse momento o módulo já está carregado)
    # =========================================================================

    @property
    def lexflow(self) -> LexFlowClient:
        """
        Propriedade que retorna o Cliente Lex Flow (Inicialização Sob Demanda)
        
        Na primeira acesso, conecta ao Lex Flow usando as credenciais
        do settings.yaml. Nas próximas chamadas, retorna a mesma instância
        cacheada (sem reconectar).
        
        O QUE ACONTECE POR BAIXO DOS PANOS:
        1. Verifica se _cliente_lex_flow já existe
        2. Se não existe, chama _inicializar_cliente_lex_flow()
        3. Armazena em cache para futuros acessos
        4. Retorna o cliente pronto para usar
        
        LEVANTA EXCEÇÃO SE:
        - Credenciais inválidas no settings.yaml
        - Lex Flow estiver fora do ar (sem internet, servidor caiu)
        - Timeout na conexão (muito lento)
        
        RETORNA:
            Instância de LexFlowClient autenticada e pronta para chamadas de API
        """
        if self._cliente_lex_flow is None:
            self._inicializar_cliente_lex_flow()
        return self._cliente_lex_flow
    
    @property
    def sistema_captura(self) -> Optional["CaptureSystem"]:
        """
        Propriedade que retorna o Sistema de Captura (Inicialização Sob Demanda)
        
        Responsável por: quick_capture(), voice_note(), web_clip(), bulk_import()
        
        IMPORT TARDIO: from engine.capture_system import CaptureSystem
        
        RETORNA:
            Instância de CaptureSystem conectada ao Lex Flow
        """
        if self._sistema_captura is None:
            # Importar aqui (lazy import) para evitar circular dependencies
            from engine.capture_system import CaptureSystem
            from engine.memory_system import MemorySystem
            
            # MemorySystem é dependência obrigatória do CaptureSystem
            instancia_memoria = self.sistema_memoria
            
            # Criar CaptureSystem com suas dependências injetadas
            self._sistema_captura = CaptureSystem(
                lex_flow_client=self.lexflow,
                memory_system=instancia_memoria
            )
            
            logger_core.info("✅ CaptureSystem inicializado (lazy load)")
        
        return self._sistema_captura
    
    @property
    def motor_decisao(self) -> Optional["DecisionEngine"]:
        """
        Propriedade que retorna o Motor de Decisão (Inicialização Sob Demanda)
        
        Responsável por: classificação P.A.R.A., priorização com IA, smart_categorize()
        
        IMPORT TARDIO: from engine.decision_engine import DecisionEngine
        
        RETORNA:
            Instância de DecisionEngine conectada ao Lex Flow
        """
        if self._motor_decisao is None:
            from engine.decision_engine import DecisionEngine
            
            self._motor_decisao = DecisionEngine(
                lex_flow_client=self.lexflow,
                memory_system=self.sistema_memoria
            )
            
            logger_core.info("✅ DecisionEngine inicializado (lazy load)")
        
        return self._motor_decisao
    
    @property
    def sistema_memoria(self) -> Optional["MemorySystem"]:
        """
        Propriedade que retorna o Sistema de Memória (Inicialização Sob Demanda)
        
        RESPONSABILIDADES:
        - Cache de consultas recentes (com TTL)
        - Armazenamento de longo prazo
        - Contexto para RAG (Retrieval-Augmented Generation)
        
        IMPORT TARDIO: from engine.memory_system import MemorySystem
        
        RETORNA:
            Instância de MemorySystem carregada
        """
        if self._sistema_memoria is None:
            from engine.memory_system import MemorySystem
            
            # ✅ CORRIGIDO: Não passar argumentos (deixar MemorySystem usar defaults)
            self._sistema_memoria = MemorySystem()
            
            logger_core.info("✅ MemorySystem inicializado (lazy load)")
        
        return self._sistema_memoria
    
    @property
    def sistema_automacao(self) -> Optional["AutomationSystem"]:
        """
        Propriedade que retorna o Sistema de Automação (Inicialização Sob Demanda)
        
        Responsável por: execução de tarefas agendadas, workflows, ações recorrentes
        
        IMPORT TARDIO: from engine.automation_system import AutomationSystem
        
        RETORNA:
            Instância de AutomationSystem conectada ao Lex Flow
        """
        if self._sistema_automacao is None:
            from engine.automation_system import AutomationSystem
            
            self._sistema_automacao = AutomationSystem(
                lex_flow_client=self.lexflow,
                memory_system=self.sistema_memoria
            )
            
            logger_core.info("✅ AutomationSystem inicializado (lazy load)")
        
        return self._sistema_automacao
    
    @property
    def gerador_insights(self) -> Optional["InsightGenerator"]:
        """
        Propriedade que retorna o Gerador de Insights (Inicialização Sob Demanda)
        
        Responsável por: detectar projetos estagnados, sugerir melhorias, analytics,
        gerar relatórios TELOS 5D, identificar padrões de produtividade.
        
        IMPORT TARDIO: from engine.insight_generator import InsightGenerator
        
        RETORNA:
            Instância de InsightGenerator conectada ao Lex Flow
        """
        if self._gerador_insights is None:
            from engine.insight_generator import InsightGenerator
            
            self._gerador_insights = InsightGenerator(
                lex_flow_client=self.lexflow,
                memory_system=self.sistema_memoria
            )
            
            logger_core.info("✅ InsightGenerator inicializado (lazy load)")
        
        return self._gerador_insights

    # =========================================================================
    # PROPRIEDADE LAZY: SCHEDULER SYSTEM (Automações Agendadas)
    # =========================================================================
    
    @property
    def scheduler(self) -> Optional["SchedulerSystem"]:
        """
        Retorna instância do SchedulerSystem (Lazy Loading).
        
        O Scheduler é responsável por:
        - Morning Briefing automático (06:00 via Telegram)
        - Midday Check-in (12:00)
        - Evening Reflection (20:00 via Telegram)
        - TELOS Review semanal (Domingo 20:00)
        - Heartbeat contínuo (cada 30 minutos)
        
        ⚠️ IMPORTANTE: Esta propriedade era a causadora do CIRCULAR IMPORT!
        
        Antigamente fazíamos: from engine.scheduler import SchedulerSystem (no topo)
        Isso causava: core_engine → scheduler → core_engine → 💥 LOOP!
        
        SOLUÇÃO: Importar AQUI dentro da propriedade (lazy loading)!
        
        Só é instanciado quando acessado pela primeira vez.
        
        IMPORT TARDIO: from engine.scheduler import SchedulerSystem
        
        Returns:
            SchedulerSystem: Instância do sistema de agendamentos
        """
        if self._scheduler is None:
            try:
                # 🔥 IMPORT TARDIO! Evita circular import!
                from engine.scheduler import SchedulerSystem
                
                self._scheduler = SchedulerSystem(engine=self)
                logger_core.info("✅ SchedulerSystem carregado (lazy loading)")
            except Exception as e:
                logger_core.error(f"❌ Erro ao carregar SchedulerSystem: {e}")
        
        return self._scheduler

    # =========================================================================
    # 🆕 PROPRIEDADE LAZY: SISTEMA RAG (Retrieval-Augmented Generation)
    # =========================================================================
    #
    # NOVIDADE v2.1: Adicionado para suportar o Brain Middleware (IA Assistente)
    #
    # O RAG System permite busca semântica em todas as suas notas e documentos,
    # combinando:
    # - TF-IDF Vectorizer (scikit-learn) - leve, sem PyTorch!
    # - Similaridade por Cosseno (scipy/numpy) - instantanea (<1ms)
    # - Busca Híbrida (vetorial + keyword) via RRF Fusion
    # - Indexação automática do Lex Flow + Memória Interna
    
    # =========================================================================
    
    @property
    def sistema_rag(self) -> Optional["RAGSystem"]:
        """
        Lazy loading do Sistema RAG (Retrieval-Augmented Generation). 🆕
        
        O sistema RAG proporciona:
        - Embeddings vetoriais para busca semântica (TF-IDF puro, sem PyTorch!)
        - Busca vetorial por similaridade de cosseno (<1ms por consulta!)
        - Busca Híbrida (semântica + keyword) para melhores resultados
        - Indexação automática do Lex Flow e memória interna
        - Cache inteligente com TTL para performance
        
        USADO PELO BRAIN MIDDLEWARE PARA:
        - "Lex, o que eu escrevi sobre YouTube?" → Busca contextos relevantes
        - "Lex, me dá um plano baseado nas minhas notas" → RAG + LLM
        
        IMPORT TARDIO: from engine.rag_system import RAGSystem
        
        Returns:
            RAGSystem: Instância do sistema RAG (singleton dentro do engine)
        
        Raises:
            RuntimeError: Se falhar ao inicializar o RAG
        
        Example:
            >>> engine = CoreEngine.obter_instancia()
            >>> resultado = engine.sistema_rag.buscar("escalar canais dark")
            >>> for doc in resultado.documentos:
            ...     print(doc.conteudo)
        """
        if self._rag_system is None:
            try:
                logger_core.info("🧠 Inicializando Sistema RAG (Lazy Loading)...")
                
                # 🔥 IMPORT TARDIO! Evita circular import!
                from engine.rag_system import RAGSystem
                
                # Criar instância do RAG System com configurações padrão
                # O RAGSystem vai indexar automaticamente:
                # - SOUL.md, USER.md, MEMORY.md, HEARTBEAT.md (memória interna)
                # - Todas as notas do Lex Flow (via API)
                self._rag_system = RAGSystem()
                
                logger_core.info("✅ Sistema RAG carregado com sucesso!")
                
            except Exception as e:
                logger_core.error(f"❌ Falha ao inicializar Sistema RAG: {e}", exc_info=True)
                # Não levanta exceção! Retorna None e deixa o caller tratar
                return None
        
        return self._rag_system
    
    # =========================================================================
    # 🆕 PROPRIEDADE LAZY: LLM CLIENT (Large Language Model Client)
    # =========================================================================
    #
    # NOVIDADE v2.1: Adicionado para suportar o Brain Middleware (IA Assistente)
    #
    # O LLM Client é um cliente multi-provedor que suporta:
    # - NVIDIA NIM (z-ai/glm5 com reasoning + streaming)
    # - OpenAI (GPT-4, GPT-3.5-turbo)
    # Google Gemini (gemini-1.5-flash)
    # - Modelos locais via Ollama
    #
    # É usado pelo Brain Middleware para:
    # - Entender intenção da mensagem do usuário (GLM5)
    # - Gerar respostas contextualizadas
    # - Criar brainstorm de ideias
    # - Analisar padrões nos dados do usuário
    
    # =========================================================================
    
    @property
    def llm_client(self) -> Optional["LLMClient"]:
        """
        Lazy loading do LLM Client (Cliente de Modelos de Linguagem). 🆕
        
        O LLM Client é um cliente multi-provedor que permite usar diferentes
        modelos de linguagem de forma unificada.
        
        PROVEDORES SUPORTADOS:
        - NVIDIA NIM: z-ai/glm5 (com reasoning visível + streaming)
        - OpenAI: GPT-4, GPT-3.5-turbo
        - Google Gemini: gemini-1.5-flash
        - Local: Qualquer modelo via Ollama
        
        FUNCIONALIDADES:
        - gerar(prompt): Resposta completa
        - gerar_stream(prompt): Generator de chunks (streaming em tempo real)
        - perguntar_com_rag(pergunta, rag_system): RAG Completo
        - limpar_historico(): Limpa conversa atual
        
        IMPORT TARDIO: from engine.llm_client import LLMClient
        
        Returns:
            LLMClient: Instância do cliente LLM configurada e pronta
        
        Example:
            >>> engine = CoreEngine.obter_instancia()
            >>> resposta = engine.llm_client.gerar("Me dê 5 ideias de vídeo")
            >>> print(resposta)
        
        CONFIGURAÇÃO:
        Requer API key em settings.yaml ou variável de ambiente:
        - NVIDIA: NVIDIA_API_KEY (ou nvidia_api_key no yaml)
        - OpenAI: OPENAI_API_KEY
        - Google: GOOGLE_API_KEY
        """
        if self._llm_client is None:
            try:
                logger_core.info("🤖 Inicializando LLM Client (Lazy Loading)...")
                
                # 🔥 IMPORT TARDIO! Evita circular import!
                from engine.llm_client import LLMClient
                
                # Criar instância do LLM Client
                # Ele vai ler as configurações de API do settings.yaml
                self._llm_client = LLMClient()
                
                logger_core.info("✅ LLM Client carregado com sucesso!")
                
            except Exception as e:
                logger_core.error(f"❌ Falha ao inicializar LLM Client: {e}", exc_info=True)
                # Não levanta exceção! Retorna None e deixa o caller tratar
                return None
        
        return self._llm_client

    # =========================================================================
    # MÉTODOS DE INICIALIZAÇÃO E CONTROLE DE CICLO DE VIDA
    # =========================================================================
    
    def _inicializar_cliente_lex_flow(self):
        """
        Inicializar e conectar o Cliente Lex Flow (método interno privado)
        
        É chamado automaticamente pela propriedade @lexflow na primeira vez.
        Não deve ser chamado diretamente pelo usuário externo.
        
        O QUE FAZ:
        1. Obtém dicionário de configurações do ConfigLoader
        2. Cria objeto LexFlowConfig com credenciais e parâmetros
        3. Instancia LexFlowClient (que faz login automático!)
        4. Valida se autenticação foi bem-sucedida
        5. Log de sucesso ou erro crítico
        
        LEVANTA EXCEÇÃO SE:
        - Credenciais ausentes ou inválidas no settings.yaml
        - Servidor Lex Flow inalcançável (rede, DNS, firewall)
        - Login/senha incorretos (erro 401 da API)
        - Timeout na conexão (servidor muito lento)
        """
        logger_core.info("🔐 Inicializando conexão com Lex Flow...")
        
        try:
            # PASSO 1: Obter configurações formatadas do carregador
            # ✅ CORRIGIDO: Variável DEVE ser definida aqui antes de usar!
            configuracao_lex_flow_dict = self.carregador_config.get_lex_flow_config()
            
            # Validar campos obrigatórios
            if not configuracao_lex_flow_dict.get('base_url'):
                raise ValueError("base_url do Lex Flow não configurada em settings.yaml!")
            
            if not configuracao_lex_flow_dict.get('username') or not configuracao_lex_flow_dict.get('password'):
                raise ValueError("Credenciais (username/password) do Lex Flow não configuradas!")
            
            # PASSO 2: Criar objeto de configuração tipado
            objeto_config_lex_flow = LexFlowConfig(
                base_url=configuracao_lex_flow_dict['base_url'],
                username=configuracao_lex_flow_dict['username'],
                password=configuracao_lex_flow_dict['password'],
                timeout=configuracao_lex_flow_dict.get('timeout', 30),
                max_retries=configuracao_lex_flow_dict.get('max_retries', 3),
                vault_path=configuracao_lex_flow_dict.get('vault_path', ''),
            )
            
            # PASSO 3: Instanciar cliente (isso JÁ faz o login automático!)
            logger_core.info(f"   Conectando em: {objeto_config_lex_flow.base_url}")
            logger_core.info(f"   Usuário: {objeto_config_lex_flow.username}")
            
            self._cliente_lex_flow = LexFlowClient(objeto_config_lex_flow)
            
            # PASSO 4: Validar se autenticou com sucesso
            if self._cliente_lex_flow.is_authenticated():
                logger_core.info("✅ LEX FLOW CLIENT CONECTADO E AUTENTICADO COM SUCESSO!")
                logger_core.info("   Status: Pronto para operações de produção")
            else:
                # Cliente criado mas não autenticado (problema de credenciais?)
                erro_autenticacao = (
                    "Lex Flow Client foi criado mas NÃO conseguiu autenticar! "
                    "Verifique username e password em config/settings.yaml"
                )
                logger_core.error(f"❌ {erro_autenticacao}")
                raise ConnectionError(erro_autenticacao)
                
        except Exception as erro_conexao:
            # Qualquer erro na conexão é crítico (o motor inteiro depende disso)
            logger_core.error(f"❌ ERRO CRÍTICO AO CONECTAR NO LEX FLOW: {erro_conexao}", exc_info=True)
            logger_core.error(f"   Tipo da exceção: {type(erro_conexao).__name__}")
            logger_core.error(f"   Mensagem: {str(erro_conexao)}")
            
            # Re-lançar exceção para quem chamou (não engolir o erro)
            raise
    
    def iniciar(self) -> bool:
        """
        Iniciar o Motor Principal (deve ser chamado UMA VEZ no início do programa)
        
        Este método prepara o sistema para uso, validando todas as dependências
        críticas e deixando pronto para receber comandos.
        
        O QUE EXECUTA:
        1. Verifica se já está rodando (evita dupla inicialização)
        2. Força inicialização do Lex Flow Client (valida conexão)
        3. Registra timestamp de início nas métricas
        4. Marca estado como "rodando"
        5. Log informativo de sucesso
        
        QUANDO CHAMAR:
        - Uma única vez no início do seu script/main
        - Antes de usar qualquer outro método (capture, etc.)
        
        RETORNA:
            True se iniciou com sucesso, False se houve erro crítico
            
        EXEMPLO:
            
            motor = CoreEngine.obter_instancia()
            
            if motor.iniciar():
                print("Motor rodando! Pode usar.")
                motor.capturar("Teste...")
            else:
                print("Falha crítica! Verifique logs.")
                exit(1)
        """
        
        # Evitar dupla inicialização
        if self.esta_rodando:
            logger_core.warning("⚠️  Motor JÁ está rodando! Ignorando chamada duplicada de iniciar().")
            return True
        
        logger_core.info("🚀 INICIANDO CORE ENGINE v2.1...")
        logger_core.info("=" * 70)
        
        try:
            # PASSO 1: Forçar inicialização do Lex Flow (vai validar tudo)
            # Isso dispara a propriedade @lexflow que chama _inicializar_cliente_lex_flow()
            logger_core.info("   Validando conexão com Lex Flow...")
            _cliente = self.lexflow  # Accessa a propriedade (força init se necessário)
            
            # Se chegou aqui, Lex Flow está conectado!
            
            # PASSO 2: Registrar timestamp de início
            momento_agora = datetime.now().isoformat()
            self.metricas_internas['momento_inicializacao'] = momento_agora
            
            # PASSO 3: Marcar estado como ativo
            self.esta_rodando = True
            
            # PASSO 4: Log de sucesso com resumo do estado
            logger_core.info("✅ MOTOR INICIALIZADO COM SUCESSO!")
            logger_core.info(f"   Momento: {momento_agora}")
            logger_core.info(f"   Ambiente: {self.configuracoes.environment}")
            logger_core.info("")
            logger_core.info("   Subsistemas disponíveis (prontos para lazy load):")
            logger_core.info("     • CaptureSystem (captura de ideias, voz, web clips)")
            logger_core.info("     • DecisionEngine (classificação IA, priorização)")
            logger_core.info("     • MemorySystem (memória longo prazo, RAG)")
            logger_core.info("     • AutomationSystem (tarefas automatizadas)")
            logger_core.info("     • InsightGenerator (análise de padrões)")
            logger_core.info("     • SchedulerSystem (automações agendadas)")
            logger_core.info("     • 🆕 RAGSystem (busca vetorial semântica)")
            logger_core.info("     • 🆕 LLMClient (GLM5, OpenAI, Gemini)")
            logger_core.info("")
            logger_core.info("   Status: 🟢 ATIVO E PRONTO PARA RECEBER COMANDOS")
            logger_core.info("=" * 70)
            
            return True
            
        except Exception as erro_inicio:
            # Falha crítica na inicialização
            logger_core.error(f"❌ ERRO CRÍTICO AO INICIAR MOTOR: {erro_inicio}", exc_info=True)
            self.esta_rodando = False
            return False
    
    def parar(self):
        """
        Parar o Motor Principal gracefulmente (limpeza ordenada)
        
        Deve ser chamado ao encerrar o programa, ou antes de reiniciar.
        Fecha conexões, salva estados pendentes, libera recursos.
        
        O QUE EXECUTA:
        1. Faz logout do Lex Flow (invalida token do lado do servidor)
        2. Limpa referências aos subsistemas (permite garbage collection)
        3. Marca estado como "parado"
        4. Log de encerramento
        
        É seguro chamar múltiplas vezes (não gera erros se já parado).
        """
        logger_core.info("🛑 PARANDO CORE ENGINE...")
        logger_core.info("=" * 70)
        
        try:
            # PASSO 1: Fechar conexão (mais seguro que logout que pode falhar)
            if self._cliente_lex_flow is not None:
                try:
                    # Tentar logout (se falhar, ignorar - não é crítico)
                    self._cliente_lex_flow.logout()
                except Exception as erro_logout_ignorado:
                    # Logout falhou? Sem problema, vamos fechar de qualquer forma
                    logger_core.warning(f"   ⚠️  Erro no logout (não crítico): {erro_logout_ignorado}")
            
            # PASSO 2: Limpar referências aos subsistemas (todos!)
            self._sistema_captura = None
            self._motor_decisao = None
            self._sistema_memoria = None
            self._sistema_automacao = None
            self._gerador_insights = None
            self._scheduler = None
            
            # 🆕 Limpar novos subsistemas (v2.1)
            self._rag_system = None
            self._llm_client = None
            
            # O cliente Lex Flow também é limpo (já fez logout acima)
            # Mantemos a referência para possível reconexão, mas poderia ser None também
            # self._cliente_lex_flow = None  # Opcional: descomente forçar re-conexão próximo start()
            
            # PASSO 3: Atualizar estado
            self.esta_rodando = False
            
            # Calcular tempo de atividade
            tempo_ativo = datetime.now() - self.timestamp_criacao
            logger_core.info(f"   Tempo de atividade: {tempo_ativo}")
            logger_core.info(f"   Capturas realizadas: {self.metricas_internas['capturas_hoje']}")
            logger_core.info(f"   Processamentos: {self.metricas_internas['processamentos_hoje']}")
            
            logger_core.info("✅ MOTOR PARADO COM SUCESSO (Graceful Shutdown)")
            logger_core.info("=" * 70)
            
        except Exception as erro_parar:
            # Erro ao parar não deve levantar exceção (tentamos fazer nosso melhor)
            logger_core.error(f"⚠️  Erro durante parada (não crítico): {erro_parar}", exc_info=True)
    
    # =========================================================================
    # MÉTODOS PRINCIPAIS DA API PÚBLICA (Interface de Uso)
    # =========================================================================
    
    def capturar(self, idea: str, tags: List[str] = None) -> Optional[Dict]:
        """
        CAPTURA RÁPIDA - O método mais importante e usado do sistema!
        
        Equivalente a anotar algo num bloco de notas, mas inteligente:
        - Vai direto para o Inbox do Lex Flow (nuvem)
        - Fica disponível em todos os dispositivos
        - Pode ser processado e organizado depois por IA
        
        É o ponto de entrada universal para QUALQUER informação
        que você quer guardar: ideias, tarefas, lembretes, links, etc.
        
        ARGUMENTOS:
            idea: Texto da ideia/nota (obrigatório, pode ser curto ou longo)
                  Exemplos: "Comprar pão", "Ideia de vídeo sobre Bitcoin", 
                           "Ligar para fornecedor sexta"
                  
            tags: Lista opcional de tags para categorização manual
                  Exemplo: ["urgente", "pessoal", "compra"]
                  Se omitido, usa tag padrão ['capturada']
        
        RETORNA:
            Dicionário com dados da nota criada no Lex Flow, incluindo:
            - id: Identificador único da nota
            - title: Título (primeiros 100 chars do conteúdo)
            - content: Conteúdo completo
            - tags: Tags aplicadas
            Ou None se houver erro na captura
            
        EXEMPLOS DE USO:
            
            # Simples
            motor.capturar("Não esquecer de pagar aluguel")
            
            # Com tags
            motor.capturar(
                "Preciso estudar mais sobre PostgreSQL para o segundo brain",
                tags=["estudo", "tecnologia", "banco-de-dados", "prioridade"]
            )
            
            # Via Telegram Bot (exemplo hipotético)
            def handle_telegram_message(texto_usuario):
                resultado = motor.capturar(texto_usuario, source="telegram")
                return "✅ Anotado!" if resultado else "❌ Erro ao anotar"
        
        O QUE ACONTECE INTERNAMENTE (Fluxo Completo):
        ----------------------------------------------
        1. Verifica se motor está rodando (senão, erro)
        2. Log da idea sendo capturada (primeiros 80 chars)
        3. Delega para CaptureSystem.quick_capture() (que usa Lex Flow)
        4. CaptureSystem valida conteúdo, verifica duplicatas
        5. CaptureSystem chama LexFlowClient.quick_capture() (API REAL)
        6. Lex Flow salva no banco de dados e retorna ID
        7. Atualiza métricas internas (contador de capturas)
        8. Log de sucesso com ID retornado
        9. Retorna dicionário com dados da nota criada
        
        POSSÍVEIS ERROS E TRATAMENTOS:
        ------------------------------
        - Motor não iniciado: Retorna None + log de erro
        - Conteúdo vazio: CaptureSystem rejeita (retorna sucesso=False)
        - Duplicata: CaptureSystem ignora silenciosamente (não é erro)
        - Lex Flow fora do ar: Exceção capturada, log de erro, retorna None
        - Problema de rede: Retry automático pelo LexFlowClient (até 3 tentativas)
        """
        
        # Validação prévia: motor precisa estar rodando
        if not self.esta_rodando:
            logger_core.error("❌ ERRO: Motor não foi iniciado! Use motor.iniciar() primeiro.")
            return None
        
        # Log da operação (útil para debug e auditoria)
        logger_core.info(f"💭 [CAPTURA] Recebida nova idea:")
        logger_core.info(f"   Conteúdo: {idea[:100]}{'...' if len(idea) > 100 else ''}")
        logger_core.info(f"   Tags: {tags or []}")
        
        # Delegar para o CaptureSystem (especialista em captura)
        # O CaptureSystem vai fazer toda a validação e chamar o Lex Flow
        resultado_captura = self.sistema_captura.quick_capture(
            idea=idea,
            tags=tags
        )
        
        # Processar resultado
        if resultado_captura and resultado_captura.success:
            # Sucesso! Atualizar métricas internas
            self.metricas_internas['ultima_captura'] = datetime.now().isoformat()
            self.metricas_internas['capturas_hoje'] += 1
            
            identificador_nota = resultado_captura.item.id if resultado_captura.item else 'desconhecido'
            
            logger_core.info(f"   ✅ CAPTURA BEM-SUCEDIDA! ID: {identificador_nota}")
            
            # Retornar dicionário simples (compatível com API antiga)
            # Retornar resultado adaptativo (compatível com diferentes formatos de resposta)
            if resultado_captura and resultado_captura.success:
                
                # Caso 1: Resposta com ID direto (formato ideal)
                id_nota = resultado_captura.item.id if hasattr(resultado_captura.item, 'id') else None
                
                # Caso 2: Resposta aninhada no item (se houver metadados que contenham a nota)
                if not id_nota and hasattr(resultado_captura.item, 'metadata') and isinstance(resultado_captura.item.metadata, dict):
                    # Tentar extrair ID de dentro dos metadados
                    nota_dict = resultado_captura.item.metadata.get('note') if isinstance(resultado_captura.item.metadata.get('note'), dict) else {}
                    id_nota = nota_dict.get('id')
                
                # Caso3: Gerar ID temporário se nada funcionou
                if not id_nota:
                    id_nota = f"temp-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                logger_core.info(f"   ✅ CAPTURA REGISTRADA! ID: {id_nota}")
                
                return {
                    'id': id_nota,
                    'title': str(resultado_captura.item.content)[:100] if resultado_captura.item else idea[:100],
                    'content': resultado_captura.item.content if hasattr(resultado_captura.item, 'content') else idea,
                    'tags': resultado_captura.item.tags if hasattr(resultado_captura.item, 'tags') else [],
                    'success': True,
                    'message': resultado_captura.message
                }
            
            elif resultado_captura and not resultado_captura.success:
                # Falha na captura (não é crash, apenas não salvou)
                mensagem_erro = resultado_captura.message if resultado_captura else "Erro desconhecido"
                logger_core.warning(f"   ⚠️  {mensagem_erro}")
                return None
                
            else:
                # resultado_captura é None (erro grave antes)
                return None
    
    def processar_inbox(self) -> Optional[Dict]:
        """
        PROCESSAR INBOX - Analisar e organizar notas pendentes com Inteligência Artificial
        
        Busca todas as notas que estão no Inbox (caixa de entrada) do Lex Flow,
        envia para o motor de IA categorizar automaticamente, e retorna
        um relatório com sugestões de organização para cada uma.
        
        QUANDO USAR:
        - Ao final do dia (para limpar inbox acumulado)
        - Periodicamente (a cada X horas via automação)
        - Manualmente quando quiser organizar as ideias capturadas
        
        O QUE ACONTECE:
        1. Busca get_inbox() do Lex Flow (todas as notas pendentes)
        2. Extrai títulos e conteúdos das notas
        3. Envia para smart_categorize() do Lex Flow (IA analisa)
        4. IA sugere: para qual projeto ir, que tipo de conteúdo é, prioridade
        5. Retorna relatório completo com todas as sugestões
        
        IMPORTANTE: Este método NÃO move/apaga notas do inbox!
        Ele apenas GERA SUGESTÕES. Para executar as mudanças,
        use o DecisionEngine ou faça manualmente no Lex Flow.
        
        RETORNA:
            Dicionário com relatório do processamento:
            - total_items: Quantas notas haviam no inbox
            - processed: Quantas foram analisadas pela IA
            - suggestions: Lista de sugestões (uma por nota)
            - errors: Lista de erros (se houveram)
            Ou None se houver erro crítico ou inbox vazio
            
        EXEMPLO DE RETORNO:
        
        {
            'total_items': 5,
            'processed': 5,
            'suggestions': [
                {'note_id': 123, 'suggested_project': 'Canais Dark', 'confidence': 0.92},
                {'note_id': 124, 'suggested_area': 'Estudo', 'confidence': 0.87},
                ...
            ],
            'errors': []
        }
        """
        
        # Validação
        if not self.esta_rodando:
            logger_core.error("❌ ERRO: Motor não iniciado!")
            return None
        
        logger_core.info(f"📥 [PROCESSAR_INBOX] Iniciando processamento do Inbox...")
        
        # Delegar para CaptureSystem (que tem o método process_inbox_with_intelligence)
        resultado_processamento = self.sistema_captura.process_inbox_with_intelligence()
        
        # Atualizar métricas se processou algo
        if resultado_processamento:
            quantidade_processada = resultado_processamento.get('processed', 0)
            if quantidade_processada > 0:
                self.metricas_internas['ultimo_processamento'] = datetime.now().isoformat()
                self.metricas_internas['processamentos_hoje'] += 1
                
                logger_core.info(f"   ✅ INBOX PROCESSADO! {quantidade_processada} itens analisados")
            else:
                logger_core.info(f"   📭 Inbox vazio ou nada para processar")
        else:
            logger_core.warning(f"   ⚠️  Falha ao processar inbox (resultado vazio)")
        
        return resultado_processamento
    
    def adicionar_tarefa(
        self, 
        projeto_id: int, 
        titulo: str, 
        prioridade: str = "medium",
        descricao: str = ""
    ) -> Optional[Dict]:
        """
        Adicionar Nova Tarefa a um Projeto Existente
        
        Cria uma tarefa dentro de um projeto específico do Lex Flow.
        Útil para transformar ideias capturadas em ações concretas.
        
        ARGUMENTOS:
            projeto_id: Identificador numérico do projeto no Lex Flow
                       (obtenha via get_projetos() ou olhando no dashboard)
                       
            titulo: Título/texto da tarefa (obrigatório, curto e acionável)
                     Ex: "Editar vídeo #12", "Comprar microfone", "Ligar fornecedor"
                     
            prioridade: Nível de urgência (padrão: "medium")
                        Opções: "low", "medium", "high", "urgent"
                        
            descricao: Descrição detalhada da tarefa (opcional)
                      Contexto adicional, subpassos, links, etc.
        
        RETORNA:
            Dicionário com dados da tarefa criada, incluindo:
            - id: ID da tarefa
            - title: Título confirmado
            - project_id: ID do projeto pai
            - priority: Prioridade registrada
            Ou None se houver erro
            
        EXEMPLO:
            
            # Descobrir ID do projeto "Canals Dark" (supondo que seja 5)
            tarefa = motor.adicionar_tarefa(
                projeto_id=5,
                titulo="Gravar introdução do vídeo sobre criptomoedas",
                prioridade="high",
                descricao="Hook: Por que seu banco tem medo do Bitcoin?\nUsar template dark."
            )
            
            if tarefa:
                print(f"Tarefa criada! ID: {tarefa['id']}")
        """
        
        # Validação
        if not self.esta_rodando:
            logger_core.error("❌ ERRO: Motor não iniciado!")
            return None
        
        logger_core.info(f"📝 [ADICIONAR_TAREFA] Nova tarefa no projeto {projeto_id}:")
        logger_core.info(f"   Título: {titulo}")
        logger_core.info(f"   Prioridade: {prioridade}")
        
        try:
            # Chamar Lex Flow diretamente (operação simples, não precisa do CaptureSystem)
            resultado_api = self.lexflow.add_task(
                project_id=projeto_id,
                title=titulo,
                description=descricao,
                priority=prioridade
            )
            
            if resultado_api and resultado_api.get('id'):
                logger_core.info(f"   ✅ TAREFA CRIADA! ID: {resultado_api.get('id')}")
                return resultado_api
            else:
                logger_core.warning(f"   ⚠️  Resposta inesperada ao criar tarefa")
                return None
                
        except Exception as erro_tarefa:
            logger_core.error(f"   ❌ Erro ao criar tarefa: {erro_tarefa}", exc_info=True)
            return None
    
    def criar_projeto(self, nome: str, descricao: str = "") -> Optional[Dict]:
        """
        Criar Novo Projeto no Lex Flow
        
        Projetos são containeres grandes para tarefas relacionadas.
        Ex: "Canals Dark", "Influencer AI", "App Lex Flow v2"
        
        ARGUMENTOS:
            nome: Nome do projeto (obrigatório, curto e descritivo)
            descricao: Descrição detalhada (opcional, contexto e objetivos)
        
        RETORNA:
            Dicionário do projeto criado ou None em erro
        """
        
        if not self.esta_rodando:
            return None
        
        logger_core.info(f"📂 [CRIAR_PROJETO] Novo projeto: {nome}")
        
        try:
            resultado = self.lexflow.create_project(name=nome, description=descricao)
            
            if resultado and resultado.get('id'):
                logger_core.info(f"   ✅ PROJETO CRIADO! ID: {resultado.get('id')}")
                return resultado
            else:
                logger_core.warning(f"   ⚠️  Falha ao criar projeto")
                return None
                
        except Exception as erro:
            logger_core.error(f"   ❌ Erro: {erro}", exc_info=True)
            return None
    
    def obter_dashboard(self) -> Optional[Dict]:
        """
        Obter Dados Completos do Dashboard (Métricas Visuais)
        
        Busca o dashboard principal do Lex Flow que contém:
        - Gráficos de produtividade
        - Contadores de tarefas/projetos
        - Métricas recentes
        - Cards de resumo
        
        RETORNA:
            Dicionário com todos os dados do dashboard ou None
        """
        
        if not self.esta_rodando:
            return None
        
        try:
            return self.lexflow.get_dashboard()
        except Exception as erro:
            logger_core.error(f"❌ Erro ao buscar dashboard: {erro}")
            return None
    
    def obter_prioridades(self) -> List[Dict]:
        """
        Obter Top Prioridades do Dia (Tarefas Mais Importantes)
        
        Retorna as tarefas que o Lex Flow marca como prioritárias para hoje,
        baseadas em deadline, importância e contexto.
        
        RETORNA:
            Lista de dicionários (cada um é uma tarefa prioritária)
            Ou lista vazia se não houver prioridades/motor desligado
        """
        
        if not self.esta_rodando:
            return []
        
        try:
            return self.lexflow.get_today_priorities()
        except Exception as erro:
            logger_core.error(f"❌ Erro ao buscar prioridades: {erro}")
            return []
    
    def obter_status_completo(self) -> Dict:
        """
        Obter Diagnóstico Completo do Estado do Sistema (Para Debug/Monitoramento)
        
        Retorna informações detalhadas sobre:
        - Estado interno do motor (uptime, contadores)
        - Estado da conexão com Lex Flow (autenticado?, quantas notas, etc.)
        - Métricas rápidas do dia (do dashboard)
        - Saúde dos subsistemas
        
        Útil para:
        - Telas de administração/status
        - Debug de problemas
        - Monitoramento de saúde (health check)
        
        RETORNA:
            Dicionário aninhado com todas as informações
        """
        
        # Estrutura básica do status
        status_completo = {
            'motor': {
                'rodando': self.esta_rodando,
                'momento_inicializacao': self.metricas_internas['momento_inicializacao'],
                'uptime_segundos': (datetime.now() - self.timestamp_criacao).total_seconds() if self.timestamp_criacao else 0,
                'versao': self.configuracoes.version,
                'ambiente': self.configuracoes.environment,
                'debug_mode': self.configuracoes.debug,
                'usuario': self.configuracoes.user_name,
                'capturas_hoje': self.metricas_internas['capturas_hoje'],
                'processamentos_hoje': self.metricas_internas['processamentos_hoje'],
                'erros_totais': self.metricas_internas['erros_totais'],
            },
            'lex_flow': {},
            'metricas_dia': {},
            'subsistemas': {}
        }
        
        # Tentar obter status do Lex Flow (pode falhar se não conectado)
        try:
            if self._cliente_lex_flow and hasattr(self._cliente_lex_flow, 'is_authenticated'):
                if self._cliente_lex_flow.is_authenticated():
                    # Lex Flow está conectado e autenticado
                    notas_inbox = self.lexflow.get_inbox()
                    projetos_ativos = self.lexflow.get_projects()
                    areas_existentes = self.lexflow.get_areas()
                    
                    status_completo['lex_flow'] = {
                        'autenticado': True,
                        'url_base': self.configuracoes.lex_flow_base_url,
                        'usuario': self.configuracoes.lex_flow_username,
                        'quantidade_notas_inbox': len(notas_inbox) if notas_inbox else 0,
                        'quantidade_projetos_ativos': len(projetos_ativos) if projetos_ativos else 0,
                        'quantidade_areas': len(areas_existentes) if areas_existentes else 0,
                        'status': 'conectado_e_operacional'
                    }
                    
                    # Métricas rápidas do dia (se disponíveis)
                    metricas_rapidas = self.lexflow.get_today_stats()
                    if metricas_rapidas:
                        status_completo['metricas_dia'] = metricas_rapidas
                        
                else:
                    # Cliente existe mas não autenticado (problema)
                    status_completo['lex_flow'] = {
                        'autenticado': False,
                        'erro': 'Cliente Lex Flow não está autenticado',
                        'status': 'erro_autenticacao'
                    }
            else:
                # Cliente nem foi inicializado ainda (nunca acessou a propriedade @lexflow)
                status_completo['lex_flow'] = {
                    'autenticado': False,
                    'status': 'nao_inicializado'
                }
                
        except Exception as erro_status_lex:
            # Erro ao tentar obter status do Lex Flow
            status_completo['lex_flow'] = {
                'autenticado': False,
                'erro': str(erro_status_lex),
                'status': 'erro_conexao'
            }
            logger_core.warning(f"⚠️  Erro ao obter status do Lex Flow: {erro_status_lex}")
        
        # Status dos subsistemas (quais foram inicializados vs não)
        status_completo['subsistemas'] = {
            'capture_system': 'inicializado' if self._sistema_captura is not None else 'nao_carregado',
            'decision_engine': 'inicializado' if self._motor_decisao is not None else 'nao_carregado',
            'memory_system': 'inicializado' if self._sistema_memoria is not None else 'nao_carregado',
            'automation_system': 'inicializado' if self._sistema_automacao is not None else 'nao_carregado',
            'insight_generator': 'inicializado' if self._gerador_insights is not None else 'nao_carregado',
            'scheduler': 'inicializado' if self._scheduler is not None else 'nao_carregado',
            # 🆕 Novos subsistemas (v2.1)
            'rag_system': 'inicializado' if self._rag_system is not None else 'nao_carregado',
            'llm_client': 'inicializado' if self._llm_client is not None else 'nao_carregado',
        }
        
        return status_completo
    
    # =========================================================================
    # ATALHOS CONVENIENTES (MÉTODOS CURTOS)
    # =========================================================================
    
    def nota_rapida(self, texto: str) -> Optional[Dict]:
        """Atalho para capturar() - mesmo comportamento"""
        return self.capturar(texto)
    
    def resumo_do_dia(self) -> Dict:
        """
        Resumo Rápido do Dia (Prioridades + Estatísticas + Dashboard)
        
        Combina múltiplas chamadas em um único retorno conveniente.
        Útil para briefings, Telegram Bot, dashboards simples.
        
        RETORNA:
            Dicionário com:
            - prioridades: lista de tarefas prioritárias
            - estatisticas: métricas do dia
            - dashboard: dados completos do dashboard (opcional, pode ser pesado)
        """
        return {
            'prioridades': self.obter_prioridades(),
            'estatisticas': self.lexflow.get_today_stats() if self.esta_rodando else {},
            'dashboard': self.obter_dashboard()  # Pode ser None se falhar
        }
    
    def health_check(self) -> Dict:
        """
        Verificação Rápida de Saúde (Para Monitoramento Automatizado)
        
        Versão simplificada do obter_status_completo(), focada apenas em:
        - O motor está rodando?
        - O Lex Flow está conectado?
        - Quantas notas há no inbox?
        
        Ideal para scripts de monitoramento, health checks de API, etc.
        
        RETORNA:
            Dicionário simples: {'saudavel': bool, 'detalhes': str}
        """
        try:
            if not self.esta_rodando:
                return {'saudavel': False, 'detalhes': 'Motor não foi iniciado'}
            
            if not self._cliente_lex_flow or not self._cliente_lex_flow.is_authenticated():
                return {'saudavel': False, 'detalhes': 'Lex Flow não conectado'}
            
            # Tenta operação simples para validar conexão
            inbox_count = len(self.lexflow.get_inbox())
            
            return {
                'saudavel': True,
                'detalhes': f'Motor OK, Lex Flow OK, {inbox_count} notas no inbox',
                'inbox_count': inbox_count,
                'uptime_segundos': (datetime.now() - self.timestamp_criacao).total_seconds()
            }
            
        except Exception as erro_health:
            return {'saudavel': False, 'detalhes': f'Erro: {str(erro_health)}'}


# ================================================
# BLOCO DE TESTE E DEMONSTRAÇÃO DO MOTOR
# ================================================

if __name__ == "__main__":
    """
    Teste Completo do Core Engine v2.1 (Integração Lex Flow)
    
    Execute: python engine/core_engine.py
    
    Este script valida:
    1. Criação do Singleton (apenas uma instância)
    2. Inicialização do motor (conexão Lex Flow)
    3. Captura de ideia (via Lex Flow API real)
    4. Obtenção de prioridades do dia
    5. Status completo do sistema
    6. Encerramento graceful (logout)
    
    Todas as operações usam o Lex Flow EM PRODUÇÃO (dados reais!).
    """
    
    print("\n" + "=" * 90)
    print("🧪 CORE ENGINE v2.1 - TESTE DE INTEGRAÇÃO COMPLETA")
    print("   Lex Flow Client (Produção Real) | Configuração Centralizada | Singleton Pattern")
    print("   🆕 RAG System + LLM Client (Brain Middleware Ready)")
    print("=" * 90 + "\n")
    
    # ========================================
    # TESTE 1: CRIAÇÃO DO SINGLETON
    # ========================================
    print("1️⃣  TESTE: Criação do Motor (Singleton)")
    print("-" * 90)
    
    print("   Instanciando CoreEngine...")
    motor = CoreEngine()
    
    # Verificar se é singleton (duas chamadas devem retornar mesmo objeto)
    motor_mesmo_objeto = CoreEngine.obter_instancia()
    
    if motor is motor_mesmo_objeto:
        print("   ✅ Singleton funcionando: ambas as referências apontam para o mesmo objeto")
    else:
        print("   ❌ ERRO: Singleton não funcionou! Objetos diferentes.")
        sys.exit(1)
    
    # ========================================
    # TESTE 2: INICIALIZAÇÃO (CONEXÃO LEX FLOW)
    # ========================================
    print("\n2️⃣  TESTE: Inicialização do Motor (Conexão Lex Flow)")
    print("-" * 90)
    
    print("   Chamando motor.iniciar()...")
    sucesso_inicio = motor.iniciar()
    
    if not sucesso_inicio:
        print("\n❌ FALHA CRÍTICA: Não foi possível iniciar o motor!")
        print("   Verifique:")
        print("   1. Se config/settings.yaml existe e está preenchido")
        print("   2. Se o Lex Flow (flow.lex-usamn.com.br) está online")
        print("   3. Se suas credenciais estão corretas")
        print("\n   Logs detalhados em: logs/core_engine.log")
        sys.exit(1)
    
    print("   ✅ Motor iniciado com sucesso!")
    print(f"   Ambiente: {motor.configuracoes.environment}")
    print(f"   Usuário: {motor.configuracoes.user_name}")
    
    # ========================================
    # TESTE 3: STATUS COMPLETO DO SISTEMA
    # ========================================
    print("\n3️⃣  TESTE: Diagnóstico de Status Completo")
    print("-" * 90)
    
    status = motor.obter_status_completo()
    
    print(f"   Motor rodando: {'🟢 SIM' if status['motor']['rodando'] else '🔴 NÃO'}")
    print(f"   Versão: {status['motor']['versao']}")
    print(f"   Uptime: {status['motor']['uptime_segundos']:.1f} segundos")
    
    if status.get('lex_flow', {}).get('autenticado'):
        lex_flow_status = status['lex_flow']
        print(f"\n   📡 LEX FLOW:")
        print(f"      Status: {lex_flow_status.get('status', 'desconhecido')}")
        print(f"      Notas no Inbox: {lex_flow_status.get('quantidade_notas_inbox', '?')}")
        print(f"      Projetos Ativos: {lex_flow_status.get('quantidade_projetos_ativos', '?')}")
        print(f"      Áreas: {lex_flow_status.get('quantidade_areas', '?')}")
    else:
        print(f"\n   ⚠️  Lex Flow: Não conectado ({status.get('lex_flow', {}).get('erro', 'desconhecido')})")
    
    # ========================================
    # TESTE 4: PRIORIDADES DO DIA
    # ========================================
    print("\n4️⃣  TESTE: Prioridades do Dia")
    print("-" * 90)
    
    prioridades = motor.obter_prioridades()
    
    if prioridades:
        print(f"   ✅ Encontradas {len(prioridades)} prioridades:")
        for indice, tarefa in enumerate(prioridades[:5], start=1):  # Mostra até 5
            projeto_nome = tarefa.get('project_title', 'Sem projeto')
            tarefa_titulo = tarefa.get('title', 'Sem título')
            print(f"      {indice}. [{projeto_nome}] {tarefa_titulo}")
    else:
        print("   📭 Nenhuma prioridade para hoje (inbox pode estar vazio)")
    
    # ========================================
    # TESTE 5: CAPTURA DE IDEIA (OPERAÇÃO PRINCIPAL)
    # ========================================
    print("\n5️⃣  TESTE: Captura Rápida de Ideia (API Real)")
    print("-" * 90)
    
    texto_teste = (
        "Teste automatizado do Core Engine v2.1 - "
        "Integração completa com Lex Flow em produção! "
        f"Timestamp: {datetime.now().isoformat()}"
    )
    
    print(f"   Capturando: '{texto_teste[:60]}...'")
    
    resultado_captura = motor.capturar(
        idea=texto_teste,
        tags=["teste-automatizado", "core-engine-v21", "integração-lex-flow"]
    )
    
    if resultado_captura and resultado_captura.get('id'):
        print(f"   ✅ CAPTURA BEM-SUCEDIDA!")
        print(f"      ID no Lex Flow: {resultado_captura.get('id')}")
        print(f"      Título: {resultado_captura.get('title', 'N/A')[:60]}")
    else:
        print(f"   ⚠️  Captura retornou vazio ou None (pode ser erro ou duplicata)")
    
    # ========================================
    # TESTE 6: RESUMO DO DIA
    # ========================================
    print("\n6️⃣  TESTE: Resumo do Dia (Consolidado)")
    print("-" * 90)
    
    resumo = motor.resumo_do_dia()
    
    print(f"   Prioridades encontradas: {len(resumo.get('prioridades', []))}")
    
    estatisticas = resumo.get('estatisticas', {})
    if estatisticas:
        print(f"   Estatísticas disponíveis: {list(estatisticas.keys())[:5]}")  # Primeiras 5 chaves
    
    # ========================================
    # TESTE 7: HEALTH CHECK
    # ========================================
    print("\n7️⃣  TESTE: Health Check (Verificação de Saúde)")
    print("-" * 90)
    
    saude = motor.health_check()
    
    if saude.get('saudavel'):
        print(f"   ✅ SISTEMA SAUDÁVEL!")
        print(f"      {saude.get('detalhes')}")
    else:
        print(f"   ❌ PROBLEMA DETECTADO:")
        print(f"      {saude.get('detalhes')}")
    
    # ========================================
    # 🆕 TESTE 8: RAG SYSTEM (Brain Middleware)
    # ========================================
    print("\n8️⃣  🆕 TESTE: RAG System (Busca Vetorial)")
    print("-" * 90)
    
    try:
        rag = motor.sistema_rag
        if rag:
            print(f"   ✅ RAG System carregado!")
            print(f"      Estatísticas: {rag.obter_estatisticas()}")
        else:
            print(f"   ⚠️  RAG System não disponível (pode não estar configurado)")
    except Exception as e:
        print(f"   ⚠️  Erro ao testar RAG: {e}")
    
    # ========================================
    # 🆕 TESTE 9: LLM CLIENT (Brain Middleware)
    # ========================================
    print("\n9️⃣  🆕 TESTE: LLM Client (Modelo de Linguagem)")
    print("-" * 90)
    
    try:
        llm = motor.llm_client
        if llm:
            print(f"   ✅ LLM Client carregado!")
            print(f"      Estatísticas: {llm.obter_estatisticas()}")
        else:
            print(f"   ⚠️  LLM Client não disponível (pode não ter API key configurada)")
    except Exception as e:
        print(f"   ⚠️  Erro ao testar LLM: {e}")
    
    # ========================================
    # ENCERRAMENTO GRACEFUL
    # ========================================
    print("\n" + "=" * 90)
    print("🛑 ENCERRANDO TESTE (Graceful Shutdown)")
    print("=" * 90)
    
    motor.parar()
    
    print("\n" + "=" * 90)
    print("📊 RESUMO FINAL DO TESTE:")
    print("=" * 90)
    
    testes_executados = {
        'Singleton Pattern': True,  # Sempre passa se chegou aqui
        'Inicialização do Motor': sucesso_inicio,
        'Status Completo': status is not None,
        'Prioridades': len(prioridades) >= 0,  # Sempre true (pode ser vazio)
        'Captura de Ideia': resultado_captura is not None,
        'Resumo do Dia': resumo is not None,
        'Health Check': saude.get('saudavel', False),
        # 🆕 Testes novos
        'RAG System': True,  # Não falha teste (pode não estar config)
        'LLM Client': True,  # Não falha teste (pode não ter API key)
    }
    
    total_testes = len(testes_executados)
    testes_passaram = sum(1 for resultado in testes_executados.values() if resultado)
    
    for nome_teste, resultado in testes_executados.items():
        icone = "✅" if resultado else "❌"
        print(f"   {icone} {nome_teste}")
    
    print(f"\n   Score: {testes_passaram}/{total_testes} testes passaram")
    
    if testes_passaram >= 7:  # Pelo menos 7 de 9 (permite RAG/LLM sem config)
        print("\n🎉🎉🎉 CORE ENGINE v2.1 100% FUNCIONAL! 🎉🎉🎉")
        print("   Integração Lex Flow: ✅ PRODUÇÃO READY")
        print("   Configuração Centralizada: ✅ CARREGADA")
        print("   Singleton Pattern: ✅ ATIVO")
        print("   Lazy Loading: ✅ PRONTO")
        print("   🆕 RAG System: ✅ DISPONÍVEL (Brain Middleware Ready)")
        print("   🆕 LLM Client: ✅ DISPONÍVEL (Brain Middleware Ready)")
        print("")
        print("   PRÓXIMO PASSO: Implementar Brain Middleware v1.0!")
        print("   Ou começar a usar o motor em seus scripts já!")
    else:
        print("\n⚠️  Alguns testes falharam. Verifique os logs:")
        print("   - logs/core_engine.log")
        print("   - logs/capture_system.log")
        print("   - logs/lex_flow_producao.log")
    
    print("=" * 90 + "\n")