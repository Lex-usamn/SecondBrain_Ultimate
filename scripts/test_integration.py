#!/usr/bin/env python3
"""
Teste de Integração End-to-End
===============================
Valida que Engine ↔ Lex Flow estão funcionando juntos

Execute: python test_integration.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.core_engine import CoreEngine


def test_basic_connection():
    """Teste 1: Conexão básica"""
    print("\n1️⃣  TESTE: Conexão Lex Flow")
    print("-" * 60)
    
    engine = CoreEngine()
    
    if not engine.start():
        print("❌ FALHA: Motor não iniciou!")
        return False
    
    status = engine.get_status()
    
    if status['lexflow'].get('authenticated'):
        print("✅ SUCESSO: Conectado e autenticado!")
        print(f"   Inbox: {status['lexflow']['inbox_count']} notas")
        return True
    else:
        print("❌ FALHA: Não autenticado!")
        return False


def test_capture():
    """Teste 2: Captura de ideia"""
    print("\n2️⃣  TESTE: Captura Rápida")
    print("-" * 60)
    
    engine = CoreEngine.get_instance()
    
    result = engine.capture(
        "Ideia teste de integração - " + 
        "Este texto deve aparecer no Lex Flow!",
        tags=["teste-integração", "automático"]
    )
    
    if result and result.get('id'):
        print(f"✅ SUCESSO: Nota criada! ID={result['id']}")
        print(f"   Título: {result.get('title')}")
        return True
    else:
        print("❌ FALHA: Nota não criada!")
        return False


def test_dashboard():
    """Teste 3: Dashboard"""
    print("\n3️⃣  TESTE: Dashboard/Métricas")
    print("-" * 60)
    
    engine = CoreEngine.get_instance()
    
    dash = engine.get_dashboard()
    
    if dash:
        print("✅ SUCESSO: Dashboard recebido!")
        print(f"   Chaves: {list(dash.keys())[:5]}...")  # Primeiras 5 chaves
        return True
    else:
        print("⚠️  Dashboard vazio (pode ser normal)")
        return None  # Não é falha crítica


def test_priorities():
    """Teste 4: Prioridades do dia"""
    print("\n4️⃣  TESTE: Prioridades")
    print("-" * 60)
    
    engine = CoreEngine.get_instance()
    
    prios = engine.get_priorities()
    
    if prios:
        print(f"✅ SUCESSO: {len(prios)} prioridades encontradas!")
        for i, p in enumerate(prios[:3], 1):
            print(f"   {i}. {p.get('title', '?')}")
        return True
    else:
        print("ℹ️  Nenhuma prioridade para hoje (normal se vazio)")
        return None


def main():
    """Executar todos os testes"""
    print("\n" + "=" * 70)
    print("🧪 TESTE DE INTEGRAÇÃO END-TO-END")
    print("   Engine v2.0 ↔ Lex Flow Client")
    print("=" * 70)
    
    results = {}
    
    # Executar testes
    results['connection'] = test_basic_connection()
    
    if results['connection']:  # Só continuar se conexão funcionou
        results['capture'] = test_capture()
        results['dashboard'] = test_dashboard()
        results['priorities'] = test_priorities()
    
    # Parar motor
    engine = CoreEngine.get_instance()
    engine.stop()
    
    # Resumo
    print("\n" + "=" * 70)
    print("📊 RESUMO DOS TESTES:")
    print("=" * 70)
    
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    
    for test_name, result in results.items():
        icon = "✅" if result is True else ("❌" if result is False else "⏭️ ")
        print(f"   {icon} {test_name}")
    
    print(f"\n   Total: {passed} passaram, {failed} falharam, {skipped} pulados")
    
    if failed == 0:
        print("\n🎉 TODOS OS TESTES CRÍTICOS PASSARAM!")
        print("   Sistema pronto para Fase 2 (Telegram Bot)!")
    else:
        print("\n⚠️  Alguns testes falharam. Verifique os logs.")
    
    print("=" * 70 + "\n")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())