#!/usr/bin/env python3
"""Teste rápido do Brain Middleware"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("🧪 TESTE BRAIN MIDDLEWARE")
print("=" * 60)

# Teste 1: Importar tipos
print("\n[TESTE 1] Importando brain_types...")
try:
    from engine.brain_types import (
        BrainMiddleware, RespostaBrain, EstadoConversa,
        NOME_ASSISTENTE, TipoIntencao, IntencaoDetectada,
        ContextoConversa, PrioridadeTarefa, converter_prazo
    )
    print(f"   ✅ brain_types OK | Assistente: {NOME_ASSISTENTE}")
except ImportError as e:
    print(f"   ❌ ERRO brain_types: {e}")
    sys.exit(1)

# Teste 2: Importar intencao
print("\n[TESTE 2] Importando brain_intencao...")
try:
    from engine.brain_intencao import (
        NormalizadorMensagem, DetectorIntencao, 
        GeradorClarificacao, PalavrasChave, ExtratorEntidades
    )
    print(f"   ✅ brain_intencao OK")
except ImportError as e:
    print(f"   ❌ ERRO brain_intencao: {e}")
    sys.exit(1)

# Teste 3: Importar acoes
print("\n[TESTE 3] Importando brain_acoes...")
try:
    from engine.brain_acoes import ExecutorAcoes
    print(f"   ✅ brain_acoes OK")
except ImportError as e:
    print(f"   ❌ ERRO brain_acoes: {e}")
    sys.exit(1)

# Teste 4: Importar orquestrador
print("\n[TESTE 4] Importando brain_middleware...")
try:
    from engine.brain_middleware import BrainMiddleware
    print(f"   ✅ brain_middleware OK")
except ImportError as e:
    print(f"   ❌ ERRO brain_middleware: {e}")
    sys.exit(1)

# Teste 5: Inicializar
print("\n[TESTE5] Inicializando BrainMiddleware...")
try:
    brain = BrainMiddleware()
    sucesso = brain.inicializar()
    if sucesso:
        print(f"   ✅ BrainMiddleware INICIALIZADO!")
        print(f"   🤖 LLM: {type(brain._llm).__name__}")
        print(f"   🔍 RAG: {type(brain._rag).__name__}")
        print(f"   🌐 LexFlow: {type(brain._lexflow).__name__}")
        
        # Testar processamento
        print("\n[TESTE6] Processando mensagem...")
        resultado = brain.processar("Mago, lembra de corte pra quinta", 
                                   {"usuario_id": 12345})
        print(f"   ✅ Processado!")
        print(f"   📝 Ação: {resultado.acao_executada}")
        print(f"   ❓ Clarificação: {resultado.requer_clarificacao}")
        print(f"   💬 Resposta: {resultado.resposta_ia[:100]}...")
    else:
        print(f"   ❌ Falha na inicialização!")
except Exception as e:
    print(f"   ❌ ERRO: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("🧪 FIM DO TESTE")
