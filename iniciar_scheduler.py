#!/usr/bin/env python3
"""
================================================================================
INICIALIZADOR COMPLETO DO LEX-BRAIN HYBRID (v1.1 - BRAIN MIDDLEWARE READY)
================================================================================

Arquitetura Final:
- MAIN THREAD:   Telegram Bot Polling (obrigatório!)
- BACKGROUND:    Scheduler System (APScheduler)
- 🆕 BRAIN:      Brain Middleware IA Assistente (conversação natural)

Autor: Lex-Usamn
Data: 12/04/2026
Versão: 1.1
Status: ✅ PRODUÇÃO
================================================================================
"""

import sys
import os
import signal
import time
from pathlib import Path

# ============================================================================
# CONFIGURAÇÃO DO PATH
# ============================================================================

diretorio_raiz = Path(__file__).parent
sys.path.insert(0, str(diretorio_raiz))

print("=" * 70)
print("🧠 LEX-BRAIN HYBRID v1.1 - INICIALIZAÇÃO COMPLETA")
print("   🆕 Brain Middleware (IA Assistente) INCLUÍDO!")
print("=" * 70)
print()

# ============================================================================
# IMPORTAÇÕES
# ============================================================================

print("📦 Importando módulos...")

try:
    from engine.core_engine import CoreEngine
    print("   ✅ CoreEngine")
except ImportError as e:
    print(f"   ❌ CoreEngine: {e}")
    sys.exit(1)

try:
    from engine.scheduler import SchedulerSystem, APSCHEDULER_AVAILABLE
    print("   ✅ SchedulerSystem")
except ImportError as e:
    print(f"   ❌ SchedulerSystem: {e}")
    sys.exit(1)

try:
    from integrations.telegram_bot import LexBrainTelegramBot
    print("   ✅ LexBrainTelegramBot")
    telegram_disponivel = True
except ImportError as e:
    print(f"   ⚠️ LexBrainTelegramBot: {e}")
    telegram_disponivel = False

# ============================================================================
# 🆕 BRAIN MIDDLEWARE (NOVO!)
# ============================================================================

brain_middleware_disponivel = False
brain_middleware_instance = None

try:
    from engine.brain_middleware import BrainMiddleware
    print("   ✅ BrainMiddleware (IA Assistente)")
    brain_middleware_disponivel = True
except ImportError as e:
    print(f"   ⚠️ BrainMiddleware: {e} (bot usará modo clássico)")
    brain_middleware_disponivel = False

print()

# ============================================================================
# VARIÁVEIS GLOBAIS
# ============================================================================

scheduler_instance = None
telegram_bot_instance = None
engine_instance = None


# ============================================================================
# FUNÇÃO DE INICIALIZAÇÃO (RODA UMA VEZ NO INÍCIO)
# ============================================================================

def inicializar_tudo():
    """
    Inicializa Engine + Scheduler + Brain Middleware.
    
    O Telegram Bot será iniciado DEPOIS na main thread.
    """
    global scheduler_instance, telegram_bot_instance, engine_instance
    global brain_middleware_instance
    
    # =========================================================================
    # FASE 1: CORE ENGINE
    # =========================================================================
    
    print("=" * 70)
    print("🚀 FASE 1: CORE ENGINE")
    print("=" * 70)
    
    try:
        engine_instance = CoreEngine.obter_instancia()
        print(f"✅ CoreEngine criado")
        
        if hasattr(engine_instance, 'lexflow') and engine_instance.lexflow:
            print(f"✅ Lex Flow: Conectado")
        else:
            print(f"⚠️ Lex Flow: Modo degradado")
            
    except Exception as e:
        print(f"❌ Erro fatal no CoreEngine: {e}")
        return False
    
    # =========================================================================
    # FASE 2: SCHEDULER SYSTEM (BACKGROUND)
    # =========================================================================
    
    print()
    print("=" * 70)
    print("⏰ FASE 2: SCHEDULER SYSTEM (BACKGROUND)")
    print("=" * 70)
    
    if not APSCHEDULER_AVAILABLE:
        print("❌ APScheduler não instalado!")
        return False
    
    try:
        scheduler_instance = SchedulerSystem(
            engine=engine_instance,
            timezone_str="America/Sao_Paulo"
        )
        print(f"✅ SchedulerSystem criado")
        
        # Inicializar e iniciar o scheduler (roda em background!)
        scheduler_instance.inicializar()
        scheduler_instance.iniciar()
        
        print(f"✅ Scheduler RODANDO EM BACKGROUND!")
        print(f"\n📋 Workflows Ativos:")
        for nome, config in scheduler_instance._workflows.items():
            if config.ativo:
                print(f"   ✅ {nome}: {config.tipo_trigger} {config.horario_execucao}")
        
    except Exception as e:
        print(f"❌ Erro no Scheduler: {e}")
        return False
    
    # =========================================================================
    # 🆕 FASE 2.5: BRAIN MIDDLEWARE (IA ASSISTENTE)
    # =========================================================================
    
    print()
    print("=" * 70)
    print("🧠 FASE 2.5: BRAIN MIDDLEWARE (IA ASSISTENTE PESSOAL)")
    print("=" * 70)
    
    if brain_middleware_disponivel:
        try:
            brain_middleware_instance = BrainMiddleware()
            
            sucesso_bm = brain_middleware_instance.inicializar()
            
            if sucesso_bm:
                print(f"✅ BrainMiddleware INICIALIZADO E PRONTO!")
                print(f"   🤖 IA: GLM5 (NVIDIA NIM)")
                print(f"   🔍 RAG: TF-IDF + Busca Híbrida")
                print(f"   💬 Conversação natural ATIVA!")
                
                # Injeta o Brain Middleware no bot (se disponível)
                if telegram_disponivel:
                    # O bot já vai pegar automaticamente via obter_brain_middleware()
                    # Mas podemos pré-inicializar aqui para garantir
                    pass
                
            else:
                print(f"⚠️ BrainMiddleware não conseguiu inicializar")
                print(f"   (Bot usará modo clássico: /comandos)")
                brain_middleware_instance = None
                
        except Exception as e:
            print(f"❌ Erro no BrainMiddleware: {e}")
            print(f"   (Bot usará modo clássico: /comandos)")
            brain_middleware_instance = None
    else:
        print(f"⏭️ BrainMiddleware não disponível (módulo não encontrado)")
        print(f"   (Bot usará modo clássico: /comandos)")
    
    # =========================================================================
    # FASE 3: TELEGRAM BOT (SÓ CRIA, NÃO INICIA AINDA!)
    # =========================================================================
    
    print()
    print("=" * 70)
    print("🤖 FASE 3: TELEGRAM BOT (PREPARAÇÃO)")
    print("=" * 70)
    
    if not telegram_disponivel:
        print("⚠️ Telegram não disponível")
        telegram_bot_instance = None
    else:
        try:
            telegram_bot_instance = LexBrainTelegramBot()
            
            # Conectar o bot ao scheduler (para envio de mensagens automáticas)
            scheduler_instance.telegram_bot = telegram_bot_instance
            
            status_brain = "🟢 ATIVO (Conversação Natural)" if brain_middleware_instance else "⚠️ Modo Clássico"
            
            print(f"✅ @Lex_Cerebro_bot criado e conectado ao Scheduler!")
            print(f"🧠 Brain Middleware: {status_brain}")
            print(f"💡 O bot será iniciado na main thread (próximo passo)")
            
        except Exception as e:
            print(f"⚠️ Erro ao criar bot: {e}")
            telegram_bot_instance = None
    
    return True


# ============================================================================
# PONTO DE ENTRADA PRINCIPAL
# ============================================================================

def main():
    """
    Função principal.
    
    Ordem de execução:
    1. Inicializar Engine + Scheduler + Brain MW (rápido)
    2. Iniciar Telegram Bot na MAIN THREAD (bloqueia aqui!)
    """
    inicio_total = time.time()
    
    print()
    print(f"🕐 Início: {time.strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # -------------------------------------------------------------------------
    # PASSO 1: Inicializar tudo (Engine + Scheduler + Brain MW)
    # -------------------------------------------------------------------------
    
    sucesso = inicializar_tudo()
    
    if not sucesso:
        print("\n❌ FALHA NA INICIALIZAÇÃO")
        sys.exit(1)
    
    # -------------------------------------------------------------------------
    # PASSO 2: Iniciar Telegram Bot na MAIN THREAD
    # -------------------------------------------------------------------------
    
    if telegram_bot_instance:
        print()
        print("=" * 70)
        print("🤖 INICIANDO TELEGRAM BOT (MAIN THREAD)")
        print("=" * 70)
        print()
        print("✅ TUDO PRONTO!")
        print()
        print("📱 @Lex_Cerebro_bot está ONLINE e OUVINDO!")
        print()
        
        if brain_middleware_instance:
            print("🧠 *BRAIN MIDDLEWARE ATIVO!*")
            print("   → Conversação natural HABILITADA!")
            print("   → 'Lex, anota isso' → ✅ Nota criada")
            print("   → 'Lex, lembra que tenho que...' → ✅ Tarefa")
            print("   → 'Lex, o que eu escrevi sobre...?' → 🔍 Busca RAG + IA")
            print()
            
            # ============================================================
            # 🔥🔥🔥 INJETAR INSTÂNCIA NO BOT (SINGLETON COMPARTILHADO)
            # ============================================================
            try:
                from integrations.telegram_bot import definir_brain_middleware_global
                
                definir_brain_middleware_global(brain_middleware_instance)
                print("🔗 Brain Middleware injetado no Telegram Bot (Singleton ativo)")
                
            except Exception as e_injecao:
                print(f"⚠️ Aviso: Não foi possível injetar Brain MW no bot: {e_injecao}")
                print("   O bot criará sua própria instância (lazy init)")
        
        else:
            print("⚠️ Brain Middleware não disponível (modo clássico)")
        
        print()
        print("   → Envie /start para começar")
        print("   → Comandos: /ajuda /status /projetos /hoje /nota /tarefa")
        print()
        
        print("   → Envie /start para começar")
        print("   → Comandos: /ajuda /status /projetos /hoje /nota /tarefa")
        print()
        print("⏰ Workflows automáticos ativos:")
        print("   • Morning Briefing:    06:00 (Seg-Sex)")
        print("   • Midday Check-in:     12:00 (Seg-Sex)")
        print("   • Evening Reflection:  20:00 (Todos dias)")
        print("   • TELOS Review:        Domingo 20:00")
        print("   • Heartbeat:           A cada 30 min")
        print()
        print("-" * 70)
        print("⌨️  Pressione Ctrl+C para encerrar gracefulmente")
        print("-" * 70)
        
        # Calcular tempo de boot
        tempo_boot = time.time() - inicio_total
        print(f"\n⏱️ Tempo de boot: {tempo_boot:.2f} segundos")
        print()
        
        # ✅ INICIAR O POLLING DO TELEGRAM NA MAIN THREAD!
        try:
            telegram_bot_instance.iniciar()  # ← BLOQUEIA AQUI!
        except KeyboardInterrupt:
            print("\n\n⛔ Ctrl+C recebido...")
        except Exception as e:
            print(f"\n❌ Erro no Telegram Bot: {e}")
    
    else:
        # Sem Telegram - só mostrar status do scheduler
        print()
        print("=" * 70)
        print("⚠️ MODO: SCHEDULER SEM TELEGRAM")
        print("=" * 70)
        print("\n✅ Scheduler rodando em background!")
        print("⌨️  Pressione Ctrl+C para encerrar")
        
        try:
            while True:
                time.sleep(60)
                hora = time.strftime("%H:%M:%S")
                total = sum(w.contador_execucoes for w in scheduler_instance._workflows.values())
                print(f"[{hora}] 💓 Scheduler ativo | Execuções: {total}")
        except KeyboardInterrupt:
            print("\n\n⛔ Ctrl+C recebido...")
    
    # -------------------------------------------------------------------------
    # DESLIGAMENTO
    # -------------------------------------------------------------------------
    
    print()
    print("=" * 70)
    print("⛔ DESLIGANDO SISTEMA")
    print("=" * 70)
    
    if scheduler_instance:
        try:
            scheduler_instance.parar()
            print("✅ Scheduler parado")
        except Exception as e:
            print(f"⚠️ Erro ao parar scheduler: {e}")
    
    tempo_total = time.time() - inicio_total
    horas = int(tempo_total // 3600)
    minutos = int((tempo_total % 3600) // 60)
    
    print()
    print(f"⏱️ Tempo total de execução: {horas}h {minutos}m")
    print("👋 Até logo, Lex! 🧠💤")
    print()


# ============================================================================
# EXECUÇÃO
# ============================================================================

if __name__ == "__main__":
    main()