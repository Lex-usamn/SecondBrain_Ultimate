# test_clarificacao.py

from engine.brain_llm_orchestrator import obter_orchestrator_global

orch = obter_orchestrator_global()

# Simula conversa
contexto = {"usuario_id": 123}

# 1ª mensagem
resp1 = orch.processar("preciso criar um shorts", contexto)
print(f"Bot: {resp1.resposta_ia}")
print(f"Aguardando? {resp1.aguardando_resposta}")
print(f"Clarif pendente? {resp1.clarificacao_pendente}")
print("-" * 50)

# 2ª mensagem (resposta do usuário)
resp2 = orch.processar("so uma nota mesmo", contexto)
print(f"Bot: {resp2.resposta_ia}")
print(f"Aguardando? {resp2.aguardando_resposta}")
print(f"Clarif pendente? {resp2.clarificacao_pendente}")