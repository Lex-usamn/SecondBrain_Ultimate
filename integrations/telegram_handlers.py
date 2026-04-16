"""
================================================================================
LEX BRAIN TELEGRAM BOT - Handlers de Comandos v2.1
================================================================================

Contém TODOS os handlers de comandos do bot (/start, /hoje, /nota, /tarefa,
/projetos, /metricas, /pomodoro, /status, /ajuda).

Separado do arquivo principal para:
- Manter código modular e organizado
- Facilitar manutenção
- Permitir testes unitários isolados

AUTOR: Lex-Usamn | DATA: 12/04/2026
STATUS: ✅ Produção (Brain Middleware v2.1 Integrado)
================================================================================
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List, Any

from telegram import Update
from telegram.ext import ContextTypes, CallbackContext

# Utilitários compartilhados
from integrations.telegram_utils import (
    logger_telegram,
    EmojiSystema as E,
    formatar_tempo,
    formatar_data_extensa,
    truncar_texto,
    obter_emoji_prioridade,
    normalizar_prioridade,
    mensagem_erro_generica,
    mensagem_sucesso_nota,
    mensagem_sucesso_tarefa,
    MENSAGEM_BOAS_VINDAS,
    MENSAGEM_AJUDA,
    MAPEAMENTO_PRIORIDADE_API
)

# Core Engine (Singleton)
from engine.core_engine import CoreEngine


class TelegramHandlers:
    """
    Coleção de handlers de comandos para o Lex Brain Telegram Bot.
    
    Esta classe contém todos os métodos que respondem a comandos do Telegram.
    Cada método é um handler independente que pode ser registrado no Application.
    
    Padrão seguido:
    1. Logar recebimento do comando
    2. Executar lógica de negócio
    3. Responder ao usuário
    4. Tratar erros gracefulmente (nunca crasha)
    """
    
    def __init__(self, bot_instance: 'LexBrainTelegramBot'):
        """
        Inicializa handlers com referência ao bot principal.
        
        Args:
            bot_instance: Instância do LexBrainTelegramBot (para acessar motor, etc.)
        """
        self.bot = bot_instance
    
    # =========================================================================
    # COMANDO /start - Boas-vindas
    # =========================================================================
    
    async def comando_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler do comando /start - Boas-vindas e status inicial."""
        
        usuario_nome = update.effective_user.first_name or "Usuário"
        usuario_id = update.effective_user.id
        username = update.effective_user.username or "sem_username"
        
        logger_telegram.info(
            f"💬 [/start] Usuário: {usuario_nome} (ID: {usuario_id}, @{username})"
        )
        
        try:
            # Tentar health check rápido
            try:
                saude = self.bot.motor.health_check()
                status_texto = saude.get('detalhes', '✅ Sistema operacional')
                emoji_status = "🟢"
            except Exception:
                status_texto = "⚠️ Motor não inicializado (iniciará sob demanda)"
                emoji_status = "🟡"
            
            # Montar mensagem personalizada
            mensagem = MENSAGEM_BOAS_VINDAS.format(
                nome=usuario_nome,
                status=f"{emoji_status} {status_texto}"
            )
            
            await update.message.reply_text(mensagem, parse_mode='Markdown')
            logger_telegram.info(f"✅ [/start] Enviado para {usuario_nome}")
            
        except Exception as erro:
            logger_telegram.error(f"❌ [/start] Erro: {erro}", exc_info=True)
            await update.message.reply_text(
                "❌ Desculpe, ocorreu um erro ao inicializar. Tente novamente."
            )
    
    # =========================================================================
    # COMANDO /hoje - Morning Briefing (Prioridades do Dia)
    # =========================================================================
    
    async def comando_hoje(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler do comando /hoje - Exibe prioridades do dia."""
        
        usuario_nome = update.effective_user.first_name or "Usuário"
        logger_telegram.info(f"💬 [/hoje] Solicitado por {usuario_nome}")
        
        try:
            prioridades = self.bot.motor.obter_prioridades()
            resumo = self.bot.motor.resumo_do_dia()
            estatisticas = resumo.get('estatisticas', {}) if resumo else {}
            
            # Cabeçalho
            mensagem = f"""
📋 *PRIORIDADES DE HOJE*
📅 {formatar_data_extensa()}
━━━━━━━━━━━━━━━━━━━━━
"""
            
            # Listar prioridades
            if prioridades:
                for idx, tarefa in enumerate(prioridades[:5], start=1):
                    titulo = tarefa.get('title', 'Sem título')
                    projeto = tarefa.get('project_title', 'Sem projeto')
                    emoji_p = obter_emoji_prioridade(tarefa.get('priority', 'medium'))
                    
                    mensagem += f"{idx}. {emoji_p} *{titulo}*\n"
                    mensagem += f"   📂 Projeto: {projeto}\n\n"
            else:
                mensagem += (
                    "✨ *Nenhuma prioridade definida!*\n\n"
                    "   🎉 Aproveite! Ou use `/nota` para planejar.\n\n"
                )
            
            # Estatísticas
            if estatisticas:
                pomodoros = estatisticas.get('pomodoros', 0)
                notas = estatisticas.get('quickNotes', 0)
                tarefas_feitas = estatisticas.get('tasksCompleted', 0)
                
                mensagem += f"""━━━━━━━━━━━━━━━━━━━━━
📊 *Resumo:*
• 🍅 Pomodoros: {pomodoros}
• 📝 Notas: {notas}
• ✅ Concluídas: {tarefas_feitas}
"""
            
            # Motivação
            if estatisticas and estatisticas.get('tasksCompleted', 0) >= 5:
                mensagem += "\n🔥 *Incendiário! Continue assim!*"
            elif estatisticas and estatisticas.get('tasksCompleted', 0) >= 3:
                mensagem += "\n💪 *Bom progresso! Vamos finalizar mais!"
            else:
                mensagem += "\n☀️ *Bom dia! Vamos conquistar juntos!*"
            
            await update.message.reply_text(mensagem, parse_mode='Markdown')
            logger_telegram.info(f"✅ [/hoje] Enviado ({len(prioridades) if prioridades else 0} itens)")
            
        except Exception as erro:
            logger_telegram.error(f"❌ [/hoje] Erro: {erro}", exc_info=True)
            await update.message.reply_text(
                "❌ *Erro ao buscar prioridades*\n\nTente novamente em instantes.",
                parse_mode='Markdown'
            )
    
    # =========================================================================
    # COMANDO /nota - Captura Rápida de Ideias
    # =========================================================================
    
    async def comando_nota(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler do comando /nota - Captura ideia/nota rapidamente."""
        
        usuario_nome = update.effective_user.first_name or "Usuário"
        logger_telegram.info(f"💬 [/nota] Solicitado por {usuario_nome}")
        
        try:
            # Extrair texto
            texto_completo = ' '.join(context.args) if context.args else ''
            
            if not texto_completo.strip():
                await update.message.reply_text(
                    "❌ *Uso incorreto*\n\n"
                    "`/nota <texto da nota>`\n\n"
                    "Exemplos:\n"
                    "`/nota Ideia incrível para vídeo`\n"
                    "`/nota Comprar microfone --tags compras urgente`",
                    parse_mode='Markdown'
                )
                return
            
            # Parsear --tags
            tags = []
            idea_texto = texto_completo
            
            if '--tags' in texto_completo:
                partes = texto_completo.split('--tags', 1)
                idea_texto = partes[0].strip()
                tags_str = partes[1].strip() if len(partes) > 1 else ''
                tags = [t.strip() for t in tags_str.split() if t.strip()]
                logger_telegram.info(f"   Tags detectadas: {tags}")
            
            # Feedback visual
            msg_espera = await update.message.reply_text(
                f"⏳ *Capturando...* 📝\n\nEnviando para Lex Flow...",
                parse_mode='Markdown'
            )
            
            # Executar captura
            resultado = self.bot.motor.capturar(
                idea=idea_texto,
                tags=tags if tags else None
            )
            
            # Processar resultado
            if resultado and resultado.get('id'):
                resposta = mensagem_sucesso_nota(resultado, idea_texto)
                await msg_espera.edit_text(resposta, parse_mode='Markdown')
                logger_telegram.info(f"✅ [/nota] Nota ID={resultado.get('id')} criada")
            else:
                await msg_espera.edit_text(
                    "❌ *Falha ao capturar nota*\n\n"
                    "Lex Flow pode estar indisponível. Tente novamente.",
                    parse_mode='Markdown'
                )
                logger_telegram.warning(f"⚠️ [/nota] Falha. Resultado: {resultado}")
                
        except Exception as erro:
            logger_telegram.error(f"❌ [/nota] Erro: {erro}", exc_info=True)
            await update.message.reply_text(*mensagem_erro_generica(erro, "captura de nota"))
    
    # =========================================================================
    # COMANDO /tarefa - Criar Tarefa em Projeto
    # =========================================================================
    
    async def comando_tarefa(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler do comando /tarefa v1.4 - Criação de tarefas completa."""
        
        usuario_nome = update.effective_user.first_name or "Usuário"
        logger_telegram.info(f"💬 [/tarefa] Solicitado por {usuario_nome}")
        
        try:
            # Extrair texto
            texto_completo = ' '.join(context.args) if context.args else ''
            
            if not texto_completo.strip():
                await update.message.reply_text(
                    "❌ Uso incorreto\n\n"
                    "Formatos:\n"
                    "/tarefa <texto>\n"
                    "/tarefa <texto> --projeto <ID|NOME>\n"
                    "/tarefa <texto> --prioridade <nivel>\n\n"
                    "Prioridades: baixa, media, alta, urgente"
                )
                return
            
            # Inicializar motor
            motor = CoreEngine.obter_instancia()
            
            if not motor.lexflow:
                await update.message.reply_text("❌ Lex Flow indisponível. Tente novamente.")
                return
            
            # Parsear argumentos
            titulo_tarefa = texto_completo
            projeto_id = None
            prioridade = "medium"
            projeto_nome_busca = None
            
            # --- Parsear --projeto ---
            if '--projeto' in texto_completo:
                partes_proj = texto_completo.split('--projeto', 1)
                titulo_tarefa = partes_proj[0].strip()
                resto = partes_proj[1].strip() if len(partes_proj) > 1 else ''
                
                # Pegar tudo até próximo -- ou fim (suporta nomes com espaço!)
                if '--prioridade' in resto:
                    proj_identificador = resto.split('--prioridade')[0].strip()
                else:
                    proj_identificador = resto.strip()
                
                if proj_identificador:
                    try:
                        projeto_id = int(proj_identificador)
                        logger_telegram.info(f"   ✅ Projeto ID numérico: {projeto_id}")
                    except ValueError:
                        projeto_nome_busca = proj_identificador
                        logger_telegram.info(f"   🔍 Buscando projeto: '{projeto_nome_busca}'")
            
            # --- Parsear --prioridade ---
            if '--prioridade' in texto_completo:
                partes_pri = texto_completo.split('--prioridade', 1)
                parte_apos = partes_pri[1].strip() if len(partes_pri) > 1 else ''
                pri_str = parte_apos.split()[0] if parte_apos.split() else 'medium'
                prioridade = normalizar_prioridade(pri_str)
                logger_telegram.info(f"   📊 Prioridade: {prioridade}")
            
            # --- Resolver projeto por nome ---
            if projeto_nome_busca and not projeto_id:
                logger_telegram.info(f"   🔍 Buscando projeto: '{projeto_nome_busca}'")
                
                try:
                    projetos = motor.lexflow.get_projects()
                    
                    if projetos:
                        projeto_encontrado = None
                        for p in projetos:
                            nome_p = p.get('name', '').lower().strip()
                            busca_l = projeto_nome_busca.lower().strip()
                            
                            if busca_l == nome_p or busca_l in nome_p or nome_p in busca_l:
                                projeto_encontrado = p
                                break
                        
                        if projeto_encontrado:
                            projeto_id = projeto_encontrado.get('id')
                            nome_real = projeto_encontrado.get('name', '?')
                            logger_telegram.info(f"   ✅ Encontrado: '{nome_real}' (ID: {projeto_id})")
                        else:
                            nomes = [p.get('name', '?') for p in projetos[:10]]
                            lista = "\n".join([f"• {n}" for n in nomes])
                            
                            await update.message.reply_text(
                                f"❌ Projeto '{projeto_nome_busca}' não encontrado\n\n"
                                f"Disponíveis:\n{lista}\n\n"
                                f"Use ID numérico ou nome exato."
                            )
                            return
                    
                except Exception as e:
                    logger_telegram.error(f"   ❌ Erro ao buscar projetos: {e}")
            
            # Default: Inbox se sem projeto
            if not projeto_id:
                logger_telegram.info("   📥 Sem projeto → Inbox (ID=1)")
                projeto_id = 1  # Inbox
            
            # Log finais
            logger_telegram.info(f"   🎯 DADOS: Título='{titulo_tarefa}', Projeto={projeto_id}, Pri={prioridade}")
            
            # Criar tarefa (múltiplas tentativas de assinatura)
            resultado = None
            erros = []
            
            # Tentativa 1: Parâmetros nomeados
            try:
                logger_telegram.info("   🔄 T1: add_task(project_id, title, priority)")
                resultado = motor.lexflow.add_task(
                    project_id=projeto_id,
                    title=titulo_tarefa,
                    priority=prioridade
                )
            except Exception as e1:
                erros.append(f"T1: {e1}")
                # Tentativa 2: Posicionais
                try:
                    logger_telegram.info("   🔄 T2: add_task(title, project_id, priority)")
                    resultado = motor.lexflow.add_task(titulo_tarefa, projeto_id, prioridade)
                except Exception as e2:
                    erros.append(f"T2: {e2}")
                    # Tentativa 3: title + project_id
                    try:
                        logger_telegram.info("   🔄 T3: add_task(title, project_id)")
                        resultado = motor.lexflow.add_task(titulo_tarefa, projeto_id)
                    except Exception as e3:
                        erros.append(f"T3: {e3}")
                        # Tentativa 4: Só title
                        try:
                            logger_telegram.info("   🔄 T4: add_task(title)")
                            resultado = motor.lexflow.add_task(titulo_tarefa)
                        except Exception as e4:
                            erros.append(f"T4: {e4}")
            
            # Processar resultado
            if resultado:
                task_id = None
                
                if isinstance(resultado, dict):
                    if 'task' in resultado and isinstance(resultado['task'], dict):
                        task_obj = resultado['task']
                        task_id = task_obj.get('id') or task_obj.get('_id') or task_obj.get('taskId')
                    else:
                        for campo in ['id', 'task_id', '_id', 'taskId']:
                            if campo in resultado:
                                task_id = resultado[campo]
                                break
                        if not task_id:
                            task_id = '?'
                elif isinstance(resultado, (int, str)):
                    task_id = resultado
                else:
                    task_id = str(resultado)[:20]
                
                resposta = mensagem_sucesso_tarefa(task_id, titulo_tarefa, prioridade, projeto_id)
                await update.message.reply_text(resposta)
                logger_telegram.info(f"✅ [/tarefa] Criada ID={task_id}")
            
            else:
                msg_erro = "❌ Falha ao criar tarefa\n\nErros:\n"
                for e in erros:
                    msg_erro += f"• {e}\n"
                msg_erro += "\nUse /projetos para ver IDs válidos"
                
                await update.message.reply_text(msg_erro)
                logger_telegram.error(f"❌ [/tarefa] Falha total: {erros}")
            
        except Exception as e:
            logger_telegram.error(f"❌ [/tarefa] ERRO CRÍTICO: {type(e).__name__}: {e}", exc_info=True)
            await update.message.reply_text("⚠️ Erro inesperado no /tarefa")
    
    # =========================================================================
    # COMANDO /projetos - Listar Projetos Ativos
    # =========================================================================
    
    async def comando_projetos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler do comando /projetos - Lista projetos ativos."""
        
        usuario_nome = update.effective_user.first_name or "Usuário"
        logger_telegram.info(f"💬 [/projetos] Solicitado por {usuario_nome}")
        
        try:
            projetos = self.bot.motor.lexflow.get_projects()
            
            if not projetos:
                await update.message.reply_text(
                    "📭 *Nenhum projeto encontrado!*\n\n"
                    "Acesse https://flow.lex-usamn.com.br para criar.\n\n"
                    "Depois use `/projetos` novamente.",
                    parse_mode='Markdown'
                )
                return
            
            # Montar lista
            mensagem = f"📂 *PROJETOS ATIVOS* ({len(projetos)})\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            for idx, proj in enumerate(projetos, start=1):
                proj_id = proj.get('id', '?')
                proj_nome = proj.get('name', 'Sem nome')
                proj_desc = proj.get('description', '')
                
                mensagem += f"{idx}. *{proj_nome}* `(ID: {proj_id})`\n"
                
                if proj_desc:
                    desc_curta = truncar_texto(proj_desc, 80)
                    mensagem += f"   💡 {desc_curta}\n"
                mensagem += "\n"
            
            mensagem += (
                "💡 *Dica:* Use `/tarefa Título --projeto ID`\n"
                "   Exemplo: `/tarefa Editar vídeo --projeto 5`"
            )
            
            # Verificar limite Telegram (4096 chars)
            if len(mensagem) > 4000:
                mensagem = mensagem[:3970] + "\n\n...(truncado)"
            
            await update.message.reply_text(mensagem, parse_mode='Markdown')
            logger_telegram.info(f"✅ [/projetos] Listados {len(projetos)} projetos")
            
        except Exception as erro:
            logger_telegram.error(f"❌ [/projetos] Erro: {erro}", exc_info=True)
            await update.message.reply_text(
                "❌ *Erro ao buscar projetos*\n\nTente novamente.",
                parse_mode='Markdown'
            )
    
    # =========================================================================
    # COMANDO /metricas - Painel de Métricas
    # =========================================================================
    
    async def comando_metricas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler do comando /metricas - Painel de produtividade."""
        
        usuario_nome = update.effective_user.first_name or "Usuário"
        logger_telegram.info(f"💬 [/metricas] Solicitado por {usuario_nome}")
        
        try:
            stats = self.bot.motor.obter_today_stats()
            
            if not stats:
                await update.message.reply_text(
                    "📊 *Métricas Indisponíveis*\n\n"
                    "Dados insuficientes. Comece a usar `/tarefa` ou `/nota`!",
                    parse_mode='Markdown'
                )
                return
            
            # Extrair métricas
            tarefas = stats.get('tarefas_concluidas', 0)
            notas = stats.get('notas_capturadas', 0)
            pomodoros = stats.get('pomodoros', 0)
            projetos_atv = stats.get('projetos_ativos', 0)
            taxa = stats.get('taxa_conclusao', 'N/A')
            horas_foco = stats.get('horas_foco', 'N/A')
            
            data_atual = datetime.now().strftime('%d/%m/%Y')
            
            mensagem = f"""
📊 *PAINEL DE MÉTRICAS*
📅 {data_atual}
━━━━━━━━━━━━━━━━━━━━━

✅ *Tarefas Concluídas:* {tarefas}
📝 *Notas Capturadas:* {notas}
🍅 *Pomodoros:* {pomodoros} ({(pomodoros * 25) // 60}h {(pomodoros * 25) % 60}m de foco)
📁 *Projetos Ativos:* {projetos_atv}

━━━━━━━━━━━━━━━━━━━━━

📈 *Taxa de Conclusão:* {taxa}%
⚡ *Horas de Foco:* {horas_foco}h
"""
            
            # Motivação
            if tarefas >= 5:
                mensagem += "\n🔥 *INCENDIÁRIO!* Performance de alto nível!"
            elif tarefas >= 3:
                mensagem += "\n💪 *BOM PROGRESSO!* No caminho certo!"
            elif tarefas >= 1:
                mensagem += "\n👍 *BOM INÍCIO!* Vamos para a próxima?"
            else:
                mensagem += "\n🌱 *HORA DE COMEÇAR!* Use `/tarefa`!"
            
            await update.message.reply_text(mensagem, parse_mode='Markdown')
            logger_telegram.info(f"✅ [/metricas] Enviado (Tarefas: {tarefas})")
            
        except Exception as erro:
            logger_telegram.error(f"❌ [/metricas] Erro: {erro}", exc_info=True)
            await update.message.reply_text(
                "❌ *Erro ao calcular métricas*", parse_mode='Markdown'
            )
    
    # =========================================================================
    # COMANDO /pomodoro - Controle de Sessões de Foco
    # =========================================================================
    
    async def comando_pomodoro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler do comando /pomodoro - Controle Pomodoro."""
        
        usuario_nome = update.effective_user.first_name or "Usuário"
        acao = ' '.join(context.args).lower().strip() if context.args else ''
        
        logger_telegram.info(f"💬 [/pomodoro] Ação: '{acao}' por {usuario_nome}")
        
        try:
            if acao in ['iniciar', 'start', 'começar']:
                resposta = """🍅 *POMODORO INICIADO!*

⏱️ *Timer:* 25 minutos
🎯 *Modo:* FOCO TOTAL

━━━━━━━━━━━━━━━━━━━━━
📋 *Durante esta sessão:*
• Silencie o celular
• Feche abas desnecessárias
• Foque em UMA tarefa só

*Dica:* Eu te aviso quando acabar!
*Status:* 🟢 *Em andamento...*"""
            
            elif acao in ['parar', 'stop', 'pause', 'pausar']:
                resposta = """⏸️ *POMODORO PAUSADO*

Sessão interrompida.

Quando voltar:
`/pomodoro iniciar` → Retomar
`/pomodoro logar` → Registrar como feito

💪 Pausas estratégicas são parte do processo!"""
            
            elif acao in ['logar', 'log', 'feito', 'done', 'concluir', 'completar']:
                resultado = self.bot.motor.capturar(
                    idea="✅ Sessão Pomodoro Concluída (25min de foco)",
                    tags=["pomodoro", "produtividade", "foco"]
                )
                
                if resultado and resultado.get('id'):
                    resposta = f"""✅ *POMODORO REGISTRADO!*

🍅 +1 sessão de foco!
🆔 ID: `{resultado.get('id')}`

☕ *Hora da pausa!* (5 minutos)

Quando pronto: `/pomodoro iniciar`"""
                else:
                    resposta = """⚠️ *POMODORO RECEBIDO*

Registramos sua sessão!
☕ *Pausa merecida!*"""
            
            else:
                # Menu principal
                try:
                    stats = self.bot.motor.obter_today_stats()
                    pomos_hoje = stats.get('pomodoros', 0) if stats else 0
                except Exception:
                    pomos_hoje = '?'
                
                resposta = f"""🍅 *CONTROLE POMODORO*

Escolha uma ação:

`/pomodoro iniciar` → Começar 25min 🔥
`/pomodoro parar` → Pausar ⏸️
`/pomodoro logar` → Registrar como feito ✅

━━━━━━━━━━━━━━━━━━━━━
📊 *Hoje:* {pomos_hoje} sessões
🎯 *Meta diária:* 8 pomodoros (4h)

*Técnica:* 25min foco + 5min pausa"""
            
            await update.message.reply_text(resposta, parse_mode='Markdown')
            logger_telegram.info(f"✅ [/pomodoro] Ação '{acao}' processada")
            
        except Exception as erro:
            logger_telegram.error(f"❌ [/pomodoro] Erro: {erro}", exc_info=True)
            await update.message.reply_text("❌ *Erro no Pomodoro*", parse_mode='Markdown')
    
    # =========================================================================
    # COMANDO /status - Health Check Completo
    # =========================================================================
    
    async def comando_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler do comando /status - Diagnóstico completo do sistema."""
        
        usuario_nome = update.effective_user.first_name or "Usuário"
        logger_telegram.info(f"💬 [/status] Solicitado por {usuario_nome}")
        
        try:
            status = self.bot.motor.obter_status_completo()
            
            motor_st = status.get('motor', {})
            lex_st = status.get('lex_flow', {})
            
            uptime = formatar_tempo(motor_st.get('uptime_segundos', 0))
            motor_rodando = "🟢 *ATIVO*" if motor_st.get('rodando') else "🔴 *PARADO*"
            lex_ok = "🟢 *Conectado*" if lex_st.get('autenticado') else "🔴 *Desconectado*"
            
            mensagem = f"""
🏥 *HEALTH CHECK COMPLETO*
━━━━━━━━━━━━━━━━━━━━━

🧠 *Motor Principal:* {motor_rodando}
⏱️ *Uptime:* {uptime}
📊 *Versão:* {motor_st.get('versao', 'N/A')}
🌐 *Ambiente:* {motor_st.get('ambiente', 'N/A')}

📡 *Lex Flow:* {lex_ok}
📥 *Notas Inbox:* {lex_st.get('quantidade_notas_inbox', '?')}
📂 *Projetos Ativos:* {lex_st.get('quantidade_projetos_ativos', '?')}
🏷️ *Áreas:* {lex_st.get('quantidade_areas', '?')}

━━━━━━━━━━━━━━━━━━━━━

📈 *Operação Hoje:*
• 📝 Capturas: {motor_st.get('capturas_hoje', 0)}
• ⚙️ Processamentos: {motor_st.get('processamentos_hoje', 0)}
• ❌ Erros: {motor_st.get('erros_totais', 0)}

🕐 *Verificado:* {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
            
            await update.message.reply_text(mensagem, parse_mode='Markdown')
            logger_telegram.info(f"✅ [/status] Enviado")
            
        except Exception as erro:
            logger_telegram.error(f"❌ [/status] Erro: {erro}", exc_info=True)
            await update.message.reply_text(
                "❌ *Erro ao obter status*", parse_mode='Markdown'
            )
    
    # =========================================================================
    # COMANDO /ajuda - Documentação Completa
    # =========================================================================
    
    async def comando_ajuda(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler do comando /ajuda - Manual de comandos."""
        
        logger_telegram.info("💬 [/ajuda] Manual solicitado")
        
        await update.message.reply_text(MENSAGEM_AJUDA, parse_mode='Markdown')
        logger_telegram.info("✅ [/ajuda] Enviado")