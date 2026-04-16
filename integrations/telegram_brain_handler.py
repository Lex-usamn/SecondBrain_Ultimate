"""
================================================================================
TELEGRAM BRAIN HANDLER v3.0 - IA Conversacional (LLM-First Architecture)
================================================================================

SUBSTITUI O ANTIGO brain_middleware v2.1!

Este arquivo é o PONTE entre o Telegram Bot e o BrainLLMOrchestrator v3.0

AUTOR: Mago-Usamn | DATA: 14/04/2026
VERSÃO: 3.0 (LLM-First - GLM5 decide tudo!)

================================================================================
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Optional, Tuple
from enum import Enum


# Imports SEMPRE disponíveis (em runtime, não só para type checking!)
from telegram import Update
from telegram.ext import CallbackContext

if TYPE_CHECKING:
    # Apenas imports que causariam circular import (se houver)
    from engine.brain_llm_orchestrator import BrainLLMOrchestrator, RespostaBrain
else:
    # Em runtime, evitamos import circular aqui (serão importados quando necessários)
    BrainLLMOrchestrator = None  # type: ignore
    RespostaBrain = None  # type: ignore


logger = logging.getLogger("TelegramBrainHandler")


# =============================================================================
# ENUM DE TIPO DE RESPOSTA
# =============================================================================

class TipoResposta(Enum):
    """Tipos de resposta que o handler pode retornar."""
    CONVERSA = "conversa"
    TAREFA_CRIADA = "tarefa_criada"
    NOTA_CRIADA = "nota_criada"
    BUSCA_REALIZADA = "busca_realizada"
    ERRO = "erro"
    AGUARDANDO_CLARIFICACAO = "aguardando_clarificacao"


# =============================================================================
# FLAG GLOBAL DE DISPONIBILIDADE
# =============================================================================

BRAIN_DISPONIVEL = True  # Sempre disponível na v3.0!


# =============================================================================
# CLASSE PRINCIPAL: BRAIN HANDLER v3.0
# =============================================================================

class BrainHandler:
    """
    Handler de IA Conversacional para o Telegram Bot v3.0.
    
    DIFERENÇA CRÍTICA vs v2.1:
    - v2.1: Usava BrainMiddleware (Regex-based) → Burro!
    - v3.0: Usa BrainLLMOrchestrator (GLM5-based) → Inteligente!
    
    Este handler:
    1. Recebe mensagem do usuário (via telegram_bot.py)
    2. Extrai dados do usuário (id, nome, username)
    3. Chama orchestrator.processar() com contexto
    4. Retorna (TipoResposta, texto_resposta) pro bot enviar
    """
    
    def __init__(self):
        """Inicializa o Brain Handler v3.0."""
        self._orchestrator = None
        self._clarificacoes_pendentes: Dict[int, Dict[str, Any]] = {}

        logger.info("🧠 [v3.0] BrainHandler inicializado (modo LLM-First)")

     # =========================================================================
    # MÉTODO PRINCIPAL: processar_mensagem() (SEM STREAMING)
    # =========================================================================
    
    async def processar_mensagem(
        self,
        mensagem: str,
        update: Update,
        context: CallbackContext
    ) -> Tuple[TipoResposta, str]:
        """
        Processa mensagem do usuário usando BrainLLMOrchestrator.
        
        Versão SEM streaming - processa tudo e retorna resposta completa.
        
        Args:
            mensagem: Texto da mensagem do usuário
            update: Objeto Update do Telegram
            context: Objeto Context do Telegram
            
        Returns:
            Tuple[TipoResposta, str]: (tipo da resposta, texto da resposta)
        """
        usuario_id = update.effective_user.id
        
        logger.info(f"💬 [BRAIN] Processando mensagem: '{mensagem[:50]}...'")
        
        # VALOR PADRÃO SEGURO (sempre retorna isso se der erro!)
        resultado_padrao = (
            TipoResposta.ERRO,
            "❌ Erro ao processar mensagem. Tente novamente."
        )
        
        try:
            # =================================================================
            # ✅✅✅ ADICIONAR AQUI - MOSTRAR "DIGITANDO..." ✅✅✅
            # =================================================================
            try:
                from telegram import ChatAction
                
                await update.message.chat.send_action(
                    action=ChatAction.TYPING
                )
                logger.debug("⌨️ [BRAIN] Ação 'typing' enviada!")
            except Exception as erro_typing:
                logger.debug(f"⚠️ [BRAIN] Typing falhou (não crítico): {erro_typing}")
            # =================================================================
            
            # 1. Obter orquestrador global
            orchestrator = self._obter_orchestrator()
            
            if not orchestrator:
                logger.error("❌ [BRAIN] Orchestrador não disponível!")
                return (
                    TipoResposta.ERRO,
                    "❌ Cérebro indisponível. Tente novamente em instantes."
                )
            
            # 2. Preparar contexto com dados do usuário
            contexto_usuario = {
                "usuario_id": usuario_id,
                "nome": update.effective_user.first_name or "Usuário",
                "username": update.effective_user.username or None
            }
            
            # =================================================================
            # 3. VERIFICAR CLARIFICAÇÃO PENDENTE (CORREÇÃO DO LOOP v3.2!)
            # =================================================================
            
            usuario_id = update.effective_user.id
            
            # ✅ VERIFICAR PRIMEIRO se há clarificação pendente!
            clarificacao_pendente = orchestrator.obter_clarificacao_pendente(usuario_id)
            
            if clarificacao_pendente:
                logger.info(f"🔄 [BRAIN] Clarificação pendente detectada para user {usuario_id}")
                
                resposta = orchestrator.processar_resposta_clarificacao(
                    mensagem=mensagem,
                    usuario_id=usuario_id
                )
                
                # 🛡️ v3.3: SE falhar, NÃO chama o LLM de novo (evita loop de clarificação)
                if not resposta:
                    logger.warning("⚠️ [BRAIN] Falha ao processar clarificação. Criando resposta de fallback segura...")
                    resposta = RespostaBrain(
                        sucesso=True,
                        acao_executada="erro_clarificacao",
                        resposta_ia="🤔 Não consegui processar sua confirmação. Pode repetir se quer `nota` ou `tarefa`?",
                        aguardando_resposta=False,
                        clarificacao_pendente=False
                    )
                else:
                    logger.info(f"✅ [BRAIN] Resposta de clarificação processada com sucesso!")
            
            else:
                logger.info(f"🧠 [BRAIN] Chamando orchestrator.processar()...")
                resposta = orchestrator.processar(
                    mensagem=mensagem,
                    contexto=contexto_usuario
                )
            
            # =================================================================
            # 4. EXTRAIR TEXTO DA RESPOSTA (CORRIGIDO - v3.0.1!)
            # =================================================================
            
            texto_resposta = None
            
            # Verificar se resposta é None
            if resposta is None:
                logger.warning("⚠️ [BRAIN] Resposta é None!")
                return (
                    TipoResposta.ERRO,
                    "🤔 Não consegui gerar resposta. Tenta de novo?"
                )
            
            # ✅ Tentativa 1: Atributo correto 'resposta_ia' (com underscore!)
            if hasattr(resposta, 'resposta_ia') and resposta.resposta_ia:
                texto_resposta = resposta.resposta_ia
                logger.debug(f"✅ [BRAIN] Extraído via .resposta_ia")
                
            # ✅ Tentativa 2: Variação sem underscore (compatibilidade)
            elif hasattr(resposta, 'respostaia') and resposta.respostaia:
                texto_resposta = resposta.respostaia
                logger.debug(f"✅ [BRAIN] Extraído via .respostaia")
                
            # ✅ Tentativa 3: Campo 'texto'
            elif hasattr(resposta, 'texto') and resposta.texto:
                texto_resposta = resposta.texto
                logger.debug(f"✅ [BRAIN] Extraído via .texto")
                
            # ✅ Tentativa 4: Campo 'conteudo'
            elif hasattr(resposta, 'conteudo') and resposta.conteudo:
                texto_resposta = resposta.conteudo
                logger.debug(f"✅ [BRAIN] Extraído via .conteudo")
                
            # ✅ Tentativa 5: Se for dicionário
            elif isinstance(resposta, dict):
                texto_resposta = (
                    resposta.get('resposta_ia') or 
                    resposta.get('respostaia') or 
                    resposta.get('texto') or 
                    resposta.get('conteudo') or 
                    resposta.get('resposta')
                )
                logger.debug(f"✅ [BRAIN] Extraído de dict")
            
            # ❌ Último recurso: Extrair da string do objeto
            if not texto_resposta:
                texto_str = str(resposta)
                logger.warning(f"⚠️ [BRAIN] Extraindo da string: {texto_str[:100]}...")
                
                import re
                
                # Provar padrão 1: resposta_ia='...'
                match = re.search(r"resposta_ia=['\"]([^'\"]*)['\"]", texto_str)
                if match:
                    texto_resposta = match.group(1)
                else:
                    # Provar padrão 2: respostaia='...'
                    match = re.search(r"respostaia=['\"]([^'\"]*)['\"]", texto_str)
                    if match:
                        texto_resposta = match.group(1)
                    else:
                        # Nada encontrado - usar string truncada
                        texto_resposta = texto_str[:500]
                        if len(texto_str) > 500:
                            texto_resposta += "..."
            
            # Garantir que temos uma string válida
            if not texto_resposta:
                texto_resposta = "(resposta vazia)"
            elif not isinstance(texto_resposta, str):
                texto_resposta = str(texto_resposta)
            
            # =================================================================
            # 5. DETERMINAR TIPO DE RESPOSTA
            # =================================================================
            
            tipo_resposta = TipoResposta.CONVERSA  # Padrão
            
            if hasattr(resposta, 'acao_executada') and resposta.acao_executada:
                tipo_resposta = self._mapear_tipo(resposta.acao_executada)
            elif hasattr(resposta, 'tipo') and resposta.tipo:
                try:
                    tipo_resposta = TipoResposta(resposta.tipo)
                except ValueError:
                    tipo_resposta = TipoResposta.CONVERSA
            
            # Log de sucesso
            logger.info(
                f"✅ [BRAIN] Resposta gerada ({len(texto_resposta)} chars, "
                f"tipo: {tipo_resposta.value})"
            )
            
            # ✅ RETORNO SEGARANTE (sempre chega aqui!)
            return (tipo_resposta, texto_resposta)
            
        except Exception as erro_processamento:
            logger.error(f"❌ [BRAIN] Erro ao processar mensagem: {erro_processamento}", exc_info=True)
            
            # ✅ RETORNO SEGURO (mesmo com exceção!)
            return (
                TipoResposta.ERRO,
                f"Ops! Algo deu errado aqui... 😅\n\n"
                f"Erro: `{str(erro_processamento)[:100]}`\n\n"
                f"Tenta mandar de novo?"
            )  
    
    # =========================================================================
    # MÉTODO PRINCIPAL: processar_mensagem()
    # =========================================================================
    
    async def processar_mensagem_com_streaming(
        self,
        mensagem: str,
        update: Update,
        context: CallbackContext
    ) -> Tuple[TipoResposta, str]:
        """
        Versão com STREAMING VISUAL (texto aparece aos poucos).
        
        UX: Usuário vê "Lex está digitando..." → texto vai aparecendo
        """
        usuario_id = update.effective_user.id
        
        logger.info(f"💬 [STREAMING] Processando: '{mensagem[:30]}...'")
        
        try:
            # 1. Enviar mensagem inicial "pensando..."
            msg_status = await update.message.reply_text(
                "🤔 *Lex está pensando...*",
                parse_mode='Markdown'
            )
            
            # 2. Obter orquestrador/brain
            orchestrator = obter_orchestrator_global()
            if not orchestrator:
                await msg_status.edit_text("❌ Cérebro indisponível")
                return (TipoResposta.ERRO, "Erro")
            
            # 3. Processar com streaming (se Gemini disponível)
            texto_final = ""
            
            # Verificar se tem Gemini client no LLM
            tem_streaming = (
                hasattr(orchestrator, 'llm_client') and 
                orchestrator.llm_client is not None and
                hasattr(orchestrator.llm_client, '_gemini_client') and
                orchestrator.llm_client._gemini_client is not None
            )
            
            if tem_streaming:
                # STREAMING REAL DO GEMINI!
                logger.info("🌊 Usando streaming Gemini...")
                
                prompt = orchestrator._construir_prompt(mensagem, {"usuario_id": usuario_id})
                
                import asyncio
                chunk_count = 0
                
                async for chunk in orchestrator.llm_client._gemini_client.gerar_stream_async(prompt):
                    texto_final += chunk
                    chunk_count += 1
                    
                    # Atualizar mensagem a cada 3-5 chunks (não em todos para não spammar API Telegram)
                    if chunk_count % 4 == 0:
                        try:
                            preview = texto_final[:4000]  # Limite Telegram
                            if len(texto_final) > 4000:
                                preview += "\n\n[...]"
                            await msg_status.edit_text(preview)
                        except:
                            pass  # Ignorar erros de edit (pode estar muito rápido)
                
            else:
                # Sem streaming: processar normal (mas rápido mesmo assim com Gemini!)
                logger.info("⚡ Processamento normal (rápido!)")
                tipo, texto = await self.processar_mensagem(mensagem, update, context)
                texto_final = texto
            
            # 4. Edição final (mensagem completa)
            try:
                await msg_status.edit_text(
                    texto_final[:4096],  # Limite máximo Telegram
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
            except:
                await msg_status.edit_text(texto_final[:4096])
            
            logger.info(f"✅ [STREAMING] Concluído ({len(texto_final)} chars)")
            
            return (TipoResposta.CONVERSA, texto_final)
            
        except Exception as e:
            logger.error(f"❌ [STREAMING] Erro: {e}", exc_info=True)
            return (TipoResposta.ERRO, f"Erro: {str(e)[:50]}")
    
    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================
    
    def _obter_orchestrator(self) -> Optional["BrainLLMOrchestrator"]:
        """Obtém instância do orchestrator (global ou local)."""
        
        # Tentar pegar do singleton global primeiro
        try:
            from engine.brain_llm_orchestrator import obter_orchestrator_global  # ✅ CORRETO!
            orch = obter_orchestrator_global()  # ✅ CORRETO!
            if orch:
                return orch
        except Exception:
            pass
        
        return self._orchestrator
    
    def definir_orchestrador(self, orchestrator: "BrainLLMOrchestrator"):
        """Define instância local do orchestrator."""
        self._orchestrator = orchestrator
        logger.info("✅ [v3.0] Orchestrador definido no Handler")
    
    def _mapear_tipo(self, acao_executada: str) -> TipoResposta:
        """Mapeia ação executada para TipoResposta."""
        mapeamento = {
            "conversar": TipoResposta.CONVERSA,
            "criar_tarefa": TipoResposta.TAREFA_CRIADA,
            "criar_nota": TipoResposta.NOTA_CRIADA,
            "buscar_info": TipoResposta.BUSCA_REALIZADA,
            "gerar_ideias": TipoResposta.CONVERSA,
            "status_painel": TipoResposta.CONVERSA,
            "erro": TipoResposta.ERRO
        }
        return mapeamento.get(acao_executada, TipoResposta.CONVERSA)


# =============================================================================
# FUNÇÕES GLOBAIS (compatibilidade com código existente)
# =============================================================================

def definir_brain_middleware_global(instance):
    """
    Função de compatibilidade - define o orchestrator como global.
    
    Na v3.0, isso define o BrainLLMOrchestrator como global.
    Mantido por compatibilidade com código existente.
    """
    try:
        from engine.brain_llm_orchestrator import definir_orchestrador_global
        definir_orchestrador_global(instance)
        logger.info("✅ [COMPAT] Brain Middleware Global definido (v3.0)")
    except Exception as e:
        logger.error(f"❌ [COMPAT] Erro definindo global: {e}")


# =============================================================================
# TESTE RÁPIDO
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 TESTE DO TELEGRAM BRAIN HANDLER v3.0")
    print("=" * 60 + "\n")
    
    handler = BrainHandler()
    print(f"✅ BrainHandler v3.0 criado")
    print(f"🧠 Modo: LLM-First (GLM5)")
    print(f"📊 Disponibilidade: {'✅ ATIVA' if BRAIN_DISPONIVEL else '❌ INATIVA'}")