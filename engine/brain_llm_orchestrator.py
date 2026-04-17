"""
================================================================================
BRAIN LLM ORCHESTRATOR v3.5 - IA Conversacional REAL
================================================================================

AUTOR: Mago-Usamn

FILOSOFIA:
- A IA (Gemini) é o CÉREBRO principal
- O Orchestrator é o Maestro (Delega para LexFlowConnector, ExecutorAcoes, BrainClarificacao)
- Contexto carregado dos arquivos .md (SOUL, USER, MEMORY, HEARTBEAT)
- Conversa NATURAL
================================================================================
"""

import os
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any, List
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from engine.rag_system import RAGSystem
    from engine.llm_client import LLMClient
    from integrations.lex_flow_definitivo import LexFlowClient

from engine.brain_types import logger_brain, RespostaBrain
from engine.brain_lexflow_connector import LexFlowConnector
from engine.brain_acoes import ExecutorAcoes
from engine.brain_clarification import BrainClarificacao
from engine.brain_prompts import construir_prompt_mestre, parsear_resposta_llm

@dataclass
class MensagemContextualizada:
    """Mensagem enriquecida com contexto dos arquivos .md."""
    mensagem_original: str
    mensagem_usuario: str
    contexto_soul: str = ""
    contexto_user: str = ""
    contexto_memory: str = ""
    contexto_heartbeat: str = ""
    historico_conversa: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class BrainLLMOrchestrator:
    """
    ORQUESTRADOR BASEADO EM LLM - IA Conversacional Real.
    """
    
    def __init__(self):
        self._llm = None
        self._rag = None
        self._context_loader = None
        
        # Módulos Delegados
        self.conector_lexflow = LexFlowConnector()
        self.executor_acoes = None
        self.clarificador = None
        
        self._contextos_cache: Dict[str, str] = {
            "soul": "", "user": "", "memory": "", "heartbeat": ""
        }
        
        self._conversas: Dict[int, List[Dict[str, str]]] = {}
        self._ultima_atualizacao: Optional[datetime] = None
        self._cache_validade_horas = 1
        
        self._inicializado = False
        logger_brain.info("[v3.5] BrainLLMOrchestrator instanciado (MODULARIZADO)")
    
    def inicializar(self, llm_client=None, rag_system=None, 
                    lexflow_client=None, context_loader=None) -> bool:
        """Inicializa o orquestrador com dependências."""
        try:
            self._llm = llm_client
            self._rag = rag_system
            self._context_loader = context_loader
            
            # Inicializando módulos dependentes
            self.conector_lexflow.inicializar(lexflow_client)
            self.executor_acoes = ExecutorAcoes(self.conector_lexflow, self._llm, self._rag)
            self.clarificador = BrainClarificacao(self.executor_acoes)
            
            logger_brain.info(f"[v3.5] Dependências recebidas e injetadas.")
            
            if self.conector_lexflow.esta_conectado:
                logger_brain.info(f"[v3.5] ✅ LEX FLOW CONECTADO!")
            else:
                logger_brain.warning(f"[v3.5] ⚠️ Lex Flow indisponível.")
            
            self._atualizar_todos_contextos()
            self._inicializado = True
            logger_brain.info("[v3.5] Orquestrador PRONTO!")
            return True
        except Exception as e:
            logger_brain.error(f"[v3.5] Erro na inicialização: {e}", exc_info=True)
            return False

    def processar(self, mensagem: str, contexto: Optional[Dict[str, Any]] = None) -> RespostaBrain:
        """Processa mensagem usando IA REAL e delega ações se necessário."""
        usuario_id = contexto.get("usuario_id") if contexto else None
        nome_usuario = contexto.get("nome", "Usuário") if contexto else "Usuário"
        
        logger_brain.info(f"[v3.5] Processando: '{mensagem[:50]}...'")
        
        try:
            # 1. Preparar contextos
            msg_ctx = self._preparar_mensagem_contextualizada(mensagem, usuario_id, nome_usuario)
            
            # 2. Obter dados da área de trabalho (Inbox Local) assegurando reconexão
            inbox_text = ""
            if self.conector_lexflow.garantir_conectado():
                inbox = self.conector_lexflow.get_inbox_robusto()
                if inbox and isinstance(inbox, list):
                    inbox_lines = []
                    for i, item in enumerate(inbox[:10], 1):
                        if isinstance(item, dict):
                            titulo = item.get('title', item.get('nome', 'Sem título'))
                            conteudo = str(item.get('content', '')).replace('\n', ' ')[:80]
                            inbox_lines.append(f"  {i}. 📝 {titulo}\n     └─ {conteudo}")
                    inbox_text = "\n".join(inbox_lines) if inbox_lines else "[Caixa de Entrada vazia]"
            else:
                inbox_text = "[Lex Flow indisponível]"
                
            # 3. Chamar IA
            prompt_mestre = construir_prompt_mestre(msg_ctx, inbox_text)
            resposta_llm_raw = self._llm.gerar(prompt_mestre)
            decisao = parsear_resposta_llm(resposta_llm_raw.conteudo)
            
            acao_decidida = decisao.get("acao", "conversar")
            logger_brain.info(f"🎯 IA decidiu: acao={acao_decidida}")
            
            # 4. Clarificação Explícita (v3.8 - MELHORADO!)
            if acao_decidida in ["criar_tarefa", "criar_nota"]:
                msg_lower = mensagem.lower().strip()
                
                # Detectar tipo pelo COMANDO explícito
                comeca_com_anota = any([msg_lower.startswith(p) for p in ["anota:", "nota:", "anota ", "nota "]])
                comeca_com_tarefa = any([msg_lower.startswith(p) for p in ["tarefa:", "tarefa ", "lembra:", "lembrar"]])
                
                # Detectar palavras-chave no meio da frase
                tem_nota = any(p in msg_lower for p in ["nota", "anotar", "anota", "registrar", "rascunho"])
                tem_tarefa = any(p in msg_lower for p in ["tarefa", "lembrete", "agenda", "prazo", "to-do"])
                
                # v3.8: Comandos ÓBVIOS → EXECUTAR DIRETO (sem perguntar!)
                if comeca_com_anota or (tem_nota and not tem_tarefa):
                    decisao["acao"] = "criar_nota"
                    logger_brain.info(f"⚡ [v3.8] COMANDO ÓBVIO → criar_nota (sem clarificação)")
                    resultado = self.executor_acoes.executar(decisao, mensagem, contexto)
                    if resultado:
                        return resultado
                    return RespostaBrain(sucesso=True, acao_executada="criar_nota", 
                                        resposta_ia=f"📝 *Nota salva!*", 
                                        aguardando_resposta=False, clarificacao_pendente=False)
                
                if comeca_com_tarefa or (tem_tarefa and not tem_nota):
                    decisao["acao"] = "criar_tarefa"
                    logger_brain.info(f"⚡ [v3.8] COMANDO ÓBVIO → criar_tarefa (sem clarificação)")
                    resultado = self.executor_acoes.executar(decisao, mensagem, contexto)
                    if resultado:
                        return resultado
                    return RespostaBrain(sucesso=True, acao_executada="criar_tarefa",
                                        resposta_ia=f"✅ *Tarefa criada!*",
                                        aguardando_resposta=False, clarificacao_pendente=False)
                
                # Só perguntar se NÃO for óbvio
                comando_obvio = any([
                    msg_lower.startswith(("anota:", "nota:", "tarefa:", "lembrar", "lembra")),
                    ":" in msg_lower[:15] and len(msg_lower) > 15
                ])
                
                if not comando_obvio:
                    conteudo = decisao.get("entidades", {}).get("conteudo", mensagem)[:60]
                    tipo = "TAREFA (com lembrete/prazo)" if acao_decidida == "criar_tarefa" else "NOTA simples"
                    resposta_clarificacao = f"🤔 *Deixa eu ver se entendi...*\n\nVocê quer registrar: **{conteudo}...**\n\n📋 *Quer criar uma {tipo}?*\n\n💡 *Responda:*\n• `sim` → Confirmar criação\n• `tarefa` → Se for tarefa com prazo\n• `nota` → Se for só anotar\n• `cancela` → Desistir"
                    
                    self.clarificador.salvar_pendente(usuario_id, {
                        "acao_original": acao_decidida, 
                        "decisao_completa": decisao, 
                        "mensagem_original": mensagem, 
                        "contexto": contexto
                    })
                    return RespostaBrain(sucesso=True, acao_executada="clarificacao", 
                                        resposta_ia=resposta_clarificacao, 
                                        aguardando_resposta=True, 
                                        clarificacao_pendente=True) 
            # 5. Execução Plena
            if acao_decidida and acao_decidida not in ["conversar", "clarificacao"]:
                resultado_acao = self.executor_acoes.executar(decisao, mensagem, contexto)
                if resultado_acao:
                    self._salvar_no_historico(usuario_id, mensagem, resultado_acao.resposta_ia)
                    return resultado_acao
            
            # 6. Fallback de conversa
            resposta_final = decisao.get("resposta", resposta_llm_raw.conteudo)
            self._salvar_no_historico(usuario_id, mensagem, resposta_final)
            return RespostaBrain(sucesso=True, acao_executada=decisao.get("acao", "conversar"), resposta_ia=resposta_final)
            
        except Exception as e:
            logger_brain.error(f"[v3.5] Erro no processamento: {e}", exc_info=True)
            return RespostaBrain(sucesso=False, acao_executada="erro", resposta_ia=f"Ops! Deu erro aqui: {str(e)[:50]}", erro=str(e))

    def processar_resposta_clarificacao(self, mensagem: str, usuario_id: int) -> Optional[RespostaBrain]:
        """Repassa a verificação de clarificações pendentes."""
        return self.clarificador.processar_resposta(mensagem, usuario_id)
        
    def obter_clarificacao_pendente(self, usuario_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """Helpers para retrocompatibilidade."""
        return self.clarificador.obter_pendente(usuario_id)

    def _atualizar_todos_contextos(self) -> None:
        """Carrega/atualiza todos os arquivos de contexto (.md)."""
        agora = datetime.now()
        if self._ultima_atualizacao and ((agora - self._ultima_atualizacao).total_seconds() / 3600) < self._cache_validade_horas:
            return
            
        try:
            if self._context_loader:
                contextos = self._context_loader.carregar_todos(forcar_reload=True)
                for chave, valor in contextos.items():
                    self._contextos_cache[chave] = valor if not valor.startswith("[Erro") and not valor.startswith("[Arquivo") else ""
            else:
                self._carregar_arquivos_direto()
            self._ultima_atualizacao = agora
        except Exception as e:
            logger_brain.warning(f"Erro carregando contextos: {e}")
            
    def _carregar_arquivos_direto(self) -> None:
        for chave, arq in {"soul": "SOUL.md", "user": "USER.md", "memory": "MEMORY.md", "heartbeat": "HEARTBEAT.md"}.items():
            cam = os.path.join(os.path.dirname(__file__), '..', arq)
            if os.path.exists(cam):
                with open(cam, 'r', encoding='utf-8') as f:
                    self._contextos_cache[chave] = f.read()
            else:
                self._contextos_cache[chave] = ""

    def _preparar_mensagem_contextualizada(self, mensagem: str, usuario_id: Optional[int], nome_usuario: str) -> MensagemContextualizada:
        self._atualizar_todos_contextos()
        historico = self._conversas.get(usuario_id, []) if usuario_id else []
        return MensagemContextualizada(
            mensagem_original=mensagem, mensagem_usuario=mensagem,
            contexto_soul=self._contextos_cache.get("soul", ""), contexto_user=self._contextos_cache.get("user", ""),
            contexto_memory=self._contextos_cache.get("memory", ""), contexto_heartbeat=self._contextos_cache.get("heartbeat", ""),
            historico_conversa=historico, metadata={"usuario_id": usuario_id, "nome_usuario": nome_usuario}
        )

    def _salvar_no_historico(self, usuario_id: Optional[int], mensagem_usuario: str, resposta_bot: str) -> None:
        if not usuario_id: return
        if usuario_id not in self._conversas: self._conversas[usuario_id] = []
        self._conversas[usuario_id].append({"role": "user", "texto": mensagem_usuario, "timestamp": datetime.now().isoformat()})
        self._conversas[usuario_id].append({"role": "assistant", "texto": resposta_bot[:300], "timestamp": datetime.now().isoformat()})
        if len(self._conversas[usuario_id]) > 20: self._conversas[usuario_id] = self._conversas[usuario_id][-20:]

    def limpar_conversa(self, usuario_id: int) -> None:
        if usuario_id in self._conversas: del self._conversas[usuario_id]

    def obter_estatisticas(self) -> Dict[str, Any]:
        return {
            "versao": "3.5 (LLM-FIRST MODULAR)",
            "inicializado": self._inicializado,
            "conversas_ativas": len(self._conversas),
            "contextos_carregados": {k: len(v) for k, v in self._contextos_cache.items()}
        }

_orchestrator_global: Optional[BrainLLMOrchestrator] = None

def obter_orchestrator_global() -> Optional[BrainLLMOrchestrator]:
    global _orchestrator_global
    return _orchestrator_global

def definir_orchestrator_global(instancia: BrainLLMOrchestrator) -> None:
    global _orchestrator_global
    _orchestrator_global = instancia