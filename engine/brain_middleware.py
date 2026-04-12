"""
============================================
BRAIN MIDDLEWARE v1.0 - IA Assistente Pessoal
============================================

Camada inteligente que transforma mensagens naturais em ações executadas pelo sistema.

Autor: Lex-Usamn
Data: 11/04/2026
Status: ✅ IMPLEMENTADO

Capacidades:
- 📝 Criar notas (intenção implícita)
- ✅ Criar tarefas (prazos, prioridades, projetos)
- 🔍 Buscar informações (RAG + análise)
- 💡 Gerar ideias (brainstorm com base nos dados)
- 📊 Consultar métricas e status
- 🎯 Criar planos e estratégias
- 🗣️ Transcrever e processar áudios

Integrações:
- LLM Client (GLM5/NVIDIA NIM) para entendimento de intenção
- RAG System para busca contextual de informações
- Lex Flow API para persistência de notas/tarefas
- Core Engine como orquestrador central
"""

import logging
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field


# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

logger_brain = logging.getLogger("brain_middleware")
logger_brain.setLevel(logging.DEBUG)

# Handler para arquivo de log
file_handler = logging.FileHandler(
    "logs/brain_middleware.log",
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)

# Formato detalhado
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(funcName)-25s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(formatter)

# Evita duplicação de handlers
if not logger_brain.handlers:
    logger_brain.addHandler(file_handler)


# ============================================================================
# ENUMERAÇÕES E TIPOS
# ============================================================================

class TipoIntencao(Enum):
    """Tipos de intenções que o Brain Middleware pode detectar."""
    
    CRIAR_NOTA = "criar_nota"
    CRIAR_TAREFA = "criar_tarefa"
    BUSCAR_INFO = "buscar_info"
    GERAR_IDEIAS = "gerar_ideias"
    CONSULTAR_METRICAS = "consultar_metricas"
    CRIAR_PLANO = "criar_plano"
    CONVERSAR = "conversar"
    DESCONHECIDA = "desconhecida"


class PrioridadeTarefa(Enum):
    """Níveis de prioridade para tarefas."""
    
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"


@dataclass
class IntencaoDetectada:
    """
    Representa uma intenção detectada na mensagem do usuário.
    
    Attributes:
        tipo: Tipo da intenção detectada
        confianca: Nível de confiança (0.0 a 1.0)
        entidades: Dados extraídos da mensagem (prazos, projetos, etc.)
        texto_original: Mensagem original do usuário
    """
    tipo: TipoIntencao
    confianca: float
    entidades: dict[str, Any] = field(default_factory=dict)
    texto_original: str = ""


@dataclass
class RespostaBrain:
    """
    Resposta completa do Brain Middleware.
    
    Attributes:
        sucesso: Se a ação foi executada com sucesso
        acao_executada: Tipo de ação que foi realizada
        resposta_ia: Texto de resposta para o usuario
        detalhes: Detalhes técnicos da execução
        sugestoes: Sugestões de ações adicionais
        erro: Mensagem de erro (se houver)
    """
    sucesso: bool
    acao_executada: str
    resposta_ia: str
    detalhes: dict[str, Any] = field(default_factory=dict)
    sugestoes: list[str] = field(default_factory=list)
    erro: Optional[str] = None


# ============================================================================
# CLASSE PRINCIPAL: BRAIN MIDDLEWARE
# ============================================================================

class BrainMiddleware:
    """
    CAMADA INTELIGENTE - O Cérebro do Sistema.
    
    Recebe: Mensagem natural do usuário (texto ou transcrição)
    Processa: GLM5 identifica intenção + extrai dados estruturados
    Executa: Chama RAG System, LLM Client, Lex Flow, etc.
    Responde: Confirmação do que foi feito + sugestões
    
    Example:
        >>> from engine.brain_middleware import BrainMiddleware
        >>> brain = BrainMiddleware()
        >>> resultado = brain.processar("Lex, anota que preciso comprar microfone")
        >>> print(resultado.resposta_ia)
        ✅ Nota criada: 'Comprar microfone'
        
    Attributes:
        _inicializado: Se o middleware foi inicializado
        _llm: Referência ao LLM Client
        _rag: Referência ao RAG System
        _lexflow: Referência ao Lex Flow Client
    """
    
    # Mapeamento de palavras-chave para cada tipo de intenção
    CAPACIDADES: dict[TipoIntencao, list[str]] = {
        TipoIntencao.CRIAR_NOTA: [
            "anota", "anote", "lembra disso", "nota aí", "registra", 
            "guarda isso", "salva", "escreve aí", "nota pra mim",
            "anotado", "registra aí"
        ],
        TipoIntencao.CRIAR_TAREFA: [
            "preciso", "tenho que", "lembra de", "até sexta", "lembre",
            "tem que", "preciso terminar", "preciso fazer", "vou fazer",
            "precisa ser feito", "deadline", "prazo", "entregar"
        ],
        TipoIntencao.BUSCAR_INFO: [
            "o que eu escrevi", "o que eu falei", "resuma", "me dê um plano",
            "quais são", "como estão", "me mostre", "procure", "busque",
            "encontre", "sobre o que", "já falei sobre", "tenho anotado"
        ],
        TipoIntencao.GERAR_IDEIAS: [
            "ideias para", "sugira", "brainstorm", "dê ideias",
            "crie ideias", "me dá ideias", "sugestões de", 
            "o que posso fazer", "conteúdo sobre"
        ],
        TipoIntencao.CONSULTAR_METRICAS: [
            "como estão", "quanto fiz", "minhas métricas", "produtividade",
            "status do dia", "como foi meu dia", "progresso",
            "quanto produzi", "rendimento"
        ],
        TipoIntencao.CRIAR_PLANO: [
            "plano para", "estratégia de", "como escalar", "roadmap",
            "plano de ação", "roteiro para", "passo a passo",
            "como conseguir", "meta de"
        ]
    }
    
    # Padrões regex para extração de entidades
    PADROES_ENTIDADES = {
        "prazo": r"(?:até|para|até\s+a)\s+(?:a\s+)?(?:(?:esta|essa|proxima?)\s+)?(segunda|terça|quarta|quinta|sexta|sabado|domingo|semana|mes|amanhã|hoje|\d{1,2}/\d{1,2}|\d{1,2}\s*de?\s*\w+)",
        "prioridade": r"(?:prioridade\s*:?\s*(alta|baixa|media|média|urgente)|urgente|importante|com\s*prioridade)",
        "projeto": r"(?:projeto|canal|para\s+o\s+|sobre\s+o\s+)(?:['\"]?)([\w\s&]+?)(?:['\"]?(?:\s|$|\.|,|\?))",
        "quantidade": r"(\d+)\s*(?:ideias?s|itens?|opçõe?s|tarefas?)",
    }
    
    def __init__(self):
        """Inicializa o Brain Middleware com lazy loading dos componentes."""
        self._inicializado: bool = False
        self._llm = None
        self._rag = None
        self._lexflow = None
        self._engine = None
        
        logger_brain.info("🧠 BrainMiddleware instanciado (aguardando inicialização)")
    
    def inicializar(self) -> bool:
        """
        Inicializa o middleware carregando as dependências do CoreEngine.
        
        Returns:
            True se inicializado com sucesso, False caso contrário
        """
        try:
            # Importação tardia para evitar circular imports
            from engine.core_engine import CoreEngine
            
            logger_brain.info("🔄 Inicializando Brain Middleware...")
            
            # Obtém instância Singleton do Engine
            self._engine = CoreEngine.obter_instancia()
            
            # Carrega componentes via lazy loading
            self._llm = self._engine.llm_client
            self._rag = self._engine.sistema_rag
            self._lexflow = self._engine.lexflow
            
            self._inicializado = True
            
            logger_brain.info("✅ Brain Middleware inicializado com sucesso!")
            logger_brain.info(f"   🤖 LLM: {type(self._llm).__name__}")
            logger_brain.info(f"   🔍 RAG: {type(self._rag).__name__}")
            logger_brain.info(f"   🌐 LexFlow: {type(self._lexflow).__name__}")
            
            return True
            
        except Exception as e:
            logger_brain.error(f"❌ Erro ao inicializar Brain Middleware: {e}")
            self._inicializado = False
            return False
    
    def _garantir_inicializacao(self) -> bool:
        """
        Garante que o middleware está inicializado.
        
        Returns:
            True se inicializado ou se conseguiu inicializar
        """
        if not self._inicializado:
            return self.inicializar()
        return True
    
    # =========================================================================
    # MÉTODO PRINCIPAL: PROCESSAR MENSAGEM
    # =========================================================================
    
    def processar(self, mensagem: str, contexto: Optional[dict] = None) -> RespostaBrain:
        """
        Processa mensagem natural e retorna ação executada.
        
        Este é o método principal do Brain Middleware. Recebe uma mensagem
        em linguagem natural, detecta a intenção, extrai entidades e
        executa a ação apropriada.
        
        Args:
            mensagem: Texto da mensagem do usuário
            contexto: Informações adicionais opcionais (chat_id, user_id, etc.)
        
        Returns:
            RespostaBrain com resultado da processamento
        
        Example:
            >>> brain = BrainMiddleware()
            >>> brain.inicializar()
            >>> resultado = brain.processar("Lex, anota que preciso comprar microfone")
            >>> print(resultado.resposta_ia)
            ✅ Nota criada: 'Comprar microfone Blue Yeti para Canal Dark'
        """
        
        logger_brain.info("=" * 60)
        logger_brain.info("🧠 NOVA MENSAGEM RECEBIDA PARA PROCESSAMENTO")
        logger_brain.info(f"💬 Mensagem: '{mensagem[:100]}{'...' if len(mensagem) > 100 else ''}'")
        
        # Garante inicialização
        if not self._garantir_inicializacao():
            return RespostaBrain(
                sucesso=False,
                acao_executada="erro_inicializacao",
                resposta_ia="❌ Desculpe, estou tendo problemas para me conectar aos meus sistemas. Tente novamente em instantes.",
                erro="Falha na inicialização do Brain Middleware"
            )
        
        try:
            # Passo 1: Detectar intenção
            intencao = self._detectar_intencao(mensagem)
            logger_brain.info(f"🎯 Intenção detectada: {intencao.tipo.value} (confiança: {intencao.confianca:.2f})")
            
            # Passo 2: Executar ação baseada na intenção
            resultado = self._executar_acao(intencao, mensagem, contexto)
            
            logger_brain.info(f"✅ Processamento concluído: {resultado.sucesso}")
            logger_brain.info("=" * 60)
            
            return resultado
            
        except Exception as e:
            logger_brain.error(f"❌ Erro inesperado no processamento: {e}", exc_info=True)
            
            return RespostaBrain(
                sucesso=False,
                acao_executada="erro",
                resposta_ia="❌ Ops! Algo deu errado ao processar sua mensagem. Pode tentar de outra forma?",
                erro=str(e)
            )
    
    # =========================================================================
    # DETECÇÃO DE INTENÇÃO
    # =========================================================================
    
    def _detectar_intencao(self, mensagem: str) -> IntencaoDetectada:
        """
        Detecta a intenção da mensagem usando análise híbrida.
        
        Usa combinação de:
        1. Matching de palavras-chave (rápido, determinístico)
        2. Análise via LLM (mais preciso, para casos complexos)
        
        Args:
            mensagem: Texto da mensagem do usuário
        
        Returns:
            IntencaoDetectada com tipo e confiança
        """
        mensagem_lower = mensagem.lower().strip()
        
        # Passo 1: Tentar detecção por palavras-chave (rápido)
        intencao_keyword = self._detectar_por_keywords(mensagem_lower)
        
        if intencao_keyword and intencao_keyword.confianca >= 0.8:
            # Alta confiança no keyword matching, extrair entidades
            entidades = self._extrair_entidades(mensagem)
            return IntencaoDetectada(
                tipo=intencao_keyword.tipo,
                confianca=intencao_keyword.confianca,
                entidades=entidades,
                texto_original=mensagem
            )
        
        # Passo 2: Usar LLM para detecção mais precisa
        try:
            intencao_llm = self._detectar_por_llm(mensagem)
            if intencao_llm:
                return intencao_llm
        except Exception as e:
            logger_brain.warning(f"⚠️ Falha na detecção via LLM: {e}")
        
        # Fallback: retornar keyword match ou desconhecida
        if intencao_keyword:
            entidades = self._extrair_entidades(mensagem)
            return IntencaoDetectada(
                tipo=intencao_keyword.tipo,
                confianca=intencao_keyword.confianca,
                entidades=entidades,
                texto_original=mensagem
            )
        
        return IntencaoDetectada(
            tipo=TipoIntencao.DESCONHECIDA,
            confianca=0.0,
            entidades={},
            texto_original=mensagem
        )
    
    def _detectar_por_keywords(self, mensagem_lower: str) -> Optional[IntencaoDetectada]:
        """
        Detecta intenção baseada em palavras-chave.
        
        Args:
            mensagem_lower: Mensagem em minúsculas
        
        Returns:
            IntencaoDetectada ou None se não encontrou match
        """
        melhor_match: Optional[TipoIntencao] = None
        melhor_score = 0.0
        total_matches = 0
        
        for tipo_intencao, keywords in self.CAPACIDADES.items():
            score = 0
            for keyword in keywords:
                if keyword in mensagem_lower:
                    score += len(keyword) / len(mensagem_lower) * 2
                    score += 0.5  # Bônus por match
            
            if score > melhor_score:
                melhor_score = score
                melhor_match = tipo_intencao
            if score > 0:
                total_matches += 1
        
        if melhor_match and melhor_score > 0:
            # Normalizar confiança entre 0.3 e 0.95
            confianca = min(0.95, max(0.3, melhor_score))
            
            return IntencaoDetectada(
                tipo=melhor_match,
                confianca=confianca
            )
        
        return None
    
    def _detectar_por_llm(self, mensagem: str) -> Optional[IntencaoDetectada]:
        """
        Detecta intenção usando LLM para análise semântica.
        
        Args:
            mensagem: Mensagem original do usuário
        
        Returns:
            IntencaoDetectada ou None se falhou
        """
        if not self._llm:
            return None
        
        prompt_intencao = f"""Analise a seguinte mensagem e identifique a intenção do usuário.

MENSAGEM: "{mensagem}"

INTENÇÕES POSSÍVEIS:
- criar_nota: Usuário quer salvar/anotar algo
- criar_tarefa: Usuário tem algo a fazer com prazo
- buscar_info: Usuário quer encontrar informações existentes
- gerar_ideias: Usuário quer sugestões/ideias
- consultar_metricas: Usuário quer saber seu progresso/status
- criar_plano: Usuário quer um plano ou estratégia
- conversar: É apenas uma conversa casual ou pergunta geral

RESPONDA APENAS EM FORMATO JSON:
{{"intencao": "tipo_de_intencao", "confianca": 0.0-1.0, "entidades": {{}}}}

Exemplo: {{"intencao": "criar_nota", "confianca": 0.9, "entidades": {{"texto": "comprar microfone"}}}}"""

        try:
            resposta = self._llm.gerar(prompt_intencao)
            
            # Extrair JSON da resposta
            json_match = re.search(r'\{[^{}]+\}', resposta)
            if json_match:
                import json
                dados = json.loads(json_match.group())
                
                tipo_str = dados.get("intencao", "desconhecida")
                try:
                    tipo = TipoIntencao(tipo_str)
                except ValueError:
                    tipo = TipoIntencao.DESCONHECIDA
                
                return IntencaoDetectada(
                    tipo=tipo,
                    confianca=float(dados.get("confianca", 0.5)),
                    entidades=dados.get("entidades", {}),
                    texto_original=mensagem
                )
                
        except Exception as e:
            logger_brain.warning(f"⚠️ Erro ao parsear resposta do LLM: {e}")
        
        return None
    
    def _extrair_entidades(self, mensagem: str) -> dict[str, Any]:
        """
        Extrai entidades relevantes da mensagem usando regex.
        
        Extrai: prazos, prioridades, projetos, quantidades
        
        Args:
            mensagem: Mensagem original do usuário
        
        Returns:
            Dicionário com entidades encontradas
        """
        entidades: dict[str, Any] = {}
        mensagem_lower = mensagem.lower()
        
        # Extrair prazo
        prazo_match = re.search(self.PADROES_ENTIDADES["prazo"], mensagem_lower)
        if prazo_match:
            entidades["prazo"] = self._converter_prazo(prazo_match.group(1))
        
        # Extrair prioridade
        prio_match = re.search(self.PADROES_ENTIDADES["prioridade"], mensagem_lower)
        if prio_match:
            prio_str = prio_match.group(1).lower()
            if prio_str in ["urgente"]:
                entidades["prioridade"] = PrioridadeTarefa.URGENTE.value
            elif prio_str in ["alta", "importante"]:
                entidades["prioridade"] = PrioridadeTarefa.ALTA.value
            elif prio_str in ["media", "média"]:
                entidades["prioridade"] = PrioridadeTarefa.MEDIA.value
            else:
                entidades["prioridade"] = PrioridadeTarefa.BAIXA.value
        
        # Extrair quantidade
        qtd_match = re.search(self.PADROES_ENTIDADES["quantidade"], mensagem_lower)
        if qtd_match:
            entidades["quantidade"] = int(qtd_match.group(1))
        
        # Limpar mensagem para extrair conteúdo principal
        conteudo = self._limpar_mensagem_para_conteudo(mensagem)
        if conteudo:
            entidades["conteudo"] = conteudo
        
        # Tentar identificar projeto mencionado
        projeto_match = re.search(self.PADROES_ENTIDADES["projeto"], mensagem_lower, re.IGNORECASE)
        if projeto_match:
            entidades["projeto_sugerido"] = projeto_match.group(1).strip()
        
        # Detectar menção a canais/projetos conhecidos
        if any(p in mensagem_lower for p in ["canal dark", "dark", "youtube", "yt"]):
            entidades["projeto_sugerido"] = "Canais Dark"
        elif any(p in mensagem_lower for p in ["instagram", "ig", "influencer"]):
            entidades["projeto_sugerido"] = "Influencer AI"
        
        logger_brain.debug(f"🔍 Entidades extraídas: {entidades}")
        
        return entidades
    
    def _limpar_mensagem_para_conteudo(self, mensagem: str) -> str:
        """
        Remove prefixos e ruído da mensagem para extrair o conteúdo real.
        
        Args:
            mensagem: Mensagem original
        
        Returns:
            Conteúdo limpo
        """
        # Remover prefixos comuns
        prefixos = [
            r"^lex[,:\s]*",
            r"^ei[,:\s]*",
            r"^olá[,:\s]*",
            r"^oi[,:\s]*",
            r"^anota\s+(?:aí\s+)?(?:que\s+)?",
            r"^lembra?\s+(?:de\s+|que\s+)?(?:que\s+)?",
            r"^anote\s+(?:aí\s+)?(?:que\s+)?",
            r"^registra?\s+(?:aí\s+)?(?:que\s+)?",
            r"^preciso\s+(?:comprar|fazer|terminar|criar|escrever)\s+",
            r"^tenho\s+que\s+",
            r"^vou\s+",
        ]
        
        conteudo = mensagem.strip()
        for prefixo in prefixos:
            conteudo = re.sub(prefixo, "", conteudo, flags=re.IGNORECASE).strip()
        
        # Remover pontuação final excessiva
        conteudo = conteudo.rstrip("!?. ")
        
        return conteudo if len(conteudo) > 2 else ""
    
    def _converter_prazo(self, prazo_str: str) -> str:
        """
        Converte string de prazo para formato padronizado.
        
        Args:
            prazo_str: String do prazo extraída (ex: "sexta", "amanhã")
        
        Returns:
            Data formatada ou string legível
        """
        hoje = datetime.now()
        prazo_str = prazo_str.lower().strip()
        
        mapeamento_dias = {
            "hoje": hoje,
            "amanhã": hoje + timedelta(days=1),
            "segunda": self._proximo_dia_semana(hoje, 0),
            "terça": self._proximo_dia_semana(hoje, 1),
            "quarta": self._proximo_dia_semana(hoje, 2),
            "quinta": self._proximo_dia_semana(hoje, 3),
            "sexta": self._proximo_dia_semana(hoje, 4),
            "sabado": self._proximo_dia_semana(hoje, 5),
            "domingo": self._proximo_dia_semana(hoje, 6),
        }
        
        if prazo_str in mapeamento_dias:
            data = mapeamento_dias[prazo_str]
            return data.strftime("%Y-%m-%d")
        
        if prazo_str == "semana":
            return (hoje + timedelta(days=7)).strftime("%Y-%m-%d")
        
        if prazo_str == "mes":
            return (hoje + timedelta(days=30)).strftime("%Y-%m-%d")
        
        return prazo_str  # Retorna original se não reconheceu
    
    @staticmethod
    def _proximo_dia_semana(data_base: datetime, dia_semana: int) -> datetime:
        """
        Calcula a próxima ocorrência de um dia da semana.
        
        Args:
            data_base: Data de referência
            dia_semana: 0=Segunda, 1=Terça, ..., 6=Domingo
        
        Returns:
            Data do próximo dia especificado
        """
        dias_ate = (dia_semana - data_base.weekday()) % 7
        if dias_ate == 0:
            dias_ate = 7  # Próxima semana, não hoje
        return data_base + timedelta(days=dias_ate)
    
    # =========================================================================
    # EXECUÇÃO DE AÇÕES
    # =========================================================================
    
    def _executar_acao(
        self, 
        intencao: IntencaoDetectada, 
        mensagem: str, 
        contexto: Optional[dict]
    ) -> RespostaBrain:
        """
        Executa a ação apropriada baseada na intenção detectada.
        
        Args:
            intencao: Intenção detectada
            mensagem: Mensagem original
            contexto: Contexto adicional
        
        Returns:
            RespostaBrain com resultado da execução
        """
        # Dispatcher de ações
        acoes: dict[TipoIntencao, callable] = {
            TipoIntencao.CRIAR_NOTA: self._acao_criar_nota,
            TipoIntencao.CRIAR_TAREFA: self._acao_criar_tarefa,
            TipoIntencao.BUSCAR_INFO: self._acao_buscar_info,
            TipoIntencao.GERAR_IDEIAS: self._acao_gerar_ideias,
            TipoIntencao.CONSULTAR_METRICAS: self._acao_consultar_metricas,
            TipoIntencao.CRIAR_PLANO: self._acao_criar_plano,
            TipoIntencao.CONVERSAR: self._acao_conversar,
            TipoIntencao.DESCONHECIDA: self._acao_desconhecida,
        }
        
        executor = acoes.get(intencao.tipo, self._acao_desconhecida)
        
        try:
            return executor(intencao, mensagem, contexto)
        except Exception as e:
            logger_brain.error(f"❌ Erro na ação {intencao.tipo.value}: {e}", exc_info=True)
            return RespostaBrain(
                sucesso=False,
                acao_executada=intencao.tipo.value,
                resposta_ia=f"❌ Desculpe, tive um problema ao executar essa ação. Erro: {str(e)[:50]}",
                erro=str(e)
            )
    
    # -----------------------------------------------------------------
    # AÇÃO: CRIAR NOTA
    # -----------------------------------------------------------------
    
    def _acao_criar_nota(
        self, 
        intencao: IntencaoDetectada, 
        mensagem: str, 
        contexto: Optional[dict]
    ) -> RespostaBrain:
        """
        Cria uma nota no Lex Flow baseada na mensagem.
        
        Args:
            intencao: Intenção com entidades extraídas
            mensagem: Mensagem original
            contexto: Contexto adicional
        
        Returns:
            RespostaBrain confirmando a criação da nota
        """
        logger_brain.info("📝 Executando: CRIAR NOTA")
        
        # Extrair título e conteúdo
        conteudo = intencao.entidades.get("conteudo", mensagem)
        
        # Gerar título curto (primeiros 50 chars)
        titulo = conteudo[:50] + ("..." if len(conteudo) > 50 else "")
        
        # Adicionar contexto automático
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%H")
        conteudo_completo = f"[Captura via Brain Middleware - {timestamp}]\n\n{conteudo}"
        
        # Adicionar projeto se identificado
        if "projeto_sugerido" in intencao.entidades:
            conteudo_completo += f"\n\n📁 Projeto relacionado: {intencao.entidades['projeto_sugerido']}"
        
        try:
            # Chamar Lex Flow API
            resultado = self._lexflow.add_note(titulo, content=conteudo_completo)
            
            if resultado.get("success"):
                nota_id = resultado.get("note", {}).get("id", "N/A")
                
                logger_brain.info(f"✅ Nota criada com ID: {nota_id}")
                
                resposta = f"""✅ **Nota criada com sucesso!**

📝 *{titulo}*

💾 Salvo no Lex Flow às {timestamp}
"""
                
                if "projeto_sugerido" in intencao.entidades:
                    resposta += f"📁 Vinculado ao projeto: {intencao.entidades['projeto_sugerido']}\n"
                
                return RespostaBrain(
                    sucesso=True,
                    acao_executada="criar_nota",
                    resposta_ia=resposta,
                    detalhes={"nota_id": nota_id, "titulo": titulo},
                    sugestoes=[
                        "Quer que eu crie uma tarefa para isso?",
                        "Quer adicionar mais detalhes à nota?"
                    ]
                )
            else:
                raise Exception(resultado.get("error", "Erro desconhecido do Lex Flow"))
                
        except Exception as e:
            logger_brain.error(f"❌ Erro ao criar nota: {e}")
            return RespostaBrain(
                sucesso=False,
                acao_executada="criar_nota",
                resposta_ia=f"❌ Não consegui criar a nota. Erro: {str(e)[:50]}",
                erro=str(e)
            )
    
    # -----------------------------------------------------------------
    # AÇÃO: CRIAR TAREFA (v2.0 - Inbox vs Projeto)
    # -----------------------------------------------------------------
    
    def _acao_criar_tarefa(
        self, 
        intencao: IntencaoDetectada, 
        mensagem: str, 
        contexto: Optional[dict]
    ) -> RespostaBrain:
        """
        Cria uma tarefa no Lex Flow baseada na mensagem.
        
        LÓGICA INTELIGENTE:
        - Tem projeto específico? → add_task() no projeto
        - Sem projeto?           → add_note() na CAIXA DE ENTRADA (Inbox)
        
        Args:
            intencao: Intenção com entidades extraídas
            mensagem: Mensagem original
            contexto: Contexto adicional
        
        Returns:
            RespostaBrain confirmando a criação da tarefa
        """
        logger_brain.info("✅ Executando: CRIAR TAREFA")
        
        # Extrair dados da tarefa
        conteudo = intencao.entidades.get("conteudo", mensagem)
        titulo = conteudo[:80] + ("..." if len(conteudo) > 80 else "")
        
        # Prioridade (padrão: média)
        prioridade = intencao.entidades.get("prioridade", PrioridadeTarefa.MEDIA.value)
        
        # Normalizar prioridade para inglês (API espera "medium", não "media")
        prioridade_en = prioridade
        if prioridade_en == "media":
            prioridade_en = "medium"
        elif prioridade_en == "alta":
            prioridade_en = "high"
        elif prioridade_en == "baixa":
            prioridade_en = "low"
        elif prioridade_en == "urgente":
            prioridade_en = "urgent"
        
        # Tentar encontrar projeto
        projeto_id = None
        projeto_nome = None
        
        if "projeto_sugerido" in intencao.entidades:
            projeto_id = self._buscar_projeto_id(intencao.entidades["projeto_sugerido"])
            if projeto_id:
                projeto_nome = intencao.entidades["projeto_sugerido"]
        
        # Verificar se temos um projeto válido (ID > 0)
        tem_projeto_valido = projeto_id and int(projeto_id) > 0
        
        try:
            resultado = None
            task_id = "N/A"
            modo_criacao = ""
            
            # ============================================================
            # 🔥 DECISÃO: PROJETO vs CAIXA DE ENTRADA (INBOX)
            # ============================================================
            
            if tem_projeto_valido:
                # ========================================
                # CASO 1: Tem projeto → Criar tarefa no projeto
                # ========================================
                modo_criacao = "projeto"
                
                logger_brain.info(f"📁 Criando tarefa no PROJETO {projeto_id} ('{projeto_nome}')...")
                
                # Preparar descrição
                descricao = f"[Criado via Brain Middleware - {datetime.now().strftime('%d/%m/%Y %H:%M')}]\n\n{mensagem}"
                
                # Adicionar prazo se detectado
                due_date = None
                if "prazo" in intencao.entidades:
                    due_date = intencao.entidades["prazo"]
                
                try:
                    resultado = self._lexflow.add_task(
                        int(projeto_id),       # project_id (int)
                        titulo,               # title (str)
                        description=descricao,
                        priority=prioridade_en,
                        due_date=due_date
                    )
                    
                    logger_brain.info(f"📦 Resultado add_task: {type(resultado).__name__}")
                    
                    # Extrair ID do resultado
                    if isinstance(resultado, dict):
                        task_data = resultado.get("task", resultado.get("note", {}))
                        if isinstance(task_data, dict):
                            task_id = task_data.get("id", "N/A")
                        elif isinstance(task_data, (int, str)):
                            task_id = str(task_data)
                        # Se não tem success explícito mas tem dados, OK
                        if task_id != "N/A" and not resultado.get("success"):
                            resultado["success"] = True
                            
                    elif isinstance(resultado, list) and len(resultado) > 0:
                        primeiro = resultado[0]
                        if isinstance(primeiro, dict):
                            task_id = primeiro.get("id", primeiro.get("task", {}).get("id", "N/A"))
                        else:
                            task_id = str(primeiro)
                        resultado = {"success": True}
                        
                    elif resultado is not None:
                        task_id = str(resultado)
                        resultado = {"success": True}
                        
                except Exception as e_task:
                    logger_brain.error(f"❌ Erro add_task: {e_task}")
                    resultado = None
                    
            else:
                # ========================================
                # CASO 2: Sem projeto → CAIXA DE ENTRADA (INBOX)
                # ========================================
                modo_criacao = "inbox"
                
                logger_brain.info("📥 Sem projeto → Enviando para CAIXA DE ENTRADA (Inbox)")
                
                # Montar título formatado como tarefa
                titulo_inbox = f"📋 {titulo}"
                
                # Adicionar prazo ao título se existir
                if "prazo" in intencao.entidades:
                    titulo_inbox += f" ⏰ {intencao.entidades['prazo']}"
                
                # Ícone de prioridade
                icones_prioridade = {
                    "high": "🔴",
                    "low": "🟢",
                    "urgent": "🚨",
                    "medium": "🟡"
                }
                if prioridade_en in icones_prioridade:
                    titulo_inbox += f" {icones_prioridade[prioridade_en]}"
                
                # Montar descrição rica
                descricao_inbox = f"""[Criado via Brain Middleware - {datetime.now().strftime('%d/%m/%Y %H:%M')}]

{mensagem}

{'='*40}
🤖 *Status:* Aguardando triagem
⚡ *Prioridade:* {prioridade_en.capitalize()}"""
                
                if "prazo" in intencao.entidades:
                    descricao_inbox += f"\n📅 *Prazo:* {intencao.entidades['prazo']}"
                
                descricao_inbox += "\n\n💡 *Ação necessária:* Mover para projeto quando possível"
                
                # Tags especiais para identificar como tarefa pendente
                tags_tarefa = ["tarefa", "inbox", "brain-mw", f"prioridade:{prioridade_en}"]
                
                if "prazo" in intencao.entidades:
                    tags_tarefa.append(f"prazo:{intencao.entidades['prazo']}")
                
                # Criar NOTA na Caixa de Entrada via /quicknotes/
                logger_brain.info(f"📝 Criando nota inbox: '{titulo_inbox}'")
                
                try:
                    resultado = self._lexflow.add_note(
                        title=titulo_inbox,
                        content=descricao_inbox,
                        tags=tags_tarefa
                    )
                    
                    logger_brain.info(f"📦 Resultado add_note: {type(resultado).__name__}")
                    
                    # Extrair ID da nota criada
                    if isinstance(resultado, dict):
                        note_data = resultado.get("note", resultado)
                        if isinstance(note_data, dict):
                            task_id = note_data.get("id", "N/A")
                        elif isinstance(note_data, (int, str)):
                            task_id = str(note_data)
                        else:
                            task_id = "N/A"
                            
                    elif resultado is not None:
                        task_id = str(resultado)
                    else:
                        task_id = "N/A"
                        
                    if resultado:
                        resultado = {"success": True}
                        
                except Exception as e_inbox:
                    logger_brain.error(f"❌ Erro add_note (inbox): {e_inbox}", exc_info=True)
                    resultado = None
            
            # ============================================================
            # VERIFICAR SUCESSO E MONTAR RESPOSTA
            # ============================================================
            
            sucesso = (resultado is not None) and resultado.get("success", False) and (task_id != "N/A")
            
            if sucesso:
                logger_brain.info(f"✅ Tarefa criada! ID: {task_id} (modo: {modo_criacao})")
                
                # Montar resposta conforme o modo de criação
                if modo_criacao == "inbox":
                    resposta = f"""✅ *Tarefa enviada para a Caixa de Entrada!*

📋 *{titulo}*
📥 *Localização:* Caixa de Entrada (Inbox)"""

                    if "prazo" in intencao.entidades:
                        resposta += f"\n📅 Prazo: {intencao.entidades['prazo']}"
                    
                    if prioridade_en != "medium":
                        icon_prio = {"high": "🔴", "low": "🟢", "urgent": "🚨", "medium": "🟡"}
                        resposta += f"\n⚡ Prioridade: {icon_prio.get(prioridade_en, '⚪')} {prioridade_en.capitalize()}"
                    
                    resposta += """

💡 *Aguardando sua triagem:*
   • Mover para um projeto específico
   • Definir sub-tarefas se necessário
   • Ajustar prazo se preciso"""
                    
                    sugestoes = [
                        "Quer mover para algum projeto?",
                        "Quer definir lembretes?",
                        "Quer ver outras tarefas na caixa de entrada?"
                    ]
                    
                else:  # modo_criacao == "projeto"
                    resposta = f"""✅ *Tarefa criada com sucesso!*

📋 *{titulo}*"""

                    if "prazo" in intencao.entidades:
                        resposta += f"\n📅 Prazo: {intencao.entidades['prazo']}"
                    
                    icon_prio = {"urgente": "🔴", "alta": "🟠", "media": "🟡", "baixa": "🟢"}
                    resposta += f"\n⚡ Prioridade: {icon_prio.get(prioridade, '⚪')} {prioridade.capitalize()}"
                    
                    if projeto_nome:
                        resposta += f"\n📁 Projeto: {projeto_nome}"
                    
                    sugestoes = [
                        "Quer que eu crie uma nota com mais detalhes?",
                        "Quer definir lembretes para esta tarefa?",
                        "Quer adicionar sub-tarefas?"
                    ]
                
                return RespostaBrain(
                    sucesso=True,
                    acao_executada="criar_tarefa",
                    resposta_ia=resposta,
                    detalhes={
                        "task_id": task_id, 
                        "titulo": titulo,
                        "modo_criacao": modo_criacao,
                        "project_id": projeto_id if tem_projeto_valido else None,
                        "prioridade": prioridade_en
                    },
                    sugestoes=sugestoes
                )
            else:
                # Falha na criação
                erro_msg = "Erro desconhecido"
                if resultado is None:
                    erro_msg = "Sem resposta da API"
                elif isinstance(resultado, dict) and resultado.get("error"):
                    erro_msg = str(resultado.get("error"))[:100]
                    
                raise Exception(erro_msg)
                
        except Exception as e:
            logger_brain.error(f"❌ Erro ao criar tarefa: {e}", exc_info=True)
            return RespostaBrain(
                sucesso=False,
                acao_executada="criar_tarefa",
                resposta_ia=f"❌ Não consegui criar a tarefa.\n\nErro: `{str(e)[:80]}`\n\n_Tente novamente ou use /tarefa manualmente_",
                erro=str(e)
            ) 

            
    def _buscar_projeto_id(self, nome_projeto: str) -> Optional[int]:
        """
        Busca o ID de um projeto pelo nome.
        
        Args:
            nome_projeto: Nome do projeto (parcial ou completo)
        
        Returns:
            ID do projeto ou None se não encontrado
        """
        try:
            resultado = self._lexflow.get_projects()
            
            if resultado.get("success") and resultado.get("projects"):
                projetos = resultado["projects"]
                
                # Buscar exato ou parcial
                nome_lower = nome_projeto.lower()
                for proj in projetos:
                    if isinstance(proj, dict):
                        proj_nome = proj.get("name", "").lower()
                        proj_id = proj.get("id")
                        if nome_lower in proj_nome or proj_nome in nome_lower:
                            logger_brain.debug(f"📁 Projeto encontrado: {proj_nome} (ID: {proj_id})")
                            return proj_id
            
            return None
            
        except Exception as e:
            logger_brain.warning(f"⚠️ Erro ao buscar projeto: {e}")
            return None
    
    # -----------------------------------------------------------------
    # AÇÃO: BUSCAR INFORMAÇÕES (RAG)
    # -----------------------------------------------------------------
    
    def _acao_buscar_info(
        self, 
        intencao: IntencaoDetectada, 
        mensagem: str, 
        contexto: Optional[dict]
    ) -> RespostaBrain:
        """
        Busca informações usando RAG System e gera resposta contextual.
        
        Args:
            intencao: Intenção com entidades extraídas
            mensagem: Mensagem original
            contexto: Contexto adicional
        
        Returns:
            RespostaBrain com informações encontradas
        """
        logger_brain.info("🔍 Executando: BUSCAR INFORMAÇÕES (RAG)")
        
        # Extrair query de busca
        query = intencao.entidades.get("conteudo", mensagem)
        
        # Limpar query removendo palavras de busca
        query_limpa = re.sub(
            r"(o que eu|já|escrevi|falei|anotei|sobre|resuma|me dê|me mostre|quais são|como estão)",
            "",
            query,
            flags=re.IGNORECASE
        ).strip()
        
        if len(query_limpa) < 3:
            query_limpa = query
        
        try:
            # Buscar no RAG System
            logger_brain.info(f"🔍 Buscando no RAG: '{query_limpa}'")
            
            resultados_rag = self._rag.buscar(
                query=query_limpa,
                n_results=5,
                estrategia="hibrida"  # type: ignore
            )
            
            if not resultados_rag or not resultados_rag.get("resultados"):
                return RespostaBrain(
                    sucesso=True,
                    acao_executada="buscar_info",
                    resposta_ia=f"🔍 **Não encontrei nada sobre** *'{query_limpa}'*\n\nParece que você ainda não tem notas sobre esse assunto. Quer que eu anote sua pergunta para pesquisar depois?",
                    detalhes={"query": query_limpa, "resultados_encontrados": 0},
                    sugestoes=["Quer que eu anote esse tema para pesquisar?"]
                )
            
            # Preparar contextos para o LLM
            contextos = []
            for i, res in enumerate(resultados_rag.get("resultados", [])[:5], 1):
                contextos.append(f"[{i}] {res.get('conteudo', '')[:200]}...")
            
            contexto_texto = "\n".join(contextos)
            
            # Gerar resposta com LLM
            prompt_resposta = f"""Baseado nas informações abaixo, responda à pergunta do usuário de forma clara e útil.

PERGUNTA DO USUÁRIO: {mensagem}

INFORMAÇÕES ENCONTRADAS NO SISTEMA:
{contexto_texto}

Responda de forma:
- Clara e direta
- Destacando os pontos principais
- Com emojis quando apropriado
- Em português brasileiro"""

            resposta_llm = self._llm.gerar(prompt_resposta)
            
            num_resultados = len(resultados_rag.get("resultados", []))
            
            resposta_final = f"""🔍 **Encontrei {num_resultados} referências sobre** *'{query_limpa}'*

---
{resposta_llm}
---

💡 Quer que eu busque mais detalhes sobre algum ponto específico?"""
            
            return RespostaBrain(
                sucesso=True,
                acao_executada="buscar_info",
                resposta_ia=resposta_final,
                detalhes={
                    "query": query_limpa,
                    "resultados_encontrados": num_resultados,
                    "estrategia": "hibrida"
                },
                sugestoes=[
                    "Quer que eu crie um plano baseado nessas informações?",
                    "Quer que eu gere ideias relacionadas?"
                ]
            )
            
        except Exception as e:
            logger_brain.error(f"❌ Erro na busca RAG: {e}")
            return RespostaBrain(
                sucesso=False,
                acao_executada="buscar_info",
                resposta_ia=f"❌ Erro ao buscar informações: {str(e)[:50]}",
                erro=str(e)
            )
    
    # -----------------------------------------------------------------
    # AÇÃO: GERAR IDEIAS
    # -----------------------------------------------------------------
    
    def _acao_gerar_ideias(
        self, 
        intencao: IntencaoDetectada, 
        mensagem: str, 
        contexto: Optional[dict]
    ) -> RespostaBrain:
        """
        Gera ideias usando RAG + LLM baseadas nos dados do usuário.
        
        Args:
            intencao: Intenção com entidades extraídas
            mensagem: Mensagem original
            contexto: Contexto adicional
        
        Returns:
            RespostaBrain com ideias geradas
        """
        logger_brain.info("💡 Executando: GERAR IDEIAS")
        
        # Extrair tema
        tema = intencao.entidades.get("conteudo", mensagem)
        quantidade = intencao.entidades.get("quantidade", 5)
        
        # Limpar tema
        tema_limpo = re.sub(
            r"(ideias?|sugira|sugestões|brainstorm|dê|me dá|crie|para|sobre)",
            "",
            tema,
            flags=re.IGNORECASE
        ).strip()
        
        if len(tema_limpo) < 2:
            tema_limpo = "conteúdo em geral"
        
        try:
            # Buscar contextos relacionados no RAG
            logger_brain.info(f"🔍 Buscando contextos para brainstorm: '{tema_limpo}'")
            
            contextos_rag = []
            try:
                rag_result = self._rag.buscar(
                    query=tema_limpo,
                    n_results=3,
                    estrategia="vetorial"  # type: ignore
                )
                if rag_result and rag_result.get("resultados"):
                    for res in rag_result["resultados"][:3]:
                        contextos_rag.append(res.get("conteudo", "")[:150])
            except Exception as e:
                logger_brain.warning(f"⚠️ Erro ao buscar contextos RAG: {e}")
            
            contexto_base = "\n".join(contextos_rag) if contextos_rag else "Sem contextos anteriores encontrados."
            
            # Prompt para geração de ideias
            prompt_ideias = f"""Você é um assistente criativo especialista em gerar ideias de conteúdo para criadores digitais.

TEMA SOLICITADO: {tema_limpo}
QUANTIDADE DE IDEIAS: {quantidade}

CONTEXTOS ANTERIORES DO USUÁRIO:
{contexto_base}

Gere {quantidade} ideias CRIATIVAS e ORIGINAIS sobre o tema.

Para cada ideia, inclua:
1. Título chamativo (clickbait ético)
2. Descrição breve (2-3 linhas)
3. Por que vai funcionar (motivo)
4. Score de viralidade (🔥1-10)
5. Score de facilidade (✏️1-10)

Formato de resposta:
💡 **IDEIA N**: [Título]
📝 Descrição...
🎯 Por que funciona: ...
🔥 Viralidade: X/10 | ✏️ Facilidade: X/10

Seja criativo e pense como um YouTuber/TikToker de sucesso!"""

            resposta_llm = self._llm.gerar(prompt_ideias)
            
            resposta_final = f"""💡 **{quantidade} IDEIAS SOBRE** *'{tema_limpo.upper()}'*

*(Geradas com base nos seus dados)*

---
{resposta_llm}
---

🎯 Quer que eu transforme alguma ideia em tarefa?
📁 Quer salvar essas ideias como nota?"""
            
            return RespostaBrain(
                sucesso=True,
                acao_executada="gerar_ideias",
                resposta_ia=resposta_final,
                detalhes={
                    "tema": tema_limpo,
                    "quantidade": quantidade,
                    "contextos_usados": len(contextos_rag)
                },
                sugestoes=[
                    "Quer criar tarefas para essas ideias?",
                    "Quer salvar como nota para referência futura?",
                    "Quer mais ideias sobre outro tema?"
                ]
            )
            
        except Exception as e:
            logger_brain.error(f"❌ Erro ao gerar ideias: {e}")
            return RespostaBrain(
                sucesso=False,
                acao_executada="gerar_ideias",
                resposta_ia=f"❌ Erro ao gerar ideias: {str(e)[:50]}",
                erro=str(e)
            )
    
    # -----------------------------------------------------------------
    # AÇÃO: CONSULTAR MÉTRICAS
    # -----------------------------------------------------------------
    
    def _acao_consultar_metricas(
        self, 
        intencao: IntencaoDetectada, 
        mensagem: str, 
        contexto: Optional[dict]
    ) -> RespostaBrain:
        """
        Consulta e apresenta métricas de produtividade do usuário.
        
        Args:
            intencao: Intenção detectada
            mensagem: Mensagem original
            contexto: Contexto adicional
        
        Returns:
            RespostaBrain com métricas atuais
        """
        logger_brain.info("📊 Executando: CONSULTAR MÉTRICAS")
        
        try:
            # Coletar métricas de vários fontes
            metricas: dict[str, Any] = {}
            
            # Métricas do RAG
            try:
                stats_rag = self._rag.obter_estatisticas()  # type: ignore
                metricas["documentos_indexados"] = stats_rag.get("total_documentos", 0)
                metricas["notas_lexflow"] = stats_rag.get("notas_lexflow", 0)
            except Exception as e:
                logger_brain.warning(f"⚠️ Erro ao obter stats RAG: {e}")
            
            # Métricas do Lex Flow (tarefas)
            try:
                inbox = self._lexflow.get_inbox()
                if inbox.get("success"):
                    metricas["tarefas_inbox"] = len(inbox.get("inbox", []))
            except Exception as e:
                logger_brain.warning(f"⚠️ Erro ao obter inbox: {e}")
            
            # Projetos
            try:
                projetos = self._lexflow.get_projects()
                if projetos.get("success"):
                    metricas["projetos_ativos"] = len(projetotos.get("projects", []))  # type: ignore
            except Exception as e:
                logger_brain.warning(f"⚠️ Erro ao obter projetos: {e}")
            
            # Data/hora atual
            agora = datetime.now()
            metricas["data_hora"] = agora.strftime("%d/%m/%Y %H:%M")
            metricas["dia_semana"] = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][agora.weekday()]
            
            # Gerar resposta com LLM para análise personalizada
            prompt_metricas = f"""Analise as métricas atuais do usuário e dê um feedback motivador e útil.

MÉTRICAS ATUAIS:
- Documentos indexados no sistema: {metricas.get('documentos_indexados', 0)}
- Notas no Lex Flow: {metricas.get('notas_lexflow', 0)}
- Tarefas no Inbox: {metricas.get('tarefas_inbox', 0)}
- Projetos ativos: {metricas.get('projetos_ativos', 0)}
- Data/Hora: {metricas.get('data_hora', '')} ({metricas.get('dia_semana', '')})

Responda de forma:
- Motivadora e positiva
- Destacando conquistas
- Sugerindo próximos passos se relevante
- Com emojis
- Concisa (máx 5 linhas)"""

            try:
                feedback_llm = self._llm.gerar(prompt_metricas)
            except Exception:
                feedback_llm = "Continue assim! Você está evoluindo bem! 💪"
            
            resposta_final = f"""📊 **SEU PAINEL DE MÉTRICAS**
📅 *{metricas.get('dia_semana', '')}, {metricas.get('data_hora', '')}*

━━━━━━━━━━━━━━━━━━━━
📚 **Conhecimento**
   📄 Documentos indexados: `{metricas.get('documentos_indexados', 0)}`
   📝 Notas salvas: `{metricas.get('notas_lexflow', 0)}`

✅ **Tarefas & Projetos**
   📥 Tarefas no Inbox: `{metricas.get('tarefas_inbox', 0)}`
   📁 Projetos ativos: `{metricas.get('projetos_ativos', 0)}`
━━━━━━━━━━━━━━━━━━━━

💭 *{feedback_llm}*"""
            
            return RespostaBrain(
                sucesso=True,
                acao_executada="consultar_metricas",
                resposta_ia=resposta_final,
                detalhes=metricas,
                sugestoes=[
                    "Quer ver suas tarefas pendentes?",
                    "Quer criar uma nova tarefa?"
                ]
            )
            
        except Exception as e:
            logger_brain.error(f"❌ Erro ao consultar métricas: {e}")
            return RespostaBrain(
                sucesso=False,
                acao_executada="consultar_metricas",
                resposta_ia=f"❌ Erro ao carregar métricas: {str(e)[:50]}",
                erro=str(e)
            )
    
    # -----------------------------------------------------------------
    # AÇÃO: CRIAR PLANO
    # -----------------------------------------------------------------
    
    def _acao_criar_plano(
        self, 
        intencao: IntencaoDetectada, 
        mensagem: str, 
        contexto: Optional[dict]
    ) -> RespostaBrain:
        """
        Cria um plano ou estratégia baseada nos dados do usuário.
        
        Args:
            intencao: Intenção com entidades extraídas
            mensagem: Mensagem original
            contexto: Contexto adicional
        
        Returns:
            RespostaBrain com plano gerado
        """
        logger_brain.info("🎯 Executando: CRIAR PLANO")
        
        # Extrair objetivo
        objetivo = intencao.entidades.get("conteudo", mensagem)
        objetivo_limpo = re.sub(
            r"(plano|estratégia|roadmap|plano de ação|roteiro|como|para|de)",
            "",
            objetivo,
            flags=re.IGNORECASE
        ).strip()
        
        if len(objetivo_limpo) < 2:
            objetivo_limpo = "escalar produção de conteúdo"
        
        try:
            # Buscar contextos relevantes
            logger_brain.info(f"🔍 Buscando contextos para plano: '{objetivo_limpo}'")
            
            contextos = []
            try:
                rag_result = self._rag.buscar(
                    query=objetivo_limpo,
                    n_results=5,
                    estrategia="hibrida"  # type: ignore
                )
                if rag_result and rag_result.get("resultados"):
                    for res in rag_result["resultados"][:5]:
                        contextos.append(res.get("conteudo", "")[:200])
            except Exception as e:
                logger_brain.warning(f"⚠️ Erro ao buscar contextos: {e}")
            
            contexto_texto = "\n".join(contextos) if contextos else "Sem informações prévias encontradas."
            
            # Gerar plano com LLM
            prompt_plano = f"""Você é um consultor estratégico especialista em produtividade e criação de conteúdo digital.

OBJETIVO DO USUÁRIO: {objetivo_limpo}

INFORMAÇÕES DISPONÍVEIS SOBRE O USUÁRIO:
{contexto_texto}

Crie um PLANO DE AÇÃO ESTRUTURADO e PRÁTICO.

Estrutura do plano:
🎯 **OBJETIVO CLARO** (1 linha)
📋 **VISÃO GERAL** (2-3 linhas)
📅 **FASES** (divida em 3-4 fases com prazos sugeridos):
   Fase 1: Fundação (Semana 1-2)
   Fase 2: Execução (Semana 3-6)
   Fase 3: Otimização (Semana 7-12)
   
Cada fase deve ter:
- 3-5 ações específicas
- KPIs/métricas de sucesso
- Ferramentas sugeridas

⚠️ **RISCOS E MITIGAÇÕES** (2-3 riscos principais)
💡 **DICAS EXTRA** (baseado nos dados do usuário)

Seja PRÁTICO e REALISTA. O usuário é criador de conteúdo com foco em YouTube/Instagram."""

            resposta_llm = self._llm.gerar(prompt_plano)
            
            resposta_final = f"""🎯 **PLANO DE AÇÃO:** *{objetivo_limpo.upper()}*

*(Gerado com base nos seus dados)*

═══════════════════════════════
{resposta_llm}
═══════════════════════════════

✅ Quer que eu crie tarefas para cada fase deste plano?
💾 Quer salvar este plano como nota?"""
            
            return RespostaBrain(
                sucesso=True,
                acao_executada="criar_plano",
                resposta_ia=resposta_final,
                detalhes={"objetivo": objetivo_limpo, "contextos_usados": len(contextos)},
                sugestoes=[
                    "Criar tarefas para as fases do plano?",
                    "Salvar plano como nota?",
                    "Buscar mais informações sobre algum ponto específico?"
                ]
            )
            
        except Exception as e:
            logger_brain.error(f"❌ Erro ao criar plano: {e}")
            return RespostaBrain(
                sucesso=False,
                acao_executada="criar_plano",
                resposta_ia=f"❌ Erro ao gerar plano: {str(e)[:50]}",
                erro=str(e)
            )
    
    # -----------------------------------------------------------------
    # AÇÃO: CONVERSAR (FALLBACK CASUAL)
    # -----------------------------------------------------------------
    
    def _acao_conversar(
        self, 
        intencao: IntencaoDetectada, 
        mensagem: str, 
        contexto: Optional[dict]
    ) -> RespostaBrain:
        """
        Responde conversas casuais ou perguntas gerais.
        
        Args:
            intencao: Intenção detectada
            mensagem: Mensagem original
            contexto: Contexto adicional
        
        Returns:
            RespostaBrain com resposta conversacional
        """
        logger_brain.info("💬 Executando: CONVERSAR")
        
        try:
            prompt_conversa = f"""Você é o Lex, um assistente pessoal de IA amigável e prestativo.

O usuário enviou: "{mensagem}"

Responda de forma:
- Natural e conversacional
- Amigável mas profissional
- Se for pergunta, responda diretamente
- Se for saudação, cumprimente de volta
- Se parecer tarefa/lembrete, ofereça-se para ajudar
- Máximo 3-4 linhas
- Use emojis moderadamente"""

            resposta_llm = self._llm.gerar(prompt_conversa)
            
            return RespostaBrain(
                sucesso=True,
                acao_executada="conversar",
                resposta_ia=resposta_llm,
                sugestoes=[
                    "Posso ajudar com mais algo?",
                    "Quer criar uma nota ou tarefa?"
                ]
            )
            
        except Exception as e:
            logger_brain.error(f"❌ Erro na conversa: {e}")
            return RespostaBrain(
                sucesso=False,
                acao_executada="conversar",
                resposta_ia="Hey! 👋 Como posso te ajudar hoje? Posso criar notas, tarefas, buscar informações ou gerar ideias!",
                erro=str(e)
            )
    
    # -----------------------------------------------------------------
    # AÇÃO: DESCONHECIDA (FALLBACK)
    # -----------------------------------------------------------------
    
    def _acao_desconhecida(
        self, 
        intencao: IntencaoDetectada, 
        mensagem: str, 
        contexto: Optional[dict]
    ) -> RespostaBrain:
        """
        Ação fallback quando não consegue detectar a intenção.
        
        Args:
            intencao: Intenção desconhecida
            mensagem: Mensagem original
            contexto: Contexto adicional
        
        Returns:
            RespostaBrain pedindo esclarecimento
        """
        logger_brain.info("❓ Executando: INTENÇÃO DESCONHECIDA")
        
        resposta = """🤔 **Não tenho certeza do que você precisa...**

Mas posso te ajudar com várias coisas:

📝 **"Lex, anota [algo]"** → Crio uma nota
✅ **"Lex, lembra que tenho que [fazer]"** → Crio uma tarefa
🔍 **"Lex, o que eu escrevi sobre [tema]?"** → Busco suas anotações
💡 **"Lex, me dá ideias sobre [tema]"** → Gero ideias criativas
📊 **"Lex, como estão minhas métricas?"** → Mostro seu progresso
🎯 **"Lex, faz um plano para [objetivo]"** → Crio estratégia

**Como posso te ajudar?** 😊"""
        
        return RespostaBrain(
            sucesso=True,
            acao_executada="desconhecida",
            resposta_ia=resposta,
            sugestoes=["Tente reformular sua mensagem"]
        )


# ============================================================================
# FUNÇÃO AUXILIAR PARA USO SIMPLIFICADO
# ============================================================================

def processar_mensagem(mensagem: str) -> RespostaBrain:
    """
    Função conveniente para processar uma mensagem sem instanciar manualmente.
    
    Args:
        mensagem: Texto da mensagem do usuário
    
    Returns:
        RespostaBrain com resultado do processamento
    
    Example:
        >>> from engine.brain_middleware import processar_mensagem
        >>> resultado = processar_mensagem("Lex, anota: comprar microfone")
        >>> print(resultado.resposta_ia)
    """
    brain = BrainMiddleware()
    return brain.processar(mensagem)


# ============================================================================
# BLOCO DE TESTE RÁPIDO
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧠 BRAIN MIDDLEWARE - TESTE RÁPIDO")
    print("=" * 60)
    
    # Inicializar
    brain = BrainMiddleware()
    
    if brain.inicializar():
        print("\n✅ Brain Middleware inicializado!")
        
        # Testes de exemplo
        testes = [
            "Lex, anota que preciso comprar um microfone Blue Yeti",
            "Lex, lembra que tenho que terminar o vídeo até sexta",
            "Lex, o que eu já escrevi sobre YouTube?",
            "Lex, me dá 5 ideias de vídeo sobre automação com IA",
            "Lex, como estão minhas métricas dessa semana?",
            "Lex, cria um plano para escalar meu canal em 90 dias",
        ]
        
        print("\n🧪 Executando testes...\n")
        
        for i, teste in enumerate(testes, 1):
            print(f"--- Teste {i}: {teste[:50]}... ---")
            resultado = brain.processar(teste)
            print(f"✅ Sucesso: {resultado.sucesso}")
            print(f"📝 Ação: {resultado.acao_executada}")
            print(f"💬 Resposta: {resultado.resposta_ia[:100]}...\n")
        
        print("🎉 Testes concluídos!")
        
    else:
        print("\n❌ Erro ao inicializar Brain Middleware")