#!/usr/bin/env python3
"""
================================================================================
INICIADOR COMPLETO - LEX-BRAIN HYBRID v3.0 (CORRIGIDO!)
================================================================================

AUTOR: Mago-Usamn | DATA: 14/04/2026
VERSÃO: 3.0 (LLM-First Architecture)

CORREÇÕES DESTA VERSÃO:
✅ Função helper obter_classe_do_modulo() para extrair classes dos módulos
✅ Todos os __import__ agora funcionam corretamente
✅ CoreEngine, Scheduler, Bot, Orchestrator, ContextLoader todos OK!
================================================================================
"""

import sys
import os
import time
import logging
import threading

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/iniciador.log', encoding='utf-8')
    ]
)

logger = logging.getLogger("Iniciador")


# =============================================================================
# FUNÇÃO HELPER: Extrair classe de módulo (CORREÇÃO PRINCIPAL!)
# =============================================================================

def obter_classe_do_modulo(modulo, nome_classe):
    """
    Extrai uma classe de dentro de um módulo importado.
    
    Problema: __import__() retorna o MÓDULO, não a CLASSE.
    Solução: Usar getattr() para pegar a classe pelo nome.
    
    Args:
        modulo: O módulo importado via __import__
        nome_classe: Nome da classe dentro do módulo
        
    Returns:
        A classe solicitada
        
    Raises:
        Exception: Se a classe não for encontrada no módulo
    """
    classe = getattr(modulo, nome_classe, None)
    
    if classe is None:
        raise Exception(
            f"Classe '{nome_classe}' não encontrada no módulo '{modulo.__name__}'"
        )
    
    return classe


def main():
    tempo_inicio = time.time()
    
    print("\n" + "=" * 60)
    print("   LEX-BRAIN HYBRID v3.0 - INICIALIZAÇÃO COMPLETA")
    print("   Nova Arquitetura: LLM-FIRST (IA Conversacional Real)")
    print("=" * 60 + "\n")
    
    # ========================================
    # FASE 0: IMPORTAR MÓDULOS
    # ========================================
    print("=" * 60)
    print(" FASE 0: IMPORTANDO MÓDULOS...")
    print("=" * 60)
    
    modulos = {}
    
    lista_modulos = [
        ("CoreEngine", "engine.core_engine", "CoreEngine"),
        ("SchedulerSystem", "engine.scheduler", "SchedulerSystem"),
        ("LexBrainTelegramBot", "integrations.telegram_bot", "LexBrainTelegramBot"),
        ("BrainLLMOrchestrator", "engine.brain_llm_orchestrator", "BrainLLMOrchestrator"),
        ("BrainContextLoader", "engine.brain_context_loader", "BrainContextLoader"),
    ]
    
    for nome, caminho, nome_classe in lista_modulos:
        try:
            modulo = __import__(caminho, fromlist=[nome])
            classe = obter_classe_do_modulo(modulo, nome_classe)
            modulos[nome] = classe  # Armazena a CLASSE, não o módulo!
            print(f"   [OK] {nome}")
            
        except Exception as e:
            print(f"   [ERRO] {nome}: {e}")
            logger.error(f"Erro importando {nome}: {e}", exc_info=True)
    
    # ========================================
    # FASE 1: CORE ENGINE
    # ========================================
    print("\n" + "=" * 60)
    print(" FASE 1: CORE ENGINE")
    print("=" * 60)
    
    engine = None
    
    try:
        ClasseCore = modulos.get("CoreEngine")
        if not ClasseCore:
            raise Exception("CoreEngine não foi importado")
        
        engine = ClasseCore.obter_instancia()
        print("   [OK] CoreEngine criado")
        
        lexflow_status = "CONECTADO" if engine.lexflow else "ERRO"
        print(f"   [INFO] LexFlow: {lexflow_status}")
        
    except Exception as e:
        print(f"   [ERRO FATAL] {e}")
        logger.critical(f"Erro no CoreEngine: {e}", exc_info=True)
        sys.exit(1)
    
    # ========================================
    # FASE 2: SCHEDULER (BACKGROUND)
    # ========================================
    print("\n" + "=" * 60)
    print(" FASE 2: SCHEDULER SYSTEM (BACKGROUND)")
    print("=" * 60)
    
    try:
        ClasseScheduler = modulos.get("SchedulerSystem")
        
        if ClasseScheduler:
            scheduler = ClasseScheduler(engine)
            scheduler_thread = threading.Thread(
                target=scheduler.iniciar, daemon=True
            )
            scheduler_thread.start()
            print("   [OK] Scheduler RODANDO EM BACKGROUND!")
            time.sleep(0.5)
        else:
            print("   [AVISO] Scheduler não disponível (opcional)")
            
    except Exception as e:
        print(f"   [AVISO] Erro Scheduler (não fatal): {e}")
        logger.warning(f"Erro no Scheduler: {e}")
    
    # ========================================
    # FASE 2.5: BRAIN LLM ORCHESTRATOR v3.0 (CORRIGIDA!)
    # ========================================
    print("\n" + "=" * 60)
    print(" FASE 2.5: BRAIN LLM ORCHESTRATOR v3.0 (NOVO!)")
    print("=" * 60)
    
    orchestrator = None
    
    try:
        ClasseOrchestrator = modulos.get("BrainLLMOrchestrator")
        ClasseLoader = modulos.get("BrainContextLoader")
        
        if not ClasseOrchestrator:
            raise Exception("BrainLLMOrchestrator não importado")
        
        # --- Inicializar Context Loader ---
        print("   [1/3] Inicializando Context Loader (.md files)...")
        
        context_loader = None
        
        if ClasseLoader:
            context_loader = ClasseLoader()
            
            arquivos_ok = context_loader.verificar_arquivos_existem()
            for nome, existe in arquivos_ok.items():
                status = "[OK]" if existe else "[AUSENTE]"
                print(f"          {status} {nome.upper()}.md")
            
            print("   [2/3] Carregando contextos...")
            contextos = context_loader.carregar_todos(forcar_reload=True)
            
            for nome, conteudo in contextos.items():
                tamanho = len(conteudo)
                print(f"          {nome.upper()}: {tamanho} chars")
            
            from engine.brain_context_loader import definir_context_loader_global
            definir_context_loader_global(context_loader)
            
        else:
            print("   [AVISO] Context Loader não disponível")
        
        # --- Inicializar Orquestrador ---
        print("   [3/3] Conectando no LLM (GLM5/NVIDIA)...")
        
        orchestrator = ClasseOrchestrator()
        
        # 🔧 CORREÇÃO v3.0.1: Obter llm_client com fallback!
        llm_client = getattr(engine, 'llm_client', None)
        rag_system = getattr(engine, 'sistema_rag', None)
        lexflow_client = getattr(engine, 'lexflow', None)
        
        # 🔑 Se llm_client não existir no engine, criar um novo!
        if not llm_client:
            print("   [⚠️] engine.llm_client não disponível, criando novo...")
            
            # Tentar obter API key do ambiente
            nvidia_key = os.getenv("OPENAI_API_KEY") or os.getenv("NVIDIA_API_KEY")
            
            if nvidia_key:
                from engine.llm_client import LLMClient, ProvedorLLM, criar_llm_nvidia
                
                llm_client = criar_llm_nvidia(
                    api_key=nvidia_key,
                    modelo="z-ai/glm5"
                )
                print(f"   ✅ Novo LLMClient criado! (key: {nvidia[:8]}...{nvidia[-4:]})")
                
            else:
                print("   ❌ Nenhuma API key encontrada!")
                print("      Tente: export OPENAI_API_KEY='sua-chave'")
                print("      Ou: export NVIDIA_API_KEY='sua-chave'")
        
        sucesso = orchestrator.inicializar(
            llm_client=llm_client,
            rag_system=rag_system,
            lexflow_client=lexflow_client,
            context_loader=context_loader
        )
        
        if sucesso:
            from engine.brain_llm_orchestrator import definir_orchestrator_global
            definir_orchestrator_global(orchestrator)
            
            print("")
            print("   *** ORQUESTRADOR LLM PRONTO! ***")
            print("       Modo: LLM-FIRST (IA Conversacional Real)")
            
            stats = orchestrator.obter_estatisticas()
            
            print("")
            print("   ESTATÍSTICAS DO CÉREBRO:")
            print(f"       Versão: {stats['versao']}")
            print(f"       Modo: {stats['modo']}")
            print("       Recursos:")
            print(f"           - LLM (GLM5): {'SIM' if stats['recursos']['llm'] else 'NAO'}")
            print(f"           - RAG System: {'SIM' if stats['recursos']['rag'] else 'NAO'}")
            print(f"           - Lex Flow: {'SIM' if stats['recursos']['lexflow'] else 'NAO'}")
            
            if stats.get('contextos_carregados'):
                print("")
                print("       CONTEXTOS CARREGADOS:")
                for ctx_nome, ctx_tamanho in stats['contextos_carregados'].items():
                    print(f"           - {ctx_nome.upper()}: {ctx_tamanho} chars")
            
        else:
            print("   [ERRO] Falha ao inicializar orquestrador!")
            
    except Exception as e:
        print(f"   [ERRO] Falha no Orquestrador: {e}")
        logger.critical(f"Erro no Orquestrador v3.0: {e}", exc_info=True)
        print("")
        print("   [AVISO] O bot vai funcionar SEM IA conversacional (modo legacy)")
    
    tempo_parcial = time.time() - tempo_inicio
    print(f"\n   Tempo de boot (cérebros): {tempo_parcial:.2f} segundos")
    
    # ========================================
    # FASE 3: TELEGRAM BOT (MAIN THREAD)
    # ========================================
    print("\n" + "=" * 60)
    print(" FASE 3: TELEGRAM BOT (MAIN THREAD)")
    print("=" * 60)
    
    try:
        ClasseBot = modulos.get("LexBrainTelegramBot")
        
        if not ClasseBot:
            raise Exception("TelegramBot não foi importado")
        
        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        
        if not token:
            print("   [ERRO] TELEGRAM_BOT_TOKEN não encontrado!")
            print("   Execute: export TELEGRAM_BOT_TOKEN=seu_token_aqui")
            sys.exit(1)
        
        bot = ClasseBot()  # Agora funciona!
        
        if hasattr(bot, 'definir_engine'):
            bot.definir_engine(engine)
        
        # Injetar orquestrador v3.0
        if orchestrator and hasattr(bot, 'inicializar_orchestrator_v3'):
            bot.inicializar_orchestrator_v3(orchestrator)
            print("   [OK] Orquestrador v3.0 injetado no Bot!")
        else:
            print("   [AVISO] Orquestrador v3.0 não disponível")
        
        print("")
        print("+" * 60)
        print("")
        bot_username = getattr(bot, 'username', None) or 'seu_bot'
        print(f"   >>> @{bot_username} está ONLINE e OUVINDO!")
        print("")
        print("   BRAIN LLM ORCHESTRATOR v3.0 ATIVO!")
        print("      -> IA Conversacional HABILITADA (GLM5/NVIDIA)")
        print("      -> Contextos .md CARREGADOS (SOUL, USER, MEMORY, HEARTBEAT)")
        print("      -> Decisões INTELIGENTES (não mais regex!)")
        print("")
        print("+" * 60)
        print("")
        
        bot.iniciar()
        
    except KeyboardInterrupt:
        print("\n\n   Bot encerrado pelo usuário (Ctrl+C)")
        
    except Exception as e:
        print(f"\n   [ERRO FATAL] no Bot: {e}")
        logger.critical(f"Erro no TelegramBot: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()