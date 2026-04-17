"""
================================================================================
BRAIN ORCHESTRATOR - Execução de Ações Modulares (v3.4)
================================================================================

AUTOR: Mago-Usamn
NOME DO ASSISTENTE: MAGO 🧙

Módulo de ações responsável por interpretar decisões do LLM e 
executar tarefas reais no Lex Flow, como criar, mover e deletar.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from engine.brain_types import (
    logger_brain, RespostaBrain, NOME_ASSISTENTE_DISPLAY
)
from engine.brain_lexflow_connector import LexFlowConnector

class ExecutorAcoes:
    """Executor de ações do Brain Orchestrator."""
    
    def __init__(self, lexflow_connector: LexFlowConnector, llm_client, rag_system):
        self._conector = lexflow_connector
        # Em algumas ações podemos usar diretamente self._conector.client
        self._llm = llm_client
        self._rag = rag_system
        
    @property
    def _lexflow(self):
        """Retorna o cliente raw do Lex Flow se conectado."""
        return self._conector.client if self._conector else None

    # =========================================================================
    # ROTEADOR DE AÇÕES
    # =========================================================================
    
    def executar(self, decisao: Dict[str, Any], 
                 mensagem: str, contexto: Optional[dict]) -> Optional[RespostaBrain]:
        """Executa a ação que a IA decidiu."""
        
        acao = decisao.get("acao")
        entidades = decisao.get("entidades", {})
        resposta_ia = decisao.get("resposta", "")
        
        logger_brain.info(f"Execução ação da IA: {acao}")
        
        try:
            if acao == "criar_tarefa":
                return self._executar_criar_tarefa(entidades, mensagem, resposta_ia)
                
            elif acao == "criar_nota":
                return self._executar_criar_nota(entidades, mensagem, resposta_ia)
                
            elif acao == "buscar_info":
                return self._executar_buscar_info(entidades, mensagem, resposta_ia)

            elif acao == "deletar_notas":
                return self._executar_deletar_notas(entidades, mensagem, resposta_ia)
                
            elif acao == "mover_nota":
                return self._executar_mover_nota(entidades, mensagem, resposta_ia)               
              
            elif acao == "gerar_ideias":
                return self._executar_gerar_ideias(entidades, mensagem, resposta_ia)
                
            elif acao == "consultar_metricas":
                return RespostaBrain(
                    sucesso=True,
                    acao_executada="consultar_metricas",
                    resposta_ia=resposta_ia
                )
            
            return None
            
        except Exception as e:
            logger_brain.error(f"Erro executando {acao}: {e}", exc_info=True)
            return RespostaBrain(
                sucesso=False,
                acao_executada=acao,
                resposta_ia=f"{resposta_ia}Erro ao executar: {str(e)[:50]}",
                erro=str(e)
            )

    # =========================================================================
    # IMPLEMENTAÇÃO DAS AÇÕES
    # =========================================================================

    def _executar_criar_tarefa(self, entidades: dict, 
                                mensagem: str, resposta_ia: str) -> RespostaBrain:
        """Executa criação de tarefa no Lex Flow."""
        
        if not self._lexflow:
            return RespostaBrain(
                sucesso=False, 
                acao_executada="criar_tarefa", 
                resposta_ia="Lex Flow indisponível"
            )
        
        conteudo = entidades.get("conteudo", mensagem)
        titulo = conteudo[:80]
        
        titulo_inbox = f"TAREFA: {titulo}"
        if entidades.get("prazo"):
            titulo_inbox += f" | PRAZO: {entidades['prazo']}"
        
        prioridade = entidades.get("prioridade", "medium")
        icones = {"high": "URGENTE", "low": "BAIXA", "urgent": "!!! URGENTE !!!", "medium": "MEDIA"}
        if prioridade in icones:
            titulo_inbox += f" | PRIORIDADE: {icones[prioridade]}"
        
        descricao = (
            f"[Criado por {NOME_ASSISTENTE_DISPLAY} v3.0 - IA]"
            f"{mensagem}Status: Aguardando triagem"
        )
        tags = ["tarefa", "inbox", "brain-v30-ia", f"pri:{prioridade}"]
        
        try:
            resultado = self._lexflow.add_note(
                title=titulo_inbox, content=descricao, tags=tags
            )
            
            # Extrair ID corretamente (mesma correção v3.9)
            tarefa_id = None
            if isinstance(resultado, dict):
                if 'note' in resultado and isinstance(resultado['note'], dict):
                    tarefa_id = resultado['note'].get('id')
                if not tarefa_id:
                    tarefa_id = resultado.get('id')
            
            logger_brain.info(f"✅ [CRIAR TAREFA v3.9] ID extraído: {tarefa_id}")
            
            sucesso = (resultado is not None)
            
            if sucesso:
                resposta_final = (
                    f"{resposta_ia}"
                    f"Tarefa registrada na Caixa de Entrada!"
                    f"- {titulo}"
                )
                if entidades.get("prazo"):
                    resposta_final += f"- Prazo: {entidades['prazo']}"
                resposta_final += f"- Prioridade: {prioridade.capitalize()}"
                
                return RespostaBrain(
                    sucesso=True,
                    acao_executada="criar_tarefa",
                    resposta_ia=resposta_final,
                    detalhes={"modo": "inbox", "fonte": "decisao_ia"}
                )
            
            raise Exception("Falha ao criar tarefa")
            
        except Exception as e:
            logger_brain.error(f"Erro tarefa: {e}")
            return RespostaBrain(
                sucesso=False,
                acao_executada="criar_tarefa",
                resposta_ia=f"{resposta_ia}Erro ao salvar: {str(e)[:40]}"
            )

    def _executar_criar_nota(self, entidades: dict, 
                              mensagem: str, resposta_ia: str) -> RespostaBrain:
        """
        Executa criação de nota no Lex Flow.
        
        v3.8 CORRIGIDO: 
        - Detecta "na área X" / "no projeto X" e MOVE AUTOMATICAMENTE!
        - Funciona com "anota: ..." direto!
        """
        if not self._lexflow:
            return RespostaBrain(
                sucesso=False, 
                acao_executada="criar_nota", 
                resposta_ia="⚠️ Lex Flow indisponível.",
                erro="lexflow_none"
            )
        
        try:
            import re
            
            conteudo = entidades.get("conteudo", mensagem)
            
            # ================================================
            # LIMPAR CONTEÚDO (remover prefixos como "anota:")
            # ================================================
            
            msg_clean = conteudo
            for prefixo in ['anota:', 'anota ', 'nota:', 'nota ', 'note:', 'note ']:
                if msg_clean.lower().startswith(prefixo):
                    msg_clean = msg_clean[len(prefixo):].strip()
                    break
            
            titulo = msg_clean[:60] + ("..." if len(msg_clean) > 60 else "")
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            logger_brain.info(f"📝 [CRIAR NOTA v3.8] Título limpo: '{titulo}'")
            logger_brain.info(f"📝 [CRIAR NOTA v3.8] Mensagem original: '{mensagem}'")
            
            # ================================================
            # DETECTAR DESTINO NA MENSAGEM ORIGINAL (v3.8)
            # ================================================
            
            msg_lower = mensagem.lower()
            destino_tipo = None
            destino_nome = None
            
            # Padrões ÁREA: "na área X", "para área X", "em X", "na X"
            padroes_area = [
                r'(?:na\s+|pra\s+|para\s+a?\s+|em\s+|na\s+área\s+|pra\s+área\s+)([\w\sà-ú]+?)(?:\s*$|\s+(?:dia|data|prazo|com\s|e\s+o?\s|$))',
                r'(?:área|area)\s*(?:de\s*)?["\']?([\w\sà-ú]+?)["\']?\s*$',
                r'\b(?:saúde|saude|academia|profissional|pessoal|finanças|financas|estudos|carreira|saúde)\b',
            ]
            
            for padrao in padroes_area:
                match = re.search(padrao, msg_lower, re.IGNORECASE)
                if match:
                    destino_nome = match.group(1).strip() if match.lastindex else match.group(0).strip()
                    # Normalizar "saude" → "Saude" (como está no Flow!)
                    if destino_nome.lower() in ['saude', 'saúde', 'saúde']:
                        destino_nome = 'Saude'
                    destino_tipo = 'area'
                    logger_brain.info(f"🎯 [CRIAR NOTA v3.8] ÁREA detectada: '{destino_nome}'")
                    break
            
            # Padrões PROJETO: "no projeto X", "para X", "canal X"
            if not destino_nome:
                padroes_projeto = [
                    r'(?:no\s+|pra\s+o?\s+|para\s+o?\s+|no\s+projeto\s+|pra\s+projeto\s+)([\w\sà-ú]+?)(?:\s*$|\s+(?:dia|data|prazo|com\s|e\s+o?\s|$))',
                    r'(?:projeto|canal|canais?|dark)\s*["\']?([\w\sà-ú]+?)["\']?\s*$',
                ]
                
                for padrao in padroes_projeto:
                    match = re.search(padrao, msg_lower, re.IGNORECASE)
                    if match:
                        destino_nome = match.group(1).strip()
                        destino_tipo = 'project'
                        logger_brain.info(f"🎯 [CRIAR NOTA v3.8] PROJETO detectado: '{destino_nome}'")
                        break
            
            # ================================================
            # CRIAR A NOTA
            # ================================================
            
            conteudo_completo = (
                f"[Captura via {NOME_ASSISTENTE_DISPLAY} v3.8 - {timestamp}]\n\n"
                f"{msg_clean}"
            )
            
            resultado = self._lexflow.add_note(
                title=titulo, 
                content=conteudo_completo
            )
            
            if not resultado:
                return RespostaBrain(
                    sucesso=False,
                    acao_executada="criar_nota",
                    resposta_ia="❌ Erro ao criar a nota.",
                    erro="falha_criar"
                )
            
            # ================================================
            # EXTRAIR ID/TÍTULO CORRETAMENTE (v3.9)
            # A API retorna: {"note": {"id": X, "title": "..."}}
            # ================================================
            
            nota_id = None
            nota_titulo_real = titulo
            
            if isinstance(resultado, dict):
                # Tentar pegar da chave 'note' primeiro (formato real da API!)
                if 'note' in resultado and isinstance(resultado['note'], dict):
                    nota_id = resultado['note'].get('id')
                    nota_titulo_real = resultado['note'].get('title', titulo)
                    logger_brain.info(f"📋 [CRIAR NOTA v3.9] Extraído de 'note': ID={nota_id}")
                
                # Fallback: tentar da raiz
                if not nota_id:
                    nota_id = resultado.get('id')
                    nota_titulo_real = resultado.get('title', titulo)
                    logger_brain.info(f"📋 [CRIAR NOTA v3.9] Extraído da raiz: ID={nota_id}")
            
            logger_brain.info(f"✅ [CRIAR NOTA v3.9] Nota criada: ID={nota_id}, Título='{nota_titulo_real}'")
            
            if not nota_id:
                logger_brain.error(f"❌ [CRIAR NOTA v3.9] ID não encontrado! Resposta bruta: {resultado}")
                return RespostaBrain(
                    sucesso=True,
                    acao_executada="criar_nota",
                    resposta_ia=(
                        f"⚠️ *Nota criada mas ID não retornado.*\n\n"
                        f"📝 **{nota_titulo_real}**\n\n"
                        f"A nota pode estar na Caixa de Entrada.\n"
                        f"Use `move item 1 para [destino]` para mover manualmente."
                    ),
                    detalhes={"nota_id": None, "erro": "sem_id", "resposta_bruta": str(resultado)[:200]}
                )
            
            logger_brain.info(f"✅ [CRIAR NOTA v3.8] Nota criada: ID={nota_id}, Título='{nota_titulo_real}'")
            
            # ================================================
            # MOVER PARA DESTINO (SE DETECTADO!) - v3.8
            # ================================================
            
            if destino_nome and destino_tipo and nota_id:
                logger_brain.info(f"🚀 [CRIAR NOTA v3.8] Tentando mover para {destino_tipo}: '{destino_nome}'...")
                
                destino_obj = None
                
                if destino_tipo == 'area':
                    destino_obj = self._lexflow.buscar_area_por_nome(destino_nome)
                elif destino_tipo == 'project':
                    destino_obj = self._lexflow.buscar_projeto_por_nome(destino_nome)
                
                if destino_obj:
                    destino_id = destino_obj.get('id')
                    destino_nome_real = destino_obj.get('name', destino_obj.get('title', destino_nome))
                    
                    logger_brain.info(f"🎯 [CRIAR NOTA v3.8] Destino encontrado: {destino_tipo}:{destino_id} ({destino_nome_real})")
                    
                    # MOVER USANDO /link (endpoint CORRIGIDO!)
                    move_result = self._lexflow.mover_nota_para_destino(nota_id, destino_tipo, destino_id)
                    
                    if move_result:
                        tipo_display = "🏷️ Área" if destino_tipo == 'area' else "📁 Projeto"
                        
                        return RespostaBrain(
                            sucesso=True,
                            acao_executada="criar_nota_movida",
                            resposta_ia=(
                                f"✅ *Nota criada e organizada!*\n\n"
                                f"📝 **{nota_titulo_real}**\n"
                                f"{tipo_display}: **{destino_nome_real}**\n\n"
                                f"💡 Já saiu da Caixa de Entrada!"
                            ),
                            detalhes={
                                "nota_id": nota_id,
                                "destino_tipo": destino_tipo,
                                "destino_id": destino_id,
                                "destino_nome": destino_nome_real,
                                "movida": True
                            }
                        )
                    else:
                        logger_brain.warning(f"⚠️ [CRIAR NOTA v3.8] Falha ao mover")
                        return RespostaBrain(
                            sucesso=True,
                            acao_executada="criar_nota",
                            resposta_ia=(
                                f"✅ *Nota criada!* 📝 **{nota_titulo_real}**\n\n"
                                f"⚠️ Tentei mover para {destino_tipo} '{destino_nome_real}' mas deu erro.\n"
                                f"A nota está na Caixa de Entrada.\n\n"
                                f"Use: `move item 1 para {destino_nome_real}`"
                            ),
                            detalhes={"nota_id": nota_id, "movida": False}
                        )
                else:
                    logger_brain.warning(f"⚠️ [CRIAR NOTA v3.8] Destino '{destino_nome}' não encontrado!")
                    
                    # Listar opções disponíveis
                    if destino_tipo == 'area':
                        areas = self._lexflow.listar_areas()
                        lista_disp = "\n".join([f"  • {a.get('name')}" for a in areas[:5]])
                    else:
                        projetos = self._lexflow.listar_projetos()
                        lista_disp = "\n".join([f"  • {p.get('name', p.get('title'))}" for p in projetos[:5]])
                    
                    return RespostaBrain(
                        sucesso=True,
                        acao_executada="criar_nota",
                        resposta_ia=(
                            f"✅ *Nota criada!* 📝 **{nota_titulo_real}**\n\n"
                            f"⚠️ Não encontrei '{destino_nome}'.\n\n"
                            f"*{'Áreas' if destino_tipo == 'area' else 'Projetos'} disponíveis:*\n{lista_disp}\n\n"
                            f"Use: `move item 1 para [nome]`"
                        ),
                        detalhes={"nota_id": nota_id, "destino_nao_encontrado": destino_nome}
                    )
            
            # Sem destino → Criou normally na inbox
            return RespostaBrain(
                sucesso=True,
                acao_executada="criar_nota",
                resposta_ia=f"✅ *Nota salva!* 📝 **{nota_titulo_real}**\n\n📥 Adicionada à Caixa de Entrada.",
                detalhes={"fonte": "inbox", "nota_id": nota_id}
            )
            
        except Exception as e:
            logger_brain.error(f"❌ [CRIAR NOTA v3.8] Erro: {e}", exc_info=True)
            return RespostaBrain(
                sucesso=False,
                acao_executada="criar_nota",
                resposta_ia=f"❌ Erro ao criar nota: {str(e)[:50]}",
                erro=str(e)
            )

    def _executar_deletar_notas(self, entidades: dict, mensagem: str, resposta_ia: str) -> RespostaBrain:
        """
        Deleta notas/tarefas do Lex Flow baseado em critérios.
        
        v3.3: Implementa deleção real
        """
        if not self._lexflow:
            return RespostaBrain(
                sucesso=False,
                acao_executada="deletar_notas",
                resposta_ia="⚠️ Lex Flow indisponível. Não consigo deletar agora.",
                erro="lexflow_none"
            )
        
        try:
            criterio = entidades.get("criterio", entidades.get("conteudo", ""))
            
            if not criterio:
                return RespostaBrain(
                    sucesso=False,
                    acao_executada="deletar_notas",
                    resposta_ia="🤔 Qual palavra-chave devo procurar para deletar? (Ex: 'shorts', 'teste', etc.)",
                    erro="criterio_vazio"
                )
            
            logger_brain.info(f"🗑️ [DELETAR] Procurando notas com critério: '{criterio}'")
            
            # ATENÇÃO: usa o conector para contornar os bugs!
            inbox = self._conector.get_inbox_robusto()
            
            if not inbox or not isinstance(inbox, list):
                logger_brain.warning(f"⚠️ [DELETAR] Inbox vazio ou inválido: {inbox}")
                return RespostaBrain(
                    sucesso=False,
                    acao_executada="deletar_notas",
                    resposta_ia="📭 Sua Caixa de Entrada está vazia. Nada para deletar!",
                    erro="inbox_vazio"
                )
            
            criterio_lower = criterio.lower()
            itens_deletar = []
            
            for item in inbox:
                if not isinstance(item, dict):
                    continue
                
                titulo = str(item.get('title', item.get('label', item.get('nome', '')))).lower()
                conteudo = str(item.get('content', item.get('conteudo', ''))).lower()
                
                if criterio_lower in titulo or criterio_lower in conteudo:
                    itens_deletar.append(item)
            
            if not itens_deletar:
                return RespostaBrain(
                    sucesso=True,
                    acao_executada="deletar_notas",
                    resposta_ia=f"🔍 Não encontrei notas com **'{criterio}'** na Caixa de Entrada.\n\nQuer que eu mostre o que tem?",
                    detalhes={"encontrados": 0}
                )
            
            deletados = []
            erros = []
            
            for item in itens_deletar:
                item_id = item.get('id')
                item_titulo = item.get('title', item.get('label', 'Sem título'))
                
                if not item_id:
                    continue
                
                try:
                    if hasattr(self._lexflow, 'delete_note'):
                        resultado = self._lexflow.delete_note(item_id)
                        logger_brain.info(f"🗑️ [DELETAR] Deletado ID={item_id}: {item_titulo}")
                        deletados.append(item_titulo)
                    else:
                        erros.append(f"ID {item_id} (método não existe)")
                        
                except Exception as e_del:
                    erros.append(f"ID {item_id} ({str(e_del)[:30]})")
            
            total_deletados = len(deletados)
            total_erros = len(erros)
            
            if total_deletados > 0:
                msg_deletados = "\n".join([f"  • {t}" for t in deletados[:5]])
                if total_deletados > 5:
                    msg_deletados += f"\n  • ... e mais {total_deletados - 5} itens"
                
                resposta_final = f"🗑️ **Deletei {total_deletados} nota(s) com '{criterio}':**\n\n{msg_deletados}"
                if total_erros > 0:
                    resposta_final += f"\n\n⚠️ {total_erros} erro(s) ao deletar alguns itens."
                
                return RespostaBrain(
                    sucesso=True,
                    acao_executada="deletar_notas",
                    resposta_ia=resposta_final,
                    detalhes={"deletados": total_deletados, "erros": total_erros, "criterio": criterio}
                )
            else:
                return RespostaBrain(
                    sucesso=False,
                    acao_executada="deletar_notas",
                    resposta_ia=f"❌ Não consegui deletar nenhuma nota.\n\nErros: {len(erros)}",
                    erro="nenhum_deletado"
                )
                
        except Exception as e:
            logger_brain.error(f"❌ [DELETAR] Erro geral: {e}", exc_info=True)
            return RespostaBrain(
                sucesso=False, acao_executada="deletar_notas",
                resposta_ia=f"❌ Erro ao deletar: {str(e)[:50]}", erro=str(e)
            )

    def _executar_mover_nota(self, entidades: dict, mensagem: str, 
                             resposta_ia: str) -> RespostaBrain:
        """
        MOVER NOTA PARA PROJETO/ÁREA - CORRIGIDO v3.5
        
        Agora funciona com:
        - "move item 1 para Canais Dark"
        - "mova a nota Procurar imagens para área Y"
        - "transforme o item 3 em tarefa no projeto Z"
        """
        if not self._lexflow:
            return RespostaBrain(
                sucesso=False, acao_executada="mover_nota",
                resposta_ia="⚠️ Lex Flow indisponível.", erro="lexflow_none"
            )
        
        try:
            # ========================================
            # 1. EXTRAIR PARÂMETROS DA MENSAGEM
            # ========================================
            
            destino = entidades.get("destino", 
                   entidades.get("projeto", 
                   entidades.get("area", "")))
            
            criterio = entidades.get("criterio", 
                      entidades.get("conteudo", ""))
            
            msg_lower = mensagem.lower().strip()
            
            # Detectar se quer converter em tarefa
            converter_em_tarefa = any(p in msg_lower for p in [
                "converte", "converter", "transforma", "transformar",
                "tarefa", "criar tarefa", "vira tarefa"
            ])
            
            logger_brain.info(f"📂 [MOVER v3.5] destino='{destino}', "
                            f"criterio='{criterio}', converter={converter_em_tarefa}")
            
            # ========================================
            # 2. VALIDAR DESTINO
            # ========================================
            
            if not destino:
                # Tentar extrair destino da mensagem usando regex
                import re
                # Padrões: "para [Destino]", "em [Destino]", "no projeto [Destino]"
                padroes = [
                    r'(?:para|em|no\s+projeto|na\s+área)\s+(.+?)(?:\s*$|\s+(?:e|que|com))',
                    r'(?:canais?|projeto|área)\s+["\']?(.+?)["\']?\s*$'
                ]
                
                for padrao in padroes:
                    match = re.search(padrao, msg_lower, re.IGNORECASE)
                    if match:
                        destino = match.group(1).strip()
                        logger_brain.info(f"🎯 [MOVER v3.5] Destino extraído: '{destino}'")
                        break
                
                if not destino:
                    return RespostaBrain(
                        sucesso=False, acao_executada="mover_nota",
                        resposta_ia=(
                            "🤔 *Para onde devo mover?*\n\n"
                            "Diga assim:\n"
                            "• `move item 1 para Canais Dark`\n"
                            "• `mova nota X para área Academia`\n\n"
                            "Ou digite `/projetos` para ver a lista."
                        ),
                        erro="destino_vazio"
                    )
            
            # ========================================
            # 3. VALIDAR CRITÉRIO (QUAL NOTA?)
            # ========================================
            
            if not criterio:
                # Tentar extrair critério da mensagem
                import re
                
                # Padrões: "item X", "nota X", "Xª nota", "primeira/segunda/terceira"
                padroes_indice = [
                    r'(?:item|nota)\s+(\d+)',
                    r'(\d+)(?:ª|º)?\s*(?:nota|item)',
                    r'(?:primeira|1ª?)\s*nota',
                    r'(?:segunda|2ª?)\s*nota',
                    r'(?:terceira|3ª?)\s*nota',
                ]
                
                # Mapeamento de ordinais para números
                ordinais = {'primeira': '1', 'segunda': '2', 'terceira': '3', 
                           'quarta': '4', 'quinta': '5'}
                
                for padrao in padroes_indice:
                    match = re.search(padrao, msg_lower, re.IGNORECASE)
                    if match:
                        if match.group(1) and match.group(1).isdigit():
                            criterio = match.group(1)
                        else:
                            palavra = match.group(0).split()[0]
                            criterio = ordinais.get(palavra, '')
                        
                        if criterio:
                            logger_brain.info(f"🔢 [MOVER v3.5] Índice extraído: '{criterio}'")
                            break
                
                # Se ainda não tiver critério, procurar entre aspas ou após verbos
                if not criterio:
                    # "move [Título da Nota] para..."
                    match = re.search(r'move(?:r)?\s+(.+?)\s+para', msg_lower, re.IGNORECASE)
                    if match:
                        criterio = match.group(1).strip()
                        logger_brain.info(f"📝 [MOVER v3.5] Título extraído: '{criterio}'")
            
            if not criterio:
                return RespostaBrain(
                    sucesso=False, acao_executada="mover_nota",
                    resposta_ia=(
                        "🤔 *Qual nota devo mover?*\n\n"
                        "Diga assim:\n"
                        "• `move item 1 para Canais Dark`\n"
                        "• `mova \"Procurar imagens\" para projeto X`\n\n"
                        "Ou digite `/inbox` para ver suas notas."
                    ),
                    erro="criterio_vazio"
                )
            
            # ========================================
            # 4. BUSCAR A NOTA (por índice ou título)
            # ========================================
            
            logger_brain.info(f"🔍 [MOVER v3.5] Buscando nota: '{criterio}'")
            
            # Usar o NOVO método que entende índices!
            nota_encontrada = self._lexflow.buscar_nota_por_indice_ou_titulo(criterio)
            
            if not nota_encontrada:
                # Listar opções disponíveis
                inbox = self._conector.get_inbox_robusto()
                lista_opcoes = ""
                if inbox and isinstance(inbox, list):
                    for i, item in enumerate(inbox[:7], 1):
                        titulo = item.get('title', 'Sem título')
                        lista_opcoes += f"\n  {i}. {titulo}"
                
                return RespostaBrain(
                    sucesso=False, acao_executada="mover_nota",
                    resposta_ia=(
                        f"🔍 *Não encontrei '{criterio}' na Caixa de Entrada.*\n\n"
                        f"*Suas notas:*{lista_opcoes or ' (Caixa vazia)'}\n\n"
                        f"Diga `move item [número] para [destino]`"
                    ),
                    erro="nota_nao_encontrada"
                )
            
            nota_id = nota_encontrada.get('id')
            nota_titulo = nota_encontrada.get('title', 'Sem título')
            
            logger_brain.info(f"✅ [MOVER v3.5] Nota encontrada: ID={nota_id}, Título='{nota_titulo}'")
            
            # ========================================
            # 5. BUSCAR DESTINO (projeto ou área)
            # ========================================
            
            destino_lower = destino.lower().strip()
            destino_encontrado = None
            destino_tipo = None
            
            # Buscar como ÁREA primeiro
            area = self._lexflow.buscar_area_por_nome(destino)
            if area:
                destino_encontrado = area
                destino_tipo = 'area'
                logger_brain.info(f"🏷️ [MOVER v3.5] Área encontrada: {area['name']} (ID={area['id']})")
            
            # Se não achou como área, buscar como PROJETO
            if not destino_encontrado:
                projeto = self._lexflow.buscar_projeto_por_nome(destino)
                if projeto:
                    destino_encontrado = projeto
                    destino_tipo = 'project'
                    logger_brain.info(f"📁 [MOVER v3.5] Projeto encontrado: {projeto.get('name')} (ID={projeto.get('id')})")
            
            if not destino_encontrado:
                # Listar destinos disponíveis
                destinos = self._lexflow.listar_destinos_disponiveis()
                
                msg_opcoes = f"🤔 *Não encontrei '{destino}'.*\n\n"
                
                areas = destinos.get('areas', [])
                if areas:
                    msg_opcoes += "*Áreas disponíveis:*\n"
                    msg_opcoes += "\n".join([f"  • {a.get('name')}" for a in areas[:5]])
                
                projetos = destinos.get('projetos', [])
                if projetos:
                    msg_opcoes += "\n\n*Projetos disponíveis:*\n"
                    msg_opcoes += "\n".join([f"  • {p.get('name', p.get('title'))}" for p in projetos[:8]])
                
                if not areas and not projetos:
                    msg_opcoes += "Nenhum projeto ou área encontrado."
                
                return RespostaBrain(
                    sucesso=False, acao_executada="mover_nota",
                    resposta_ia=msg_opcoes,
                    erro="destino_nao_encontrado"
                )
            
            destino_id = destino_encontrado.get('id')
            destino_nome = destino_encontrado.get('name', destino_encontrado.get('title', destino))
            
            # ========================================
            # 6. EXECUTAR A MOVIMENTAÇÃO (USANDO /link!)
            # ========================================
            
            logger_brain.info(f"🚀 [MOVER v3.5] Executando movimento → {destino_tipo}:{destino_id}")
            
            if converter_em_tarefa and destino_tipo == 'project':
                # Converter em tarefa E mover para projeto
                logger_brain.info(f"🔄 [MOVER v3.5] Convertendo em tarefa...")
                resultado = self._lexflow.converter_nota_em_tarefa_com_projeto(nota_id, destino_id)
                
                if resultado:
                    return RespostaBrain(
                        sucesso=True, acao_executada="mover_nota",
                        resposta_ia=(
                            f"✅ *Tarefa criada com sucesso!*\n\n"
                            f"📋 **{nota_titulo}**\n"
                            f"📁 Projeto: **{destino_nome}**\n"
                            f"📊 Status: Aguardando execução\n\n"
                            f"💡 A nota foi convertida em tarefa e movida!"
                        ),
                        detalhes={
                            "nota_id": nota_id,
                            "projeto_id": destino_id,
                            "convertido": True,
                            "metodo": "convert-to-task"
                        }
                    )
                else:
                    # Fallback: só mover (sem converter)
                    logger_brain.warning(f"⚠️ [MOVER v3.5] Conversão falhou, tentando mover...")
                    converter_em_tarefa = False
            
            # MOVER NORMAL (usando o endpoint /link CORRIGIDO!)
            resultado = self._lexflow.mover_nota_para_destino(nota_id, destino_tipo, destino_id)
            
            if resultado:
                tipo_display = "🏷️ Área" if destino_tipo == 'area' else "📁 Projeto"
                emoji_acao = "🔄" if converter_em_tarefa else "📂"
                
                return RespostaBrain(
                    sucesso=True, acao_executada="mover_nota",
                    resposta_ia=(
                        f"{emoji_acao} *Nota movida com sucesso!*\n\n"
                        f"📝 **{nota_titulo}**\n"
                        f"{tipo_display}: **{destino_nome}**\n\n"
                        f"✅ A nota saiu da Caixa de Entrada!"
                    ),
                    detalhes={
                        "nota_id": nota_id,
                        "destino_tipo": destino_tipo,
                        "destino_id": destino_id,
                        "destino_nome": destino_nome,
                        "metodo": "/link (CORRIGIDO)"
                    }
                )
            else:
                return RespostaBrain(
                    sucesso=False, acao_executada="mover_nota",
                    resposta_ia=(
                        f"❌ *Erro ao mover a nota.*\n\n"
                        f"A nota **{nota_titulo}** não foi movida.\n"
                        f"Tente novamente ou verifique os logs."
                    ),
                    erro="falha_mover_api"
                )
            
        except Exception as e:
            logger_brain.error(f"❌ [MOVER v3.5] EXCEÇÃO: {e}", exc_info=True)
            return RespostaBrain(
                sucesso=False, acao_executada="mover_nota",
                resposta_ia=f"❌ *Erro técnico:* `{str(e)[:80]}`\n\nVerifique os logs.",
                erro=str(e)
            )

    def _executar_buscar_info(self, entidades: dict, 
                            mensagem: str, resposta_ia: str) -> RespostaBrain:
        """
        Busca informações usando Lex Flow + RAG.
        
        v3.6 CORRIGIDO: Detecta intenção de listar ÁREAS/PROJETOS/INBOX
        em vez de ir pro RAG todo hora!
        """
        query = entidades.get("conteudo", mensagem)
        msg_lower = mensagem.lower().strip()
        
        logger_brain.info(f"🔍 [BUSCA v3.6] Query: '{query}'")
        logger_brain.info(f"🔍 [BUSCA v3.6] Mensagem original: '{mensagem}'")
        
        # ================================================
        # DETECTAR INTENÇÕES ESPECÍFICAS (antes de buscar!)
        # ================================================
        
        # --- INTENÇÃO: LISTAR ÁREAS P.A.R.A ---
        if any(p in msg_lower for p in [
            'minhas áreas', 'minhas areas', 'minha área', 'minha area',
            'quais áreas', 'quais areas', 'lista de áreas', 'lista de areas',
            'mostra as áreas', 'mostra as areas', 'ver áreas', 'ver areas',
            'todas as áreas', 'todas as areas', 'areas do para', 'áreas do para'
        ]):
            logger_brain.info("🏷️ [BUSCA v3.6] → INTENÇÃO: Listar Áreas P.A.R.A")
            
            if self._lexflow and self._conector.garantir_conectado():
                try:
                    areas = self._lexflow.listar_areas()
                    
                    if not areas:
                        return RespostaBrain(
                            sucesso=True, acao_executada="listar_areas",
                            resposta_ia="📭 *Você não tem nenhuma área cadastrada no Lex Flow.*\n\nQuer que eu crie uma área 'Saúde' pra você?"
                        )
                    
                    texto = f"🏷️ *Suas Áreas (P.A.R.A) no Lex Flow:*\n\n"
                    for i, area in enumerate(areas, 1):
                        nome = area.get('name', 'Sem nome')
                        desc = area.get('description', '')
                        area_id = area.get('id', '?')
                        linha = f"  {i}. **{nome}** (ID: {area_id})"
                        if desc:
                            linha += f"\n     └_ {desc[:60]}"
                        texto += linha + "\n"
                    
                    texto += "\n💡 *Dica:* Use `move item X para área [nome]` para organizar notas!"
                    
                    return RespostaBrain(
                        sucesso=True, acao_executada="listar_areas",
                        resposta_ia=texto,
                        detalhes={"total": len(areas), "fonte": "lex_flow"}
                    )
                except Exception as e:
                    logger_brain.error(f"❌ [BUSCA v3.6] Erro listando áreas: {e}")
            
            return RespostaBrain(
                sucesso=False, acao_executada="listar_areas",
                resposta_ia="⚠️ Não consegui acessar suas áreas. Lex Flow indisponível."
            )
        
        # --- INTENÇÃO: LISTAR PROJETOS ---
        if any(p in msg_lower for p in [
            'meus projetos', 'meu projeto', 'quais projetos', 'lista de projetos',
            'mostra os projetos', 'ver projetos', 'todos os projetos',
            'projetos ativos', 'canais'
        ]) or ('projeto' in msg_lower and any(p in msg_lower for p in ['lista', 'mostra', 'ver', 'quais', 'todos'])):
            logger_brain.info("📁 [BUSCA v3.6] → INTENÇÃO: Listar Projetos")
            
            if self._lexflow and self._conector.garantir_conectado():
                try:
                    projetos = self._lexflow.listar_projetos()
                    
                    if not projetos:
                        return RespostaBrain(
                            sucesso=True, acao_executada="listar_projetos",
                            resposta_ia="📭 *Você não tem nenhum projeto cadastrado.*\n\nQuer que eu crie um?"
                        )
                    
                    texto = f"📁 *Seus Projetos no Lex Flow:*\n\n"
                    for i, proj in enumerate(projetos, 1):
                        nome = proj.get('name', proj.get('title', 'Sem nome'))
                        desc = proj.get('description', '')
                        proj_id = proj.get('id', '?')
                        linha = f"  {i}. **{nome}** (ID: {proj_id})"
                        if desc:
                            linha += f"\n     └_ {desc[:50]}"
                        texto += linha + "\n"
                    
                    texto += "\n💡 *Dica:* Use `move item X para [nome do projeto]` para mover notas!"
                    
                    return RespostaBrain(
                        sucesso=True, acao_executada="listar_projetos",
                        resposta_ia=texto,
                        detalhes={"total": len(projetos), "fonte": "lex_flow"}
                    )
                except Exception as e:
                    logger_brain.error(f"❌ [BUSCA v3.6] Erro listando projetos: {e}")
            
            return RespostaBrain(
                sucesso=False, acao_executada="listar_projetos",
                resposta_ia="⚠️ Não consegui acessar seus projetos."
            )
        
        # --- INTENÇÃO: MOSTRAR CAIXA DE ENTRADA / INBOX ---
        if any(p in msg_lower for p in [
            'caixa de entrada', 'inbox', 'o que tem na caixa',
            'minhas notas', 'notas da entrada', 'entrada do flow',
            'quick notes', 'notas rápidas', 'capturas', 'anotações'
        ]) or (any(p in msg_lower for p in ['nota', 'notas']) and any(p in msg_lower for p in ['tem', 'tenho', 'mostra', 'ver', 'lista'])):
            logger_brain.info("📥 [BUSCA v3.6] → INTENÇÃO: Mostrar Inbox")
            
            if self._lexflow and self._conector.garantir_conectado():
                try:
                    inbox = self._conector.get_inbox_robusto()
                    
                    if not inbox or not isinstance(inbox, list):
                        return RespostaBrain(
                            sucesso=True, acao_executada="mostrar_inbox",
                            resposta_ia="📭 *Sua Caixa de Entrada está vazia!*\n\nCapture ideias com:\n• `anota: sua ideia`\n• `tarefa: fazer algo`"
                        )
                    
                    texto = f"📥 *Caixa de Entrada ({len(inbox)} itens):*\n\n"
                    
                    for i, item in enumerate(inbox, 1):
                        if not isinstance(item, dict):
                            continue
                        
                        titulo = item.get('title', item.get('label', 'Sem título'))
                        conteudo = str(item.get('content', '')).replace('\n', ' ')[:60]
                        tags = item.get('tags', [])
                        
                        # Formatar tags
                        tags_str = ""
                        if tags:
                            if isinstance(tags, str):
                                try:
                                    import json
                                    tags = json.loads(tags)
                                except:
                                    tags = []
                            if isinstance(tags, list) and len(tags) > 0:
                                tags_str = " [" + ", ".join(tags[:3]) + "]"
                        
                        linha = f"  {i}. 📝 *{titulo}*{tags_str}"
                        if conteudo and len(conteudo) > 3:
                            linha += f"\n     └_ {conteudo}..."
                        texto += linha + "\n"
                    
                    texto += (
                        "\n\n💡 *Comandos úteis:*\n"
                        "• `move item N para [Projeto/Área]`\n"
                        "• `converte item N em tarefa no [Projeto]`\n"
                        "• `deleta item N` ou `deleta [palavra-chave]`"
                    )
                    
                    return RespostaBrain(
                        sucesso=True, acao_executada="mostrar_inbox",
                        resposta_ia=texto,
                        detalhes={"total": len(inbox), "fonte": "lex_flow"}
                    )
                except Exception as e:
                    logger_brain.error(f"❌ [BUSCA v3.6] Erro mostrando inbox: {e}")
            
            return RespostaBrain(
                sucesso=False, acao_executada="mostrar_inbox",
                resposta_ia="⚠️ Não consegui acessar sua Caixa de Entrada."
            )
        
        # ================================================
        # BUSCA NORMAL (RAG + Lex Flow) - para outras queries
        # ================================================
        
        resultados_texto = []
        
        if self._lexflow:
            try:
                self._conector.garantir_conectado()
                
                # Método 1: search_notes
                if hasattr(self._lexflow, 'search_notes'):
                    try:
                        resultados_lexflow = self._lexflow.search_notes(query)
                        if resultados_lexflow and isinstance(resultados_lexflow, list):
                            for item in resultados_lexflow[:5]:
                                if isinstance(item, dict):
                                    titulo = item.get('title', item.get('nome', 'Sem título'))
                                    conteudo = item.get('content', item.get('conteudo', ''))
                                    if conteudo:
                                        preview = str(conteudo).replace('\n', ' ')[:200]
                                        resultados_texto.append(f"📝 **{titulo}**\n{preview}")
                                    else:
                                        resultados_texto.append(f"📝 **{titulo}**")
                                elif isinstance(item, str):
                                    resultados_texto.append(f"📝 {item}")
                    except Exception as e_sn:
                        logger_brain.error(f"❌ [BUSCA v3.6] Erro search_notes: {e_sn}")
                
                # Método 2: Buscar manualmente no inbox (fallback)
                if not resultados_texto:
                    inbox = self._conector.get_inbox_robusto()
                    if inbox and isinstance(inbox, list) and len(inbox) > 0:
                        query_lower = query.lower()
                        palavras_query = query_lower.split()
                        
                        palavras_genericas = [
                            'nota', 'notas', 'tarefa', 'tarefas', 'inbox', 'entrada', 
                            'caixa', 'hoje', 'tem', 'tenho', 'qual', 'oque', 
                            'o que', 'existe', 'listar', 'mostrar', 'ver'
                        ]
                        eh_query_generica = any(x in query_lower for x in palavras_genericas)
                        
                        for item in inbox[:15]:
                            item_str = str(item).lower()
                            match_score = sum(1 for p in palavras_query if len(p) > 2 and p in item_str)
                            
                            if match_score >= 1 or eh_query_generica:
                                if isinstance(item, dict):
                                    titulo = item.get('title', item.get('nome', 'Sem título'))
                                    conteudo = item.get('content', item.get('conteudo', ''))
                                    if conteudo:
                                        preview = str(conteudo).replace('\n', ' ')[:150]
                                        resultados_texto.append(f"📋 **{titulo}**\n{preview}")
                                    else:
                                        resultados_texto.append(f"📋 {titulo}")
                                else:
                                    resultados_texto.append(f"📋 {item}")

                if resultados_texto:
                    refs = "\n\n".join(resultados_texto[:5])
                    resposta_final = f"{resposta_ia}\n\n🔍 **Encontrei no Lex Flow ({len(resultados_texto)} resultado(s)):**\n\n{refs}"
                    return RespostaBrain(
                        sucesso=True, acao_executada="buscar_info",
                        resposta_ia=resposta_final, detalhes={"fonte": "lex_flow"}
                    )
            except Exception as e_lex:
                logger_brain.error(f"❌ [BUSCA v3.6] Erro geral Lex Flow: {e_lex}")
        
        # BUSCAR NO RAG FALLBACK
        if self._rag:
            try:
                from engine.rag_system import EstrategiaBusca
                estrategia_param = EstrategiaBusca.HIBRIDA
                
                resultados_rag = self._rag.buscar(query=query, n_results=5, estrategia=estrategia_param)
                
                if resultados_rag and isinstance(resultados_rag, dict):
                    resultados_lista = (resultados_rag.get("resultados") or 
                                       resultados_rag.get("results") or [])
                    if resultados_lista:
                        refs = "\n".join([f"- {r.get('conteudo', r.get('content', r.get('texto', '')))[:150]}" 
                                         for r in resultados_lista[:3]])
                        return RespostaBrain(
                            sucesso=True, acao_executada="buscar_info",
                            resposta_ia=f"{resposta_ia}\n\n📚 **Referências encontradas:**\n{refs}",
                            detalhes={"fonte": "rag"}
                        )
            except Exception as e_rag:
                logger_brain.error(f"❌ [BUSCA v3.6] Erro RAG: {e_rag}")
        
        # NADA ENCONTRADO
        return RespostaBrain(
            sucesso=True, acao_executada="buscar_info",
            resposta_ia=(
                f"{resposta_ia}\n\n"
                f"🔍 **Não encontrei nada sobre '{query[:50]}'**\n\n"
                f"💡 *Dicas:*\n"
                f"• `me mostra minhas áreas` — Ver áreas P.A.R.A\n"
                f"• `meus projetos` — Ver projetos\n"
                f"• `caixa de entrada` — Ver inbox\n"
                f"• `/nota` ou `/tarefa` — Criar novo"
            ),
            detalhes={"fonte": "fallback"}
        )

    def _executar_gerar_ideias(self, entidades: dict, 
                               mensagem: str, resposta_ia: str) -> RespostaBrain:
        return RespostaBrain(
            sucesso=True, acao_executada="gerar_ideias", resposta_ia=resposta_ia
        )