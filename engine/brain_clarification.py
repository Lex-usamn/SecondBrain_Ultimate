"""
================================================================================
BRAIN ORCHESTRATOR - Sistema de Clarificação (v3.1)
================================================================================

AUTOR: Mago-Usamn

Módulo que gerencia as perguntas pendentes e dúvidas da IA.
Resolve o comportamento de quando a IA não sabe se o usuário
quer uma Tarefa ou uma Nota, guardando o estado e processando a resposta.
"""

import logging
from typing import Optional, Dict, Any

from engine.brain_types import logger_brain, RespostaBrain
from engine.brain_acoes import ExecutorAcoes

class BrainClarificacao:
    """Gerenciador de Estado de Clarificação."""
    
    def __init__(self, executor_acoes: ExecutorAcoes):
        self._clarificacoes_dict: Dict[int, Dict[str, Any]] = {}
        self._executor = executor_acoes
        
    def salvar_pendente(self, usuario_id: Optional[int], dados_clarificacao: dict) -> None:
        """Salva estado de clarificação para um usuário."""
        if not usuario_id:
            return
        
        self._clarificacoes_dict[usuario_id] = dados_clarificacao
        logger_brain.info(f"📝 [CLARIFICAÇÃO] Salva para user {usuario_id}: {dados_clarificacao.get('acao_original')}")

    def obter_pendente(self, usuario_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """Obtem clarificação pendente de um usuário."""
        if not usuario_id:
            return None
        return self._clarificacoes_dict.get(usuario_id)

    def processar_resposta(self, mensagem: str, usuario_id: int) -> Optional[RespostaBrain]:
        """
        Processa resposta do usuário a uma clarificação pendente.
        Compreende linguagem coloquial e acionamentos (cancelamento, confirmação).
        """
        clarificacao = self.obter_pendente(usuario_id)
        
        if not clarificacao:
            logger_brain.warning(f"⚠️ [CLARIFICAÇÃO] Não há clarificação pendente para user {usuario_id}")
            return None
        
        logger_brain.info(f"💬 [CLARIFICAÇÃO] Processando resposta: '{mensagem}'")
        
        msg_lower = mensagem.lower().strip()
        import unicodedata
        msg_normalized = unicodedata.normalize('NFKD', msg_lower).encode('ASCII', 'ignore').decode('ASCII')
        
        # =====================================================================
        # 1. CANCELAMENTO
        # =====================================================================
        palavras_cancelar = [
            "cancela", "cancelar", "esquece", "ignora", 
            "deixa", "nao", "não", "nem", "deixa pra la",
            "desiste", "desistir", "apaga"
        ]
        
        if any(palavra in msg_normalized for palavra in palavras_cancelar):
            if usuario_id in self._clarificacoes_dict:
                del self._clarificacoes_dict[usuario_id]
            
            return RespostaBrain(
                sucesso=True,
                acao_executada="cancelado",
                resposta_ia="👍 *Beleza, cancelado!* Se precisar de algo, é só chamar! 😊",
                aguardando_resposta=False,
                clarificacao_pendente=False
            )
        
        # =====================================================================
        # 2. TIPO DIRETO (nota / tarefa)
        # =====================================================================
        padroes_nota = [
            "nota", "anotar", "anota", "so nota", "só nota", "apenas nota",
            "nota so", "nota só", "so anotar", "só anotar", "registra",
            "registrar", "guarda", "guardar", "lembrete", "rascunho",
            "nao e tarefa", "nao tarefa", "notar"
        ]
        
        padroes_tarefa = [
            "tarefa", "task", "to-do", "todo", "agenda", "compromisso",
            "lembra", "lembrar", "prazo", "deadline", "agendar",
            "colocar na agenda", "criar tarefa", "nova tarefa"
        ]
        
        # NOTA
        if any(padrao in msg_normalized for padrao in padroes_nota):
            if usuario_id in self._clarificacoes_dict:
                del self._clarificacoes_dict[usuario_id]
            
            decisao_original = clarificacao.get("decisao_completa", {})
            decisao_original["acao"] = "criar_nota"
            
            logger_brain.info(f"✅ [CLARIFICAÇÃO] Usuário escolheu NOTA")
            resultado = self._executor.executar(
                decisao_original, 
                clarificacao.get("mensagem_original", mensagem),
                clarificacao.get("contexto", {})
            )
            
            if resultado:
                resultado.resposta_ia = "📝 *Nota salva!*\n\n" + resultado.resposta_ia
                return resultado
            return RespostaBrain(
                sucesso=True, acao_executada="criar_nota",
                resposta_ia=f"📝 *Anotei!* Salvei como nota.",
                aguardando_resposta=False, clarificacao_pendente=False
            )
        
        # TAREFA
        if any(padrao in msg_normalized for padrao in padroes_tarefa):
            if usuario_id in self._clarificacoes_dict:
                del self._clarificacoes_dict[usuario_id]
            
            decisao_original = clarificacao.get("decisao_completa", {})
            decisao_original["acao"] = "criar_tarefa"
            
            logger_brain.info(f"✅ [CLARIFICAÇÃO] Usuário escolheu TAREFA")
            resultado = self._executor.executar(
                decisao_original, mensagem, clarificacao.get("contexto", {})
            )
            
            if resultado:
                resultado.resposta_ia = "✅ *Tarefa criada!*\n\n" + resultado.resposta_ia
                return resultado
            return RespostaBrain(
                sucesso=True, acao_executada="criar_tarefa",
                resposta_ia=f"✅ *Tarefa criada!*",
                aguardando_resposta=False, clarificacao_pendente=False
            )
        
        # =====================================================================
        # 3. CONFIRMAÇÃO GERAL (sim / ok)
        # =====================================================================
        palavras_confirmar = [
            "sim", "yes", "y", "ok", "blz", "blaza", "beleza",
            "claro", "certo", "confirmar", "pode", "vai", 
            "pode ir", "pode criar", "cria", "feito", "por favor",
            "pfv", "fav", "favor", "ta bom", "tá bom", "ta bem",
            "tá bem", "ok then", "isso", "continue", "seguinte",
            "prossegue", "manda", "bora", "vamos", "vambora"
        ]
        
        if any(palavra in msg_normalized for palavra in palavras_confirmar):
            if usuario_id in self._clarificacoes_dict:
                del self._clarificacoes_dict[usuario_id]
            
            decisao_original = clarificacao.get("decisao_completa", {})
            mensagem_original = clarificacao.get("mensagem_original", mensagem)
            contexto_original = clarificacao.get("contexto", {})
            acao_pendente = clarificacao.get('acao_original', 'desconhecido')
            
            logger_brain.info(f"✅ [CLARIFICAÇÃO] Usuário CONFIRMOU → {acao_pendente}")
            
            resultado = self._executor.executar(decisao_original, mensagem_original, contexto_original)
            
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
                sucesso=True, acao_executada=acao_pendente,
                resposta_ia=f"✅ *Criado com sucesso!*",
                aguardando_resposta=False, clarificacao_pendente=False
            )
        
        # =====================================================================
        # 4. NÃO ENTENDEU
        # =====================================================================
        return RespostaBrain(
            sucesso=True, acao_executada="clarificacao_repetir",
            resposta_ia=f"🤔 *Hmm, não entendi muito bem...*\n\nVocê disse: \"{mensagem}\"\n\n💡 *Opções válidas:*\n• `sim` → Criar conforme sugerido\n• `tarefa` → Criar como TAREFA\n• `nota` → Criar como NOTA\n• `cancela` → Desistir\n\nComo prefere?",
            aguardando_resposta=True, clarificacao_pendente=True
        )
