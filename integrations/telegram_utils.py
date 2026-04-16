"""
================================================================================
LEX BRAIN TELEGRAM BOT - Utilitários e Constantes v2.1
================================================================================

Módulo auxiliar contendo:
- Constantes e configurações compartilhadas
- Funções de formatação de texto/data
- Utilitários de logging
- Mapeamentos de prioridades, emojis, etc.

AUTOR: Lex-Usamn | DATA: 12/04/2026
STATUS: ✅ Produção
================================================================================
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum


# ============================================================================
# CONSTANTES DO SISTEMA
# ============================================================================

class Prioridade(Enum):
    """Enumeração de níveis de prioridade."""
    BAIXA = "low"
    MEDIA = "medium"
    ALTA = "high"
    URGENTE = "urgent"


class EmojiSystema:
    """Emojis usados no sistema para feedback visual."""
    SUCESSO = "✅"
    ERRO = "❌"
    ALERTA = "⚠️"
    PROCESSANDO = "⏳"
    CEREBRO = "🧠"
    ROBOT = "🤖"
    NOTA = "📝"
    TAREFA = "📋"
    PROJETO = "📂"
    RELOGIO = "🕐"
    FOGO = "🔥"
    ALVO = "🎯"
    BULLETPONT = "➜"
    POMODORO = "🍅"
    GRAFICO = "📊"
    SAUDE = "🏥"
    INTERROGACAO = "❓"
    PENSAMENTO = "🤔"
    BRAÇOS = "🙌"
    CORACAO = "💡"
    ZAP = "💬"


# Mapeamento de prioridades para emojis
MAPEAMENTO_PRIORIDADE_EMOJI = {
    'urgent': '🔴🔴🔴',
    'urgente': '🔴🔴🔴', 
    'high': '🟠',
    'alta': '🟠',
    'medium': '🟡',
    'media': '🟡',
    'média': '🟡',
    'low': '🟢',
    'baixa': '🟢'
}

# Mapeamento de prioridade em português para inglês (API)
MAPEAMENTO_PRIORIDADE_API = {
    'alta': 'high',
    'media': 'medium', 
    'média': 'medium',
    'baixa': 'low',
    'urgente': 'urgent',
    'high': 'high',
    'medium': 'medium', 
    'low': 'low',
    'urgent': 'urgent'
}

# Dias da semana em português
DIAS_SEMANA = [
    'Segunda-feira', 'Terça-feira', 'Quarta-feira',
    'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'
]


# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

def configurar_logger_telegram() -> logging.Logger:
    """
    Configura e retorna logger dedicado ao Telegram Bot.
    
    Implementa padrão singleton para evitar duplicação de handlers
    em múltiplas chamadas.
    
    Returns:
        Logger configurado com handlers de arquivo e console
    """
    # Criar diretório de logs se não existir
    os.makedirs('logs', exist_ok=True)
    
    # Logger específico do Telegram Bot
    logger = logging.getLogger('TelegramBot')
    
    # Só configurar se ainda não foi configurado (evita duplicação)
    if not logger.handlers:
        # Handler para arquivo (persistente)
        handler_arquivo = logging.FileHandler(
            'logs/telegram_bot.log',
            encoding='utf-8',
            mode='a'
        )
        
        # Handler para console (tempo real)
        handler_console = logging.StreamHandler()
        
        # Formatador unificado
        formatador = logging.Formatter(
            fmt='%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        handler_arquivo.setFormatter(formatador)
        handler_console.setFormatter(formatador)
        
        logger.addHandler(handler_arquivo)
        logger.addHandler(handler_console)
        logger.setLevel(logging.INFO)
    
    return logger


# Instância global do logger (importada por outros módulos)
logger_telegram = configurar_logger_telegram()


# ============================================================================
# FUNÇÕES DE FORMATAÇÃO
# ============================================================================

def formatar_tempo(segundos: float) -> str:
    """
    Formata segundos para string legível.
    
    Args:
        segundos: Tempo em segundos
        
    Returns:
        String formatada (ex: "2h 30m 15s", "45s")
    """
    if segundos <= 0:
        return "0s"
    
    if segundos < 60:
        return f"{int(segundos)}s"
    
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs_restantes = int(segundos % 60)
    
    partes = []
    if horas > 0:
        partes.append(f"{horas}h")
    if minutos > 0:
        partes.append(f"{minutos}m")
    if segs_restantes > 0 and not horas:
        partes.append(f"{segs_restantes}s")
    
    return ' '.join(partes) if partes else "0s"


def formatar_data_extensa() -> str:
    """
    Retorna data atual formatada de forma extensa.
    
    Returns:
        String como "Segunda-feira, 15/04/2026"
    """
    hoje = datetime.now()
    nome_dia = DIAS_SEMANA[hoje.weekday()]
    data_formatada = hoje.strftime('%d/%m/%Y')
    return f"{nome_dia}, {data_formatada}"


def truncar_texto(texto: str, max_length: int = 80, sufixo: str = "...") -> str:
    """
    Trunca texto se exceder tamanho máximo.
    
    Args:
        texto: Texto original
        max_length: Tamanho máximo permitido
        sufixo: Sufixo a adicionar quando truncado
        
    Returns:
        Texto truncado ou original
    """
    if len(texto) <= max_length:
        return texto
    return texto[:max_length - len(sufixo)] + sufixo


def obter_emoji_prioridade(prioridade: str) -> str:
    """
    Retorna emoji correspondente à prioridade.
    
    Args:
        prioridade: String de prioridade ('high', 'media', etc.)
        
    Returns:
        Emoji correspondente ou ⚪ se desconhecida
    """
    return MAPEAMENTO_PRIORIDADE_EMOJI.get(prioridade.lower(), '⚪')


def normalizar_prioridade(prioridade_str: str) -> str:
    """
    Normaliza string de prioridade para formato da API.
    
    Args:
        prioridade_str: Prioridade em português ou inglês
        
    Returns:
        Prioridade normalizada (lowercase, inglês)
    """
    return MAPEAMENTO_PRIORIDADE_API.get(
        prioridade_str.lower().strip(), 
        'medium'  # Default seguro
    )


# ============================================================================
# FUNÇÕES DE RESPOSTA PADRONIZADAS
# ============================================================================

def mensagem_erro_generica(erro: Exception, operacao: str = "operação") -> tuple:
    """
    Gera mensagem de erro padronizada para o usuário.
    
    Args:
        erro: Exceção capturada
        operacao: Descrição da operação que falhou
        
    Returns:
        Tupla (mensagem_para_usuario, mensagem_para_log)
    """
    msg_usuario = (
        f"❌ *Erro inesperado na {operacao}*\n\n"
        f"Desculpe, ocorreu um erro inesperado. "
        f"Nossa equipe foi notificada automaticamente.\n\n"
        f"Por favor, tente novamente."
    )
    msg_log = f"❌ Exceção na {operacao}: {type(erro).__name__}: {erro}"
    
    return msg_usuario, msg_log


def mensagem_sucesso_nota(resultado: Dict[str, Any], texto_original: str) -> str:
    """
    Gera mensagem de sucesso para criação de nota.
    
    Args:
        resultado: Dicionário com resultado da API (deve conter 'id')
        texto_original: Texto original da nota
        
    Returns:
        Mensagem formatada para exibição
    """
    id_nota = resultado.get('id', 'desconhecido')
    titulo_exibicao = truncar_texto(texto_original, 50)
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    msg = (
        f"✅ *NOTA CAPTURADA COM SUCESSO!*\n\n"
        f"🆔 *ID:* `{id_nota}`\n"
        f"📝 *Texto:* {titulo_exibicao}\n\n"
        f"💾 Salva no *Lex Flow* ✓\n"
        f"🕐 Timestamp: {timestamp}"
    )
    
    # Adicionar tags se presentes
    if resultado.get('tags'):
        tags_fmt = ', '.join(resultado['tags'])
        msg += f"\n🏷️ *Tags:* {tags_fmt}"
    
    return msg


def mensagem_sucesso_tarefa(
    task_id: Any,
    titulo: str,
    prioridade: str,
    projeto_id: int
) -> str:
    """
    Gera mensagem de sucesso para criação de tarefa.
    
    Args:
        task_id: ID da tarefa criada
        titulo: Título da tarefa
        prioridade: Nível de prioridade
        projeto_id: ID do projeto
        
    Returns:
        Mensagem formatada para exibição
    """
    emoji = obter_emoji_prioridade(prioridade)
    
    return (
        f"✅ *TAREFA CRIADA COM SUCESSO!*\n\n"
        f"🆔 ID: {task_id}\n"
        f"📋 Título: {titulo}\n"
        f"{emoji} Prioridade: {prioridade.upper()}\n"
        f"📂 Projeto ID: {projeto_id}"
    )


# ============================================================================
# CONSTANTES DE MENSAGENS PRÉ-DEFINIDAS
# ============================================================================

MENSAGEM_BOAS_VINDAS = """
🧠 *LEX BRAIN HYBRID* v2.1
━━━━━━━━━━━━━━━━━━━━━

Olá, *{nome}*! 👋

Seu *Assistente Pessoal Inteligente* está online!

*Status do Sistema:* {status}

*🎯 Comandos Principais:*
➜ `/hoje` – Ver prioridades do dia
➜ `/nota <texto>` – Capturar ideia rapidamente
➜ `/tarefa <texto>` – Criar tarefa
➜ `/projetos` – Listar projetos ativos
➜ `/metricas` – Ver métricas de produtividade
➜ `/pomodoro` – Controlar sessões de foco
➜ `/status` – Health check do sistema
➜ `/ajuda` – Ver todos os comandos

💡 *Modo Conversacional ATIVO!*
Envie mensagens naturais como:
• "Lex, anota isso..."
• "Lex, lembra que tenho que..."
• "Lex, o que eu escrevi sobre...?"

_Lex Brain Hybrid by Lex-Usamn_
"""

MENSAGEM_AJUDA = """
📚 *AJUDA - COMANDOS DISPONÍVEIS*
━━━━━━━━━━━━━━━━━━━━━

*🎯 COMANDOS PRINCIPAIS:*

/start – Iniciar bot e ver status
/hoje – Ver prioridades do dia 📋
/nota `<texto>` – Capturar ideia/nota 📝
/tarefa `<texto>` – Criar tarefa 📋
/projetos – Listar projetos ativos 📂
/metricas – Painel de métricas 📊
/pomodoro – Controle Pomodoro 🍅
/status – Health check completo 🏥
/ajuda – Esta mensagem ℹ️

━━━━━━━━━━━━━━━━━━━━━

*🧬 MODO CONVERSACIONAL (NOVIDADE!):*

Eu entendo **português natural**! Experimente:
• "Lex, lembra de cortar o vídeo até quinta"
• "Lex, anota: comprar microfone novo"
• "Lex, quais minhas tarefas pra hoje?"
• "Lex, me dá 5 ideias sobre Bitcoin"

Se eu tiver dúvida, **eu pergunto** antes de agir! 🤔

━━━━━━━━━━━━━━━━━━━━━

*📖 EXEMPLOS AVANÇADOS:*

`/tarefa Editar vídeo --projeto Canais Dark --prioridade alta`
`/nota Ideia incrível --tags youtube criativo`
`/pomodoro iniciar`

━━━━━━━━━━━━━━━━━━━━━
🧠 *Lex Brain Hybrid v2.1* | *IA Assistente Pessoal*
"""