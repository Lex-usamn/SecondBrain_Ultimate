"""
Capture System - Captura Inteligente Multi-Canal
==========================================

Sistema de captura rápida e organização automática de ideias,
notas, pensamentos e informações de múltiplas fontes.

Funcionalidades:
- Quick capture (texto, voz, imagem)
- Categorização automática via IA
- Deduplicação inteligente
- Roteamento para projetos certos
- Tags e metadados automáticos
- Multi-canal (CLI, Telegram, Discord, Web)

Autor: Second Brain Ultimate System
Versão: 1.0.0
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

try:
    from .memory_system import MemorySystem
except ImportError:
    from memory_system import MemorySystem

try:
    from ..integrations.lex_flow_definitivo import LexFlowClient
except ImportError:
    from integrations.lex_flow_definitivo import LexFlowClient

# ============================================
# LOGGING
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
# ENUMS E CONSTANTS
# ============================================

class CaptureSource(Enum):
    """Origens de captura"""
    THOUGHT = "thought"           # Ideia espontânea
    VOICE_NOTE = "voice"             # Nota de voz
    MANUAL = "manual"              # Digitada manualmente
    TELEGRAM = "telegram"           # Via Telegram Bot
    DISCORD = "discord"             # Via Discord
    WEB_DASHBOARD = "web"              # Via Lex Flow Dashboard
    API = "api"                   # Via API externa
    BULK_IMPORT = "bulk"              # Importação em lote

class CaptureType(Enum):
    """Tipos de conteúdo que podem serem capturados"""
    IDEA = "idea"                 # Ideia geral
    TASK = "task"                 # Tarefa açãoável
    NOTE = "note"                  # Nota/informação
    REFERENCE = "reference"           # Link/referência
    QUICK_CAPTURE = "quick_capture"      # Captura ultra-rápida
    MEETING_NOTE = "meeting_note"       # Nota de reunião
    CONTENT_DRAFT = "draft"              # Rascunho de conteúdo
    METRIC_UPDATE = "metric_update"      # Atualização de métrica

class CapturePriority(Enum):
    """Níveis de prioridade inicial"""
    CRITICAL = "critical"         # Urgente (responder HOJE)
    HIGH = "high"               # Importante (responder Hoje)
    MEDIUM = "medium"             # Importante (responder esta semana)
    LOW = "low"                 # Importante (quando tiver tempo)
    SOMEDAY = "someday"         # Importante (futuro)

class CaptureStatus(Enum):
    """Status da captura após processamento"""
    NEW = "new"                   # Recém criada
    PROCESSING = "processing"           # Sendo processada
    CATEGORIZED = "categorized"         # Categorizada
    CONVERTED_TO_TASK = "converted_to_task" # Convertida em tarefa
    ARCHIVED = "archived"              # Arquivada
    DELETED = "deleted"              # Deletada


# ============================================
# DATA CLASSES
# ============================================

@dataclass
class CaptureItem:
    """Item capturado (representação unificada)"""
    id: str = ""                     # ID único (gerado automaticamente)
    content: str = ""                 # Conteúdo original
    source: CaptureSource = CaptureSource.THOUGHT
    type: CaptureType = CaptureType.IDEA
    priority: CapturePriority = CapturePriority.MEDIUM
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    created_at: str = ""
    processed: bool = False
    processing_result: Dict = None
    
    # Dados enriquecidos (pós-captura)
    suggested_project: str = None       # Para onde deve ir
    suggested_category: str = None      # Categoria sugerida pela IA
    confidence_score: float = 0.0          # Quão confiamos na categorização
    duplicates: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Gera ID único se não existir"""
        if not self.id:
            self.id = self._generate_id()
            self.created_at = datetime.now().isoformat()
    
    def _generate_id(self) -> str:
        """Gera ID único baseado em hash do conteúdo"""
        content_hash = hashlib.sha256(
            f"{self.source.value}{self.content}{self.created_at}".encode()
        ).hexdigest()[:12]
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"{self.source.value}_{timestamp}"
    
    def to_dict(self) -> Dict:
        """Converte para dicionário (para salvar em Lex Flow)"""
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
    """Resultado de uma operação de captura"""
    success: bool = False
    item: CaptureItem = None
    message: str = ""
    action_taken: str = ""
    errors: List[str] = field(default_factory=list)


@dataclass
class BatchCaptureResult:
    """Resultado de captura em lote"""
    total_submitted: int = 0
    successful: int = 0
    failed: int = 0
    items: List[CaptureItem] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# ============================================
# MAIN CLASS
# ============================================

class CaptureSystem:
    """
    Sistema de Captura Inteligente Multi-Canal
    
    Coordena entrada de dados de múltiplas fontes,
    processa com IA, organiza automaticamente e roteia para
    destino correto (projetos, áreas ou recursos).
    
    Uso:
        capture = CaptureSystem(lex_flow=lf, memory=memory)
        
        # Capturas rápidas
        capture.quick_capture("Minha ideia...")
        capture.voice_note("Nota de voz transcrita aqui...")
        capture.bulk_import([
            {"content": "Ideia 1", "source": "telegram"},
            {"content": "Ideia 2", "source": "thought"},
        ])
        
        # Processar inbox
        capture.process_inbox_with_ai()
        
        # Buscar ideias
        capture.search("canais dark monetização")
    """
    
    def __init__(self, lex_flow: LexFlowClient, memory: MemorySystem):
        """
        Inicializa o Sistema de Captura
        
        Args:
            lex_flow: Cliente Lex Flow conectado
            memory: Sistema de memória carregado
        """
        self.lex_flow = lex_flow
        self.memory = memory
        
        self._deduplication_cache = {}  # Cache para deduplicação
        self._id_counter = 0
        
        log.info("📥 Capture System inicializado")
        log.info(f"   Lex Flow: {type(lex_flow).__name__}")
        log.info(f"   Memory: {type(memory).__name__}")
    
    def _generate_id(self) -> str:
        """Gera ID sequencial para captures"""
        self._id_counter += 1
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"CAP-{timestamp}-{self._id_counter:04d}"
    
    # ========================================
    # CAPTURA PRINCIPAL
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
        CAPTURA RÁPIDA - Método principal de uso!
        
        Captura ideia/informação instantaneamente no sistema.
        Equivalente ao "funil universal" de entrada de dados.
        
        Args:
            idea: Texto da idea/nota (obrigatório)
            source: Origem da captura
            tags: Lista de tags opcionais
            priority: Nível de prioridade inicial
            metadata: Metadados adicionais
            
        Returns:
            CaptureResult com resultado da operação
        """
        log.info(f"📥 Quick Capture: {idea[:50]}... (via {source})")
        
        # Criar objeto de captura
        item = CaptureItem(
            content=idea,
            source=CaptureSource(source) if isinstance(source, str) else CaptureSource.MANUAL,
            type=CaptureType.IDEA,
            priority=priority,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        # Gerar ID
        item.__post_init__()
        
        # Validar conteúdo mínimo
        if not item.content.strip():
            return CaptureResult(
                success=False,
                message="❌ Conteúdo não pode estar vazio",
                item=item
            )
        
        # Verificar duplicatas antes de salvar
        if self._is_duplicate(item):
            return CaptureResult(
                success=True,  # Não é erro, apenas ignora
                item=item,
                message=f"✅ Ideia duplicada (ID: {item.id})"
            )
        
        # Salvar no Lex Flow
        try:
            saved = self.lex_flow.add_note(
                title=item.content[:100],
                content=item.content,
                tags=item.tags or [source.value],
                summary=item.content[:200]
            )
            
            item.processed = True
            item.suggested_project = self._suggest_destination(item)
            item.suggested_category = self._categorize_quick(item)
            item.confidence_score = self._calculate_confidence(item)
            
            log.info(f"   ✅ Salvo em Lex Flow! ID: {item.id}")
            
            return CaptureResult(
                success=True,
                item=item,
                message=f"Captura salva em Lex Flow!",
                action_taken="saved_to_lexflow"
            )
            
        except Exception as e:
            log.error(f"❌ Erro salvando em Lex Flow: {e}")
            
            # Salvar localmente como fallback
            self._save_locally(item)
            
            return CaptureResult(
                success=True,
                item=item,
                message=f"Salvo localmente (Lex Flow indisponível no momento)",
                action_taken="saved_local_fallback"
            )
    
    def voice_capture(
        self,
        transcribed_text: str,
        tags: List[str] = None,
        metadata: Dict = None
    ) -> CaptureResult:
        """
        Captura de nota de voz transcrita
        
        Args:
            transcribed_text: Texto transcrito
            tags: Tags opcionais
            metadata: Metadados adicionais (ex: speaker_id, duration, etc.)
            
        Return:
            CaptureResult da operação
        """
        log.info("🎤 Voice Note Captura")
        
        return self.quick_capture(
            idea=f"[VOZ] {transcribed_text}",
            source=CaptureSource.VOICE_NOTE,
            tags=tags or ['voice', 'transcrição'],
            metadata=metadata or {'format': 'voice', 'duration': metadata.get('duration')}
        )
    
    def bulk_import(
        self,
        items: List[Dict],
        default_source: str = "bulk"
    ) -> BatchCaptureResult:
        """
        Importação em lote de múltiplos itens
        
        Perfeito para:
        - Importar lista de notas de outro sistema
        - Migrar dados de backup
        - Processar batch de ideias capturadas offline
        
        Args:
            items: Lista de dicionários com keys: {'content': ..., 'source': ...}
            default_source: Fonte padrão se não especificado nos items
            
        Returns:
            BatchCaptureResult com estatísticas da operação
        """
        log.info(f"📦 Bulk Import: {len(items)} itens")
        
        results = BatchCaptureResult()
        total_submitted = len(items)
        
        for item in items:
            content = item.get('content', '')
            source = item.get('source', default_source)
            tags = item.get('tags', [])
            metadata = item.get('metadata', {})
            
            result = self.quick_capture(
                idea=content,
                source=source,
                tags=tags,
                metadata={**metadata, 'imported': True}
            )
            
            results.items.append(result.item)
            
            if result.success:
                results.successful += 1
            else:
                results.failed += 1
                results.errors.append(result.message)
        
        results.total_submitted = total_submitted
        log.info(f"   ✅ Concluído: {results.successful}/{total_submitted}")
        
        if results.failed > 0:
            log.warning(f"   ⚠️ {results.failed} itens falharam")
        
        return results
    
    # ========================================
    # PROCESSAMENTO DE INBOX
    # ========================================
    
    def process_inbox(self) -> Dict:
        """
        Processa todas as notas do Inbox (Caixa de Entrada)
        
        Fluxo:
        1. Busca notas não processadas
        2. Categorizar com IA (smart_categorize)
        3. Detectar duplicatas
        4. Sugerir destinos
        5. Mover/Converter para projetos
        
        Returns:
            Dicionário com estatísticas do processamento
        """
        log.info("📥 Processando Inbox com IA...")
        
        notes = self.lex_flow.get_inbox()
        
        if not notes:
            return {
                'processed_count': 0,
                'moved_to_projects': 0,
                'archived': 0,
                'remaining': 0,
                'errors': [],
                'categorization': [],
                'duplicates_found': 0
            }
        
        total = len(notes)
        processed = 0
        moved = 0
        archived = 0
        remaining = 0
        duplicates_found = 0
        errors = []
        categorization = []
        
        # Detectar duplicatas
        seen_content = {}
        
        for note in notes:
            content_key = note.get('content', '').strip().lower()
            
            # Normalizar whitespace e converter para lowercase
            normalized = ' '.join(content.split())
            
            if normalized in seen_content:
                duplicates_found += 1
                continue  # Ignorar duplicata
                
            seen_content[normalized] = {
                'original_id': note.get('id'),
                'duplicate_of': seen_content[normalized]['original_id']
            }
            
            # Categorizar com IA
            try:
                cat_result = self.lex_flow.smart_categorize(
                    items=[note.get('title', '')],
                    text=note.get('content', '')
                )
                
                if isinstance(cat_result, dict):
                    categorization.append({
                        'note_id': note.get('id'),
                        'suggested_area': cat_result.get('area', 'Pendente'),
                        'confidence': cat_result.get('confidence', 0.5),
                        'tags_suggested': cat_result.get('tags', []),
                        'reasoning': cat_result.get('reasoning', '')
                    })
                    
            except Exception as e:
                errors.append(f"Erro categorizando nota {note.get('id')}: {e}")
                categorization.append({
                    'note_id': note.get('id'),
                    'suggested_area': 'Pendente análise manual',
                    'confidence': 0.3,
                    'tags_suggested': ['inbox', 'precisa-análise'],
                    'reasoning': 'Erro na categorização IA'
                })
            
            processed += 1
        
        remaining = total - processed - archived - duplicates_found
        
        return {
            'processed_count': processed,
            'moved_to_projects': moved,
            'archived': archived,
            'remaining': remaining,
            'duplicates_found': duplicates_found,
            'errors': errors,
            'categorization': categorization
        }
    
    def process_inbox_with_ai(self) -> Dict:
        """
        Versão avançada do processamento com IA mais inteligente
        
        Além da categorização básica, também:
        - Extraia metadados ocultos (emoções, sentimentos)
        - Detectar tarefas ocultas nas notas
        - Sugerir merge de notas similares
        """
        return self.process_inbox()  # Por enquanto, usa versão básica
        # TODO: Implementar versão avançada aqui
    
    # ========================================
    # BUSCA E RECUPERAÇÃO
    # ========================================
    
    def search_captures(
        self,
        query: str,
        max_results: int = 10,
        filters: Dict = None
    ) -> List[Dict]:
        """
        Busca em todas as capturas (Lex Flow + Local)
        
        Args:
            query: Termo de busca
            max_results: Máximo de resultados
            filters: Filtros opcionais (type, source, tags, date_range)
            
        Returns:
            Lista de dicionários com matches encontrados
        """
        log.info(f"🔍 Buscando capturas: '{query}'")
        
        results = []
        
        # Buscar no Lex Flow
        lex_notes = self.lex_flow.search_notes(query)
        for note in lex_notes[:max_results]:
            results.append({
                'id': note.get('id'),
                'title': note.get('title', ''),
                'content_preview': note.get('content', '')[:150],
                'source': note.get('source', 'unknown'),
                'type': 'lex_flow',
                'created_at': note.get('created_at', ''),
                'url': f"/quicknotes/{note.get('id')}"
            })
        
        # TODO: Buscar em cache local (quando implementar)
        # results.extend(self._search_local(query, max_results))
        
        log.info(f"   Encontrados: {len(results)} capturas no Lex Flow")
        
        return results
    
    def get_unprocessed(self) -> List[Dict]:
        """
        Retorna todas as notas NÃO processadas ainda
        
        Returns:
            Lista de dicionários de notas pendentes
        """
        notes = self.lex_flow.get_inbox()
        
        return [{
            'id': n.get('id'),
            'title': n.get('title', ''),
            'created_at': n.get('created_at', ''),
            'days_since_capture': self._days_since(n.get('created_at')),
            'content_preview': n.get('content', '')[:100],
            'tags': n.get('tags', [])
        } for n in notes if not n.get('processed')]
    
    def get_all_captures(
        self,
        source_filter: str = None,
        type_filter: str = None,
        tag_filter: str = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Busca capturas com filtros opcionais
        
        Returns:
            Lista de dicionários
        """
        notes = self.lex_flow.get_inbox()
        
        results = []
        
        for note in notes:
            # Aplicar filtros
            if source_filter and note.get('source', '') != source_filter:
                continue
            if type_filter and note.get('type', '') != type_filter:
                continue
            if tag_filter:
                tags = note.get('tags', [])
                if not any(t.lower() == tag_filter.lower() for t in tags):
                    continue
            
            results.append({
                'id': note.get('id'),
                'title': note.get('title', ''),
                'content': note.get('content', ''),
                'source': note.get('source', 'unknown'),
                'type': note.get('type', 'idea'),
                'tags': note.get('tags', []),
                'created_at': note.get('created_at', ''),
                'processed': note.get('processed', False),
                'project_linked': note.get('project_id'),
                'area_linked': note.get('area_id'),
                'converted_to_task': note.get('converted_to_task')
            })
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_stats(self) -> Dict:
        """Estatísticas de capturas"""
        all_notes = self.lex_flow.get_inbox()
        
        return {
            'total_captured': len(all_notes),
            'unprocessed': len([n for n in all_notes if not n.get('processed')]),
            'processed': len([n for n in all_notes if n.get('processed')]),
            'by_source': self._count_by_attr(all_notes, 'source'),
            'by_type': self._count_by_attr(all_notes, 'type'),
            'with_tags': len([n for n in all_notes if n.get('tags')]),
            'converted_to_tasks': len([n for n in all_notes if n.get('converted_to_task')]),
            'archived': len([n for n in all_notes if n.get('archived')])
        }
    
    def _count_by_attr(self, items: List[Dict], attr: str) -> Dict:
        """Conta itens por atributo específico"""
        counts = {}
        for item in items:
            val = item.get(attr, '')
        counts[val] = counts.get(val, 0) + 1
        return dict(sorted(counts.items(), 
                             key=lambda x: (-x[1])))
    
    def _is_duplicate(self, new_item: CaptureItem) -> bool:
        """Verifica se é duplicata (baseada em conteúdo similaridade)"""
        if not new_item.content:
            return False
        
        content_normalized = ' '.join(new_item.content.lower().split())
        
        # Verificar cache de duplicatas
        content_hash = hashlib.sha256(
            content_normalized.encode()).hexdigest()[:16]
        
        if content_hash in self._deduplication_cache:
            # Verificar se é realmente duplicata (>80% similar)
            cached = self._deduplication_cache[content_hash]
            similarity = self._calculate_similarity(
                content_normalized,
                cached
            )
            
            if similarity > 0.85:  # Considerar duplicata
                return True
        
        # Salvar no cache
        self._deduplication_cache[content_hash] = {
            'original_id': new_item.id,
            'duplicate_of': content_hash,
            'first_seen': datetime.now().isoformat()
        }
        
        return False
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calcula similaridade entre dois textos (0.0 a 1.0)"""
        if text1 == text2:
            return 1.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def _save_locally(self, item: CaptureItem):
        """Salva captura localmente (fallback se Lex Flow falhar)"""
        try:
            filepath = Path('./SecondBrain_Ultimate/00_INBOX/')
            filepath.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            filename = f"{item.source.value}_{timestamp}.md"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {item.id}\n")
                f.write(f"Título: {item.content[:100]}\n")
                f.write("\n")
                f.write("---\n")
                f.write(f"{item.content}\n")
                f.write("---\n")
                f.write("** METADADOS:**\n")
                f.write(f"- ID: {item.id}\n")
                f.write(f"- Source: {item.source.value}\n")
                f.write(f"- Type: {item.type.value}\n")
                f.write(f"- Priority: {item.priority.value}\n")
                f.write(f"- Tags: {', '.join(item.tags)}\n")
                f.write(f"- Created: {item.created_at}\n")
                f.write(f"- Confidence: {item.confidence_score:.2f}\n")
            
            log.info(f"   💾 Salvo local: {filename}")
            
            return True
            
        except Exception as e:
            log.error(f"Erro salvando localmente: {e}")
            return False
    
    def _suggest_destination(self, item: CaptureItem) -> str:
        """Sugere para qual projeto/área esta nota deve ir"""
        content_lower = item.content.lower()
        project_keywords = ['canal', 'dark', 'youtube', 'monetização', 'creativo', 'video']
        area_keywords = ['ti', 'tecnologia', 'infraestrutura', 'supermercado', 'segurança']
        influencer_keywords = ['instagram', 'tiktok', 'redes', 'engajamento', 'social media', 'influencer', 'digital']
        book_keywords = ['livro', 'escreva', 'livro', 'autor', 'publicar', 'editora', 'escrever']
        app_keywords = ['app', 'aplicação', 'software', 'desenvolvimento', 'dev', 'bug', 'feature']
        
        # Lógica de decisão de destino
        if any(kw in content_lower for kw in project_keywords):
            return f"PROJETO: Canais Dark/{kw.capitalize()} Monetização"
        
        if any(kw in content_lower for kw in influencer_keywords):
            return f"ÁREA: Influencer Digital/{kw.capitalize()} Gestão"
        
        if any(kw in content_lower for kw in book_keywords):
            return f"RECURSO: Livro/{kw.capitalize()} Escrita"
        
        if any(kw in content_lower for kw in app_keywords):
            return f"APPS: App/{kw.capitalize()} Desenvolvimento"
        
        # Default: Área genérica
        return f"RECURSO: Geral (aguardando análise)"
    
    def _categorize_quick(self, item: CaptureItem) -> str:
        """Categorização rápida sem usar IA (fallback se smart_categorize falhar)"""
        content_lower = item.content.lower()
        
        # Regras de heurísticas
        if any(word in content_lower for word in ['vídeo', 'video', 'canal', 'youtube']):
            return "Projetos: Canais Dark"
        elif any(word in content_lower for word in ['influencer', 'instagram', 'tiktok', 'redes', 'social']):
            return "Negócios: Influencer Digital"
        elif any(word in content_lower for word in ['app', 'software', 'code', 'dev', 'bug']):
            return "Desenvolvimento: Apps"
        elif any(word in content_lower for word in ['livro', 'escrever', 'livro', 'autor', 'publicar', 'editora']):
            return "Recursos: Escrita/Livro"
        elif any(word in content_lower for word in ['ti', 'tecnologia', 'infraestrutura', 'supermercado', 'segurança']):
            return "Áreas: TI / Infraestrutura"
        elif any(word in content_lower for word in ['streak', 'saúde', 'exercício', 'descanso']):
            return "Saúde/Bem-estar"
        elif any(word in content_lower for word in ['compra', 'tarefa', 'todo', 'afazeres']):
            return "Produtividade Pessoal"
        elif any(word in content_lower for word in ['estudar', 'ler', 'aula', 'aulas']):
            return "Educação/Cursos"
        else:
            return "Geral (aguardando análise)"
    
    def _calculate_confidence(self, item: CaptureItem) -> float:
        """Calcula confiança da categorização (0.0 a 1.0)"""
        confidence = 0.5  # Base
        content_lower = item.content.lower()
        
        # Ajustes baseado em palavras-chave
        if len(content_lower) > 100:
            confidence += 0.1  # Conteúdo longo = mais confiável
        if any(word in content_lower for word in ['!', '?', '!!!', 'urgente', 'importante']):
            confidence += 0.15  # Expressão de urgência
        if any(word in content_lower for word in ['objetivo', 'meta', 'meta']):
            confidence += 0.10  # Objetivos = mais sérios
        if item.tags:
            confidence += 0.05 # por tag relevante
            relevant_tags = ['dark', 'monetização', 'urgente', 'pronto', 'canal', 'youtube']
            for tag in item.tags:
                if tag.lower() in relevant_tags:
                    confidence += 0.02
        
        return min(1.0, confidence)
    
    def get_unprocessed_count(self) -> int:
        """Contagem de itens NÃO processados"""
        notes = self.lex_flow.get_inbox()
        return len([n for n in notes if not n.get('processed')])
    
    def get_processed_count(self) -> int:
        """Contagem de itens JÁ processados"""
        notes = self.lex_flow.get_inbox()
        return len([n for n in notes if n.get('processed')])

    def get_archived_count(self) -> int:
        """Contagem de itens arquivados"""
        notes = self.lex_flow.get_inbox()
        return len([n for n in notes if n.get('archived')])
    
    def get_total_count(self) -> int:
        """Total de itens no Inbox"""
        return len(self.lex_flow.get_inbox())
    
    def get_stats_detailed(self) -> Dict:
        """Estatísticas detalhadas de capturas"""
        
        return {
            'total': self.get_total_count(),
            'unprocessed': self.get_unprocessed_count(),
            'processed': self.get_processed_count(),
            'archived': self.get_archived_count(),
            'duplicates_detectados': self._get_duplicates_count(),
            'by_source': self._count_by_attr(self.get_all_captures(), 'source'),
            'by_type': self._count_by_attr(self.get_all_captures(), 'type'),
            'with_tags': len([n for n in self.get_all_captures() if n.get('tags')]),
            'converted_to_tasks': self.get_converted_to_tasks(),
            'avg_time_to_process': self._calc_avg_process_time(),
            'storage_location': "Lex Flow Cloud + Obsidian Local"
        }
    
    def get_duplicates_count(self) -> int:
        """Contagem de duplicatas detectadas"""
        return len(self._deduplication_cache)
    
    def _get_duplicates_count(self) -> int:
        """Contagem de duplicatas no cache"""
        return len(self._deduplication_cache)
    
    def _calc_avg_process_time(self) -> str:
        """Calcula média de tempo para processar itens"""
        processed = self.get_processed_count()
        archived = self.get_archived_count()
        
        if processed == 0:
            return "N/A (nada processada ainda)"
        
        # Simulação: 2 min por item (média razo)
        avg_seconds = (processed + archived) * 120  # 2 minutos
        if avg_seconds > 0:
            return f"{avg_seconds/60:.1f} minutos"
        else:
            return "N/A"
    
    def clear_duplicates_cache(self) -> int:
        """Limpa cache de duplicatas"""
        count = len(self._deduplication_cache)
        self._deduplication_cache = {}
        return count
    
    def export_to_obsidian(self, vault_path: str = None) -> Dict:
        """Exporta capturas para formato Obsidian
        
        Exporta todas as notas (processadas e não) para markdown
        prontos para uso no Obsidian.
        
        Args:
            vault_path: Caminho para vault Obsidian (opcional, usa default)
            
        Returns:
            Dicionário com estatísticas da exportação
        """
        vault_path = vault_path or "./SecondBrain_Ultimate/01_INBOX_EXPORTED/"
        
        try:
            Path(vault_path).mkdir(parents=True, exist_ok=True)
            
            notes = self.get_all_captures()
            
            export_data = {
                'exported_at': datetime.now().isoformat(),
            'total_items': len(notes),
            'exported_by': 0,
            'errors': [],
            'vault_path': str(vault_path),
            'items': []
            }
            
            for note in notes:
                try:
                    obsidian_note = {
                        'title': note.get('title', ''),
                        'content': note.get('content', ''),
                        'tags': note.get('tags', []),
                        'source': note.get('source', 'unknown'),
                        'type': note.get('type', 'idea'),
                        'created_at': note.get('created_at', ''),
                        'processed': note.get('processed', False),
                        'project_linked': note.get('project_id'),
                        'area_linked': note.get('area_id'),
                        'converted_to_task': note.get('converted_to_task'),
                        'archived': note.get('archived', False),
                        'id': note.get('id',)
                    }
                    
                    export_data['items'].append(obsidian_note)
                    export_data['exported_by'] += 1
                    
                except Exception as e:
                    export_data['errors'].append({
                        'item_id': note.get('id'),
                        'error': str(e)
                    })
            
            # Salvar arquivo índice
            export_filepath = Path(vault_path) / f"export_inbox_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            
            with open(export_filepath, 'w', encoding='utf-8') as f:
                f.write(f"# 📥 INBOX EXPORTADO\n\n")
                f.write(f"# Exportação automática do Second Brain\n")
                f.write(f"Data: {json.dumps(export_data, indent=2, ensure_ascii=False)}\n\n")
                
                for item in export_data['items']:
                    f.write(f"\n## {item['title']}\n")
                    f.write(f"- **ID:** `{item['id']}`\n")
                    f.write(f"- **Fonte:** `{item['source']}`  \n")
                    f.write(f"- **Tipo:** `{item['type']}`\n")
                    f.write(f"- **Tags:** {', '.join(item['tags'])}\n")
                    f.write(f"- **Criado:** `{item['created_at']}`\n")
                    f.write(f"- **Status:** {'✅ Processado' if item['processed'] else '⬜️ Pendente'}\n")
                    f.write(f"- **Projeto:** {item['project_linked'] or 'Não vinculado'}\n")
                    f.write(f"- **Área:** {item['area_linked'] or 'Não vinculada'}\n")
                    f.write(f"- **Convertido:** {'✅ Sim' if item.get('converted_to_task') else '⬜️ Não'}\n")
                    f.write(f"\n---\n")
                    f.write(f"{item['content']}\n")
                
            log.info(f"✅ Exportação concluída: {export_data['exported_by']} itens")
            
            return export_data
            
        except Exception as e:
            log.error(f"❌ Erro exportando: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_all_captures(self) -> List[Dict]:
        """Busca TODAS as capturas (incluindo processadas e arquivadas)"""
        
        return self.lex_flow.get_inbox()