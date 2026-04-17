"""
================================================================================
LEX BRAIN TELEGRAM BOT v2.1 - Interface Mobile do Second Brain Ultimate
================================================================================

VERSÃO: 2.1 (Brain Middleware Conversacional INTELIGENTE!)
DATA: 12/04/2026 (Refatorado e Corrigido)
AUTOR: Lex-Usamn | Second Brain Ultimate System
STATUS: ✅ Produção (Conversação Funcional!)

NOVIDADES v2.1:
--------------
🧠 CONVERSAÇÃO FUNCIONAL!
   ✅ Bot SABE quando está em uma conversa com você!
   ✅ Mantém contexto por usuário (usuario_id)
   ✅ Detecta respostas a perguntas de clarificação
   ✅ Entende "sim", "não", "tarefa", "nota", "editar", etc.
   ✅ Sistema de memória de curto prazo por usuário

ARQUITETURA MODULAR (v2.1):
------------------------
✅ telegram_utils.py      → Constantes, formatação, logging
✅ telegram_handlers.py   → Comandos (/start, /tarefa, /nota, etc.)
✅ telegram_brain_handler.py → IA Conversacional (Brain MW v2.1)
✅ telegram_bot.py        → Este arquivo (classe principal + boot)

FUNCIONALIDADES PRINCIPAIS:
---------------------------
✅ Captura rápida de ideias via mensagem de texto (/nota ou texto livre)
✅ Criação de tarefas em projetos (/tarefa) com parse avançado
✅ Visualização de prioridades do dia (/hoje) - Morning Briefing
✅ Listagem de projetos ativos (/projetos)
✅ Métricas de produtividade (/metricas)
✅ Controle de sessões Pomodoro (/pomodoro)
✅ Health check completo do sistema (/status)
✅ Comando de ajuda (/ajuda)
🆕 Conversação natural via Brain Middleware (IA GLM5 + RAG)
🆕 Contexto mantido por usuário (sabe quando está conversando!)

COMO USAR:
----------
1. Configurar token em config/settings.yaml ou variável ambiente
2. Instalar dependência: pip install python-telegram-bot>=20.7
3. Executar: python integrations/telegram_bot.py
4. Enviar /start no @seu_bot
5. Pronto para usar!

EXEMPLOS DE INTERAÇÃO (CONVERSAÇÃO NATURAL):
-------------------------------------------
Você: "Lex, anota que preciso comprar microfone Blue Yeti"
Bot: ✅ Nota criada com sucesso!

Você: "Lex, lembra que tenho que terminar o vídeo até sexta"
Bot: 🤔 Entendi que você quer criar um lembrete sobre 'terminar o vídeo até sexta'.
     Isso mesmo?
     🔹 TAREFA com lembrete?
     🔹 NOTA simples?
Você: "tarefa, prioridade alta!"
Bot: ✅ Tarefa criada! 📋 Terminar o vídeo 📅 Prazo: Sexta 🔥 Prioridade: Alta

DEPENDÊNCIAS:
------------
python-telegram-bot>=20.7
engine.core_engine (CoreEngine Singleton)
engine.brain_middleware (BrainMiddleware - opcional)

================================================================================
"""

import sys
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# ============================================================================
# ADICIONAR DIRETÓRIO RAIZ AO PATH
# ============================================================================
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================================
# IMPORTAÇÕES DO TELEGRAM
# ============================================================================

try:
    from telegram import Update, ReplyKeyboardRemove
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        filters,
        ContextTypes,
        CallbackContext
    )
    LIB_TELEGRAM_DISPONIVEL = True
except ImportError:
    LIB_TELEGRAM_DISPONIVEL = False
    print("⚠️  Biblioteca python-telegram-bot não instalada!")
    print("   Instale com: pip install python-telegram-bot>=20.7")

# ============================================================================
# IMPORTAÇÕES DOS MÓDULOS INTERNOS (Modular!)
# ============================================================================

# Utilitários compartilhados (logging, formatação, constantes)
from integrations.telegram_utils import (
    logger_telegram,
    EmojiSystema as E,
    formatar_tempo,
    formatar_data_extensa,
    truncar_texto,
    configurar_logger_telegram
)

# === BRAIN v3.0 (LLM-First Architecture) ===
from engine.brain_llm_orchestrator import (
    BrainLLMOrchestrator,
    obter_orchestrator_global,      # ✅ ATOR (não ADOR!)
    definir_orchestrator_global,    # ✅ ATOR (não ADOR!)
    RespostaBrain
)

# Handlers de comandos (/start, /tarefa, /nota, etc.)
from integrations.telegram_handlers import TelegramHandlers

# Handler de IA Conversacional (Brain MW v2.1)
from integrations.telegram_brain_handler import (
    BrainHandler,
    TipoResposta,
    definir_brain_middleware_global,
    BRAIN_DISPONIVEL
)

# Core Engine (motor principal)
from engine.core_engine import CoreEngine


# ============================================================================
# CLASSE PRINCIPAL: LEX BRAIN TELEGRAM BOT v2.1
# ============================================================================

class LexBrainTelegramBot:
    """
    Bot do Telegram para o Lex Brain Hybrid System v2.1
    
    Este é o ponto de entrada mobile para todo o sistema.
    Arquitetura modular: delega handlers para módulos especializados.
    
    NOVIDADE v2.1: Conversação funcional com Brain Middleware!
    - Bot SABE quando está em conversa com cada usuário
    - Mantém contexto separado por usuario_id
    - Detecta respostas a clarificações automaticamente
    
    ==========================================================================
    PADRÃO DE PROJETO:
    ==========================================================================
    1. CoreEngine Singleton (uma instância compartilhada)
    2. Lazy Initialization (só inicia quando necessário)
    3. Brain Handler com estado de conversa por usuário
    4. Logging completo (logs/telegram_bot.log)
    5. Tratamento robusto de erros (nunca crasha)
    
    ==========================================================================
    ESTRUTURA MODULAR:
    ==========================================================================
    - telegram_utils.py       → Constantes, formatação, logging
    - telegram_handlers.py    → Handlers de comandos (/start, /tarefa, ...)
    - telegram_brain_handler.py → IA Conversacional (contexto por usuário)
    - telegram_bot.py         → Esta classe (orquestrador principal)
    
    ==========================================================================
    """
    
    def __init__(self):
        """
        Inicializa o Bot do Telegram.
        
        O que acontece aqui:
        1. Carrega token (env > yaml)
        2. Prepara referências lazy (_motor, _handlers, _brain_handler)
        3. Não conecta em nada pesado ainda (lazy init!)
        """
        
        # Carregar token
        self.token = self._obter_token()
        
        if not self.token:
            raise ValueError(
                "❌ Token do Telegram Bot não configurado!\n\n"
                "Configure TELEGRAM_BOT_TOKEN ou edite settings.yaml\n\n"
                "Exemplo:\n"
                "export TELEGRAM_BOT_TOKEN=seu_token_aqui"
            )
        
        # Motor do Core Engine (lazy init)
        self._motor = None
        self._motor_inicializado = False
        
        # Handlers de comandos (instanciado sob demanda)
        self._handlers: Optional[TelegramHandlers] = None
        
        # Brain Handler (IA Conversacional) - INSTÂNCIA ÚNICA!
        self._brain_handler: Optional[BrainHandler] = None
        
        logger_telegram.info("=" * 80)
        logger_telegram.info(f"🤖 LEX BRAIN TELEGRAM BOT v2.1 INICIALIZADO")
        logger_telegram.info(f"   Token: {self.token[:10]}...{self.token[-4:]}")
        logger_telegram.info(f"   Brain MW: {'✅ Disponível' if BRAIN_DISPONIVEL else '⚠️ Indisponível'}")
        logger_telegram.info(f"   Status: ⏳ Aguardando primeiro comando (Lazy Init)")
        logger_telegram.info("=" * 80)
    
    # =========================================================================
    # PROPRIEDADES (Lazy Initialization)
    # =========================================================================
    
    @property
    def motor(self) -> CoreEngine:
        """Retorna Core Engine (inicia se necessário)."""
        if self._motor is None or not self._motor_inicializado:
            logger_telegram.info("🔄 [LAZY INIT] Iniciando Core Engine...")
            
            try:
                self._motor = CoreEngine.obter_instancia()
                sucesso = self._motor.iniciar()
                
                if not sucesso:
                    raise ConnectionError(
                        "❌ Falha ao iniciar Core Engine!\n"
                        "Verifique logs/core_engine.log"
                    )
                
                self._motor_inicializado = True
                logger_telegram.info("✅ [LAZY INIT] Core Engine pronto!")
                
            except Exception as erro:
                logger_telegram.critical(
                    f"💥 [LAZY INIT] FALHA CRÍTICA: {erro}", exc_info=True
                )
                raise
        
        return self._motor
    
    @property
    def handlers(self) -> TelegramHandlers:
        """Retorna instância de TelegramHandlers."""
        if self._handlers is None:
            self._handlers = TelegramHandlers(self)
            logger_telegram.info("✅ [HANDLERS] Instância criada")
        return self._handlers
    
    @property
    def brain_handler(self) -> Optional[BrainHandler]:
        """
        Retorna instância do BrainHandler (IA Conversacional).
        
        É CRÍTICO que seja sempre a mesma instância para manter
        o estado das conversas por usuário!
        """
        if self._brain_handler is None:
            self._brain_handler = BrainHandler()
            logger_telegram.info("✅ [BRAIN HANDLER] Instância criada")
        return self._brain_handler

# === ADICIONAR ISTO ===
    def inicializar_orchestrator_v3(self, orchestrator_instance: BrainLLMOrchestrator):
        """
        Inicializa o Orquestrador LLM v3.0 no Bot.
        
        Este método é chamado pelo iniciar_scheduler.py durante o boot.
        Conecta o cérebro IA ao bot!
        
        Args:
            orchestrator_instance: Instância do BrainLLMOrchestrator já inicializada
        """
        # Também atualiza o brain_handler para usar o orchestrator
        if self._brain_handler:
            self._brain_handler.definir_orchestrador(orchestrator_instance)
            logger_telegram.info("✅ [BOT] Orchestrator v3.0 conectado ao BrainHandler!")
        
        # Definir como global (para acesso de outros módulos)
        definir_orchestrator_global(orchestrator_instance) 
        
        logger_telegram.info("✅ [BOT] Orquestrador v3.0 (LLM-First) inicializado!")
        logger_telegram.info("   🧠 Modo: IA Conversacional Real (GLM5)")
# === FIM DO QUE ADICIONAR ===
    
    # =========================================================================
    # MÉTODO PARA OBTER TOKEN
    # =========================================================================
    
    def _obter_token(self) -> Optional[str]:
        """Obter token de variável ambiente ou settings.yaml."""
        
        # Tentativa 1: Variável de ambiente (prioridade máxima)
        token_env = os.environ.get('TELEGRAM_BOT_TOKEN')
        if token_env and token_env.strip():
            logger_telegram.info("✅ Token de variável de ambiente")
            return token_env.strip()
        
        # Tentativa 2: Settings.yaml
        try:
            from engine.config_loader import ConfigLoader
            config_loader = ConfigLoader.get_instance()
            
            if hasattr(config_loader.configuracoes, 'telegram'):
                tg_cfg = config_loader.configuracoes.telegram
                if hasattr(tg_cfg, 'bot_token') and tg_cfg.bot_token:
                    logger_telegram.info("✅ Token de settings.yaml")
                    return tg_cfg.bot_token
                    
        except Exception as erro:
            logger_telegram.warning(f"⚠️ Erro ao ler settings.yaml: {erro}")
        
        logger_telegram.warning("❌ Token não encontrado")
        return None
    
    # =========================================================================
    # HANDLER PRINCIPAL DE MENSAGEM (COM SUPORTE A CONVERSA v2.1!)
    # =========================================================================
    
    async def handler_mensagem_texto(self, update, context):
        """
        Handler PRINCIPAL para mensagens de texto - v3.0 (IA Real!)
        
        FLUXO CORRETO v3.0:
        Telegram → Bot → BrainHandler → Orchestrator(GLM5) → Resposta
        """
        
        mensagem = update.message.text
        usuario = update.effective_user
        usuario_id = usuario.id
        nome_usuario = usuario.first_name or "Usuario"
        
        logger_telegram.info(f"[BRAIN v3.0] Mensagem de {nome_usuario} (ID: {usuario_id})")
        logger_telegram.info(f"   Texto: '{mensagem}'")
        
        try:
            # ================================================================
            # USAR BRAIN HANDLER (forma CORRETA!)
            # ================================================================
            brain = self.brain_handler
            
            if not brain:
                logger_telegram.warning("[BRAIN v3.0] BrainHandler nao disponivel!")
                await update.message.reply_text(
                    "Mago esta acordando...\n\n"
                    "Da 2 segundos que ja tou online!\n\n"
                    "(Se persistir, use /start)",
                    parse_mode='Markdown'
                )
                return
            
            # Processar via BrainHandler (ele cuida de tudo!)
            tipo_resposta, texto_resposta = await brain.processar_mensagem(
                mensagem=mensagem,
                update=update,
                context=context
            )
            
            # Enviar resposta ao usuario (com fallback se Markdown falhar!)
            try:
                # Tentativa 1: Com Markdown (bonito!)
                await update.message.reply_text(
                    texto_resposta,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
            except Exception as erro_markdown:
                # Se Markdown falhar → enviar como texto puro (seguro!)
                logger_telegram.warning(
                    f"[BRAIN v3.0] Markdown falhou, usando texto puro: {erro_markdown}"
                )
                
                # Limpar caracteres problemáticos do Markdown
                texto_limpo = self._limpar_markdown(texto_resposta)
                
                await update.message.reply_text(
                    texto_limpo,
                    disable_web_page_preview=True
                )
            
            logger_telegram.info(f"[RESPOSTA v3.0] Tipo: {tipo_resposta.value}")
                                
            return
            
        except Exception as e:
            logger_telegram.error(f"[BRAIN v3.0] Erro critico: {e}", exc_info=True)
            
            await update.message.reply_text(
                f"Ops! Algo deu errado aqui... 😅\n\n"
                f"Erro: `{str(e)[:50]}`\n\n"
                f"Tenta mandar de novo?",
                parse_mode='Markdown'
            )
    
    async def _fallback_auto_capture(
        self,
        update: Update,
        context: CallbackContext,
        mensagem: str,
        nome_usuario: str
    ):
        """
        Fallback quando Brain MW não está disponível.
        Captura como nota simples (comportamento original).
        """
        logger_telegram.info(
            f"📝 [AUTO-CAPTURE] Capturando de {nome_usuario}: '{mensagem[:50]}...'"
        )
        
        try:
            # Tentar salvar via motor
            resultado = self.motor.capturar(idea=mensagem)
            
            if resultado and resultado.get('id'):
                await update.message.reply_text(
                    f"📝 *Nota capturada!*\n\n"
                    f"💬 {truncar_texto(mensagem, 80)}\n\n"
                    f"🆔 ID: `{resultado.get('id')}`\n\n"
                    f"ℹ️ Modo simplificado (sem IA conversacional)",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"📝 *Recebido!*\n\n"
                    f"💬 {truncar_texto(mensagem, 60)}\n\n"
                    f"(IA indisponível - mensagem registrada)",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger_telegram.error(f"❌ [AUTO-CAPTURE] Erro: {e}")
            await update.message.reply_text(
                "📝 Mensagem recebida! (modo simplificado)"
            )
    
    def _limpar_markdown(self, texto: str) -> str:
        """
        Remove/caracteres especiais de Markdown para envio seguro.
        
        Quando o parse_mode='Markdown' falha, chamamos este método
        para limpar o texto e enviar como texto puro (sem formatação).
        
        Args:
            texto: Texto que pode conter Markdown malformado
            
        Returns:
            Texto limpo, seguro para enviar sem parse_mode
        """
        if not texto:
            return ""
        
        # Caracteres problemáticos do Markdown que vamos remover
        substituicoes = [
            ('**', ''),     # Bold (**texto**)
            ('*', ''),      # Italic (*texto*)
            ('__', ''),     # Underline (__texto__)
            ('_', ''),      # Italic (_texto_)
            ('```', ''),    # Code block
            ('`', ''),      # Inline code (`codigo`)
            ('~~', ''),     # Strikethrough
            ('~', ''),      # Strikethrough simples
            ('>', ' '),     # Blockquote
            ('|', ' '),     # Table separator
            ('---', '---'), # Horizontal rule (manter como separador)
            ('###', ''),    # Header H3
            ('##', ''),     # Header H2
            ('#', ''),      # Header H1
        ]
        
        texto_limpo = texto
        
        # Aplicar substituições (ordem importa: primeiro as duplas!)
        for velho, novo in substituicoes:
            texto_limpo = texto_limpo.replace(velho, novo)
        
        # Limpar múltiplos espaços consecutivos
        import re
        texto_limpo = re.sub(r'  +', ' ', texto_limpo)
        
        # Remover espaços no início/fim de cada linha
        linhas = [linha.strip() for linha in texto_limpo.split('\n')]
        texto_limpo = '\n'.join(linhas)
        
        return texto_limpo.strip()

    # =========================================================================
    # MÉTODOS DE CONTROLE DO BOT
    # =========================================================================
    
    def iniciar(self):
        """
        Iniciar o Bot do Telegram (Método Principal - Bloqueante).
        
        Fluxo:
        1. Validar dependências
        2. Criar Application
        3. Registrar handlers (delegando aos módulos)
        4. Iniciar polling (loop infinito)
        """
        
        # Validar biblioteca
        if not LIB_TELEGRAM_DISPONIVEL:
            print("\n" + "=" * 80)
            print("❌ FATAL: python-telegram-bot não instalado!")
            print("   pip install python-telegram-bot>=20.7")
            print("=" * 80 + "\n")
            return
        
        logger_telegram.info("🚀 Iniciando Telegram Bot v2.1...")
        
        try:
            # Criar Application
            aplicacao = Application.builder().token(self.token).build()
            logger_telegram.info("✅ Application criada")
            
            # ==============================================================
            # REGISTRAR HANDLERS DE COMANDOS
            # ==============================================================
            logger_telegram.info("📋 Registrando handlers...")
            
            h = self.handlers  # Atalho para instância de handlers
            
            # Comandos básicos
            aplicacao.add_handler(CommandHandler("start", h.comando_start))
            aplicacao.add_handler(CommandHandler("help", h.comando_ajuda))
            aplicacao.add_handler(CommandHandler("ajuda", h.comando_ajuda))
            
            # Comandos de produtividade
            aplicacao.add_handler(CommandHandler("hoje", h.comando_hoje))
            aplicacao.add_handler(CommandHandler("nota", h.comando_nota))
            aplicacao.add_handler(CommandHandler("tarefa", h.comando_tarefa))
            aplicacao.add_handler(CommandHandler("projetos", h.comando_projetos))
            aplicacao.add_handler(CommandHandler("metricas", h.comando_metricas))
            aplicacao.add_handler(CommandHandler("pomodoro", h.comando_pomodoro))
            
            # Comandos de sistema
            aplicacao.add_handler(CommandHandler("status", h.comando_status))
            
            # Handler de mensagens diretas (sem /)
            # ESTE É O QUE CHAMA O BRAIN HANDLER!
            aplicacao.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handler_mensagem_texto)
            )
            
            logger_telegram.info(f"✅ {10} handlers registrados")
            
            # ==============================================================
            # INICIAR POLLING
            # ==============================================================
            logger_telegram.info("📡 Conectando ao Telegram...")
            logger_telegram.info("=" * 80)
            logger_telegram.info("🤖 LEX BRAIN BOT v2.1 ONLINE!")
            logger_telegram.info("   🧠 Conversação ATIVA (contexto por usuário)")
            logger_telegram.info("   Pressione Ctrl+C para encerrar")
            logger_telegram.info("=" * 80)
            
            # Print visual no console
            print("\n" + "🟢" * 40)
            print("✅ LEX BRAIN BOT v2.1 CONECTADO!")
            print(f"   🤖 @seu_bot")
            print(f"   🧠 IA Conversacional: {'ATIVA' if BRAIN_DISPONIVEL else 'INATIVA'}")
            print("   📱 Envie /start para começar!")
            print("🟢" * 40 + "\n")
            
            # Loop principal (bloqueante!)
            aplicacao.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
        except KeyboardInterrupt:
            logger_telegram.info("\n⛔ Bot encerrado pelo usuário (Ctrl+C)")
            print("\n\n⛔ Bot encerrado. Até logo! 👋\n")
            
        except Exception as erro_bot:
            logger_telegram.error(f"❌ ERRO FATAL: {erro_bot}", exc_info=True)
            print(f"\n{'❌' * 40}")
            print(f"ERRO FATAL: {erro_bot}")
            print(f"Verifique logs/telegram_bot.log")
            print(f"{'❌' * 40}\n")


# ============================================================================
# PONTO DE ENTRADA PRINCIPAL (Entry Point)
# ============================================================================

if __name__ == "__main__":
    """
    Executar o bot em modo standalone.
    
    Como usar:
        cd SecondBrain_Ultimate
        export TELEGRAM_BOT_TOKEN=seu_token
        python integrations/telegram_bot.py
    """
    
    print("\n" + "=" * 80)
    print("🤖 LEX BRAIN TELEGRAM BOT v2.1")
    print("   Second Brain Ultimate | IA Assistente Pessoal")
    print("   Autor: Lex-Usamn | Data: 12/04/2026")
    print("=" * 80 + "\n")
    
    try:
        # Criar instância do bot
        bot = LexBrainTelegramBot()
        
        # Iniciar (bloqueante - loop infinito)
        bot.iniciar()
        
    except ValueError as erro_valor:
        print(f"\n❌ ERRO DE CONFIGURAÇÃO: {erro_valor}\n")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n⛔ Interrompido durante inicialização.\n")
        sys.exit(0)
        
    except Exception as erro_geral:
        print(f"\n💥 ERRO INESPERADO: {erro_geral}\n")
        print("🔧 Verifique logs/telegram_bot.log\n")
        sys.exit(1)