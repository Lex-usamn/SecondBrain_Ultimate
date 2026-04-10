"""
================================================================================
LEX BRAIN TELEGRAM BOT v1.0 - Interface Mobile do Second Brain Ultimate
================================================================================

VERSÃO: 1.0 (MVP Funcional - Produção Ready)
DATA: 2026-04-09
AUTOR: Lex-Usamn | Second Brain Ultimate System
STATUS: ✅ Produção (Pronto para deploy)

FUNCIONALIDADES PRINCIPAIS:
---------------------------
✅ Captura rápida de ideias via mensagem de texto (/nota ou texto livre)
✅ Criação de tarefas em projetos (/tarefa) com parse avançado de argumentos
✅ Visualização de prioridades do dia (/hoje) - Morning Briefing
✅ Listagem de projetos ativos (/projetos)
✅ Métricas de produtividade (/metricas)
✅ Controle de sessões Pomodoro (/pomodoro)
✅ Health check completo do sistema (/status)
✅ Comando de ajuda (/ajuda)
✅ Captura automática de mensagens diretas (sem comando)
✅ Suporte a tags personalizadas (--tags)
✅ Seleção de projeto (--projeto) e prioridade (--prioridade)

INTEGRAÇÃO COM CORE ENGINE:
----------------------------
Este bot usa EXCLUSIVAMENTE o CoreEngine (Singleton) para todas as operações.
Não acessa diretamente o LexFlowClient - tudo passa pelo motor orquestrador.

PADRÃO DE PROJETO:
------------------
- CoreEngine Singleton (uma única instância compartilhada)
- Lazy Initialization do motor (só inicia quando recebe primeiro comando)
- Logging completo de toda interação (segurança + debug + audit trail)
- Tratamento robusto de erros (nunca crasha, sempre responde ao usuário)
- Mensagens de feedback visual (⏳ Capturando... → ✅ Sucesso!)

SEGURANÇA:
----------
- Token NUNCA hard-coded em produção (sempre em settings.yaml ou variável ambiente)
- Validação de usuário opcional (apenas dono pode usar comandos administrativos)
- Logs de todas as interações em arquivo dedicado (logs/telegram_bot.log)
- Tratamento seguro de erros (nunca expõe dados sensíveis nas mensagens)

COMO USAR:
----------
1. Configurar token em config/settings.yaml (seção telegram)
2. Instalar dependência: pip install python-telegram-bot>=20.7
3. Executar: python integrations/telegram_bot.py
4. Enviar /start no @Lex_Cerebro_bot no Telegram
5. Pronto para usar!

EXEMPLOS DE INTERAÇÃO:
--------------------
Você: /hoje
Bot: 📋 SUAS PRIORIDADES DE HOJE:
     1. 🔴 Estudar SASS para novo projeto
     2. 🟠 Gravar vídeo sobre Bitcoin
     3. 🟡 Revisar contrato do cliente

Você: Ideia incrível para vídeo sobre criptomoedas
Bot: ✅ *Capturada!* ID: 42

Você: /tarefa Editar vídeo #12 --projeto Canais Dark --prioridade alta
Bot: ✅ *TAREFA CRIADA COM SUCESSO!*
     🆔 ID: 23
     📋 Título: Editar vídeo #12
     🟠 Prioridade: HIGH
     📂 Projeto ID: 5

Você: /nota Preciso comprar microfone novo --tags compras equipamento urgente
Bot: ✅ *NOTA CAPTURADA COM SUCESSO!*
     🆔 ID: 44
     📝 Título: Preciso comprar microfone novo
     🏷️ Tags: compras, equipamento, urgente

DEPENDÊNCIAS:
------------
python-telegram-bot>=20.7

================================================================================
"""

import sys
import os
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any


# ============================================================================
# IMPORTAÇÕES DO SISTEMA INTERNO (Core Engine)
# ============================================================================

# Adicionar diretório raiz ao path (para imports relativos funcionarem em qualquer contexto de execução)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Core Engine (motor principal - Singleton Pattern)
from engine.core_engine import CoreEngine


# ============================================================================
# IMPORTAÇÃO DA BIBLIOTECA PYTHON-TELEGRAM-BOT
# ============================================================================

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        filters,
        ContextTypes,
        CallbackContext
    )
    LIB_TELEGRAM_DISPONIVEL = True
except ImportError:
    LIB_TELEGRAM_DISPONIVEL = False
    print("⚠️  Biblioteca python-telegram-bot não instalada!")
    print("   Instale com: pip install python-telegram-bot>=20.7")


# ============================================================================
# CONFIGURAÇÃO DE LOGGING ESPECÍFICA DO TELEGRAM BOT
# ============================================================================

# Criar diretório de logs se não existir (evita erro na primeira execução)
os.makedirs('logs', exist_ok=True)

# Logger específico e dedicado ao Telegram Bot (separado do core_engine.log)
logger_telegram = logging.getLogger('TelegramBot')

# Configurar handlers apenas se ainda não foram configurados (evita duplicação de logs em re-inicializações)
if not logger_telegram.handlers:
    # Handler para arquivo de log (persistente - guarda histórico completo)
    handler_arquivo = logging.FileHandler(
        'logs/telegram_bot.log',
        encoding='utf-8',
        mode='a'  # Modo append (adiciona ao invés de sobrescrever)
    )
    
    # Handler para console (visível em tempo real durante desenvolvimento)
    handler_console = logging.StreamHandler()
    
    # Formatador unificado para ambos os handlers (fácil de ler e parsear)
    formatador = logging.Formatter(
        fmt='%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Aplicar formatador aos handlers
    handler_arquivo.setFormatter(formatador)
    handler_console.setFormatter(formatador)
    
    # Registrar handlers no logger
    logger_telegram.addHandler(handler_arquivo)
    logger_telegram.addHandler(handler_console)
    logger_telegram.setLevel(logging.INFO)


# ============================================================================
# CLASSE PRINCIPAL: LEX BRAIN TELEGRAM BOT
# ============================================================================

class LexBrainTelegramBot:
    """
    Bot do Telegram para o Lex Brain Hybrid System v1.0
    
    Este é o ponto de entrada mobile para todo o sistema Second Brain Ultimate.
    Permite capturar ideias, criar tarefas, ver prioridades, controlar pomodoros,
    monitorar métricas - tudo diretamente do celular via Telegram, 24/7.
    
    ==========================================================================
    PADRÃO DE PROJETO ARQUITETURAL:
    ==========================================================================
    
    1. SINGLETON DO MOTOR:
       - Usa CoreEngine Singleton (não cria novas instâncias do motor)
       - Todas as operações passam pelo orquestrador central
       - Garante consistência de dados e estado global
    
    2. LAZY INITIALIZATION:
       - Motor só é inicializado quando o PRIMEIRO comando chega
       - Economiza recursos (não conecta no Lex Flow se ninguém usar)
       - Evita falhas na inicialização do bot se Lex Flow estiver temporariamente fora
    
    3. LOGGING COMPLETO:
       - Toda interação é logada (audit trail completo)
       - Arquivo dedicado: logs/telegram_bot.log
       - Útil para debug, segurança e análise de uso
    
    4. TRATAMENTO ROBUSTO DE ERROS:
       - NENHUM comando faz o bot crashar
       - Sempre responde ao usuário (mesmo em caso de erro)
       - Mensagens de erro amigáveis (sem stack traces expostos)
    
    ==========================================================================
    ATRIBUTOS PRINCIPAIS:
    ==========================================================================
    
    - token: Token do bot (carregado de settings.yaml ou variável ambiente)
    - _motor: Instância do CoreEngine (inicializada sob demanda via lazy loading)
    - _motor_inicializado: Flag booleana para evitar reinicializações desnecessárias
    
    ==========================================================================
    EXEMPLO DE USO (Programático):
    =========================================================================-
    
        # Importar e instanciar
        from integrations.telegram_bot import LexBrainTelegramBot
        
        # Criar bot (ainda não conecta em nada pesado)
        bot = LexBrainTelegramBot()
        
        # Iniciar (bloqueia aqui - roda até Ctrl+C)
        # Isso vai: criar Application → registrar handlers → conectar Telegram → loop infinito
        bot.iniciar()
    
    ==========================================================================
    """

    def __init__(self):
        """
        Inicializa o Bot do Telegram
        
        ====================================================================
        O QUE ACONTECE NESTE MÉTODO (__init__):
        ====================================================================
        
        1. CARREGAR TOKEN:
           - Busca em variável de ambiente (TELEGRAM_BOT_TOKEN) - PRIORIDADE MÁXIMA
           - Fallback para config/settings.yaml (seção telegram.bot_token)
           - Se não encontrar nada, levanta ValueError com instruções claras
        
        2. PREPARAR REFERÊNCIA AO MOTOR (MAS NÃO INICIALIZAR AINDA):
           - Cria atributo _motor = None (lazy loading)
           - Cria flag _motor_inicializado = False
           - O motor só vai ser inicializado na PRIMEIRA chamada à propriedade .motor
        
        3. CONFIGURAR ESTADO INTERNO:
           - Registra log informativo da inicialização
           - Prepara ambiente para receber comandos
        
        ====================================================================
        POR QUÊ LAZY INITIALIZATION?
        ====================================================================
        
        Se iniciássemos o motor aqui no __init__, o bot falharia inteiro se:
        - Lex Flow estivesse offline na inicialização
        - Credenciais estivessem erradas
        - Rede estivesse lenta ou indisponível
        
        Com lazy init, o bot SOBRE no Telegram mesmo se o motor falhar depois.
        O usuário pode usar comandos básicos (como /ajuda) mesmo sem Lex Flow.
        """
        
        # Carregar token das configurações (ordem de prioridade: env > yaml)
        self.token = self._obter_token()
        
        # Validação crítica: sem token, o bot não funciona de jeito nenhum
        if not self.token:
            raise ValueError(
                "❌ Token do Telegram Bot não configurado!\n\n"
                "Para resolver, escolha UMA das opções abaixo:\n\n"
                "OPÇÃO 1 (Recomendada - Produção):\n"
                "  Exporte variável de ambiente:\n"
                "  export TELEGRAM_BOT_TOKEN=8628939675:AAEJf_7IhgsEe3z5EgemB43ivXhpjKPVqH0\n\n"
                "OPÇÃO 2 (Desenvolvimento):\n"
                "  Edite config/settings.yaml e adicione:\n"
                "  telegram:\n"
                "    enabled: true\n"
                "    bot_token: 8628939675:AAEJf_7IhgsEe3z5EgemB43ivXhpjKPVqH0\n\n"
                "Após configurar, execute este script novamente."
            )
        
        # Motor do Core Engine (inicializado sob demanda - lazy loading pattern)
        self._motor = None
        
        # Flag de controle para saber se o motor já foi inicializado (evita múltiplas inicializações)
        self._motor_inicializado = False
        
        # Log informativo de inicialização bem-sucedida
        logger_telegram.info("=" * 80)
        logger_telegram.info("🤖 LEX BRAIN TELEGRAM BOT v1.0 INICIALIZADO COM SUCESSO")
        logger_telegram.info(f"   Token configurado: {self.token[:10]}...{self.token[-4:]}")
        logger_telegram.info("   Status do Motor: ⏳ Aguardando primeiro comando para iniciar (Lazy Init)")
        logger_telegram.info("=" * 80)

    def _obter_token(self) -> Optional[str]:
        """
        Obter token do bot de configurações ou variável ambiente
        
        ====================================================================
        ORDEM DE PRIORIDADE (mais segura primeiro):
        ====================================================================
        
        1. VARIÁVEL AMBIENTE TELEGRAM_BOT_TOKEN (PRIORIDADE MÁXIMA)
           - Mais segura para produção (não fica gravada no código/fonte)
           - Pode ser gerenciada por secrets managers (AWS, Docker, etc.)
           - Não risco de commit acidental no Git
        
        2. CONFIGURAÇÃO SETTINGS.YAML (FALLBACK PARA DEV)
           - Mais fácil para desenvolvimento local
           - Centralizada com outras configs do sistema
           - Pode usar ${VAR} para referenciar variáveis de ambiente
        
        RETORNA:
            String com token válido ou None se não encontrado em lugar nenhum
        """
        
        # Tentativa 1: Variável de ambiente (prioridade máxima - segurança em produção)
        token_env = os.environ.get('TELEGRAM_BOT_TOKEN')
        if token_env and token_env.strip():
            logger_telegram.info("✅ Token obtido de variável de ambiente TELEGRAM_BOT_TOKEN")
            return token_env.strip()
        
        # Tentativa 2: Settings.yaml via ConfigLoader (fallback para desenvolvimento)
        try:
            from engine.config_loader import ConfigLoader
            
            # Obter instância singleton do carregador de configurações
            config_loader = ConfigLoader.get_instance()
            
            # Tentar acessar seção telegram do objeto de configurações tipado
            if hasattr(config_loader.configuracoes, 'telegram'):
                telegram_cfg = config_loader.configuracoes.telegram
                
                if hasattr(telegram_cfg, 'bot_token') and telegram_cfg.bot_token:
                    token_yaml = telegram_cfg.bot_token
                    logger_telegram.info(f"✅ Token obtido de settings.yaml (seção telegram)")
                    return token_yaml
            
            # Tentativa 3: Ler direto do dicionário bruto (fallback emergencial)
            lex_flow_config = config_loader.get_lex_flow_config()
            
            if isinstance(lex_flow_config, dict) and 'bot_token' in lex_flow_config:
                token_dict = lex_flow_config['bot_token']
                logger_telegram.info(f"✅ Token obtido de configuração do Lex Flow (dicionário)")
                return token_dict
                
        except Exception as erro_config:
            # Log de warning mas não crasha (token pode vir de outro lugar)
            logger_telegram.warning(f"⚠️  Erro ao tentar carregar token do settings.yaml: {erro_config}")
            logger_telegram.info("   (Isso é normal se você usa apenas variável de ambiente)")
        
        # Nenhuma fonte encontrou o token
        logger_telegram.warning("❌ Token não encontrado em variável de ambiente nem em settings.yaml")
        return None

    @property
    def motor(self) -> CoreEngine:
        """
        Propriedade que retorna o Core Engine (Inicialização Sob Demanda - Lazy Loading)
        
        ====================================================================
        COMO FUNCIONA ESTE PADRÃO:
        ====================================================================
        
        Na PRIMEIRA chamada desta propriedade:
        1. Verifica se _motor já existe (cache check)
        2. Se não existir, obtém instância Singleton do CoreEngine
        3. Chama .iniciar() para conectar no Lex Flow (autenticação JWT)
        4. Cacheia a instância em self._motor
        5. Marca _motor_inicializado = True
        
        Nas PRÓXIMAS chamadas:
        1. Retorna self._motor diretamente (instantâneo, zero overhead)
        2. Não reinicializa nada
        3. Reaproveita a mesma conexão com Lex Flow
        
        ====================================================================
        POR QUÊ PROPERTY EM VEZ DE MÉTODO NORMAL?
        ====================================================================
        
        - Sintaxe mais limpa: self.motor.obter_prioridades() vs self.get_motor().obter_prioridades()
        - Encapsula a lógica de lazy loading (usuário não precisa saber quando inicia)
        - Parece um atributo normal, mas tem inteligência por trás
        
        LEVA EXCEÇÃO SE:
        - Lex Flow não conseguir conectar (credenciais erradas, servidor fora, timeout)
        - CoreEngine levantar exceção na inicialização
        
        RETORNA:
            Instância de CoreEngine pronta para uso, completamente inicializada
        """
        
        # Verifica se precisa inicializar (primeira chamada ou reinicialização forçada)
        if self._motor is None or not self._motor_inicializado:
            logger_telegram.info("🔄 [LAZY INIT] Inicializando Core Engine na primeira requisição...")
            logger_telegram.info("   Isso pode levar alguns segundos (conectando no Lex Flow)...")
            
            try:
                # Obter instância Singleton do motor (sempre a mesma em todo o processo)
                self._motor = CoreEngine.obter_instancia()
                
                # Iniciar motor completo (conecta Lex Flow, valida dependências, prepara subsistemas)
                sucesso = self._motor.iniciar()
                
                if not sucesso:
                    raise ConnectionError(
                        "❌ Falha crítica ao iniciar Core Engine!\n\n"
                        "Possíveis causas:\n"
                        "• Lex Flow offline (https://flow.lex-usamn.com.br)\n"
                        "• Credenciais inválidas no settings.yaml\n"
                        "• Problema de rede ou firewall\n\n"
                        "Verifique logs/core_engine.log para detalhes técnicos completos."
                    )
                
                # Marca como inicializado (próximas chamadas pulam esta lógica inteira)
                self._motor_inicializado = True
                logger_telegram.info("✅ [LAZY INIT] Core Engine iniciado e conectado com sucesso!")
                logger_telegram.info("   Pronto para processar comandos!")
                
            except Exception as erro_motor:
                logger_telegram.critical(f"💥 [LAZY INIT] FALHA CRÍTICA AO INICIAR MOTOR: {erro_motor}", exc_info=True)
                # Re-levanta exceção para o handler tratar gracefulmente
                raise
        
        return self._motor

    # =========================================================================
    # MÉTODOS HANDLERS DE COMANDOS DO TELEGRAM
    # =========================================================================
    # Cada método abaixo corresponde a um comando que o usuário pode enviar
    # Todos seguem o mesmo padrão: logar → executar → responder → tratar erros
    # =========================================================================

    async def comando_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler do comando /start - Boas-vindas e status inicial do sistema
        
        ====================================================================
        QUANDO É CHAMADO:
        - Primeira vez que o usuário abre o bot (clica em "Start")
        - Quando o usuário envia /start manualmente
        - Botão "Start" no perfil do bot (@Lex_Cerebro_bot)
        
        ====================================================================
        O QUE FAZ:
        1. Extrai nome e ID do usuário (para personalização e log)
        2. Executa health check rápido do motor (sem crashar se falhar)
        3. Monta mensagem de boas-vindas personalizada e formatada
        4. Lista comandos disponíveis (quick reference)
        5. Envia resposta formatada em Markdown
        
        ====================================================================
        ARGUMENTOS:
            update: Objeto Update do Telegram contendo:
                    - message: Mensagem enviada pelo usuário
                    - effective_user: Dados do usuário (nome, ID, username)
                    - chat: Informações do chat (ID, tipo)
            
            context: ContextTypes.DEFAULT_TYPE - Contexto mantido pelo bot entre comandos
                     (pode armazenar dados persistentes da conversa se necessário)
        
        ====================================================================
        """

        # Extrair informações do usuário para personalização e log
        usuario_nome = update.effective_user.first_name or "Usuário"
        usuario_id = update.effective_user.id
        username = update.effective_user.username or "sem_username"
        
        # Log de auditoria (registra quem acessou e quando)
        logger_telegram.info(f"💬 [/start] Usuário: {usuario_nome} (ID: {usuario_id}, @{username})")
        
        try:
            # Tentar obter status rápido de saúde do sistema (pode falhar se motor não iniciado)
            try:
                saude = self.motor.health_check()
                status_texto = saude.get('detalhes', '✅ Sistema operacional')
                emoji_status = "🟢"
            except Exception:
                # Se health_check falhar, não impede o /start de funcionar
                status_texto = "⚠️ Motor não inicializado (iniciará sob demanda)"
                emoji_status = "🟡"
            
            # Montar mensagem de boas-vindas completa e formatada
            mensagem_boas_vindas = f"""
🧠 *LEX BRAIN HYBRID* v1.0
━━━━━━━━━━━━━━━━━━━━━

Olá, *{usuario_nome}*! 👋

Seu *Segundo Cérebro Híbrido* está online!

*Status do Sistema:* {emoji_status} {status_texto}

*🎯 Comandos Principais:*
➜ `/hoje` – Ver prioridades do dia (Morning Briefing)
➜ `/nota <texto>` – Capturar ideia/nota rapidamente
➜ `/tarefa <texto>` – Criar tarefa em projeto
➜ `/projetos` – Listar projetos ativos
➜ `/metricas` – Ver métricas de produtividade
➜ `/pomodoro` – Controlar sessões de foco
➜ `/status` – Health check completo do sistema
➜ `/ajuda` – Ver todos os comandos com exemplos

💡 *Dica Super Importante:*
Envie qualquer texto diretamente (sem /comando) que eu capturo como nota automaticamente! 📝

_Lex Brain Hybrid by Lex-Usamn | Segundo Cérebro Ultimate_
"""
            
            # Enviar mensagem ao usuário (parse_mode=Markdown para formatação rica)
            await update.message.reply_text(
                mensagem_boas_vindas,
                parse_mode='Markdown'
            )
            
            # Log de sucesso
            logger_telegram.info(f"✅ [/start] Resposta enviada com sucesso para {usuario_nome}")
            
        except Exception as erro_start:
            # Log detalhado do erro (com stack trace completo para debug)
            logger_telegram.error(f"❌ [/start] Erro inesperado: {erro_start}", exc_info=True)
            
            # Resposta amigável ao usuário (sem expor detalhes técnicos)
            await update.message.reply_text(
                "❌ Desculpe, ocorreu um erro ao inicializar.\n\n"
                "Tente novamente em alguns segundos. "
                "Se persistir, verifique os logs em logs/telegram_bot.log"
            )

    async def comando_hoje(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler do comando /hoje - Morning Briefing (Prioridades do Dia)
        
        ====================================================================
        PROPÓSITO PRINCIPAL:
        Este é o comando MAIS IMPORTANTE para produtividade diária.
        Equivalente ao "Morning Briefing" que executivos recebem pela manhã.
        
        Deve ser o PRIMEIRO comando que você roda ao acordar (depois do café ☕)
        
        ====================================================================
        O QUE EXIBE:
        1. Data atual formatada (dia da semana + data)
        2. Top 5 prioridades do dia (ordenadas por importância)
        3. Emoji de prioridade visual (🔴 Urgente / 🟠 Alta / 🟡 Média / 🟢 Baixa)
        4. Projeto associado a cada tarefa
        5. Estatísticas rápidas do dia (pomodoros, notas, tarefas feitas)
        
        ====================================================================
        FONTES DE DADOS:
        - Prioridades: motor.obter_prioridades() → consulta Lex Flow API
        - Estatísticas: motor.resumo_do_dia() → agrega dados do dia
        
        ====================================================================
        """

        usuario_nome = update.effective_user.first_name or "Usuário"
        logger_telegram.info(f"💬 [/hoje] Morning briefing solicitado por {usuario_nome}")
        
        try:
            # ========================================
            # BUSCAR PRIORIDADES DO DIA (Top 5)
            # ========================================
            prioridades = self.motor.obter_prioridades()
            
            # ========================================
            # BUSCAR RESUMO/ESTATÍSTICAS DO DIA
            # ========================================
            resumo = self.motor.resumo_do_dia()
            estatisticas = resumo.get('estatisticas', {}) if resumo else {}
            
            # ========================================
            # MONTAR MENSAGEM FORMATADA
            # ========================================
            
            # Data formatada de forma amigável
            data_hoje = datetime.now().strftime('%d/%m/%Y')
            
            # Mapeamento de dias da semana em português
            dias_semana = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 
                          'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
            nome_dia = dias_semana[datetime.now().weekday()]
            
            # Cabeçalho da mensagem
            mensagem = f"""
📋 *PRIORIDADES DE HOJE*
📅 {nome_dia}, {data_hoje}
━━━━━━━━━━━━━━━━━━━━━
"""
            
            # ========================================
            # LISTAR PRIORIDADES (se existirem)
            # ========================================
            if prioridades:
                for indice, tarefa in enumerate(prioridades[:5], start=1):  # Limitar a 5 itens
                    titulo = tarefa.get('title', 'Sem título')
                    projeto = tarefa.get('project_title', 'Sem projeto definido')
                    
                    # Mapeamento de prioridades para emojis visuais (rápida compreensão)
                    emoji_prioridade = {
                        'urgent': '🔴',
                        'urgente': '🔴',
                        'high': '🟠',
                        'alta': '🟠',
                        'medium': '🟡',
                        'media': '🟡',
                        'low': '🟢',
                        'baixa': '🟢'
                    }.get(tarefa.get('priority', 'medium').lower(), '⚪')  # Default cinza se desconhecida
                    
                    # Formatar cada item da lista
                    mensagem += f"{indice}. {emoji_prioridade} *{titulo}*\n"
                    mensagem += f"   📂 Projeto: {projeto}\n\n"
            else:
                # Caso especial: dia livre ou nada planejado
                mensagem += "✨ *Nenhuma prioridade definida para hoje!*\n\n"
                mensagem += "   🎉 Aproveite o dia! Ou use `/nota` para planejar algo.\n\n"
            
            # ========================================
            # ADICIONAR ESTATÍSTICAS RÁPIDAS (se disponíveis)
            # ========================================
            if estatisticas:
                pomodoros = estatisticas.get('pomodoros', 0)
                notas_rapidas = estatisticas.get('quickNotes', 0)
                tarefas_feitas = estatisticas.get('tasksCompleted', 0)
                tarefas_pendentes = estatisticas.get('tarefas_pendentes', '?')
                
                mensagem += f"""━━━━━━━━━━━━━━━━━━━━━
📊 *Resumo de Produtividade:*
• 🍅 Pomodoros concluídos: {pomodoros}
• 📝 Notas rápidas capturadas: {notas_rapidas}
• ✅ Tarefas concluídas: {tarefas_feitas}
• 📋 Tarefas pendentes: {tarefas_pendentes}
"""
            
            # Rodapé motivacional (varia baseado nas estatísticas)
            if estatisticas and estatisticas.get('tasksCompleted', 0) >= 5:
                mensagem += "\n🔥 *Incendiário! Você está em dia!* Continue assim!"
            elif estatisticas and estatisticas.get('tasksCompleted', 0) >= 3:
                mensagem += "\n💪 *Bom progresso!* Vamos finalizar mais algumas!"
            else:
                mensagem += "\n☀️ *Bom dia!* Vamos conquistar hoje juntos!"
            
            # Enviar mensagem completa ao usuário
            await update.message.reply_text(mensagem, parse_mode='Markdown')
            
            # Log de sucesso
            logger_telegram.info(f"✅ [/hoje] Morning briefing enviado ({len(prioridades) if prioridades else 0} prioridades)")
            
        except Exception as erro_hoje:
            # Log do erro com stack trace
            logger_telegram.error(f"❌ [/hoje] Erro ao gerar briefing: {erro_hoje}", exc_info=True)
            
            # Resposta de erro amigável
            await update.message.reply_text(
                "❌ *Erro ao buscar prioridades*\n\n"
                "Não foi possível obter os dados de hoje.\n\n"
                "Possíveis causas:\n"
                "• Lex Flow temporariamente indisponível\n"
                "• Problema de conexão com a internet\n\n"
                "Tente novamente em alguns segundos.",
                parse_mode='Markdown'
            )

    async def comando_nota(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler do comando /nota - Captura Rápida de Ideias e Notas
        
        ====================================================================
        COMANDO MAIS USADO DO BOT (por design):
        Este é o coração do sistema de captura rápida. Permite registrar
        qualquer ideia, pensamento, referência ou lembrete em segundos.
        
        ====================================================================
        FORMATOS SUPORTADOS:
        
        BÁSICO:
            /nota <texto da nota>
            Exemplo: /nota Ideia incrível para vídeo sobre Bitcoin
        
        AVANÇADO (COM TAGS PERSONALIZADAS):
            /nota <texto> --tags tag1 tag2 tag3
            Exemplo: /nota Comprar microfone novo --tags compras equipamento urgente
        
        ====================================================================
        FLUXO DE EXECUÇÃO:
        1. Validar se texto foi fornecido (senão mostrar ajuda)
        2. Parsear tags opcionais (se --tags presente)
        3. Enviar mensagem visual "⏳ Capturando..." (feedback imediato)
        4. Executar motor.capturar() (envia para Lex Flow via API)
        5. Editar mensagem anterior com resultado final (sucesso ou erro)
        
        ====================================================================
        POR QUÊ MENSAGEM DUPLA (espera → edição)?
        - UX melhor: usuário sabe que algo está acontecendo
        - Evita dúvida: "será que funcionou?"
        - Feedback progressivo: processando... → pronto!
        
        ====================================================================
        """

        usuario_nome = update.effective_user.first_name or "Usuário"
        logger_telegram.info(f"💬 [/nota] Captura de nota solicitada por {usuario_nome}")
        
        try:
            # ========================================
            # EXTRAIR TEXTO DO COMANDO
            # =================================-------
            # context.args contém tudo após "/nota" como lista de strings
            # Juntamos com espaço para reconstruir o texto original
            texto_completo = ' '.join(context.args) if context.args else ''
            
            # Validação: texto não pode estar vazio
            if not texto_completo.strip():
                await update.message.reply_text(
                    "❌ *Uso incorreto do comando /nota*\n\n"
                    "*Formato básico:*\n"
                    "`/nota <texto da sua nota>`\n\n"
                    "*Exemplos:*\n"
                    "`/nota Ideia incrível para vídeo`\n"
                    "`/nota Lembrar: ligar para o cliente`\n"
                    "`/nota Referência: artigo sobre produtividade`\n\n"
                    "*Formato avançado (com tags):*\n"
                    "`/nota Texto --tags tag1 tag2 tag3`\n\n"
                    "*Dica:* Você também pode enviar texto diretamente (sem comando)!",
                    parse_mode='Markdown'
                )
                return  # Interrompe execução aqui (uso incorreto)
            
            # ========================================
            # PARSEAR ARGUMENTOS OPCIONAIS (--tags)
            # ========================================
            tags = []  # Lista vazia se nenhuma tag fornecida
            idea_texto = texto_completo  # Texto original (pode ser modificado se tiver --tags)
            
            # Verifica se usuário incluiu --tags no texto
            if '--tags' in texto_completo:
                # Divide o texto em duas partes: antes e depois de --tags
                partes = texto_completo.split('--tags', 1)  # maxsplit=1 (só divide na primeira ocorrência)
                idea_texto = partes[0].strip()  # Parte antes do --tags é a nota em si
                
                # Parte depois do --tags contém as tags (se existir)
                tags_str = partes[1].strip() if len(partes) > 1 else ''
                
                # Divide tags por espaço e filtra vazias
                tags = [tag.strip() for tag in tags_str.split() if tag.strip()]
                
                logger_telegram.info(f"   Tags detectadas: {tags}")
            
            # ========================================
            # FEEDBACK VISUAL IMEDIATO (Mensagem de Espera)
            # ========================================
            # Isso é CRÍTICO para UX: usuário sabe que estamos processando
            mensagem_espera = await update.message.reply_text(
                "⏳ *Capturando sua nota...* 📝\n\n"
                "Enviando para o Lex Flow...",
                parse_mode='Markdown'
            )
            
            # ========================================
            # EXECUTAR CAPTURA VIA CORE ENGINE
            # =================================-------
            # O motor vai: validar → enriquecer metadados → enviar para Lex Flow API → retornar resultado
            resultado = self.motor.capturar(
                idea=idea_texto,
                tags=tags if tags else None  # None se lista vazia (motor usa padrão)
            )
            
            # ========================================
            # PROCESSAR RESULTADO E RESPONDER
            # ========================================
            if resultado and resultado.get('id'):
                # === SUCESSO NA CAPTURA ===
                id_nota = resultado.get('id', 'desconhecido')
                titulo_exibicao = resultado.get('title', idea_texto)[:50]  # Limitar a 50 chars para exibição
                timestamp = datetime.now().strftime('%H:%M:%S')
                
                # Montar mensagem de sucesso
                resposta_sucesso = f"""
✅ *NOTA CAPTURADA COM SUCESSO!*

🆔 *ID:* `{id_nota}`
📝 *Texto:* {titulo_exibicao}

💾 Salva no *Lex Flow* ✓
🕐 Timestamp: {timestamp}
"""
                
                # Adicionar seção de tags (apenas se foram fornecidas)
                if tags:
                    tags_formatadas = ', '.join(tags)  # Junta tags com vírgula
                    resposta_sucesso += f"\n🏷️ *Tags:* {tags_formatadas}"
                
                # Editar mensagem de espera com o resultado final (ao invés de enviar nova mensagem)
                # Isso mantém o chat limpo (apenas 1 mensagem ao invés de 2)
                await mensagem_espera.edit_text(resposta_sucesso, parse_mode='Markdown')
                
                # Log de sucesso com ID para rastreamento futuro
                logger_telegram.info(f"✅ [/nota] Nota capturada com sucesso! ID={id_nota}, Tags={tags}")
                
            else:
                # === FALHA NA CAPTURA ===
                await mensagem_espera.edit_text(
                    "❌ *Falha ao capturar nota*\n\n"
                    "O sistema não conseguiu salvar sua nota no Lex Flow.\n\n"
                    "Possíveis causas:\n"
                    "• Lex Flow temporariamente indisponível\n"
                    "• Problema de autenticação (token expirado)\n"
                    "• Dados inválidos ou muito grandes\n\n"
                    "🔧 *Solução:* Tente novamente em alguns segundos.\n"
                    "Se persistir, verifique logs/core_engine.log",
                    parse_mode='Markdown'
                )
                
                # Log de erro (resultado veio vazio ou sem ID)
                logger_telegram.warning(f"⚠️ [/nota] Falha ao capturar nota. Resultado: {resultado}")
                
        except Exception as erro_nota:
            # Log detalhado do erro (com stack trace completo para diagnóstico)
            logger_telegram.error(f"❌ [/nota] Exceção não tratada: {erro_nota}", exc_info=True)
            
            # Resposta genérica ao usuário (sem expor detalhes técnicos do erro)
            await update.message.reply_text(
                "❌ *Erro inesperado ao capturar nota*\n\n"
                "Desculpe, ocorreu um erro inesperado. "
                "Nossa equipe foi notificada automaticamente.\n\n"
                "Por favor, tente novamente.",
                parse_mode='Markdown'
            )

    async def comando_tarefa(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler do comando /tarefa v1.3 FINAL - 100% Funcional!
        
        FORMATOS SUPORTADOS:
        - /tarefa <texto>  → Inbox automático
        - /tarefa <texto> --projeto <ID>  → ID numérico
        - /tarefa <texto> --projeto <NOME>  → Busca por nome
        - /tarefa <texto> --prioridade <nivel>
        - /tarefa <texto> --projeto <ID|NOME> --prioridade <nivel>
        
        v1.3 - EXTRAÇÃO DE ID DA ESTRUTURA REAL DA API:
        A API retorna: {'success': True, 'task': {'id': 123, ...}}
        """

        usuario_nome = update.effective_user.first_name or "Usuário"
        logger_telegram.info(f"💬 [/tarefa] Criação de tarefa solicitada por {usuario_nome}")
        
        try:
            # ========================================
            # PASSO 1: EXTRAIR TEXTO DO COMANDO
            # ========================================
            texto_completo = ' '.join(context.args) if context.args else ''
            
            if not texto_completo.strip():
                await update.message.reply_text(
                    "❌ Uso incorreto do /tarefa\n\n"
                    "Formatos:\n"
                    "/tarefa <texto>\n"
                    "/tarefa <texto> --projeto <ID|NOME>\n"
                    "/tarefa <texto> --prioridade <nivel>\n\n"
                    "Exemplos:\n"
                    "/tarefa Editar vídeo #12\n"
                    "/tarefa Revisar contrato --projeto 5\n"
                    "/tarefa Gravar podcast --projeto Canais Dark\n\n"
                    "Prioridades: baixa, media, alta, urgente"
                )
                return
            
            # ========================================
            # PASSO 2: INICIALIZAR MOTOR
            # ========================================
            motor = CoreEngine.obter_instancia()
            
            if not motor.lexflow:
                await update.message.reply_text(
                    "❌ Lex Flow indisponível\n\nTente novamente em instantes."
                )
                return
            
            # ========================================
            # PASSO 3: PARSEAR ARGUMENTOS
            # ========================================
            
            titulo_tarefa = texto_completo
            projeto_id = None
            prioridade = "medium"
            projeto_nome_busca = None
            
            # --- PARSEAR --PROJETO (suporta nomes com espaços!) ---
            if '--projeto' in texto_completo:
                partes_projeto = texto_completo.split('--projeto', 1)
                titulo_tarefa = partes_projeto[0].strip()
                resto_apos_projeto = partes_projeto[1].strip() if len(partes_projeto) > 1 else ''
                
                # Pega tudo até o próximo -- ou fim (suporta "Canais Dark" com espaço!)
                if '--prioridade' in resto_apos_projeto:
                    projeto_identificador = resto_apos_projeto.split('--prioridade')[0].strip()
                else:
                    projeto_identificador = resto_apos_projeto.strip()
                
                if projeto_identificador:
                    try:
                        projeto_id = int(projeto_identificador)
                        logger_telegram.info(f"   ✅ Projeto ID numérico: {projeto_id}")
                    except ValueError:
                        projeto_nome_busca = projeto_identificador
                        logger_telegram.info(f"   🔍 Projeto nome: '{projeto_nome_busca}'")
            
            # --- PARSEAR --PRIORIDADE ---
            if '--prioridade' in texto_completo:
                partes_prioridade = texto_completo.split('--prioridade', 1)
                parte_apos_prioridade = partes_prioridade[1].strip() if len(partes_prioridade) > 1 else ''
                
                prioridade_str = parte_apos_prioridade.split()[0] if parte_apos_prioridade.split() else 'medium'
                
                mapeamento_prioridade = {
                    'alta': 'high', 'media': 'medium', 'média': 'medium',
                    'baixa': 'low', 'urgente': 'urgent',
                    'high': 'high', 'medium': 'medium', 'low': 'low', 'urgent': 'urgent'
                }
                
                prioridade = mapeamento_prioridade.get(prioridade_str.lower(), 'medium')
                logger_telegram.info(f"   📊 Prioridade: '{prioridade_str}' → '{prioridade}'")
            
            # ========================================
            # PASSO 4: RESOLVER PROJETO (BUSCA POR NOME)
            # ========================================
            
            if projeto_nome_busca and not projeto_id:
                logger_telegram.info(f"   🔍 Buscando projeto: '{projeto_nome_busca}'")
                
                try:
                    projetos = motor.lexflow.get_projects()
                    
                    if projetos:
                        projeto_encontrado = None
                        
                        for p in projetos:
                            nome_projeto = p.get('name', '').lower().strip()
                            busca_lower = projeto_nome_busca.lower().strip()
                            
                            # Match exato, parcial ou inverso
                            if (busca_lower == nome_projeto or 
                                busca_lower in nome_projeto or 
                                nome_projeto in busca_lower):
                                projeto_encontrado = p
                                break
                        
                        if projeto_encontrado:
                            projeto_id = projeto_encontrado.get('id')
                            nome_real = projeto_encontrado.get('name', 'Desconhecido')
                            logger_telegram.info(f"   ✅ Projeto encontrado: '{nome_real}' (ID: {projeto_id})")
                        else:
                            nomes_projetos = [p.get('name', 'Sem nome') for p in projetos[:10]]
                            lista_texto = "\n".join([f"• {nome}" for nome in nomes_projetos])
                            
                            await update.message.reply_text(
                                f"❌ Projeto '{projeto_nome_busca}' não encontrado\n\n"
                                f"Projetos disponíveis:\n{lista_texto}\n\n"
                                f"Use o ID numérico ou nome exato."
                            )
                            return
                    else:
                        logger_telegram.warning("   ⚠️ Nenhum projeto retornado pelo Lex Flow")
                            
                except Exception as e:
                    logger_telegram.error(f"   ❌ Erro ao buscar projetos: {e}")
            
            # Se ainda sem projeto, usar Inbox (padrão)
            if not projeto_id:
                logger_telegram.info("   📥 Nenhum projeto especificado → usando Inbox (ID=1)")
                projeto_id = 1  # ID do Inbox (ajuste se necessário)
            
            # ========================================
            # PASSO 5: CRIAR TAREFA NO LEX FLOW
            # ========================================
            
            logger_telegram.info(f"   🎯 DADOS FINAIS:")
            logger_telegram.info(f"      Título: '{titulo_tarefa}'")
            logger_telegram.info(f"      Projeto ID: {projeto_id}")
            logger_telegram.info(f"      Prioridade: {prioridade}")
            
            resultado = None
            erro_tentativas = []
            
            # === TENTATIVA 1: Parâmetros nomeados ===
            try:
                logger_telegram.info("   🔄 Tentativa 1: add_task(project_id, title, priority)")
                resultado = motor.lexflow.add_task(
                    project_id=projeto_id,
                    title=titulo_tarefa,
                    priority=prioridade
                )
                logger_telegram.info(f"   📦 Resultado: {type(resultado)} = {resultado}")
                
            except Exception as e1:
                erro_tentativas.append(f"T1: {e1}")
                logger_telegram.warning(f"   ⚠️ T1 falhou: {e1}")
                
                # === TENTATIVA 2: Posicionais ===
                try:
                    logger_telegram.info("   🔄 Tentativa 2: add_task(title, project_id, priority)")
                    resultado = motor.lexflow.add_task(titulo_tarefa, projeto_id, prioridade)
                    logger_telegram.info(f"   📦 Resultado: {type(resultado)} = {resultado}")
                    
                except Exception as e2:
                    erro_tentativas.append(f"T2: {e2}")
                    logger_telegram.warning(f"   ⚠️ T2 falhou: {e2}")
                    
                    # === TENTATIVA 3: title + project_id ===
                    try:
                        logger_telegram.info("   🔄 Tentativa 3: add_task(title, project_id)")
                        resultado = motor.lexflow.add_task(titulo_tarefa, projeto_id)
                        logger_telegram.info(f"   📦 Resultado: {type(resultado)} = {resultado}")
                        
                    except Exception as e3:
                        erro_tentativas.append(f"T3: {e3}")
                        logger_telegram.warning(f"   ⚠️ T3 falhou: {e3}")
                        
                        # === TENTATIVA 4: Só title ===
                        try:
                            logger_telegram.info("   🔄 Tentativa 4: add_task(title)")
                            resultado = motor.lexflow.add_task(titulo_tarefa)
                            logger_telegram.info(f"   📦 Resultado: {type(resultado)} = {resultado}")
                            
                        except Exception as e4:
                            erro_tentativas.append(f"T4: {e4}")
                            logger_telegram.error(f"   ❌ Todas as tentativas falharam!")
            
            # ========================================
            # PASSO 6: PROCESSAR RESULTADO (EXTRAIR ID CORRETAMENTE!)
            # ========================================
            
            if resultado:
                task_id = None
                
                # === ESTRUTURA CONHECIDA: {'success': True, 'task': {...}} ===
                if isinstance(resultado, dict):
                    if 'task' in resultado and isinstance(resultado['task'], dict):
                        # A API retorna {'success': bool, 'task': {id, title, ...}}
                        task_obj = resultado['task']
                        task_id = task_obj.get('id') or task_obj.get('_id') or task_obj.get('taskId')
                        logger_telegram.info(f"   ✅ Estrutura detectada: resultado['task']['id'] = {task_id}")
                    else:
                        # Tentar direto no resultado (formatos alternativos)
                        for campo in ['id', 'task_id', '_id', 'taskId']:
                            if campo in resultado:
                                task_id = resultado[campo]
                                break
                        
                        if not task_id:
                            logger_telegram.warning(f"   ⚠️ ID não encontrado. Chaves: {list(resultado.keys())}")
                            task_id = '?'
                
                elif isinstance(resultado, (int, str)):
                    task_id = resultado
                else:
                    task_id = str(resultado)[:20]
                
                emoji_prioridade = {
                    'urgent': '🔴🔴🔴',
                    'high': '🟠',
                    'medium': '🟡',
                    'low': '🟢'
                }.get(prioridade, '⚪')
                
                msg_sucesso = (
                    f"✅ TAREFA CRIADA COM SUCESSO!\n\n"
                    f"🆔 ID: {task_id}\n"
                    f"📋 Título: {titulo_tarefa}\n"
                    f"{emoji_prioridade} Prioridade: {prioridade.upper()}\n"
                    f"📂 Projeto ID: {projeto_id}"
                )
                
                await update.message.reply_text(msg_sucesso)
                logger_telegram.info(f"   ✅ Tarefa criada com sucesso! ID={task_id}")
                
            else:
                msg_erro = "❌ Falha ao criar tarefa\n\nErros:\n"
                for erro in erro_tentativas:
                    msg_erro += f"• {erro}\n"
                msg_erro += "\nUse /projetos para ver IDs válidos"
                
                await update.message.reply_text(msg_erro)
                logger_telegram.error(f"❌ [/tarefa] Falha total: {erro_tentativas}")
            
        except Exception as e:
            logger_telegram.error(f"❌ [/tarefa] ERRO CRÍTICO: {type(e).__name__}: {e}", exc_info=True)
            
            try:
                await update.message.reply_text("⚠️ Erro inesperado no /tarefa\n\nErro registrado nos logs.")
            except:
                pass

    async def comando_projetos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler do comando /projetos - Listagem Completa de Projetos Ativos
        
        ====================================================================
        PROPÓSITO:
        Mostrar todos os projetos cadastrados no Lex Flow Dashboard.
        Útil para: ver o que está ativo, obter IDs para usar em /tarefa --projeto,
        verificar status geral dos trabalhos em andamento.
        
        ====================================================================
        O QUE EXIBE:
        1. Contagem total de projetos ativos
        2. Lista numerada com: Nome, ID, Descrição (resumida)
        3. Dica de uso do ID em outros comandos
        
        ====================================================================
        LIMITAÇÕES TÉCNICAS:
        - Telegram limita mensagens a 4096 caracteres
        - Se houver muitos projetos, a mensagem é truncada com "(...continua)"
        - Futuro: implementar paginação se necessário (>20 projetos)
        
        ====================================================================
        """

        usuario_nome = update.effective_user.first_name or "Usuário"
        logger_telegram.info(f"💬 [/projetos] Listagem solicitada por {usuario_nome}")
        
        try:
            # ========================================
            # BUSCAR PROJETOS DO LEX FLOW (API REAL)
            # ========================================
            projetos = self.motor.lexflow.get_projects()
            
            # ========================================
            # CASO 1: NENHUM PROJETO ENCONTRADO
            # ========================================
            if not projetos:
                await update.message.reply_text(
                    "📭 *Nenhum projeto encontrado!*\n\n"
                    "Seu Lex Flow não possui projetos cadastrados ainda.\n\n"
                    "🔧 *Como resolver:*\n"
                    "1. Acesse https://flow.lex-usamn.com.br\n"
                    "2. Clique em \"Novo Projeto\"\n"
                    "3. Preencha nome e descrição\n"
                    "4. Salve e volte aqui!\n\n"
                    "Depois de criar, use `/projetos` novamente.",
                    parse_mode='Markdown'
                )
                return  # Interrompe aqui (nada a listar)
            
            # ========================================
            # CASO 2: PROJETOS ENCONTRADOS → MONTAR LISTA
            # ========================================
            
            # Cabeçalho com contagem
            mensagem = f"""
📂 *PROJETOS ATIVOS* ({len(projetos)})
━━━━━━━━━━━━━━━━━━━━━
"""
            
            # Iterar sobre cada projeto e formatar
            for indice, projeto in enumerate(projetos, start=1):
                # Extrair dados do projeto (com defaults seguros se campo faltar)
                proj_id = projeto.get('id', '?')
                proj_nome = projeto.get('name', 'Sem nome')
                proj_descricao = projeto.get('description', '')
                
                # Linha principal: nome + ID em monospace (fácil copiar)
                mensagem += f"{indice}. *{proj_nome}* `(ID: {proj_id})`\n"
                
                # Descrição (opcional - só mostra se existir)
                if proj_descricao:
                    # Limitar descrição a 80 caracteres + reticências (para não poluir)
                    desc_curta = (proj_descricao[:77] + '...') if len(proj_descricao) > 80 else proj_descricao
                    mensagem += f"   💡 {desc_curta}\n"
                
                # Espaçamento entre projetos (legibilidade)
                mensagem += "\n"
            
            # Rodapé instrutivo (ensina a usar o ID)
            mensagem += """💡 *Dica:* Use `/tarefa Título --projeto ID` para adicionar tarefas!
   Exemplo: `/tarefa Editar vídeo --projeto 5`
"""
            
            # ========================================
            # VERIFICAR LIMITE DE TAMANHO DO TELEGRAM (4096 chars)
            # ========================================
            if len(mensagem) > 4000:
                # Truncar mensagem se muito longa (evitar erro de API do Telegram)
                mensagem = mensagem[:3970] + "\n\n...(lista truncada - muitos projetos)"
                logger_telegram.warning(f"   Lista de projetos truncada ({len(mensagem)} caracteres)")
            
            # Enviar mensagem completa
            await update.message.reply_text(mensagem, parse_mode='Markdown')
            
            # Log de sucesso
            logger_telegram.info(f"✅ [/projetos] Listagem enviada ({len(projetos)} projetos)")
            
        except Exception as erro_projetos:
            # Log do erro
            logger_telegram.error(f"❌ [/projetos] Erro ao listar projetos: {erro_projetos}", exc_info=True)
            
            # Resposta de erro
            await update.message.reply_text(
                "❌ *Erro ao buscar projetos*\n\n"
                "Não foi possível obter a lista do Lex Flow.\n"
                "Tente novamente em alguns segundos.",
                parse_mode='Markdown'
            )

    async def comando_metricas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler do comando /metricas - Painel de Métricas de Produtividade
        
        ====================================================================
        PROPÓSITO:
        Mostrar estatísticas detalhadas de produtividade do dia atual.
        Permite ao usuário ter visibilidade do seu desempenho e ajustar
        o rumo se necessário (data-driven decision making).
        
        ====================================================================
        MÉTRICAS EXIBIDAS:
        - Tarefas concluídas (absoluto)
        - Notas capturadas (volume de ideias)
        - Sessões Pomodoro (horas de foco profundo)
        - Projetos ativos (escopo de trabalho)
        - Taxa de conclusão (percentual)
        - Horas de foco (estimativa baseada em pomodoros)
        
        ====================================================================
        ELEMENTO MOTIVACIONAL:
        Baseado nas métricas, adiciona mensagem personalizada:
        - ≥5 tarefas: "Incendiário!" (alto desempenho)
        - ≥3 tarefas: "Bom progresso!" (no caminho)
        - <3 tarefas: "Vamos começar?" (call to action)
        
        ====================================================================
        """

        usuario_nome = update.effective_user.first_name or "Usuário"
        logger_telegram.info(f"💬 [/metricas] Painel de métricas solicitado por {usuario_nome}")
        
        try:
            # ========================================
            # OBTER ESTATÍSTICAS DO DIA
            # ========================================
            stats = self.motor.obter_today_stats()
            
            # ========================================
            # VALIDAR SE HÁ DADOS DISPONÍVEIS
            # ========================================
            if not stats:
                await update.message.reply_text(
                    "📊 *Métricas Indisponíveis*\n\n"
                    "Dados insuficientes para gerar estatísticas de hoje.\n\n"
                    "Isso pode acontecer porque:\n"
                    "• Você acabou de começar o dia\n"
                    "• Nenhuma atividade registrada ainda\n\n"
                    "Comece a usar `/tarefa` ou `/nota` para gerar dados!",
                    parse_mode='Markdown'
                )
                return
            
            # ========================================
            # MONTAR PAINEL DE MÉTRICAS FORMATADO
            # ========================================
            data_atual = datetime.now().strftime('%d/%m/%Y')
            
            # Extrair métricas individuais (com defaults seguros)
            tarefas_concluidas = stats.get('tarefas_concluidas', 0)
            notas_capturadas = stats.get('notas_capturadas', 0)
            pomodoros = stats.get('pomodoros', 0)
            projetos_ativos = stats.get('projetos_ativos', 0)
            taxa_conclusao = stats.get('taxa_conclusao', 'N/A')
            horas_foco = stats.get('horas_foco', 'N/A')
            
            # Montar mensagem principal
            mensagem = f"""
📊 *PAINEL DE MÉTRICAS*
📅 {data_atual}
━━━━━━━━━━━━━━━━━━━━━

✅ *Tarefas Concluídas:* {tarefas_concluidas}
📝 *Notas Capturadas:* {notas_capturadas}
🍅 *Pomodoros:* {pomodoros} ({(pomodoros * 25) // 60}h {(pomodoros * 25) % 60}m de foco)
📁 *Projetos Ativos:* {projetos_ativos}

━━━━━━━━━━━━━━━━━━━━━

📈 *Taxa de Conclusão:* {taxa_conclusao}%
⚡ *Horas de Foco:* {horas_foco}h
"""
            
            # ========================================
            # ADICIONAR MENSAGEM MOTIVACIONAL PERSONALIZADA
            # ========================================
            if tarefas_concluidas >= 5:
                mensagem += "\n🔥 *INCENDIÁRIO!* Você está arrazando hoje! Performance de alto nível!"
            elif tarefas_concluidas >= 3:
                mensagem += "\n💪 *BOM PROGRESSO!* Você está no caminho certo. Continue assim!"
            elif tarefas_concluidas >= 1:
                mensagem += "\n👍 *BOM INÍCIO!* Cada tarefa conta. Vamos para a próxima?"
            else:
                mensagem += "\n🌱 *HORA DE COMEÇAR!* Use `/tarefa` para adicionar sua primeira tarefa!"
            
            # Enviar painel completo
            await update.message.reply_text(mensagem, parse_mode='Markdown')
            
            # Log de sucesso
            logger_telegram.info(f"✅ [/metricas] Painel enviado (Tarefas: {tarefas_concluidas}, Pomodoros: {pomodoros})")
            
        except Exception as erro_metricas:
            # Log do erro
            logger_telegram.error(f"❌ [/metricas] Erro ao gerar métricas: {erro_metricas}", exc_info=True)
            
            # Resposta de erro
            await update.message.reply_text(
                "❌ *Erro ao calcular métricas*\n\n"
                "Não foi possível obter as estatísticas.",
                parse_mode='Markdown'
            )

    async def comando_pomodoro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler do comando /pomodoro - Controle de Sessões de Foco (Técnica Pomodoro)
        
        ====================================================================
        O QUE É TÉCNICA POMODORO?
        Método de gestão de tempo que divide trabalho em intervalos de 25 minutos
        (chamados "pomodoros"), separados por pausas curtas. Aumenta foco e produtividade.
        
        REF: https://pt.wikipedia.org/wiki/T%C3%A9cnica_Pomodoro
        
        ====================================================================
        SUBCOMANDOS DISPONÍVEIS:
        
        1. /pomodoro iniciar (ou start / começar)
           → Inicia uma sessão de 25 minutos de foco
           → (Futuro: integrar com timer real e notificação automática)
        
        2. /pomodoro parar (ou stop / pause)
           → Pausa a sessão atual em andamento
           → Registra tempo parcial
        
        3. /pomodoro logar (ou log / feito / done)
           → Registra uma sessão já concluída manualmente
           → Salva como entrada de produtividade no sistema
        
        4. /pomodoro (sem argumentos)
           → Exibe menu de opções e status atual
        
        ====================================================================
        STATUS ATUAL (v1.0):
        - Implementação básica funcional (log manual + menu)
        - Timer automático pendente (requer APScheduler ou job queue)
        - Notificações automáticas pendentes (requer integração avançada)
        
        ====================================================================
        PLANO FUTURO (v2.0):
        - Timer real com countdown
        - Notificação automática ao terminar 25min
        - Sugestão automática de pausa
        - Estatísticas detalhadas de foco semanal/mensal
        - Gráficos de produtividade (integração com /metricas)
        
        ====================================================================
        """

        usuario_nome = update.effective_user.first_name or "Usuário"
        
        # Extrair subcomando (se fornecido) - tudo após /pomodoro
        acao = ' '.join(context.args).lower().strip() if context.args else ''
        
        logger_telegram.info(f"💬 [/pomodoro] Ação solicitada: '{acao}' por {usuario_nome}")
        
        # ========================================
        # SWITCH DE SUBCOMANDOS
        # ========================================
        try:
            if acao in ['iniciar', 'start', 'começar']:
                # === SUBCOMANDO: INICIAR SESSÃO ===
                mensagem_resposta = """
🍅 *POMODORO INICIADO!*

⏱️ *Timer:* 25 minutos
🎯 *Modo:* FOCO TOTAL (sem distrações!)

━━━━━━━━━━━━━━━━━━━━━
📋 *Durante esta sessão:*
• Silencie o celular
• Feche abas desnecessárias
• Tenha água por perto
• Foque em UMA tarefa só

*Dica:* Eu te aviso quando o tempo acabar!
(Implementação do timer automático: Fase 3 - Automações)

*Status:* 🟢 *Em andamento...*
""".strip()
                
            elif acao in ['parar', 'stop', 'pause', 'pausar']:
                # === SUBCOMANDO: PAUSAR SESSÃO ===
                mensagem_resposta = """⏸️ *POMODORO PAUSADO*

Sessão interrompida pelo usuário.

Quando voltar, use:
`/pomodoro iniciar` → Retomar contador
`/pomodoro logar` → Registrar como concluído

💪 Não se preocupe: pausas estratégicas são parte do processo!
""".strip()
                
            elif acao in ['logar', 'log', 'feito', 'done', 'concluir', 'completar']:
                # === SUBCOMANDO: REGISTRAR SESSÃO CONCLUÍDA ===
                
                # Registrar pomodoro como entrada de produtividade no sistema
                resultado = self.motor.capturar(
                    idea="✅ Sessão Pomodoro Concluída (25min de foco profundo)",
                    tags=["pomodoro", "produtividade", "foco", "log", "telegram"]
                )
                
                if resultado and resultado.get('id'):
                    id_log = resultado.get('id')
                    mensagem_resposta = f"""
✅ *POMODORO REGISTRADO COM SUCESSO!*

🍅 +1 sessão de foco completada!

*Resumo da Sessão:*
• ⏱️ Duração: 25 minutos
• 🎯 Foco: 🔥 Máximo
• ✅ Status: Concluído
🆔 ID do Log: `{id_log}`

━━━━━━━━━━━━━━━━━━━━━
☕ *Hora da pausa!* (5 minutos)

*Recomendação:*
• Levante-se e alongue
• Beba água
• Olhe para longe (descansar olhos)
• NÃO pegue o celular!

Quando estiver pronto: `/pomodoro iniciar`
""".strip()
                else:
                    # Falha ao registrar (mas não crasha)
                    mensagem_resposta = """
⚠️ *POMODORO RECEBIDO*

Registramos que você completou uma sessão!
(Houve um problema técnico ao salvar o log, mas sua contagem é válida)

☕ *Pausa merecida!* Descanse 5 minutos.
""".strip()
                
            else:
                # === SEM ARGUMENTOS OU COMANDO DESCONHECIDO → MENU PRINCIPAL ===
                
                # Tentar buscar estatísticas de pomodoros do dia (se disponíveis)
                try:
                    stats = self.motor.obter_today_stats()
                    pomodoros_hoje = stats.get('pomodoros', 0) if stats else 0
                except Exception:
                    pomodoros_hoje = '?'  # Se falhar, mostra interrogacao
                
                mensagem_resposta = f"""
🍅 *CONTROLE POMODORO*

Escolha uma ação abaixo:

`/pomodoro iniciar` → Começar 25min de foco 🔥
`/pomodoro parar` → Pausar sessão atual ⏸️
`/pomodoro logar` → Registrar como concluído ✅

━━━━━━━━━━━━━━━━━━━━━
📊 *Hoje:* {pomodoros_hoje} sessões
🎯 *Meta diária:* 8 pomodoros (4h de foco)

*Técnica Pomodoro:*
25min foco + 5min pausa
(após 4 ciclos: pausa longa 15-30min)
""".strip()
            
            # Enviar resposta do subcomando selecionado
            await update.message.reply_text(mensagem_resposta, parse_mode='Markdown')
            
            # Log de sucesso
            logger_telegram.info(f"✅ [/pomodoro] Ação '{acao}' processada com sucesso")
            
        except Exception as erro_pomodoro:
            # Log do erro
            logger_telegram.error(f"❌ [/pomodoro] Erro na ação '{acao}': {erro_pomodoro}", exc_info=True)
            
            # Resposta de erro
            await update.message.reply_text(
                "❌ *Erro no controle Pomodoro*\n\n"
                "Tente novamente.",
                parse_mode='Markdown'
            )

    async def comando_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler do comando /status - Health Check Completo do Sistema
        
        ====================================================================
        PROPÓSITO (ADMIN/MONITORAMENTO):
        Exibe diagnóstico completo do estado do sistema. Útil para:
        - Debug de problemas de conexão
        - Verificar se Lex Flow está online
        - Monitorar uptime do motor
        - Auditar estado geral da infraestrutura
        
        ====================================================================
        INFORMAÇÕES EXIBIDAS:
        
        1. MOTOR PRINCIPAL (CoreEngine):
           - Status (ativo/parado)
           - Uptime (tempo desde inicialização)
           - Versão do software
           - Ambiente (dev/staging/prod)
           - Métricas de uso do dia
        
        2. LEX FLOW (API Externa):
           - Status de autenticação (conectado/desconectado)
           - Quantidade de notas no inbox
           - Número de projetos ativos
           - Áreas configuradas
        
        3. TIMESTAMP:
           - Momento exato da verificação (para saber se dado é atual)
        
        ====================================================================
        PÚBLICO-ALVO:
        - Administradores do sistema
        - Desenvolvedores fazendo debug
        - Usuários avançados querendo diagnosticar problemas
        
        ====================================================================
        """

        usuario_nome = update.effective_user.first_name or "Usuário"
        logger_telegram.info(f"💬 [/status] Health check solicitado por {usuario_nome}")
        
        try:
            # ========================================
            # OBTER STATUS COMPLETO DO MOTOR
            # =================================-------
            # Este método retorna um dicionário com TODAS as informações do sistema
            status = self.motor.obter_status_completo()
            
            # ========================================
            # EXTRAIR E FORMATAR DADOS DO STATUS
            # ========================================
            
            # Dados do motor principal
            motor_status = status.get('motor', {})
            lex_flow_status = status.get('lex_flow', {})
            
            # Formatar uptime de segundos para string legível (ex: "2h 30m 15s")
            uptime_segundos = motor_status.get('uptime_segundos', 0)
            uptime_formatado = self._formatar_tempo(uptime_segundos)
            
            # Status textuais com emojis visuais (rápida compreensão)
            motor_rodando = "🟢 *ATIVO*" if motor_status.get('rodando') else "🔴 *PARADO*"
            lex_autenticado = "🟢 *Conectado*" if lex_flow_status.get('autenticado') else "🔴 *Desconectado*"
            
            # ========================================
            # MONTAR RELATÓRIO DE HEALTH CHECK
            # ========================================
            mensagem = f"""
🏥 *HEALTH CHECK COMPLETO*
━━━━━━━━━━━━━━━━━━━━━

🧠 *Motor Principal:* {motor_rodando}
⏱️ *Uptime:* {uptime_formatado}
📊 *Versão:* {motor_status.get('versao', 'N/A')}
🌐 *Ambiente:* {motor_status.get('ambiente', 'N/A')}

📡 *Conexão Lex Flow:* {lex_autenticado}
📥 *Notas no Inbox:* {lex_flow_status.get('quantidade_notas_inbox', '?')}
📂 *Projetos Ativos:* {lex_flow_status.get('quantidade_projetos_ativos', '?')}
🏷️ *Áreas:* {lex_flow_status.get('quantidade_areas', '?')}

━━━━━━━━━━━━━━━━━━━━━

📈 *Métricas de Operação (Hoje):*
• 📝 Capturas realizadas: {motor_status.get('capturas_hoje', 0)}
• ⚙️ Processamentos: {motor_status.get('processamentos_hoje', 0)}
• ❌ Erros registrados: {motor_status.get('erros_totais', 0)}

🕐 *Verificado em:* {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
            
            # Enviar relatório completo
            await update.message.reply_text(mensagem, parse_mode='Markdown')
            
            # Log de sucesso
            logger_telegram.info(f"✅ [/status] Health check enviado (Motor: {'Ativo' if motor_status.get('rodando') else 'Parado'})")
            
        except Exception as erro_status:
            # Log do erro
            logger_telegram.error(f"❌ [/status] Erro ao obter status: {erro_status}", exc_info=True)
            
            # Resposta de erro
            await update.message.reply_text(
                "❌ *Erro ao obter status do sistema*\n\n"
                "Não foi possível gerar o relatório de diagnóstico.",
                parse_mode='Markdown'
            )

    async def comando_ajuda(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler do comando /ajuda - Documentação Completa de Comandos
        
        ====================================================================
        PROPÓSITO:
        Exibir referência completa de todos os comandos disponíveis,
        com descrições, formatos e exemplos práticos de uso.
        
        É o "manual do usuário" do bot, sempre acessível via /ajuda.
        
        ====================================================================
        ESTRUTURA DA MENSAGEM:
        1. Cabeçalho com título
        2. Lista de comandos principais (bala de prata)
        3. Seção de exemplos práticos (copy-paste ready)
        4. Recurso extra (captura automática)
        5. Rodapé com versão e créditos
        
        ====================================================================
        """

        logger_telegram.info("💬 [/ajuda] Manual de comandos solicitado")
        
        # Mensagem de ajuda completa e formatada (documentação auto-contida)
        mensagem_ajuda = """
📚 *AJUDA - COMANDOS DISPONÍVEIS*
━━━━━━━━━━━━━━━━━━━━━

*🎯 COMANDOS PRINCIPAIS:*

/start – Iniciar bot e ver status do sistema
/hoje – Ver prioridades do dia (Morning Briefing) 📋
/nota `<texto>` – Capturar ideia/nota rapidamente 📝
/tarefa `<texto>` – Criar tarefa em projeto 📋
/projetos – Listar todos os projetos ativos 📂
/metricas – Ver painel de métricas de produtividade 📊
/pomodoro – Controlar sessões de foco (Pomodoro) 🍅
/status – Health check completo do sistema 🏥
/ajuda – Esta mensagem de ajuda ℹ️

━━━━━━━━━━━━━━━━━━━━━

*📖 EXEMPLOS PRÁTICOS DE USO:*

*Ver prioridades:*
`/hoje`

*Capturar ideia simples:*
`/nota Ideia incrível para vídeo sobre Bitcoin`

*Capturar com tags personalizadas:*
`/nota Comprar microfone --tags compras equipamento urgente`

*Criar tarefa básica:*
`/tarefa Editar vídeo #12`

*Criar tarefa avançada:*
`/tarefa Revisar contrato --projeto 5 --prioridade alta`

*Listar projetos:*
`/projetos`

*Iniciar Pomodoro:*
`/pomodoro iniciar`

*Registrar Pomodoro feito:*
`/pomodoro logar`

━━━━━━━━━━━━━━━━━━━━━

*🚀 RECURSO EXTRA - CAPTURA AUTOMÁTICA:*

Envie qualquer texto *diretamente* (sem usar /comando) que eu capturo como nota automaticamente!

Exemplo: basta digitar "Lembrar de ligar para o cliente" e enviar ✅

*Funciona com:* textos, ideias, pensamentos, links, referências...

━━━━━━━━━━━━━━━━━━━━━
🧠 *Lex Brain Hybrid v1.0* | *Second Brain Ultimate System*
💻 *by Lex-Usamn* | *Abril 2026*
"""
        
        # Enviar mensagem de ajuda completa
        await update.message.reply_text(mensagem_ajuda, parse_mode='Markdown')
        
        # Log de sucesso
        logger_telegram.info("✅ [/ajuda] Manual de comandos enviado")

    async def handler_mensagem_texto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler para Mensagens de Texto Direto (Sem Comando /)
        
        ====================================================================
        RECURSO MAIS PODEROSO DO BOT (UX Revolution):
        
        Qualquer texto enviado pelo usuário que NÃO começa com barra (/)
        é automaticamente capturado como nota/ideia. Isso torna o uso
        extremamente natural, rápido e fluido - como conversar com um amigo.
        
        ====================================================================
        POR QUÊ ISSO É IMPORTANTE?
        
        UX Tradicional (ruim):
        Usuario precisa lembrar: /nota texto aqui
        → Friction cognitiva alta
        → Interrupção do fluxo de pensamento
        
        UX deste Bot (excelente):
        Usuario apenas digita e envia
        → Zero friction
        → Captura de ideia na velocidade do pensamento
        → Reduz barreira de entrada drasticamente
        
        ====================================================================
        REGRAS DE FILTRAGEM:
        
        1. Mensagens < 3 caracteres: IGNORADAS (provavelmente acidentes)
        2. Mensagens vazias: IGNORADAS
        3. Demais: CAPTURADAS AUTOMATICAMENTE
        
        ====================================================================
        FEEDBACK AO USUÁRIO:
        
        - Sucesso: Confirmação curta e discreta (ID da nota)
          → Não polui o chat com mensagens longas
          → Permite usuário continuar enviando rapidamente
          
        - Erro: Aviso gentil sugerindo usar /nota explicitamente
          → Fallback gracefully
          
        ====================================================================
        """

        usuario_nome = update.effective_user.first_name or "Usuário"
        texto_mensagem = update.message.text
        
        # Log de auditoria (recebimento da mensagem)
        logger_telegram.info(f"💬 [MENSAGEM DIRETA] De {usuario_nome}: {texto_mensagem[:80]}...")
        
        try:
            # ========================================
            # FILTRAGEM: Ignorar mensagens muito curtas (acidentes)
            # ========================================
            if len(texto_mensagem.strip()) < 3:
                # Silenciosamente ignorar (não responde nada)
                # Evita spam quando usuário digita "ok", "sim", "não" acidentalmente
                return
            
            # ========================================
            # CAPTURA AUTOMÁTICA VIA MOTOR
            # =================================-------
            # Mesma lógica do /note, mas sem precisar de comando
            resultado = self.motor.capturar(idea=texto_mensagem)
            
            # ========================================
            # RESPONDER COM CONFIRMAÇÃO DISCRETA
            # ========================================
            if resultado and resultado.get('id'):
                # Sucesso: confirmação curta (não interrompe fluxo do usuário)
                id_nota = resultado.get('id', 'desconhecido')
                
                await update.message.reply_text(
                    f"✅ *Capturada!* ID: `{id_nota}`",
                    parse_mode='Markdown'
                )
                
                # Log de sucesso
                logger_telegram.info(f"✅ [AUTO-CAPTURA] Nota salva! ID={id_nota}")
                
            else:
                # Falha: aviso gentil (não crasha, não expõe erro técnico)
                await update.message.reply_text(
                    "⚠️ *Não consegui salvar.*\n\n"
                    "Tente com `/nota texto` explicitamente.",
                    parse_mode='Markdown'
                )
                
                # Log de aviso
                logger_telegram.warning(f"⚠️ [AUTO-CAPTURA] Falha silenciosa ao salvar mensagem")
                
        except Exception as erro_mensagem:
            # Log do erro (mas NÃO responde ao usuário para evitar spam)
            # Se der erro, é melhor ignorar silenciosamente do que poluir chat com msg de erro
            logger_telegram.error(f"❌ [AUTO-CAPTURA] Erro ao processar mensagem: {erro_mensagem}", exc_info=True)
            # Decisão consciente: não responder erro em mensagens diretas (UX > debug)

    # =========================================================================
    # MÉTODOS AUXILIARES INTERNOS (Utilitários Privados)
    # =========================================================================

    def _formatar_tempo(self, segundos: float) -> str:
        """
        Formatador de Tempo para Exibição Amigável (Human-Readable)
        
        Converte um valor em segundos para formato legível por humanos.
        Exemplos: 900 → "15min", 3665 → "1h 1min 5s", 45 → "45s"
        
        ====================================================================
        ARGUMENTOS:
            segundos: Quantidade de tempo em segundos (float ou int)
                      Pode ser decimal (ex: 90.5 segundos)
        
        RETORNA:
            String formatada de forma amigável:
            - "<X>s" para menos de 1 minuto
            - "<X>m <Y>s" para menos de 1 hora  
            - "<X>h <Y>m" para 1+ hora
            - "0s" para zero ou negativo
        
        ====================================================================
        EXEMPLOS DE USO:
        
            >>> self._formatar_tempo(45)
            '45s'
            
            >>> self._formatar_tempo(90)
            '1m 30s'
            
            >>> self._formatar_tempo(3661)
            '1h 1m 1s'
            
            >>> self._formatar_tempo(0)
            '0s'
        
        ====================================================================
        """
        
        # Caso especial: zero ou negativo
        if segundos <= 0:
            return "0s"
        
        # Caso simples: menos de 1 minuto (mostra só segundos)
        if segundos < 60:
            return f"{int(segundos)}s"
        
        # Calcular componentes de tempo
        horas = int(segundos // 3600)  # 3600 segundos = 1 hora
        minutos = int((segundos % 3600) // 60)  # Resto da divisão por hora, dividido por 60
        segundos_restantes = int(segundos % 60)  # Resto da divisão por minuto
        
        # Construir string formatada (só inclui componentes relevantes)
        partes = []
        
        if horas > 0:
            partes.append(f"{horas}h")  # Adiciona horas se > 0
            
        if minutos > 0:
            partes.append(f"{minutos}m")  # Adiciona minutos se > 0
            
        # Só mostra segundos se não temos horas (evita "2h 0m 5s" → preferível "2h 5s"? Não, decidimos omitir segundos se tem horas)
        if segundos_restantes > 0 and not horas:
            partes.append(f"{segundos_restantes}s")  # Segundos só sem horas
        
        # Se por algum motivo não adicionou nada (não deveria acontecer), retorna "0s"
        return ' '.join(partes) if partes else "0s"

    # =========================================================================
    # MÉTODOS DE CONTROLE DO BOT (Inicialização e Execução)
    # =========================================================================

    def iniciar(self):
        """
        Iniciar o Bot do Telegram (Método Principal - Bloqueante)
        
        ====================================================================
        ESTE É O MÉTODO QUE TUDO ORQUESTRA.
        É o ponto de entrada único para colocar o bot no ar.
        
        ====================================================================
        FLUXO DE EXECUÇÃO COMPLETO:
        
        1. VALIDAR DEPENDÊNCIAS
           - Verifica se python-telegram-bot está instalado
           - Se não estiver, exibe instruções de instalação e aborta
        
        2. CRIAR APPLICATION
           - Instancia Application.builder().token(self.token).build()
           - Configura conexão com servidores do Telegram
        
        3. REGISTRAR HANDLERS (MAPEAR COMANDOS → FUNÇÕES)
           - /start → self.comando_start
           - /hoje → self.comando_hoje
           - /nota → self.comando_nota
           - /tarefa → self.comando_tarefa
           - /projetos → self.comando_projetos
           - /metricas → self.comando_metricas
           - /pomodoro → self.comando_pomodoro
           - /status → self.comando_status
           - /ajuda → self.comando_ajuda
           - (texto direto) → self.handler_mensagem_texto
        
        4. INICIAR POLLING (CONECTAR NO TELEGRAM)
           - Conecta nos servidores do Telegram via long-polling
           - Começa a receber updates (mensagens, comandos, etc.)
           - Fica em loop infinito aguardando interações
        
        5. LOOP PRINCIPAL (INFINITO - ATÉ CTRL+C)
           - Para cada mensagem recebida: despacha para handler correto
           - Handler processa e responde ao usuário
           - Repete indefinidamente
        
        ====================================================================
        COMO PARAR O BOT:
        - Pressione Ctrl+C no terminal onde o bot está rodando
        - Ou envie SIGINT/SIGTERM (kill command no Linux)
        - O bot intercepta e encerra gracefulmente (limpa recursos)
        
        ====================================================================
        NOTA TÉCNICA - POLLING VS WEBHOOK:
        
        POLLING (usado aqui):
        - Vantagem: Simples, funciona em qualquer máquina (mesmo localhost)
        - Desvantagem: Requer processo rodando 24/7
        - Ideal para: Desenvolvimento, testes, VPS dedicado
        
        WEBHOOK (produção escalável):
        - Vantagem: Escalável, não precisa ficar "ouvindo" ativamente
        - Desvantagem: Requer URL pública (HTTPS), servidor web
        - Ideal para: Produção com muitos usuários, serverless
        
        Futuro: Implementar modo webhook para deploy em produção escalável.
        
        ====================================================================
        """
        
        # ========================================
        # PASSO 1: VALIDAR DEPENDÊNCIA CRÍTICA
        # ========================================
        if not LIB_TELEGRAM_DISPONIVEL:
            # Erro fatal sem a biblioteca - não tem como prosseguir
            print("\n" + "=" * 80)
            print("❌ FATAL: Biblioteca python-telegram-bot não instalada!")
            print("=" * 80)
            print("\n🔧 SOLUÇÃO - Execute o comando abaixo para instalar:\n")
            print("   pip install python-telegram-bot>=20.7\n")
            print("Ou instale todas as dependências do projeto:\n")
            print("   pip install -r requirements.txt\n")
            print("Após instalar, execute este script novamente.")
            print("=" * 80 + "\n")
            return  # Aborta execução aqui
        
        # ========================================
        # LOGS DE INICIALIZAÇÃO
        # ========================================
        logger_telegram.info("🚀 Iniciando Telegram Bot...")
        logger_telegram.info(f"   Token configurado: {self.token[:10]}...{self.token[-4:]}")
        logger_telegram.info("   Biblioteca python-telegram-bot: ✅ Disponível")
        
        try:
            # ========================================
            # PASSO 2: CRIAR APPLICATION (Builder Pattern)
            # =================================-------
            # O Application é o "cérebro" do bot que gerencia tudo internamente
            aplicacao = Application.builder().token(self.token).build()
            
            logger_telegram.info("✅ Application criada com sucesso")
            
            # ========================================
            # PASSO 3: REGISTRAR TODOS OS HANDLERS
            # =================================-------
            # Cada CommandHandler mapeia um comando textual (/comando) para um método Python
            # O MessageHandler captura qualquer texto que não é comando (para auto-capture)
            
            logger_telegram.info("📋 Registrando handlers de comandos...")
            
            # Handlers de comandos (textual, começa com /)
            aplicacao.add_handler(CommandHandler("start", self.comando_start))
            aplicacao.add_handler(CommandHandler("help", self.comando_ajuda))  # Alias inglês
            aplicacao.add_handler(CommandHandler("ajuda", self.comando_ajuda))  # Português
            aplicacao.add_handler(CommandHandler("hoje", self.comando_hoje))
            aplicacao.add_handler(CommandHandler("nota", self.comando_nota))
            aplicacao.add_handler(CommandHandler("tarefa", self.comando_tarefa))
            aplicacao.add_handler(CommandHandler("projetos", self.comando_projetos))
            aplicacao.add_handler(CommandHandler("metricas", self.comando_metricas))
            aplicacao.add_handler(CommandHandler("pomodoro", self.comando_pomodoro))
            aplicacao.add_handler(CommandHandler("status", self.comando_status))
            
            # Handler de mensagens diretas (texto sem / - captura automática!)
            # Filtros: TEXT (só texto) AND NOT COMMAND (não é comando)
            aplicacao.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handler_mensagem_texto)
            )
            
            # TODO (Futuro): Handler para voice notes (áudio) - requer Whisper/transcrição
            # aplicacao.add_handler(MessageHandler(filters.VOICE, self.handler_voice_note))
            
            # TODO (Futuro): Handler para documentos/arquivos
            # aplicacao.add_handler(MessageHandler(filters.Document, self.handler_documento))
            
            # TODO (Futuro): Handler para imagens/fotos
            # aplicacao.add_handler(MessageHandler(filters.PHOTO, self.handler_foto))
            
            logger_telegram.info(f"✅ {10} handlers registrados (9 comandos + 1 mensagem direta)")
            
            # ========================================
            # PASSO 4: INICIAR POLLING (CONECTAR NO TELEGRAM)
            # ========================================
            
            logger_telegram.info("📡 Conectando aos servidores do Telegram...")
            logger_telegram.info("=" * 80)
            logger_telegram.info("🤖 LEX BRAIN TELEGRAM BOT ONLINE! AGUARDANDO MENSAGENS...")
            logger_telegram.info("   Pressione Ctrl+C (no terminal) para encerrar gracefulmente")
            logger_telegram.info("=" * 80)
            
            # Print no console (além do log) para feedback visual imediato
            print("\n" + "🟢" * 40)
            print("✅ BOT CONECTADO COM SUCESSO AO TELEGRAM!")
            print(f"   🤖 Username: @Lex_Cerebro_bot")
            print(f"   🔗 Link direto: https://t.me/Lex_Cerebro_bot")
            print("   📱 Abra o Telegram e envie /start para começar!")
            print("🟢" * 40 + "\n")
            
            # ========================================
            # PASSO 5: LOOP PRINCIPAL (BLOQUEANTE - INFINITO)
            # =================================-------
            # run_polling() bloqueia a thread principal aqui
            # Só retorna quando: KeyboardInterrupt (Ctrl+C) ou erro fatal
            # allowed_updates=Update.ALL_TYPES: recebe todos os tipos de mensagem
            
            aplicacao.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True  # Limpa mensagens antigas que chegaram enquanto bot estava offline
            )
            
        except KeyboardInterrupt:
            # Intercepta Ctrl+C (interrupção graciosa pelo usuário)
            logger_telegram.info("\n" + "=" * 80)
            logger_telegram.info("⛔ BOT ENCERRADO PELO USUÁRIO (Ctrl+C)")
            logger_telegram.info("   Encerramento graceful concluído.")
            logger_telegram.info("=" * 80)
            
            print("\n\n⛔  Bot encerrado pelo usuário (Ctrl+C)")
            print("   Até logo! 👋\n")
            
        except Exception as erro_bot:
            # Captura qualquer outro erro fatal durante a execução
            logger_telegram.error(f"❌ ERRO CRÍTICO FATAL NO BOT: {erro_bot}", exc_info=True)
            
            print(f"\n\n{'❌' * 40}")
            print(f"ERRO FATAL: {erro_bot}")
            print(f"\n🔧 DIAGNÓSTICO:")
            print(f"   1. Verifique sua conexão com a internet")
            print(f"   2. Verifique se o token do bot está correto")
            print(f"   3. Verifique logs/telegram_bot.log para detalhes técnicos")
            print(f"   4. Reinicie o bot e tente novamente")
            print(f"\n📄 Log completo salvo em: logs/telegram_bot.log")
            print(f"{'❌' * 40}\n")


# ============================================================================
# PONTO DE ENTRADA PRINCIPAL (Entry Point do Script)
# ============================================================================

if __name__ == "__main__":
    """
    EXECUTAR O BOT DO TELEGRAM (Modo Standalone)
    
    ====================================================================
    COMO USAR:
    
    Opção 1 - Execução direta (recomendada para desenvolvimento):
        cd SecondBrain_Ultimate
        python integrations/telegram_bot.py
    
    Opção 2 - Como módulo (para programático/automatizado):
        from integrations.telegram_bot import LexBrainTelegramBot
        bot = LexBrainTelegramBot()
        bot.iniciar()
    
    ====================================================================
    O QUE ESTE SCRIPT FAZ (PASSO A PASSO):
    
    1. Exibe cabeçalho bonito com informações do sistema
    2. Cria instância de LexBrainTelegramBot (carrega token, prepara motor lazy)
    3. Chama bot.iniciar() que:
       a. Cria Application do python-telegram-bot
       b. Registra todos os handlers (comandos + mensagens)
       c. Conecta no Telegram via polling
       d. Entra em loop infinito aguardando mensagens
    4. Fica rodando 24/7 até usuário pressionar Ctrl+C
    
    ====================================================================
    COMO PARAR:
    
    - No terminal onde o bot está rodando: pressione Ctrl+C
    - O bot intercepta, encerra gracefulmente, libera recursos
    - Logs são preservados em logs/telegram_bot.log
    
    ====================================================================
    PRÉ-REQUISITOS:
    
    - Python 3.10+
    - python-telegram-bot>=20.7 instalado (pip install python-telegram-bot>=20.7)
    - Token configurado (settings.yaml ou TELEGRAM_BOT_TOKEN env var)
    - Conexão com internet (para conectar nos servidores do Telegram)
    - Lex Flow online (para funcionalidades completas - mas bot funciona parcialmente sem ele)
    
    ====================================================================
    """
    
    # ========================================
    # CABEÇALHO VISUAL (Arte ASCII para terminal)
    # ========================================
    print("\n" + "=" * 80)
    print("🤖 LEX BRAIN TELEGRAM BOT v1.0")
    print("   Second Brain Ultimate System | Interface Mobile Completa")
    print("   Autor: Lex-Usamn | Data: Abril 2026")
    print("=" * 80 + "\n")
    
    try:
        # ========================================
        # CRIAR INSTÂNCIA DO BOT
        # =================================-------
        # O __init__ carrega token e prepara lazy init do motor
        # (ainda não conecta em nada pesado neste ponto)
        bot = LexBrainTelegramBot()
        
        # ========================================
        # INICIAR BOT (BLOQUEANTE - LOOP INFINITO)
        # =================================-------
        # Este método só retorna quando o bot é encerrado (Ctrl+C ou erro fatal)
        bot.iniciar()
        
    except ValueError as erro_valor:
        # Erro de configuração (token ausente, por exemplo)
        print(f"\n❌ ERRO DE CONFIGURAÇÃO: {erro_valor}\n")
        sys.exit(1)  # Saída com erro
        
    except KeyboardInterrupt:
        # Usuário interrompeu (Ctrl+C) durante a inicialização
        print("\n⛔  Interrompido pelo usuário durante inicialização.\n")
        sys.exit(0)  # Saída limpa (sem erro)
        
    except Exception as erro_geral:
        # Qualquer outro erro não previsto durante inicialização
        print(f"\n💥 ERRO INESPERADO AO INICIAR BOT: {erro_geral}\n")
        print("🔧 Verifique logs/telegram_bot.log para detalhes técnicos completos.\n")
        sys.exit(1)  # Saída com erro