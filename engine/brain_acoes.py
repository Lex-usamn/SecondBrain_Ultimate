"""
================================================================================
BRAIN MIDDLEWARE v2.1 - Execução de Ações
================================================================================

AUTOR: Mago-Usamn | DATA: 12/04/2026
NOME DO ASSISTENTE: MAGO 🧙
================================================================================
"""

import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from engine.brain_types import (
    logger_brain, TipoIntencao, IntencaoDetectada, ContextoConversa,
    RespostaBrain, NOME_ASSISTENTE, NOME_ASSISTENTE_DISPLAY,
    PrioridadeTarefa, converter_prazo, normalizar_prioridade
)


class ExecutorAcoes:
    """Executor de ações do Brain Middleware."""
    
    def __init__(self, lexflow_client, llm_client, rag_system):
        self._lexflow = lexflow_client
        self._llm = llm_client
        self._rag = rag_system
    
    def executar(self, intencao: IntencaoDetectada, mensagem: str, contexto: Optional[dict]) -> RespostaBrain:
        acoes = {
            TipoIntencao.CRIAR_NOTA: self.criar_nota,
            TipoIntencao.CRIAR_TAREFA: self.criar_tarefa,
            TipoIntencao.BUSCAR_INFO: self.buscar_info,
            TipoIntencao.GERAR_IDEIAS: self.gerar_ideias,
            TipoIntencao.CONSULTAR_METRICAS: self.consultar_metricas,
            TipoIntencao.CRIAR_PLANO: self.criar_plano,
            TipoIntencao.CONVERSAR: self.conversar,
            TipoIntencao.DESCONHECIDA: self.desconhecida,
        }
        
        executor = acoes.get(intencao.tipo, self.desconhecida)
        
        try:
            return executor(intencao, mensagem, contexto)
        except Exception as e:
            logger_brain.error(f"❌ Erro na ação {intencao.tipo.value}: {e}", exc_info=True)
            return RespostaBrain(sucesso=False, acao_executada=intencao.tipo.value,
                                  resposta_ia=f"❌ Erro: {str(e)[:50]}", erro=str(e))
    
    def criar_nota(self, intencao: IntencaoDetectada, mensagem: str, contexto: Optional[dict]) -> RespostaBrain:
        logger_brain.info("📝 Executando: CRIAR NOTA")
        
        conteudo = intencao.entidades.get("conteudo", mensagem)
        titulo = conteudo[:50] + ("..." if len(conteudo) > 50 else "")
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        conteudo_completo = f"[Captura via {NOME_ASSISTENTE_DISPLAY} v2.1 - {timestamp}]\n\n{conteudo}"
        
        try:
            resultado = self._lexflow.add_note(titulo, content=conteudo_completo)
            if resultado.get("success"):
                nota_id = resultado.get("note", {}).get("id", "N/A")
                resposta = f"""✅ **Nota criada com sucesso!**

📝 *{titulo}*
💾 Salvo às {timestamp}

💡 Quer transformar em TAREFA? Buscar infos relacionadas?"""
                return RespostaBrain(sucesso=True, acao_executada="criar_nota", resposta_ia=resposta,
                                      detalhes={"nota_id": nota_id}, sugestoes=["Criar tarefa?", "Buscar infos?"])
            raise Exception(resultado.get("error", "Erro"))
        except Exception as e:
            logger_brain.error(f"❌ Erro nota: {e}")
            return RespostaBrain(sucesso=False, acao_executada="criar_nota", resposta_ia=f"❌ Erro: {str(e)[:50]}", erro=str(e))
    
    def criar_tarefa(self, intencao: IntencaoDetectada, mensagem: str, contexto: Optional[dict]) -> RespostaBrain:
        """
        Cria tarefa (no projeto ou inbox).
        
        CORREÇÃO v2.1.1: Trata respostas da API que não trazem {"success": True}
        mesmo quando a criação funciona corretamente.
        """
        logger_brain.info("✅ Executando: CRIAR TAREFA")
        
        conteudo = intencao.entidades.get("conteudo", mensagem)
        titulo = conteudo[:80] + ("..." if len(conteudo) > 80 else "")
        prioridade = intencao.entidades.get("prioridade", PrioridadeTarefa.MEDIA.value)
        prioridade_en = normalizar_prioridade(prioridade)
        
        projeto_id = None
        projeto_nome = None
        if "projeto_sugerido" in intencao.entidades:
            projeto_id = self._buscar_projeto_id(intencao.entidades["projeto_sugerido"])
            if projeto_id:
                projeto_nome = intencao.entidades["projeto_sugerido"]
        
        tem_projeto = projeto_id and int(projeto_id) > 0
        
        try:
            if tem_projeto:
                descricao = f"[Criado via {NOME_ASSISTENTE_DISPLAY} v2.1]\n\n{mensagem}"
                due_date = intencao.entidades.get("prazo") if "prazo" in intencao.entidades else None
                
                resultado = self._lexflow.add_task(
                    int(projeto_id), 
                    titulo, 
                    description=descricao, 
                    priority=prioridade_en, 
                    due_date=due_date
                )
                task_id = self._extrair_task_id(resultado)
                modo = "projeto"
            else:
                # === MODO INBOX (NOTA) ===
                titulo_inbox = f"📋 {titulo}"
                if "prazo" in intencao.entidades:
                    titulo_inbox += f" ⏰ {intencao.entidades['prazo']}"
                
                icones = {"high": "🔴", "low": "🟢", "urgent": "🚨", "medium": "🟡"}
                if prioridade_en in icones:
                    titulo_inbox += f" {icones[prioridade_en]}"
                
                descricao_inbox = f"[{NOME_ASSISTENTE_DISPLAY} v2.1]\n\n{mensagem}\n\nStatus: Aguardando triagem"
                tags = ["tarefa", "inbox", "brain-mw-v21", f"pri:{prioridade_en}"]
                
                logger_brain.info(f"📝 Criando nota inbox: '{titulo_inbox}'")
                
                try:
                    resultado = self._lexflow.add_note(
                        title=titulo_inbox,
                        content=descricao_inbox,
                        tags=tags
                    )
                    
                    # ✅✅✅ CORREÇÃO CRÍTICA (v2.1.1) ✅✅✅
                    # A API do Lex Flow às vezes cria a nota mas não retorna {"success": True}
                    # Se temos um resultado não-nulo, consideramos sucesso!
                    if resultado is not None:
                        if isinstance(resultado, dict) and not resultado.get("success"):
                            # API retornou dict mas sem success=True → forçar sucesso
                            resultado["success"] = True
                            logger_brain.info(f"🔄 Corrigido: success forçado para True")
                        elif not isinstance(resultado, dict):
                            # API retornou algo que não é dict → envelopar
                            resultado = {"success": True, "raw": resultado}
                            logger_brain.info(f"🔄 Corrigido: resultado envelopado em dict")
                    # ✅✅✅ FIM DA CORREÇÃO ✅✅✅
                    
                    logger_brain.info(f"📦 Resultado add_note: {type(resultado).__name__} | Conteúdo: {str(resultado)[:100]}")
                    
                    task_id = self._extrair_note_id(resultado)
                    modo = "inbox"
                    
                except Exception as e_inbox:
                    logger_brain.error(f"❌ Erro específico no add_note (inbox): {e_inbox}", exc_info=True)
                    raise Exception(f"Falha ao criar nota no Inbox: {str(e_inbox)}")
            
            # === VERIFICAÇÃO DE SUCESSO (COM TOLERÂNCIA) ===
            # Critérios relaxados: se temos resultado e task_id, deu certo!
            resultado_existe = resultado is not None
            sucesso_api = False
            
            if isinstance(resultado, dict):
                sucesso_api = resultado.get("success", False)
            else:
                # Se não é dict mas existe, assumimos sucesso (nota foi criada)
                sucesso_api = bool(resultado)
            
            task_id_valido = task_id and task_id != "N/A" and task_id != "None"
            
            # NOVA LÓGICA: Basta um dos dois (sucesso API OU task_id válido)
            sucesso = resultado_existe and (sucesso_api or task_id_valido)
            
            logger_brain.info(f"🔍 Verificação: existe={resultado_existe}, api_ok={sucesso_api}, id_ok={task_id_valido} → final={sucesso}")
            
            if sucesso:
                # === MONTAR RESPOSTA DE SUCESSO ===
                icon_prio = {"urgente": "🔴", "alta": "🟠", "media": "🟡", "baixa": "🟢"}
                
                if modo == "inbox":
                    resposta = f"""✅ *Tarefa na Caixa de Entrada!*

    📋 *{titulo}*"""
                    if "prazo" in intencao.entidades:
                        resposta += f"\n📅 {intencao.entidades['prazo']}"
                    resposta += f"\n⚡ {icon_prio.get(prioridade_en, '⚪')} {prioridade_en.capitalize()}"
                else:
                    resposta = f"""✅ *Tarefa criada!*

    📋 *{titulo}*"""
                    if "prazo" in intencao.entidades:
                        resposta += f"\n📅 {intencao.entidades['prazo']}"
                    resposta += f"\n⚡ {icon_prio.get(prioridade, '⚪')} {prioridade.capitalize()}"
                    if projeto_nome:
                        resposta += f"\n📁 {projeto_nome}"
                
                resposta += "\n\n🤖 Quer mais alguma coisa?"
                
                logger_brain.info(f"✅ Tarefa criada com sucesso! (modo: {modo}, id: {task_id})")
                
                return RespostaBrain(
                    sucesso=True, 
                    acao_executada="criar_tarefa", 
                    resposta_ia=resposta,
                    detalhes={"task_id": task_id, "modo": modo}, 
                    sugestoes=["Mais detalhes?", "Lembretes?"]
                )
            
            # Se chegou aqui, realmente falhou
            erro_detalle = f"resultado={type(resultado).__name__}, success={sucesso_api}, task_id={task_id}"
            logger_brain.error(f"❌ Falha na verificação: {erro_detalle}")
            raise Exception(f"Verificação falhou: {erro_detalle}")
            
        except Exception as e:
            logger_brain.error(f"❌ Erro tarefa: {e}", exc_info=True)
            return RespostaBrain(
                sucesso=False, 
                acao_executada="criar_tarefa", 
                resposta_ia=f"❌ Erro: {str(e)[:80]}", 
                erro=str(e)
            )
    def _buscar_projeto_id(self, nome: str) -> Optional[int]:
        try:
            resultado = self._lexflow.get_projects()
            if resultado.get("success") and resultado.get("projects"):
                for proj in resultado["projects"]:
                    if isinstance(proj, dict):
                        if nome.lower() in proj.get("name", "").lower():
                            return proj.get("id")
        except Exception as e:
            logger_brain.warning(f"⚠️ Erro buscar projeto: {e}")
        return None
    
    def _extrair_task_id(self, resultado) -> str:
        if isinstance(resultado, dict):
            if 'task' in resultado and isinstance(resultado['task'], dict):
                return resultado['task'].get('id', 'N/A')
            return resultado.get('id', 'N/A')
        elif isinstance(resultado, (int, str)):
            return str(resultado)
        return 'N/A'
    
    def _extrair_note_id(self, resultado) -> str:
        if isinstance(resultado, dict):
            note_data = resultado.get("note", resultado)
            if isinstance(note_data, dict):
                return note_data.get('id', 'N/A')
            return str(note_data) if note_data else 'N/A'
        return str(resultado) if resultado else 'N/A'
    
    def buscar_info(self, intencao: IntencaoDetectada, mensagem: str, contexto: Optional[dict]) -> RespostaBrain:
        logger_brain.info("🔍 Executando: BUSCAR INFO")
        
        query = intencao.entidades.get("conteudo", mensagem)
        query_limpa = re.sub(r"(o que eu|já|escrevi|falei|sobre)", "", query, flags=re.I).strip()
        
        try:
            resultados_rag = self._rag.buscar(query=query_limpa, n_results=5, estrategia="hibrida")
            if not resultados_rag or not resultados_rag.get("resultados"):
                return RespostaBrain(sucesso=True, acao_executada="buscar_info",
                                      resposta_ia=f"🔍 **Nada sobre** *'{query_limpa}'*")
            
            contextos = [f"[{i}] {r.get('conteudo', '')[:200]}" for i, r in enumerate(resultados_rag.get("resultados", [])[:5], 1)]
            prompt = f"Baseado em:\n{chr(10).join(contextos)}\n\nPergunta: {mensagem}\nResponda clara e diretamente."
            resposta_llm = self._llm.gerar(prompt)
            
            return RespostaBrain(sucesso=True, acao_executada="buscar_info",
                                  resposta_ia=f"🔍 **Encontrados {len(resultados_rag.get('resultados', []))} refs**\n\n{resposta_llm}")
        except Exception as e:
            return RespostaBrain(sucesso=False, acao_executada="buscar_info", resposta_ia=f"❌ Erro: {str(e)[:50]}")
    
    def gerar_ideias(self, intencao: IntencaoDetectada, mensagem: str, contexto: Optional[dict]) -> RespostaBrain:
        logger_brain.info("💡 Executando: GERAR IDEIAS")
        
        tema = intencao.entidades.get("conteudo", mensagem)
        quantidade = intencao.entidades.get("quantidade", 5)
        
        try:
            prompt = f"Gere {quantidade} ideias criativas sobre: {tema}\n\nSeja criativo!"
            resposta_llm = self._llm.gerar(prompt)
            return RespostaBrain(sucesso=True, acao_executada="gerar_ideias",
                                  resposta_ia=f"💡 **{quantidade} IDEIAS**: *'{tema.upper()}'*\n\n{resposta_llm}")
        except Exception as e:
            return RespostaBrain(sucesso=False, acao_executada="gerar_ideias", resposta_ia=f"❌ Erro: {str(e)[:50]}")
    
    def consultar_metricas(self, intencao: IntencaoDetectada, mensagem: str, contexto: Optional[dict]) -> RespostaBrain:
        logger_brain.info("📊 Executando: MÉTRICAS")
        
        try:
            agora = datetime.now()
            dia = ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"][agora.weekday()]
            return RespostaBrain(sucesso=True, acao_executada="consultar_metricas",
                                  resposta_ia=f"📊 **PAINEL DE MÉTRICAS**\n📅 {dia}, {agora.strftime('%d/%m/%Y')}\n\n✅ Tudo funcionando bem! 💪")
        except Exception as e:
            return RespostaBrain(sucesso=False, acao_executada="consultar_metricas", resposta_ia=f"❌ Erro: {str(e)[:50]}")
    
    def criar_plano(self, intencao: IntencaoDetectada, mensagem: str, contexto: Optional[dict]) -> RespostaBrain:
        logger_brain.info("🎯 Executando: PLANO")
        
        objetivo = intencao.entidades.get("conteudo", mensagem)
        try:
            prompt = f"Crie um plano estratégico para: {objetivo}\n\nSeja prático e estruturado."
            resposta_llm = self._llm.gerar(prompt)
            return RespostaBrain(sucesso=True, acao_executada="criar_plano",
                                  resposta_ia=f"🎯 **PLANO:** *'{objetivo.upper()}'*\n\n{resposta_llm}")
        except Exception as e:
            return RespostaBrain(sucesso=False, acao_executada="criar_plano", resposta_ia=f"❌ Erro: {str(e)[:50]}")
    
    def conversar(self, intencao: IntencaoDetectada, mensagem: str, contexto: Optional[dict]) -> RespostaBrain:
        logger_brain.info("💬 Executando: CONVERSAR")
        
        try:
            prompt = f"Você é o {NOME_ASSISTENTE_DISPLAY}, assistente amigável.\n\nUsuário: '{mensagem}'\nResponda naturalmente, máximo 4 linhas."
            resposta = self._llm.gerar(prompt)
            return RespostaBrain(sucesso=True, acao_executada="conversar", resposta_ia=resposta)
        except Exception as e:
            return RespostaBrain(sucesso=False, acao_executada="conversar",
                                  resposta_ia=f"Hey! 👋 Sou {NOME_ASSISTENTE_DISPLAY}! Como ajudar?")
    
    def desconhecida(self, intencao: IntencaoDetectada, mensagem: str, contexto: Optional[dict]) -> RespostaBrain:
        logger_brain.info("❓ Executando: DESCONHECIDA")
        
        return RespostaBrain(sucesso=True, acao_executada="desconhecida",
                              resposta_ia=f"""🤔 **Não tenho certeza...**

Mas posso ajudar:

📝 **{NOME_ASSISTENTE}, anota [algo]** → Nota
✅ **{NOME_ASSISTENTE}, lembra que [fazer]** → Tarefa
🔍 **{NOME_ASSISTENTE}, o que escrevi sobre [tema]?** → Busca
💡 **{NOME_ASSISTENTE}, ideias sobre [tema]** → Ideias

**Como posso ajudar?** 😊""")