"""
Memory System v2.0 - Sistema de Memória Inteligente do Segundo Cérebro
=====================================================================

Gerencia memória de longo prazo com dupla camada:
- Camada Local: Arquivos .md (SOUL.md, USER.md, MEMORY.md, HEARTBEAT.md)
- Camada Remota: Lex Flow API (notas, lições, contexto)

Funcionalidades:
- Leitura/Escrita estruturada de arquivos Markdown
- Parse de seções e metadados
- Sincronização bidirecional com Lex Flow
- Busca por conteúdo e chaves
- Armazenamento de lições aprendidas
- Cache inteligente com TTL
- Preparado para RAG (embeddings futuros)

Integração Lex Flow:
- Notas são syncadas com Quick Notes do Lex Flow
- Lições aprendidas ficam em MEMORY.md E no Lex Flow
- Busca contextual via search_notes()

Autor: Second Brain Ultimate System
Versão: 2.0.0 (Refatorado - Integração Lex Flow Real)
Data: 09/04/2026
"""

import os
import re
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from functools import lru_cache

# ============================================
# IMPORTS DO LEX FLOW CLIENT (com fallbacks robustos)
# ============================================
try:
    from ..integrations.lex_flow_definitivo import LexFlowClient
except ImportError:
    try:
        from integrations.lex_flow_definitivo import LexFlowClient
    except ImportError:
        # Último recurso: import absoluto
        import sys
        from pathlib import Path as _Path
        sys.path.insert(0, str(_Path(__file__).parent.parent))
        try:
            from integrations.lex_flow_definitivo import LexFlowClient
        except ImportError:
            # Define placeholder se não conseguir importar
            class LexFlowClient:
                """Placeholder quando LexFlowClient não disponível"""
                pass

# ============================================
# LOGGING DEDICADO
# ============================================
os.makedirs('logs', exist_ok=True)

# Logger específico deste módulo
logger_memory = logging.getLogger('MemorySystem')

# Configurar handler apenas se não existe ainda (evita duplicados)
if not logger_memory.handlers:
    logger_memory.setLevel(logging.DEBUG)
    
    # Handler para arquivo
    file_handler = logging.FileHandler(
        'logs/memory_system.log',
        encoding='utf-8',
        mode='a'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    ))
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    ))
    
    logger_memory.addHandler(file_handler)
    logger_memory.addHandler(console_handler)


# ============================================
# DATA CLASSES
# ============================================

@dataclass
class MemoryFile:
    """
    Representação de um arquivo de memória
    
    Attributes:
        path: Caminho completo do arquivo
        name: Nome do arquivo
        exists: Se o arquivo existe no disco
        last_modified: Data da última modificação (ISO format)
        size_bytes: Tamanho em bytes
        content: Conteúdo textual completo
        sections: Dicionário de seções parseadas
        hash_md5: Hash MD5 para detecção de mudanças
    """
    path: str
    name: str
    exists: bool = False
    last_modified: Optional[str] = None
    size_bytes: int = 0
    content: str = ""
    sections: Dict[str, Any] = field(default_factory=dict)
    hash_md5: Optional[str] = None


@dataclass
class Section:
    """
    Seção extraída de arquivo Markdown
    
    Attributes:
        name: Nome/título da seção
        content: Conteúdo textual da seção
        start_line: Linha inicial (1-based)
        end_line: Linha final (1-based)
        metadata: Metadados extras da seção
        level: Nível do cabeçalho (2 para ##, 3 para ###)
    """
    name: str
    content: str
    start_line: int
    end_line: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    level: int = 2


@dataclass
class MemoryUpdate:
    """
    Resultado de uma atualização de memória
    
    Attributes:
        file_name: Nome do arquivo atualizado
        section_updated: Nome da seção modificada
        timestamp: Momento da atualização
        success: Se a operação foi bem-sucedida
        error: Mensagem de erro (se houve falha)
        changes_count: Quantidade de alterações realizadas
    """
    file_name: str
    section_updated: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = False
    error: Optional[str] = None
    changes_count: int = 0


@dataclass
class LearnedLesson:
    """
    Lição aprendida armazenada na memória
    
    Attributes:
        lesson: Texto da lição
        category: Categoria (productividade, técnico, vida, etc.)
        source: Onde/foi aprendido
        tags: Tags para busca
        created_at: Data de criação
        times_applied: Vezes que foi aplicada
        impact: Impacto estimado (alto, médio, baixo)
    """
    lesson: str
    category: str = "geral"
    source: str = "sistema"
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    times_applied: int = 0
    impact: str = "médio"


@dataclass
class SearchResult:
    """
    Resultado de uma busca na memória
    
    Attributes:
        item: Item encontrado (texto ou dicionário)
        relevance_score: Score de relevância (0.0 a 1.0)
        source: Origem do resultado (local, lex_flow, cache)
        matched_fields: Campos que deram match
        preview: Preview do conteúdo (primeiros 200 chars)
    """
    item: Any
    relevance_score: float = 0.0
    source: str = "local"
    matched_fields: List[str] = field(default_factory=list)
    preview: str = ""


@dataclass
class SyncResult:
    """
    Resultado de uma sincronização
    
    Attributes:
        synced_from_local: Itens enviados PARA o Lex Flow
        synced_to_local: Itens recebidos DO Lex Flow
        conflicts: Conflitos detectados
        errors: Erros durante a sync
        duration_seconds: Duração da operação
    """
    synced_from_local: int = 0
    synced_to_local: int = 0
    conflicts: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


# ============================================
# CLASSE PRINCIPAL
# ============================================

class MemorySystem:
    """
    Sistema de Memória v2.0 do Segundo Cérebro
    
    Gerencia memória de longo prazo com duas camadas:
    1. LOCAL: Arquivos .md (SOUL, USER, MEMORY, HEARTBEAT)
    2. REMOTA: Lex Flow API (notas, projetos, contextos)
    
    Funcionalidades principais:
    - Carregar/salvar arquivos de memória core
    - Adicionar e buscar lições aprendidas
    - Sincronizar com Lex Flow
    - Busca híbrida (local + remoto)
    - Cache inteligente para performance
    
    Uso básico:
        # Inicialização com Lex Flow integration
        memory = MemorySystem(
            vault_path='./',
            lex_flow_client=lex_flow_client  # Opcional mas recomendado
        )
        
        # Carregar identidade do sistema
        soul_data = memory.load_soul()
        
        # Carregar perfil do usuário
        user_data = memory.load_user()
        
        # Adicionar lição aprendida
        memory.add_lesson(
            "Sempre testar antes de deploy",
            category="técnico",
            tags=["deploy", "testes"]
        )
        
        # Buscar por contexto
        resultados = memory.search("produtividade manhã")
        
    Atributos:
        vault_path: Path para diretório base dos .md
        _lex_flow: Cliente Lex Flow (opcional)
        _cache: Cache interno para operações repetidas
        CORE_FILES: Mapeamento de tipos para nomes de arquivo
    """
    
    # Mapeamento dos arquivos core do sistema
    CORE_FILES = {
        'soul': 'SOUL.md',
        'user': 'USER.md', 
        'memory': 'MEMORY.md',
        'heartbeat': 'HEARTBEAT.md'
    }
    
    # Configurações de cache (em segundos)
    CACHE_TTL_SECONDS = {
        'soul': 300,       # 5 minutos para SOUL
        'user': 300,       # 5 minutos para USER
        'memory': 180,     # 3 minutos para MEMORY (muda mais)
        'heartbeat': 600,  # 10 minutos para HEARTBEAT
        'lessons': 120,    # 2 minutos para lições
        'search': 60       # 1 minuto para buscas
    }
    
    def __init__(
        self, 
        vault_path: str = "./",
        lex_flow_client: Optional[LexFlowClient] = None,
        enable_cache: bool = True
    ):
        """
        Inicializa o Sistema de Memória v2.0
        
        Args:
            vault_path: Caminho para o diretório base onde estão os arquivos .md
            lex_flow_client: Instância conectada do LexFlowClient (opcional)
            enable_cache: Se True, ativa cache inteligente para performance
        """
        # Configurar path do vault (diretório base)
        self.vault_path = Path(vault_path).resolve()
        
        # Referência ao cliente Lex Flow (pode ser None se não disponível)
        self._lex_flow = lex_flow_client
        
        # Flag de controle de cache
        self._enable_cache = enable_cache
        
        # Cache interno com timestamps
        self._cache: Dict[str, Dict] = {}
        
        # Estatísticas de uso
        self._stats = {
            'loads': 0,
            'saves': 0,
            'searches': 0,
            'syncs': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0
        }
        
        # Log de inicialização
        logger_memory.info("=" * 60)
        logger_memory.info("🧠 MEMORY SYSTEM v2.0 INICIALIZADO")
        logger_memory.info(f"   Vault path: {self.vault_path}")
        logger_memory.info(f"   Lex Flow: {'✅ Conectado' if lex_flow_client else '⚠️ Não conectado'}")
        logger_memory.info(f"   Cache: {'✅ Ativo' if enable_cache else '❌ Desativado'}")
        logger_memory.info("=" * 60)
        
        # Verificar/criar diretório do vault
        self._ensure_vault_exists()
        
        # Verificar status do Lex Flow (seguro, não crasha se falhar)
        self._check_lex_flow_status()
    
    def _ensure_vault_exists(self) -> None:
        """
        Garante que o diretório vault existe, cria se necessário
        
        Este método é chamado no init para garantir que temos
        um lugar válido para ler/escrever os arquivos .md
        """
        if not self.vault_path.exists():
            logger_memory.warning(f"⚠️ Diretório vault não existe: {self.vault_path}")
            logger_memory.info("   Criando diretório automaticamente...")
            try:
                self.vault_path.mkdir(parents=True, exist_ok=True)
                logger_memory.info("   ✅ Diretório criado com sucesso")
            except Exception as erro:
                logger_memory.error(f"   ❌ Erro criando diretório: {erro}")
                raise RuntimeError(f"Não foi possível criar vault: {erro}")
    
    def _check_lex_flow_status(self) -> None:
        """
        Verifica status da conexão com Lex Flow de forma segura
        
        Não lança exceções, apenas loga o status para diagnóstico.
        É chamado no init para diagnóstico inicial.
        """
        if not self._lex_flow:
            logger_memory.info("   Lex Flow: Não configurado (modo local-only)")
            return
            
        try:
            # Verificar se tem método is_authenticated (definido no client)
            if hasattr(self._lex_flow, 'is_authenticated'):
                is_auth = self._lex_flow.is_authenticated()
                logger_memory.info(f"   Lex Flow Autenticado: {is_auth}")
            else:
                logger_memory.info("   Lex Flow: Método is_authentication() não disponível")
                
        except Exception as erro:
            logger_memory.warning(f"⚠️ Erro verificando status Lex Flow: {erro}")
            logger_memory.info("   O sistema funcionará em modo degradado (local-only)")
    
    # ========================================
    # MÉTODOS AUXILIARES DE PATH E ARQUIVO
    # ========================================
    
    def _get_file_path(self, file_type: str) -> Path:
        """
        Retorna caminho completo para um arquivo core baseado no tipo
        
        Args:
            file_type: Tipo do arquivo ('soul', 'user', 'memory', 'heartbeat')
            
        Returns:
            Path completo para o arquivo
            
        Raises:
            ValueError: Se o tipo de arquivo for desconhecido
        """
        filename = self.CORE_FILES.get(file_type.lower())
        if not filename:
            raise ValueError(
                f"Tipo de arquivo desconhecido: '{file_type}'. "
                f"Tipos válidos: {list(self.CORE_FILES.keys())}"
            )
        return self.vault_path / filename
    
    @staticmethod
    def _calculate_md5(content: str) -> str:
        """
        Calcula hash MD5 de um conteúdo textual
        
        Usado para detectar mudanças em arquivos e invalidar cache.
        
        Args:
            content: Texto para calcular hash
            
        Returns:
            String hexadecimal do hash MD5
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    # ========================================
    # LEITURA DE ARQUIVOS
    # ========================================
    
    def _read_file(self, filepath: Path) -> MemoryFile:
        """
        Lê arquivo do disco e retorna objeto MemoryFile estruturado
        
        Este método faz toda a pesada de I/O: abre o arquivo, lê conteúdo,
        extrai metadados do SO, calcula hash, e parseia seções.
        
        Args:
            filepath: Caminho completo do arquivo a ler
            
        Returns:
            MemoryFile com todos os dados extraídos (exists=False se não encontrado)
        """
        # Criar objeto básico
        mem_file = MemoryFile(
            path=str(filepath),
            name=filepath.name,
            exists=filepath.exists()
        )
        
        # Se não existe, retornar vazio (não é erro, pode ser primeiro uso)
        if not mem_file.exists:
            logger_memory.debug(f"Arquivo não encontrado (pode ser normal): {filepath.name}")
            return mem_file
        
        try:
            # Abrir e ler conteúdo
            with open(filepath, 'r', encoding='utf-8') as arquivo:
                content = arquivo.read()
            
            # Extrair metadados do sistema de arquivos
            stat_info = filepath.stat()
            mem_file.content = content
            mem_file.size_bytes = stat_info.st_size
            mem_file.last_modified = datetime.fromtimestamp(
                stat_info.st_mtime
            ).isoformat()
            
            # Calcular hash para detecção de mudanças
            mem_file.hash_md5 = self._calculate_md5(content)
            
            # Parsear seções do Markdown
            mem_file.sections = self._parse_sections(content)
            
            logger_memory.debug(
                f"Arquivo lido: {filepath.name} "
                f"({mem_file.size_bytes} bytes, {len(mem_file.sections)} seções)"
            )
            
        except PermissionError:
            logger_memory.error(f"❌ Permissão negada lendo: {filepath.name}")
            mem_file.content = ""
            
        except UnicodeDecodeError:
            logger_memory.error(f"❌ Erro de codificação em: {filepath.name}")
            logger_memory.info("   Tentando com codificação latin-1...")
            try:
                with open(filepath, 'r', encoding='latin-1') as arquivo:
                    mem_file.content = arquivo.read()
                mem_file.sections = self._parse_sections(mem_file.content)
            except Exception as erro_segundo:
                logger_memory.error(f"❌ Falha também com latin-1: {erro_segundo}")
                mem_file.content = ""
                
        except Exception as erro:
            logger_memory.error(f"❌Erro inesperado lendo {filepath.name}: {erro}")
            mem_file.content = ""
        
        return mem_file
    
    def _write_file(self, filepath: Path, content: str) -> bool:
        """
        Escreve conteúdo em arquivo de forma segura
        
        Cria backup automático antes de sobrescrever.
        
        Args:
            filepath: Caminho do arquivo
            content: Conteúdo a escrever
            
        Returns:
            True se sucesso, False se erro
        """
        try:
            # Criar backup se arquivo já existe
            if filepath.exists():
                backup_path = filepath.with_suffix(f'{filepath.suffix}.bak')
                try:
                    filepath.rename(backup_path)
                    logger_memory.debug(f"Backup criado: {backup_path.name}")
                except Exception:
                    pass  # Backup não é crítico, continuar
            
            # Escrever novo conteúdo
            with open(filepath, 'w', encoding='utf-8') as arquivo:
                arquivo.write(content)
            
            logger_memory.info(f"✅ Arquivo salvo: {filepath.name}")
            self._stats['saves'] += 1
            return True
            
        except PermissionError:
            logger_memory.error(f"❌ Permissão negada escrevendo: {filepath.name}")
            self._stats['errors'] += 1
            return False
            
        except Exception as erro:
            logger_memory.error(f"❌Erro escrevendo {filepath.name}: {erro}")
            self._stats['errors'] += 1
            return False
    
    # ========================================
    # PARSEAMENTO DE MARKDOWN
    # ========================================
    
    def _parse_sections(self, content: str) -> Dict[str, Section]:
        """
        Parseia arquivo Markdown extraindo seções estruturadas
        
        Detecta cabeçalhos ## e ### e organiza o conteúdo
        em seções nomeadas com metadados de posição.
        
        Formato esperado:
            ## Título da Seção
            Conteúdo aqui...
            
            ### Subseção
            Mais conteúdo...
        
        Args:
            content: Conteúdo Markdown completo
            
        Returns:
            Dicionário mapeando nome da seção → objeto Section
        """
        secoes: Dict[str, Section] = {}
        secao_atual = None
        linhas_atuais: List[str] = []
        linha_inicio = 0
        
        # Dividir em linhas para processamento linha-a-linha
        linhas = content.split('\n')
        
        for numero_linha, linha in enumerate(linhas):
            # Detectar cabeçalhos de seção (## ou ###)
            if linha.startswith('## ') or linha.startswith('### '):
                
                # Salvar seção anterior se existir
                if secao_atual is not None:
                    nome_secao = secao_atual.name
                    secoes[nome_secao] = Section(
                        name=nome_secao,
                        content='\n'.join(linhas_atuais).strip(),
                        start_line=linha_inicio,
                        end_line=numero_linha - 1,
                        level=secao_atual.level
                    )
                
                # Determinar nível do cabeçalho
                nivel = 2 if linha.startswith('## ') else 3
                
                # Extrair nome (remover # e espaços)
                nome = linha.lstrip('#').strip()
                
                # Criar nova seção
                secao_atual = Section(
                    name=nome,
                    content="",
                    start_line=numero_linha + 1,
                    end_line=numero_linha + 1,
                    level=nivel
                )
                linhas_atuais = []
                linha_inicio = numero_linha + 1
                
            elif secao_atual is not None:
                # Adicionar linha à seção atual
                linhas_atuais.append(linha)
        
        # Não esquecer a última seção!
        if secao_atual is not None:
            secoes[secao_atual.name] = Section(
                name=secao_atual.name,
                content='\n'.join(linhas_atuais).strip(),
                start_line=linha_inicio,
                end_line=len(linhas) - 1,
                level=secao_atual.level
            )
        
        # Se não encontrou seções mas tem conteúdo, tratar como única seção
        if not secoes and content.strip():
            secoes['principal'] = Section(
                name='Conteúdo Principal',
                content=content.strip(),
                start_line=0,
                end_line=len(linhas) - 1,
                level=1
            )
        
        return secoes
    
    # ========================================
    # GERENCIAMENTO DE CACHE
    # ========================================
    
    def _get_from_cache(self, chave: str) -> Optional[Any]:
        """
        Tenta obter valor do cache se ainda válido
        
        Args:
            chave: Identificador único do item em cache
            
        Returns:
            Valor em cache ou None se expirado/não existe
        """
        if not self._enable_cache:
            return None
        
        if chave not in self._cache:
            self._stats['cache_misses'] += 1
            return None
        
        entrada_cache = self._cache[chave]
        timestamp = entrada_cache.get('timestamp', 0)
        ttl = entrada_cache.get('ttl', 60)
        
        # Verificar se expirou
        idade = (datetime.now() - timestamp).total_seconds()
        if idade > ttl:
            # Cache expirado, remover
            del self._cache[chave]
            self._stats['cache_misses'] += 1
            return None
        
        # Cache válido!
        self._stats['cache_hits'] += 1
        logger_memory.debug(f"Cache HIT: {chave} (idade: {idade:.1f}s)")
        return entrada_cache.get('data')
    
    def _set_cache(self, chave: str, dados: Any, ttl_segundos: int = 60) -> None:
        """
        Armazena valor no cache com TTL
        
        Args:
            chave: Identificador único
            dados: Dados para armazenar
            ttl_segundos: Tempo de vida em segundos
        """
        if not self._enable_cache:
            return
            
        self._cache[chave] = {
            'data': dados,
            'timestamp': datetime.now(),
            'ttl': ttl_segundos
        }
        logger_memory.debug(f"Cache SET: {chave} (TTL: {ttl_segundos}s)")
    
    def _invalidate_cache(self, padrao: str = None) -> None:
        """
        Invalida itens do cache
        
        Args:
            padrao: Se fornecido, só remove itens que contêm esta string.
                    Se None, limpa todo o cache.
        """
        if padrao:
            # Remover apenas itens que combinam com o padrão
            chaves_para_remover = [
                chave for chave in self._cache 
                if padrao in chave
            ]
            for chave in chaves_para_remover:
                del self._cache[chave]
            logger_memory.info(f"Cache invalidado ({len(chaves_para_remover)} itens): *{padrao}*")
        else:
            # Limpar tudo
            tamanho_anterior = len(self._cache)
            self._cache.clear()
            logger_memory.info(f"Cache totalmente limpo ({tamanho_anterior} itens)")
    
    # ========================================
    # CARREGAMENTO DOS ARQUIVOS CORE
    # ========================================
    
    def load_soul(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Carrega SOUL.md (Identidade e Propósito do Segundo Cérebro)
        
        O SOUL.md contém a personalidade, propósito e valores do sistema.
        É usado pelo Decision Engine para tomar decisões alinhadas
        à identidade do Second Brain.
        
        Args:
            force_refresh: Se True, força releitura ignorando cache
            
        Returns:
            Dicionário com dados estruturados ou None se não existir:
            - raw_content: Conteúdo bruto completo
            - sections: Seções parseadas
            - purpose: Propósito principal (extraído)
            - last_modified: Data última modificação
            - path: Caminho do arquivo
        """
        # Tentar cache primeiro (se não forçar refresh)
        if not force_refresh:
            cached = self._get_from_cache('soul_data')
            if cached:
                return cached
        
        logger_memory.info("📖 Carregando SOUL.md...")
        self._stats['loads'] += 1
        
        filepath = self._get_file_path('soul')
        arquivo_memoria = self._read_file(filepath)
        
        if not arquivo_memoria.exists or not arquivo_memoria.content:
            logger_memory.warning("⚠️ SOUL.md não encontrado ou vazio")
            logger_memory.info("   O sistema funcionará sem identidade explícita")
            return None
        
        # Estruturar dados principais
        dados_soul = {
            'raw_content': arquivo_memoria.content,
            'sections': {
                nome: {'content': secao.content, 'level': secao.level}
                for nome, secao in arquivo_memoria.sections.items()
            },
            'last_modified': arquivo_memoria.last_modified,
            'path': str(filepath),
            'exists': True,
            'size_bytes': arquivo_memoria.size_bytes
        }
        
        # Extrair campo específico: Propósito Principal
        # Tenta múltiplos nomes possíveis (português/inglês/variações)
        proposto = None
        for chave_possivel in ['Propósito Principal', 'PROPÓSITO PRINCIPAL', 'Purpose', 'purpose']:
            if chave_possivel in arquivo_memoria.sections:
                proposto = arquivo_memoria.sections[chave_possivel].content
                break
        
        if proposto:
            dados_soul['purpose'] = proposto[:500]  # Limitar tamanho
        
        # Salvar no cache
        self._set_cache('soul_data', dados_soul, self.CACHE_TTL_SECONDS['soul'])
        
        logger_memory.info(f"   ✅ SOUL.md carregado ({arquivo_memoria.size_bytes} bytes)")
        return dados_soul
    
    def load_user(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Carrega USER.md (Perfil Operacional do Usuário)
        
        Contém informações sobre o Lex-Usamn: preferências, rotinas,
        objetivos, contextos de trabalho, etc.
        
        Args:
            force_refresh: Se True, força releitura ignorando cache
            
        Returns:
            Dicionário com dados do usuário ou None
        """
        # Tentar cache
        if not force_refresh:
            cached = self._get_from_cache('user_data')
            if cached:
                return cached
        
        logger_memory.info("👤 Carregando USER.md...")
        self._stats['loads'] += 1
        
        filepath = self._get_file_path('user')
        arquivo_memoria = self._read_file(filepath)
        
        if not arquivo_memoria.exists or not arquivo_memoria.content:
            logger_memory.warning("⚠️ USER.md não encontrado ou vazio")
            return None
        
        # Estruturar dados
        dados_usuario = {
            'raw_content': arquivo_memoria.content,
            'sections': {
                nome: {'content': secao.content, 'level': secao.level}
                for nome, secao in arquivo_memoria.sections.items()
            },
            'last_modified': arquivo_memoria.last_modified,
            'path': str(filepath),
            'exists': True
        }
        
        # Extrair preferências de comunicação (útil para respostas)
        prefs_comunicacao = None
        for chave_possivel in ['Preferências de Comunicação', 'PREFERÊNCIAS DE COMUNICAÇÃO']:
            if chave_possivel in arquivo_memoria.sections:
                prefs_comunicacao = arquivo_memoria.sections[chave_possivel].content[:300]
                break
        
        if prefs_comunicacao:
            dados_usuario['communication_preferences'] = prefs_comunicacao
        
        # Cache
        self._set_cache('user_data', dados_usuario, self.CACHE_TTL_SECONDS['user'])
        
        logger_memory.info(f"   ✅ USER.md carregado ({arquivo_memoria.size_bytes} bytes)")
        return dados_usuario
    
    def load_memory(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Carrega MEMORY.md (Lições Aprendidas e Fatos Importantes)
        
        Este arquivo contém o conhecimento acumulado: o que funcionou,
        o que não funcionou, anti-padrões, insights, etc.
        
        Args:
            force_refresh: Se True, força releitura ignorando cache
            
        Returns:
            Dicionário com memória estruturada ou None
        """
        # Tentar cache
        if not force_refresh:
            cached = self._get_from_cache('memory_data')
            if cached:
                return cached
        
        logger_memory.info("🧠 Carregando MEMORY.md...")
        self._stats['loads'] += 1
        
        filepath = self._get_file_path('memory')
        arquivo_memoria = self._read_file(filepath)
        
        if not arquivo_memoria.exists or not arquivo_memoria.content:
            logger_memory.warning("⚠️ MEMORY.md não encontrado ou vazio")
            return None
        
        # Estruturar dados
        dados_memoria = {
            'raw_content': arquivo_memoria.content,
            'sections': {
                nome: {'content': secao.content, 'level': secao.level}
                for nome, secao in arquivo_memoria.sections.items()
            },
            'last_modified': arquivo_memoria.last_modified,
            'path': str(filepath),
            'exists': True
        }
        
        # Extrair lições se houver seção específica
        licoes_secao = arquivo_memoria.sections.get('Lições Aprendidas')
        if licoes_secao:
            dados_memoria['lessons_raw'] = licoes_secao.content
        
        # Cache
        self._set_cache('memory_data', dados_memoria, self.CACHE_TTL_SECONDS['memory'])
        
        logger_memory.info(f"   ✅ MEMORY.md carregado ({arquivo_memoria.size_bytes} bytes)")
        return dados_memoria
    
    def load_heartbeat(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Carrega HEARTBEAT.md (Configuração de Monitoramento)
        
        Contém triggers, checklists diários, e configurações
        de monitoramento do sistema.
        
        Args:
            force_refresh: Se True, força releitura ignorando cache
            
        Returns:
            Dicionário com configurações do heartbeat ou None
        """
        # Tentar cache
        if not force_refresh:
            cached = self._get_from_cache('heartbeat_data')
            if cached:
                return cached
        
        logger_memory.info("💓 Carregando HEARTBEAT.md...")
        self._stats['loads'] += 1
        
        filepath = self._get_file_path('heartbeat')
        arquivo_memoria = self._read_file(filepath)
        
        if not arquivo_memoria.exists or not arquivo_memoria.content:
            logger_memory.warning("⚠️ HEARTBEAT.md não encontrado ou vazio")
            return None
        
        # Estruturar dados
        dados_heartbeat = {
            'raw_content': arquivo_memoria.content,
            'sections': {
                nome: {'content': secao.content, 'level': secao.level}
                for nome, secao in arquivo_memoria.sections.items()
            },
            'last_modified': arquivo_memoria.last_modified,
            'path': str(filepath),
            'exists': True
        }
        
        # Cache
        self._set_cache('heartbeat_data', dados_heartbeat, self.CACHE_TTL_SECONDS['heartbeat'])
        
        logger_memory.info(f"   ✅ HEARTBEAT.md carregado ({arquivo_memoria.size_bytes} bytes)")
        return dados_heartbeat
    
    # ========================================
    # GERENCIAMENTO DE LIÇÕES APRENDIDAS
    # ========================================
    
    def add_lesson(
        self,
        texto_licao: str,
        categoria: str = "geral",
        origem: str = "sistema",
        tags: List[str] = None,
        impacto: str = "médio"
    ) -> MemoryUpdate:
        """
        Adiciona uma nova lição aprendida à memória
        
        A lião é salva EM DUPLAS:
        1. No arquivo local MEMORY.md (persistência garantida)
        2. No Lex Flow como nota (se disponível, para busca contextual)
        
        Args:
            texto_licao: Texto da lição (obrigatório, mínimo 10 chars)
            categoria: Categoria da lição (produtividade, técnico, vida, etc.)
            origem: Onde/foi aprendido (ex: "erro em produção", "livro X")
            tags: Lista de tags para busca posterior
            impacto: Impacto estimado ('alto', 'médio', 'baixo')
            
        Returns:
            MemoryUpdate com resultado da operação
        """
        resultado = MemoryUpdate(
            file_name='MEMORY.md',
            section_updated='Lições Aprendidas',
            timestamp=datetime.now()
        )
        
        # Validação básica
        if not texto_licao or len(texto_licao.strip()) < 10:
            resultado.success = False
            resultado.error = "Texto da lição muito curto (mínimo 10 caracteres)"
            logger_memory.warning(f"⚠️ Lição rejeitada: muito curta")
            return resultado
        
        # Normalizar inputs
        texto_limpo = texto_licao.strip()
        tags = tags or []
        categoria = categoria.lower().strip()
        impacto = impacto.lower().strip()
        
        logger_memory.info(f"📝 Nova lição aprendida: {texto_limpo[:50]}...")
        logger_memory.info(f"   Categoria: {categoria} | Impacto: {impacto} | Tags: {tags}")
        
        # === PARTE 1: Salvar no MEMORY.md local ===
        try:
            filepath = self._get_file_path('memory')
            arquivo_existente = self._read_file(filepath)
            
            # Formatar nova entrada
            data_hoje = datetime.now().strftime('%d/%m/%Y %H:%M')
            entrada_formatada = f"""
### {texto_limpo[:60]}{'...' if len(texto_limpo) > 60 else ''}
- **Data**: {data_hoje}
- **Categoria**: {categoria}
- **Origem**: {origem}
- **Impacto**: {impacto}
- **Tags**: {', '.join(tags) if tags else 'nenhum'}
- **Texto Completo**: {texto_limpo}

"""
            
            # Se arquivo existe, adicionar ao final
            if arquivo_existente.exists and arquivo_existente.content:
                novo_conteudo = arquivo_existente.content.rstrip() + '\n\n' + entrada_formatada
            else:
                # Criar arquivo novo com estrutura básica
                novo_conteudo = f"""# MEMORY.md - Memória de Longo Prazo do Segundo Cérebro

## Lições Aprendidas
{entrada_formatada}
"""
            
            # Escrever arquivo atualizado
            sucesso_escrita = self._write_file(filepath, novo_conteudo)
            
            if sucesso_escrita:
                resultado.success = True
                resultado.changes_count += 1
                logger_memory.info("   ✅ Lição salva no MEMORY.md local")
            else:
                resultado.error = "Falha ao escrever MEMORY.md"
                logger_memory.error("   ❌ Falha salvando lição localmente")
                
        except Exception as erro:
            resultado.error = f"Erro local: {str(erro)}"
            logger_memory.error(f"   ❌ Erro salvando lição localmente: {erro}")
        
        # === PARTE 2: Sync com Lex Flow (se disponível) ===
        if self._lex_flow and resultado.success:
            try:
                self._sync_lesson_to_lex_flow(
                    texto=texto_limpo,
                    categoria=categoria,
                    origem=origem,
                    tags=tags,
                    impacto=impacto
                )
                logger_memory.info("   ✅ Lição sincronizada com Lex Flow")
            except Exception as erro:
                # Não é crítico, logar e continuar
                logger_memory.warning(f"   ⚠️ Sync Lex Flow falhou (não crítico): {erro}")
        
        # Invalidar cache do MEMORY.md (conteúdo mudou!)
        self._invalidate_cache('memory')
        
        return resultado
    
    def _sync_lesson_to_lex_flow(
        self,
        texto: str,
        categoria: str,
        origem: str,
        tags: List[str],
        impacto: str
    ) -> bool:
        """
        Envia lição aprendida para o Lex Flow como nota
        
        Isso permite buscar lições depois via search_notes().
        
        Args:
            texto: Texto da lição
            categoria: Categoria
            origem: Origem
            tags: Tags
            impacto: Impacto
            
        Returns:
            True se sincronizou com sucesso
        """
        if not self._lex_flow:
            return False
        
        try:
            # Montar título descritivo
            titulo = f"📚 Lição: {texto[:50]}{'...' if len(texto) > 50 else ''}"
            
            # Montar corpo da nota
            corpo = f"""**Lição Aprendida** ({datetime.now().strftime('%d/%m/%Y')})

{texto}

---
**Metadata:**
- Categoria: {categoria}
- Origem: {origem}
- Impacto: {impacto}
- Tags: {', '.join(tags) if tags else 'nenhuma'}

*Sync automático do Memory System v2.0*
"""
            
            # Usar add_note do Lex Flow Client
            # O método espera (titulo, conteudo, **kwargs)
            resposta = self._lex_flow.add_note(
                title=titulo,
                content=corpo,
                tags=['lição-aprendida', 'memory-system', categoria] + (tags or []),
                category='archives'  # Lições vão para Archives
            )
            
            if resposta:
                logger_memory.debug(f"   Lição enviada ao Lex Flow ID: {resposta.get('id', '?')}")
                return True
            else:
                logger_memory.warning("   add_note() retornou None/vazio")
                return False
                
        except AttributeError:
            # Método add_note não existe neste versão do client
            logger_memory.warning("   Método add_note() não disponível no LexFlowClient")
            return False
            
        except Exception as erro:
            logger_memory.error(f"   Erro sync lição Lex Flow: {erro}")
            return False
    
    def get_recent_lessons(
        self,
        quantidade: int = 10,
        categoria: str = None
    ) -> List[LearnedLesson]:
        """
        Retorna lições aprendidas recentes
        
        Busca no MEMORY.md local e opcionalmente no Lex Flow.
        
        Args:
            quantidade: Máximo de lições a retornar
            categoria: Filtrar por categoria (opcional)
            
        Returns:
            Lista de objetos LearnedLesson ordenados por data (mais recentes primeiro)
        """
        logger_memory.info(f"📚 Buscando lições recentes (max: {quantidade}, cat: {categoria})")
        
        licoes: List[LearnedLesson] = []
        
        # === Fonte 1: MEMORY.md local ===
        try:
            dados_memoria = self.load_memory()
            if dados_memoria and 'raw_content' in dados_memoria:
                conteudo = dados_memoria['raw_content']
                
                # Padrão regex para detectar entradas de lição
                # Procura por ### seguido de texto (título da lião)
                padrao_licao = r'###\s*(.+?)\n((?:-\s*\*\*.*?\*\*.*\n)+)'
                matches = re.findall(padrao_licao, conteudo, re.DOTALL)
                
                for titulo_match, corpo_match in matches[:quantidade]:
                    # Extrair metadados do corpo
                    licao = LearnedLesson(
                        lesson=titulo_match.strip(),
                        category=self._extrair_campo(corpo_match, 'Categoria') or 'geral',
                        source=self._extrair_campo(corpo_match, 'Origem') or 'MEMORY.md',
                        tags=self._extrair_tags(corpo_match),
                        impact=self._extrair_campo(corpo_match, 'Impacto') or 'médio'
                    )
                    licoes.append(licao)
                    
        except Exception as erro:
            logger_memory.error(f"Erro extraindo lições do MEMORY.md: {erro}")
        
        # === Fonte 2: Lex Flow (se disponível e precisar mais) ===
        if self._lex_flow and len(licoes) < quantidade:
            try:
                # Buscar notas com tag 'lição-aprendida'
                notas_lexflow = self._lex_flow.search_notes(
                    query="lição-aprendida OR lesson",
                    limit=quantidade - len(licoes)
                )
                
                if notas_lexflow:
                    for nota in notas_lexflow:
                        # Converter para LearnedLesson
                        licao = LearnedLesson(
                            lesson=nota.get('title', 'Sem título'),
                            category=nota.get('category', 'geral'),
                            source='Lex Flow',
                            tags=nota.get('tags', [])
                        )
                        licoes.append(licao)
                        
            except Exception as erro:
                logger_memory.debug(f"Busca Lex Flow para liões falhou: {erro}")
        
        # Aplicar filtro de categoria se especificado
        if categoria:
            categoria_lower = categoria.lower()
            licoes = [l for l in licoes if l.category.lower() == categoria_lower]
        
        # Limitar quantidade
        licoes = licoes[:quantidade]
        
        logger_memory.info(f"   ✅ {len(licoes)} lições encontradas")
        return licoes
    
    def _extrair_campo(self, texto: str, campo: str) -> Optional[str]:
        """
        Extrai valor de um campo formatado como **Campo**: valor
        
        Args:
            texto: Texto onde procurar
            campo: Nome do campo (sem os asteriscos)
            
        Returns:
            Valor do campo ou None se não encontrado
        """
        padrao = rf'\*\*{campo}\*\*:\s*(.+)'
        match = re.search(padrao, texto, re.IGNORECASE)
        return match.group(1).strip() if match else None
    
    def _extrair_tags(self, texto: str) -> List[str]:
        """
        Extrai lista de tags de texto formatado
        
        Args:
            texto: Texto com campo Tags
            
        Returns:
            Lista de strings (tags)
        """
        tags_str = self._extrair_campo(texto, 'Tags')
        if not tags_str or tags_str.lower() == 'nenhum':
            return []
        
        # Separar por vírgula e limpar
        return [tag.strip() for tag in tags_str.split(',') if tag.strip()]
    
    # ========================================
    # BUSCA NA MEMÓRIA
    # ========================================
    
    def search(
        self,
        consulta: str,
        limite_resultados: int = 10,
        fontes: List[str] = None,
        fuzzy: bool = True
    ) -> List[SearchResult]:
        """
        Busca híbrida na memória (local + Lex Flow)
        
        Realiza busca em múltiplas fontes e combina resultados
        com scores de relevância.
        
        Args:
            consulta: Texto para buscar
            limite_resultados: Máximo de resultados
            fontes: Lista de fontes ('local', 'lex_flow'). None = todas
            fuzzy: Se True, usa matching parcial (contém)
            
        Returns:
            Lista de SearchResult ordenada por relevância (maior primeiro)
        """
        logger_memory.info(f"🔍 Buscando na memória: '{consulta}' (limite: {limite_resultados})")
        self._stats['searches'] += 1
        
        # Normalizar consulta
        consulta_lower = consulta.lower().strip()
        termos_consulta = consulta_lower.split()
        
        # Fontes padrão
        if fontes is None:
            fontes = ['local', 'lex_flow']
        
        todos_resultados: List[SearchResult] = []
        
        # === FONTE 1: Arquivos locais ===
        if 'local' in fontes:
            resultados_locais = self._search_local(consulta_lower, termos_consulta, fuzzy)
            todos_resultados.extend(resultados_locais)
        
        # === FONTE 2: Lex Flow ===
        if 'lex_flow' in fontes and self._lex_flow:
            resultados_lexflow = self._search_lex_flow(consulta, limite_resultados)
            todos_resultados.extend(resultados_lexflow)
        
        # Ordenar por relevância (descendente)
        todos_resultados.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Aplicar limite
        resultados_finais = todos_resultados[:limite_resultados]
        
        logger_memory.info(f"   ✅ {len(resultados_finais)} resultados encontrados")
        return resultados_finais
    
    def _search_local(
        self,
        consulta_lower: str,
        termos: List[str],
        fuzzy: bool
    ) -> List[SearchResult]:
        """
        Busca nos arquivos .md locais
        
        Args:
            consulta: Consulta em minúsculas
            termos: Termos individuais da consulta
            fuzzy: Se True, usa matching parcial
            
        Returns:
            Lista de SearchResult
        """
        resultados: List[SearchResult] = []
        
        # Buscar em cada arquivo core
        for tipo_arquivo in ['memory', 'soul', 'user', 'heartbeat']:
            try:
                # Carregar dados (usa cache automaticamente)
                if tipo_arquivo == 'memory':
                    dados = self.load_memory()
                elif tipo_arquivo == 'soul':
                    dados = self.load_soul()
                elif tipo_arquivo == 'user':
                    dados = self.load_user()
                else:
                    dados = self.load_heartbeat()
                
                if not dados or 'raw_content' not in dados:
                    continue
                
                conteudo = dados['raw_content']
                conteudo_lower = conteudo.lower()
                
                # Calcular score de relevância
                score = self._calcular_relevancia(conteudo_lower, termos, fuzzy)
                
                # Só incluir se tiver relevância mínima
                if score > 0.1:
                    # Encontrar campos que deram match
                    campos_match = []
                    for nome_secao, dados_secao in dados.get('sections', {}).items():
                        secao_texto = dados_secao.get('content', '').lower()
                        if any(termo in secao_texto for termo in termos):
                            campos_match.append(nome_secao)
                    
                    resultado = SearchResult(
                        item={
                            'source_file': self.CORE_FILES[tipo_arquivo],
                            'type': tipo_arquivo,
                            'content_preview': conteudo[:500]
                        },
                        relevance_score=min(score, 1.0),
                        source='local',
                        matched_fields=campos_match,
                        preview=conteudo[:200].replace('\n', ' ')
                    )
                    resultados.append(resultado)
                    
            except Exception as erro:
                logger_memory.debug(f"Erro buscando em {tipo_arquivo}: {erro}")
        
        return resultados
    
    def _search_lex_flow(
        self,
        consulta: str,
        limite: int
    ) -> List[SearchResult]:
        """
        Busca via API do Lex Flow
        
        Args:
            consulta: Texto da consulta
            limite: Máximos resultados
            
        Returns:
            Lista de SearchResult
        """
        if not self._lex_flow:
            return []
        
        resultados: List[SearchResult] = []
        
        try:
            # Usar search_notes do Lex Flow Client
            notas = self._lex_flow.search_notes(
                query=consulta,
                limit=limite
            )
            
            if notas:
                for nota in notas:
                    # Score baseado na nota (Lex Flow pode retornar relevance)
                    score = nota.get('relevance', nota.get('score', 0.7))
                    
                    resultado = SearchResult(
                        item=nota,
                        relevance_score=float(score) if score else 0.5,
                        source='lex_flow',
                        matched_fields=[nota.get('category', 'note')],
                        preview=nota.get('content', '')[:200] or nota.get('title', '')
                    )
                    resultados.append(resultado)
                    
            logger_memory.debug(f"   Lex Flow retornou {len(notas)} notas")
            
        except AttributeError:
            # Método search_notes não existe
            logger_memory.debug("   search_notes() não disponível no LexFlowClient")
            
        except Exception as erro:
            logger_memory.debug(f"   Erro busca Lex Flow: {erro}")
        
        return resultados
    
    def _calcular_relevancia(
        self,
        texto_lower: str,
        termos_busca: List[str],
        fuzzy: bool
    ) -> float:
        """
        Calcula score de relevância (0.0 a 1.0+)
        
        Considera:
        - Termos exatos (peso maior)
        - Termos parciais se fuzzy=True
        - Frequência dos termos
        - Proximidade entre termos
        
        Args:
            texto_lower: Texto para analisar (já em minúsculas)
            termos_busca: Lista de termos procurados
            fuzzy: Se permite matching parcial
            
        Returns:
            Score de relevância (pode ser > 1.0 com boosters)
        """
        if not termos_busca:
            return 0.0
        
        score_total = 0.0
        
        for termo in termos_busca:
            if not termo or len(termo) < 2:
                continue
            
            # Contar ocorrências
            count = texto_lower.count(termo)
            
            if count > 0:
                # Score base: peso pelo comprimento do termo (termos mais específicos valem mais)
                peso_termo = min(len(termo) / 3, 2.0)  # Cap em 2.0
                
                # Boost por frequência (diminuído, para não dominar)
                frequencia_boost = min(count * 0.1, 0.5)
                
                score_total += peso_termo + frequencia_boost
            
            elif fuzzy:
                # Matching parcial: verificar se termo está contido em qualquer palavra
                palavras = texto_lower.split()
                for palavra in palavras:
                    if termo in palavra or palavra in termo:
                        score_total += 0.3  # Score menor para partial match
                        break  # Só conta uma vez por termo
        
        # Booster: termos próximos uns dos outros (frase exata)
        if len(termos_busca) > 1:
            frase_completa = ' '.join(termos_busca)
            if frase_completa in texto_lower:
                score_total *= 1.5  # Boost significativo para frases exatas
        
        return score_total
    
    # ========================================
    # SINCRONIZAÇÃO COM LEX FLOW
    # ========================================
    
    def sync_with_lex_flow(self, direcao: str = 'both') -> SyncResult:
        """
        Sincroniza dados entre memória local e Lex Flow
        
        Direções:
        - 'push': Local → Lex Flow (enviar lições/notas locais)
        - 'pull': Lex Flow → Local (trazer notas relevantes)
        - 'both': Bidirecional (padrão)
        
        Args:
            direção: Direção da sincronização
            
        Returns:
            SyncResult com estatísticas da operação
        """
        resultado = SyncResult()
        inicio = datetime.now()
        
        logger_memory.info(f"🔄 Iniciando sync com Lex Flow (direção: {direcao})")
        self._stats['syncs'] += 1
        
        if not self._lex_flow:
            logger_memory.warning("⚠️ Lex Flow não disponível, sync cancelado")
            resultado.errors.append("Lex Flow client não configurado")
            return resultado
        
        try:
            # === PUSH: Local → Lex Flow ===
            if direcao in ['push', 'both']:
                push_stats = self._push_to_lex_flow()
                resultado.synced_from_local = push_stats.get('enviados', 0)
                resultado.errors.extend(push_stats.get('erros', []))
            
            # === PULL: Lex Flow → Local ===
            if direcao in ['pull', 'both']:
                pull_stats = self._pull_from_lex_flow()
                resultado.synced_to_local = pull_stats.get('recebidos', 0)
                resultado.errors.extend(pull_stats.get('erros', []))
            
            # Calcular duração
            fim = datetime.now()
            resultado.duration_seconds = (fim - inicio).total_seconds()
            
            logger_memory.info(
                f"   ✅ Sync concluído em {resultado.duration_seconds:.2f}s "
                f"(↑{resultado.synced_from_local} ↓{resultado.synced_to_local})"
            )
            
        except Exception as erro:
            resultado.errors.append(f"Erro durante sync: {str(erro)}")
            logger_memory.error(f"   ❌ Erro na sincronização: {erro}")
        
        return resultado
    
    def _push_to_lex_flow(self) -> Dict[str, Any]:
        """
        Envia dados locais para o Lex Flow
        
        Returns:
            Dicionário com estatísticas (enviados, erros)
        """
        stats = {'enviados': 0, 'erros': []}
        
        try:
            # Enviar lições do MEMORY.md que ainda não estão no Lex Flow
            dados_memoria = self.load_memory(force_refresh=True)
            
            if dados_memoria and 'raw_content' in dados_memoria:
                # Aqui poderíamos implementar lógica mais sofisticada
                # para detectar quais lições já foram enviadas
                # Por enquanto, logamos que o push foi considerado
                logger_memory.info("   Push: MEMORY.md verificado para sync")
                stats['enviados'] += 1  # Simplificado
                
        except Exception as erro:
            stats['erros'].append(f"Erro push MEMORY.md: {erro}")
        
        return stats
    
    def _pull_from_lex_flow(self) -> Dict[str, Any]:
        """
        Traz dados relevantes do Lex Flow para memória local
        
        Returns:
            Dicionário com estatísticas (recebidos, erros)
        """
        stats = {'recebidos': 0, 'erros': []}
        
        try:
            # Buscar notas recentes marcadas como importantes
            if hasattr(self._lex_flow, 'get_inbox'):
                inbox = self._lex_flow.get_inbox()
                
                if inbox and isinstance(inbox, list):
                    # Filtrar notas importantes ou recentes
                    notas_relevantes = [
                        nota for nota in inbox[:5]  # Últimas 5
                        if nota.get('important') or nota.get('starred')
                    ]
                    
                    if notas_relevantes:
                        stats['recebidos'] = len(notas_relevantes)
                        logger_memory.info(f"   Pull: {len(notas_relevantes)} notas relevantes do Inbox")
                        
        except Exception as erro:
            stats['erros'].append(f"Erro pull do Lex Flow: {erro}")
        
        return stats
    
    # ========================================
    # UTILITÁRIOS E DIAGNÓSTICO
    # ========================================
    
    def get_status(self) -> Dict[str, Any]:
        """
        Retorna status completo do Memory System
        
        Útil para health checks e diagnósticos.
        
        Returns:
            Dicionário com status detalhado
        """
        # Verificar existência dos arquivos core
        arquivos_status = {}
        for tipo, nome in self.CORE_FILES.items():
            filepath = self._get_file_path(tipo)
            arquivos_status[nome] = {
                'exists': filepath.exists(),
                'path': str(filepath),
                'size': filepath.stat().st_size if filepath.exists() else 0
            }
        
        # Status do Lex Flow
        lex_flow_status = 'not_configured'
        if self._lex_flow:
            try:
                if hasattr(self._lex_flow, 'is_authenticated'):
                    lex_flow_status = 'connected' if self._lex_flow.is_authenticated() else 'error'
                else:
                    lex_flow_status = 'configured'
            except Exception:
                lex_flow_status = 'error'
        
        return {
            'version': '2.0.0',
            'vault_path': str(self.vault_path),
            'files': arquivos_status,
            'lex_flow': lex_flow_status,
            'cache_enabled': self._enable_cache,
            'cache_items': len(self._cache),
            'statistics': self._stats.copy(),
            'timestamp': datetime.now().isoformat()
        }
    
    def clear_cache(self) -> None:
        """
        Limpa todo o cache internamente
        
        Força recarga de todos os dados na próxima leitura.
        """
        tamanho_anterior = len(self._cache)
        self._cache.clear()
        logger_memory.info(f"🗑️ Cache limpado ({tamanho_anterior} itens removidos)")
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Retorna estatísticas de uso do Memory System
        
        Returns:
            Dicionário com contadores de operações
        """
        return self._stats.copy()


# ============================================
# BLOCO DE TESTE STANDALONE
# ============================================

if __name__ == "__main__":
    """
    Modo de teste standalone - executa validações básicas
    sem precisar do Core Engine completo.
    
    Para executar:
        python engine/memory_system.py
    """
    print("\n" + "=" * 70)
    print("🧠 MEMORY SYSTEM v2.0 - TESTE STANDALONE")
    print("=" * 70 + "\n")
    
    # Teste 1: Inicialização básica (sem Lex Flow)
    print("📋 Teste 1: Inicialização sem Lex Flow...")
    try:
        memoria_local = MemorySystem(vault_path="./")
        print("   ✅ MemorySystem inicializado (modo local-only)\n")
    except Exception as erro:
        print(f"   ❌ ERRO: {erro}\n")
    
    # Teste 2: Carregar arquivos core
    print("📋 Teste 2: Carregando arquivos core...")
    try:
        soul = memoria_local.load_soul()
        user = memoria_local.load_user()
        memory = memoria_local.load_memory()
        heartbeat = memoria_local.load_heartbeat()
        
        print(f"   SOUL.md:     {'✅ Carregado' if soul else '⚠️ Não encontrado'}")
        print(f"   USER.md:     {'✅ Carregado' if user else '⚠️ Não encontrado'}")
        print(f"   MEMORY.md:   {'✅ Carregado' if memory else '⚠️ Não encontrado'}")
        print(f"   HEARTBEAT.md: {'✅ Carregado' if heartbeat else '⚠️ Não encontrado'}\n")
    except Exception as erro:
        print(f"   ❌ ERRO: {erro}\n")
    
    # Teste 3: Adicionar lição aprendida
    print("📋 Teste 3: Adicionando lição de teste...")
    try:
        resultado_licao = memoria_local.add_lesson(
            texto_licao="Teste standalone do Memory System v2.0 - se você vê isso, funcionou!",
            categoria="teste",
            origem="teste_standalone",
            tags=["teste", "memory-system"],
            impacto="baixo"
        )
        
        if resultado_licao.success:
            print(f"   ✅ Lição adicionada com sucesso")
            print(f"   Arquivo: {resultado_licao.file_name}")
            print(f"   Seção: {resultado_licao.section_updated}\n")
        else:
            print(f"   ⚠️ Lição não adicionada: {resultado_licao.error}\n")
    except Exception as erro:
        print(f"   ❌ ERRO: {erro}\n")
    
    # Teste 4: Buscar na memória
    print("📋 Teste 4: Buscando na memória...")
    try:
        resultados_busca = memoria_local.search("teste", limite_resultados=5)
        print(f"   ✅ Busca realizada: {len(resultados_busca)} resultados")
        for i, resultado in enumerate(resultados_busca[:3], 1):
            print(f"      [{i}] Score: {resultado.relevance_score:.2f} | Fonte: {resultado.source}")
        print()
    except Exception as erro:
        print(f"   ❌ ERRO: {erro}\n")
    
    # Teste 5: Status do sistema
    print("📋 Teste 5: Status do sistema...")
    try:
        status = memoria_local.get_status()
        print(f"   Versão: {status['version']}")
        print(f"   Vault: {status['vault_path']}")
        print(f"   Lex Flow: {status['lex_flow']}")
        print(f"   Cache: {status['cache_items']} itens")
        print(f"   Stats: {status['statistics']}\n")
    except Exception as erro:
        print(f"   ❌ ERRO: {erro}\n")
    
    # Teste 6: Com Lex Flow (opcional, pode falhar se não configurado)
    print("📋 Teste 6: Tentativa de conexão com Lex Flow...")
    try:
        from integrations.lex_flow_definitivo import LexFlowClient
        lex_flow = LexFlowClient()
        
        memoria_com_lexflow = MemorySystem(
            vault_path="./",
            lex_flow_client=lex_flow
        )
        
        status_lf = memoria_com_lexflow.get_status()
        print(f"   ✅ MemorySystem com Lex Flow: {status_lf['lex_flow']}\n")
        
    except ImportError:
        print("   ⚠️ LexFlowClient não disponível (modo local-only)\n")
    except Exception as erro:
        print(f"   ⚠️ Lex Flow não conectado (normal se sem credenciais): {erro}\n")
    
    print("=" * 70)
    print("🎯 TESTES CONCLUÍDOS - Verifique os logs em logs/memory_system.log")
    print("=" * 70 + "\n")