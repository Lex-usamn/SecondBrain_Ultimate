"""
Lex Flow Connector v1.0 - Gestão de Conexão Robusta
==================================================

Responsabilidade ÚNICA:
- Manter conexão Lex Flow sempre saudável
- Reconexão automática quando cai
- get_inbox() com múltiplos fallbacks (contorna bug _unwrap_list)

Autor: Mago-Usamn | Extraído do BrainLLMOrchestrator v3.0
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger_brain = logging.getLogger("brain.lexflow_connector")


class LexFlowConnector:
    """
    Gerenciador de conexão Lex Flow.
    
    Problemas que resolve:
    - Sessão HTTP perdida/expirada
    - Token inválido silencioso  
    - Instância corrompida
    - Bug do _unwrap_list() que não extrai chave 'notes'
    
    Uso:
        connector = LexFlowConnector()
        connector.inicializar(lexflow_client)
        
        # Garante conectado (reconecta se necessário)
        if connector.garantir_conectado():
            inbox = connector.get_inbox_robusto()
    """
    
    def __init__(self):
        self._lexflow = None
        self._config = {
            "base_url": "https://flow.lex-usamn.com.br",
            "username": "Lex-Usamn",
            "password": "Lex#157."
        }
        
        # Métricas de reconexão
        self._ultima_reconexao: Optional[datetime] = None
        self._reconexoes_hoje = 0
        
        logger_brain.info("[LEX-FLOW-CONNECTOR] Instanciado")
    
    # =========================================================================
    # PROPRIEDADES PÚBLICAS
    # =========================================================================
    
    @property
    def client(self):
        """Retorna instância ativa do LexFlowClient (ou None)."""
        return self._lexflow
    
    @property
    def esta_conectado(self) -> bool:
        """Verifica se há instância e está autenticada."""
        if not self._lexflow:
            return False
        
        try:
            if hasattr(self._lexflow, 'is_authenticated'):
                return self._lexflow.is_authenticated()
            return True  # Se não tem método, assume OK
        except:
            return False
    
    # =========================================================================
    # INICIALIZAÇÃO
    # =========================================================================
    
    def inicializar(self, lexflow_client=None) -> bool:
        """
        Inicializa conector com cliente existente ou cria novo.
        
        Args:
            lexflow_client: Instância opcional de LexFlowClient
            
        Returns:
            True se inicializou com sucesso
        """
        if lexflow_client:
            self._lexflow = lexflow_client
            logger_brain.info(
                f"✅ [LEX-FLOW] Cliente recebido via injeção "
                f"(id={id(lexflow_client)})"
            )
            return True
        
        # Criar novo cliente
        return self._recriar_cliente()
    
    # =========================================================================
    # GARANTIR CONEXÃO (RECONEXÃO AUTOMÁTICA)
    # =========================================================================
    
    def garantir_conectado(self) -> bool:
        """
        Garante que Lex Flow está conectado e funcionando.
        
        Estratégia:
        1. Verifica se instância existe
        2. Testa autenticação
        3. Testa get_inbox()
        4. Tenta re-login se inbox vazio
        5. Recria cliente como última opção
        
        Returns:
            True se conectado e funcionando, False se falhou tudo
        """
        
        # PASSO 1: Sem instância?
        if not self._lexflow:
            logger_brain.warning(
                "🔌 [RECONEXÃO] self._lexflow é None! "
                "Tentando criar nova instância..."
            )
            return self._recriar_cliente()
        
        # PASSO 2: Testar instância atual
        try:
            logger_brain.info(
                f"🔍 [RECONEXÃO] Testando Lex Flow "
                f"(id={id(self._lexflow)})..."
            )
            
            # Testar autenticação
            if hasattr(self._lexflow, 'is_authenticated'):
                if not self._lexflow.is_authenticated():
                    logger_brain.warning(
                        "⚠️ [RECONEXÃO] Não autenticado! Reconectando..."
                    )
                    return self._recriar_cliente()
            
            # Testar inbox
            inbox_teste = self.get_inbox_robusto()
            
            logger_brain.info(
                f"🔍 [RECONEXÃO] get_inbox(): "
                f"type={type(inbox_teste)}, "
                f"len={len(inbox_teste) if isinstance(inbox_teste, list) else 'N/A'}"
            )
            
            # SUCESSO!
            if inbox_teste and isinstance(inbox_teste, list) and len(inbox_teste) > 0:
                logger_brain.info(
                    f"✅ [RECONEXÃO] Lex Flow OK! "
                    f"{len(inbox_teste)} itens"
                )
                return True
            
            # Lista vazia → tentar re-login
            logger_brain.warning(
                "⚠️ [RECONEXÃO] Inbox vazio. Tentando re-login..."
            )
            
            if hasattr(self._lexflow, 'login'):
                login_ok = self._lexflow.login()
                
                if login_ok:
                    inbox_apos_login = self.get_inbox_robusto()
                    
                    if inbox_apos_login and isinstance(inbox_apos_login, list) \
                       and len(inbox_apos_login) > 0:
                        logger_brain.info(
                            f"✅ [RECONEXÃO] Re-login funcionou! "
                            f"{len(inbox_apos_login)} itens"
                        )
                        return True
            
            # Re-login não resolveu → recriar
            logger_brain.warning(
                "❌ [RECONEXÃO] Re-login falhou! Recriando instância..."
            )
            return self._recriar_cliente()
            
        except Exception as e:
            logger_brain.error(
                f"❌ [RECONEXÃO] Erro testando: {e}",
                exc_info=True
            )
            return self._recriar_cliente()
    
    def _recriar_cliente(self) -> bool:
        """
        Recria cliente Lex Flow do zero (SOLUÇÃO NUCLEAR).
        
        Usa quando:
        - Sessão corrompida
        - Token expirado que não renova
        - Problemas persistentes de conexão
        
        Returns:
            True se conseguiu recriar e testar com sucesso
        """
        try:
            logger_brain.info("🔄 [RECONEXÃO] Importando LexFlowClient...")
            
            from integrations.lex_flow_definitivo import (
                LexFlowClient,
                LexFlowConfig
            )
            
            logger_brain.info("🔄 [RECONEXÃO] Criando configuração...")
            config = LexFlowConfig(**self._config)
            
            logger_brain.info("🔄 [RECONEXÃO] Instanciando...")
            novo_cliente = LexFlowClient(config)
            
            # Verificar autenticação
            if not novo_cliente or not novo_cliente.is_authenticated():
                logger_brain.error("❌ [RECONEXÃO] Novo cliente não autenticou!")
                return False
            
            # Testar inbox
            logger_brain.info("🔄 [RECONEXÃO] Testando inbox...")
            inbox_novo = self.get_inbox_robusto(novo_cliente)
            
            if inbox_novo and isinstance(inbox_novo, list) and len(inbox_novo) > 0:
                # SUCESSO!
                self._lexflow = novo_cliente
                self._ultima_reconexao = datetime.now()
                self._reconexoes_hoje += 1
                
                logger_brain.info(
                    f"✅ [RECONEXÃO] SUCESSO! Cliente substituído "
                    f"(novo id={id(self._lexflow)}, "
                    f"{self._reconexoes_hoje} reconexões hoje)"
                )
                return True
            else:
                logger_brain.error(
                    f"❌ [RECONEXÃO] Novo cliente inbox vazio: {inbox_novo}"
                )
                return False
                
        except ImportError as e:
            logger_brain.error(f"❌ [RECONEXÃO] Erro importando: {e}")
            return False
            
        except Exception as e:
            logger_brain.error(
                f"❌ [RECONEXÃO] Erro recriando: {e}",
                exc_info=True
            )
            return False
    
    # =========================================================================
    # GET_INBOX ROBUSTO (MÚLTIPLAS ESTRATÉGIAS)
    # =========================================================================
    
    def get_inbox_robusto(self, cliente=None) -> List[Dict]:
        """
        Busca inbox com múltiplas estratégias de fallback.
        
        Contorna bug do _unwrap_list() que não extrai chave 'notes'.
        
        A API real retorna: {"notes": [...]}
        Mas _unwrap_list() só procurava: ['data','projects','items',...]
        
        Args:
            cliente: Instância opcional (usa self._lexflow se None)
            
        Returns:
            Lista de dicionários com notas (ou lista vazia)
        """
        
        cliente = cliente or self._lexflow
        
        if not cliente:
            logger_brain.warning("⚠️ [INBOX] Cliente é None!")
            return []
        
        try:
            # ================================================================
            # ESTRATÉGIA 1: get_inbox() normal
            # ================================================================
            
            resultado = cliente.get_inbox()
            
            if resultado and isinstance(resultado, list) and len(resultado) > 0:
                logger_brain.info(
                    f"✅ [INBOX] Normal funcionou: {len(resultado)} itens"
                )
                return resultado
            
            # ================================================================
            # ESTRATÉGIA 2: _request direto (pula _unwrap_list!)
            # ================================================================
            
            logger_brain.warning(
                f"⚠️ [INBOX] get_inbox() vazio "
                f"(type={type(resultado)}, valor={str(resultado)[:100]}). "
                f"Tentando _request() direto..."
            )
            
            if hasattr(cliente, '_request'):
                resposta_crua = cliente._request('GET', '/quicknotes/')
                
                logger_brain.info(
                    f"🔍 [INBOX] Resposta crua: type={type(resposta_crua)}"
                )
                
                # API retorna {"notes": [...]}
                if isinstance(resposta_crua, dict):
                    # PRIMEIRO: Chave REAL 'notes'!
                    if 'notes' in resposta_crua:
                        notas = resposta_crua['notes']
                        if isinstance(notas, list) and len(notas) > 0:
                            logger_brain.info(
                                f"✅ [INBOX] Via 'notes': {len(notas)} itens!"
                            )
                            return notas
                    
                    # Outras chaves conhecidas
                    for chave in ['data', 'quicknotes', 'items', 'results']:
                        if chave in resposta_crua:
                            valor = resposta_crua[chave]
                            if isinstance(valor, list) and len(valor) > 0:
                                logger_brain.info(
                                    f"✅ [INBOX] Via '{chave}': "
                                    f"{len(valor)} itens"
                                )
                                return valor
                    
                    # Logar chaves disponíveis
                    logger_brain.warning(
                        f"⚠️ [INBOX] Dict sem lista válida. "
                        f"Chaves: {list(resposta_crua.keys())}"
                    )
                
                elif isinstance(resposta_crua, list):
                    logger_brain.info(
                        f"✅ [INBOX] Já era lista: "
                        f"{len(resposta_crua)} itens"
                    )
                    return resposta_crua
            
            # ================================================================
            # ESTRATÉGIA 3: search_notes fallback
            # ================================================================
            
            logger_brain.warning(
                "⚠️ [INBOX] Tentando search_notes('*')..."
            )
            
            if hasattr(cliente, 'search_notes'):
                todas_notas = cliente.search_notes("*") or []
                if todas_notas:
                    logger_brain.info(
                        f"✅ [INBOX] search_notes: {len(todas_notas)} itens"
                    )
                    return todas_notas
            
            # ================================================================
            # FALHA TOTAL
            # ================================================================
            
            logger_brain.error("❌ [INBOX] Todas as estratégias falharam!")
            return []
            
        except Exception as e:
            logger_brain.error(
                f"❌ [INBOX] Erro: {e}",
                exc_info=True
            )
            return []
    
    # =========================================================================
    # UTILITÁRIOS E STATUS
    # =========================================================================
    
    def verificar_disponibilidade(self) -> Dict[str, Any]:
        """Retorna status detalhado da conexão."""
        return {
            "conectado": self._lexflow is not None,
            "autenticado": self.esta_conectado,
            "itens_inbox": (
                len(self.get_inbox_robusto()) 
                if self._lexflow else 0
            ),
            "ultima_reconexao": (
                self._ultima_reconexao.isoformat() 
                if self._ultima_reconexao else None
            ),
            "reconexoes_hoje": self._reconexoes_hoje,
            "client_id": (
                id(self._lexflow) 
                if self._lexflow else None
            )
        }
    
    def __repr__(self) -> str:
        status = "CONECTADO" if self.esta_conectado else "DESCONECTADO"
        return f"<LexFlowConnector [{status}]>"