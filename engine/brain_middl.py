"""
================================================================================
BRAIN MIDDLEWARE v2.1.1 - IA Assistente Pessoal CONVERSACIONAL
================================================================================

AUTOR: Mago-Usamn | DATA: 14/04/2026 (CORREÇÃO CRÍTICA!)
NOME DO ASSISTENTE: MAGO 🧙
VERSÃO: 2.1.1 (Fix: Classificador Agressivo + Conversacional)

MUDANÇAS v2.1.1:
✅ Sistema de CLARIFICAÇÃO ativo (pergunta antes de criar tarefas)
✅ Detecção de CONVERSA CASUAL (não transforma tudo em ação)
✅ Thresholds ajustados (só executa se for MUITO óbvio)
✅ Contexto de conversação mantido entre mensagens
✅ Respostas amigáveis e naturais

================================================================================
"""

import re
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass  # Type hints serão resolvidos em runtime

# Imports com TYPE_CHECKING para evitar circular imports
if TYPE_CHECKING:
    from engine.rag_system import RAGSystem
    from engine.llm_client import LLMClient
    from integrations.lex_flow_definitivo import LexFlowClient
    from engine.brain_acoes import ExecutorAcoes

from engine.brain_types import (
    logger_brain,
    TipoIntencao,
    IntencaoDetectada,
    ContextoConversa,
    RespostaBrain,
    NOME_ASSISTENTE,
    NOME_ASSISTENTE_DISPLAY,
    PrioridadeTarefa,
    converter_prazo_relativo,
    normalizar_texto,
    extrair_entidades
)


# =============================================================================
# CONSTANTES DE CONFIGURAÇÃO
# =============================================================================

# 🎯 THRESHOLDS DE CONFIANCA (AJUSTADOS v2.1.1!)
CONFIANCA_EXECUTAR_DIRETO = 0.92      # Só executa se for MUITO óbvio
CONFIANCA_CLARIFICACAO = 0.65         # Abaixo disso, pergunta
CONFIANCA_CONVERSA = 0.40             # Muito baixo = conversa casual

# 📏 LIMITES
TAMANHO_MINIMO_COMANDO = 15           # Mensagens menores que isso = conversa?
HISTORICO_MAXIMO_MENSAGENS = 10       # Memória curto prazo por usuário
TIMEOUT_CONTEXTO_HORAS = 2            # Limpa contexto após X horas


# =============================================================================
# PADRÕES DE DETECÇÃO (EXPANDIDOS v2.1.1)
# =============================================================================

class PadroesDetectacao:
    """Padrões regex para detectar intenções e conversas."""
    
    # 🔴 COMANDOS ÓBVIOS (executar direto - alta confiança)
    COMANDOS_OBVIOS_NOTA = [
        r"^(anota|nota|escreve|registra|salva)\b.*:",
        r"\b(anota ai|anota isto|anota isso|bota na lista)\b",
        r"^criar nota\b",
        r"^add:\s",
        r"^\*\*.*\*\*$",  # Markdown bold = título explícito
    ]
    
    COMANDOS_OBVIOS_TAREFA = [
        r"^(tarefa|task|criar tarefa|nova tarefa)\b.*:",
        r"\b(lembrar|lembra|nao esquece|não esquece)\b.*(ate|até|amanha|amanhã|semana|quinta|sexta)",
        r"\b(prazo|deadline|entregar|terminar|finalizar)\b.*(ate|até|amanha|hoje)",
    ]
    
    # 🟢 CONVERSA CASUAL (NÃO são comandos!)
    CONVERSA_CASUAL = [
        # Saudações
        r"^(eai|e ai|ei|oi|olá|ola|hey|hello|hi|salve|fala|opa|oie)\b",
        r"^(bom dia|boa tarde|boa noite|boa|bom|tarde|noite)\b",
        
        # Perguntas gerais
        r"^(como|qual|onde|quando|por que|porque|quem|o que|q)\b.*(voce|você|ta|está)",
        r"^(tudo bem|tudo bom|como vai|como esta|como c ta|como você ta)\b",
        
        # Respostas curtas
        r"^(sim|nao|não|ok|blz|beleza|claro|certo|obrigado|valeu|thanks|okk)\s*[!?.]*$",
        r"^(cancela|cancelar|esquece|ignora|deixa pra lá|deixa pra la)\b",
        
        # Expressões casuais
        r"^(haha|kkk|rsrs|hehe|lol|😂|👍|👎|❤️|🔥|💪|🙏)\s*[!?.]*$",
        r"^(legal|bacana|maneiro|top|show|daora|dahora|incrivel|maravilhoso)\s*[!?.]*$",
        r"^(me ajuda|ajuda|socorro|help|duvida|dúvida)\b",
        
        # Sobre o assistente
        r"(voce é|você é|quem é|seu nome|teu nome|como funciona)\b",
        r"(tudo bem com voce|tudo bem com você|como você está|voce ta bem)\b",
    ]
    
    # 🟡 INDICADORES DE AÇÃO (mas precisam de clarificação)
    INDICADORES_ACAO = [
        r"\b(preciso|precisei|tenho que|tenho q|tenho de|gostaria)\b",
        r"\b(terminar|finalizar|concluir|acabar|fazer|criar|desenvolver)\b",
        r"\b(comprar|adquirir|arrumar|consertar|organizar)\b",
        r"\b(lembra|lembrar|lembrete|reminder|nao esqueça|não esqueça)\b",
    ]


@dataclass
class EstadoClarificacao:
    """Estado quando estamos esperando resposta do usuário."""
    intencao_original: IntencaoDetectada
    entidades: Dict[str, Any]
    tipo_esperado: str  # "sim_nao", "escolha_tarefa_nota", "detalhes"
    timestamp: datetime = field(default_factory=datetime.now)
    tentativas: int = 0
    
    def expirado(self) -> bool:
        return (datetime.now() - self.timestamp).total_seconds() > (TIMEOUT_CONTEXTO_HORAS * 3600)


class BrainMiddleware:
    """
    Cérebro Inteligente v2.1.1 - IA Assistente Pessoal CONVERSACIONAL.
    
    Diferença crítica v2.1 vs v2.1.1:
    - v2.1: Classificador agressivo → transformava TUDO em tarefa ❌
    - v2.1.1: Conversacional → pergunta, clarifica, conversa ✅
    
    Funcionalidades:
    - Entende português natural (coloquial, erros, gírias)
    - Pergunta quando não tem certeza (sistema de clarificação)
    - Mantém contexto de conversação por usuário
    - Só executa ações após confirmação ou comando óbvio
    """
    
    def __init__(self):
        self._llm: Optional["LLMClient"] = None
        self._rag: Optional["RAGSystem"] = None
        self._lexflow: Optional["LexFlowClient"] = None
        self._executor: Optional["ExecutorAcoes"] = None
        
        # 🧠 Contextos de conversação por usuário
        self._contextos_usuarios: Dict[int, ContextoConversa] = {}
        self._clarificacoes_pendentes: Dict[int, EstadoClarificacao] = {}
        
        self._inicializado = False
        logger_brain.info("🧠 [v2.1.1] BrainMiddleware instanciado (modo CONVERSACIONAL)")
    
    def inicializar(self, llm_client=None, rag_system=None, lexflow_client=None) -> bool:
        """Inicializa o cérebro com as dependências."""
        try:
            self._llm = llm_client
            self._rag = rag_system
            self._lexflow = lexflow_client
            
            # Inicializar executor de ações
            if all([self._lexflow, self._llm, self._rag]):
                from engine.brain_acoes import ExecutorAcoes
                self._executor = ExecutorAcoes(self._lexflow, self._llm, self._rag)
                logger_brain.info("✅ [v2.1.1] ExecutorAcoes inicializado")
            
            self._inicializado = True
            logger_brain.info(f"✅ [v2.1.1] BrainMiddleware PRONTO! (modo conversacional ativo)")
            return True
            
        except Exception as e:
            logger_brain.error(f"❌ [v2.1.1] Erro na inicialização: {e}", exc_info=True)
            return False
    
    # =========================================================================
    # MÉTODO PRINCIPAL - PROCESSAR MENSAGEM
    # =========================================================================
    
    def processar(self, mensagem: str, contexto: Optional[Dict[str, Any]] = None) -> RespostaBrain:
        """
        Processa mensagem do usuário com INTELIGÊNCIA CONVERSACIONAL.
        
        Fluxo v2.1.1:
        1. Verificar se há clarificação pendente (usuário respondendo pergunta)
        2. Normalizar texto (corrigir erros, gírias)
        3. Detectar se é CONVERSA CASUAL vs COMANDO
        4. Se comando: detectar intenção e avaliar confiança
        5. Se confiança alta E comando óbvio → EXECUTAR
        6. Se confiança média → CLARIFICAR (perguntar!)
        7. Se confiança baixa ou conversa → CONVERSAR/DESCONHECIDO
        """
        usuario_id = contexto.get("usuario_id") if contexto else None
        
        logger_brain.info(f"🧠 [v2.1.1] NOVA MENSAGEM: '{mensagem[:60]}...' (user: {usuario_id})")
        
        try:
            # 1️⃣ VERIFICAR CLARIFICAÇÃO PENDENTE
            if usuario_id and usuario_id in self._clarificacoes_pendentes:
                resultado = self._processar_resposta_clarificacao(mensagem, usuario_id)
                if resultado:
                    return resultado
            
            # 2️⃣ NORMALIZAR TEXTO
            msg_normalizada = normalizar_texto(mensagem)
            logger_brain.info(f"📝 Normalizado: '{msg_normalizada[:50]}...'")
            
            # 3️⃣ DETECTAR SE É CONVERSA CASUAL
            if self._eh_conversa_casual(mensagem, msg_normalizada):
                logger_brain.info("💬 Detectado: CONVERSA CASUAL")
                return self._gerar_resposta_conversacional(mensagem, msg_normalizada, usuario_id)
            
            # 4️⃣ DETECTAR INTENÇÃO
            intencao = self._detectar_intencao_inteligente(mensagem, msg_normalizada)
            logger_brain.info(f"🎯 Intenção: {intencao.tipo.value} ({intencao.confianca:.2f})")
            
            # 5️⃣ DECIDIR AÇÃO BASEADA NA CONFIANÇA
            return self._decisao_inteligente(intencao, mensagem, usuario_id)
            
        except Exception as e:
            logger_brain.error(f"❌ [v2.1.1] Erro no processamento: {e}", exc_info=True)
            return RespostaBrain(
                sucesso=False,
                acao_executada="erro",
                resposta_ia=f"❌ Ops! Deu um problema aqui: {str(e)[:50]} 😅",
                erro=str(e)
            )
    
    # =========================================================================
    # SISTEMA DE CLARIFICAÇÃO (NOVO v2.1.1!)
    # =========================================================================
    
    def _processar_resposta_clarificacao(self, mensagem: str, usuario_id: int) -> Optional[RespostaBrain]:
        """
        Processa resposta do usuário a uma pergunta de clarificação.
        
        Exemplo:
        Bot: "Quer criar TAREFA ou NOTA?"
        User: "tarefa" → Executar criar_tarefa
        User: "nota" → Executar criar_nota
        User: "cancela" → Cancelar operação
        """
        estado = self._clarificacoes_pendentes.get(usuario_id)
        
        if not estado or estado.expirado():
            if estado and estado.expirado():
                del self._clarificacoes_pendentes[usuario_id]
                logger_brain.info(f"⏰ Clarificação expirada para user {usuario_id}")
            return None
        
        estado.tentativas += 1
        msg_lower = mensagem.lower().strip()
        
        logger_brain.info(f"💬 Usuário respondendo clarificação: '{mensagem}' (tentativa {estado.tentativas})")
        
        # === RESPOSTAS DE CANCELAMENTO ===
        if any(x in msg_lower for x in ["cancela", "cancelar", "esquece", "ignora", "deixa", "não", "nao", "não quero", "nao quero"]):
            del self._clarificacoes_pendentes[usuario_id]
            return RespostaBrain(
                sucesso=True,
                acao_executada="cancelado",
                resposta_ia="👍 *Beleza, cancelado!* Se precisar de algo, é só chamar! 😊"
            )
        
        # === RESPOSTAS POR TIPO DE CLARIFICAÇÃO ===
        
        if estado.tipo_esperado == "escolha_tarefa_nota":
            return self._processar_escolha_tarefa_nota(mensagem, msg_lower, estado, usuario_id)
        
        elif estado.tipo_esperado == "sim_nao":
            return self._processar_resposta_sim_nao(mensagem, msg_lower, estado, usuario_id)
        
        elif estado.tipo_esperado == "detalhes":
            return self._processar_detalhes_adicionais(mensagem, estado, usuario_id)
        
        # === TENTATIVAS ESGOTADAS ===
        if estado.tentativas >= 3:
            del self._clarificacoes_pendentes[usuario_id]
            return RespostaBrain(
                sucesso=True,
                acao_executada="clarificacao_expirada",
                resposta_ia="😅 *Não entendi...* Vamos recomeçar! O que você precisa? (pode escrever de outra forma)"
            )
        
        # === NÃO ENTENDEU A RESPOSTA ===
        return RespostaBrain(
            sucesso=True,
            acao_executada="clarificacao_repetir",
            resposta_ia=f"""🤔 *Hmm, não entendi totalmente...*

Você disse: "{mensagem}"

💡 *Opções:*
• `tarefa` → Criar tarefa com lembrete
• `nota` → Apenas anotar
• `cancela` → Desistir

Ou descreva melhor o que quer! 😊"""
        )
    
    def _processar_escolha_tarefa_nota(self, mensagem, msg_lower, estado, usuario_id) -> RespostaBrain:
        """Processa escolha entre tarefa e nota."""
        
        # Escolheu TAREFA
        if any(x in msg_lower for x in ["tarefa", "task", "lembrete", "reminder", "lembrar", "alerta"]):
            del self._clarificacoes_pendentes[usuario_id]
            
            # Modificar intenção original para tarefa
            estado.intencao_original.tipo = TipoIntencao.CRIAR_TAREFA
            
            logger_brain.info(f"✅ Usuário escolheu TAREFA")
            
            # Executar com o executor
            if self._executor:
                return self._executor.executar(estado.intencao_original, mensagem, {"usuario_id": usuario_id})
        
        # Escolheu NOTA
        elif any(x in msg_lower for x in ["nota", "note", "anotar", "anota", "apenas anotar", "so anota", "só anota"]):
            del self._clarificacoes_pendentes[usuario_id]
            
            # Modificar intenção original para nota
            estado.intencao_original.tipo = TipoIntencao.CRIAR_NOTA
            
            logger_brain.info(f"✅ Usuário escolheu NOTA")
            
            if self._executor:
                return self._executor.executar(estado.intencao_original, mensagem, {"usuario_id": usuario_id})
        
        # Forneceu detalhes adicionais (prazo, prioridade, etc.)
        elif any(x in msg_lower for x in ["urgente", "alta", "baixa", "media", "média", "prioridade", 
                                           "hoje", "amanha", "amanhã", "semana", "quinta", "sexta",
                                           "manhã", "tarde", "noite"]):
            # Adicionar detalhes às entidades
            estado.entidades["detalhes_extra"] = mensagem
            estado.tipo_esperado = "confirmar_execucao"
            
            logger_brain.info(f"📝 Usuário adicionou detalhes: {mensagem}")
            
            return RespostaBrain(
                sucesso=True,
                acao_executada="clarificacao_detalhes",
                resposta_ia=f"""👍 *Entendi!*

📋 **Detalhes:** {mensagem}

⚡ *Vou criar a TAREFA com esses detalhes.*

✅ Confirmar? (responda `sim` ou `cancela`)""",
                aguardando_resposta=True
            )
        
        # Não reconheceu
        return None  # Cairá no padrão "não entendi"
    
    def _processar_resposta_sim_nao(self, mensagem, msg_lower, estado, usuario_id) -> RespostaBrain:
        """Processa resposta sim/não."""
        
        if any(x in msg_lower for x in ["sim", "yes", "y", "ok", "blz", "claro", "certo", "confirmar", "pode", "vai"]):
            del self._clarificacoes_pendentes[usuario_id]
            logger_brain.info(f"✅ Usuário CONFIRMOU execução")
            
            if self._executor:
                return self._executor.executar(estado.intencao_original, mensagem, {"usuario_id": usuario_id})
        
        else:
            del self._clarificacoes_pendentes[usuario_id]
            return RespostaBrain(
                sucesso=True,
                acao_executada="cancelado_usuario",
                resposta_ia="👍 *Beleja, não vou fazer nada então!* Se mudar de ideia, é só falar! 😊"
            )
    
    def _processar_detalhes_adicionais(self, mensagem, estado, usuario_id) -> RespostaBrain:
        """Processa detalhes adicionais fornecidos pelo usuário."""
        estado.entidades["detalhes_extra"] = mensagem
        del self._clarificacoes_pendentes[usuario_id]
        
        # Atualizar intenção original com detalhes
        conteudo_original = estado.entidades.get("conteudo", "")
        estado.entidades["conteudo"] = f"{conteudo_original}\n\n{mensagem}"
        
        logger_brain.info(f"📝 Detalhes adicionados, executando...")
        
        if self._executor:
            return self._executor.executar(estado.intencao_original, mensagem, {"usuario_id": usuario_id})
    
    def _solicitar_clarificacao(self, intencao: IntencaoDetectada, mensagem: str, usuario_id: int) -> RespostaBrain:
        """
        Gera pergunta de clarificação para o usuário.
        
        Esta é a FUNÇÃO CHAVE que faz o bot ser CONVERSACIONAL!
        """
        conteudo = intencao.entidades.get("conteudo", mensagem)
        conteudo_curto = conteudo[:60] + ("..." if len(conteudo) > 60 else "")
        
        # Determinar tipo de pergunta baseado na intenção
        if intencao.tipo == TipoIntencao.CRIAR_TAREFA:
            tipo_pergunta = "escolha_tarefa_nota"
            resposta = f"""🤔 *Deixa eu ver se entendi...*

Você quer registrar: **{conteudo_curto}**

📋 *Quer criar uma TAREFA* (com lembrete/prazo)?
📝 *Ou é apenas uma NOTA* simples?

💡 *Responda:*
• `tarefa` → Vou criar tarefa
• `nota` → Só vou anotar
• Ou me dê mais detalhes (ex: "pra sexta", "urgente")"""
        
        elif intencao.tipo == TipoIntencao.CRIAR_NOTA:
            tipo_pergunta = "confirmar_anotacao"
            resposta = f"""📝 *Vou anotar isso:*

**{conteudo_curto}**

✅ *Confirmar?* (`sim` / `cancela`)
💡 Quer adicionar mais alguma informação?"""
        
        else:
            tipo_pergunta = "geral"
            resposta = f"""🤔 *Tenho quase certeza que você quer...*

{intencao.tipo.value.replace('_', ' ').title()}: **{conteudo_curto}**

✅ *Isso mesmo?* (`sim` / `nao` / `cancela`)"""
        
        # Salvar estado de clarificação
        self._clarificacoes_pendentes[usuario_id] = EstadoClarificacao(
            intencao_original=intencao,
            entidades=intencao.entidades.copy(),
            tipo_esperado=tipo_pergunta
        )
        
        logger_brain.info(f"🤔 Clarificação solicitada (tipo: {tipo_pergunta})")
        
        return RespostaBrain(
            sucesso=True,
            acao_executada="clarificacao",
            resposta_ia=resposta,
            aguardando_resposta=True,
            clarificacao_pendente=True
        )
    
    # =========================================================================
    # DETECÇÃO DE INTENÇÕES (MELHORADA v2.1.1)
    # =========================================================================
    
    def _detectar_intencao_inteligente(self, mensagem: str, msg_norm: str) -> IntencaoDetectada:
        """
        Detecta intenção de forma INTELIGENTE (não agressiva).
        
        v2.1.1: Usa múltiplos sinais, não só keywords!
        """
        msg_lower = mensagem.lower()
        msg_norm_lower = msg_norm.lower()
        
        # Extrair entidades primeiro
        entidades = extrair_entidades(mensagem)
        
        # Pontuação por tipo de intenção
        scores = {
            TipoIntencao.CRIAR_TAREFA: 0.0,
            TipoIntencao.CRIAR_NOTA: 0.0,
            TipoIntencao.BUSCAR_INFO: 0.0,
            TipoIntencao.GERAR_IDEIAS: 0.0,
            TipoIntencao.CONSULTAR_METRICAS: 0.0,
            TipoIntencao.CRIAR_PLANO: 0.0,
            TipoIntencao.CONVERSAR: 0.0,
            TipoIntencao.DESCONHECIDA: 0.0,
        }
        
        # === VERIFICAR COMANDOS ÓBVIOS (PONTUAÇÃO ALTA) ===
        
        # Comandos óbvios de NOTA
        for padrao in PadroesDetectacao.COMANDOS_OBVIOS_NOTA:
            if re.search(padrao, msg_lower, re.I):
                scores[TipoIntencao.CRIAR_NOTA] += 0.6
        
        # Comandos óbvios de TAREFA (com prazo explícito!)
        for padrao in PadroesDetectacao.COMANDOS_OBVIOS_TAREFA:
            if re.search(padrao, msg_lower, re.I):
                scores[TipoIntencao.CRIAR_TAREFA] += 0.7
        
        # === VERIFICAR INDICADORES DE AÇÃO (PONTUAÇÃO MÉDIA) ===
        
        indicadores_encontrados = []
        for padrao in PadroesDetectacao.INDICADORES_ACAO:
            if re.search(padrao, msg_lower, re.I):
                indicadores_encontrados.append(padrao)
        
        if indicadores_encontrados:
            # Tem indicadores de ação, mas NÃO é comando óbvio
            # → Pontuação média (vai cair na clarificação!)
            score_base = 0.4 + (len(indicadores_encontrados) * 0.05)
            scores[TipoIntencao.CRIAR_TAREFA] = max(scores[TipoIntencao.CRIAR_TAREFA], score_base)
            scores[TipoIntencao.CRIAR_NOTA] = max(scores[TipoIntencao.CRIAR_NOTA], score_base * 0.9)
        
        # === DETECTAR OUTRAS INTENÇÕES ESPECÍFICAS ===
        
        # Buscar info
        if any(x in msg_lower for x in ["o que eu", "já escrevi", "falei sobre", "procuro por", 
                                         "buscando", "procurando", "tem algo sobre", "lembra sobre"]):
            scores[TipoIntencao.BUSCAR_INFO] += 0.7
        
        # Gerar ideias
        if any(x in msg_lower for x in ["ideias", "idéias", "ideia para", "sugestões", "sugestoes",
                                         "criativo", "inspiração", "inspiracao", "conteúdo", "conteudo"]):
            scores[TipoIntencao.GERAR_IDEIAS] += 0.7
        
        # Métricas/status
        if any(x in msg_lower for x in ["métricas", "metricas", "status", "relatório", "relatorio",
                                         "como estão", "como estao", "resumo", "painel"]):
            scores[TipoIntencao.CONSULTAR_METRICAS] += 0.7
        
        # Plano/estratégia
        if any(x in msg_lower for x in ["plano", "planejar", "estratégia", "estrategia",
                                         "roteiro", "projeto para", "meta para"]):
            scores[TipoIntencao.CRIAR_PLANO] += 0.7
        
        # === AJUSTE FINAL: VERIFICAR SE É REALMENTE AÇÃO OU SÓ CONVERSÃO ===
        
        # Se a mensagem é muito curta e não tem verbos de ação fortes → provavelmente conversa
        if len(mensagem) < TAMANHO_MINIMO_COMANDO:
            max_score = max(scores.values())
            if max_score < 0.5:  # Baixa confiança geral
                scores[TipoIntencao.CONVERSAR] = 0.6
                scores[TipoIntencao.DESCONHECIDA] = 0.3
        
        # === DETERMINAR VENCEDOR ===
        
        tipo_vencedor = max(scores, key=scores.get)
        confianca_vencedor = scores[tipo_vencedor]
        
        # Ajuste final de confiança (não deixar muito alto para ações)
        if tipo_vencedor in [TipoIntencao.CRIAR_TAREFA, TipoIntencao.CRIAR_NOTA]:
            # Se não é comando óbvio, CAPAR confiança em 0.75 (força clarificação!)
            eh_obvio = (
                scores[tipo_vencedor] >= 0.6 or
                any(re.search(p, msg_lower, re.I) for p in PadroesDetectacao.COMANDOS_OBVIOS_NOTA + PadroesDetectacao.COMANDOS_OBVIOS_TAREFA)
            )
            
            if not eh_obvio and confianca_vencedor > 0.75:
                confianca_vencedor = 0.75  # Força clarificação!
        
        logger_brain.info(f"📊 Scores: {[(k.value, f'{v:.2f}') for k,v in scores.items() if v > 0]}")
        
        return IntencaoDetectada(
            tipo=tipo_vencedor,
            confianca=confianca_vencedor,
            entidades=entidades,
            texto_original=mensagem,
            texto_normalizado=msg_norm
        )
    
    def _eh_conversa_casual(self, mensagem: str, msg_norm: str) -> bool:
        """
        Detecta se a mensagem é CONVERSA CASUAL (não é um comando).
        
        Esta função é CRÍTICA para evitar criar tarefas para tudo!
        """
        msg_lower = mensagem.lower().strip()
        
        # 1. Mensagem muito curta (provavelmente resposta rápida)
        if len(msg_lower) < 10:
            for padrao in PadroesDetectacao.CONVERSA_CASUAL:
                if re.match(padrao, msg_lower, re.I):
                    return True
        
        # 2. Padrões de conversa (em qualquer tamanho)
        for padrao in PadroesDetectacao.CONVERSA_CASUAL:
            if re.match(padrao, msg_lower, re.I):
                return True
        
        # 3. Perguntas sobre o assistente (sem verbos de ação)
        if re.search(r"(voce|você|vc)\b.*(é|pode|sabe|ajuda|ajudar)", msg_lower, re.I):
            if not any(re.search(p, msg_lower, re.I) for p in PadroesDetectacao.INDICADORES_ACAO):
                return True
        
        return False
    
    def _decisao_inteligente(self, intencao: IntencaoDetectada, mensagem: str, usuario_id: int) -> RespostaBrain:
        """
        Tomada de decisão INTELIGENTE baseada na confiança.
        
        LÓGICA v2.1.1:
        - Confiança > 0.90 E comando óbvio → EXECUTAR DIRETO
        - Confiança 0.50-0.90 → CLARIFICAR (PERGUNTAR!)
        - Confiança < 0.50 → CONVERSAR ou DESCONHECIDO
        """
        confianca = intencao.confianca
        tipo = intencao.tipo
        
        logger_brain.info(f"🧠 Decisão: conf={confianca:.2f}, tipo={tipo.value}")
        
        # === CASO 1: EXECUTAR DIRETO (só se for MUITO óbvio!) ===
        if confianca >= CONFIANCA_EXECUTAR_DIRETO:
            # Verificação extra: é realmente óbvio?
            msg_lower = mensagem.lower()
            comando_obvio = (
                any(re.search(p, msg_lower, re.I) for p in PadroesDetectacao.COMANDOS_OBVIOS_NOTA) or
                any(re.search(p, msg_lower, re.I) for p in PadroesDetectacao.COMANDOS_OBVIOS_TAREFA) or
                tipo in [TipoIntencao.BUSCAR_INFO, TipoIntencao.GERAR_IDEIAS, 
                        TipoIntencao.CONSULTAR_METRICAS, TipoIntencao.CRIAR_PLANO]
            )
            
            if comando_obvio:
                logger_brain.info(f"⚡ Execução direta (comando óbvio): {tipo.value}")
                
                if self._executor:
                    return self._executor.executar(intencao, mensagem, {"usuario_id": usuario_id})
        
        # === CASO 2: CLARIFICAR (PERGUNTAR ANTES DE AGIR!) ===
        if confianca >= CONFIANCA_CLARIFICACAO and tipo in [TipoIntencao.CRIAR_TAREFA, TipoIntencao.CRIAR_NOTA]:
            logger_brain.info(f"🤔 Clarificação necessária (confiança média): {tipo.value}")
            return self._solicitar_clarificacao(intencao, mensagem, usuario_id)
        
        # === CASO 3: PARA OUTRAS INTENÇÕES COM MÉDIA CONFIANÇA ===
        if confianca >= CONFIANCA_CLARIFICACAO:
            logger_brain.info(f"⚡ Execução para intenção não-crítica: {tipo.value}")
            
            if self._executor:
                return self._executor.executar(intencao, mensagem, {"usuario_id": usuario_id})
        
        # === CASO 4: CONVERSA CASUAL ou DESCONHECIDO ===
        if tipo == TipoIntencao.CONVERSAR:
            return self._gerar_resposta_conversacional(mensagem, "", usuario_id)
        
        # Desconhecido com sugestões
        return self._gerar_resposta_desconhecida(mensagem)
    
    # =========================================================================
    # GERADORES DE RESPOSTA
    # =========================================================================
    
    def _gerar_resposta_conversacional(self, mensagem: str, msg_norm: str, usuario_id: Optional[int]) -> RespostaBrain:
        """Gera resposta conversacional amigável."""
        
        msg_lower = mensagem.lower().strip()
        
        # Saudações
        if any(re.match(p, msg_lower, re.I) for p in [
            r"^(eai|e ai|ei|oi|olá|ola|hey|hello|hi|salve|fala|opa|oie)\b",
            r"^(bom dia|boa tarde|boa noite)\b"
        ]):
            hora = datetime.now().hour
            if hora < 12: saudacao_tempo = "Bom dia!"
            elif hora < 18: saudacao_tempo = "Boa tarde!"
            else: saudacao_tempo = "Boa noite!"
            
            resposta = f"""{saudacao_tempo} ☀️

Sou o **{NOME_ASSISTENTE_DISPLAY}**, seu assistente pessoal! 🧙

Como posso te ajudar agora?

💡 *Exemplos:*
• "Mago, **anota**: comprar microfone"
• "**Lembra** de terminar o vídeo **sexta**"
• "**Quais ideias** para vídeo sobre automação?"
• "**O que eu escrevi** sobre YouTube?"

Estou por aqui! 😊"""
            
            return RespostaBrain(sucesso=True, acao_executada="conversar", resposta_ia=resposta)
        
        # Perguntas "como você está"
        if any(x in msg_lower for x in ["tudo bem", "tudo bom", "como vai", "como você está", "como vc ta"]):
            return RespostaBrain(
                sucesso=True,
                acao_executada="conversar",
                resposta_ia=f"""Tudo certo por aqui! 💪 Operando normalmente!

E você, como estão os projetos? Precisa de ajuda com algo específico?

📋 *Posso:* Criar tarefas, anotar ideias, buscar informações ou gerar conteúdo!

É só pedir! 😊"""
            )
        
        # Agradecimentos
        if any(x in msg_lower for x in ["obrigado", "valeu", "thanks", "vlw", "grato"]):
            return RespostaBrain(
                sucesso=True,
                acao_executada="conversar",
                resposta_ia=f"Por nada! 😊 Sempre que precisar, é só chamar! {NOME_ASSISTENTE_DISPLAY} tá online! 🧙‍♂️"
            )
        
        # Despedidas
        if any(x in msg_lower for x in ["tchau", "ate logo", "até logo", "falou", "flw", "bye", "ate mais"]):
            return RespostaBrain(
                sucesso=True,
                acao_executada="conversar",
                resposta_ia=f"Até mais! 👋 Bom trabalho! {NOME_ASSISTENTE_DISPLAY} fica aqui caso precise! 🧙✨"
            )
        
        # Resposta genérica conversacional (usa LLM se disponível)
        if self._llm:
            try:
                prompt = f"""Você é o {NOME_ASSISTENTE_DISPLAY}, assistente pessoal amigável e prestativo.
O usuário disse: "{mensagem}"

Responda de forma natural, amigável, máximo 4 linhas.
Use emojis ocasionalmente. Seja útil mas conversacional.
NÃO pareça um robô!"""

                resposta_llm = self._llm.gerar(prompt)
                
                return RespostaBrain(
                    sucesso=True,
                    acao_executada="conversar_llm",
                    resposta_ia=resposta_llm
                )
            except Exception as e:
                logger_brain.warning(f"⚠️ Erro LLM conversacional: {e}")
        
        # Fallback sem LLM
        return RespostaBrain(
            sucesso=True,
            acao_executada="conversar_fallback",
            resposta_ia=f"""Interessante! 🤔

Não tenho certeza do que você quer dizer com "{mensagem[:30]}..."

Mas posso ajudar com:

📝 **Anotar** algo
✅ **Criar lembretes/tarefas**
🔍 **Buscar informações**
💡 **Gerar ideias**

Quer tentar de outro jeito? 😊"""
        )
    
    def _gerar_resposta_desconhecida(self, mensagem: str) -> RespostaBrain:
        """Gera resposta para intenção desconhecida com sugestões."""
        
        return RespostaBrain(
            sucesso=True,
            acao_executada="desconhecida",
            resposta_ia=f"""🤔 *Hum... não tenho certeza do que você quer*

Você disse: "{mensagem[:50]}"

💡 **Mas posso te ajudar assim:**

📝 `{NOME_ASSISTENTE}, anota: [algo]`
→ Cria uma nota rápida

✅ `{NOME_ASSISTENTE}, lembra de [fazer] [quando]`
→ Cria tarefa com prazo

🔍 `{NOME_ASSISTENTE}, o que eu escrevi sobre [tema]?`
→ Busca nas suas notas

💡 `{NOME_ASSISTENTE}, ideias sobre [assunto]`
→ Gera ideias criativas

**Como posso ajudar?** 😊"""
        )
    
    # =========================================================================
    # UTILITÁRIOS
    # =========================================================================
    
    def limpar_contexto_usuario(self, usuario_id: int) -> None:
        """Limpa contexto de conversação de um usuário."""
        if usuario_id in self._contextos_usuarios:
            del self._contextos_usuarios[usuario_id]
        if usuario_id in self._clarificacoes_pendentes:
            del self._clarificacoes_pendentes[usuario_id]
        logger_brain.info(f"🗑️ Contexto limpo para user {usuario_id}")
    
    def obter_estatisticas_v21(self) -> Dict[str, Any]:
        """Retorna estatísticas do modo conversacional v2.1.1."""
        return {
            "versao": "2.1.1",
            "modo": "CONVERSACIONAL_INTELIGENTE",
            "inicializado": self._inicializado,
            "contextos_ativos": len(self._contextos_usuarios),
            "clarificacoes_pendentes": len(self._clarificacoes_pendentes),
            "threshold_executar": CONFIANCA_EXECUTAR_DIRETO,
            "threshold_clarificar": CONFIANCA_CLARIFICACAO,
            "recursos": {
                "llm": self._llm is not None,
                "rag": self._rag is not None,
                "lexflow": self._lexflow is not None,
                "executor": self._executor is not None
            }
        }


# =============================================================================
# INSTÂNCIA GLOBAL (Singleton Pattern)
# =============================================================================

_brain_middleware_global: Optional[BrainMiddleware] = None


def obter_brain_middleware_global() -> Optional[BrainMiddleware]:
    """Retorna a instância global do Brain Middleware."""
    global _brain_middleware_global
    return _brain_middleware_global


def definir_brain_middleware_global(instancia: BrainMiddleware) -> None:
    """Define a instância global do Brain Middleware."""
    global _brain_middleware_global
    _brain_middleware_global = instancia
    logger_brain.info(f"✅ [GLOBAL] Brain Middleware definido como instância global")


# =============================================================================
# FIM DO ARQUIVO
# =============================================================================