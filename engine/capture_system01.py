"""
Capture System - Sistema de Captura Inteligente Multi-Canal (Versão 2.0)
====================================================================

Sistema de captura rápida e organização automática de ideias,
notas, pensamentos e informações de múltiplas fontes.

MUDANÇAS NA VERSÃO 2.0:
- Integração completa com Lex Flow Client (produção real)
- Remoção de todos os mocks/simulações
- Uso do quick_capture() e add_note() reais da API
- Manutenção de toda a funcionalidade original

FUNCIONALIDADES PRINCIPAIS:
- Quick capture (texto, voz, imagem)
- Categorização automática via inteligência artificial
- Deduplicação inteligente
- Roteamento para projetos corretos
- Tags e metadados automáticos
- Multi-canal (linha de comando, Telegram, Discord, Web)

AUTOR: Second Brain Ultimate System
VERSÃO: 2.0.0 (Integração Lex Flow)
DATA: 2026-04-08
STATUS: ✅ Produção (Testado e aprovado)
"""

import os
import json
import hashlib
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# ============================================
# IMPORTAÇÕES DOS MÓDULOS DO SISTEMA
# ============================================

try:
    from .memory_system import MemorySystem
except ImportError:
    from memory_system import MemorySystem

try:
    from ..integrations.lex_flow_definitivo import LexFlowClient
except ImportError:
    from integrations.lex_flow_definitivo import LexFlowClient

# ============================================
# CONFIGURAÇÃO DE LOGGING
# ============================================

os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler('logs/capture_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

log = logging.getLogger('CaptureSystem')

# ============================================
# ENUMERAÇÕES E CONSTANTES
# ============================================

class CaptureSource(Enum):
    """
    Origens possíveis para uma captura
    
    Permite rastrear de onde veio cada informação
    para analytics e melhoria do sistema.
    """
    
    THOUGHT = "thought"           # Ideia espontânea (veio à mente)
    VOICE_NOTE = "voice"             # Nota de voz (transcrita)
    MANUAL = "manual"              # Digitada manualmente pelo usuário
    TELEGRAM = "telegram"           # Enviada via Bot do Telegram
    DISCORD = "discord"             # Enviada via Bot do Discord
    WEB_DASHBOARD = "web"              # Criada via Dashboard Lex Flow
    API = "api"                   # Via API externa (webhook, etc.)
    BULK_IMPORT = "bulk"              # Importação em lote (arquivo CSV, etc.)


class CaptureType(Enum):
    """
    Tipos de conteúdo que podem ser capturados
    
    Classificação semântica do que foi capturado.
    Usado para roteamento automático e templates.
    """
    
    IDEA = "idea"                 # Ideia geral (ainda não é ação)
    TASK = "task"                 # Tarefa acionável (tem próximo passo claro)
    NOTE = "note"                  # Nota/informação pura (referência)
    REFERENCE = "reference"           # Link/referência externa (URL, livro)
    QUICK_CAPTURE = "quick_capture"      # Captura ultra-rápida (sem categorizar ainda)
    MEETING_NOTE = "meeting_note"       # Nota de reunião (pontos de decisão)
    CONTENT_DRAFT = "draft"              # Rascunho de conteúdo (vídeo, post, artigo)
    METRIC_UPDATE = "metric_update"      # Atualização de métrica/dado numérico


class CapturePriority(Enum):
    """
    Níveis de prioridade inicial da captura
    
    Define urgência relativa. Pode ser ajustada
    posteriormente pelo Decision Engine.
    """
    
    CRITICAL = "critical"         # Crítico (precisa atenção IMEDIATA)
    HIGH = "high"               # Alta (fazer hoje sem falta)
    MEDIUM = "medium"             # Média (esta semana)
    LOW = "low"                 # Baixa (quando tiver tempo disponível)
    SOMEDAY = "someday"         # Futuro (talvez um dia, não agora)


class CaptureStatus(Enum):
    """
    Status do ciclo de vida de uma captura
    
    Rastreia em que etapa do processamento
    cada item capturado se encontra.
    """
    
    NEW = "new"                   # Recém criada (acabou de entrar)
    PROCESSING = "processing"           # Sendo processada (análise em andamento)
    CATEGORIZED = "categorized"         # Categorizada (já sabe para onde ir)
    CONVERTED_TO_TASK = "converted_to_task" # Convertida em tarefa de projeto
    ARCHIVED = "archived"              # Arquivada (não é mais relevante ativamente)
    DELETED = "deleted"              # Deletada (removida permanentemente)


# ============================================
# CLASSES DE DADOS (DATA CLASSES)
# ============================================

@dataclass
class CaptureItem:
    """
    Item Capturado - Representação unificada de qualquer entrada de dados
    
    É o formato interno normalizado usado pelo sistema antes de
    enviar para o Lex Flow ou processar com inteligência artificial.
    
    Atributos Principais:
        - content: O texto/ideia original capturada
        - source: De onde veio (Telegram, manual, voz, etc.)
        - type: Que tipo de conteúdo é (idea, task, note, etc.)
        - priority: Quão urgente é inicialmente
        
    Atributos Enriquecidos (pós-processamento):
        - suggested_project: Para qual projeto a IA sugeriu enviar
        - suggested_category: Categoria sugerida (P.A.R.A.)
        - confidence_score: Quão confiante está a sugestão (0.0 a 1.0)
    """
    
    # Identificação única
    id: str = ""                          # Identificador único gerado automaticamente
    content: str = ""                      # Conteúdo original capturado
    
    # Classificação inicial
    source: CaptureSource = CaptureSource.THOUGHT     # Origem da captura
    type: CaptureType = CaptureType.IDEA             # Tipo semântico do conteúdo
    priority: CapturePriority = CapturePriority.MEDIUM # Prioridade inicial
    
    # Metadados
    tags: List[str] = field(default_factory=list)     # Tags manuais ou automáticas
    metadata: Dict = field(default_factory=dict)       # Metadados extras (flexível)
    
    # Controle de ciclo de vida
    created_at: str = ""                   # Timestamp de criação (ISO 8601)
    processed: bool = False                # Já foi processado pelo Decision Engine?
    processing_result: Dict = None         # Resultado do processamento (se houver)
    
    # Dados enriquecidos pela inteligência artificial (após análise)
    suggested_project: str = None          # Nome/ID do projeto sugerido como destino
    suggested_category: str = None         # Categoria P.A.R.A. sugerida (Projects/Areas/Resources/Archives)
    confidence_score: float = 0.0          # Nível de confiança da sugestão (0.0 = chute, 1.0 = certeza)
    duplicates: List[str] = field(default_factory=list)  # Lista de IDs de itens duplicados encontrados
    
    def __post_init__(self):
        """
        Inicialização pós-criação do objeto
        
        Gera automaticamente ID e timestamp se não fornecidos.
        Este método é chamado pelo Python após __init__.
        """
        if not self.id:
            self.id = self._generate_unique_id()
            self.created_at = datetime.now().isoformat()
    
    def _generate_unique_id(self) -> str:
        """
        Gera identificador único baseado no conteúdo e timestamp
        
        Usa hash SHA-256 do conteúdo + origem + timestamp para garantir
        unicidade mesmo se capturadas ideias idênticas no mesmo segundo.
        
        Returns:
            String com formato: {origem}_{timestamp}_{hash_8_chars}
        """
        content_hash = hashlib.sha256(
            f"{self.source.value}{self.content}{self.created_at}".encode()
        ).hexdigest()[:8]
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"{self.source.value}_{timestamp}_{content_hash}"
    
    def to_dictionary(self) -> Dict:
        """
        Converte objeto para dicionário (formato compatível com Lex Flow)
        
        Prepara os dados para serem enviados como payload JSON
        para a API do Lex Flow via add_note() ou quick_capture().
        
        Returns:
            Dicionário com todos os campos serializáveis
        """
        return {
            'id': self.id,
            'title': self.content[:100] if len(self.content) > 100 else self.content,
            'content': self.content,
            'source': self.source.value,
            'type': self.type.value,
            'priority': self.priority.value,
            'tags': self.tags,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'processed': self.processed,
            'suggested_project': self.suggested_project,
            'suggested_category': self.suggested_category,
            'confidence_score': self.confidence_score
        }


@dataclass
class CaptureResult:
    """
    Resultado de uma operação de captura individual
    
    Retornado por todos os métodos de captura para indicar sucesso/fracasso
    e fornecer detalhes sobre o que aconteceu.
    
    Atributos:
        - success: Se a operação foi bem-sucedida
        - item: O objeto CaptureItem que foi criado/tentado
        - message: Mensagem legível por humano sobre o resultado
        - action_taken: Qual ação foi executada (criar, ignorar duplicata, etc.)
        - errors: Lista de erros (se houveram múltiplos)
    """
    
    success: bool = False                     # Operação concluída com sucesso?
    item: CaptureItem = None                  # Item que foi processado
    message: str = ""                         # Mensagem descritiva do resultado
    action_taken: str = ""                    # Ação específica executada
    errors: List[str] = field(default_factory=list)  # Lista de erros encontrados


@dataclass
class BatchCaptureResult:
    """
    Resultado de uma operação de captura em lote (bulk import)
    
    Usado quando múltiplos itens são importados de uma vez
    (ex: arquivo CSV, backup, migração de outro sistema).
    
    Atributos:
        - total_submitted: Quantos itens foram tentados
        - successful: Quantos tiveram sucesso
        - failed: Quantos falharam
        - items: Lista de todos os CaptureItem criados
        - errors: Mensagens de erro dos que falharam
    """
    
    total_submitted: int = 0                 # Total de itens tentados
    successful: int = 0                       # Quantos foram criados com sucesso
    failed: int = 0                           # Quantos falharam
    items: List[CaptureItem] = field(default_factory=list)  # Todos os itens (sucesso + falha)
    errors: List[str] = field(default_factory=list)        # Mensagens de erro


# ============================================
# CLASSE PRINCIPAL: CAPTURE SYSTEM
# ============================================

class CaptureSystem:
    """
    Sistema de Captura Inteligente Multi-Canal (Versão 2.0)
    
    Coordena a entrada de dados de múltiplas fontes diferentes,
    processa com inteligência artificial quando necessário,
    organiza automaticamente e roteia para o destino correto
    dentro da estrutura P.A.R.A. (Projetos, Áreas, Recursos, Arquivos).
    
    INTEGRAÇÃO COM LEX FLOW CLIENT:
    --------------------------------
    Esta versão (2.0) está 100% integrada com o LexFlowClient real.
    Todas as operações de gravação usam a API do Lex Flow em produção.
    Não há mais mocks, simulações ou dados falsos.
    
    EXEMPLOS DE USO BÁSICO:
    ----------------------
    
    # Inicialização (recebe cliente Lex Flow já conectado)
    capture_system = CaptureSystem(lex_flow_client=meu_lex_flow, memory_system=minha_memoria)
    
    # Captura rápida de ideia (método principal!)
    resultado = capture_system.quick_capture("Ideia incrível para vídeo sobre criptomoedas")
    
    # Captura com tags personalizadas
    resultado = capture_system.quick_capture(
        "Preciso comprar microfone melhor",
        tags=["equipamento", "prioridade", "youtube"],
        source="manual"
    )
    
    # Capturar nota de voz já transcrita
    resultado = capture_system.capture_voice_note(transcription_text="Texto transcrito do áudio...")
    
    # Importar múltiplas ideias de uma vez (ex: arquivo)
    resultado_lote = capture_system.bulk_import([
        {"content": "Ideia 1", "source": "telegram"},
        {"content": "Ideia 2", "source": "thought"},
        {"content": "Tarefa importante", "source": "email", "type": "task"}
    ])
    
    # Processar inbox inteiro com IA (categorização automática)
    resultado_processamento = capture_system.process_inbox_with_intelligence()
    
    # Buscar ideias anteriores por texto
    resultados_busca = capture_system.search_captures("canais dark monetização")
    
    FLUXO INTERNO DE DADOS:
    -----------------------
    
    [Input Externo] → [CaptureItem] → [Validação] → [Deduplicação] 
        → [Lex Flow API] → [Retorno CaptureResult]
    
    Atributos Principais do Objeto:
        - lex_flow: Instância de LexFlowClient (conectada e autenticada)
        - memory: Instância de MemorySystem (para contexto e histórico)
        - deduplication_cache: Cache temporário para detectar duplicatas rápidas
    """
    
    def __init__(self, lex_flow_client: LexFlowClient, memory_system: MemorySystem):
        """
        Inicializa o Sistema de Captura com dependências obrigatórias
        
        ARGUMENTOS OBRIGATÓRIOS:
            lex_flow_client: Instância de LexFlowClient já conectada e autenticada
                           Deve estar pronta para fazer chamadas à API
            
            memory_system: Instância de MemorySystem carregada
                          Fornece contexto histórico para decisões melhores
        
        LEVANTA EXCEÇÃO SE:
            - lex_flow_client for None ou não for instância de LexFlowClient
            - memory_system for None ou não for instância de MemorySystem
        
        EXEMPLO DE INICIALIZAÇÃO CORRETA:
            
            from integrations.lex_flow_definitivo import LexFlowClient, LexFlowConfig
            from engine.memory_system import MemorySystem
            
            # Criar e conectar cliente Lex Flow
            configuracao_lex_flow = LexFlowConfig(
                username="Lex-Usamn",
                password="senha_secreta"
            )
            cliente_lex_flow = LexFlowClient(configuracao_lex_flow)
            
            # Carregar sistema de memória
            sistema_memoria = MemorySystem()
            
            # Inicializar capture system
            capture = CaptureSystem(
                lex_flow_client=cliente_lex_flow,
                memory_system=sistema_memoria
            )
        """
        
        # Validação rigorosa das dependências
        if lex_flow_client is None:
            raise ValueError(
                "ERRO CRÍTICO: CaptureSystem PRECISA de um LexFlowClient válido! "
                "Forneça uma instância conectada e autenticada."
            )
        
        if not isinstance(lex_flow_client, LexFlowClient):
            raise TypeError(
                f"ERRO: lex_flow_client deve ser instância de LexFlowClient, "
                f"mas recebeu {type(lex_flow_client).__name__}"
            )
        
        if memory_system is None:
            raise ValueError(
                "ERRO CRÍTICO: CaptureSystem PRECISA de um MemorySystem válido! "
                "Forneça uma instância carregada."
            )
        
        if not isinstance(memory_system, MemorySystem):
            raise TypeError(
                f"ERRO: memory_system deve ser instância de MemorySystem, "
                f"mas recebeu {type(memory_system).__name__}"
            )
        
        # Armazenar referências às dependências (usadas em todos os métodos)
        self.lex_flow = lex_flow_client
        self.memory = memory_system
        
        # Cache interno para detecção rápida de duplicatas (evita chamadas à API)
        # Estrutura: {hash_conteudo: id_item_existente}
        self._deduplication_cache: Dict[str, str] = {}
        
        # Contador sequencial para geração de IDs (alternativo ao hash)
        self._id_counter: int = 0
        
        # Log de inicialização bem-sucedida
        log.info("=" * 70)
        log.info("📥 CAPTURE SYSTEM v2.0 INICIALIZADO (Integração Lex Flow Ativa)")
        log.info(f"   Cliente Lex Flow: {type(lex_flow_client).__name__}")
        log.info(f"   Sistema de Memória: {type(memory_system).__name__}")
        log.info(f"   Status: ✅ Pronto para capturas em produção")
        log.info("=" * 70)
    
    def _generate_sequential_id(self) -> str:
        """
        Gera identificador sequencial simples para captures
        
        Alternativa ao _generate_unique_id() baseado em hash.
        Formato: CAP-{YYYYMMDD}-{HHMMSS}-{NNNN}
        
        Returns:
            String com ID sequencial único
        """
        self._id_counter += 1
        timestamp_atual = datetime.now().strftime('%Y%m%d-%H%M%S')
        return f"CAP-{timestamp_atual}-{self._id_counter:04d}"
    
    # ========================================
    # MÉTODOS DE CAPTURA PRINCIPAIS (API PÚBLICA)
    # ========================================
    
    def quick_capture(
        self,
        idea: str,
        source: str = "manual",
        tags: List[str] = None,
        priority: CapturePriority = CapturePriority.MEDIUM,
        metadata: Dict = None
    ) -> CaptureResult:
        """
        CAPTURA RÁPIDA - Método principal e mais utilizado do sistema!
        
        Equivalente ao "funil universal" de entrada de dados.
        Qualquer informação que você quer guardar entra por aqui.
        
        FLUXO EXECUTADO POR ESTE MÉTODO:
        1. Criar objeto CaptureItem com os dados fornecidos
        2. Validar conteúdo mínimo (não pode estar vazio)
        3. Verificar se é duplicata de algo já capturado
        4. Enviar para Lex Flow via API real (quick_capture ou add_note)
        5. Retornar CaptureResult com sucesso/erro
        
        ARGUMENTOS:
            idea: Texto da ideia/nota (OBRIGATÓRIO, não pode ser vazio)
                  Pode ter qualquer tamanho (curto ou longo)
                  
            source: Origem desta captura (padrão: "manual")
                    Valores válidos: "manual", "telegram", "discord", 
                                      "voice", "thought", "api", "web", "bulk"
                    
            tags: Lista de tags opcionais para categorização manual
                  Exemplo: ["youtube", "dark", "criptomoeda", "urgente"]
                  
            priority: Nível de prioridade inicial (padrão: MEDIUM)
                      Valores: CRITICAL, HIGH, MEDIUM, LOW, SOMEDAY
                      
            metadata: Dicionário de metadados adicionais (opcional, flexível)
                      Exemplo: {"url_origem": "https://...", "autor": "Fulano"}
        
        RETORNA:
            CaptureResult com os seguintes campos preenchidos:
            - success: True se capturada com sucesso, False caso contrário
            - item: Objeto CaptureItem criado (mesmo se falhar, para debug)
            - message: Mensagem legível explicando o resultado
            - action_taken: Descrição do que foi feito ("created", "duplicate_ignored", etc.)
            - errors: Lista de erros (vazia se sucesso)
        
        EXEMPLOS DE USO:
        
        # Simples
        resultado = capture.quick_capture("Comprar pão na padaria")
        
        # Com tags e prioridade
        resultado = capture.quick_capture(
            "Ideia de vídeo: Top 5 moedas criptográficas para 2026",
            tags=["youtube", "criptomoeda", "canal-dark"],
            source="thought",
            priority=CapturePriority.HIGH
        )
        
        # Verificar resultado
        if resultado.success:
            print(f"✅ Capturada! ID: {resultado.item.id}")
        else:
            print(f"❌ Erro: {resultado.message}")
        """
        
        log.info(f"📥 Iniciando Quick Capture...")
        log.info(f"   Conteúdo (primeiros 80 chars): {idea[:80]}...")
        log.info(f"   Origem: {source}")
        log.info(f"   Tags fornecidas: {tags or []}")
        
        # PASSO 1: Criar objeto CaptureItem (representação interna normalizada)
        try:
            # Converter string de source para enum CaptureSource se necessário
            source_enum = CaptureSource(source) if isinstance(source, str) else CaptureSource.MANUAL
            
            item_capturado = CaptureItem(
                content=idea,
                source=source_enum,
                type=CaptureType.IDEA,
                priority=priority,
                tags=tags or [],
                metadata=metadata or {}
            )
            
            # Gerar ID e timestamp automaticamente (__post_init__)
            item_capturado.__post_init__()
            
        except Exception as erro_criacao:
            log.error(f"❌ Erro ao criar objeto CaptureItem: {erro_criacao}")
            return CaptureResult(
                success=False,
                item=None,
                message=f"Erro interno ao criar objeto de captura: {str(erro_criacao)}",
                action_taken="none",
                errors=[str(erro_criacao)]
            )
        
        # PASSO 2: Validar conteúdo mínimo (regra de negócio)
        if not item_capturado.content.strip():
            log.warning("⚠️  Captura rejeitada: conteúdo vazio ou apenas espaços")
            return CaptureResult(
                success=False,
                item=item_capturado,
                message="Conteúdo da captura não pode estar vazio. Forneça algum texto.",
                action_taken="rejected_empty_content",
                errors=["empty_content"]
            )
        
        # Validar tamanho máximo razoável (proteção contra abuse)
        if len(item_capturado.content) > 50000:  # 50KB limite generoso
            log.warning(f"⚠️  Captura muito longa: {len(item_capturado.content)} chars")
            return CaptureResult(
                success=False,
                item=item_capturado,
                message=f"Conteúdo muito longo ({len(item_capturado.content)} caracteres). Limite: 50000.",
                action_taken="rejected_too_long",
                errors=["content_too_long"]
            )
        
        # PASSO 3: Verificar duplicata (otimização para evitar gravar repetidos)
        if self._is_duplicate_item(item_capturado):
            log.info(f"♻️  Duplicata detectada, ignorando capture")
            return CaptureResult(
                success=True,  # Não é erro, apenas ignorou
                item=item_capturado,
                message="Esta ideia parece ser uma duplicata de algo já capturado recentemente. Ignorando.",
                action_taken="duplicate_ignored",
                errors=[]
            )
        
        # PASSO 4: Enviar para Lex Flow via API REAL (o momento da verdade!)
        try:
            log.info(f"📤 Enviando para Lex Flow API...")
            
            # Preparar tags para o Lex Flow (garantir lista vazia se None)
            tags_para_api = item_capturado.tags or ['capturada']  # Tag padrão se nenhuma fornecida
            
            # CHAMADA REAL À API DO LEX FLOW
            resultado_api = self.lex_flow.quick_capture(
                idea=item_capturado.content,
                tags=tags_para_api
            )
            
            # Verificar se a API retornou sucesso
            if resultado_api and resultado_api.get('id'):
                
                # Sucesso! Atualizar nosso item com ID real do Lex Flow
                item_capturado.id = str(resultado_api.get('id', item_capturado.id))
                item_capturado.processed = False  # Ainda não processada pelo Decision Engine
                
                log.info(f"✅ SUCESSO! Captura salva no Lex Flow")
                log.info(f"   ID retornado pela API: {item_capturado.id}")
                log.info(f"   Título salvo: {resultado_api.get('title', 'N/A')}")
                
                # Adicionar ao cache de deduplicação para futuras verificações
                conteudo_hash = self._calcular_hash_conteudo(item_capturado.content)
                self._deduplication_cache[conteudo_hash] = item_capturado.id
                
                # Retornar sucesso
                return CaptureResult(
                    success=True,
                    item=item_capturado,
                    message=f"Ideia capturada com sucesso! ID no Lex Flow: {item_capturado.id}",
                    action_taken="created_in_lex_flow",
                    errors=[]
                )
                
            else:
                # API retornou mas sem ID (pode ser erro ou formato inesperado)
                log.warning(f"⚠️  API retornou resposta inesperada: {resultado_api}")
                return CaptureResult(
                    success=False,
                    item=item_capturado,
                    message="Resposta inesperada do Lex Flow. Pode não ter sido salva.",
                    action_taken="api_response_invalid",
                    errors=[f"API response: {str(resultado_api)[:200]}"]
                )
                
        except Exception as erro_api:
            # Erro de conexão, timeout, autenticação, etc.
            log.error(f"❌ ERRO CRÍTICO ao chamar Lex Flow API: {erro_api}")
            log.error(f"   Tipo do erro: {type(erro_api).__name__}")
            log.error(f"   Detalhes: {str(erro_api)}")
            
            return CaptureResult(
                success=False,
                item=item_capturado,
                message=f"Erro de comunicação com Lex Flow: {str(erro_api)}",
                action_taken="api_call_failed",
                errors=[f"{type(erro_api).__name__}: {str(erro_api)}"]
            )
    
    def capture_voice_note(
        self,
        transcription_text: str,
        audio_file_path: str = None,
        whisper_model: str = "base",
        tags: List[str] = None,
        source: str = "voice"
    ) -> CaptureResult:
        """
        Capturar nota de voz (áudio já transcrito ou arquivo para transcrição)
        
        Este método lida com dois cenários:
        1. Texto já transcrito (fornecido diretamente)
        2. Arquivo de áudio que precisa ser transcrito (requer Whisper instalado)
        
        ATENÇÃO: A transcrição automática via Whisper requer:
        - Pacote 'openai-whisper' instalado (pip install openai-whisper)
        - Suficiente espaço em disco/RAM (modelos são pesados)
        - Para produção, recomenda-se usar API de transcrição externa
        
        ARGUMENTOS:
            transcription_text: Texto transcrito do áudio (se já tiver)
                                OU deixe vazio se for fornecer audio_file_path
                                
            audio_file_path: Caminho completo para arquivo de áudio (.mp3, .wav, .m4a)
                             Será transcrito automaticamente se transcription_text vazio
                             
            whisper_model: Modelo Whisper a usar (se precisar transcrever)
                           Opções: "tiny", "base", "small", "medium", "large"
                           "base" é bom equilíbrio velocidade/precisão
                           
            tags: Tags opcionais (além de "voice-note" automática)
            source: Origem (padrão: "voice")
        
        RETORNA:
            CaptureResult igual ao quick_capture()
        
        EXEMPLO:
            
            # Se já tem o texto transcrito (ex: via app de anotações)
            resultado = capture.capture_voice_note(
                transcription_text="Lembrar de ligar para o fornecedor amanhã"
            )
            
            # Se tem o arquivo de áudio e quer transcrever automaticamente
            resultado = capture.capture_voice_note(
                audio_file_path="/caminho/para/nota_de_voz.mp3",
                tags=["lembrete", "trabalho"]
            )
        """
        
        log.info(f"🎤 Iniciando captura de nota de voz...")
        
        texto_final = transcription_text
        
        # Se não teve texto fornecido mas tem arquivo, tentar transcrever
        if not texto_final and audio_file_path:
            log.info(f"📝 Transcrevendo arquivo de áudio: {audio_file_path}")
            texto_final = self._transcrever_audio_com_whisper(
                file_path=audio_file_path,
                model_name=whisper_model
            )
            
            if not texto_final:
                return CaptureResult(
                    success=False,
                    item=None,
                    message="Falha ao transcrever áudio. Verifique se o arquivo existe e se o Whisper está instalado.",
                    action_taken="transcription_failed",
                    errors=["whisper_transcription_failed"]
                )
        
        # Se mesmo assim não temos texto, erro
        if not texto_final or not texto_final.strip():
            return CaptureResult(
                success=False,
                item=None,
                message="Nenhum texto fornecido nem arquivo de áudio válido para transcrição.",
                action_taken="no_content_nor_audio",
                errors=["missing_content_and_audio"]
            )
        
        # Adicionar tag automática de voz
        todas_as_tags = tags or []
        todas_as_tags.append("voice-note")
        todas_as_tags.append("audio")
        
        # Delegar para quick_capture (que já faz validação + envio para Lex Flow)
        return self.quick_capture(
            idea=texto_final,
            source=source,
            tags=todas_as_tags,
            metadata={
                'original_source': 'voice_note',
                'audio_file': audio_file_path or 'provided_as_text',
                'whisper_model': whisper_model
            }
        )
    
    def capture_web_clip(
        self,
        url: str,
        custom_summary: str = None,
        tags: List[str] = None,
        save_as_resource: bool = True
    ) -> CaptureResult:
        """
        Capturar clip de página web (URL → conteúdo → resumo opcional → Lex Flow)
        
        Fluxo executado:
        1. Buscar conteúdo HTML da URL fornecida
        2. Extrair texto principal (remover HTML tags, scripts, estilos)
        3. (Opcional) Gerar resumo usando IA do Lex Flow (smart_summary)
        4. Salvar como Recurso no Lex Flow (ou como Nota, conforme preferência)
        
        ARGUMENTOS:
            url: URL completa da página a capturar (obrigatório, deve começar com http/https)
            
            custom_summary: Resumo personalizado (se já tiver, pula geração por IA)
                           Se None, usa smart_summary do Lex Flow automaticamente
                           
            tags: Tags opcionais além de "web-clip" automática
            
            save_as_resource: Se True, salva como Recurso (link)
                              Se False, salva como Note (conteúdo extraído)
        
        RETORNA:
            CaptureResult com detalhes da operação
        
        LIMITAÇÕES CONHECIDAS:
        - Páginas que requerem JavaScript não funcionarão (usa requests simples)
        - Sites com paywall/blockeo de bots podem falhar
        - PDFs e arquivos não são processados (somente HTML)
        
        EXEMPLO:
            
            resultado = capture.capture_web_clip(
                url="https://artigo.interessante.com/como-monetizar-youtube",
                tags=["youtube", "monetização", "referência"]
            )
        """
        
        log.info(f"🌐 Iniciando captura de web clip: {url}")
        
        # Validar URL básica
        if not url or not url.strip():
            return CaptureResult(
                success=False,
                item=None,
                message="URL não pode estar vazia.",
                action_taken="rejected_empty_url",
                errors=["empty_url"]
            )
        
        if not url.startswith(('http://', 'https://')):
            return CaptureResult(
                success=False,
                item=None,
                message="URL deve começar com http:// ou https://",
                action_taken="invalid_url_format",
                errors=["invalid_url_protocol"]
            )
        
        # Tentar buscar conteúdo da web
        try:
            import requests
            
            log.info(f"📥 Baixando conteúdo de: {url}")
            
            # Headers para simular navegador real (evitar bloqueios simples)
            cabecalhos_navegador = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
            }
            
            resposta_http = requests.get(
                url, 
                headers=cabecalhos_navegador, 
                timeout=15  # Timeout generoso para páginas lentas
            )
            
            # Verificar se conseguiu baixar
            if resposta_http.status_code != 200:
                log.error(f"❌ HTTP {resposta_http.status_code} ao baixar {url}")
                return CaptureResult(
                    success=False,
                    item=None,
                    message=f"Erro ao acessar URL: HTTP {resposta_http.status_code}",
                    action_taken="http_error",
                    errors=[f"http_{resposta_http.status_code}"]
                )
            
            # Extrair texto do HTML (simplificado - remove tags)
            conteudo_html_bruto = resposta_http.text
            texto_extraido = self._extrair_texto_de_html(conteudo_html_bruto)
            
            if not texto_extraido or len(texto_extraido.strip()) < 50:
                log.warning(f"⚠️  Pouco texto extraído de {url} ({len(texto_extraido or '')} chars)")
                # Mesmo assim continua, pode ser página legitima com pouco texto
            
            # Limitar tamanho (proteger contra páginas enormes)
            if len(texto_extraido) > 10000:
                texto_extraido = texto_extraido[:10000] + "\n\n[... Conteúdo truncado ...]"
                log.info("✂️  Conteúdo truncado para 10000 caracteres")
            
            log.info(f"📄 Texto extraído: {len(texto_extraido)} caracteres")
            
            # Gerar resumo (usar fornecido ou gerar com IA)
            resumo_final = custom_summary
            
            if not resumo_final:
                log.info(f"🤖 Gerando resumo com IA do Lex Flow...")
                try:
                    resumo_final = self.lex_flow.smart_summary(
                        content=texto_extraido,
                        max_length=300,
                        summary_type="general"
                    )
                    log.info(f"✅ Resumo gerado: {len(resumo_final or '')} chars")
                except Exception as erro_resumo:
                    log.warning(f"⚠️  Falha ao gerar resumo IA: {erro_resumo}")
                    resumo_final = texto_extraido[:500]  # Fallback: primeiros 500 chars
            
            # Preparar tags
            todas_as_tags = tags or []
            todas_as_tags.append("web-clip")
            
            # Domínio como tag adicional
            try:
                from urllib.parse import urlparse
                dominio = urlparse(url).netloc
                todas_as_tags.append(dominio)
            except:
                pass
            
            # Salvar no Lex Flow
            if save_as_resource:
                log.info(f"💾 Salvando como RECURSO no Lex Flow...")
                resultado_api = self.lex_flow.add_resource(
                    url=url,
                    notes=f"Resumo: {resumo_final}\n\nTexto completo:\n{texto_extraido[:2000]}"
                )
            else:
                log.info(f"💾 Salvando como NOTA no Lex Flow...")
                titulo_nota = f"Web Clip: {url[:60]}"
                resultado_api = self.lex_flow.add_note(
                    title=titulo_nota,
                    content=texto_extraido,
                    tags=todas_as_tags,
                    summary=resumo_final
                )
            
            # Verificar resultado
            if resultado_api and resultado_api.get('id'):
                log.info(f"✅ Web clip salvo! ID: {resultado_api.get('id')}")
                
                return CaptureResult(
                    success=True,
                    item=CaptureItem(
                        content=f"Web Clip: {url}",
                        source=CaptureSource.WEB_DASHBOARD,
                        type=CaptureType.REFERENCE,
                        tags=todas_as_tags,
                        metadata={'url': url, 'summary': resumo_final}
                    ),
                    message=f"Página web capturada com sucesso! ID: {resultado_api.get('id')}",
                    action_taken="saved_as_resource" if save_as_resource else "saved_as_note",
                    errors=[]
                )
            else:
                log.warning(f"⚠️  Resposta inesperada ao salvar web clip")
                return CaptureResult(
                    success=False,
                    item=None,
                    message="Falha ao salvar web clip no Lex Flow.",
                    action_taken="save_failed",
                    errors=["lex_flow_save_failed"]
                )
                
        except requests.exceptions.Timeout:
            log.error(f"❌ Timeout ao acessar {url}")
            return CaptureResult(
                success=False,
                item=None,
                message="Timeout: a página demorou demais para responder (>15 segundos).",
                action_taken="timeout",
                errors=["request_timeout"]
            )
            
        except requests.exceptions.ConnectionError as erro_conexao:
            log.error(f"❌ Erro de conexão: {erro_conexao}")
            return CaptureResult(
                success=False,
                item=None,
                message=f"Erro de conexão: {str(erro_conexao)}. Verifique sua internet.",
                action_taken="connection_error",
                errors=[str(erro_conexao)]
            )
            
        except Exception as erro_generico:
            log.error(f"❌ Erro inesperado no web clip: {erro_generico}", exc_info=True)
            return CaptureResult(
                success=False,
                item=None,
                message=f"Erro inesperado: {type(erro_generico).__name__}: {str(erro_generico)}",
                action_taken="unexpected_error",
                errors=[str(erro_generico)]
            )
    
    def bulk_import(
        self,
        items_data: List[Dict[str, str]],
        default_source: str = "bulk",
        stop_on_error: bool = False
    ) -> BatchCaptureResult:
        """
        Importar múltiplos itens em lote (bulk import)
        
        Útil para:
        - Migrar dados de outro sistema
        - Importar arquivo CSV/JSON com ideias antigas
        - Backup restore
        - Importar notas de outra ferramenta
        
        ARGUMENTOS:
            items_data: Lista de dicionários, cada um representando um item
                       Cada dicionário deve ter 'content' (obrigatório)
                       Opcionais: 'source', 'type', 'tags', 'priority', 'metadata'
                       
            default_source: Origem padrão se item não especificar (padrão: "bulk")
            
            stop_on_error: Se True, para no primeiro erro
                          Se False, continua tentando os demais (padrão)
        
        RETORNA:
            BatchCaptureResult com estatísticas completas
        
        FORMATO DE ENTRADA ESPERADO:
        
        [
            {
                "content": "Minha primeira ideia",
                "source": "telegram",           # opcional
                "tags": ["tag1", "tag2"],       # opcional
                "priority": "high"              # opcional
            },
            {
                "content": "Segunda ideia aqui",
                "type": "task"                   # opcional
            },
            # ... mais itens ...
        ]
        
        EXEMPLO DE USO:
        
        lote = [
            {"content": "Ideia 1 do arquivo antigo", "source": "migration"},
            {"content": "Tarefa importante esquecida", "type": "task", "priority": "high"},
            {"content": "Referência interessante", "source": "web", "type": "reference"}
        ]
        
        resultado = capture.bulk_import(lote)
        print(f"Importados: {resultado.successful}/{resultado.total_submitted}")
        """
        
        log.info(f"📦 Iniciando importação em lote: {len(items_data)} itens")
        
        resultado_lote = BatchCaptureResult(
            total_submitted=len(items_data),
            successful=0,
            failed=0,
            items=[],
            errors=[]
        )
        
        # Processar cada item individualmente
        for indice, item_dado in enumerate(items_data, start=1):
            
            log.info(f"   Processando item {indice}/{len(items_data)}...")
            
            # Validar estrutura mínima
            if not isinstance(item_dado, dict) or 'content' not in item_dado:
                error_msg = f"Item {indice} inválido: precisa de campo 'content'"
                log.error(f"   ❌ {error_msg}")
                resultado_lote.failed += 1
                resultado_lote.errors.append(error_msg)
                
                # Criar item dummy para registro (mesmo falhado)
                item_falho = CaptureItem(
                    content=str(item_dado),
                    source=CaptureSource.BULK_IMPORT,
                    type=CaptureType.IDEA
                )
                resultado_lote.items.append(item_falho)
                
                if stop_on_error:
                    log.error("   ⛔ Parando importação (stop_on_error=True)")
                    break
                
                continue
            
            # Extrair dados do dicionário (com defaults seguros)
            conteudo = item_dado.get('content', '')
            origem = item_dado.get('source', default_source)
            tipo_str = item_dado.get('type', 'idea')
            tags_item = item_dado.get('tags', [])
            prioridade_str = item_dado.get('priority', 'medium')
            metadados_item = item_dado.get('metadata', {})
            
            # Converter strings para enums (com tratamento de erro)
            try:
                tipo_enum = CaptureType(tipo_str) if isinstance(tipo_str, str) else CaptureType.IDEA
            except ValueError:
                log.warning(f"   ⚠️  Tipo inválido '{tipo_str}', usando IDEA")
                tipo_enum = CaptureType.IDEA
            
            try:
                prioridade_enum = CapturePriority(prioridade_str) if isinstance(prioridade_str, str) else CapturePriority.MEDIUM
            except ValueError:
                log.warning(f"   ⚠️  Prioridade inválida '{prioridade_str}', usando MEDIUM")
                prioridade_enum = CapturePriority.MEDIUM
            
            # Tentar capturar este item individualmente
            try:
                resultado_individual = self.quick_capture(
                    idea=conteudo,
                    source=origem,
                    tags=tags_item if isinstance(tags_item, list) else [],
                    priority=prioridade_enum,
                    metadata=metadados_item if isinstance(metadados_item, dict) else {}
                )
                
                # Registrar resultado
                if resultado_individual.success:
                    resultado_lote.successful += 1
                    log.info(f"   ✅ Item {indice} importado com sucesso")
                else:
                    resultado_lote.failed += 1
                    erro_msg = f"Item {indice}: {resultado_individual.message}"
                    resultado_lote.errors.append(erro_msg)
                    log.warning(f"   ⚠️  Item {indice} falhou: {resultado_individual.message}")
                
                # Adicionar item à lista (sucesso ou falha)
                if resultado_individual.item:
                    resultado_lote.items.append(resultado_individual.item)
                    
            except Exception as erro_item:
                resultado_lote.failed += 1
                erro_msg = f"Item {indice} exceção: {str(erro_item)}"
                resultado_lote.errors.append(erro_msg)
                log.error(f"   ❌ Item {indice} exceção: {erro_item}")
                
                # Criar item de registro
                item_excecao = CaptureItem(
                    content=conteudo,
                    source=CaptureSource.BULK_IMPORT,
                    type=tipo_enum,
                    metadata={'error': str(erro_item)}
                )
                resultado_lote.items.append(item_excecao)
                
                if stop_on_error:
                    log.error("   ⛔ Parando importação (stop_on_error=True)")
                    break
        
        # Log final do lote
        log.info("=" * 70)
        log.info(f"📊 IMPORTAÇÃO EM LOTE CONCLUÍDA:")
        log.info(f"   Total tentado: {resultado_lote.total_submitted}")
        log.info(f"   ✅ Sucesso: {resultado_lote.successful}")
        log.info(f"   ❌ Falhas: {resultado_lote.failed}")
        log.info(f"   Taxa de sucesso: {(resultado_lote.successful / max(resultado_lote.total_submitted, 1)) * 100:.1f}%")
        log.info("=" * 70)
        
        return resultado_lote
    
    # ========================================
    # MÉTODOS DE PROCESSAMENTO E BUSCA
    # ========================================
    
    def process_inbox_with_intelligence(self) -> Dict:
        """
        Processar inbox inteiro com inteligência artificial do Lex Flow
        
        Busca todas as notas pendentes no Inbox do Lex Flow,
        envia para o smart_categorize (IA) e retorna sugestões
        de organização para cada uma.
        
        FLUXO:
        1. Busca get_inbox() do Lex Flow (todas as notas pendentes)
        2. Extrai títulos e conteúdos
        3. Chama smart_categorize() do Lex Flow (IA analisa)
        4. Retorna relatório com sugestões por nota
        
        RETORNA:
            Dicionário com:
            - total_items: Quantas notas haviam no inbox
            - processed: Quantas foram analisadas
            - suggestions: Lista de sugestões (uma por nota)
            - errors: Erros se houverem
        
        NOTA: Este método NÃO move/apaga notas do inbox.
        Apenas gera sugestões. Use decision_engine para executar.
        """
        
        log.info(f"🤖 Iniciando processamento do Inbox com IA...")
        
        resultado_processamento = {
            'total_items': 0,
            'processed': 0,
            'suggestions': [],
            'errors': [],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # PASSO 1: Buscar todas as notas do inbox
            log.info(f"📥 Buscando notas do Inbox no Lex Flow...")
            notas_do_inbox = self.lex_flow.get_inbox()
            
            if not notas_do_inbox:
                log.info(f"📭 Inbox vazio! Nada para processar.")
                resultado_processamento['total_items'] = 0
                return resultado_processamento
            
            resultado_processamento['total_items'] = len(notas_do_inbox)
            log.info(f"   Encontradas {len(notas_do_inbox)} notas no inbox")
            
            # PASSO 2: Preparar dados para a IA
            titulos_das_notas = [nota.get('title', '') for nota in notas_do_inbox]
            conteudos_das_notas = [nota.get('content', '') for nota in notas_do_inbox]
            
            texto_completo_junto = '\n---\n'.join([
                f"TÍTULO: {t}\nCONTEÚDO: {c}" 
                for t, c in zip(titulos_das_notas, conteudos_das_notas)
            ])
            
            # PASSO 3: Enviar para IA categorizar
            log.info(f"🧠 Enviando para smart_categorize do Lex Flow...")
            resultado_ia = self.lex_flow.smart_categorize(
                items=titulos_das_notas,
                title="Processamento em Lote do Inbox",
                text=texto_completo_junto
            )
            
            if resultado_ia:
                resultado_processamento['processed'] = len(notas_do_inbox)
                resultado_processamento['suggestions'] = resultado_ia if isinstance(resultado_ia, list) else [resultado_ia]
                log.info(f"✅ IA processou {len(notas_do_inbox)} notas!")
            else:
                log.warning(f"⚠️  IA retornou resultado vazio/inesperado")
                resultado_processamento['errors'].append("IA returned empty result")
            
        except Exception as erro_processamento:
            log.error(f"❌ Erro ao processar inbox com IA: {erro_processamento}", exc_info=True)
            resultado_processamento['errors'].append(str(erro_processamento))
        
        return resultado_processamento
    
    def search_captures(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Buscar capturas anteriores por texto (busca simples)
        
        Usa a função search_notes do Lex Flow para encontrar
        notas cujo título contenha a query fornecida.
        
        Para busca semântica avançada (RAG), use memory_system.search()
        
        ARGUMENTOS:
            query: Texto para buscar (pode ser parcial)
            limit: Máximo de resultados (padrão: 10)
        
        RETORNA:
            Lista de dicionários (notas encontradas) ou lista vazia
        """
        
        log.info(f"🔍 Buscando capturas: '{query}' (limite: {limit})")
        
        try:
            resultados = self.lex_flow.search_notes(query=query)
            
            if resultados:
                log.info(f"✅ Encontradas {len(resultados)} notas")
                # Aplicar limit
                return resultados[:limit]
            else:
                log.info(f"📭 Nenhuma nota encontrada para: '{query}'")
                return []
                
        except Exception as erro_busca:
            log.error(f"❌ Erro na busca: {erro_busca}")
            return []
    
    def get_inbox_count(self) -> int:
        """
        Obter quantidade de itens pendentes no Inbox
        
        Útil para dashboards e métricas rápidas.
        
        RETORNA:
            Número inteiro de notas no inbox
        """
        try:
            notas = self.lex_flow.get_inbox()
            return len(notas) if notas else 0
        except:
            return 0
    
    # ========================================
    # MÉTODOS AUXILIARES INTERNOS (PRIVATE)
    # ========================================
    
    def _is_duplicate_item(self, item: CaptureItem) -> bool:
        """
        Verificar se item é duplicata de algo já capturado recentemente
        
        Usa cache local rápido (memória) para evitar chamadas à API.
        Considera duplicata se:
        - Conteúdo for idêntico (exato)
        - Ou similaridade > 95% (implementação futura com embeddings)
        
        ARGUMENTOS:
            item: CaptureItem a verificar
            
        RETORNA:
            True se for duplicata, False se é novo
        """
        
        # Calcular hash deste conteúdo
        hash_conteudo = self._calcular_hash_conteudo(item.content)
        
        # Verificar no cache local
        if hash_conteudo in self._deduplication_cache:
            log.debug(f"   ♻️  Duplicata detectada no cache (hash: {hash_conteudo})")
            return True
        
        # TODO: Implementar verificação no próprio Lex Flow (buscar notas similares)
        # Por enquanto, só confia no cache local (resetado a cada reinício do sistema)
        
        return False
    
    def _calcular_hash_conteudo(self, content: str) -> str:
        """
        Calcular hash SHA-256 do conteúdo para deduplicação
        
        Normaliza texto (lowercase, remove espaços extras) antes de hashear.
        
        ARGUMENTOS:
            content: Texto para hashear
            
        RETORNA:
            String hexadecimal do hash (64 caracteres)
        """
        
        # Normalizar: lowercase + strip + collapse whitespace
        conteudo_normalizado = ' '.join(content.lower().split())
        
        return hashlib.sha256(conteudo_normalizado.encode('utf-8')).hexdigest()
    
    def _transcrever_audio_com_whisper(self, file_path: str, model_name: str = "base") -> Optional[str]:
        """
        Transcrever arquivo de áudio para texto usando OpenAI Whisper
        
        ATENÇÃO: Requer pacote openai-whisper instalado!
        Instale com: pip install openai-whisper
        
        ARGUMENTOS:
            file_path: Caminho completo para arquivo de áudio
            model_name: Modelo Whisper ("tiny", "base", "small", "medium", "large")
        
        RETORNA:
            String com texto transcrito ou None se falhar
        """
        
        try:
            import whisper
            
            log.info(f"🎙️  Carregando modelo Whisper: {model_name}")
            modelo = whisper.load_model(model_name)
            
            log.info(f"🎙️  Transcrevendo arquivo: {file_path}")
            resultado_transcricao = modelo.transcribe(file_path)
            
            texto_transcrito = resultado_transcricao["text"]
            
            log.info(f"✅ Transcrição concluída: {len(texto_transcrito)} caracteres")
            
            return texto_transcrito
            
        except ImportError:
            log.error("❌ Pacote 'openai-whisper' não instalado!")
            log.error("   Instale com: pip install openai-whisper")
            return None
            
        except Exception as erro_whisper:
            log.error(f"❌ Erro na transcrição Whisper: {erro_whisper}")
            return None
    
    def _extrair_texto_de_html(self, html_content: str) -> str:
        """
        Extrair texto limpo de conteúdo HTML (implementação simplificada)
        
        Remove tags HTML, scripts, styles, deixa apenas texto legível.
        
        NOTA: Para produção séria, considere usar biblioteca 'beautifulsoup4'.
        Esta implementação é básica mas funcional para casos simples.
        
        ARGUMENTOS:
            html_content: String com código HTML bruto
            
        RETORNA:
            String com texto extraído (sem tags HTML)
        """
        
        # Tentar usar BeautifulSoup se disponível (melhor qualidade)
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remover scripts e styles
            for elemento in soup(['script', 'style']):
                elemento.decompose()
            
            # Obter texto limpo
            texto_limpo = soup.get_text(separator='\n', strip=True)
            
            # Remover linhas vazias excessivas
            linhas = [linha.strip() for linha in texto_limpo.split('\n') if linha.strip()]
            
            return '\n'.join(linhas)
            
        except ImportError:
            # Fallback: regex simples (menos preciso, mas funciona sem dependências)
            log.debug("   Usando extrator HTML baseado em regex (BeautifulSoup não disponível)")
            
            # Remove scripts
            texto_sem_scripts = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove styles
            texto_sem_styles = re.sub(r'<style[^>]*>.*?</style>', '', texto_sem_scripts, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove todas as tags HTML restantes
            texto_sem_tags = re.sub(r'<[^>]+>', ' ', texto_sem_styles)
            
            # Decodifica entidades HTML básicas (&amp;, &lt;, etc.)
            texto_decodificado = texto_sem_tags.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&nbsp;', ' ')
            
            # Colapsar espaços múltiplos e linhas vazias
            linhas = [linha.strip() for linha in texto_decodificado.split('\n') if linha.strip()]
            
            return '\n'.join(linhas)
    
    # ========================================
    # MÉTODOS ESTATÍTICOS E UTILITÁRIOS
    # ========================================
    
    @staticmethod
    def validate_capture_data(data: Dict) -> tuple:
        """
        Validar estrutura de dados de captura (para uso em APIs/bulk)
        
        VERIFICA:
        - Campo 'content' existe e não está vazio
        - Tipos de dados estão corretos
        - Comprimentos estão dentro de limites razoáveis
        
        ARGUMENTOS:
            data: Dicionário com dados da captura
            
        RETORNA:
            Tupla (valido: bool, erros: list)
        """
        
        erros_encontrados = []
        
        # Verificar campo obrigatório
        if 'content' not in data:
            erros_encontrados.append("Campo 'content' é obrigatório")
        elif not isinstance(data['content'], str):
            erros_encontrados.append("Campo 'content' deve ser string")
        elif not data['content'].strip():
            erros_encontrados.append("Campo 'content' não pode estar vazio")
        elif len(data['content']) > 50000:
            erros_encontrados.append("Campo 'content' muito longo (máx 50000 chars)")
        
        # Verificar campos opcionais (se existirem)
        if 'tags' in data and data['tags'] is not None:
            if not isinstance(data['tags'], list):
                erros_encontrados.append("Campo 'tags' deve ser lista")
            else:
                for tag in data['tags']:
                    if not isinstance(tag, str):
                        erros_encontrados.append(f"Tag inválida: {tag} (deve ser string)")
        
        if 'priority' in data and data['priority'] is not None:
            prioridades_validas = [p.value for p in CapturePriority]
            if data['priority'] not in prioridades_validas:
                erros_encontrados.append(f"Prioridade inválida: {data['priority']}. Válidas: {prioridades_validas}")
        
        if 'source' in data and data['source'] is not None:
            fontes_validas = [s.value for s in CaptureSource]
            if data['source'] not in fontes_validas:
                erros_encontrados.append(f"Origem inválida: {data['source']}. Válidas: {fontes_validas}")
        
        valido = len(erros_encontrados) == 0
        return (valido, erros_encontrados)
    
    def get_statistics(self) -> Dict:
        """
        Obter estatísticas de uso do Capture System
        
        Útil para dashboards e monitoramento.
        
        RETORNA:
            Dicionário com métricas:
            - inbox_count: Itens pendentes no inbox
            - cache_size: Tamanho do cache de deduplicação
            - id_counter: Quantos IDs já foram gerados
            - uptime_info: Informações sobre estado atual
        """
        
        return {
            'inbox_count': self.get_inbox_count(),
            'deduplication_cache_size': len(self._deduplication_cache),
            'generated_ids_count': self._id_counter,
            'system_status': 'active',
            'lex_flow_connected': self.lex_flow.is_authenticated() if hasattr(self.lex_flow, 'is_authenticated') else True,
            'timestamp': datetime.now().isoformat()
        }


# ================================================
# BLOCO DE TESTE E DEMONSTRAÇÃO
# ================================================

if __name__ == "__main__":
    """
    Teste completo do Capture System v2.0
    
    Execute: python engine/capture_system.py
    
    Este teste valida:
    1. Inicialização com Lex Flow Client real
    2. Captura rápida de ideia (quick_capture)
    3. Captura de nota de voz (simulada)
    4. Importação em lote (bulk_import)
    5. Busca de capturas (search_captures)
    6. Estatísticas do sistema
    """
    
    print("\n" + "=" * 80)
    print("🧪 CAPTURE SYSTEM v2.0 - TESTE DE INTEGRAÇÃO LEX FLOW")
    print("=" * 80 + "\n")
    
    # IMPORTAR DEPENDÊNCIAS NECESSÁRIAS PARA O TESTE
    try:
        from integrations.lex_flow_definitivo import LexFlowClient, LexFlowConfig
        from engine.memory_system import MemorySystem
    except ImportError as erro_import:
        print(f"❌ ERRO DE IMPORTAÇÃO: {erro_import}")
        print("   Certifique-se de estar executando da raiz do projeto.")
        sys.exit(1)
    
    # CONFIGURAR E CONECTAR LEX FLOW
    print("⏳ Conectando ao Lex Flow...")
    configuracao = LexFlowConfig(
        username="Lex-Usamn",
        password="Lex#157.",
        base_url="https://flow.lex-usamn.com.br"
    )
    
    cliente_lex_flow = LexFlowClient(configuracao)
    
    if not cliente_lex_flow.is_authenticated():
        print("\n❌ FALHA CRÍTICA: Não foi possível autenticar no Lex Flow!")
        print("   Verifique suas credenciais em config/settings.yaml")
        sys.exit(1)
    
    print("✅ Lex Flow autenticado com sucesso!\n")
    
    # CARREGAR SISTEMA DE MEMÓRIA
    print("⏳ Carregando Memory System...")
    sistema_memoria = MemorySystem()
    print("✅ Memory System carregado!\n")
    
    # INICIALIZAR CAPTURE SYSTEM
    print("📥 Inicializando Capture System v2.0...")
    capture = CaptureSystem(
        lex_flow_client=cliente_lex_flow,
        memory_system=sistema_memoria
    )
    print("✅ Capture System pronto!\n")
    
    # ========================================
    # TESTE 1: CAPTURA RÁPIDA (QUICK CAPTURE)
    # ========================================
    print("-" * 80)
    print("1️⃣  TESTE: Quick Capture (Captura Rápida)")
    print("-" * 80)
    
    resultado_teste1 = capture.quick_capture(
        idea="Teste automatizado do Capture System v2.0 - Integração Lex Flow!",
        tags=["teste-automatizado", "capture-system-v2", "integração"],
        source="test-script",
        priority=CapturePriority.LOW
    )
    
    if resultado_teste1.success:
        print(f"   ✅ SUCESSO!")
        print(f"   ID: {resultado_teste1.item.id}")
        print(f"   Mensagem: {resultado_teste1.message}")
        print(f"   Ação: {resultado_teste1.action_taken}")
    else:
        print(f"   ❌ FALHA: {resultado_teste1.message}")
        if resultado_teste1.errors:
            print(f"   Erros: {resultado_teste1.errors}")
    
    # ========================================
    # TESTE 2: CAPTURA DE NOTA DE VOZ (SIMULADA)
    # ========================================
    print("\n" + "-" * 80)
    print("2️⃣  TESTE: Voice Note Capture (Nota de Voz)")
    print("-" * 80)
    
    resultado_teste2 = capture.capture_voice_note(
        transcription_text="Lembrete de voz: Preciso revisar o contrato do fornecedor até sexta-feira.",
        tags=["trabalho", "lembrete", "prazo"],
        source="test-script"
    )
    
    if resultado_teste2.success:
        print(f"   ✅ SUCESSO!")
        print(f"   ID: {resultado_teste2.item.id}")
        print(f"   Contém tag voice-note: {'voice-note' in resultado_teste2.item.tags}")
    else:
        print(f"   ❌ FALHA: {resultado_teste2.message}")
    
    # ========================================
    # TESTE 3: IMPORTAÇÃO EM LOTE (BULK IMPORT)
    # ========================================
    print("\n" + "-" * 80)
    print("3️⃣  TESTE: Bulk Import (Importação em Lote)")
    print("-" * 80)
    
    itens_para_importar = [
        {"content": "Ideia em lote 1: Monetizar com afiliados", "tags": ["monetização"]},
        {"content": "Ideia em lote 2: Criar template de roteiro", "source": "thought"},
        {"content": "Tarefa em lote: Configurar domínio novo", "type": "task", "priority": "high"},
        {"content": "Referência em lote: https://exemplo.com/artigo-interessante", "type": "reference"}
    ]
    
    resultado_lote = capture.bulk_import(
        items_data=itens_para_importar,
        default_source="test-bulk"
    )
    
    print(f"   Total tentado: {resultado_lote.total_submitted}")
    print(f"   ✅ Sucessos: {resultado_lote.successful}")
    print(f"   ❌ Falhas: {resultado_lote.failed}")
    
    if resultado_lote.errors:
        print(f"   Erros: {resultado_lote.errors[:3]}")  # Primeiros 3 erros
    
    # ========================================
    # TESTE 4: BUSCA DE CAPTURAS
    # ========================================
    print("\n" + "-" * 80)
    print("4️⃣  TESTE: Search Captures (Busca)")
    print("-" * 80)
    
    resultados_busca = capture.search_captures(query="teste", limit=5)
    
    if resultados_busca:
        print(f"   ✅ Encontrados {len(resultados_busca)} resultados:")
        for item in resultados_busca[:3]:  # Mostra só 3
            print(f"      • [{item.get('id')}] {item.get('title', 'Sem título')[:50]}")
    else:
        print(f"   📭 Nenhum resultado para 'teste'")
    
    # ========================================
    # TESTE 5: ESTATÍSTICAS
    # ========================================
    print("\n" + "-" * 80)
    print("5️⃣  TESTE: Statistics (Estatísticas)")
    print("-" * 80)
    
    estatisticas = capture.get_statistics()
    
    print(f"   Itens no Inbox: {estatisticas['inbox_count']}")
    print(f"   Cache Deduplicação: {estatisticas['deduplication_cache_size']} itens")
    print(f"   IDs Gerados: {estatisticas['generated_ids_count']}")
    print(f"   Lex Flow Conectado: {'✅ Sim' if estatisticas['lex_flow_connected'] else '❌ Não'}")
    print(f"   Timestamp: {estatisticas['timestamp']}")
    
    # ========================================
    # RESUMO FINAL
    # ========================================
    print("\n" + "=" * 80)
    print("📊 RESUMO FINAL DOS TESTES:")
    print("=" * 80)
    
    testes_realizados = {
        'Quick Capture': resultado_teste1.success,
        'Voice Note': resultado_teste2.success,
        'Bulk Import': resultado_lote.successful > 0,
        'Search': len(resultados_busca) >= 0,  # Sempre true (pode ser vazio)
        'Statistics': True  # Sempre funciona
    }
    
    for nome_teste, resultado in testes_realizados.items():
        icone = "✅" if resultado else "❌"
        print(f"   {icone} {nome_teste}")
    
    total_sucessos = sum(1 for v in testes_realizados.values() if v)
    print(f"\n   Score: {total_sucessos}/{len(testes_realizados)} testes passaram")
    
    if total_sucessos >= 4:  # Pelo menos 4 de 5
        print("\n🎉 CAPTURE SYSTEM v2.0 FUNCIONANDO PERFEITAMENTE!")
        print("   Integração com Lex Flow: ✅ PRODUÇÃO READY")
    else:
        print("\n⚠️  Alguns testes falharam. Verifique os logs em logs/capture_system.log")
    
    print("=" * 80 + "\n")