"""
================================================================================
BRAIN MIDDLEWARE v2.1 - Sistema de Detecção de Intenção
================================================================================

AUTOR: Mago-Usamn | DATA: 12/04/2026
STATUS: ✅ Produção
NOME DO ASSISTENTE: MAGO 🧙
================================================================================
"""

import re
import json
import logging
from typing import Optional, Dict, Any, List

from engine.brain_types import (
    logger_brain,
    TipoIntencao,
    NivelConfianca,
    IntencaoDetectada,
    ContextoConversa,
    RespostaBrain,
    NOME_ASSISTENTE,
    PADROES_ENTIDADES,
    converter_prazo,
    normalizar_prioridade,
    classificar_nivel_confianca,
    PrioridadeTarefa
)


class PalavrasChave:
    """Palavras-chave expandidas para detecção de intenções."""
    
    CAPACIDADES: Dict[TipoIntencao, List[str]] = {
        TipoIntencao.CRIAR_NOTA: [
            "anota", "anote", "anotar", "nota", "notar",
            "escreve", "escrever", "escreva",
            "registra", "registrar", "registre",
            "guarda", "guardar", "guarde", "salva", "salvar", "salve",
            "grave", "gravar", "grava",
            "nota aí", "nota ai", "registra aí", "guarda isso", "salva isso",
            "anotado", "registrado", "guardado", "salvo",
            "isso é importante", "nao esquecer isso", "lembrete", "aponta", "marcar",
            "bota aí", "coloca aí", "joga aí",
        ],
        
        TipoIntencao.CRIAR_TAREFA: [
            "lembra", "lembrar", "lembre", "lembra-me", "lembrar-me",
            "lembra de", "lembrar de", "lembre de",
            "nao esquece", "não esquece", "nao esquecer", "não esquecer",
            "nao esqueça", "não esqueça", "recorda", "recordar",
            "preciso", "tenho que", "tenho de", "tenho q",
            "precisa", "tem que", "tem de", "tem q",
            "vo fazer", "vou fazer", "vai fazer", "vamos fazer",
            "preciso terminar", "preciso fazer", "preciso criar",
            "terminar", "finalizar", "acabar", "concluir", "entregar",
            "completar", "fazer", "faça", "realizar", "executar",
            "criar tarefa", "nova tarefa", "adicionar tarefa",
            "até sexta", "ate sexta", "até segunda", "ate segunda",
            "até quinta", "ate quinta", "amanhã", "hoje",
            "essa semana", "esta semana", "proxima semana",
            "compromisso", "reuniao", "reunião", "evento", "entrega",
            "deadline", "prazo", "data limite", "lembrete", "alerta",
            "tenho que lembrar", "nao posso esquecer", "agenda", "agendar",
        ],
        
        TipoIntencao.BUSCAR_INFO: [
            "o que eu escrevi", "o que eu falei", "o que eu disse",
            "o que eu tenho", "o que eu anotei", "resuma", "me dê um resumo",
            "quais são", "como estão", "me mostre", "procure", "procurar",
            "busca", "buscar", "busque", "encontre", "encontrar", "ache", "achar",
            "cadê", "onde tá", "onde esta",
        ],
        
        TipoIntencao.GERAR_IDEIAS: [
            "ideias para", "ideias de", "ideias sobre",
            "sugira", "sugerir", "sugestao", "sugestão", "sugestões",
            "brainstorm", "brainstorming", "dê ideias", "da ideias",
            "crie ideias", "criar ideias", "me dá ideias", "me da ideias",
            "inspiração", "inspiracao", "inspire", "criatividade",
            "X ideias", "5 ideias", "10 ideias",
        ],
        
        TipoIntencao.CONSULTAR_METRICAS: [
            "como estão", "como estao", "como está", "como esta",
            "quanto fiz", "minhas métricas", "minhas metricas",
            "produtividade", "status do dia", "progresso", "como vai",
            "relatorio", "relatório", "resumo do dia", "painel", "dashboard",
        ],
        
        TipoIntencao.CRIAR_PLANO: [
            "plano para", "plano de", "estratégia de", "estrategia de",
            "como escalar", "roadmap", "roteiro", "plano de ação",
            "passo a passo", "como conseguir", "meta de", "objetivo de",
            "planejamento", "planejar", "planeje", "cronograma", "agenda",
        ]
    }


class NormalizadorMensagem:
    """Normaliza mensagens corrigindo erros ortográficos."""
    
    CORRECOES_ORTOGRAFICAS = [
        (r'\bateh\b', 'até'), (r'\bathe[eé]\b', 'até'),
        (r'\bate\b', 'até'), (r'\bnao\b', 'não'),
        (r'\bñ\b', 'não'), (r'\bvc\b', 'você'),
        (r'\btbm\b', 'também'), (r'\btb\b', 'também'),
        (r'\boq\b', 'o que'), (r'\bpq\b', 'porque'),
        (r'\bpqra\b', 'para'), (r'\bpra\b', 'para'),
        (r'\bj[aá]\b', 'já'), (r'\bt[aá]\b', 'tá'),
        (r'\bdp\b', 'depois'), (r'\bamanha\b', 'amanhã'),
        (r'\bsabado\b', 'sábado'),
    ]
    
    PREFIXOS_PARA_REMOVER = [
        r"^mago[,:\s]*",           # MAGO (novo nome!)
        r"^lex[,:\s]*",             # Lex (antigo - compatibilidade)
        r"^ei[,:\s]*", r"^olá[,:\s]*", r"^oi[,:\s]*",
        r"^anota\s+(?:aí\s+)?(?:que\s+)?",
        r"^anote\s+(?:aí\s+)?(?:que\s+)?",
        r"^lembra?\s+(?:de\s+|que\s+)?(?:que\s+)?(?:de\s+)?",
        r"^lembrar?\s+(?:de\s+|que\s+)?(?:que\s+)?(?:de\s+)?",
        r"^[aã]o\s+esquec[ae]\s+(?:de\s+)?(?:que\s+)?",
        r"^registra?\s+(?:aí\s+)?(?:que\s+)?",
        r"^preciso\s+(?:comprar|fazer|terminar|criar)\s+",
        r"^tenho\s+que\s+", r"^tenho\s+de\s+",
        r"^vou\s+", r"^vamos\s+", r"^terminar\s+",
        r"^finalizar\s+", r"^fazer\s+", r"^criar\s+",
        r"^buscar\s+", r"^busque\s+", r"^procure\s+",
        r"^gerar\s+", r"^me\s+d[eê]\s+", r"^me\s+da\s+",
        r"^quais?\s+s[aã]o\s+", r"^como\s+(?:est[aã]o|est[áa])\s+",
        r"^o\s+que\s+eu\s+", r"^resuma\s+",
        r"^plano\s+(?:para|de)\s+", r"^estrategia\s+(?:para|de)\s+",
        r"^ideias?\s+(?:para|sobre|de)\s+", r"^metricas?\s+",
    ]
    
    @classmethod
    def normalizar(cls, mensagem: str) -> str:
        msg = mensagem.strip()
        msg_lower = msg.lower()
        
        for pattern, replacement in cls.CORRECOES_ORTOGRAFICAS:
            msg_lower = re.sub(pattern, replacement, msg_lower, flags=re.IGNORECASE)
        
        if msg_lower:
            msg_normalizada = msg_lower[0].upper() + msg_lower[1:] if len(msg_lower) > 1 else msg_lower.upper()
        else:
            msg_normalizada = mensagem
        
        return msg_normalizada
    
    @classmethod
    def extrair_conteudo(cls, mensagem: str) -> str:
        conteudo = mensagem.strip()
        for prefixo in cls.PREFIXOS_PARA_REMOVER:
            conteudo = re.sub(prefixo, "", conteudo, flags=re.IGNORECASE).strip()
        conteudo = conteudo.rstrip("!?.")
        return conteudo if len(conteudo) > 2 else ""


class DetectorIntencao:
    """Detector de intenção usando análise híbrida (Keywords + LLM)."""
    
    def __init__(self, llm_client=None):
        self._llm = llm_client
        self._palavras_chave = PalavrasChave()
    
    def detectar(self, mensagem: str) -> IntencaoDetectada:
        mensagem_lower = mensagem.lower().strip()
        
        intencao_keyword = self._detectar_por_keywords(mensagem_lower)
        
        if intencao_keyword and intencao_keyword.confianca >= 0.75:
            entidades = ExtratorEntidades.extrair(mensagem)
            return IntencaoDetectada(
                tipo=intencao_keyword.tipo,
                confianca=intencao_keyword.confianca,
                entidades=entidades,
                texto_original=mensagem,
                requer_clarificacao=intencao_keyword.confianca < 0.85
            )
        
        try:
            intencao_llm = self._detectar_por_llm(mensagem)
            if intencao_llm:
                return intencao_llm
        except Exception as e:
            logger_brain.warning(f"⚠️ Falha na detecção via LLM: {e}")
        
        if intencao_keyword:
            entidades = ExtratorEntidades.extrair(mensagem)
            return IntencaoDetectada(
                tipo=intencao_keyword.tipo,
                confianca=intencao_keyword.confianca,
                entidades=entidades,
                texto_original=mensagem,
                requer_clarificacao=True
            )
        
        return IntencaoDetectada(
            tipo=TipoIntencao.DESCONHECIDA,
            confianca=0.0,
            entidades={},
            texto_original=mensagem,
            requer_clarificacao=True
        )
    
    def _detectar_por_keywords(self, mensagem_lower: str) -> Optional[IntencaoDetectada]:
        melhor_match = None
        melhor_score = 0.0
        
        for tipo_intencao, keywords in self._palavras_chave.CAPACIDADES.items():
            score = 0
            for keyword in keywords:
                if keyword in mensagem_lower:
                    peso = len(keyword) / 10
                    score += peso
                    score += 0.3
            
            if score > melhor_score:
                melhor_score = score
                melhor_match = tipo_intencao
        
        if melhor_match and melhor_score > 0:
            confianca_base = min(0.90, max(0.25, melhor_score))
            if melhor_score > 1.5:
                confianca_base = min(0.95, confianca_base + 0.10)
            
            return IntencaoDetectada(tipo=melhor_match, confianca=confianca_base)
        
        return None
    
    def _detectar_por_llm(self, mensagem: str) -> Optional[IntencaoDetectada]:
        if not self._llm:
            return None
        
        prompt = f'''Analise a seguinte mensagem em PORTUGUÊS BRASILEIRO COLOQUIAL:

MENSAGEM: "{mensagem}"

INTENÇÕES POSSÍVEIS:
- criar_nota, criar_tarefa, buscar_info, gerar_ideias, consultar_metricas, criar_plano, conversar, desconhecida

RESPONDA APENAS EM JSON:
{{"intencao": "tipo", "confianca": 0.0-1.0, "entidades": {{"texto": "conteúdo"}}}}'''
        
        try:
            resposta = self._llm.gerar(prompt)
            json_match = re.search(r'\{[^{}]+\}', resposta)
            if json_match:
                dados = json.loads(json_match.group())
                tipo_str = dados.get("intencao", "desconhecida")
                try:
                    tipo = TipoIntencao(tipo_str)
                except ValueError:
                    tipo = TipoIntencao.DESCONHECIDA
                
                confianca = float(dados.get("confianca", 0.5))
                entidades = dados.get("entidades", {})
                if "texto" in entidades:
                    entidades["conteudo"] = entidades["texto"]
                
                return IntencaoDetectada(
                    tipo=tipo, confianca=confianca,
                    entidades=entidades, texto_original=mensagem,
                    requer_clarificacao=confianca < 0.70
                )
        except Exception as e:
            logger_brain.warning(f"⚠️ Erro ao parsear LLM: {e}")
        
        return None


class ExtratorEntidades:
    """Extrai entidades relevantes da mensagem."""
    
    @classmethod
    def extrair(cls, mensagem: str) -> Dict[str, Any]:
        entidades: Dict[str, Any] = {}
        mensagem_lower = mensagem.lower()
        
        prazo_match = re.search(PADROES_ENTIDADES["prazo"], mensagem_lower)
        if prazo_match:
            entidades["prazo"] = converter_prazo(prazo_match.group(1))
        
        prio_match = re.search(PADROES_ENTIDADES["prioridade"], mensagem_lower)
        if prio_match:
            entidades["prioridade"] = normalizar_prioridade(prio_match.group(1))
        
        qtd_match = re.search(PADROES_ENTIDADES["quantidade"], mensagem_lower)
        if qtd_match:
            entidades["quantidade"] = int(qtd_match.group(1))
        
        conteudo = NormalizadorMensagem.extrair_conteudo(mensagem)
        if conteudo:
            entidades["conteudo"] = conteudo
        
        projeto_match = re.search(PADROES_ENTIDADES["projeto"], mensagem_lower, re.IGNORECASE)
        if projeto_match:
            entidades["projeto_sugerido"] = projeto_match.group(1).strip()
        
        if any(p in mensagem_lower for p in ["canal dark", "dark", "youtube", "yt"]):
            entidades["projeto_sugerido"] = "Canais Dark"
        elif any(p in mensagem_lower for p in ["instagram", "ig", "influencer"]):
            entidades["projeto_sugerido"] = "Influencer AI"
        
        return entidades


class GeradorClarificacao:
    """Gera perguntas de clarificação inteligentes."""
    
    @staticmethod
    def gerar_pergunta_clarificacao(mensagem_original: str, intencao: IntencaoDetectada, ctx_conv: ContextoConversa) -> RespostaBrain:
        ctx_conv.tentativas_clarificacao += 1
        ctx_conv.aguardando_confirmacao = True
        ctx_conv.ultima_intencao = intencao.tipo
        ctx_conv.entidades_pendentes = intencao.entidades.copy()
        
        conteudo = intencao.entidades.get("conteudo", mensagem_original[:80])
        tipo = intencao.tipo
        
        if tipo == TipoIntencao.CRIAR_TAREFA:
            pergunta = f"""🤔 **Entendi parte do que você quer...**

Você disse algo sobre: *"{conteudo}"*

Quero confirmar: Isso é um **LEMBRETE/TAREFA**?

1️⃣ **Sim, criar TAREFA**
2️⃣ Na verdade é uma **NOTA**
3️⃣ Quero **editar** os detalhes
4️⃣ **Cancelar**"""
        elif tipo == TipoIntencao.CRIAR_NOTA:
            pergunta = f"""📝 **Quer salvar isso como anotação?**

*"{conteudo}"*

1️⃣ **Sim, salvar NOTA** ✅
2️⃣ Criar **TAREFA/LEMBRETE**
3️⃣ **BUSCAR** informações
4️⃣ **Cancelar**"""
        elif tipo == TipoIntencao.BUSCAR_INFO:
            pergunta = f"""🔍 **Buscar informações?**

Sobre: *"{conteudo}"*

1️⃣ **Sim, BUSCAR** 🔍
2️⃣ Refinar termo
3️⃣ **Cancelar**"""
        elif tipo == TipoIntencao.GERAR_IDEIAS:
            pergunta = f"""💡 **Gerar ideias criativas?**

Sobre: *"{conteudo}"*

1️⃣ **Sim, gerar IDEIAS** 🎨
2️⃣ Mudar tema
3️⃣ **Cancelar**"""
        else:
            pergunta = f"""🤔 **Deixe eu confirmar...**

Parece que você quer: *{tipo.value.replace('_', ' ').upper()}*
Sobre: *"{conteudo}"*

1️⃣ **Sim, EXECUTAR** ✅
2️⃣ **Não**, outra coisa
3️⃣ **Cancelar**"""
        
        ctx_conv.pergunta_pendente = pergunta
        
        return RespostaBrain(
            sucesso=True,
            acao_executada="clarificacao_pendente",
            resposta_ia=pergunta,
            requer_clarificacao=True,
            pergunta_clarificacao=pergunta
        )
    
    @staticmethod
    def gerar_pergunta_ajuda(mensagem_original: str, intencao: IntencaoDetectada, ctx_conv: ContextoConversa) -> RespostaBrain:
        ctx_conv.tentativas_clarificacao += 1
        ctx_conv.aguardando_confirmacao = True
        
        pergunta = f"""🤔 **Hmm, não tenho certeza do que você precisa...**

Você disse: *"{mensagem_original[:60]}"*

Mas posso te ajudar com várias coisas! O que você quer?

📝 **Criar NOTA** → "anota [algo]"
✅ **Criar TAREFA** → "lembra que tenho que [fazer]"
🔍 **BUSCAR informações** → "o que eu escrevi sobre [tema]?"
💡 **Gerar IDEIAS** → "me dá ideias sobre [tema]"
📊 **Ver MÉTRICAS** → "como estão minhas métricas?"
📋 **Criar PLANO** → "faz um plano para [objetivo]"

**É algum desses?** 😊"""
        
        ctx_conv.pergunta_pendente = pergunta
        
        return RespostaBrain(
            sucesso=True,
            acao_executada="ajuda_geral",
            resposta_ia=pergunta,
            requer_clarificacao=True,
            pergunta_clarificacao=pergunta
        )