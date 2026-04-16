"""
================================================================================
BRAIN MIDDLEWARE v2.1 - Tipos, Enumerações e Dataclasses
================================================================================

Módulo contendo todos os tipos de dados usados pelo Brain Middleware:
- Enumerações (TipoIntencao, NivelConfianca, PrioridadeTarefa)
- Dataclasses (IntencaoDetectada, ContextoConversa, RespostaBrain)
- Constantes de configuração

AUTOR: Mago-Usamn | DATA: 12/04/2026
STATUS: ✅ Produção
NOME DO ASSISTENTE: MAGO (antigo Lex)
================================================================================
"""

import json
import re
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional, List, Dict
from dataclasses import dataclass, field


# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

logger_brain = logging.getLogger("brain_middleware")
logger_brain.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(
    "logs/brain_middleware.log",
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(funcName)-25s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(formatter)

if not logger_brain.handlers:
    logger_brain.addHandler(file_handler)


# ============================================================================
# ENUMERAÇÕES E TIPOS
# ============================================================================

class TipoIntencao(Enum):
    """Tipos de intenções que o Brain Middleware pode detectar."""
    
    CRIAR_NOTA = "criar_nota"
    CRIAR_TAREFA = "criar_tarefa"
    BUSCAR_INFO = "buscar_info"
    GERAR_IDEIAS = "gerar_ideias"
    CONSULTAR_METRICAS = "consultar_metricas"
    CRIAR_PLANO = "criar_plano"
    CONVERSAR = "conversar"
    DESCONHECIDA = "desconhecida"


class NivelConfianca(Enum):
    """Níveis de confiança para decisão de ação."""
    MUITO_ALTA = "muito_alta"      # 0.9+ → Executar direto
    ALTA = "alta"                  # 0.7-0.9 → Executar + confirmar
    MEDIA = "media"                # 0.5-0.7 → Perguntar clarificação
    BAIXA = "baixa"                # 0.3-0.5 → Perguntar intenção geral
    MUITO_BAIXA = "muito_baixa"    # <0.3 → Pedir reformulação


class PrioridadeTarefa(Enum):
    """Níveis de prioridade para tarefas."""
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"


class EstadoConversa:
    """Estados da conversação com o usuário."""
    AGUARDANDO_CLARIFICACAO = "aguardando_clarificacao"
    CONVERSANDO = "conversando"
    OCIOSO = "ocioso"
    AGUARDANDO_EDICAO = "aguardando_edicao"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class IntencaoDetectada:
    """
    Representa uma intenção detectada na mensagem do usuário.
    """
    tipo: TipoIntencao
    confianca: float
    entidades: dict[str, Any] = field(default_factory=dict)
    texto_original: str = ""
    requer_clarificacao: bool = False


@dataclass
class ContextoConversa:
    """
    Mantém estado da conversação com um usuário.
    """
    usuario_id: int
    mensagens_antigas: List[Dict] = field(default_factory=list)
    ultima_intencao: Optional[TipoIntencao] = None
    entidades_pendentes: Dict[str, Any] = field(default_factory=dict)
    aguardando_confirmacao: bool = False
    pergunta_pendente: Optional[str] = None
    tentativas_clarificacao: int = 0


@dataclass
class RespostaBrain:
    """
    Resposta completa do Brain Middleware.
    """
    sucesso: bool
    acao_executada: str
    resposta_ia: str
    detalhes: dict[str, Any] = field(default_factory=dict)
    sugestoes: list[str] = field(default_factory=list)
    erro: Optional[str] = None
    requer_clarificacao: bool = False
    pergunta_clarificacao: Optional[str] = None
    
    # Campo extra para compatibilidade
    entidades: Dict[str, Any] = field(default_factory=dict)
    confianca: float = 0.0
    # ✅✅ ADICIONAR ESTES DOIS CAMPOS AQUI ✅✅
    aguardando_resposta: bool = False          # ← ADICIONAR ESTA LINHA
    clarificacao_pendente: bool = False         # ← ADICIONAR ESTA LINHA


# ============================================================================
# CONSTANTES DE CONFIGURAÇÃO
# ============================================================================

# Nome do assistente (MUDADO DE LEX PARA MAGO!)
NOME_ASSISTENTE = "Mago"
NOME_ASSISTENTE_DISPLAY = "🧙 Mago"

# Palavras-chave que ativam o assistente
PALAVRAS_ATIVACAO = [
    "mago", "magão", "mage", 
    "ai", "assistente", "bot", "robô",
    "você", "vc", "voce"
]

# Padrões regex para extração de entidades
PADROES_ENTIDADES = {
    "prazo": r"(?:até|para|até\s+a|ate|ateh)\s+(?:a\s+)?(?:(?:esta|essa|proxima?)\s+)?(segunda|ter[çc]a|quarta|quinta|sexta|s[áa]bado|domingo|semana|m[êe]s|amanh[ãa]|hoje|\d{1,2}/\d{1,2}|\d{1,2}\s*de?\s*\w+)",
    "prioridade": r"(?:prioridade\s*:?\s*(alta|baixa|m[ée]dia|urgente)|urgente|importante|com\s*prioridade|priorit[áa]rio)",
    "projeto": r"(?:projeto|canal|para\s+o\s+|sobre\s+o\s+)(?:['\"]?)([\w\s&]+?)(?:['\"]?(?:\s|$|\.|,|\?))",
    "quantidade": r"(\d+)\s*(?:ideias?|itens?|op[çcõo]es?|tarefas?)",
}


# ============================================================================
# FUNÇÕES AUXILIARES DE TIPO
# ============================================================================

def converter_prazo(prazo_str: str) -> str:
    """Converte string de prazo para formato padronizado."""
    hoje = datetime.now()
    prazo_str = prazo_str.lower().strip()
    
    mapeamento_dias = {
        "hoje": hoje,
        "amanhã": hoje + timedelta(days=1),
        "amanha": hoje + timedelta(days=1),
        "segunda": _proximo_dia_semana(hoje, 0),
        "terça": _proximo_dia_semana(hoje, 1),
        "terca": _proximo_dia_semana(hoje, 1),
        "quarta": _proximo_dia_semana(hoje, 2),
        "quinta": _proximo_dia_semana(hoje, 3),
        "sexta": _proximo_dia_semana(hoje, 4),
        "sábado": _proximo_dia_semana(hoje, 5),
        "sabado": _proximo_dia_semana(hoje, 5),
        "domingo": _proximo_dia_semana(hoje, 6),
    }
    
    if prazo_str in mapeamento_dias:
        data = mapeamento_dias[prazo_str]
        return data.strftime("%Y-%m-%d")
    
    if prazo_str in ["semana"]:
        return (hoje + timedelta(days=7)).strftime("%Y-%m-%d")
    
    if prazo_str in ["mes", "mês"]:
        return (hoje + timedelta(days=30)).strftime("%Y-%m-%d")
    
    return prazo_str


def _proximo_dia_semana(data_base: datetime, dia_semana: int) -> datetime:
    """Calcula a próxima ocorrência de um dia da semana."""
    dias_ate = (dia_semana - data_base.weekday()) % 7
    if dias_ate == 0:
        dias_ate = 7
    return data_base + timedelta(days=dias_ate)


def normalizar_prioridade(prio_str: str) -> str:
    """Normaliza string de prioridade para formato da API."""
    prio_lower = prio_str.lower()
    
    if prio_lower in ["urgente"]:
        return "urgent"
    elif prio_lower in ["alta", "importante"]:
        return "high"
    elif prio_lower in ["media", "média", "medio"]:
        return "medium"
    else:
        return "low"


def classificar_nivel_confianca(confianca: float) -> NivelConfianca:
    """Classifica nível de confiança para tomada de decisão."""
    if confianca >= 0.90:
        return NivelConfianca.MUITO_ALTA
    elif confianca >= 0.70:
        return NivelConfianca.ALTA
    elif confianca >= 0.50:
        return NivelConfianca.MEDIA
    elif confianca >= 0.30:
        return NivelConfianca.BAIXA
    else:
        return NivelConfianca.MUITO_BAIXA