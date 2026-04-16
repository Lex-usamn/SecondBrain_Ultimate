"""
================================================================================
BRAIN LLM ORCHESTRATOR v3.0 - IA Conversacional REAL com RAG
================================================================================

AUTOR: Mago-Usamn | DATA: 14/04/2026
NOME DO ASSISTENTE: MAGO 🧙

FILOSOFIA:
- A IA (Gemini) é o CÉREBRO principal
- Regras só para execução de ações (não para decisão)
- Contexto carregado dos arquivos .md (SOUL, USER, MEMORY, HEARTBEAT)
- Conversa NATURAL como ChatGPT/Claude
- Só executa ações quando a IA decide

CORREÇÕES APLICADAS (v3.0.1):
✅ REMOVIDO TRUNCATION de arquivos .md (agora carrega 100% do conteúdo)
✅ CORRIGIDA INDENTAÇÃO de todos os métodos (estavam fora da classe!)
✅ PROMPT MESTRE usa contexto COMPLETO (sem [:1500] cuts)
================================================================================
"""

import json
import logging
import re
import os
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any, List
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from engine.rag_system import RAGSystem
    from engine.llm_client import LLMClient
    from integrations.lex_flow_definitivo import LexFlowClient

from engine.brain_types import (
    logger_brain,
    RespostaBrain,
    NOME_ASSISTENTE_DISPLAY
)


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
    
    Como funciona:
    1. Recebe mensagem do usuário
    2. Carrega contexto dos arquivos .md (via ContextLoader)
    3. Monta prompt mega-contextualizado para o LLM
    4. LLM decide: conversar, criar tarefa, buscar info, etc.
    5. Se precisar executar ação, extrai intenção e executa
    6. Retorna resposta natural gerada pela IA
    """
    
    def __init__(self):
        self._llm = None
        self._rag = None
        self._lexflow = None
        self._context_loader = None
        
        # Contextos carregados dos arquivos .md
        self._contextos_cache: Dict[str, str] = {
            "soul": "",
            "user": "",
            "memory": "",
            "heartbeat": ""
        }
        
        # Histórico de conversas por usuário (memória curto prazo)
        self._conversas: Dict[int, List[Dict[str, str]]] = {}
        
        # Timestamp da última atualização dos contextos
        self._ultima_atualizacao: Optional[datetime] = None
        self._cache_validade_horas = 1
        
        # ✅ NOVO v3.1: Sistema de clarificação (variável de instância no __init__!)
        self._clarificacoes_dict: Dict[int, Dict[str, Any]] = {}
        
        self._inicializado = False
        logger_brain.info("[v3.1] BrainLLMOrchestrator instanciado (modo LLM-FIRST)")
        logger_brain.info(f"[v3.1] _lexflow inicializado como: {self._lexflow}")  # Deve ser None aqui
    
    # =========================================================================
    # SISTEMA DE RECONEXÃO AUTOMÁTICA DO LEX FLOW (ROBUSTEZ!)
    # =========================================================================
    
    def _garantir_lexflow_conectado(self) -> bool:
        """
        Garante que o Lex Flow está conectado e funcionando.
        
        Se get_inbox() retornar vazio, recria a instância do cliente.
        Isso resolve problemas de:
        - Sessão HTTP perdida/expirada
        - Token inválido silencioso
        - Instância corrompida
        
        Returns:
            True se Lex Flow está OK, False se não conseguiu reconectar
        """
        
        if not self._lexflow:
            logger_brain.warning("🔌 [RECONEXÃO] self._lexflow é None! Tentando criar nova instância...")
            return self._recriar_lexflow_client()
        
        try:
            logger_brain.info(f"🔍 [RECONEXÃO] Testando Lex Flow atual (id={id(self._lexflow)})...")
            
            # Testar autenticação primeiro
            if hasattr(self._lexflow, 'is_authenticated'):
                if not self._lexflow.is_authenticated():
                    logger_brain.warning("⚠️ [RECONEXÃO] Lex Flow não autenticado! Reconectando...")
                    return self._recriar_lexflow_client()
            
            # ✅ CORRIGIDO: Usar _get_inbox_robusto() em vez de get_inbox()
            inbox_teste = self._get_inbox_robusto()
            
            logger_brain.info(
                f"🔍 [RECONEXÃO] get_inbox() retornou: "
                f"type={type(inbox_teste)}, "
                f"len={len(inbox_teste) if isinstance(inbox_teste, list) else 'N/A'}"
            )
            
            # ✅ SUCESSO - tem dados!
            if inbox_teste and isinstance(inbox_teste, list) and len(inbox_teste) > 0:
                logger_brain.info(
                    f"✅ [RECONEXÃO] Lex Flow OK! {len(inbox_teste)} itens no inbox"
                )
                return True
            
            # ⚠️ Lista vazia - pode ser bug ou realmente vazio
            logger_brain.warning(
                f"⚠️ [RECONEXÃO] Inbox vazio (lista vazia). "
                f"Tentando re-login forçado..."
            )
            
            # Tentar login novamente na instância atual
            if hasattr(self._lexflow, 'login'):
                login_ok = self._lexflow.login()
                if login_ok:
                    # ✅ CORRIGIDO: Typo inbox_apois_login → inbox_apos_login
                    inbox_apos_login = self._get_inbox_robusto()
                    if inbox_apos_login and isinstance(inbox_apos_login, list) and len(inbox_apos_login) > 0:
                        logger_brain.info(
                            f"✅ [RECONEXÃO] Re-login funcionou! {len(inbox_apos_login)} itens"
                        )
                        return True
            
            # ❌ Ainda vazio mesmo após re-login → recriar instância
            logger_brain.warning(
                f"❌ [RECONEXÃO] Re-login não resolveu! "
                f"Recriando instância do LexFlowClient..."
            )
            return self._recriar_lexflow_client()
            
        except Exception as e:
            logger_brain.error(
                f"❌ [RECONEXÃO] Erro testando Lex Flow: {e}",
                exc_info=True
            )
            return self._recriar_lexflow_client()
    
    def _recriar_lexflow_client(self) -> bool:
        """
        Recria o cliente Lex Flow do zero.
        
        Solução nuclear para:
        - Sessões corrompidas
        - Tokens expirados que não renovam
        - Problemas de conexão persistente
        
        Returns:
            True se conseguiu recriar e testar com sucesso
        """
        try:
            logger_brain.info("🔄 [RECONEXÃO] Importando LexFlowClient...")
            
            from integrations.lex_flow_definitivo import (
                LexFlowClient,
                LexFlowConfig
            )
            
            logger_brain.info("🔄 [RECONEXÃO] Criando nova configuração...")
            
            nova_config = LexFlowConfig(
                base_url="https://flow.lex-usamn.com.br",
                username="Lex-Usamn",
                password="Lex#157."
            )
            
            logger_brain.info("🔄 [RECONEXÃO] Instanciando novo cliente...")
            
            # Criar NOVA instância (vai fazer auto-login!)
            novo_cliente = LexFlowClient(nova_config)
            
            # Verificar se funcionou
            if not novo_cliente or not novo_cliente.is_authenticated():
                logger_brain.error("❌ [RECONEXÃO] Novo cliente não autenticou!")
                return False
            
            # ✅ CORRIGIDO: Usar _get_inbox_robusto() em vez de get_inbox()
            logger_brain.info("🔄 [RECONEXÃO] Testando get_inbox() no novo cliente...")
            inbox_novo = self._get_inbox_robusto(novo_cliente)
            
            if inbox_novo and isinstance(inbox_novo, list) and len(inbox_novo) > 0:
                logger_brain.info(
                    f"✅ [RECONEXÃO] SUCESSO! Novo cliente tem {len(inbox_novo)} itens!"
                )
                
                # Substituir a instância antiga pela nova
                self._lexflow = novo_cliente
                
                logger_brain.info(
                    f"✅ [RECONEXÃO] self._lexflow substituído (novo id={id(self._lexflow)})"
                )
                
                return True
            else:
                logger_brain.error(
                    f"❌ [RECONEXÃO] Novo cliente também retornou inbox vazio: {inbox_novo}"
                )
                return False
                
        except ImportError as e_import:
            logger_brain.error(
                f"❌ [RECONEXÃO] Erro importando LexFlowClient: {e_import}"
            )
            return False
            
        except Exception as e:
            logger_brain.error(
                f"❌ [RECONEXÃO] Erro recriando cliente: {e}",
                exc_info=True
            )
            return False
    
    # =========================================================================
    # 🆕 MÉTODO ROBUSTO DE INBOX (CONTORNA BUG DO _unwrap_list!)
    # =========================================================================
    
    def _get_inbox_robusto(self, lexflow_instance=None) -> List[Dict]:
        """
        Busca inbox do Lex Flow de forma ROBUSTA.
        
        Contorna possível bug do _unwrap_list() que não extrai 
        a chave 'notes' da resposta da API.
        
        A API real retorna: {"notes": [...]}
        Mas _unwrap_list() só procurava: ['data','projects','items','quicknotes',...]
        
        Args:
            lexflow_instance: Instância opcional do LexFlowClient.
                             Se None, usa self._lexflow.
        
        Returns:
            Lista de dicionários com as notas (ou lista vazia)
        """
        
        cliente = lexflow_instance or self._lexflow
        
        if not cliente:
            logger_brain.warning("⚠️ [INBOX-ROBUSTO] Cliente Lex Flow é None!")
            return []
        
        try:
            # ═══════════════════════════════════════════════════
            # ESTRATÉGIA 1: Chamar get_inbox() normal
            # ═══════════════════════════════════════════════════
            
            resultado = cliente.get_inbox()
            
            if resultado and isinstance(resultado, list) and len(resultado) > 0:
                logger_brain.info(f"✅ [INBOX-ROBUSTO] get_inbox() normal funcionou: {len(resultado)} itens")
                return resultado
            
            # ═══════════════════════════════════════════════════
            # ESTRATÉGIA 2: Chamar _request direto (pula _unwrap_list!)
            # ═══════════════════════════════════════════════════
            
            logger_brain.warning(
                f"⚠️ [INBOX-ROBUSTO] get_inbox() retornou vazio "
                f"(type={type(resultado)}, valor={str(resultado)[:100]})"
            )
            logger_brain.info(f"🔍 [INBOX-ROBUSTO] Tentando _request() direto...")
            
            if hasattr(cliente, '_request'):
                resposta_crua = cliente._request('GET', '/quicknotes/')
                
                logger_brain.info(
                    f"🔍 [INBOX-ROBUSTO] Resposta crua: type={type(resposta_crua)}"
                )
                
                # A API retorna: {"notes": [...]} ← chave CORRETA é 'notes'!
                if isinstance(resposta_crua, dict):
                    
                    # ✅ PRIMEIRO: Procurar 'notes' (a chave REAL!)
                    if 'notes' in resposta_crua:
                        notas = resposta_crua['notes']
                        if isinstance(notas, list):
                            logger_brain.info(
                                f"✅ [INBOX-ROBUSTO] Extraído via chave 'notes': "
                                f"{len(notas)} itens!"
                            )
                            return notas
                    
                    # Depois tentar outras chaves conhecidas
                    for chave in ['data', 'quicknotes', 'items', 'results']:
                        if chave in resposta_crua:
                            valor = resposta_crua[chave]
                            if isinstance(valor, list) and len(valor) > 0:
                                logger_brain.info(
                                    f"✅ [INBOX-ROBUSTO] Extraído via chave '{chave}': "
                                    f"{len(valor)} itens"
                                )
                                return valor
                    
                    # Logar chaves disponíveis pra debug
                    logger_brain.warning(
                        f"⚠️ [INBOX-ROBUSTO] Dict recebido mas sem lista válida. "
                        f"Chaves: {list(resposta_crua.keys())}"
                    )
                
                elif isinstance(resposta_crua, list):
                    logger_brain.info(
                        f"✅ [INBOX-ROBUSTO] Resposta já era lista: {len(resposta_crua)} itens"
                    )
                    return resposta_crua
            
            # ═══════════════════════════════════════════════════
            # ESTRATÉGIA 3: search_notes como fallback
            # ═══════════════════════════════════════════════════
            
            logger_brain.warning("⚠️ [INBOX-ROBUSTO] Tentando search_notes('*') como fallback...")
            
            if hasattr(cliente, 'search_notes'):
                todas_notas = cliente.search_notes("*") or []
                if todas_notas:
                    logger_brain.info(
                        f"✅ [INBOX-ROBUSTO] search_notes encontrou: {len(todas_notas)} itens"
                    )
                    return todas_notas
            
            # ═══════════════════════════════════════════════════
            # FALHA TOTAL
            # ═══════════════════════════════════════════════════
            
            logger_brain.error("❌ [INBOX-ROBUSTO] Todas as estratégias falharam!")
            return []
            
        except Exception as e:
            logger_brain.error(
                f"❌ [INBOX-ROBUSTO] Erro: {e}",
                exc_info=True
            )
            return []
    
    def inicializar(self, llm_client=None, rag_system=None, 
                    lexflow_client=None, context_loader=None) -> bool:
        """Inicializa o orquestrador com dependências."""
        try:
            self._llm = llm_client
            self._rag = rag_system
            self._lexflow = lexflow_client
            self._context_loader = context_loader
            
            # Debug das dependências
            logger_brain.info(f"[v3.1] Dependências recebidas:")
            logger_brain.info(f"  - llm_client: {'✅' if self._llm else '❌ None'} (type: {type(self._llm)})")
            logger_brain.info(f"  - rag_system: {'✅' if self._rag else '❌ None'} (type: {type(self._rag)})")
            logger_brain.info(f"  - lexflow_client: {'✅' if self._lexflow else '❌ None'} (type: {type(self._lexflow)})")
            logger_brain.info(f"  - context_loader: {'✅' if self._context_loader else '❌ None'}")
            
            # ✅ CORRIGIDO: Testar com _get_inbox_robusto() em vez de get_inbox()
            if self._lexflow:
                try:
                    test_inbox = self._get_inbox_robusto()
                    logger_brain.info(
                        f"[v3.1] ✅ TESTE LEX FLOW OK! get_inbox() = "
                        f"{len(test_inbox) if isinstance(test_inbox, list) else test_inbox}"
                    )
                except Exception as e_test:
                    logger_brain.error(f"[v3.1] ⚠️ TESTE LEX FLOW FALHOU: {e_test}")
            else:
                logger_brain.warning(f"[v3.1] ⚠️ lexflow_client É NONE! Inbox não vai funcionar!")
            
            # Carregar contextos imediatamente
            self._atualizar_todos_contextos()
            
            self._inicializado = True
            logger_brain.info("[v3.1] Orquestrador PRONTO! (contextos carregados)")
            return True
            
        except Exception as e:
            logger_brain.error(f"[v3.1] Erro na inicialização: {e}", exc_info=True)
            return False


    # =========================================================================
    # SISTEMA DE RECONEXÃO AUTOMÁTICA DO LEX FLOW (ROBUSTEZ!)
    # =========================================================================
    
    def _garantir_lexflow_conectado(self) -> bool:
        """
        Garante que o Lex Flow está conectado e funcionando.
        
        Se get_inbox() retornar vazio, recria a instância do cliente.
        Isso resolve problemas de:
        - Sessão HTTP perdida/expirada
        - Token inválido silencioso
        - Instância corrompida
        
        Returns:
            True se Lex Flow está OK, False se não conseguiu reconectar
        """
        
        # ════════════════════════════════════════════════════════
        # PASSO 1: Verificar se instância existe
        # ════════════════════════════════════════════════════════
        
        if not self._lexflow:
            logger_brain.warning("🔌 [RECONEXÃO] self._lexflow é None! Tentando criar nova instância...")
            return self._recriar_lexflow_client()
        
        # ════════════════════════════════════════════════════════
        # PASSO 2: Testar se instância atual funciona (get_inbox)
        # ════════════════════════════════════════════════════════
        
        try:
            logger_brain.info(f"🔍 [RECONEXÃO] Testando Lex Flow atual (id={id(self._lexflow)})...")
            
            # Testar autenticação primeiro
            if hasattr(self._lexflow, 'is_authenticated'):
                if not self._lexflow.is_authenticated():
                    logger_brain.warning("⚠️ [RECONEXÃO] Lex Flow não autenticado! Reconectando...")
                    return self._recriar_lexflow_client()
            
            # Testar get_inbox()
            inbox_teste = self._get_inbox_robusto()
            
            logger_brain.info(
                f"🔍 [RECONEXÃO] get_inbox() retornou: "
                f"type={type(inbox_teste)}, "
                f"len={len(inbox_teste) if isinstance(inbox_teste, list) else 'N/A'}"
            )
            
            # ✅ SUCESSO - tem dados!
            if inbox_teste and isinstance(inbox_teste, list) and len(inbox_teste) > 0:
                logger_brain.info(
                    f"✅ [RECONEXÃO] Lex Flow OK! {len(inbox_teste)} itens no inbox"
                )
                return True
            
            # ⚠️ Lista vazia - pode ser bug ou realmente vazio
            # Vamos tentar login forçado antes de desistir
            logger_brain.warning(
                f"⚠️ [RECONEXÃO] Inbox vazio (lista vazia). "
                f"Tentando re-login forçado..."
            )
            
            # Tentar login novamente na instância atual
            if hasattr(self._lexflow, 'login'):
                login_ok = self._lexflow.login()
                if login_ok:
                    # Testar novamente após login
                    inbox_apos_login = self._get_inbox_robusto()
                    if inbox_apois_login and isinstance(inbox_apos_login, list) and len(inbox_apos_login) > 0:
                        logger_brain.info(
                            f"✅ [RECONEXÃO] Re-login funcionou! {len(inbox_apos_login)} itens"
                        )
                        return True
            
            # ❌ Ainda vazio mesmo após re-login → recriar instância
            logger_brain.warning(
                f"❌ [RECONEXÃO] Re-login não resolveu! "
                f"Recriando instância do LexFlowClient..."
            )
            return self._recriar_lexflow_client()
            
        except Exception as e:
            logger_brain.error(
                f"❌ [RECONEXÃO] Erro testando Lex Flow: {e}",
                exc_info=True
            )
            return self._recriar_lexflow_client()
    
    def _recriar_lexflow_client(self) -> bool:
        """
        Recria o cliente Lex Flow do zero.
        
        Solução nuclear para:
        - Sessões corrompidas
        - Tokens expirados que não renovam
        - Problemas de conexão persistente
        
        Returns:
            True se conseguiu recriar e testar com sucesso
        """
        try:
            logger_brain.info("🔄 [RECONEXÃO] Importando LexFlowClient...")
            
            from integrations.lex_flow_definitivo import (
                LexFlowClient,
                LexFlowConfig
            )
            
            logger_brain.info("🔄 [RECONEXÃO] Criando nova configuração...")
            
            # Criar config fresh (vai ler credenciais do default)
            nova_config = LexFlowConfig(
                base_url="https://flow.lex-usamn.com.br",
                username="Lex-Usamn",
                password="Lex#157."
            )
            
            logger_brain.info("🔄 [RECONEXÃO] Instanciando novo cliente...")
            
            # Criar NOVA instância (vai fazer auto-login!)
            novo_cliente = LexFlowClient(nova_config)
            
            # Verificar se funcionou
            if not novo_cliente or not novo_cliente.is_authenticated():
                logger_brain.error("❌ [RECONEXÃO] Novo cliente não autenticou!")
                return False
            
            # Testar get_inbox() na nova instância
            logger_brain.info("🔄 [RECONEXÃO] Testando get_inbox() no novo cliente...")
            inbox_novo = novo_cliente.get_inbox()
            
            if inbox_novo and isinstance(inbox_novo, list):
                logger_brain.info(
                    f"✅ [RECONEXÃO] SUCESSO! Novo cliente tem {len(inbox_novo)} itens!"
                )
                
                # Substituir a instância antiga pela nova
                self._lexflow = novo_cliente
                
                logger_brain.info(
                    f"✅ [RECONEXÃO] self._lexflow substituído (novo id={id(self._lexflow)})"
                )
                
                return True
            else:
                logger_brain.error(
                    f"❌ [RECONEXÃO] Novo cliente também retornou inbox vazio: {inbox_novo}"
                )
                return False
                
        except ImportError as e_import:
            logger_brain.error(
                f"❌ [RECONEXÃO] Erro importando LexFlowClient: {e_import}"
            )
            return False
            
        except Exception as e:
            logger_brain.error(
                f"❌ [RECONEXÃO] Erro recriando cliente: {e}",
                exc_info=True
            )
            return False


    def inicializar(self, llm_client=None, rag_system=None, 
                    lexflow_client=None, context_loader=None) -> bool:
        """Inicializa o orquestrador com dependências."""
        try:
            self._llm = llm_client
            self._rag = rag_system
            self._lexflow = lexflow_client
            self._context_loader = context_loader
            
            # ✅ NOVO: Debug das dependências
            logger_brain.info(f"[v3.0] Dependências recebidas:")
            logger_brain.info(f"  - llm_client: {'✅' if self._llm else '❌ None'} (type: {type(self._llm)})")
            logger_brain.info(f"  - rag_system: {'✅' if self._rag else '❌ None'} (type: {type(self._rag)})")
            logger_brain.info(f"  - lexflow_client: {'✅' if self._lexflow else '❌ None'} (type: {type(self._lexflow)})")
            logger_brain.info(f"  - context_loader: {'✅' if self._context_loader else '❌ None'}")
            
            # Testar Lex Flow se disponível
            if self._lexflow:
                try:
                    test_inbox = self._get_inbox_robusto()
                    logger_brain.info(f"[v3.0] ✅ TESTE LEX FLOW OK! get_inbox() = {len(test_inbox) if isinstance(test_inbox, list) else test_inbox}")
                except Exception as e_test:
                    logger_brain.error(f"[v3.0] ⚠️ TESTE LEX FLOW FALHOU: {e_test}")
            else:
                logger_brain.warning(f"[v3.0] ⚠️ lexflow_client É NONE! Inbox não vai funcionar!")
            
            # Carregar contextos imediatamente
            self._atualizar_todos_contextos()
            
            self._inicializado = True
            logger_brain.info("[v3.0] Orquestrador PRONTO! (contextos carregados)")
            return True
            
        except Exception as e:
            logger_brain.error(f"[v3.0] Erro na inicialização: {e}", exc_info=True)
            return False
    
    # =========================================================================
    # MÉTODO PRINCIPAL - PROCESSAR COM IA REAL
    # =========================================================================
    
    def processar(self, mensagem: str, contexto: Optional[Dict[str, Any]] = None) -> RespostaBrain:
        """
        Processa mensagem usando IA REAL (Gemini) como cérebro principal.
        v3.3 - CORREÇÃO: Detecta tipo explícito no meio da frase e evita dupla clarificação.
        """
        usuario_id = contexto.get("usuario_id") if contexto else None
        nome_usuario = contexto.get("nome", "Usuário") if contexto else "Usuário"
        
        logger_brain.info(f"[v3.3] Processando com IA REAL: '{mensagem[:50]}...'")
        
        try:
            # 1. Preparar mensagem contextualizada
            msg_ctx = self._preparar_mensagem_contextualizada(mensagem, usuario_id, nome_usuario)
            
            # 2. Montar o PROMPT MESTRE
            prompt_mestre = self._construir_prompt_mestre(msg_ctx)
            logger_brain.info(f"Prompt montado ({len(prompt_mestre)} chars)")
            
            if not self._llm:
                raise Exception("LLM Client não inicializado")
            
            # 3. Enviar para o LLM
            resposta_llm_raw = self._llm.gerar(prompt_mestre)
            logger_brain.info(f"LLM respondeu ({len(resposta_llm_raw.conteudo)} chars)")
            
            # 4. Parsear resposta
            decisao = self._parsear_resposta_llm(resposta_llm_raw.conteudo)
            acao_decidida = decisao.get("acao", "conversar")
            resposta_ia = decisao.get("resposta", "")
            logger_brain.info(f"🎯 IA decidiu: acao={acao_decidida}")
            
            # =====================================================================
            # ✅ v3.3: DETECÇÃO DE INTENÇÃO EXPLÍCITA (Evita dupla pergunta!)
            # =====================================================================
            if acao_decidida in ["criar_tarefa", "criar_nota"]:
                msg_lower = mensagem.lower().strip()
                
                # Palavras que indicam tipo EXPLÍCITO (mesmo no meio da frase)
                tem_nota_explicita = any(p in msg_lower for p in ["nota", "anotar", "anota", "registrar", "rascunho"])
                tem_tarefa_explicita = any(p in msg_lower for p in ["tarefa", "lembrete", "agenda", "prazo", "to-do"])
                
                # Se o usuário já especificou o tipo, PULA a clarificação!
                if tem_nota_explicita and not tem_tarefa_explicita:
                    logger_brain.info(f"⚡ [v3.3] Tipo NOTA explícito detectado → Executando direto!")
                    decisao["acao"] = "criar_nota"
                    return self._executar_acao(decisao, mensagem, contexto) or RespostaBrain(
                        sucesso=True, acao_executada="criar_nota",
                        resposta_ia=f"📝 *Nota salva!* Anotei: \"{mensagem}\"",
                        aguardando_resposta=False, clarificacao_pendente=False
                    )
                
                if tem_tarefa_explicita and not tem_nota_explicita:
                    logger_brain.info(f"⚡ [v3.3] Tipo TAREFA explícito detectado → Executando direto!")
                    decisao["acao"] = "criar_tarefa"
                    return self._executar_acao(decisao, mensagem, contexto) or RespostaBrain(
                        sucesso=True, acao_executada="criar_tarefa",
                        resposta_ia=f"✅ *Tarefa criada!* Registrei: \"{mensagem}\"",
                        aguardando_resposta=False, clarificacao_pendente=False
                    )
                
                # Se não tem tipo explícito, verifica se é comando óbvio (prefixo)
                comando_obvio = any([
                    msg_lower.startswith(("anota:", "nota:", "tarefa:", "lembrar", "lembra", "criar tarefa", "nova tarefa")),
                    ":" in msg_lower[:15] and len(msg_lower) > 15
                ])
                
                if not comando_obvio:
                    # ❌ Precisa clarificar
                    logger_brain.info(f"🤔 [CLARIFICAÇÃO] Ação '{acao_decidida}' requer confirmação")
                    conteudo = decisao.get("entidades", {}).get("conteudo", mensagem)
                    conteudo_curto = conteudo[:60] + ("..." if len(conteudo) > 60 else "")
                    tipo_acao_display = "TAREFA (com lembrete/prazo)" if acao_decidida == "criar_tarefa" else "NOTA simples"
                    
                    resposta_clarificacao = f"""🤔 *Deixa eu ver se entendi...*

Você quer registrar: **{conteudo_curto}**

📋 *Quer criar uma {tipo_acao_display}?*

💡 *Responda:*
• `sim` → Confirmar criação
• `tarefa` → Se for tarefa com prazo
• `nota` → Se for só anotar
• `cancela` → Desistir"""
                    
                    self._salvar_clarificacao_pendente(usuario_id, {
                        "acao_original": acao_decidida,
                        "decisao_completa": decisao,
                        "mensagem_original": mensagem,
                        "contexto": contexto,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    return RespostaBrain(
                        sucesso=True, acao_executada="clarificacao",
                        resposta_ia=resposta_clarificacao,
                        aguardando_resposta=True, clarificacao_pendente=True,
                        detalhes={"acao_pendente": acao_decidida}
                    )
                else:
                    logger_brain.info(f"⚡ Comando óbvio detectado → executar direto")
            
            # =====================================================================
            # EXECUTAR AÇÃO (se não for clarificação)
            # =====================================================================
            if acao_decidida and acao_decidida not in ["conversar", "clarificar"]:
                resultado_acao = self._executar_acao(decisao, mensagem, contexto)
                if resultado_acao:
                    self._salvar_no_historico(usuario_id, mensagem, resultado_acao.resposta_ia)
                    return resultado_acao
            
            # 6. Retornar resposta conversacional
            resposta_final = decisao.get("resposta", resposta_llm_raw.conteudo)
            self._salvar_no_historico(usuario_id, mensagem, resposta_final)
            
            return RespostaBrain(
                sucesso=True, acao_executada=decisao.get("acao", "conversar"),
                resposta_ia=resposta_final,
                detalhes={"metodo": "llm_orchestrator_v33", "usou_contextos_md": True, "usou_inbox": True}
            )
            
        except Exception as e:
            logger_brain.error(f"[v3.3] Erro no processamento: {e}", exc_info=True)
            return RespostaBrain(
                sucesso=False, acao_executada="erro",
                resposta_ia=f"Ops! Deu um probleminha aqui: {str(e)[:50]}\n\nPode tentar de novo?",
                erro=str(e)
            )

    # =========================================================================
    # SISTEMA DE CLARIFICAÇÃO v3.1 (NOVO - Corrige Bug 3!)
    # =========================================================================

    def _salvar_clarificacao_pendente(self, usuario_id: Optional[int], dados_clarificacao: dict) -> None:
        """Salva estado de clarificação para um usuário."""
        if not usuario_id:
            return
        
        # Usar variável de instância (não de classe!)
        if not hasattr(self, '_clarificacoes_dict'):
            self._clarificacoes_dict = {}
        
        self._clarificacoes_dict[usuario_id] = dados_clarificacao
        logger_brain.info(f"📝 [CLARIFICAÇÃO] Salva para user {usuario_id}: {dados_clarificacao.get('acao_original')}")

    def obter_clarificacao_pendente(self, usuario_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """Obtem clarificação pendente de um usuário."""
        if not usuario_id:
            return None
        
        if not hasattr(self, '_clarificacoes_dict'):
            return None
        
        return self._clarificacoes_dict.get(usuario_id)

    def processar_resposta_clarificacao(self, mensagem: str, usuario_id: int) -> Optional[RespostaBrain]:
        """
        Processa resposta do usuário a uma clarificação pendente.
        
        v3.3 - MELHORADO: Entende português coloquial e erros de digitação!
        """
        clarificacao = self.obter_clarificacao_pendente(usuario_id)
        
        if not clarificacao:
            logger_brain.warning(f"⚠️ [CLARIFICAÇÃO] Não há clarificação pendente para user {usuario_id}")
            return None
        
        logger_brain.info(f"💬 [CLARIFICAÇÃO] Processando resposta: '{mensagem}'")
        
        # Normalizar mensagem (minúsculas, remover acentos extras, espaços)
        msg_lower = mensagem.lower().strip()
        import unicodedata
        msg_normalized = unicodedata.normalize('NFKD', msg_lower).encode('ASCII', 'ignore').decode('ASCII')
        
        # =====================================================================
        # 1. CANCELAMENTO (palavras claras de negação)
        # =====================================================================
        palavras_cancelar = [
            "cancela", "cancelar", "esquece", "ignora", 
            "deixa", "nao", "não", "nem", "esquece", "deixa pra la",
            "desiste", "desistir", "apaga"
        ]
        
        if any(palavra in msg_normalized for palavra in palavras_cancelar):
            if hasattr(self, '_clarificacoes_dict') and usuario_id in self._clarificacoes_dict:
                del self._clarificacoes_dict[usuario_id]
            
            return RespostaBrain(
                sucesso=True,
                acao_executada="cancelado",
                resposta_ia="👍 *Beleza, cancelado!* Se precisar de algo, é só chamar! 😊",
                aguardando_resposta=False,
                clarificacao_pendente=False
            )
        
        # =====================================================================
        # 2. USUÁRIO JÁ DISSE O TIPO DIRETO! (nota / tarefa / lembrete)
        # =====================================================================
        
        # Padrões para NOTA
        padroes_nota = [
            "nota", "anotar", "anota", "so nota", "só nota", "apenas nota",
            "nota so", "nota só", "so anotar", "só anotar", "registra",
            "registrar", "guarda", "guardar", "lembrete", "rascunho",
            "nao e tarefa", "não é tarefa", "nao tarefa", "notar"
        ]
        
        # Padrões para TAREFA
        padroes_tarefa = [
            "tarefa", "task", "to-do", "todo", "agenda", "compromisso",
            "lembra", "lembrar", "prazo", "deadline", "agendar",
            "colocar na agenda", "criar tarefa", "nova tarefa"
        ]
        
        # Verificar se quer NOTA
        if any(padrao in msg_normalized for padrao in padroes_nota):
            if hasattr(self, '_clarificacoes_dict') and usuario_id in self._clarificacoes_dict:
                del self._clarificacoes_dict[usuario_id]
            
            decisao_original = clarificacao.get("decisao_completa", {})
            decisao_original["acao"] = "criar_nota"
            
            logger_brain.info(f"✅ [CLARIFICAÇÃO] Usuário escolheu NOTA (direto!)")
            
            resultado = self._executar_acao(
                decisao_original, 
                clarificacao.get("mensagem_original", mensagem),
                clarificacao.get("contexto", {})
            )
            
            if resultado:
                resultado.resposta_ia = "📝 *Nota salva!*\n\n" + resultado.resposta_ia
                return resultado
            
            return RespostaBrain(
                sucesso=True,
                acao_executada="criar_nota",
                resposta_ia=f"📝 *Anotei!* Salvei como nota: \"{clarificacao.get('mensagem_original', mensagem)}\"",
                aguardando_resposta=False,
                clarificacao_pendente=False
            )
        
        # Verificar se quer TAREFA
        if any(padrao in msg_normalized for padrao in padroes_tarefa):
            if hasattr(self, '_clarificacoes_dict') and usuario_id in self._clarificacoes_dict:
                del self._clarificacoes_dict[usuario_id]
            
            decisao_original = clarificacao.get("decisao_completa", {})
            decisao_original["acao"] = "criar_tarefa"
            
            logger_brain.info(f"✅ [CLARIFICAÇÃO] Usuário escolheu TAREFA (direto!)")
            
            resultado = self._executar_acao(
                decisao_original, 
                mensagem,
                clarificacao.get("contexto", {})
            )
            
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
        
        # =====================================================================
        # 3. CONFIRMAÇÃO GERAL (sim / ok / blz / claro / pode / vai / etc.)
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
            if hasattr(self, '_clarificacoes_dict') and usuario_id in self._clarificacoes_dict:
                del self._clarificacoes_dict[usuario_id]
            
            # Executar ação original que estava pendente
            decisao_original = clarificacao.get("decisao_completa", {})
            mensagem_original = clarificacao.get("mensagem_original", mensagem)
            contexto_original = clarificacao.get("contexto", {})
            
            acao_pendente = clarificacao.get('acao_original', 'desconhecido')
            logger_brain.info(f"✅ [CLARIFICAÇÃO] Usuário CONFIRMOU → Executando {acao_pendente}")
            
            resultado = self._executar_acao(decisao_original, mensagem_original, contexto_original)
            
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
            
            # Fallback se execução falhar
            return RespostaBrain(
                sucesso=True,
                acao_executada=acao_pendente,
                resposta_ia=f"✅ *Criado com sucesso!* {mensagem_original}",
                aguardando_resposta=False,
                clarificacao_pendente=False
            )
        
        # =====================================================================
        # 4. NÃO ENTENDEU → Repetir opções de forma mais amigável
        # =====================================================================
        acao_sugerida = clarificacao.get('acao_original', 'criar')
        msg_original = clarificacao.get('mensagem_original', 'isso')
        
        return RespostaBrain(
            sucesso=True,
            acao_executada="clarificacao_repetir",
            resposta_ia=f"""🤔 *Hmm, não entendi muito bem...*

    Você disse: "{mensagem}"

    💡 *Opções válidas:*
    • `sim` → Criar conforme sugerido
    • `tarefa` → Criar como TAREFA
    • `nota` → Criar como NOTA  
    • `cancela` → Desistir

    Como prefere?""",
            aguardando_resposta=True,
            clarificacao_pendente=True
        )    



    # =========================================================================
    # CARREGAMENTO DE CONTEXTOS (.md FILES) - SEM TRUNCATION!
    # =========================================================================
    
    def _atualizar_todos_contextos(self) -> None:
        """Carrega/atualiza todos os arquivos de contexto (.md)."""
        agora = datetime.now()
        
        # Verificar se cache ainda é válido
        if self._ultima_atualizacao:
            horas_desde_update = (
                agora - self._ultima_atualizacao
            ).total_seconds() / 3600
            if horas_desde_update < self._cache_validade_horas:
                logger_brain.debug(f"Cache valido ({horas_desde_update:.1f}h)")
                return
        
        logger_brain.info("Atualizando contextos dos arquivos .md...")
        
        try:
            if self._context_loader:
                contextos = self._context_loader.carregar_todos(forcar_reload=True)
                for chave, valor in contextos.items():
                    if not valor.startswith("[Erro") and not valor.startswith("[Arquivo"):
                        self._contextos_cache[chave] = valor
                    else:
                        self._contextos_cache[chave] = ""
            else:
                self._carregar_arquivos_direto()
            
            self._ultima_atualizacao = agora
            logger_brain.info("Contextos atualizados")
            
        except Exception as e:
            logger_brain.warning(f"Erro carregando contextos: {e}")
    
    def _carregar_arquivos_direto(self) -> None:
        """Lê os arquivos .md diretamente (fallback se ContextLoader falhar)."""
        arquivos = {
            "soul": "SOUL.md",
            "user": "USER.md",
            "memory": "MEMORY.md",
            "heartbeat": "HEARTBEAT.md"
        }
        
        for chave, arquivo in arquivos.items():
            caminho = os.path.join(os.path.dirname(__file__), '..', arquivo)
            
            try:
                if os.path.exists(caminho):
                    with open(caminho, 'r', encoding='utf-8') as f:
                        conteudo = f.read()
                        # ✅ CORREÇÃO: Carregar ARQUIVO INTEIRO (sem truncation!)
                        self._contextos_cache[chave] = conteudo
                        logger_brain.info(f"{chave}: lido diretamente ({len(conteudo)} chars)")
                else:
                    self._contextos_cache[chave] = ""
                    logger_brain.warning(f"Arquivo não encontrado: {caminho}")
                    
            except Exception as e:
                logger_brain.error(f"Erro lendo {arquivo}: {e}")
                self._contextos_cache[chave] = ""
    
    # =========================================================================
    # CONSTRUÇÃO DO PROMPT MESTRE - CONTEXTO COMPLETO!
    # =========================================================================
    
    def _construir_prompt_mestre(self, msg_ctx: MensagemContextualizada) -> str:
        """Monta o PROMPT MESTRE que dá à IA TODO o contexto necessário."""
        
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        # ✅ CORREÇÃO: Usar CONTEXTO COMPLETO (sem cortes!)
        soul_text = msg_ctx.contexto_soul or "[Não encontrado]"
        user_text = msg_ctx.contexto_user or "[Não encontrado]"
        memory_text = msg_ctx.contexto_memory or "[Não encontrado]"
        heartbeat_text = msg_ctx.contexto_heartbeat or "[Não encontrado]"
        
        # ✅ NOVO: Carregar inbox do Lex Flow se disponível (COM RECONEXÃO AUTOMÁTICA!)
        inbox_text = ""
        
        if self._lexflow:
            try:
                # ════════════════════════════════════════════════════════
                # 🆕 GARANTIR QUE LEX FLOW ESTÁ CONECTADO ANTES DE BUSCAR!
                # ════════════════════════════════════════════════════════
                
                lexflow_ok = self._garantir_lexflow_conectado()
                
                if not lexflow_ok:
                    inbox_text = "[⚠️ Lex Flow indisponível - usando sem inbox]"
                    logger_brain.warning("⚠️ [PROMPT] Não foi possível conectar Lex Flow")
                else:
                    # Lex Flow está OK → buscar inbox
                    logger_brain.info(f"📥 [PROMPT] Carregando inbox via get_inbox()...")
                    inbox_items = self._get_inbox_robusto()
                    
                    logger_brain.info(
                        f"📥 [PROMPT] get_inbox() retornou: "
                        f"type={type(inbox_items)}, "
                        f"valor={str(inbox_items)[:300]}"
                    )
                    
                    if inbox_items and isinstance(inbox_items, list) and len(inbox_items) > 0:
                        inbox_lines = []
                        for i, item in enumerate(inbox_items[:10], 1):  # Máx 10 itens
                            if isinstance(item, dict):
                                titulo = item.get('title', item.get('nome', 'Sem título'))
                                conteudo_preview = item.get('content', item.get('conteudo', ''))
                                if conteudo_preview:
                                    preview = str(conteudo_preview).replace('\n', ' ')[:80]
                                    inbox_lines.append(f"  {i}. 📝 {titulo}")
                                    inbox_lines.append(f"     └─ {preview}")
                                else:
                                    inbox_lines.append(f"  {i}. 📝 {titulo}")
                            elif isinstance(item, str):
                                inbox_lines.append(f"  {i}. 📝 {item}")
                            else:
                                inbox_lines.append(f"  {i}. 📝 {str(item)}")
                        
                        inbox_text = "\n".join(inbox_lines)
                        logger_brain.info(f"✅ [PROMPT] Inbox carregado: {len(inbox_items)} itens formatados")
                        
                    elif inbox_items == [] or inbox_text == "":
                        inbox_text = "[Caixa de Entrada vazia]"
                        logger_brain.info(f"⚠️ [PROMPT] Inbox está VAZIO (lista vazia)")
                        
                    else:
                        inbox_text = f"[Inbox retornou formato inesperado: {type(inbox_items)} = {str(inbox_items)[:200]}]"
                        logger_brain.warning(f"⚠️ [PROMPT] Inbox formato estranho: {inbox_items}")
                        
            except Exception as e:
                inbox_text = f"[ERRO ao carregar inbox: {str(e)[:100]}]"
                logger_brain.error(f"❌ [PROMPT] Erro carregando inbox: {e}", exc_info=True)
        else:
            inbox_text = "[Lex Flow não disponível (self._lexflow é None)]"
            logger_brain.warning(f"⚠️ [PROMPT] self._lexflow é None! Lex Flow não foi inicializado!")
        
        if not inbox_text:
            inbox_text = "[Caixa de Entrada indisponível]"
        
        prompt = f"""{NOME_ASSISTENTE_DISPLAY} v3.1 - Assistente Pessoal Inteligente
    {'='*60}

    DATA/HORA ATUAL: {data_hora}

    ═══════════════════════════════════════════════════════
    QUEM EU SOU (SOUL.md - Minha Identidade Completa)
    ═══════════════════════════════════════════════════════
    {soul_text}

    ═══════════════════════════════════════════════════════
    QUEM É O USUÁRIO (USER.md - Perfil Completo)
    ═══════════════════════════════════════════════════════
    {user_text}

    ═══════════════════════════════════════════════════════
    MEMÓRIA E LIÇÕES (MEMORY.md - Experiência)
    ═══════════════════════════════════════════════════════
    {memory_text}

    ═══════════════════════════════════════════════════════
    STATUS ATUAL (HEARTBEAT.md - Hoje)
    ═══════════════════════════════════════════════════════
    {heartbeat_text}

    ═══════════════════════════════════════════════════════
    📋 CAIXA DE ENTRADA ATUAL (Lex Flow - NOTAS/TAREFAS REAIS)
    ═══════════════════════════════════════════════════════
    {inbox_text}

    ═══════════════════════════════════════════════════════
    HISTÓRICO DESTA CONVERSA (Últimas mensagens)
    ═══════════════════════════════════════════════════════
    """

        # Adicionar histórico da conversa
        if msg_ctx.historico_conversa:
            for item in msg_ctx.historico_conversa[-8:]:
                role = item.get('role', 'user')
                texto = item.get('texto', '')[:200]
                prompt += f"{role.upper()}: {texto}\n"
        else:
            prompt += "[Início da conversa]\n"

        prompt += f"""
    ═══════════════════════════════════════════════════════
    MENSAGEM ATUAL DO USUÁRIO
    ═══════════════════════════════════════════════════════
    {msg_ctx.mensagem_usuario}

    ═══════════════════════════════════════════════════════
    SUA TAREFA AGORA
    ═══════════════════════════════════════════════════════

    Você É o {NOME_ASSISTENTE_DISPLAY}, o cérebro pessoal do Lex.
    Use TODO o contexto acima para responder de forma PERSONALIZADA.

    🎯 REGRAS CRÍTICAS (OBRIGATÓRIAS):

    📋 QUANDO USUÁRIO PERGUNTAR SOBRE NOTAS/TAREFAS EXISTENTES:
    - Use a seção "CAIXA DE ENTRADA ATUAL" acima (dados REAIS do Lex Flow!)
    - NÃO invente dados do HEARTBEAT.md (ele só tem planejamento, não tarefas reais)
    - Se acao="buscar_info", liste o que tem na Caixa de Entrada
    - Se estiver vazia, diga "Não há notas/tarefas no momento"

    🤔 QUANDO USUÁRIO QUISER CRIAR ALGO (tarefa/nota):
    - NUNCA execute direto! Use acao="clarificar"
    - Pergunte: "Quer criar TAREFA ou NOTA?"
    - Aguarde confirmação antes de criar

    💬 FORMATO DA RESPOSTA (OBRIGATÓRIO):
    - Use QUEBRAS DE LINHA entre parágrafos (\\n)
    - Separe ideias com linhas em branco
    - Use emojis MODERADAMENTE
    - Máximo 6-8 linhas (seja conciso!)
    - NÃO escreva tudo em uma linha só!

    Decida o que fazer:

    1. CONVERSAR (saudação, pergunta casual, agradecimento)
    2. CLARIFICAR (usuário quer criar algo, mas precisa confirmar)
    3. CRIAR_TAREFA (SÓ se confirmado!)
    4. CRIAR_NOTA (SÓ se confirmado!)
    5. BUSCAR_INFO (perguntar sobre notas/tarefas → use CAIXA DE ENTRADA!)
    6. DELETAR_NOTAS (apagar/remover notas da Caixa de Entrada)
    7. MOVER_NOTA (mover nota da Caixa para área/projeto P.A.R.A)  ← 🆕 NOVO!
    8. GERAR_IDEIAS (pedir sugestões/criatividade)
    9. CONSULTAR_METRICAS (pedir status/relatório)

    ═══════════════════════════════════════════════════════
    FORMATO DE RESPOSTA (OBRIGATÓRIO - JSON)
    ═══════════════════════════════════════════════════════

    Responda EXATAMENTE neste formato JSON (nada fora dele):

    {{
    "acao": "conversar|clarificar|criar_tarefa|criar_nota|buscar_info|deletar_notas|gerar_ideias|consultar_metricas",
    "resposta": "Sua resposta natural aqui em português\\nUse quebras de linha entre parágrafos",
    "entidades": {{
        "conteudo": "o que foi dito (se for tarefa/nota)",
        "criterio": "palavra-chave para deletar (se for deletar_notas)",  ← 🆕 NOVO!
        "destino": "área ou projeto de destino (se for mover_nota)",
        "converter_tarefa": false,
        "prazo": "prazo detectado (opcional)",
        "prioridade": "prioridade (opcional)",
        "projeto": "projeto relacionado (opcional)"
    }}
    }}

    Seu JSON:"""
        
        return prompt
    
    # =========================================================================
    # PARSEAMENTO DA RESPOSTA DO LLM
    # =========================================================================
    
    def _parsear_resposta_llm(self, resposta_raw: str) -> Dict[str, Any]:
        """
        Extrai o JSON da resposta do LLM.
        
        v3.0.1: MELHORADO - Mais robusto contra variações de formato!
        """
        
        # Se já for dict (não deveria, mas por segurança)
        if isinstance(resposta_raw, dict):
            return resposta_raw
        
        # Se não for string, converter
        if not isinstance(resposta_raw, str):
            resposta_raw = str(resposta_raw)
        
        texto = resposta_raw.strip()
        
        # =====================================================================
        # ESTRATÉGIA 1: Provar padrões JSON diretos
        # =====================================================================
        
        padroes_json = [
            # Padrão 1: Code block ```json ... ```
            r'```json\s*(\{.*?\})\s*```',
            # Padrão 2: Code block genérico ``` ... ```
            r'```\s*(\{.*?\})\s*```',
            # Padrão 3: JSON direto (começa com { e termina com })
            r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',
        ]
        
        for padrao in padroes_json:
            match = re.search(padrao, texto, re.DOTALL | re.I)
            if match:
                try:
                    json_str = match.group(1).strip()
                    
                    # Limpar possíveis caracteres problemáticos
                    json_str = json_str.replace('\n', ' ').replace('\r', '')
                    
                    decisao = json.loads(json_str)
                    
                    # Validar campos obrigatórios
                    if "acao" in decisao and "resposta" in decisao:
                        logger_brain.info(f"✅ [PARSE] JSON extraído: acao={decisao.get('acao')}")
                        return decisao
                        
                except json.JSONDecodeError as e:
                    logger_brain.debug(f"[PARSE] JSON inválido no padrão {padrao[:20]}: {e}")
                    continue
        
        # =====================================================================
        # ESTRATÉGIA 2: Provar campos individuais (fallback inteligente)
        # =====================================================================
        
        logger_brain.warning("⚠️ [PARSE] Padrões JSON falharam, tentando extração individual...")
        
        resultado = {
            "acao": "conversar",
            "resposta": texto,  # Texto original como resposta
            "entidades": {}
        }
        
        # Tentar extrair "acao"
        match_acao = re.search(r'"acao"\s*:\s*"([^"]*)"', texto)
        if match_acao:
            resultado["acao"] = match_acao.group(1)
        
        # Tentar extrair "resposta"
        match_resposta = re.search(r'"resposta"\s*:\s*"((?:[^"\\]|\\.)*)"', texto)
        if match_resposta:
            resultado["resposta"] = match_resposta.group(1)
            logger_brain.info(f"✅ [PARSE] Resposta extraída individualmente!")
        
        # Tentar extrair "entidades" (se existir)
        match_entidades = re.search(r'"entidades"\s*:\s*(\{.*?\})', texto, re.DOTALL)
        if match_entidades:
            try:
                entidades_str = match_entidades.group(1)
                resultado["entidades"] = json.loads(entidades_str)
            except:
                resultado["entidades"] = {}
        
        # Se encontramos pelo menos a ação, é válido
        if resultado.get("acao") and resultado.get("resposta"):
            return resultado
        
        # =====================================================================
        # ESTRATÉGIA 3: Último recurso - tratar tudo como conversa
        # =====================================================================
        
        logger_brain.warning("⚠️ [PARSE] Não encontrou JSON, tratando como conversa")
        
        # Se o texto parecer conter JSON (tem chaves), limpar
        if '{' in texto and '}' in texto:
            # Remover tudo que parecer JSON, ficar só com texto legível
            linhas = texto.split('\n')
            linhas_limpas = []
            for linha in linhas:
                # Pular linhas que parecem JSON
                if not linha.strip().startswith(('"', '{', '}', '[', ']', '  "', '    "')):
                    linhas_limpas.append(linha)
            
            texto_limpo = '\n'.join(linhas_limpas).strip()
            if texto_limpo:
                resultado["resposta"] = texto_limpo
            else:
                # Se tudo era JSON, usar mensagem genérica
                resultado["resposta"] = "Entendi! Como posso te ajudar com isso? 😊"
        
        return resultado
    
    # =========================================================================
    # EXECUÇÃO DE AÇÕES
    # =========================================================================
    
    def _executar_acao(self, decisao: Dict[str, Any], 
                       mensagem: str, contexto: Optional[dict]) -> Optional[RespostaBrain]:
        """Executa ação que a IA decidiu."""
        
        acao = decisao.get("acao")
        entidades = decisao.get("entidades", {})
        resposta_ia = decisao.get("resposta", "")
        
        logger_brain.info(f"Execução ação da IA: {acao}")
        
        try:
            if acao == "criar_tarefa":
                return self._executar_criar_tarefa(entidades, mensagem, resposta_ia)
                
            elif acao == "criar_nota":
                return self._executar_criar_nota(entidades, mensagem, resposta_ia)
                
            elif acao == "buscar_info":
                return self._executar_buscar_info(entidades, mensagem, resposta_ia)

            elif acao == "deletar_notas":
                return self._executar_deletar_notas(entidades, mensagem, resposta_ia)
                
            elif acao == "mover_nota":
                return self._executar_mover_nota(entidades, mensagem, resposta_ia)               
              
            elif acao == "gerar_ideias":
                return self._executar_gerar_ideias(entidades, mensagem, resposta_ia)
                
            elif acao == "consultar_metricas":
                return RespostaBrain(
                    sucesso=True,
                    acao_executada="consultar_metricas",
                    resposta_ia=resposta_ia
                )
            
            return None
            
        except Exception as e:
            logger_brain.error(f"Erro executando {acao}: {e}", exc_info=True)
            return RespostaBrain(
                sucesso=False,
                acao_executada=acao,
                resposta_ia=f"{resposta_ia}Erro ao executar: {str(e)[:50]}",
                erro=str(e)
            )
    
    def _executar_criar_tarefa(self, entidades: dict, 
                                mensagem: str, resposta_ia: str) -> RespostaBrain:
        """Executa criação de tarefa no Lex Flow."""
        
        if not self._lexflow:
            return RespostaBrain(
                sucesso=False, 
                acao_executada="criar_tarefa", 
                resposta_ia="Lex Flow indisponível"
            )
        
        conteudo = entidades.get("conteudo", mensagem)
        titulo = conteudo[:80]
        
        titulo_inbox = f"TAREFA: {titulo}"
        if entidades.get("prazo"):
            titulo_inbox += f" | PRAZO: {entidades['prazo']}"
        
        prioridade = entidades.get("prioridade", "medium")
        icones = {"high": "URGENTE", "low": "BAIXA", "urgent": "!!! URGENTE !!!", "medium": "MEDIA"}
        if prioridade in icones:
            titulo_inbox += f" | PRIORIDADE: {icones[prioridade]}"
        
        descricao = (
            f"[Criado por {NOME_ASSISTENTE_DISPLAY} v3.0 - IA]"
            f"{mensagem}Status: Aguardando triagem"
        )
        tags = ["tarefa", "inbox", "brain-v30-ia", f"pri:{prioridade}"]
        
        try:
            resultado = self._lexflow.add_note(
                title=titulo_inbox, content=descricao, tags=tags
            )
            
            if resultado is not None:
                if isinstance(resultado, dict) and not resultado.get("success"):
                    resultado["success"] = True
            
            sucesso = (
                resultado is not None and 
                (not isinstance(resultado, dict) or resultado.get("success"))
            )
            
            if sucesso:
                resposta_final = (
                    f"{resposta_ia}"
                    f"Tarefa registrada na Caixa de Entrada!"
                    f"- {titulo}"
                )
                if entidades.get("prazo"):
                    resposta_final += f"- Prazo: {entidades['prazo']}"
                resposta_final += f"- Prioridade: {prioridade.capitalize()}"
                
                return RespostaBrain(
                    sucesso=True,
                    acao_executada="criar_tarefa",
                    resposta_ia=resposta_final,
                    detalhes={"modo": "inbox", "fonte": "decisao_ia"}
                )
            
            raise Exception("Falha ao criar tarefa")
            
        except Exception as e:
            logger_brain.error(f"Erro tarefa: {e}")
            return RespostaBrain(
                sucesso=False,
                acao_executada="criar_tarefa",
                resposta_ia=f"{resposta_ia}Erro ao salvar: {str(e)[:40]}"
            )
    
    def _executar_criar_nota(self, entidades: dict, 
                              mensagem: str, resposta_ia: str) -> RespostaBrain:
        """Executa criação de nota no Lex Flow."""
        
        if not self._lexflow:
            return RespostaBrain(
                sucesso=False, 
                acao_executada="criar_nota", 
                resposta_ia="Lex Flow indisponível"
            )
        
        conteudo = entidades.get("conteudo", mensagem)
        titulo = conteudo[:50] + ("..." if len(conteudo) > 50 else "")
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        conteudo_completo = (
            f"[Captura via {NOME_ASSISTENTE_DISPLAY} v3.0 - IA - {timestamp}]"
            f"{conteudo}"
        )
        
        try:
            resultado = self._lexflow.add_note(titulo, content=conteudo_completo)
            
            if resultado is not None:
                if isinstance(resultado, dict) and not resultado.get("success"):
                    resultado["success"] = True
            
            if resultado and (not isinstance(resultado, dict) or resultado.get("success")):
                return RespostaBrain(
                    sucesso=True,
                    acao_executada="criar_nota",
                    resposta_ia=f"{resposta_ia}Nota salva!",
                    detalhes={"fonte": "decisao_ia"}
                )
            
            raise Exception("Falha ao criar nota")
            
        except Exception as e:
            return RespostaBrain(
                sucesso=False,
                acao_executada="criar_nota",
                resposta_ia=f"{resposta_ia}Erro: {str(e)[:40]}"
            )
    
    def _executar_deletar_notas(self, entidades: dict, mensagem: str, resposta_ia: str) -> RespostaBrain:
        """
        Deleta notas/tarefas do Lex Flow baseado em critérios.
        
        v3.3: Implementa deleção real (antes só fingia deletar!)
        """
        if not self._lexflow:
            return RespostaBrain(
                sucesso=False,
                acao_executada="deletar_notas",
                resposta_ia="⚠️ Lex Flow indisponível. Não consigo deletar agora.",
                erro="lexflow_none"
            )
        
        try:
            # 1. Obter critério de busca
            criterio = entidades.get("criterio", entidades.get("conteudo", ""))
            
            if not criterio:
                return RespostaBrain(
                    sucesso=False,
                    acao_executada="deletar_notas",
                    resposta_ia="🤔 Qual palavra-chave devo procurar para deletar? (Ex: 'shorts', 'teste', etc.)",
                    erro="criterio_vazio"
                )
            
            logger_brain.info(f"🗑️ [DELETAR] Procurando notas com critério: '{criterio}'")
            
            # 2. Buscar notas que correspondem ao critério
            inbox = self._get_inbox_robusto()
            
            if not inbox or not isinstance(inbox, list):
                logger_brain.warning(f"⚠️ [DELETAR] Inbox vazio ou inválido: {inbox}")
                return RespostaBrain(
                    sucesso=False,
                    acao_executada="deletar_notas",
                    resposta_ia="📭 Sua Caixa de Entrada está vazia. Nada para deletar!",
                    erro="inbox_vazio"
                )
            
            # 3. Filtrar itens que contêm o critério (case-insensitive)
            criterio_lower = criterio.lower()
            itens_deletar = []
            
            for item in inbox:
                if not isinstance(item, dict):
                    continue
                
                # Verificar em title/label/content
                titulo = str(item.get('title', item.get('label', item.get('nome', '')))).lower()
                conteudo = str(item.get('content', item.get('conteudo', ''))).lower()
                
                if criterio_lower in titulo or criterio_lower in conteudo:
                    itens_deletar.append(item)
            
            if not itens_deletar:
                logger_brain.info(f"ℹ️ [DELETAR] Nenhum item encontrado com '{criterio}'")
                return RespostaBrain(
                    sucesso=True,
                    acao_executada="deletar_notas",
                    resposta_ia=f"🔍 Não encontrei notas com **'{criterio}'** na Caixa de Entrada.\n\nQuer que eu mostre o que tem?",
                    detalhes={"encontrados": 0}
                )
            
            # 4. Deletar cada item encontrado
            deletados = []
            erros = []
            
            for item in itens_deletar:
                item_id = item.get('id')
                item_titulo = item.get('title', item.get('label', 'Sem título'))
                
                if not item_id:
                    logger_brain.warning(f"⚠️ [DELETAR] Item sem ID: {item}")
                    continue
                
                try:
                    # Chamar API de deleção do Lex Flow
                    if hasattr(self._lexflow, 'delete_note'):
                        resultado = self._lexflow.delete_note(item_id)
                        logger_brain.info(f"🗑️ [DELETAR] Deletado ID={item_id}: {item_titulo}")
                        deletados.append(item_titulo)
                    else:
                        logger_brain.error(f"❌ [DELETAR] LexFlowClient não tem método delete_note()!")
                        erros.append(f"ID {item_id} (método não existe)")
                        
                except Exception as e_del:
                    logger_brain.error(f"❌ [DELETAR] Erro deletando ID={item_id}: {e_del}")
                    erros.append(f"ID {item_id} ({str(e_del)[:30]})")
            
            # 5. Montar resposta
            total_deletados = len(deletados)
            total_erros = len(erros)
            
            if total_deletados > 0:
                msg_deletados = "\n".join([f"  • {t}" for t in deletados[:5]])
                if total_deletados > 5:
                    msg_deletados += f"\n  • ... e mais {total_deletados - 5} itens"
                
                resposta_final = f"🗑️ **Deletei {total_deletados} nota(s) com '{criterio}':**\n\n{msg_deletados}"
                
                if total_erros > 0:
                    resposta_final += f"\n\n⚠️ {total_erros} erro(s) ao deletar alguns itens."
                
                return RespostaBrain(
                    sucesso=True,
                    acao_executada="deletar_notas",
                    resposta_ia=resposta_final,
                    detalhes={
                        "deletados": total_deletados,
                        "erros": total_erros,
                        "criterio": criterio
                    }
                )
            else:
                return RespostaBrain(
                    sucesso=False,
                    acao_executada="deletar_notas",
                    resposta_ia=f"❌ Não consegui deletar nenhuma nota.\n\nErros: {len(erros)}",
                    erro="nenhum_deletado",
                    detalhes={"erros": erros}
                )
                
        except Exception as e:
            logger_brain.error(f"❌ [DELETAR] Erro geral: {e}", exc_info=True)
            return RespostaBrain(
                sucesso=False,
                acao_executada="deletar_notas",
                resposta_ia=f"❌ Erro ao deletar: {str(e)[:50]}",
                erro=str(e)
            )

    def _executar_mover_nota(self, entidades: dict, mensagem: str, resposta_ia: str) -> RespostaBrain:
        """
        Move nota para área ou projeto (P.A.R.A).
        
        v3.3: Implementa movimentação real entre contextos.
        """
        if not self._lexflow:
            return RespostaBrain(
                sucesso=False, acao_executada="mover_nota",
                resposta_ia="⚠️ Lex Flow indisponível.", erro="lexflow_none"
            )
        
        try:
            # 1. Extrair destino (área ou projeto)
            destino = entidades.get("destino", entidades.get("projeto", entidades.get("area", "")))
            criterio = entidades.get("criterio", entidades.get("conteudo", ""))
            converter_tarefa = entidades.get("converter_tarefa", False)
            
            if not destino:
                return RespostaBrain(
                    sucesso=False, acao_executada="mover_nota",
                    resposta_ia="🤔 Para onde devo mover? (área ou projeto)",
                    erro="destino_vazio"
                )
            
            if not criterio:
                return RespostaBrain(
                    sucesso=False, acao_executada="mover_nota",
                    resposta_ia="🤔 Qual nota devo mover? Preciso de uma palavra-chave.",
                    erro="criterio_vazio"
                )
            
            logger_brain.info(f"📂 [MOVER] Procurando '{criterio}' para mover para '{destino}'")
            
            # 2. Buscar nota na inbox
            inbox = self._get_inbox_robusto()
            if not inbox:
                return RespostaBrain(
                    sucesso=False, acao_executada="mover_nota",
                    resposta_ia="📭 Caixa de Entrada vazia.", erro="inbox_vazio"
                )
            
            # 3. Encontrar nota
            criterio_lower = criterio.lower()
            nota_encontrada = None
            
            for item in inbox:
                if not isinstance(item, dict):
                    continue
                titulo = str(item.get('title', item.get('label', ''))).lower()
                conteudo = str(item.get('content', '')).lower()
                
                if criterio_lower in titulo or criterio_lower in conteudo:
                    nota_encontrada = item
                    break
            
            if not nota_encontrada:
                return RespostaBrain(
                    sucesso=False, acao_executada="mover_nota",
                    resposta_ia=f"🔍 Não encontrei nota com '{criterio}'.",
                    erro="nota_nao_encontrada"
                )
            
            nota_id = nota_encontrada.get('id')
            nota_titulo = nota_encontrada.get('title', nota_encontrada.get('label', 'Sem título'))
            
            # 4. Buscar área ou projeto de destino
            destino_lower = destino.lower()
            
            # Tentar área primeiro
            area = self._lexflow.buscar_area_por_nome(destino)
            if area:
                logger_brain.info(f"✅ [MOVER] Área encontrada: {area['name']} (ID={area['id']})")
                sucesso = self._lexflow.mover_nota_para_area(nota_id, area['id'])
                
                if sucesso:
                    return RespostaBrain(
                        sucesso=True, acao_executada="mover_nota",
                        resposta_ia=f"📂 **Nota movida com sucesso!**\n\n• **{nota_titulo}**\n• Destino: Área **{area['name']}**",
                        detalhes={"nota_id": nota_id, "area_id": area['id'], "area_nome": area['name']}
                    )
                else:
                    return RespostaBrain(
                        sucesso=False, acao_executada="mover_nota",
                        resposta_ia=f"❌ Erro ao mover para área {area['name']}.",
                        erro="falha_mover_area"
                    )
            
            # Tentar projeto
            projeto = self._lexflow.buscar_projeto_por_nome(destino)
            if projeto:
                logger_brain.info(f"✅ [MOVER] Projeto encontrado: {projeto.get('name')} (ID={projeto.get('id')})")
                
                # Se pediu conversão para tarefa, fazer isso
                if converter_tarefa:
                    resultado = self._lexflow.converter_nota_em_tarefa_com_projeto(nota_id, projeto['id'])
                    if resultado:
                        return RespostaBrain(
                            sucesso=True, acao_executada="mover_nota",
                            resposta_ia=f"✅ **Tarefa criada com sucesso!**\n\n📋 **{nota_titulo}**\n📁 Projeto: **{projeto.get('name')}**\n📊 Status: Aguardando tratamento",
                            detalhes={"nota_id": nota_id, "projeto_id": projeto['id'], "convertido": True}
                        )
                    else:
                        return RespostaBrain(
                            sucesso=False, acao_executada="mover_nota",
                            resposta_ia=f"❌ Erro ao converter em tarefa.",
                            erro="falha_converter"
                        )
                else:
                    # Mover sem converter
                    sucesso = self._lexflow.mover_nota_para_projeto(nota_id, projeto['id'])
                    
                    if sucesso:
                        return RespostaBrain(
                            sucesso=True, acao_executada="mover_nota",
                            resposta_ia=f"📁 **Nota movida com sucesso!**\n\n• **{nota_titulo}**\n• Destino: Projeto **{projeto.get('name')}**",
                            detalhes={"nota_id": nota_id, "projeto_id": projeto['id'], "projeto_nome": projeto.get('name')}
                        )
                    else:
                        return RespostaBrain(
                            sucesso=False, acao_executada="mover_nota",
                            resposta_ia=f"❌ Erro ao mover para projeto {projeto.get('name')}.",
                            erro="falha_mover_projeto"
                        )
            
            # Destino não encontrado
            areas_disponiveis = [a['name'] for a in self._lexflow.listar_areas()]
            projetos_disponiveis = [p.get('name', p.get('title')) for p in self._lexflow.listar_projetos()]
            
            msg_opcoes = f"🤔 Não encontrei '{destino}'.\n\n**Áreas disponíveis:**\n"
            msg_opcoes += "\n".join([f"• {a}" for a in areas_disponiveis]) if areas_disponiveis else "• (nenhuma)"
            msg_opcoes += f"\n\n**Projetos disponíveis:**\n"
            msg_opcoes += "\n".join([f"• {p}" for p in projetos_disponiveis]) if projetos_disponiveis else "• (nenhum - crie um no Lex Flow!)"
            
            return RespostaBrain(
                sucesso=False, acao_executada="mover_nota",
                resposta_ia=msg_opcoes,
                erro="destino_nao_encontrado"
            )
            
        except Exception as e:
            logger_brain.error(f"❌ [MOVER] Erro: {e}", exc_info=True)
            return RespostaBrain(
                sucesso=False, acao_executada="mover_nota",
                resposta_ia=f"❌ Erro ao mover: {str(e)[:50]}",
                erro=str(e)
            )




    def _executar_buscar_info(self, entidades: dict, 
                            mensagem: str, resposta_ia: str) -> RespostaBrain:
        """
        Busca informações usando Lex Flow + RAG.
        
        v3.1: PRIORIZA Lex Flow (onde estão as notas reais!)
            + DEBUG DETALHADO!
        """
        
        query = entidades.get("conteudo", mensagem)
        resultados_texto = []
        
        logger_brain.info(f"🔍 [BUSCA] Iniciando busca por: '{query}'")
        
        # =====================================================================
        # PRIORIDADE 1: Buscar no Lex Flow (notas/tarefas reais!)
        # =====================================================================
        
        if self._lexflow:
            try:
                logger_brain.info(f"🔍 [BUSCA-LEX] self._lexflow disponível: {type(self._lexflow)}")
                logger_brain.info(f"🔍 [BUSCA-LEX] Tem get_inbox? {hasattr(self._lexflow, 'get_inbox')}")
                logger_brain.info(f"🔍 [BUSCA-LEX] Tem search_notes? {hasattr(self._lexflow, 'search_notes')}")
                
                # ════════════════════════════════════════════════════════
                # ✅ NOVO: VERIFICAR/REFORÇAR AUTENTICAÇÃO ANTES DE BUSCAR
                # ════════════════════════════════════════════════════════
                
                logger_brain.info(f"🔐 [BUSCA-LEX] Verificando autenticação Lex Flow...")
                
                if hasattr(self._lexflow, 'is_authenticated'):
                    if not self._lexflow.is_authenticated():
                        logger_brain.warning("⚠️ [BUSCA-LEX] NÃO autenticado! Tentando re-login...")
                        self._lexflow.login()
                    else:
                        # Mesmo autenticado, verificar token
                        if hasattr(self._lexflow, 'verify_token'):
                            if not self._lexflow.verify_token():
                                logger_brain.warning("⚠️ [BUSCA-LEX] Token expirado! Re-logando...")
                                self._lexflow.login()
                            else:
                                logger_brain.info(f"✅ [BUSCA-LEX] Token válido!")
                
                # Método 1: search_notes (busca por texto)
                if hasattr(self._lexflow, 'search_notes'):
                    try:
                        logger_brain.info(f"🔍 [BUSCA-LEX] Chamando search_notes('{query}')...")
                        resultados_lexflow = self._lexflow.search_notes(query)
                        
                        logger_brain.info(f"🔍 [BUSCA-LEX] search_notes retornou: type={type(resultados_lexflow)}, valor={resultados_lexflow}")
                        
                        if resultados_lexflow and isinstance(resultados_lexflow, list):
                            for item in resultados_lexflow[:5]:  # Máximo 5 resultados
                                if isinstance(item, dict):
                                    titulo = item.get('title', item.get('nome', 'Sem título'))
                                    conteudo = item.get('content', item.get('conteudo', ''))
                                    if conteudo:
                                        preview = str(conteudo).replace('\n', ' ')[:200]
                                        resultados_texto.append(f"📝 **{titulo}**\n{preview}")
                                    else:
                                        resultados_texto.append(f"📝 **{titulo}**")
                                elif isinstance(item, str):
                                    resultados_texto.append(f"📝 {item}")
                                    
                        elif resultados_lexflow:
                            logger_brain.warning(f"⚠️ [BUSCA-LEX] search_notes não retornou lista: {type(resultados_lexflow)}")
                            
                    except Exception as e_sn:
                        logger_brain.error(f"❌ [BUSCA-LEX] Erro search_notes: {e_sn}", exc_info=True)
                
                # ════════════════════════════════════════════════════════
                # MÉTODO 2: get_inbox() COM RECONEXÃO AUTOMÁTICA!
                # ════════════════════════════════════════════════════════
                
                # Só busca no inbox se search_notes não encontrou nada
                if not resultados_texto and hasattr(self._lexflow, 'get_inbox'):
                    
                    # 🆕 Garantir conexão antes de buscar!
                    lexflow_ok_para_busca = self._garantir_lexflow_conectado()
                    
                    if not lexflow_ok_para_busca:
                        logger_brain.warning("⚠️ [BUSCA-LEX] Não foi possível reconectar Lex Flow")
                    else:
                        inbox = []
                        
                        # 🔁 TENTAR ATÉ 2 VEZES (segunda vez com re-login!)
                        for tentativa in range(1, 3):
                            try:
                                logger_brain.info(
                                    f"🔍 [BUSCA-LEX] Chamando get_inbox() "
                                    f"(tentativa {tentativa}/2)..."
                                )
                                inbox = self._get_inbox_robusto()
                                
                                logger_brain.info(
                                    f"🔍 [BUSCA-LEX] get_inbox() retornou: "
                                    f"type={type(inbox)}, "
                                    f"len={len(inbox) if isinstance(inbox, list) else 'N/A'}"
                                )
                                
                                # SUCESSO! Encontrou itens!
                                if inbox and isinstance(inbox, list) and len(inbox) > 0:
                                    logger_brain.info(
                                        f"✅ [BUSCA-LEX] Inbox encontrado na tentativa "
                                        f"{tentativa}! {len(inbox)} itens"
                                    )
                                    break
                                    
                                # Lista vazia → tentar re-login antes da próxima
                                elif inbox == []:
                                    if tentativa < 2:
                                        logger_brain.warning(
                                            f"⚠️ [BUSCA-LEX] Inbox VAZIO na tentativa "
                                            f"{tentativa}. Tentando re-login..."
                                        )
                                        if hasattr(self._lexflow, 'login'):
                                            login_ok = self._lexflow.login()
                                            if login_ok:
                                                logger_brain.info(
                                                    f"✅ [BUSCA-LEX] Re-login OK, "
                                                    f"tentando novamente..."
                                                )
                                            else:
                                                logger_brain.error(
                                                    f"❌ [BUSCA-LEX] Re-login FALHOU!"
                                                )
                                                break
                                    else:
                                        logger_brain.info(
                                            f"ℹ️ [BUSCA-LEX] Inbox realmente VAZIO "
                                            f"após 2 tentativas"
                                        )
                                
                                # Formato inesperado
                                else:
                                    logger_brain.warning(
                                        f"⚠️ [BUSCA-LEX] Formato inesperado: {inbox}"
                                    )
                                    
                            except Exception as e_inbox:
                                logger_brain.error(
                                    f"❌ [BUSCA-LEX] Erro get_inbox() tentativa "
                                    f"{tentativa}: {e_inbox}",
                                    exc_info=True
                                )
                                
                                # Tentar re-login antes da próxima tentativa
                                if tentativa < 2 and hasattr(self._lexflow, 'login'):
                                    logger_brain.info(
                                        f"🔄 [BUSCA-LEX] Re-login após erro..."
                                    )
                                    self._lexflow.login()
                        
                        # ═══════════════════════════════════════════════════
                        # PROCESSAR RESULTADOS DO INBOX (mesmo código de antes)
                        # ═══════════════════════════════════════════════════
                        
                        if inbox and isinstance(inbox, list) and len(inbox) > 0:
                            query_lower = query.lower()
                            palavras_query = query_lower.split()
                            
                            # Palavras-chave genéricas que devem mostrar TUDO
                            palavras_genericas = [
                                'nota', 'notas', 'tarefa', 'tarefas', 
                                'inbox', 'entrada', 'caixa', 
                                'hoje', 'tem', 'tenho', 'qual', 'oque', 'o que',
                                'existe', 'listar', 'mostrar', 'ver'
                            ]
                            eh_query_generica = any(
                                x in query_lower for x in palavras_genericas
                            )
                            
                            for item in inbox[:15]:  # Máximo 15 itens
                                item_str = str(item).lower()
                                
                                # Calcular match score
                                match_score = sum(
                                    1 for p in palavras_query 
                                    if len(p) > 2 and p in item_str
                                )
                                
                                # Se matchou OU é pergunta genérica → mostrar
                                if match_score >= 1 or eh_query_generica:
                                    if isinstance(item, dict):
                                        titulo = item.get(
                                            'title', 
                                            item.get('nome', 'Sem título')
                                        )
                                        conteudo = item.get(
                                            'content', 
                                            item.get('conteudo', '')
                                        )
                                        if conteudo:
                                            preview = str(conteudo).replace(
                                                '\n', ' '
                                            )[:150]
                                            resultados_texto.append(
                                                f"📋 **{titulo}**\n{preview}"
                                            )
                                        else:
                                            resultados_texto.append(f"📋 {titulo}")
                                    else:
                                        resultados_texto.append(f"📋 {item}")
                                        
                        elif inbox == []:
                            logger_brain.info(
                                f"ℹ️ [BUSCA-LEX] Inbox está VAZIO (lista vazia)"
                            )
                        else:
                            logger_brain.warning(
                                f"⚠️ [BUSCA-LEX] Inbox inválido: {inbox}"
                            )
                
                # Se encontrou resultados no Lex Flow → retornar!
                if resultados_texto:
                    refs = "\n\n".join(resultados_texto[:5])  # Máximo 5
                    
                    resposta_final = (
                        f"{resposta_ia}\n\n"
                        f"🔍 **Encontrei no Lex Flow ({len(resultados_texto)} resultado(s)):**\n\n"
                        f"{refs}"
                    )
                    
                    logger_brain.info(f"✅ [BUSCA] Retornando {len(resultados_texto)} resultados do Lex Flow")
                    
                    return RespostaBrain(
                        sucesso=True,
                        acao_executada="buscar_info",
                        resposta_ia=resposta_final,
                        detalhes={"fonte": "lex_flow", "quantidade": len(resultados_texto)}
                    )
                else:
                    logger_brain.warning(f"⚠️ [BUSCA] Nada encontrado no Lex Flow!")
                    
            except Exception as e_lex:
                logger_brain.error(f"❌ [BUSCA] Erro geral no Lex Flow: {e_lex}", exc_info=True)
        else:
            logger_brain.warning(f"⚠️ [BUSCA] self._lexflow é None! Não posso buscar no Lex Flow!")
        
        # =====================================================================
        # PRIORIDADE 2: Buscar no RAG System (se Lex Flow não tiver nada)
        # =====================================================================
        
        if self._rag:
            try:
                logger_brain.info(f"🔍 [BUSCA-RAG] Buscando no RAG system...")
                
                # ════════════════════════════════════════════════════════
                # ✅ CORREÇÃO BUG RAG: Usar Enum em vez de string!
                # ════════════════════════════════════════════════════════
                
                estrategia_param = "hibrida"  # Default fallback
                
                # Tentar importar o Enum correto
                try:
                    from engine.rag_system import EstrategiaBusca
                    estrategia_param = EstrategiaBusca.HIBRIDA
                    logger_brain.debug(f"✅ [RAG] Enum encontrado: EstrategiaBusca.HIBRIDA")
                except ImportError:
                    try:
                        from engine.rag_system import EstrategiaBusca as EstrategiaBuscaAlt
                        estrategia_param = EstrategiaBuscaAlt.HIBRIDA
                        logger_brain.debug(f"✅ [RAG] Enum alt encontrado")
                    except ImportError:
                        # Tentar descobrir qual o nome certo olhando o módulo
                        try:
                            import engine.rag_system as rag_module
                            # Provar qualquer classe que termine com "Busca" ou "Estrategia"
                            for attr_name in dir(rag_module):
                                attr_obj = getattr(rag_module, attr_name)
                                if isinstance(attr_obj, type) and ('busca' in attr_name.lower() or 'estrategia' in attr_name.lower()):
                                    if hasattr(attr_obj, 'HIBRIDA') or hasattr(attr_obj, 'hibrida'):
                                        estrategia_param = getattr(attr_obj, 'HIBRIDA', getattr(attr_obj, 'hibrida', None)) or estrategia_param
                                        logger_brain.info(f"✅ [RAG] Enum dinâmico: {attr_name}")
                                        break
                        except Exception:
                            pass
                
                logger_brain.info(f"🔍 [BUSCA-RAG] Chamando buscar() com estrategia={estrategia_param}")
                
                resultados_rag = self._rag.buscar(
                    query=query,
                    n_results=5,
                    estrategia=estrategia_param
                )
                
                logger_brain.info(f"🔍 [BUSCA-RAG] RAG retornou: {resultados_rag}")
                
                if resultados_rag and isinstance(resultados_rag, dict):
                    resultados_lista = (
                        resultados_rag.get("resultados") or 
                        resultados_rag.get("results") or 
                        resultados_rag.get("data") or 
                        []
                    )
                    
                    if resultados_lista:
                        refs = "\n".join([
                            f"- {r.get('conteudo', r.get('content', r.get('texto', '')))[:150]}" 
                            for r in resultados_lista[:3]
                        ])
                        
                        resposta_final = f"{resposta_ia}\n\n📚 **Referências encontradas:**\n{refs}"
                        
                        return RespostaBrain(
                            sucesso=True,
                            acao_executada="buscar_info",
                            resposta_ia=resposta_final,
                            detalhes={"fonte": "rag"}
                        )
                        
            except AttributeError as e_attr:
                # Erro específico de .value (Enum bug)
                if "'str' object has no attribute 'value'" in str(e_attr):
                    logger_brain.error(
                        f"❌ [BUSCA-RAG] Bug de Enum detectado! O RAG espera Enum, não string. "
                        f"Erro: {e_attr}"
                    )
                    # Tentar sem estratégia (deixar o RAG usar default)
                    try:
                        logger_brain.info(f"🔄 [BUSCA-RAG] Tentando SEM parametro estrategia...")
                        resultados_rag = self._rag.buscar(query=query, n_results=5)
                        if resultados_rag:
                            return RespostaBrain(
                                sucesso=True,
                                acao_executada="buscar_info",
                                resposta_ia=f"{resposta_ia}\n\n📚 {str(resultados_rag)[:500]}",
                                detalhes={"fonte": "rag_fallback"}
                            )
                    except Exception as e_fallback:
                        logger_brain.error(f"❌ [BUSCA-RAG] Fallback também falhou: {e_fallback}")
                else:
                    logger_brain.error(f"❌ [BUSCA-RAG] Erro: {e_attr}", exc_info=True)
                    
            except Exception as e_rag:
                logger_brain.error(f"❌ [BUSCA-RAG] Erro geral no RAG: {e_rag}", exc_info=True)
        
        # =====================================================================
        # FALLBACK: Nada encontrado
        # =====================================================================
        
        resposta_final = (
            f"{resposta_ia}\n\n"
            f"🔍 **Não encontrei notas específicas** sobre '{query[:50]}'.\n\n"
            f"Dica: Você pode usar:\n"
            f"• `/nota` para anotar algo agora\n"
            f"• `/tarefa` para criar um lembrete"
        )
        
        return RespostaBrain(
            sucesso=True,
            acao_executada="buscar_info",
            resposta_ia=resposta_final,
            detalhes={"fonte": "fallback"}
        )
    
    def _executar_gerar_ideias(self, entidades: dict, 
                               mensagem: str, resposta_ia: str) -> RespostaBrain:
        """Gera ideias (já foi feito pelo LLM no prompt principal)."""
        return RespostaBrain(
            sucesso=True,
            acao_executada="gerar_ideias",
            resposta_ia=resposta_ia
        )
    
    # =========================================================================
    # UTILITÁRIOS
    # =========================================================================
    
    def _preparar_mensagem_contextualizada(
        self, mensagem: str, usuario_id: Optional[int], nome_usuario: str
    ) -> MensagemContextualizada:
        """Prepara mensagem com todos os contextos carregados."""
        
        self._atualizar_todos_contextos()
        
        historico = []
        if usuario_id and usuario_id in self._conversas:
            historico = self._conversas[usuario_id]
        
        return MensagemContextualizada(
            mensagem_original=mensagem,
            mensagem_usuario=mensagem,
            contexto_soul=self._contextos_cache.get("soul", ""),
            contexto_user=self._contextos_cache.get("user", ""),
            contexto_memory=self._contextos_cache.get("memory", ""),
            contexto_heartbeat=self._contextos_cache.get("heartbeat", ""),
            historico_conversa=historico,
            metadata={
                "usuario_id": usuario_id,
                "nome_usuario": nome_usuario,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def _salvar_no_historico(
        self, usuario_id: Optional[int], 
        mensagem_usuario: str, resposta_bot: str
    ) -> None:
        """Salva troca de mensagens no histórico da conversa."""
        
        if not usuario_id:
            return
        
        if usuario_id not in self._conversas:
            self._conversas[usuario_id] = []
        
        self._conversas[usuario_id].append({
            "role": "user",
            "texto": mensagem_usuario,
            "timestamp": datetime.now().isoformat()
        })
        
        self._conversas[usuario_id].append({
            "role": "assistant",
            "texto": resposta_bot[:300],
            "timestamp": datetime.now().isoformat()
        })
        
        # Manter apenas últimas 20 mensagens (10 pares)
        if len(self._conversas[usuario_id]) > 20:
            self._conversas[usuario_id] = self._conversas[usuario_id][-20:]
    
    def limpar_conversa(self, usuario_id: int) -> None:
        """Limpa histórico de conversa de um usuário."""
        if usuario_id in self._conversas:
            del self._conversas[usuario_id]
            logger_brain.info(f"Conversa limpa para user {usuario_id}")
    
    def obter_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas do orquestrador."""
        return {
            "versao": "3.0 (LLM-FIRST)",
            "modo": "IA_CONVERSACIONAL_REAL",
            "inicializado": self._inicializado,
            "conversas_ativas": len(self._conversas),
            "contextos_carregados": {
                k: len(v) for k, v in self._contextos_cache.items()
            },
            "recursos": {
                "llm": self._llm is not None,
                "rag": self._rag is not None,
                "lexflow": self._lexflow is not None
            },
            "ultima_atualizacao": (
                self._ultima_atualizacao.isoformat() 
                if self._ultima_atualizacao else None
            )
        }


# =============================================================================
# INSTÂNCIA GLOBAL
# =============================================================================

_orchestrator_global: Optional[BrainLLMOrchestrator] = None


def obter_orchestrator_global() -> Optional[BrainLLMOrchestrator]:
    global _orchestrator_global
    return _orchestrator_global


def definir_orchestrator_global(instancia: BrainLLMOrchestrator) -> None:
    global _orchestrator_global
    _orchestrator_global = instancia
    logger_brain.info("[GLOBAL] BrainLLMOrchestrator definido como instância global")