"""
================================================================================
BRAIN ORCHESTRATOR - Prompts e Parsers (v3.1)
================================================================================

AUTOR: Mago-Usamn

Módulo que abriga templates de prompts gigantes e a lógica
de parsing de JSON para despoluir o código do Orchestrator principal.
"""

import json
import re
from datetime import datetime
from typing import Dict, Any, List
from engine.brain_types import logger_brain, NOME_ASSISTENTE_DISPLAY

def _formatar_historico(historico_conversa: List[Dict[str, str]]) -> str:
    """Extrai até as últimas 8 mensagens do histórico do usuário."""
    if not historico_conversa:
        return "[Início da conversa]\n"
    
    texto_hist = ""
    for item in historico_conversa[-8:]:
        role = item.get('role', 'user')
        texto = item.get('texto', '')[:200]
        texto_hist += f"{role.upper()}: {texto}\n"
    return texto_hist

def construir_prompt_mestre(msg_ctx: Any, inbox_text: str) -> str:
    """Monta o PROMPT MESTRE dando à IA todo o contexto necessário."""
    
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    soul_text = msg_ctx.contexto_soul or "[Não encontrado]"
    user_text = msg_ctx.contexto_user or "[Não encontrado]"
    memory_text = msg_ctx.contexto_memory or "[Não encontrado]"
    heartbeat_text = msg_ctx.contexto_heartbeat or "[Não encontrado]"
    
    historico = _formatar_historico(msg_ctx.historico_conversa)
    
    prompt = f"""{NOME_ASSISTENTE_DISPLAY} v3.1 - Assistente Pessoal Inteligente
{'='*60}

DATA/HORA ATUAL: {data_hora}

═══════════════════════════════════════════════════════
QUEM EU SOU (SOUL.md - Minha Identidade Completa)
═══════════════════════════════════════════════════════
{soul_text}

═══════════════════════════════════════════════════════
QUEM É O USUÁRIO (USER.md - Perfil Completo)
═══════════════════════════════════════════════════════
{user_text}

═══════════════════════════════════════════════════════
MEMÓRIA E LIÇÕES (MEMORY.md - Experiência)
═══════════════════════════════════════════════════════
{memory_text}

═══════════════════════════════════════════════════════
STATUS ATUAL (HEARTBEAT.md - Hoje)
═══════════════════════════════════════════════════════
{heartbeat_text}

═══════════════════════════════════════════════════════
📋 CAIXA DE ENTRADA ATUAL (Lex Flow - NOTAS/TAREFAS REAIS)
═══════════════════════════════════════════════════════
{inbox_text}

═══════════════════════════════════════════════════════
HISTÓRICO DESTA CONVERSA (Últimas mensagens)
═══════════════════════════════════════════════════════
{historico}
═══════════════════════════════════════════════════════
MENSAGEM ATUAL DO USUÁRIO
═══════════════════════════════════════════════════════
{msg_ctx.mensagem_usuario}

═══════════════════════════════════════════════════════
SUA TAREFA AGORA
═══════════════════════════════════════════════════════

Você É o {NOME_ASSISTENTE_DISPLAY}, o cérebro pessoal do Lex.
Use TODO o contexto acima para responder de forma PERSONALIZADA.

🎯 REGRAS CRÍTICAS (OBRIGATÓRIAS):

📋 QUANDO USUÁRIO PERGUNTAR SOBRE NOTAS/TAREFAS EXISTENTES:
- Use a seção "CAIXA DE ENTRADA ATUAL" acima (dados REAIS do Lex Flow!)
- NÃO invente dados do HEARTBEAT.md (ele só tem planejamento, não tarefas reais)
- Se acao="buscar_info", liste o que tem na Caixa de Entrada
- Se estiver vazia, diga "Não há notas/tarefas no momento"

🤔 QUANDO USUÁRIO QUISER CRIAR ALGO (tarefa/nota):
- NUNCA execute direto! Use acao="clarificar"
- Pergunte: "Quer criar TAREFA ou NOTA?"
- Aguarde confirmação antes de criar

💬 FORMATO DA RESPOSTA (OBRIGATÓRIO):
- Use QUEBRAS DE LINHA entre parágrafos (\\n)
- Separe ideias com linhas em branco
- Use emojis MODERADAMENTE
- Máximo 6-8 linhas (seja conciso!)
- NÃO escreva tudo em uma linha só!

NSTRUCOES_MOVER_NOTAS = 
## REGRAS PARA MOVER/ORGANIZAR NOTAS (v3.5)

Quando o usuário pedir para MOVER, TRANSFERIR ou ORGANIZAR notas:

1. Identificar QUAL nota (por índice "item 1" ou título)
2. Identificar PARA ONDE (projeto "Canais Dark" ou área "Academia")
3. Se disser "converter em tarefa" → usar converter_tarefa=true
4. Sempre extrair:
   - criterio: título da nota ou número do item
   - destino: nome do projeto ou área
   - converter_tarefa: true/false

Exemplos de mensagens e como interpretar:
- "move item 1 para Canais Dark" → criterio="1", destino="Canais Dark"
- "mova Procurar imagens para área Y" → criterio="Procurar imagens", destino="Y"
- "transforme item 2 em tarefa no Canal Dark" → criterio="2", destino="Canal Dark", converter_tarefa=true

AÇÃO SEMPRE: "mover_nota"


Decida o que fazer:

1. CONVERSAR (saudação, pergunta casual, agradecimento)
2. CLARIFICAR (usuário quer criar algo, mas precisa confirmar)
3. CRIAR_TAREFA (SÓ se confirmado!)
4. CRIAR_NOTA (SÓ se confirmado!)
5. BUSCAR_INFO (perguntar sobre notas/tarefas → use CAIXA DE ENTRADA!)
6. DELETAR_NOTAS (apagar/remover notas da Caixa de Entrada)
7. MOVER_NOTA (mover nota da Caixa para área/projeto P.A.R.A)
8. GERAR_IDEIAS (pedir sugestões/criatividade)
9. CONSULTAR_METRICAS (pedir status/relatório)

═══════════════════════════════════════════════════════
FORMATO DE RESPOSTA (OBRIGATÓRIO - JSON)
═══════════════════════════════════════════════════════

Responda EXATAMENTE neste formato JSON (nada fora dele):

{{
  "acao": "conversar|clarificar|criar_tarefa|criar_nota|buscar_info|deletar_notas|mover_nota|gerar_ideias|consultar_metricas",
  "resposta": "Sua resposta natural aqui em português\\nUse quebras de linha entre parágrafos",
  "entidades": {{
      "conteudo": "o que foi dito (se for tarefa/nota)",
      "criterio": "palavra-chave para deletar (se for deletar_notas)",
      "destino": "área ou projeto de destino (se for mover_nota)",
      "converter_tarefa": false,
      "prazo": "prazo detectado (opcional)",
      "prioridade": "prioridade (opcional)",
      "projeto": "projeto relacionado (opcional)"
  }}
}}

Seu JSON:"""
    return prompt

def parsear_resposta_llm(resposta_raw: str) -> Dict[str, Any]:
    """Extrai o JSON da resposta do LLM."""
    if isinstance(resposta_raw, dict):
        return resposta_raw
    if not isinstance(resposta_raw, str):
        resposta_raw = str(resposta_raw)
    
    texto = resposta_raw.strip()
    padroes_json = [
        r'```json\s*(\{.*?\})\s*```',
        r'```\s*(\{.*?\})\s*```',
        r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',
    ]
    
    for padrao in padroes_json:
        match = re.search(padrao, texto, re.DOTALL | re.I)
        if match:
            try:
                json_str = match.group(1).strip()
                json_str = json_str.replace('\n', ' ').replace('\r', '')
                decisao = json.loads(json_str)
                if "acao" in decisao and "resposta" in decisao:
                    logger_brain.info(f"✅ [PARSE] JSON extraído: acao={decisao.get('acao')}")
                    return decisao
            except json.JSONDecodeError as e:
                logger_brain.debug(f"[PARSE] JSON inválido: {e}")
                continue
    
    logger_brain.warning("⚠️ [PARSE] Padrões JSON falharam, tentando extração individual...")
    resultado = {"acao": "conversar", "resposta": texto, "entidades": {}}
    
    match_acao = re.search(r'"acao"\s*:\s*"([^"]*)"', texto)
    if match_acao: resultado["acao"] = match_acao.group(1)
    
    match_resposta = re.search(r'"resposta"\s*:\s*"((?:[^"\\]|\\.)*)"', texto)
    if match_resposta:
        resultado["resposta"] = match_resposta.group(1).encode('utf-8').decode('unicode_escape')
        logger_brain.info(f"✅ [PARSE] Resposta extraída individualmente!")
    
    match_entidades = re.search(r'"entidades"\s*:\s*(\{.*?\})', texto, re.DOTALL)
    if match_entidades:
        try:
            entidades_str = match_entidades.group(1)
            resultado["entidades"] = json.loads(entidades_str)
        except:
            pass
            
    if resultado.get("acao") and resultado.get("resposta") and resultado.get("resposta") != texto:
        return resultado
        
    logger_brain.warning("⚠️ [PARSE] Não encontrou JSON, tratando como conversa")
    if '{' in texto and '}' in texto:
        linhas = [l for l in texto.split('\n') if not l.strip().startswith(('"', '{', '}', '[', ']'))]
        texto_limpo = '\n'.join(linhas).strip()
        resultado["resposta"] = texto_limpo if texto_limpo else "Entendi! Como posso te ajudar com isso? 😊"
    
    return resultado
