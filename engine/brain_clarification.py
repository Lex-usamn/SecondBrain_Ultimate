"""
================================================================================
BRAIN CLARIFICATION SYSTEM v3.3 - Sistema de Clarificação Inteligente
================================================================================

Responsável por:
- Salvar/recuperar estados de clarificação pendente
- Processar respostas do usuário (sim/não/tarefa/nota/cancela)
- Entender português coloquial e erros de digitação
- Evitar loop infinito de perguntas

AUTOR: Mago-Usamn | DATA: 16/04/2026
DEPENDÊNCIAS: brain_types.py
================================================================================
"""

import logging
import unicodedata
from typing import Optional, Dict, Any
from datetime import datetime

from engine.brain_types import (
    logger_brain,
    RespostaBrain,
    NOME_ASSISTENTE_DISPLAY
)


class BrainClarificationSystem:
    """
    Sistema de Clarificação v3.3.
    
    Gerencia o fluxo de confirmação quando o bot precisa saber
    se usuário quer TAREFA ou NOTA (ou outras decisões).
    
    Uso:
        clarification = BrainClarificationSystem()
        clarification.salvar_pendente(usuario_id, dados)
        resposta = clarification.processar_resposta(mensagem, usuario_id)
    """
    
    def __init__(self):
        self._clarificacoes_dict: Dict[int, Dict[str, Any]] = {}
        logger_brain.info("✅ [CLARIFICAÇÃO] BrainClarificationSystem inicializado")
    
    def salvar_pendente(
        self, 
        usuario_id: Optional[int], 
        dados_clarificacao: dict
    ) -> None:
        """Salva estado de clarificação para um usuário."""
        if not usuario_id:
            return
        
        self._clarificacoes_dict[usuario_id] = dados_clarificacao
        logger_brain.info(
            f"📝 [CLARIFICAÇÃO] Salva para user {usuario_id}: "
            f"{dados_clarificacao.get('acao_original')}"
        )
    
    def obter_pendente(self, usuario_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """Obtem clarificação pendente de um usuário."""
        if not usuario_id:
            return None
        
        return self._clarificacoes_dict.get(usuario_id)
    
    def tem_pendente(self, usuario_id: Optional[int]) -> bool:
        """Verifica se há clarificação pendente para o usuário."""
        if not usuario_id:
            return False
        
        return usuario_id in self._clarificacoes_dict
    
    def limpar_pendente(self, usuario_id: int) -> None:
        """Remove clarificação pendente (após confirmar/cancelar)."""
        if usuario_id in self._clarificacoes_dict:
            del self._clarificacoes_dict[usuario_id]
            logger_brain.info(f"🗑️ [CLARIFICAÇÃO] Limpa para user {usuario_id}")
    
    def processar_resposta(
        self, 
        mensagem: str, 
        usuario_id: int,
        executar_acao_callback=None  # Callback para executar ação após confirmar
    ) -> Optional[RespostaBrain]:
        """
        Processa resposta do usuário a uma clarificação pendente.
        
        v3.3 - MELHORADO: Entende português coloquial e erros de digitação!
        
        Args:
            mensagem: Texto da resposta do usuário
            usuario_id: ID do Telegram do usuário
            executar_acao_callback: Função para executar(decisao, msg, contexto)
                                   Se None, retorna RespostaBrain genérica
        
        Returns:
            RespostaBrain com resultado, ou None se não havia clarificação
        """
        
        clarificacao = self.obter_pendente(usuario_id)
        
        if not clarificacao:
            logger_brain.warning(
                f"⚠️ [CLARIFICAÇÃO] Não há clarificação pendente para user {usuario_id}"
            )
            return None
        
        logger_brain.info(f"💬 [CLARIFICAÇÃO] Processando resposta: '{mensagem}'")
        
        # Normalizar mensagem (minúsculas, remover acentos extras, espaços)
        msg_lower = mensagem.lower().strip()
        msg_normalized = unicodedata.normalize('NFKD', msg_lower).encode(
            'ASCII', 'ignore'
        ).decode('ASCII')
        
        # =====================================================================
        # 1. CANCELAMENTO (palavras claras de negação)
        # =====================================================================
        if self._eh_cancelamento(msg_normalized):
            self.limpar_pendente(usuario_id)
            
            return RespostaBrain(
                sucesso=True,
                acao_executada="cancelado",
                resposta_ia="👍 *Beleza, cancelado!* Se precisar de algo, é só chamar! 😊",
                aguardando_resposta=False,
                clarificacao_pendente=False
            )
        
        # =====================================================================
        # 2. USUÁRIO DISSE O TIPO DIRETO! (nota / tarefa / lembrete)
        # =====================================================================
        
        # Verificar NOTA
        if self._eh_escolha_nota(msg_normalized):
            return self._processar_escolha_nota(
                usuario_id, clarificacao, mensagem, executar_acao_callback
            )
        
        # Verificar TAREFA
        if self._eh_escolha_tarefa(msg_normalized):
            return self._processar_escolha_tarefa(
                usuario_id, clarificacao, mensagem, executar_acao_callback
            )
        
        # =====================================================================
        # 3. CONFIRMAÇÃO GERAL (sim / ok / blz / claro / pode / vai / etc.)
        # =====================================================================
        
        if self._eh_confirmacao_geral(msg_normalized):
            return self._processar_confirmacao(
                usuario_id, clarificacao, mensagem, executar_acao_callback
            )
        
        # =====================================================================
        # 4. NÃO ENTENDEU → Repetir opções de forma mais amigável
        # =====================================================================
        
        return self._resposta_nao_entendido(clarificacao, mensagem)
    
    # =========================================================================
    # MÉTODOS PRIVADOS DE DETECÇÃO DE INTENÇÃO
    # =========================================================================
    
    def _eh_cancelamento(self, msg: str) -> bool:
        """Detecta intenção de cancelamento."""
        palavras_cancelar = [
            "cancela", "cancelar", "esquece", "ignora", 
            "deixa", "nao", "não", "nem", "esquece", "deixa pra la",
            "desiste", "desistir", "apaga"
        ]
        
        return any(p in msg for p in palavras_cancelar)
    
    def _eh_escolha_nota(self, msg: str) -> bool:
        """Detecta quando usuário escolhe NOTA."""
        padroes_nota = [
            "nota", "anotar", "anota", "so nota", "só nota", "apenas nota",
            "nota so", "nota só", "so anotar", "só anotar", "registra",
            "registrar", "guarda", "guardar", "lembrete", "rascunho",
            "nao e tarefa", "não é tarefa", "nao tarefa", "notar",
            "so uma nota", "só uma nota", "apenas uma nota", "nota mesmo",
            "so nota memso", "só nota mesmo"  # ✅ Erros de digitação comuns!
        ]
        
        return any(p in msg for p in padroes_nota)
    
    def _eh_escolha_tarefa(self, msg: str) -> bool:
        """Detecta quando usuário escolhe TAREFA."""
        padroes_tarefa = [
            "tarefa", "task", "to-do", "todo", "agenda", "compromisso",
            "lembra", "lembrar", "prazo", "deadline", "agendar",
            "colocar na agenda", "criar tarefa", "nova tarefa"
        ]
        
        return any(p in msg for p in padroes_tarefa)
    
    def _eh_confirmacao_geral(self, msg: str) -> bool:
        """Detecta confirmação geral (sim/ok/blz/etc)."""
        palavras_confirmar = [
            "sim", "yes", "y", "ok", "blz", "blaza", "beleza",
            "claro", "certo", "confirmar", "pode", "vai", 
            "pode ir", "pode criar", "cria", "feito", "por favor",
            "pfv", "fav", "favor", "ta bom", "tá bom", "ta bem",
            "tá bem", "ok then", "isso", "continue", "seguinte",
            "prossegue", "manda", "bora", "vamos", "vambora"
        ]
        
        return any(p in msg for p in palavras_confirmar)
    
    # =========================================================================
    # MÉTODOS PRIVADOS DE PROCESSAMENTO
    # =========================================================================
    
    def _processar_escolha_nota(
        self, 
        usuario_id: int, 
        clarificacao: dict,
        mensagem: str,
        callback=None
    ) -> RespostaBrain:
        """Processa quando usuário escolheu NOTA."""
        
        self.limpar_pendente(usuario_id)
        
        decisao_original = clarificacao.get("decisao_completa", {})
        decisao_original["acao"] = "criar_nota"
        
        logger_brain.info(f"✅ [CLARIFICAÇÃO] Usuário escolheu NOTA (direto!)")
        
        # Tentar executar via callback
        if callback:
            resultado = callback(
                decisao_original, 
                clarificacao.get("mensagem_original", mensagem),
                clarificacao.get("contexto", {})
            )
            
            if resultado:
                resultado.resposta_ia = "📝 *Nota salva!*\n\n" + resultado.resposta_ia
                return resultado
        
        # Fallback sem callback
        return RespostaBrain(
            sucesso=True,
            acao_executada="criar_nota",
            resposta_ia=(
                f"📝 *Anotei!* "
                f"Salvei como nota: \"{clarificacao.get('mensagem_original', mensagem)}\""
            ),
            aguardando_resposta=False,
            clarificacao_pendente=False
        )
    
    def _processar_escolha_tarefa(
        self, 
        usuario_id: int, 
        clarificacao: dict,
        mensagem: str,
        callback=None
    ) -> RespostaBrain:
        """Processa quando usuário escolheu TAREFA."""
        
        self.limpar_pendente(usuario_id)
        
        decisao_original = clarificacao.get("decisao_completa", {})
        decisao_original["acao"] = "criar_tarefa"
        
        logger_brain.info(f"✅ [CLARIFICAÇÃO] Usuário escolheu TAREFA (direto!)")
        
        if callback:
            resultado = callback(decisao_original, mensagem, clarificacao.get("contexto", {}))
            
            if resultado:
                resultado.resposta_ia = "✅ *Tarefa criada!*\n\n" + resultado.resposta_ia
                return resultado
        
        return RespostaBrain(
            sucesso=True,
            acao_executada="criar_tarefa",
            resposta_ia=f"✅ *Tarefa criada!* \"{clarificacao.get('mensagem_original', mensagem)}\"",
            aguardando_resposta=False,
            clarificacao_pendente=False
        )
    
    def _processar_confirmacao(
        self, 
        usuario_id: int, 
        clarificacao: dict,
        mensagem: str,
        callback=None
    ) -> RespostaBrain:
        """Processa confirmação geral (usuário disse 'sim')."""
        
        self.limpar_pendente(usuario_id)
        
        decisao_original = clarificacao.get("decisao_completa", {})
        mensagem_original = clarificacao.get("mensagem_original", mensagem)
        contexto_original = clarificacao.get("contexto", {})
        
        acao_pendente = clarificacao.get('acao_original', 'desconhecido')
        logger_brain.info(f"✅ [CLARIFICAÇÃO] Usuário CONFIRMOU → Executando {acao_pendente}")
        
        if callback:
            resultado = callback(decisao_original, mensagem_original, contexto_original)
            
            if resultado:
                prefixos = {
                    "criar_nota": "📝 *Nota salva!*",
                    "criar_tarefa": "✅ *Tarefa criada!*",
                    "buscar_info": "🔍 *Resultado da busca:*",
                    "conversar": ""
                }
                prefixo = prefixos.get(acao_pendente, "✅ *Pronto!*")
                resultado.resposta_ia = f"{prefixo}\n\n{resultado.resposta_ia}"
                return resultado
        
        return RespostaBrain(
            sucesso=True,
            acao_executada=acao_pendente,
            resposta_ia=f"✅ *Criado com sucesso!* {mensagem_original}",
            aguardando_resposta=False,
            clarificacao_pendente=False
        )
    
    def _resposta_nao_entendido(self, clarificacao: dict, mensagem: str) -> RespostaBrain:
        """Gera resposta quando não entendeu o usuário."""
        
        acao_sugerida = clarificacao.get('acao_original', 'criar')
        msg_original = clarificacao.get('mensagem_original', 'isso')
        
        return RespostaBrain(
            sucesso=True,
            acao_executada="clarificacao_repetir",
            resposta_ia=f"""🤔 *Hmm, não entendi muito bem...*

Você disse: "{mensagem}"

Eu tenho aqui para registrar: *"{msg_original}"*

💡 *Me diga assim:*
• `nota` → Salvar como nota rápida
• `tarefa` → Criar tarefa com prazo  
• `sim` → Confirmar como {acao_sugerida}
• `cancela` → Desistir

Como prefere?""",
            aguardando_resposta=True,
            clarificacao_pendente=True
        )
    
    def gerar_mensagem_clarificacao(
        self, 
        acao_decidida: str, 
        conteudo: str
    ) -> str:
        """Gera mensagem de clarificação padrão."""
        
        conteudo_curto = conteudo[:60] + ("..." if len(conteudo) > 60 else "")
        tipo_display = (
            "TAREFA (com lembrete/prazo)" 
            if acao_decidida == "criar_tarefa" 
            else "NOTA simples"
        )
        
        return f"""🤔 *Deixa eu ver se entendi...*

Você quer registrar: **{conteudo_curto}**

📋 *Quer criar uma {tipo_display}?*

💡 *Responda:*
• `sim` → Confirmar criação
• `tarefa` → Se for tarefa com prazo
• `nota` → Se for só anotar
• `cancela` → Desistir"""


# =============================================================================
# INSTÂNCIA GLOBAL (para uso fácil pelo orchestrator)
# =============================================================================

_clarification_global: Optional[BrainClarificationSystem] = None


def obter_clarification_system() -> BrainClarificationSystem:
    global _clarification_global
    
    if _clarification_global is None:
        _clarification_global = BrainClarificationSystem()
    
    return _clarification_global