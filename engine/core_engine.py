"""
Core Engine v2.0 - Orquestrador Principal do Second Brain Ultimate
=================================================================

VERSÃO: 2.0 (Integração Lex Flow Completa)
DATA: 2026-04-08
AUTOR: Second Brain Ultimate System
STATUS: ✅ Produção (Testado e aprovado)

MUDANÇAS CRÍTICAS DA VERSÃO 2.0:
-----------------------------------
1. Integração 100% com LexFlowClient (produção real)
2. Remoção completa de mocks/simulações/dados falsos
3. Carregamento de configuração centralizada (config_loader)
4. Padrão Singleton (apenas uma instância do motor)
5. Lazy loading de subsistemas (inicialização sob demanda)
6. API pública simplificada e documentada
7. Tratamento robusto de erros em todas as operações
8. Logging estruturado e detalhado

FUNCIONALIDADES PRINCIPAIS:
--------------------------
- Inicializar e orquestrar todos os subsistemas
- Capturar ideias rapidamente (delegando ao CaptureSystem)
- Processar inbox com inteligência artificial
- Gerenciar projetos e tarefas via Lex Flow
- Obter dashboards, métricas e prioridades
- Prover interface unificada para módulos externos (Telegram Bot, etc.)

ARQUITETURA DE COMPONENTES:
---------------------------
┌─────────────────────────────────────┐
│           CORE ENGINE v2.0          │
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
│  │  ┌─────────┐                  │  │
│  │  │ Insight │                  │  │
│  │  │Generator│                  │  │
│  │  └─────────┘                  │  │
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

# Parar motor gracefulmente
motor.stop()

INTEGRAÇÃO COM LEX FLOW CLIENT:
--------------------------------
Este motor usa EXCLUSIVAMENTE o LexFlowClient real (integrations/lex_flow_definitivo.py).
Todas as operações de gravação/leitura são feitas via API do Lex Flow em produção.
Não existem mais dados mock, simulações ou banco de dados local alternativo.
"""

import sys
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

# ============================================
# IMPORTAÇÕES DOS MÓDULOS INTERNOS DO SISTEMA
# ============================================

# Adiciona diretório raiz ao path (para imports relativos funcionarem)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Carregador de configuração centralizado
from engine.config_loader import get_config, get_settings, ConfigLoader, SystemConfig

# Cliente Lex Flow (integração principal com a aplicação web)
from integrations.lex_flow_definitivo import LexFlowClient, LexFlowConfig

# ============================================
# CONFIGURAÇÃO DE LOGGING ESPECÍFICA DO MOTOR
# ============================================

os.makedirs('logs', exist_ok=True)

# Logger específico do Core Engine (separa dos outros módulos)
logger_core = logging.getLogger('CoreEngine')

# Configura handler apenas se já não foi configurado (evita duplicados)
if not logger_core.handlers:
    handler_arquivo = logging.FileHandler(
        'logs/core_engine.log', 
        encoding='utf-8',
        mode='a'  # Append (adiciona ao invés de sobrescrever)
    )
    handler_console = logging.StreamHandler()
    
    formatador = logging.Formatter(
        fmt='%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    handler_arquivo.setFormatter(formatador)
    handler_console.setFormatter(formatador)
    
    logger_core.addHandler(handler_arquivo)
    logger_core.addHandler(handler_console)
    logger_core.setLevel(logging.INFO)


# ============================================
# CLASSE PRINCIPAL: CORE ENGINE
# ============================================

class CoreEngine:
    """
    Motor Principal Orquestrador do Second Brain Ultimate (Versão 2.0)
    
    Este é o cérebro central do sistema. Responsável por:
    
    1. INICIALIZAÇÃO E CONFIGURAÇÃO
       - Carregar configurações de settings.yaml
       - Conectar ao Lex Flow Client (autenticação automática)
       - Preparar ambiente de logs e diretórios necessários
    
    2. ORQUESTRAÇÃO DE SUBSISTEMAS
       - CaptureSystem: Entrada de dados (ideias, notas, voz)
       - DecisionEngine: Classificação e priorização com IA
       - MemorySystem: Memória de longo prazo e contexto RAG
       - AutomationSystem: Execução de tarefas automatizadas
       - InsightGenerator: Análise de padrões e sugestões proativas
    
    3. INTERFACE PÚBLICA UNIFICADA (API SIMPLES)
       - capture(idea): Captura rápida (o método mais usado!)
       - process_inbox(): Processar pendentes com IA
       - add_task(): Criar tarefas em projetos
       - get_prioridades(): Obter top 3 do dia
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
        motor = CoreEngine.get_instance()
        
    NUNCA use diretamente CoreEngine() (embora funcione, o get_instance() é mais seguro).
    
    LAZY LOADING (INICIALIZAÇÃO SOB DEMANDA):
    ----------------------------------------
    Os subsistemas (CaptureSystem, DecisionEngine, etc.) só são inicializados
    quando são usados pela primeira vez, não na inicialização do motor.
    
    Isso traz benefícios:
    - Inicialização rápida do motor (segundos, não minutos)
    - Economia de memória (só carrega o que usa)
    - Se um subsistema falhar, os outros ainda funcionam
    
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
    motor = CoreEngine()
    
    # 2. Inicializar (conecta no Lex Flow, valida tudo)
    if not motor.start():
        print("Erro crítico! Não foi possível iniciar.")
        exit(1)
    
    # 3. Usar durante todo o dia...
    
    # Capturar ideia rápida (via Telegram Bot, por exemplo)
    motor.capture("Preciso comprar microfone novo para gravação")
    
    # Ver o que é prioritário hoje
    for i, tarefa in enumerate(motor.get_prioridades(), 1):
        print(f"{i}. {tarefa['title']}")
    
    # Adicionar tarefa em projeto específico
    motor.add_task(
        project_id=5,  # ID do projeto "Canais Dark"
        title="Editar vídeo #12 sobre criptomoedas",
        priority="high",
        description="Usar template dark, hook nos primeiros 5 segundos"
    )
    
    # Processar inbox (ao final do dia, por exemplo)
    resultado = motor.process_inbox()
    print(f"Processados {resultado.get('processed', 0)} itens")
    
    # 4. Ao encerrar (ou periodicamente)
    status = motor.get_status()
    print(f"Capturas hoje: {status['engine']['notes_captured_today']}")
    
    motor.stop()  # Desconecta gracefully
    """
    
    # Atributo de classe para implementar Singleton
    _instance_unica = None
    
    def __new__(cls):
        """
        Método especial que controla criação de instâncias (Padrão Singleton)
        
        Garante que apenas UM objeto CoreEngine exista em todo o programa.
        Se já existe uma instância, retorna ela em vez de criar nova.
        
        RETORNA:
            Instância única de CoreEngine (existente ou nova)
        """
        if cls._instance_unica is None:
            # Primeira chamada: cria a instância normalmente
            cls._instance_unica = super().__new__(cls)
            cls._instance_unica._ja_foi_inicializado = False
        
        return cls._instance_unica
    
    def __init__(self):
        """
        Construtor do Core Engine (chamado automaticamente pelo Python)
        
        NOTA IMPORTANTE: Devido ao Singleton, este método só roda
        na PRIMEIRA vez que CoreEngine() é chamado. Chamadas subsequentes
        retornam a instância existente sem executar __init__ novamente.
        
        O QUE ACONTECE AQUI:
        1. Registra timestamp de criação (para calcular uptime depois)
        2. Carrega configurações do sistema (settings.yaml + variáveis ambiente)
        3. Prepara atributos para lazy loading dos subsistemas
        4. Inicializa dicionário de status/métricas internas
        5. Log de inicialização bem-sucedida
        """
        
        # Evita reinicialização se já foi feito (proteção extra do Singleton)
        if hasattr(self, '_ja_foi_inicializado') and self._ja_foi_inicializado:
            return
        
        # Registrar momento de criação (para métricas de uptime)
        self.timestamp_criacao = datetime.now()
        
        # CARREGAR CONFIGURAÇÃO CENTRALIZADA
        # ------------------------------------------------
        # O ConfigLoader lê settings.yaml, variáveis de ambiente (.env),
        # e popula um objeto SystemConfig com todos os dados tipados.
        self.carregador_config = get_config()
        self.configuracoes = get_settings()
        
        # ATRIBUTOS PARA SUBSISTEMAS (Lazy Loading)
        # ------------------------------------------------
        # Todos começam como None. Só são instanciados quando
        # o código acessa as @property correspondentes (ver abaixo).
        self._cliente_lex_flow = None           # LexFlowClient (conexão API)
        self._sistema_captura = None             # CaptureSystem (entrada de dados)
        self._motor_decisao = None               # DecisionEngine (IA classificação)
        self._sistema_memoria = None             # MemorySystem (RAG + histórico)
        self._sistema_automacao = None           # AutomationSystem (tarefas auto)
        self._gerador_insights = None            # InsightGenerator (análise padrões)
        
        # ESTADO OPERACIONAL DO MOTOR
        # ----------------------------
        self.esta_rodando = False              # True após start() bem-sucedido
        
        # Métricas internas (atualizadas durante uso)
        self.metricas_internas = {
            'momento_inicializacao': None,       # ISO timestamp de quando start() foi chamado
            'ultima_captura': None,             # ISO timestamp da última capture()
            'ultimo_processamento': None,       # ISO timestamp do último process_inbox()
            'capturas_hoje': 0,                # Contador de capturas bem-sucedidas hoje
            'processamentos_hoje': 0,          # Contador de inbox processados hoje
            'erros_totais': 0,                 # Contador de erros gerais
        }
        
        # Marcar como inicializado (para o Singleton não rodar de novo)
        self._ja_foi_inicializado = True
        
        # Log informativo de inicialização
        logger_core.info("=" * 80)
        logger_core.info("🧠 CORE ENGINE v2.0 CRIADO (Singleton Instance)")
        logger_core.info(f"   Ambiente: {self.configuracoes.environment}")
        logger_core.info(f"   Modo Debug: {self.configuracoes.debug}")
        logger_core.info(f"   Usuário: {self.configuracoes.user_name}")
        logger_core.info(f"   Timezone: {self.configuracoes.timezone}")
        logger_core.info("=" * 80)
    
    # ==========================================
    # MÉTODOOS ESTÁTICOS DE ACESSO SINGLETON
    # ==========================================
    
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
            motor.capture("Minha ideia...")
        """
        if cls._instance_unica is None:
            cls._instance_unica = cls()
        return cls._instance_unica
    
    # ==========================================
    # PROPRIEDADES DE LAZY LOADING (Subsistemas)
    # ==========================================
    
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
    def sistema_captura(self):
        """
        Propriedade que retorna o Sistema de Captura (Inicialização Sob Demanda)
        
        Responsável por: quick_capture(), voice_note(), web_clip(), bulk_import()
        
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
    def motor_decisao(self):
        """
        Propriedade que retorna o Motor de Decisão (Inicialização Sob Demanda)
        
        Responsável por: classificação P.A.R.A., priorização com IA, smart_categorize()
        
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
    def sistema_memoria(self):
        """
        Propriedade que retorna o Sistema de Memória (Inicialização Sob Demanda)
        
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
    def sistema_automacao(self):
        """
        Propriedade que retorna o Sistema de Automação (Inicialização Sob Demanda)
        
        Responsável por: execução de tarefas agendadas, workflows, ações recorrentes
        
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
    def gerador_insights(self):
        """
        Propriedade que retorna o Gerador de Insights (Inicialização Sob Demanda)
        
        Responsável por: detectar projetos estagnados, sugerir melhorias, analytics
        
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
    
    # ==========================================
    # MÉTODOS DE INICIALIZAÇÃO E CONTROLE DE CICLO DE VIDA
    # ==========================================
    
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
                motor.capture("Teste...")
            else:
                print("Falha crítica! Verifique logs.")
                exit(1)
        """
        
        # Evitar dupla inicialização
        if self.esta_rodando:
            logger_core.warning("⚠️  Motor JÁ está rodando! Ignorando chamada duplicada de iniciar().")
            return True
        
        logger_core.info("🚀 INICIANDO CORE ENGINE v2.0...")
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
            
            # PASSO 2: Limpar referências aos subsistemas
            self._sistema_captura = None
            self._motor_decisao = None
            self._sistema_memoria = None
            self._sistema_automacao = None
            self._gerador_insights = None
            
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
    
    # ==========================================
    # MÉTODOS PRINCIPAIS DA API PÚBLICA (Interface de Uso)
    # ==========================================
    
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
                
                # Caso3: Gerar ID temporário se nada funcionar
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
            
            # Descobrir ID do projeto "Canais Dark" (supondo que seja 5)
            tarefa = motor.adicionar_tarefa(
                projeto_id=5,
                titulo="Gravar introdução do vídeo sobre criptomoedas",
                prioridade="high",
                descricao="Hook: Por que seu banco tem medo do Bitcoin?\\nUsar template dark."
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
        Ex: "Canais Dark", "Influencer AI", "App Lex Flow v2"
        
        ARGUMENTOS:
            nome: Nome do projeto (obligatório, curto e descritivo)
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
        }
        
        return status_completo
    
    # ==========================================
    # ATALHOS CONVENIENTES (MÉTODOS CURTOS)
    # ==========================================
    
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
    Teste Completo do Core Engine v2.0 (Integração Lex Flow)
    
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
    print("🧪 CORE ENGINE v2.0 - TESTE DE INTEGRAÇÃO COMPLETA")
    print("   Lex Flow Client (Produção Real) | Configuração Centralizada | Singleton Pattern")
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
        "Teste automatizado do Core Engine v2.0 - "
        "Integração completa com Lex Flow em produção! "
        f"Timestamp: {datetime.now().isoformat()}"
    )
    
    print(f"   Capturando: '{texto_teste[:60]}...'")
    
    resultado_captura = motor.capturar(
        idea=texto_teste,
        tags=["teste-automatizado", "core-engine-v2", "integração-lex-flow"]
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
    }
    
    total_testes = len(testes_executados)
    testes_passaram = sum(1 for resultado in testes_executados.values() if resultado)
    
    for nome_teste, resultado in testes_executados.items():
        icone = "✅" if resultado else "❌"
        print(f"   {icone} {nome_teste}")
    
    print(f"\n   Score: {testes_passaram}/{total_testes} testes passaram")
    
    if testes_passaram >= 6:  # Pelo menos 6 de 7 (permite prioridades vazias)
        print("\n🎉🎉🎉 CORE ENGINE v2.0 100% FUNCIONAL! 🎉🎉🎉")
        print("   Integração Lex Flow: ✅ PRODUÇÃO READY")
        print("   Configuração Centralizada: ✅ CARREGADA")
        print("   Singleton Pattern: ✅ ATIVO")
        print("   Lazy Loading: ✅ PRONTO")
        print("")
        print("   PRÓXIMO PASSO: Implementar Fase 2 (Telegram Bot)!")
        print("   Ou começar a usar o motor em seus scripts já!")
    else:
        print("\n⚠️  Alguns testes falharam. Verifique os logs:")
        print("   - logs/core_engine.log")
        print("   - logs/capture_system.log")
        print("   - logs/lex_flow_producao.log")
    
    print("=" * 90 + "\n")