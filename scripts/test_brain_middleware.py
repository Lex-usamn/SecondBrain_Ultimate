"""
============================================
TESTES DO BRAIN MIDDLEWARE v1.0
============================================
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.brain_middleware import (
    BrainMiddleware,
    BrainMiddleware,
    TipoIntencao,
    IntencaoDetectada,
    RespostaBrain,
    processar_mensagem
)


def teste_inicializacao():
    """Teste 1: Inicialização do Brain Middleware"""
    print("\n" + "="*50)
    print("TESTE 1: Inicialização")
    print("="*50)
    
    brain = BrainMiddleware()
    resultado = brain.inicializar()
    
    assert resultado == True, "Falha na inicialização"
    assert brain._inicializado == True, "Marca de inicialização não definida"
    assert brain._llm is not None, "LLM não carregado"
    assert brain._rag is not None, "RAG não carregado"
    assert brain._lexflow is not None, "LexFlow não carregado"
    
    print("✅ Inicialização OK")
    return True


def teste_detectar_intencao_notas():
    """Teste 2: Detecção de intenção - Criar Nota"""
    print("\n" + "="*50)
    print("TESTE 2: Detecção - Criar Nota")
    print("="*50)
    
    brain = BrainMiddleware()
    brain.inicializar()
    
    mensagens = [
        "Lex, anota que preciso comprar microfone",
        "Lembra disso: reunião às 14h",
        "Anote aí: ideia para vídeo",
        "Registra: Blue Yeti é bom para gravação",
    ]
    
    for msg in mensagens:
        intencao = brain._detectar_intencao(msg)
        print(f"   '{msg[:40]}...' → {intencao.tipo.value} ({intencao.confianca:.2f})")
        assert intencao.tipo == TipoIntencao.CRIAR_NOTA, f"Errado: {intencao.tipo}"
    
    print("✅ Detecção de notas OK")
    return True


def teste_detectar_intencao_tarefas():
    """Teste 3: Detecção de intenção - Criar Tarefa"""
    print("\n" + "="*50)
    print("TESTE 3: Detecção - Criar Tarefa")
    print("="*50)
    
    brain = BrainMiddleware()
    brain.inicializar()
    
    mensagens = [
        "Lex, lembra que tenho que terminar o vídeo até sexta",
        "Preciso comprar o microfone till semana que vem",
        "Tenho que gravar o podcast amanhã",
        "Lembre de enviar relatório segunda",
    ]
    
    for msg in mensagens:
        intencao = brain._detectar_intencao(msg)
        print(f"   '{msg[:40]}...' → {intencao.tipo.value} ({intencao.confianca:.2f})")
        assert intencao.tipo == TipoIntencao.CRIAR_TAREFA, f"Errado: {intencao.tipo}"
    
    print("✅ Detecção de tarefas OK")
    return True


def teste_detectar_intencao_busca():
    """Teste 4: Detecção de intenção - Buscar Info"""
    print("\n" + "="*50)
    print("TESTE 4: Detecção - Buscar Informações")
    print("="*50)
    
    brain = BrainMiddleware()
    brain.inicializar()
    
    mensagens = [
        "Lex, o que eu já escrevi sobre YouTube?",
        "Me mostra tudo que tenho sobre monetização",
        "Resuma minhas anotações sobre IA",
        "Quais são minhas ideias sobre canais dark?",
    ]
    
    for msg in mensagens:
        intencao = brain._detectar_intencao(msg)
        print(f"   '{msg[:40]}...' → {intencao.tipo.value} ({intencao.confianca:.2f})")
        assert intencao.tipo == TipoIntencao.BUSCAR_INFO, f"Errado: {intencao.tipo}"
    
    print("✅ Detecção de buscas OK")
    return True


def teste_extrair_entidades():
    """Teste 5: Extração de entidades"""
    print("\n" + "="*50)
    print("TESTE 5: Extração de Entidades")
    print("="*50)
    
    brain = BrainMiddleware()
    brain.inicializar()
    
    testes = [
        ("Lex, anota que preciso comprar microfone", {"conteudo": "comprar microfone"}),
        ("Tenho que terminar vídeo até sexta", {"prazo": ..., "conteudo": ...}),
        ("Me dá 5 ideias sobre YouTube", {"quantidade": 5}),
        ("Isso é urgente pro canal dark", {"prioridade": "urgente", "projeto_sugerido": "Canals Dark"}),
    ]
    
    for msg, esperado in testes:
        entidades = brain._extrair_entidades(msg)
        print(f"   Msg: '{msg[:40]}...'")
        print(f"   Entidades: {entidades}")
        
        for chave, valor in esperado.items():
            if valor is not ...:
                assert chave in entidades, f"Entidade {chave} não encontrada"
    
    print("✅ Extração de entidades OK")
    return True


def teste_processar_completo():
    """Teste 6: Processamento completo (end-to-end)"""
    print("\n" + "="*50)
    print("TESTE 6: Processamento Completo (End-to-End)")
    print("="*50)
    
    brain = BrainMiddleware()
    brain.inicializar()
    
    # Teste com mensagem real
    mensagem_teste = "Lex, anota: Preciso pesquisar sobre Blue Yeti para gravação"
    
    resultado = brain.processar(mensagem_teste)
    
    print(f"   Mensagem: {mensagem_teste}")
    print(f"   Sucesso: {resultado.sucesso}")
    print(f"   Ação: {resultado.acao_executada}")
    print(f"   Resposta: {resultado.resposta_ia[:100]}...")
    
    assert isinstance(resultado, RespostaBrain), "Tipo de retorno incorreto"
    assert hasattr(resultado, 'resposta_ia'), "Falta atributo resposta_ia"
    assert hasattr(resultado, 'sucesso'), "Falta atributo sucesso"
    
    print("✅ Processamento completo OK")
    return True


def teste_funcao_auxiliar():
    """Teste 7: Função auxiliar processar_mensagem()"""
    print("\n" + "="*50)
    print("TESTE 7: Função Auxiliar processar_mensagem()")
    print("="*50)
    
    resultado = processar_mensagem("Teste de mensagem rápida")
    
    assert isinstance(resultado, RespostaBrain), "Retorno incorreto"
    assert resultado.resposta_ia is not None, "Resposta vazia"
    
    print(f"   Resposta: {resultado.resposta_ia[:80]}...")
    print("✅ Função auxiliar OK")
    return True


def main():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("🧠 BRAIN MIDDLEWARE - SUITE DE TESTES")
    print("="*60)
    
    testes = [
        ("Inicialização", teste_inicializacao),
        ("Detecção - Notas", teste_detectar_intencao_notas),
        ("Detecção - Tarefas", teste_detectar_intencao_tarefas),
        ("Detecção - Buscas", teste_detectar_intencao_busca),
        ("Extração de Entidades", teste_extrair_entidades),
        ("Processamento Completo", teste_processar_completo),
        ("Função Auxiliar", teste_funcao_auxiliar),
    ]
    
    resultados = []
    
    for nome, teste_func in testes:
        try:
            resultado = teste_func()
            resultados.append((nome, True, None))
        except AssertionError as e:
            resultados.append((nome, False, str(e)))
            print(f"❌ FALHA: {e}")
        except Exception as e:
            resultados.append((nome, False, str(e)))
            print(f"❌ ERRO: {e}")
    
    # Resumo final
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    
    passou = sum(1 for _, sucesso, _ in resultados if sucesso)
    total = len(resultados)
    
    for nome, sucesso, erro in resultados:
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        print(f"{status} - {nome}")
        if erro:
            print(f"   Erro: {erro}")
    
    print(f"\n🎯 RESULTADO: {passou}/{total} testes passaram")
    
    if passou == total:
        print("🎉 TODOS OS TESTES PASSARAM!")
        return 0
    else:
        print(f"⚠️ {total - passou} teste(s) falharam")
        return 1


if __name__ == "__main__":
    exit(main())