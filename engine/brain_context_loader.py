"""
================================================================================
BRAIN CONTEXT LOADER v1.0.1 - Carregador de Contextos (.md Files)
================================================================================

AUTOR: Mago-Usamn | DATA: 14/04/2026 | CORRIGIDO: 15/04/2026
NOME DO ASSISTENTE: MAGO 🧙

FUNÇÃO:
Carrega os arquivos de contexto (SOUL.md, USER.md, MEMORY.md, HEARTBEAT.md)
e disponibiliza de forma otimizada para o Brain LLM Orchestrator.

CORREÇÃO v1.0.1:
✅ REMOVIDOS LIMITES DE TRUNCATION (tamanho_max: 2000 → 999999)
✅ AGORA CARREGA 100% DO CONTEÚDO DOS ARQUIVOS .md
✅ PERSONA COMPLETA DO SOUL.md (17KB+) SERÁ ENVIADA AO GEMINI
================================================================================
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass


logger_brain = logging.getLogger("BrainContextLoader")


@dataclass
class ContextoCarregado:
    """Representa um contexto carregado de um arquivo .md."""
    nome: str
    conteudo: str
    caminho_arquivo: str
    tamanho_bytes: int
    carregado_em: datetime
    valido: bool = True
    erro: Optional[str] = None
    
    @property
    def tamanho_chars(self) -> int:
        return len(self.conteudo)
    
    @property
    def resumo(self) -> str:
        return self.conteudo[:200] + ("..." if len(self.conteudo) > 200 else "")


class BrainContextLoader:
    """
    Carregador de Contextos para o Brain LLM Orchestrator.
    
    Responsabilidades:
    1. Ler arquivos .md do diretório raiz do projeto
    2. Cache inteligente (não reler se não mudou)
    3. ✅ SEM LIMITES DE TAMANHO (carrega arquivo completo!)
    4. Fornecer resumos quando necessário
    """
    
    # Mapeamento de arquivos de contexto
    # ✅ CORREÇÃO v1.0.1: Aumentado tamanho_max para 999999 (SEM TRUNCATION!)
    ARQUIVOS_CONTEXTO = {
        "soul": {
            "arquivo": "SOUL.md",
            "descricao": "Identidade e personalidade do assistente",
            "tamanho_max": 999999,  # ✅ ERA 2000 → AGORA ILIMITADO!
            "prioridade": 1
        },
        "user": {
            "arquivo": "USER.md",
            "descricao": "Perfil, objetivos e preferências do usuário",
            "tamanho_max": 999999,  # ✅ ERA 2000 → AGORA ILIMITADO!
            "prioridade": 2
        },
        "memory": {
            "arquivo": "MEMORY.md",
            "descricao": "Lições aprendidas e experiência histórica",
            "tamanho_max": 999999,  # ✅ ERA 1500 → AGORA ILIMITADO!
            "prioridade": 3
        },
        "heartbeat": {
            "arquivo": "HEARTBEAT.md",
            "descricao": "Status atual, projetos ativos, métricas do dia",
            "tamanho_max": 999999,  # ✅ ERA 1500 → AGORA ILIMITADO!
            "prioridade": 4
        }
    }
    
    def __init__(self, diretorio_raiz: Optional[str] = None):
        if diretorio_raiz:
            self._diretorio_raiz = diretorio_raiz
        else:
            # Auto-detectar: subir 1 nível de engine/
            self._diretorio_raiz = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..')
            )
        
        # Cache de contextos carregados
        self._cache: Dict[str, ContextoCarregado] = {}
        
        # Timestamps de modificação (para detectar mudanças)
        self._timestamps: Dict[str, float] = {}
        
        # Estatísticas
        self._stats = {"total_carregamentos": 0, "erros": 0, "cache_hits": 0}
        
        logger_brain.info(f"[ContextLoader] Inicializado (dir: {self._diretorio_raiz})")
    
    def carregar_todos(self, forcar_reload: bool = False) -> Dict[str, str]:
        """
        Carrega todos os contextos e retorna dicionário {nome: conteudo}.
        
        Args:
            forcar_reload: Se True, ignora cache e relê todos os arquivos
            
        Returns:
            Dicionário com os conteúdos de cada contexto
        """
        resultados = {}
        
        for nome, config in self.ARQUIVOS_CONTEXTO.items():
            try:
                conteudo = self.carregar(nome, forcar_reload=forcar_reload)
                resultados[nome] = conteudo
                
            except Exception as e:
                logger_brain.error(f"Erro carregando {nome}: {e}")
                resultados[nome] = f"[Erro ao carregar {config['arquivo']}: {str(e)[:50]}]"
                self._stats["erros"] += 1
        
        total_chars = sum(len(v) for v in resultados.values())
        logger_brain.info(f"[ContextLoader] Todos contextos carregados ({total_chars} chars totais)")
        
        return resultados
    
    def carregar(self, nome_contexto: str, forcar_reload: bool = False) -> str:
        """
        Carrega um contexto específico por nome.
        
        Args:
            nome_contexto: Um de 'soul', 'user', 'memory', 'heartbeat'
            forcar_reload: Ignorar cache e reler
            
        Returns:
            Conteúdo do arquivo (string)
            
        Raises:
            ValueError: Se nome_contexto for inválido
            FileNotFoundError: Se arquivo não existir
        """
        # Validar nome
        if nome_contexto not in self.ARQUIVOS_CONTEXTO:
            raise ValueError(
                f"Contexto inválido: {nome_contexto}. "
                f"Disponíveis: {list(self.ARQUIVOS_CONTEXTO.keys())}"
            )
        
        config = self.ARQUIVOS_CONTEXTO[nome_contexto]
        arquivo = config["arquivo"]
        caminho_completo = os.path.join(self._diretorio_raiz, arquivo)
        
        # Verificar cache (se não forçar reload)
        if not forcar_reload and nome_contexto in self._cache:
            cache_entry = self._cache[nome_contexto]
            
            # Verificar se arquivo mudou desde último carregamento
            if os.path.exists(caminho_completo):
                mtime_atual = os.path.getmtime(caminho_completo)
                mtime_cache = self._timestamps.get(nome_contexto, 0)
                
                if mtime_atual <= mtime_cache:
                    self._stats["cache_hits"] += 1
                    logger_brain.debug(f"[ContextLoader] Cache hit: {nome_contexto}")
                    return cache_entry.conteudo
        
        # Ler arquivo
        logger_brain.info(f"[ContextLoader] Lendo: {arquivo}")
        
        if not os.path.exists(caminho_completo):
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho_completo}")
        
        with open(caminho_completo, 'r', encoding='utf-8') as f:
            conteudo_bruto = f.read()
        
        # Processar conteúdo (limpar, mas NÃO truncar mais!)
        tamanho_max = config["tamanho_max"]
        conteudo_processado = self._processar_conteudo(conteudo_bruto, tamanho_max)
        
        # Salvar no cache
        self._cache[nome_contexto] = ContextoCarregado(
            nome=nome_contexto,
            conteudo=conteudo_processado,
            caminho_arquivo=caminho_completo,
            tamanho_bytes=len(conteudo_processado.encode('utf-8')),
            carregado_em=datetime.now()
        )
        
        self._timestamps[nome_contexto] = os.path.getmtime(caminho_completo)
        self._stats["total_carregamentos"] += 1
        
        logger_brain.info(
            f"[ContextLoader] {nome_contexto.upper()} carregado "
            f"({len(conteudo_processado)} chars, original: {len(conteudo_bruto)} chars)"
        )
        
        return conteudo_processado
    
    def _processar_conteudo(self, conteudo: str, tamanho_max: int) -> str:
        """
        Processa o conteúdo do arquivo.
        
        v1.0.1: Só limpa linhas vazias excessivas (NÃO TRUNCA MAIS!)
        """
        # Remover linhas vazias excessivas
        linhas = conteudo.split('\n')
        linhas_limpas = []
        linhas_vazias_seguidas = 0
        
        for linha in linhas:
            if linha.strip() == '':
                linhas_vazias_seguidas += 1
                if linhas_vazias_seguidas <= 2:
                    linhas_limpas.append(linha)
            else:
                linhas_vazias_seguidas = 0
                linhas_limpas.append(linha)
        
        conteudo_limpo = '\n'.join(linhas_limpas)
        
        # ✅ CORREÇÃO v1.0.1: SÓ TRUNCA SE REALMENTE FOR MAIOR QUE 999999
        # (na prática, NUNCA vai truncar!)
        if len(conteudo_limpo) <= tamanho_max:
            return conteudo_limpo
        
        # Se por algum motivo for maior (improvável), mantém início e fim
        parte_inicio = int(tamanho_max * 0.6)
        parte_fim = tamanho_max - parte_inicio - 30
        
        inicio = conteudo_limpo[:parte_inicio]
        fim = conteudo_limpo[-parte_fim:] if parte_fim > 0 else ""
        
        resultado = f"{inicio}... [conteúdo truncado] ...{fim}"
        
        logger_brain.debug(f"Conteúdo truncado: {len(conteudo_limpo)} → {len(resultado)} chars")
        
        return resultado
    
    def obter_resumo_todos(self) -> Dict[str, str]:
        """Retorna resumo (primeiros 200 chars) de cada contexto."""
        resumos = {}
        for nome, entry in self._cache.items():
            resumos[nome] = entry.resumo
        return resumos
    
    def obter_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas do carregador."""
        return {
            "versao": "1.0.1",
            "diretorio_raiz": self._diretorio_raiz,
            "contextos_disponiveis": list(self.ARQUIVOS_CONTEXTO.keys()),
            "contextos_no_cache": list(self._cache.keys()),
            "tamanhos": {
                nome: entry.tamanho_chars 
                for nome, entry in self._cache.items()
            },
            "estatisticas": self._stats.copy(),
            "arquivos_existentes": {
                nome: os.path.exists(os.path.join(self._diretorio_raiz, config["arquivo"]))
                for nome, config in self.ARQUIVOS_CONTEXTO.items()
            }
        }
    
    def limpar_cache(self) -> None:
        """Limpa todo o cache (forçará reload no próximo acesso)."""
        self._cache.clear()
        self._timestamps.clear()
        logger_brain.info("[ContextLoader] Cache limpo")
    
    def verificar_arquivos_existem(self) -> Dict[str, bool]:
        """Verifica quais arquivos de contexto existem."""
        existencia = {}
        for nome, config in self.ARQUIVOS_CONTEXTO.items():
            caminho = os.path.join(self._diretorio_raiz, config["arquivo"])
            existencia[nome] = os.path.exists(caminho)
            
            if not existencia[nome]:
                logger_brain.warning(f"Arquivo não encontrado: {config['arquivo']}")
        
        return existencia


# =============================================================================
# INSTÂNCIA GLOBAL (Singleton)
# =============================================================================

_context_loader_global: Optional[BrainContextLoader] = None


def obter_context_loader_global() -> Optional[BrainContextLoader]:
    global _context_loader_global
    return _context_loader_global


def definir_context_loader_global(instancia: BrainContextLoader) -> None:
    global _context_loader_global
    _context_loader_global = instancia
    logger_brain.info("[GLOBAL] BrainContextLoader definido como instância global")