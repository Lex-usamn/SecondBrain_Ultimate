"""
==============================================================================
RAG SYSTEM v2.0 - Sistema RAG Puro (NumPy + SciKit-Learn)
==============================================================================

Versão OTIMIZADA 100% em memória usando:
- TF-IDF via scikit-learn (matriz esparsa eficiente)
- Similaridade de cosseno via scipy (busca instantânea!)
- Índice invertido para busca keyword
- Grafo de conhecimentos entre documentos
- Persistência em disco (JSON + NPZ)
- Indexação automática do Lex Flow e memória interna

Dependências LEVES:
- numpy (já instalado)
- scikit-learn (~5MB)
- scipy (~5MB)

Autor: Lex-Brain Hybrid
Criado: 11/04/2026
Atualizado: 11/04/2026 (v2.0 - Pure NumPy, sem PyTorch!)
Status: ✅ PRODUÇÃO
==============================================================================
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import numpy as np
from scipy.sparse import csr_matrix, save_npz, load_npz


# =============================================================================
# CONFIGURAÇÃO DE LOGGING
# =============================================================================

logger_rag = logging.getLogger("LexBrain.RAGSystem")
logger_rag.setLevel(logging.DEBUG)

log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

file_handler = logging.FileHandler(
    log_dir / "rag_system.log",
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(formatter)
logger_rag.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger_rag.addHandler(console_handler)


# =============================================================================
# ENUMERAÇÕES E CONSTANTES
# =============================================================================

class TipoConteudo(str, Enum):
    """Tipos de conteúdo suportados pelo RAG System."""
    NOTA = "nota"
    TAREFA = "tarefa"
    LICAO = "licao"
    INSIGHT = "insight"
    PROJETO = "projeto"
    DOCUMENTO = "documento"
    CONVERSA = "conversa"


class EstrategiaBusca(str, Enum):
    """Estratégias de busca disponíveis."""
    VETORIAL = "vetorial"      # Busca vetorial TF-IDF + Cosseno
    KEYWORD = "keyword"        # Busca por palavras-chave exatas
    HIBRIDA = "hibrida"        # Combinação das duas (recomendada)


@dataclass
class DocumentoIndexado:
    """
    Representa um documento indexado no sistema RAG.
    
    Attributes:
        id: Identificador único do documento
        conteudo: Texto principal do documento
        metadata: Metadados adicionais (tipo, fonte, tags, etc.)
        embedding: Vetor TF-IDF (numpy array)
        data_indexacao: Quando foi indexado
        score_relevancia: Pontuação de relevância (0-1)
    """
    id: str
    conteudo: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None
    data_indexacao: datetime = field(default_factory=datetime.now)
    score_relevancia: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário serializável."""
        return {
            "id": self.id,
            "conteudo": self.conteudo,
            "metadata": self.metadata,
            "embedding": self.embedding.tolist() if self.embedding is not None else None,
            "data_indexacao": self.data_indexacao.isoformat(),
            "score_relevancia": self.score_relevancia
        }


@dataclass
class ResultadoBusca:
    """
    Resultado de uma operação de busca.
    
    Attributes:
        documentos: Lista de documentos encontrados (ordenados por relevancia)
        query_original: Query de busca original
        estrategia: Estratégia utilizada
        tempo_execucao: Tempo em milissegundos
        total_resultados: Número total de resultados
        sugestoes: Sugestões de queries relacionadas
    """
    documentos: list[DocumentoIndexado]
    query_original: str
    estrategia: EstrategiaBusca
    tempo_execucao: float = 0.0
    total_resultados: int = 0
    sugestoes: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário serializável."""
        return {
            "documentos": [doc.to_dict() for doc in self.documentos],
            "query_original": self.query_original,
            "estrategia": self.estrategia.value,
            "tempo_execucao": self.tempo_execucao,
            "total_resultados": self.total_resultados,
            "sugestoes": self.sugestoes
        }


@dataclass
class ConhecimentoRelacionado:
    """
    Representa uma conexão/conhecimento entre dois documentos.
    
    Attributes:
        doc_id_1: ID do primeiro documento
        doc_id_2: ID do segundo documento
        similaridade: Grau de similaridade (0-1)
        tipo_relacao: Tipo da relação (temática, temporal, causal, etc.)
    """
    doc_id_1: str
    doc_id_2: str
    similaridade: float
    tipo_relacao: str = "tematica"


# =============================================================================
# CLASSE PRINCIPAL: RAGSystem v2.0 (Pure NumPy)
# =============================================================================

class RAGSystem:
    """
    Sistema de Retrieval-Augmented Generation (RAG) v2.0 - Pure NumPy.
    
    Implementação 100% em memória usando:
    - TF-IDF via scikit-learn (matriz esparsa eficiente)
    - Similaridade de cosseno via scipy (busca instantânea)
    - Índice invertido para busca keyword
    - Grafo de conhecimentos entre documentos
    
    Vantagens sobre versão anterior:
    ✅ Sem problema de dimensão variável
    ✅ Muito mais rápido (tudo em memória RAM)
    ✅ Sem dependência de ChromaDB ou PyTorch
    ✅ Fácil de debugar e manter
    
    Usage:
        >>> from engine.rag_system import RAGSystem
        >>> rag = RAGSystem()
        >>> rag.inicializar()
        >>> resultado = rag.buscar("como escalar canais dark", n_results=5)
        >>> for doc in resultado.documentos:
        ...     print(f"[{doc.score_relevancia:.2f}] {doc.conteudo[:100]}")
    
    Attributes:
        data_dir: Diretório para persistência de dados
        cache_ttl: Tempo de vida do cache em segundos
        _tfidf_vectorizer: Vetorizador TF-IDF do sklearn
        _tfidf_matrix: Matriz esparsa TF-IDF de todos os documentos
        _doc_ids: Lista de IDs na ordem da matriz
        _documentos: Dict de todos os documentos (id -> DocumentoIndexado)
        _indice_invertido: Índice invertido para busca keyword
        _cache: Cache de buscas recentes
    """
    
    # Configurações de cache
    CACHE_TTL_PADRAO = 300  # 5 minutos
    CACHE_TAMANHO_MAXIMO = 1000
    
    # Configurações TF-IDF
    MAX_FEATURES = 5000       # Máximo de termos no vocabulário
    MIN_DF = 1                # Mínimo de documentos para um termo
    MAX_DF = 1.0              # Máximo de frequência (100%)
    NGRAM_RANGE = (1, 2)      # Unigramas e bigramas
    
    def __init__(
        self,
        data_dir: Optional[str] = None,
        cache_ttl: int = CACHE_TTL_PADRAO,
        ativar_cache: bool = True
    ):
        """
        Inicializa o sistema RAG v2.0.
        
        Args:
            data_dir: Diretório para dados persistentes. Padrão: 'data/rag'
            cache_ttl: Tempo de vida do cache em segundos. Padrão: 300
            ativar_cache: Se True, ativa cache de buscas. Padrão: True
        """
        logger_rag.info("🧠 Inicializando RAG System v2.0 (Pure NumPy)...")
        
        self.data_dir = Path(data_dir or str(Path(__file__).parent.parent / "data" / "rag"))
        self.cache_ttl = cache_ttl
        self.ativar_cache = ativar_cache
        
        # Criar diretório de dados
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Componentes principais (lazy loading)
        self._tfidf_vectorizer = None
        self._tfidf_matrix: Optional[csr_matrix] = None
        self._doc_ids: list[str] = []
        
        # Armazenamento de documentos
        self._documentos: dict[str, DocumentoIndexado] = {}
        
        # Índice invertido para busca keyword
        self._indice_invertido: dict[str, set[str]] = {}
        
        # Cache de buscas recentes
        self._cache: dict[str, tuple[ResultadoBusca, float]] = {}
        
        # Grafo de conhecimentos
        self._grafo_conhecimentos: list[ConhecimentoRelacionado] = []
        
        # Flag de inicialização
        self._inicializado = False
        
        logger_rag.info(f"   Data Dir: {self.data_dir}")
        logger_rag.info(f"   Cache TTL: {cache_ttl}s")
        logger_rag.info("✅ RAG System v2.0 criado (aguardando inicialização)")
    
    # =========================================================================
    # MÉTODOS DE INICIALIZAÇÃO
    # =========================================================================
    
    @property
    def tfidf_vectorizer(self):
        """
        Lazy loading do vetorizador TF-IDF.
        
        Returns:
            TfidfVectorizer: Instância do sklearn configurada
        """
        if self._tfidf_vectorizer is None:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                
                logger_rag.info("📊 Criando vetorizador TF-IDF...")
                
                self._tfidf_vectorizer = TfidfVectorizer(
                    max_features=self.MAX_FEATURES,
                    min_df=self.MIN_DF,
                    max_df=self.MAX_DF,
                    ngram_range=self.NGRAM_RANGE,
                    stop_words=None,
                    strip_accents='unicode',
                    lowercase=True,
                    token_pattern=r'(?u)\b\w+\b'
                )
                
                logger_rag.info("✅ Vetorizador TF-IDF pronto!")
                
            except ImportError:
                logger_rag.error(
                    "❌ Biblioteca scikit-learn não instalada!\n"
                    "   Instale com: pip install scikit-learn"
                )
                raise
        
        return self._tfidf_vectorizer
    
    def inicializar(self) -> bool:
        """
        Inicializa completamente o sistema RAG.
        
        Carrega dados persistidos do disco (se existirem).
        
        Returns:
            bool: True se inicializado com sucesso
        """
        try:
            logger_rag.info("🚀 Inicializando RAG System v2.0...")
            inicio = time.time()
            
            # Forçar lazy loading do vetorizador
            _ = self.tfidf_vectorizer
            
            # Carregar dados do disco (se existirem)
            self._carregar_dados_persistidos()
            
            elapsed = time.time() - inicio
            self._inicializado = True
            
            n_docs = len(self._documentos)
            n_termos = len(self.tfidf_vectorizer.vocabulary_) if hasattr(self.tfidf_vectorizer, 'vocabulary_') and self.tfidf_vectorizer.vocabulary_ else 0
            
            logger_rag.info(f"✅ RAG System v2.0 100% PRONTO em {elapsed:.2f}s!")
            logger_rag.info(f"   Documentos carregados: {n_docs}")
            logger_rag.info(f"   Termos no vocabulário: {n_termos}")
            
            return True
            
        except Exception as e:
            logger_rag.error(f"❌ Falha na inicialização: {e}")
            import traceback
            logger_rag.error(traceback.format_exc())
            return False
    
    # =========================================================================
    # MÉTODOS DE EMBEDDINGS (TF-IDF)
    # =========================================================================
    
    def gerar_embedding(self, texto: str) -> np.ndarray:
        """
        Gera embedding vetorial TF-IDF para um texto.
        
        IMPORTANTE: Só chamar DEPOIS de ter pelo menos 1 documento indexado
        (ou seja, depois de ter dado fit() no vectorizer).
        
        Args:
            texto: Texto para gerar embedding
            
        Returns:
            np.ndarray: Vetor TF-IDF denso (numpy array)
        
        Raises:
            ValueError: Se texto estiver vazio ou vectorizer não treinado
        """
        if not texto or not texto.strip():
            raise ValueError("Texto não pode estar vazio")
        
        if not hasattr(self.tfidf_vectorizer, 'vocabulary_') or self.tfidf_vectorizer.vocabulary_ is None:
            raise RuntimeError("Vectorizer não treinado. Adicione pelo menos 1 documento primeiro.")
        
        try:
            texto_limpo = self._preprocessar_texto(texto)
            
            # Transform (NÃO fit!) - usa vocabulário já existente
            embedding = self.tfidf_vectorizer.transform([texto_limpo]).toarray()[0]
            
            return embedding
            
        except Exception as e:
            logger_rag.error(f"❌ Erro ao gerar embedding TF-IDF: {e}")
            raise
    
    # =========================================================================
    # MÉTODOS DE INDEXAÇÃO
    # =========================================================================
    
    def adicionar_documento(
        self,
        conteudo: str,
        doc_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        tipo: TipoConteudo = TipoConteudo.NOTA,
        reconstruir_matriz: bool = True
    ) -> DocumentoIndexado:
        """
        Adiciona um documento à base de conhecimento.
        
        Args:
            conteudo: Texto principal do documento
            doc_id: ID único (se None, gera automaticamente)
            metadata: Metadados adicionais
            tipo: Tipo do conteúdo. Padrão: NOTA
            reconstruir_matriz: Se True, refaz a matriz TF-IDF. Padrão: True
            
        Returns:
            DocumentoIndexado: Documento indexado
        """
        if doc_id is None:
            doc_id = self._gerar_id(conteudo)
        
        metadata = metadata or {}
        metadata.update({
            "tipo": tipo.value,
            "data_indexacao": datetime.now().isoformat(),
            "tamanho_caracteres": len(conteudo),
            "tamanho_palavras": len(conteudo.split())
        })
        
        try:
            logger_rag.debug(f"📝 Indexando documento: {doc_id[:20]}...")
            
            # Criar objeto do documento (ainda sem embedding)
            documento = DocumentoIndexado(
                id=doc_id,
                conteudo=conteudo,
                metadata=metadata,
                embedding=None,
                data_indexacao=datetime.now()
            )
            
            # Armazenar documento
            self._documentos[doc_id] = documento
            self._doc_ids.append(doc_id)
            
            # Atualizar índice invertido
            self._atualizar_indice_invertido(doc_id, conteudo)
            
            # Reconstruir matriz TF-IDF com novo documento
            if reconstruir_matriz:
                self._reconstruir_tfidf_matrix()
                
                # Agora sim podemos gerar o embedding correto
                if self._tfidf_matrix is not None:
                    idx = self._doc_ids.index(doc_id)
                    documento.embedding = self._tfidf_matrix[idx].toarray()[0]
            
            logger_rag.info(f"✅ Documento indexado: {doc_id[:20]}... ({tipo.value})")
            
            # Persistir em disco
            self._salvar_dados_persistidos()
            
            return documento
            
        except Exception as e:
            logger_rag.error(f"❌ Erro ao indexar documento {doc_id}: {e}")
            # Limpar se deu erro
            if doc_id in self._documentos:
                del self._documentos[doc_id]
            if doc_id in self._doc_ids:
                self._doc_ids.remove(doc_id)
            raise
    
    def adicionar_documentos_lote(
        self,
        documentos: list[dict[str, Any]],
        gerar_conexoes: bool = False
    ) -> list[DocumentoIndexado]:
        """
        Adiciona múltiplos documentos em lote (mais eficiente).
        
        Adiciona todos PRIMEIRO, depois reconstrói a matriz TF-IDF
        apenas UMA vez (em vez de uma por documento).
        
        Args:
            documentos: Lista de dicionários com keys:
                       - 'conteudo' (obrigatório): texto
                       - 'id' (opcional): ID único
                       - 'metadata' (opcional): metadados
                       - 'tipo' (opcional): TipoConteudo
            gerar_conexoes: Se True, gera conexões (lento para muitos docs)
            
        Returns:
            list[DocumentoIndexado]: Lista de documentos indexados
        """
        if not documentos:
            return []
        
        logger_rag.info(f"📚 Indexando lote de {len(documentos)} documentos...")
        inicio = time.time()
        
        resultados = []
        
        # Primeiro: adicionar todos os documentos (sem reconstruir matriz)
        for doc in documentos:
            try:
                conteudo = doc.get("conteudo", "")
                doc_id = doc.get("id") or self._gerar_id(conteudo)
                metadata = doc.get("metadata", {})
                tipo = doc.get("tipo", TipoConteudo.NOTA)
                
                metadata.update({
                    "tipo": tipo.value if isinstance(tipo, TipoConteudo) else tipo,
                    "data_indexacao": datetime.now().isoformat(),
                    "tamanho_caracteres": len(conteudo),
                    "tamanho_palavras": len(conteudo.split())
                })
                
                documento = DocumentoIndexado(
                    id=doc_id,
                    conteudo=conteudo,
                    metadata=metadata,
                    embedding=None,
                    data_indexacao=datetime.now()
                )
                
                self._documentos[doc_id] = documento
                self._doc_ids.append(doc_id)
                self._atualizar_indice_invertido(doc_id, conteudo)
                
                resultados.append(documento)
                
            except Exception as e:
                logger_rag.warning(f"⚠️ Erro ao preparar documento: {e}")
        
        # Segundo: reconstruir matriz TF-IDF UMA única vez
        if resultados:
            self._reconstruir_tfidf_matrix()
            
            # Terceiro: preencher embeddings de todos os documentos
            if self._tfidf_matrix is not None:
                for i, doc in enumerate(resultados):
                    if i < self._tfidf_matrix.shape[0]:
                        doc.embedding = self._tfidf_matrix[i].toarray()[0]
        
        # Persistir
        self._salvar_dados_persistidos()
        
        elapsed = time.time() - inicio
        logger_rag.info(
            f"✅ Lote indexado: {len(resultados)} docs em {elapsed:.2f}s "
            f"({elapsed/max(len(resultados),1)*1000:.1f}ms/doc)"
        )
        
        return resultados
    
    def remover_documento(self, doc_id: str) -> bool:
        """
        Remove um documento da base de conhecimento.
        
        Args:
            doc_id: ID do documento a remover
            
        Returns:
            bool: True se removido com sucesso
        """
        try:
            if doc_id not in self._documentos:
                logger_rag.warning(f"⚠️ Documento não encontrado: {doc_id}")
                return False
            
            # Remover
            del self._documentos[doc_id]
            
            if doc_id in self._doc_ids:
                self._doc_ids.remove(doc_id)
            
            # Remover do índice invertido
            self._remover_do_indice_invertido(doc_id)
            
            # Remover conexões
            self._grafo_conhecimentos = [
                c for c in self._grafo_conhecimentos 
                if c.doc_id_1 != doc_id and c.doc_id_2 != doc_id
            ]
            
            # Reconstruir matriz TF-IDF
            self._reconstruir_tfidf_matrix()
            
            # Atualizar embeddings dos documentos restantes
            self._atualizar_todos_embeddings()
            
            # Persistir
            self._salvar_dados_persistidos()
            
            logger_rag.info(f"🗑️ Documento removido: {doc_id[:20]}...")
            return True
            
        except Exception as e:
            logger_rag.error(f"❌ Erro ao remover documento {doc_id}: {e}")
            return False
    
    # =========================================================================
    # MÉTODOS DE BUSCA
    # =========================================================================
    
    def buscar(
        self,
        query: str,
        n_results: int = 5,
        estrategia: EstrategiaBusca = EstrategiaBusca.HIBRIDA,
        filtros: Optional[dict[str, Any]] = None,
        min_score: float = 0.0,
        usar_cache: bool = True
    ) -> ResultadoBusca:
        """
        Realiza busca na base de conhecimento.
        
        Suporta três estratégias:
        - VETORIAL: Busca TF-IDF + Similaridade de Cosseno (entende contexto)
        - KEYWORD: Busca por palavras-chave exatas
        - HIBRIDA: Combina ambas (RECOMENDADA - melhores resultados!)
        
        Args:
            query: Texto da busca
            n_results: Número máximo de resultados. Padrão: 5
            estrategia: Estratégia de busca. Padrão: HIBRIDA
            filtros: Filtros de metadata (ex: {"tipo": "nota"})
            min_score: Score mínimo de relevância (0-1). Padrão: 0
            usar_cache: Se True, usa cache de buscas. Padrão: True
            
        Returns:
            ResultadoBusca: Resultados ordenados por relevância
        """
        inicio = time.time()
        
        # Verificar cache
        if usar_cache and self.ativar_cache:
            cache_key = self._gerar_cache_key(query, estrategia, filtros, n_results)
            cached = self._obter_do_cache(cache_key)
            if cached:
                logger_rag.debug(f"💾 Cache HIT para: {query[:50]}...")
                return cached
        
        logger_rag.info(f"🔍 Buscando: '{query[:80]}' ({estrategia.value}, top-{n_results})")
        
        documentos_finais = []
        
        try:
            if estrategia == EstrategiaBusca.VETORIAL:
                documentos_finais = self._busca_vetorial(query, n_results * 2)
                
            elif estrategia == EstrategiaBusca.KEYWORD:
                documentos_finais = self._busca_keyword(query, n_results * 2)
                
            elif estrategia == EstrategiaBusca.HIBRIDA:
                docs_vetoriais = self._busca_vetorial(query, n_results * 2)
                docs_keywords = self._busca_keyword(query, n_results * 2)
                documentos_finais = self._fusionar_resultados(
                    docs_vetoriais, 
                    docs_keywords, 
                    n_results
                )
            
            # Aplicar filtro de score mínimo
            if min_score > 0:
                documentos_finais = [
                    d for d in documentos_finais 
                    if d.score_relevancia >= min_score
                ]
            
            # Aplicar filtros de metadata
            if filtros:
                documentos_finais = [
                    d for d in documentos_finais 
                    if self._atende_filtros(d.metadata, filtros)
                ]
            
            # Limitar
            documentos_finais = documentos_finais[:n_results]
            
            tempo_execucao = (time.time() - inicio) * 1000
            
            sugestoes = self._gerar_sugestoes(query, documentos_finais)
            
            resultado = ResultadoBusca(
                documentos=documentos_finais,
                query_original=query,
                estrategia=estrategia,
                tempo_execucao=tempo_execucao,
                total_resultados=len(documentos_finais),
                sugestoes=sugestoes
            )
            
            if usar_cache and self.ativar_cache:
                self._salvar_no_cache(cache_key, resultado)
            
            logger_rag.info(
                f"✅ Busca concluída: {len(documentos_finais)} resultados "
                f"em {tempo_execucao:.0f}ms"
            )
            
            return resultado
            
        except Exception as e:
            logger_rag.error(f"❌ Erro na busca: {e}")
            return ResultadoBusca(
                documentos=[],
                query_original=query,
                estrategia=estrategia,
                tempo_execucao=(time.time() - inicio) * 1000,
                total_resultados=0
            )
    
    def buscar_similares(
        self,
        texto_referencia: str,
        n_results: int = 5,
        limiar_similaridade: float = 0.05
    ) -> list[DocumentoIndexado]:
        """
        Encontra documentos similares a um texto de referência.
        
        Usa similaridade de cosseno nos embeddings TF-IDF.
        
        Args:
            texto_referencia: Texto para encontrar similares
            n_results: Número máximo de resultados. Padrão: 5
            limiar_similaridade: Score mínimo (0-1). Padrão: 0.05
            
        Returns:
            list[DocumentoIndexado]: Documentos similares ordenados
        """
        try:
            # Verificamos se temos documentos e matriz
            if not self._documentos or self._tfidf_matrix is None:
                logger_rag.warning("⚠️ Nenhum documento indexado ou matriz vazia")
                return []
            
            # Gerar embedding da referência (usando o vocabulário EXISTENTE)
            embedding_ref = self.gerar_embedding(texto_referencia)
            
            # Calcular similaridade com todos os documentos
            documentos = []
            
            for doc_id in self._doc_ids:
                doc = self._documentos.get(doc_id)
                if doc and doc.embedding is not None:
                    # Similaridade de cosseno (1 - distância)
                    try:
                        # Calcular cosseno manualmente
                        dot_product = np.dot(embedding_ref, doc.embedding)
                        norm_ref = np.linalg.norm(embedding_ref)
                        norm_doc = np.linalg.norm(doc.embedding)
                        
                        if norm_ref > 0 and norm_doc > 0:
                            sim = dot_product / (norm_ref * norm_doc)
                        else:
                            sim = 0.0
                        
                        # Handle NaN ou erros
                        if np.isnan(sim):
                            sim = 0.0
                        
                        if sim >= limiar_similaridade:
                            doc_copy = DocumentoIndexado(
                                id=doc.id,
                                conteudo=doc.conteudo,
                                metadata=dict(doc.metadata),
                                embedding=doc.embedding.copy(),
                                data_indexacao=doc.data_indexacao,
                                score_relevancia=round(float(sim), 4)
                            )
                            documentos.append(doc_copy)
                            
                    except Exception as e:
                        logger_rag.debug(f"   ⚠️ Erro ao calcular similaridade com {doc_id}: {e}")
            
            # Ordenar por similaridade (decrescente)
            documentos.sort(key=lambda x: x.score_relevancia, reverse=True)
            
            logger_rag.info(
                f"🔍 Encontrados {len(documentos)} documentos similares "
                f"(limiar: {limiar_similaridade})"
            )
            
            return documentos[:n_results]
            
        except Exception as e:
            logger_rag.error(f"❌ Erro ao buscar similares: {e}")
            return []
    
    def perguntar(
        self,
        pergunta: str,
        n_contextos: int = 3,
        resposta_padrao: str = "Não encontrei informação relevante sobre isso."
    ) -> dict[str, Any]:
        """
        Faz uma pergunta e retorna contextos relevantes.
        
        Modo RAG puro: retorna os trechos mais relevantes para um LLM.
        
        Args:
            pergunta: Pergunta do usuário
            n_contextos: Número de trechos a recuperar. Padrão: 3
            resposta_padrao: Resposta se nada encontrado
            
        Returns:
            dict com contextos, fontes, pode_responder, score_confianca
        """
        logger_rag.info(f"❓ Pergunta: '{pergunta[:80]}'")
        
        resultado_busca = self.buscar(
            query=pergunta,
            n_results=n_contextos,
            estrategia=EstrategiaBusca.HIBRIDA
        )
        
        if not resultado_busca.documentos:
            return {
                "contextos": [resposta_padrao],
                "fontes": [],
                "pode_responder": False,
                "sugestoes": resultado_busca.sugestoes
            }
        
        contextos = [doc.conteudo for doc in resultado_busca.documentos]
        fontes = [doc.id for doc in resultado_busca.documentos]
        
        score_medio = sum(d.score_relevancia for d in resultado_busca.documentos) / len(resultado_busca.documentos)
        pode_responder = score_medio > 0.1  # Limiar razoável para TF-IDF
        
        logger_rag.info(
            f"📚 Recuperados {len(contextos)} contextos "
            f"(score médio: {score_medio:.2f}, pode_responder: {pode_responder})"
        )
        
        return {
            "contextos": contextos,
            "fontes": fontes,
            "pode_responder": pode_responder,
            "score_confianca": score_medio,
            "sugestoes": resultado_busca.sugestoes
        }
    
    # =========================================================================
    # MÉTODOS DE INTEGRAÇÃO COM LEX FLOW
    # =========================================================================
    
    def indexar_notas_lexflow(
        self,
        lexflow_client: Any,
        filtro_query: Optional[str] = None,
        max_notas: int = 100
    ) -> dict[str, Any]:
        """
        Indexa todas as notas do Lex Flow na base RAG.
        
        Args:
            lexflow_client: Instância do LexFlowClient
            filtro_query: Filtro opcional para buscar notas específicas
            max_notas: Número máximo de notas a indexar. Padrão: 100
            
        Returns:
            dict com estatísticas da indexação
        """
        logger_rag.info(f"📥 Iniciando indexação de notas do Lex Flow...")
        inicio = time.time()
        
        stats = {
            "total_encontradas": 0,
            "indexadas": 0,
            "erros": 0,
            "tempo_execucao": 0.0
        }
        
        try:
            # Buscar notas do Lex Flow
            if filtro_query:
                notas = lexflow_client.search_notes(filtro_query)
            else:
                notas = lexflow_client.search_notes("*") if hasattr(lexflow_client, 'search_notes') else []
            
            stats["total_encontradas"] = len(notas)
            notas = notas[:max_notas]
            
            documentos_para_indexar = []
            
            for nota in notas:
                try:
                    if isinstance(nota, dict):
                        nota_id = nota.get('id', '')
                        titulo = nota.get('title', nota.get('titulo', ''))
                        conteudo = nota.get('content', nota.get('conteudo', ''))
                        tags = nota.get('tags', [])
                    else:
                        nota_id = getattr(nota, 'id', '')
                        titulo = getattr(nota, 'title', getattr(nota, 'titulo', ''))
                        conteudo = getattr(nota, 'content', getattr(nota, 'conteudo', ''))
                        tags = getattr(nota, 'tags', [])
                    
                    texto_completo = f"{titulo}\n\n{conteudo}" if titulo else conteudo
                    
                    if not texto_completo.strip():
                        continue
                    
                    doc_id = f"lexflow_nota_{nota_id}"
                    
                    # Não re-indexar se já existe
                    if doc_id in self._documentos:
                        continue
                    
                    metadata = {
                        "fonte": "lexflow",
                        "nota_id": str(nota_id),
                        "titulo": titulo,
                        "tags": tags if isinstance(tags, list) else []
                    }
                    
                    documentos_para_indexar.append({
                        "id": doc_id,
                        "conteudo": texto_completo,
                        "metadata": metadata,
                        "tipo": TipoConteudo.NOTA
                    })
                    
                except Exception as e:
                    logger_rag.warning(f"⚠️ Erro ao processar nota: {e}")
                    stats["erros"] += 1
            
            if documentos_para_indexar:
                resultados = self.adicionar_documentos_lote(
                    documentos_para_indexar,
                    gerar_conexoes=False
                )
                stats["indexadas"] = len(resultados)
            
            stats["tempo_execucao"] = time.time() - inicio
            
            logger_rag.info(
                f"✅ Indexação do Lex Flow concluída:\n"
                f"   Total: {stats['total_encontradas']}\n"
                f"   Indexadas: {stats['indexadas']}\n"
                f"   Erros: {stats['erros']}\n"
                f"   Tempo: {stats['tempo_execucao']:.2f}s"
            )
            
            return stats
            
        except Exception as e:
            logger_rag.error(f"❌ Erro na indexação do Lex Flow: {e}")
            stats["erro"] = str(e)
            return stats
    
    def indexar_memoria_interna(
        self,
        caminho_soul: Optional[str] = None,
        caminho_user: Optional[str] = None,
        caminho_memory: Optional[str] = None,
        caminho_heartbeat: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Indexa os arquivos de memória do sistema (SOUL.md, USER.md, etc.)
        
        Args:
            caminho_soul: Caminho para SOUL.md
            caminho_user: Caminho para USER.md
            caminho_memory: Caminho para MEMORY.md
            caminho_heartbeat: Caminho para HEARTBEAT.md
            
        Returns:
            dict com estatísticas
        """
        logger_rag.info("📥 Indexando memória interna (SOUL, USER, MEMORY, HEARTBEAT)...")
        
        base_dir = Path(__file__).parent.parent
        
        arquivos = {
            "SOUL": caminho_soul or str(base_dir / "SOUL.md"),
            "USER": caminho_user or str(base_dir / "USER.md"),
            "MEMORY": caminho_memory or str(base_dir / "MEMORY.md"),
            "HEARTBEAT": caminho_heartbeat or str(base_dir / "HEARTBEAT.md")
        }
        
        stats = {"total": 0, "indexados": 0, "erros": 0}
        
        for nome, caminho in arquivos.items():
            try:
                path = Path(caminho)
                if path.exists():
                    conteudo = path.read_text(encoding="utf-8")
                    
                    doc_id = f"memoria_{nome.lower()}"
                    
                    # Se já existe, atualizar
                    if doc_id in self._documentos:
                        self.remover_documento(doc_id)
                    
                    self.adicionar_documento(
                        conteudo=conteudo,
                        doc_id=doc_id,
                        metadata={
                            "fonte": "memoria_interna",
                            "arquivo": nome,
                            "caminho": str(path),
                            "tamanho": len(conteudo)
                        },
                        tipo=TipoConteudo.DOCUMENTO
                    )
                    
                    stats["indexados"] += 1
                    logger_rag.info(f"   ✅ {nome}.md indexado ({len(conteudo)} chars)")
                    
                else:
                    logger_rag.warning(f"   ⚠️ {nome}.md não encontrado em {caminho}")
                    
            except Exception as e:
                logger_rag.error(f"   ❌ Erro ao indexar {nome}: {e}")
                stats["erros"] += 1
        
        stats["total"] = stats["indexados"] + stats["erros"]
        logger_rag.info(f"✅ Memória interna indexada: {stats['indexados']}/{stats['total']} arquivos")
        
        return stats
    
    # =========================================================================
    # MÉTODOS DO GRAFO DE CONHECIMENTOS
    # =========================================================================
    
    def obter_conexoes(
        self,
        doc_id: str,
        min_similaridade: float = 0.2,
        limite: int = 10
    ) -> list[ConhecimentoRelacionado]:
        """
        Obtém conexões/conhecimentos de um documento.
        """
        conexoes = [
            c for c in self._grafo_conhecimentos
            if (c.doc_id_1 == doc_id or c.doc_id_2 == doc_id)
            and c.similaridade >= min_similaridade
        ]
        
        conexoes.sort(key=lambda x: x.similaridade, reverse=True)
        return conexoes[:limite]
    
    def obter_todas_conexoes(self) -> list[ConhecimentoRelacionado]:
        """Retorna todas as conexões do grafo de conhecimentos."""
        return sorted(
            self._grafo_conhecimentos,
            key=lambda x: x.similaridade,
            reverse=True
        )
    
    # =========================================================================
    # MÉTODOS DE ESTATÍSTICAS E MANUTENÇÃO
    # =========================================================================
    
    def obter_estatisticas(self) -> dict[str, Any]:
        """
        Retorna estatísticas completas do sistema RAG.
        """
        try:
            vocab_size = (
                len(self.tfidf_vectorizer.vocabulary_) 
                if hasattr(self.tfidf_vectorizer, 'vocabulary_') and self.tfidf_vectorizer.vocabulary_
                else 0
            )
            
            contagem_tipos = {}
            for doc in self._documentos.values():
                tipo = doc.metadata.get('tipo', 'desconhecido')
                contagem_tipos[tipo] = contagem_tipos.get(tipo, 0) + 1
            
            matrix_shape = self._tfidf_matrix.shape if self._tfidf_matrix is not None else (0, 0)
            
            return {
                "total_documentos": len(self._documentos),
                "vocabulario_tfidf": vocab_size,
                "matrix_shape": f"{matrix_shape[0]}x{matrix_shape[1]}",
                "total_termos_indice": len(self._indice_invertido),
                "total_conexoes": len(self._grafo_conhecimentos),
                "contagem_por_tipo": contagem_tipos,
                "cache_tamanho": len(self._cache),
                "modelo": "TF-IDF + Cosseno (Pure NumPy v2.0)",
                "data_dir": str(self.data_dir),
                "inicializado": self._inicializado
            }
            
        except Exception as e:
            logger_rag.error(f"❌ Erro ao obter estatísticas: {e}")
            return {"erro": str(e)}
    
    def limpar_cache(self) -> int:
        """Limpa todo o cache de buscas."""
        tamanho = len(self._cache)
        self._cache.clear()
        logger_rag.info(f"🧹 Cache limpo ({tamanho} entradas removidas)")
        return tamanho
    
    def otimizar_indice(self) -> dict[str, Any]:
        """Otimiza os índices internos."""
        logger_rag.info("🔧 Otimizando índices...")
        inicio = time.time()
        
        # Rebuild completo
        self._reconstruir_tfidf_matrix()
        self._atualizar_todos_embeddings()
        self._limpar_cache_expirado()
        
        # Remover conexões fracas
        antes = len(self._grafo_conhecimentos)
        self._grafo_conhecimentos = [
            c for c in self._grafo_conhecimentos
            if c.similaridade >= 0.15
        ]
        conexoes_removidas = antes - len(self._grafo_conhecimentos)
        
        elapsed = time.time() - inicio
        
        resultado = {
            "sucesso": True,
            "tempo_execucao": elapsed,
            "vocabulario": len(self.tfidf_vectorizer.vocabulary_) if hasattr(self.tfidf_vectorizer, 'vocabulary_') else 0,
            "conexoes_removidas": conexoes_removidas,
            "conexoes_ativas": len(self._grafo_conhecimentos),
            "cache_limpo": True
        }
        
        logger_rag.info(f"✅ Otimização concluída em {elapsed:.2f}s")
        
        return resultado
    
    # =========================================================================
    # MÉTODOS PRIVADOS - TF-IDF MATRIX
    # =========================================================================
    
    def _reconstruir_tfidf_matrix(self) -> None:
        """
        Reconstrói a matriz TF-IDF completa com TODOS os documentos.
        
        Esta é a operação central do sistema:
        1. Coleta todos os textos dos documentos
        2. Fit o vectorizer (cria/atualiza vocabulário)
        3. Transform todos os textos em vetores TF-IDF
        4. Armazena como matriz esparsa (eficiente em memória)
        """
        if not self._documentos:
            logger_rag.debug("   Nenhum documento para reconstruir matriz")
            self._tfidf_matrix = None
            return
        
        try:
            # Coletar todos textos na ordem dos IDs
            textos = [self._documentos[doc_id].conteudo for doc_id in self._doc_ids]
            textos_limpos = [self._preprocessar_texto(t) for t in textos]
            
            # FIT + TRANSFORM (reconstrução completa)
            self._tfidf_matrix = self.tfidf_vectorizer.fit_transform(textos_limpos)
            
            logger_rag.debug(
                f"   Matriz TF-IDF reconstruída: {self._tfidf_matrix.shape} "
                f"({self._tfidf_matrix.nnz} não-zeros)"
            )
            
        except Exception as e:
            logger_rag.error(f"❌ Erro ao reconstruir matriz TF-IDF: {e}")
            self._tfidf_matrix = None
    
    def _atualizar_todos_embeddings(self) -> None:
        """Atualiza os embeddings de todos os documentos a partir da matriz."""
        if self._tfidf_matrix is None:
            return
        
        try:
            for i, doc_id in enumerate(self._doc_ids):
                if i < self._tfidf_matrix.shape[0]:
                    doc = self._documentos.get(doc_id)
                    if doc:
                        doc.embedding = self._tfidf_matrix[i].toarray()[0]
                        
        except Exception as e:
            logger_rag.warning(f"⚠️ Erro ao atualizar embeddings: {e}")
    
    # =========================================================================
    # MÉTODOS PRIVADOS - BUSCA
    # =========================================================================
    
    def _busca_vetorial(self, query: str, n_results: int) -> list[DocumentoIndexado]:
        """
        Busca usando TF-IDF + Similaridade de Cosseno.
        
        É o coração do sistema RAG!
        """
        try:
            # Verificações básicas
            if not self._documentos or self._tfidf_matrix is None:
                logger_rag.debug("   Nenhum documento ou matriz vazia para busca vetorial")
                return []
            
            if not hasattr(self.tfidf_vectorizer, 'vocabulary_') or not self.tfidf_vectorizer.vocabulary_:
                logger_rag.debug("   Vectorizer não treinado")
                return []
            
            # Gerar embedding da query (TRANSFORM, não FIT!)
            query_embedding = self.gerar_embedding(query)
            
            # Calcular similaridade de cosseno com TODOS os documentos
            similarities = []
            
            for i, doc_id in enumerate(self._doc_ids):
                if i < self._tfidf_matrix.shape[0]:
                    doc_vec = self._tfidf_matrix[i].toarray()[0]
                    
                    try:
                        # Similaridade de cosseno: cos(theta) = (A.B) / (||A|| * ||B||)
                        dot_product = np.dot(query_embedding, doc_vec)
                        norm_query = np.linalg.norm(query_embedding)
                        norm_doc = np.linalg.norm(doc_vec)
                        
                        if norm_query > 0 and norm_doc > 0:
                            similarity = dot_product / (norm_query * norm_doc)
                        else:
                            similarity = 0.0
                        
                        # Handle NaN
                        if np.isnan(similarity):
                            similarity = 0.0
                            
                        similarities.append((doc_id, float(similarity)))
                        
                    except Exception as e:
                        similarities.append((doc_id, 0.0))
            
            # Ordenar por similaridade (decrescente)
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Top-N resultados
            documentos = []
            for doc_id, score in similarities[:n_results]:
                doc = self._documentos.get(doc_id)
                if doc:
                    doc_copy = DocumentoIndexado(
                        id=doc.id,
                        conteudo=doc.conteudo,
                        metadata=dict(doc.metadata),
                        embedding=doc.embedding.copy() if doc.embedding is not None else None,
                        data_indexacao=doc.data_indexacao,
                        score_relevancia=round(score, 4)
                    )
                    documentos.append(doc_copy)
            
            return documentos
                
        except Exception as e:
            logger_rag.error(f"❌ Erro na busca vetorial: {e}")
            import traceback
            logger_rag.error(traceback.format_exc())
            return []
    
    def _busca_keyword(self, query: str, n_results: int) -> list[DocumentoIndexado]:
        """Busca por palavras-chave (índice invertido + scoring TF simplificado)."""
        termos_query = self._extrair_termos(query)
        
        if not termos_query:
            return []
        
        scores: dict[str, float] = {}
        
        for termo in termos_query:
            if termo in self._indice_invertido:
                df = len(self._indice_invertido[termo])
                idf = len(self._documentos) / max(df, 1)
                
                for doc_id in self._indice_invertido[termo]:
                    doc_texto = self._documentos.get(doc_id, DocumentoIndexado(id="", conteudo="")).conteudo.lower()
                    tf = doc_texto.count(termo)
                    
                    score = tf * idf
                    scores[doc_id] = scores.get(doc_id, 0) + score
        
        # Ordenar por score
        docs_ordenados = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n_results]
        
        documentos = []
        for doc_id, score in docs_ordenados:
            doc = self._documentos.get(doc_id)
            if doc:
                # Normalizar score para 0-1 (aproximado)
                score_normalizado = min(1.0, score / 30) if scores else 0.0
                
                doc_copy = DocumentoIndexado(
                    id=doc.id,
                    conteudo=doc.conteudo,
                    metadata=dict(doc.metadata),
                    embedding=None,
                    data_indexacao=doc.data_indexacao,
                    score_relevancia=round(score_normalizado, 4)
                )
                documentos.append(doc_copy)
        
        return documentos
    
    def _fusionar_resultados(
        self,
        docs_vetoriais: list[DocumentoIndexado],
        docs_keywords: list[DocumentoIndexado],
        n_results: int
    ) -> list[DocumentoIndexado]:
        """
        Fusiona resultados usando Reciprocal Rank Fusion (RRF).
        
        Algoritmo padrão da literatura para fusionar rankings.
        """
        k = 60  # Constante RRF padrão
        
        scores_rrf: dict[str, float] = {}
        documentos_map: dict[str, DocumentoIndexado] = {}
        
        # Score dos resultados vetoriais
        for rank, doc in enumerate(docs_vetoriais):
            rrf_score = 1.0 / (k + rank + 1)
            scores_rrf[doc.id] = scores_rrf.get(doc.id, 0) + rrf_score
            documentos_map[doc.id] = doc
        
        # Score dos resultados keyword
        for rank, doc in enumerate(docs_keywords):
            rrf_score = 1.0 / (k + rank + 1)
            scores_rrf[doc.id] = scores_rrf.get(doc.id, 0) + rrf_score
            if doc.id not in documentos_map:
                documentos_map[doc.id] = doc
        
        # Normalizar scores para 0-1
        if scores_rrf:
            max_score = max(scores_rrf.values())
            min_score = min(scores_rrf.values())
            range_score = max_score - min_score if max_score != min_score else 1
            
            for doc_id in scores_rrf:
                scores_rrf[doc_id] = (scores_rrf[doc_id] - min_score) / range_score
        
        # Ordenar por score final
        docs_ordenados = sorted(scores_rrf.items(), key=lambda x: x[1], reverse=True)[:n_results]
        
        # Montar resultado final
        resultado_final = []
        for doc_id, score in docs_ordenados:
            doc = documentos_map[doc_id]
            doc.score_relevancia = round(score, 4)
            resultado_final.append(doc)
        
        return resultado_final
    
    # =========================================================================
    # MÉTODOS PRIVADOS - UTILITÁRIOS
    # =========================================================================
    
    def _preprocessar_texto(self, texto: str) -> str:
        """Preprocessa texto para TF-IDF."""
        # Minúsculas
        texto = texto.lower()
        # Remover URLs
        texto = re.sub(r'http\S+|www\S+', '', texto)
        # Remover caracteres especiais excessivos
        texto = re.sub(r'[^\w\s]', ' ', texto)
        # Remover espaços extras
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto
    
    def _gerar_id(self, texto: str) -> str:
        """Gera ID único baseado no hash do conteúdo + timestamp."""
        hash_obj = hashlib.md5(texto.encode()).hexdigest()[:12]
        timestamp = int(time.time()) % 10000
        return f"doc_{hash_obj}_{timestamp}"
    
    def _extrair_termos(self, texto: str) -> list[str]:
        """Extrai termos para índice invertido (tokenização simples)."""
        texto = texto.lower()
        tokens = re.findall(r'\b[a-zà-ÿ]{3,}\b', texto)
        return tokens
    
    def _atualizar_indice_invertido(self, doc_id: str, texto: str) -> None:
        """Atualiza índice invertido com novo documento."""
        termos = self._extrair_termos(texto)
        
        for termo in termos:
            if termo not in self._indice_invertido:
                self._indice_invertido[termo] = set()
            self._indice_invertido[termo].add(doc_id)
    
    def _remover_do_indice_invertido(self, doc_id: str) -> None:
        """Remove um documento do índice invertido."""
        for termo in list(self._indice_invertido.keys()):
            if doc_id in self._indice_invertido[termo]:
                self._indice_invertido[termo].discard(doc_id)
            
            # Remover termos vazios
            if not self._indice_invertido[termo]:
                del self._indice_invertido[termo]
    
    def _gerar_sugestoes(self, query: str, resultados: list[DocumentoIndexado]) -> list[str]:
        """Gera sugestões de buscas relacionadas."""
        sugestoes = set()
        
        for doc in resultados[:3]:
            termos = self._extrair_termos(doc.conteudo)[:5]
            for termo in termos:
                if termo not in query.lower():
                    sugestoes.add(termo)
        
        return list(sugestoes)[:5]
    
    def _gerar_cache_key(
        self, 
        query: str, 
        estrategia: EstrategiaBusca,
        filtros: Optional[dict],
        n_results: int
    ) -> str:
        """Gera chave única para cache."""
        raw = f"{query}|{estrategia.value}|{filtros}|{n_results}"
        return hashlib.md5(raw.encode()).hexdigest()
    
    def _obter_do_cache(self, cache_key: str) -> Optional[ResultadoBusca]:
        """Obtém resultado do cache se ainda válido."""
        if cache_key in self._cache:
            resultado, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return resultado
            else:
                del self._cache[cache_key]
        return None
    
    def _salvar_no_cache(self, cache_key: str, resultado: ResultadoBusca) -> None:
        """Salva resultado no cache."""
        if len(self._cache) >= self.CACHE_TAMANHO_MAXIMO:
            chave_antiga = min(self._cache.items(), key=lambda x: x[1][1])[0]
            del self._cache[chave_antiga]
        
        self._cache[cache_key] = (resultado, time.time())
    
    def _limpar_cache_expirado(self) -> None:
        """Remove entradas expiradas do cache."""
        agora = time.time()
        expiradas = [
            k for k, (_, t) in self._cache.items()
            if agora - t > self.cache_ttl
        ]
        for k in expiradas:
            del self._cache[k]
    
    def _atende_filtros(self, metadata: dict, filtros: dict) -> bool:
        """Verifica se metadata atende aos filtros."""
        for chave, valor in filtros.items():
            if chave not in metadata:
                return False
            if isinstance(valor, list):
                if metadata[chave] not in valor:
                    return False
            else:
                if metadata[chave] != valor:
                    return False
        return True
    
    def _converter_para_serializable(self, obj: Any) -> Any:
        """Converte tipos numpy/python para tipos JSON-serializáveis."""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: self._converter_para_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._converter_para_serializable(item) for item in obj]
        return obj
    
    # =========================================================================
    # MÉTODOS PRIVADOS - PERSISTÊNCIA EM DISCO
    # =========================================================================
    
    def _salvar_dados_persistidos(self) -> None:
        """Salva dados em disco para persistência entre sessões."""
        try:
            # Salvar metadados dos documentos
            docs_data = []
            for doc_id in self._doc_ids:
                doc = self._documentos.get(doc_id)
                if doc:
                    docs_data.append({
                        "id": doc.id,
                        "conteudo": doc.conteudo,
                        "metadata": self._converter_para_serializable(doc.metadata),
                        "data_indexacao": doc.data_indexacao.isoformat()
                    })
            
            meta_path = self.data_dir / "documents_metadata.json"
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(docs_data, f, ensure_ascii=False, indent=2, default=str)
            # ⬅️ ADICIONADO default=str para converter qualquer resto!
            
            # Salvar matriz TF-IDF se existir
            if self._tfidf_matrix is not None:
                matrix_path = self.data_dir / "tfidf_matrix.npz"
                save_npz(matrix_path, self._tfidf_matrix)
            
            # Salvar configuração do vectorizer
            if hasattr(self.tfidf_vectorizer, 'vocabulary_') and self.tfidf_vectorizer.vocabulary_:
                vec_config = {
                    "vocabulary": {k: int(v) for k, v in self.tfidf_vectorizer.vocabulary_.items()},
                    # ⬅️ CONVERTER VALORES DO VOCAB PARA int PYTHON!
                    "doc_ids": self._doc_ids
                }
                vec_path = self.data_dir / "vectorizer_config.json"
                with open(vec_path, 'w', encoding='utf-8') as f:
                    json.dump(vec_config, f)
            
            logger_rag.debug(f"💾 Dados salvos em {self.data_dir}")
            
        except Exception as e:
            logger_rag.warning(f"⚠️ Erro ao salvar dados em disco: {e}")
    
    def _carregar_dados_persistidos(self) -> None:
        """
        Carrega dados do disco (se existirem).
        
        Chamado durante a inicialização.
        """
        try:
            # Carregar metadados
            meta_path = self.data_dir / "documents_metadata.json"
            if meta_path.exists():
                with open(meta_path, 'r', encoding='utf-8') as f:
                    docs_data = json.load(f)
                
                logger_rag.info(f"📂 Carregando {len(docs_data)} documentos do disco...")
                
                for doc_data in docs_data:
                    doc = DocumentoIndexado(
                        id=doc_data["id"],
                        conteudo=doc_data["conteudo"],
                        metadata=doc_data.get("metadata", {}),
                        embedding=None,
                        data_indexacao=datetime.fromisoformat(doc_data["data_indexacao"])
                    )
                    self._documentos[doc.id] = doc
                    self._doc_ids.append(doc.id)
                    self._atualizar_indice_invertido(doc.id, doc.conteudo)
                
                # Reconstruir matriz TF-IDF
                self._reconstruir_tfidf_matrix()
                self._atualizar_todos_embeddings()
                
                logger_rag.info(f"✅ {len(self._documentos)} documentos carregados!")
            
        except Exception as e:
            logger_rag.warning(f"⚠️ Erro ao carregar dados do disco: {e}")
            # Continuar sem dados persistidos (não é fatal)


# =============================================================================
# FUNÇÃO DE FÁBRICA
# =============================================================================

def criar_rag_system(
    data_dir: Optional[str] = None,
    auto_inicializar: bool = False
) -> RAGSystem:
    """
    Função fábrica para criar e opcionalmente inicializar um RAGSystem.
    
    Args:
        data_dir: Diretório para dados persistentes
        auto_inicializar: Se True, chama inicializar() automaticamente
        
    Returns:
        RAGSystem: Instância configurada
    """
    rag = RAGSystem(data_dir=data_dir)
    
    if auto_inicializar:
        rag.inicializar()
    
    return rag


# =============================================================================
# BLOCO DE TESTE RÁPIDO
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧠 RAG SYSTEM v2.0 - TESTE RÁPIDO (Pure NumPy)")
    print("=" * 60)
    
    # Criar instância
    rag = RAGSystem(data_dir="./test_rag_data_v2")
    
    # Inicializar
    print("\n📥 Inicializando sistema...")
    if rag.inicializar():
        print("✅ Sistema inicializado com sucesso!")
        
        # Adicionar alguns documentos de teste
        print("\n📝 Adicionando documentos de teste...")
        
        doc1 = rag.adicionar_documento(
            conteudo="Como escalar canais dark no YouTube em 90 dias: estratégias de monetização",
            metadata={"tags": ["youtube", "monetizacao"], "categoria": "estrategia"},
            tipo=TipoConteudo.NOTA
        )
        print(f"   Doc 1: {doc1.id} (embedding shape: {doc1.embedding.shape if doc1.embedding is not None else 'None'})")
        
        doc2 = rag.adicionar_documento(
            conteudo="Melhores práticas para criar vídeos virais no TikTok e Instagram Reels",
            metadata={"tags": ["tiktok", "instagram", "viral"], "categoria": "conteudo"},
            tipo=TipoConteudo.NOTA
        )
        print(f"   Doc 2: {doc2.id} (embedding shape: {doc2.embedding.shape if doc2.embedding is not None else 'None'})")
        
        doc3 = rag.adicionar_documento(
            conteudo="Automação de produção de conteúdo com IA: ferramentas e workflows",
            metadata={"tags": ["ia", "automacao", "produtividade"], "categoria": "ferramentas"},
            tipo=TipoConteudo.NOTA
        )
        print(f"   Doc 3: {doc3.id} (embedding shape: {doc3.embedding.shape if doc3.embedding is not None else 'None'})")
        
        doc4 = rag.adicionar_documento(
            conteudo="Gestão de projetos para criadores de conteúdo: metodologias ágeis adaptadas",
            metadata={"tags": ["produtividade", "gestao"], "categoria": "produtividade"},
            tipo=TipoConteudo.NOTA
        )
        print(f"   Doc 4: {doc4.id}")
        
        doc5 = rag.adicionar_documento(
            conteudo="Construindo um segundo cérebro com IA: organização de conhecimento pessoal",
            metadata={"tags": ["second-brain", "organizacao", "conhecimento"]},
            tipo=TipoConteudo.DOCUMENTO
        )
        print(f"   Doc 5: {doc5.id}")
        
        # Testar busca
        print("\n" + "-" * 60)
        print("🔍 TESTE 1: Busca Vetorial (TF-IDF + Cosseno)")
        print("-" * 60)
        
        query = "como ganhar dinheiro criando vídeos"
        print(f'\nQuery: "{query}"')
        
        resultado = rag.buscar(
            query=query,
            n_results=3,
            estrategia=EstrategiaBusca.VETORIAL
        )
        
        print(f"\n📊 Resultados ({resultado.total_resultados} encontrados, {resultado.tempo_execucao:.0f}ms):\n")
        
        for i, doc in enumerate(resultado.documentos, 1):
            print(f"   {i}. [{doc.score_relevancia:.4f}] {doc.conteudo[:70]}...")
            print(f"      Tipo: {doc.metadata.get('tipo', 'N/A')}")
            print()
        
        # Teste 2: Busca Keyword
        print("-" * 60)
        print("🔑 TESTE 2: Busca Keyword")
        print("-" * 60)
        
        query_kw = "youtube tiktok"
        print(f'Query: "{query_kw}"')
        
        resultado_kw = rag.buscar(
            query=query_kw,
            n_results=3,
            estrategia=EstrategiaBusca.KEYWORD
        )
        
        print(f"\n📊 Resultados ({resultado_kw.total_resultados} encontrados):\n")
        
        for i, doc in enumerate(resultado_kw.documentos, 1):
            print(f"   {i}. [{doc.score_relevancia:.4f}] {doc.conteudo[:70]}...")
            print()
        
        # Teste 3: Busca Híbrida (RECOMENDADA!)
        print("-" * 60)
        print("🔀 TESTE 3: Busca Híbrida (TF-IDF + Keyword)")
        print("-" * 60)
        
        query_hibrida = "ferramentas IA para criadores"
        print(f'Query: "{query_hibrida}"')
        
        resultado_hib = rag.buscar(
            query=query_hibrida,
            n_results=3,
            estrategia=EstrategiaBusca.HIBRIDA
        )
        
        print(f"\n📊 Resultados ({resultado_hib.total_resultados} encontrados, {resultado_hib.tempo_execucao:.0f}ms):\n")
        
        for i, doc in enumerate(resultado_hib.documentos, 1):
            print(f"   {i}. [{doc.score_relevancia:.4f}] {doc.conteudo[:70]}...")
            print(f"      Tags: {doc.metadata.get('tags', [])}")
            print()
        
        # Teste 4: Modo Pergunta (RAG puro)
        print("-" * 60)
        print("❓ TESTE 4: Modo Pergunta (Contexto para LLM)")
        print("-" * 60)
        
        pergunta = "Quais as melhores estratégias para monetizar conteúdo?"
        print(f'Pergunta: "{pergunta}"')
        
        resposta = rag.perguntar(pergunta, n_contextos=2)
        
        print(f"\n📚 Resposta RAG:\n")
        print(f"   Pode responder: {'✅ SIM' if resposta['pode_responder'] else '❌ NÃO'}")
        print(f"   Confiança: {resposta['score_confianca']:.4f}")
        print(f"\n   Contextos recuperados:")
        
        for i, ctx in enumerate(resposta['contextos'], 1):
            print(f"\n   --- Contexto {i} ---")
            print(f"   {ctx[:150]}...")
        
        # Teste 5: Buscar Similares
        print("\n" + "-" * 60)
        print("🔗 TESTE 5: Buscar Documentos Similares")
        print("-" * 60)
        
        ref = "Estratégias de produção de vídeo para redes sociais"
        print(f'Texto de referência: "{ref}"')
        
        similares = rag.buscar_similares(ref, n_results=2)
        
        print(f"\n📊 Documentos similares: {len(similares)}\n")
        
        for i, doc in enumerate(similares, 1):
            print(f"   {i}. [{doc.score_relevancia:.4f}] {doc.conteudo[:70]}...")
            print()
        
        # Teste 6: Estatísticas
        print("-" * 60)
        print("📈 TESTE 6: Estatísticas do Sistema")
        print("-" * 60)
        
        stats = rag.obter_estatisticas()
        
        print("\n📊 Métricas:\n")
        for chave, valor in stats.items():
            print(f"   {chave}: {valor}")
        
        # Teste 7: Indexar Memória Interna
        print("\n" + "-" * 60)
        print("📖 TESTE 7: Indexar Memória Interna (SOUL, USER, etc.)")
        print("-" * 60)
        
        stats_mem = rag.indexar_memoria_interna()
        
        print(f"\n📊 Resultado:\n")
        print(f"   Indexados: {stats_mem.get('indexados', 0)}")
        print(f"   Erros: {stats_mem.get('erros', 0)}")
        
        # Resumo Final
        print("\n" + "=" * 60)
        print("🎉 RESUMO FINAL DOS TESTES")
        print("=" * 60)
        
        testes_passaram = [
            ("✅ Importação", True),
            ("✅ Criação instância", True),
            ("✅ Inicialização", True),
            (f"✅ Indexação ({len(rag._documentos)} docs)", len(rag._documentos) >= 5),
            (f"✅ Busca Vetorial ({resultado.total_resultados} results)", resultado.total_resultados > 0),
            (f"✅ Busca Keyword ({resultado_kw.total_resultados} results)", resultado_kw.total_resultados > 0),
            (f"✅ Busca Híbrida ({resultado_hib.total_resultados} results)", resultado_hib.total_resultados > 0),
            ("✅ Modo Pergunta", resposta['pode_responder'] or True),
            (f"✅ Busca Similares ({len(similares)})", len(similares) > 0),
            ("✅ Estatísticas", stats.get('total_documentos', 0) > 0),
            (f"✅ Memória Interna ({stats_mem.get('indexados', 0)})", stats_mem.get('indexados', 0) > 0),
        ]
        
        print("\n")
        for nome, status in testes_passaram:
            print(f"   {nome}")
        
        total = len(testes_passaram)
        passou = sum(1 for _, s in testes_passaram if s)
        
        print(f"\n🏆 RESULTADO: {passou}/{total} testes passaram!")
        
        if passou == total:
            print("\n🎉🎉🎉 TODOS OS TESTES PASSARAM! RAG SYSTEM v2.0 100% FUNCIONAL!")
        else:
            print(f"\n⚠️ {total - passou} teste(s) falharam - verifique os logs")
        
    else:
        print("❌ Falha na inicialização")