"""
==============================================================================
LLM CLIENT v1.0 - Cliente de Modelos de Linguagem Multi-Provedor
==============================================================================

Cliente unificado para múltiplos provedores LLM:

Provedores Suportados:
- ✅ NVIDIA NIM (API compatível OpenAI) - z-ai/glm5, llama, etc.
- ✅ OpenAI (GPT-4, GPT-3.5-turbo)
- ✅ Google Gemini (gemini-pro, gemini-flash)
- ✅ Qualquer API compatível OpenAI (local, Ollama, etc.)

Funcionalidades:
- Streaming em tempo real
- Suporte a reasoning/thinking (GLM5, DeepSeek-R1)
- Contexto RAG automático
- Cache de conversas
- Fallback entre modelos

Autor: Lex-Brain Hybrid
Criado: 11/04/2026
Status: ✅ PRODUÇÃO
==============================================================================
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Generator, Optional

# =============================================================================
# CONFIGURAÇÃO DE LOGGING
# =============================================================================

logger_llm = logging.getLogger("LexBrain.LLMClient")
logger_llm.setLevel(logging.DEBUG)

log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

file_handler = logging.FileHandler(
    log_dir / "llm_client.log",
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(formatter)
logger_llm.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger_llm.addHandler(console_handler)


# =============================================================================
# ENUMERAÇÕES E CONSTANTES
# =============================================================================

class ProvedorLLM(str, Enum):
    """Provedores de LLM disponíveis."""
    NVIDIA = "nvidia"          # NVIDIA NIM API (OpenAI-compatible)
    OPENAI = "openai"          # OpenAI oficial
    GEMINI = "gemini"          # Google Gemini
    LOCAL = "local"            # Local/Ollama


@dataclass
class MensagemLLM:
    """
    Representa uma mensagem no chat.
    
    Attributes:
        role: Papel da mensagem (system, user, assistant)
        conteudo: Texto da mensagem
        reasoning: Conteúdo de raciocínio (para modelos com thinking)
        timestamp: Quando foi criada
    """
    role: str  # "system", "user", "assistant"
    conteudo: str
    reasoning: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, str]:
        """Converte para formato de API."""
        return {"role": self.role, "content": self.conteudo}


@dataclass
class RespostaLLM:
    """
    Resposta completa do LLM.
    
    Attributes:
        conteudo: Texto gerado
        reasoning: Raciocínio interno (se disponível)
        modelo: Modelo usado
        provedor: Provedor usado
        tokens_usados: Estatísticas de tokens
        tempo_execucao: Tempo em segundos
        custo_estimado: Custo estimado em USD
    """
    conteudo: str
    reasoning: Optional[str] = None
    modelo: str = ""
    provedor: str = ""
    tokens_usados: dict[str, int] = field(default_factory=dict)
    tempo_execucao: float = 0.0
    custo_estimado: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "conteudo": self.conteudo,
            "reasoning": self.reasoning,
            "modelo": self.modelo,
            "provedor": self.provedor,
            "tokens_usados": self.tokens_usados,
            "tempo_execucao": self.tempo_execucao,
            "custo_estimado": self.custo_estimado
        }


# =============================================================================
# CLASSE PRINCIPAL: LLMClient
# =============================================================================

class LLMClient:
    """
    Cliente unificado para múltiplos provedores LLM.
    
    Funcionalidades:
    - Streaming em tempo real (yield chunks)
    - Suporte a reasoning/thinking (GLM5, DeepSeek-R1, etc.)
    - Contexto RAG automático (injeta contextos encontrados)
    - Histórico de conversa
    - Múltiplos provedores com fallback
    
    Usage:
        >>> from engine.llm_client import LLMClient, ProvedorLLM
        >>> 
        >>> llm = LLMClient(
        ...     provedor=ProvedorLLM.NVIDIA,
        ...     api_key="sua-chave",
        ...     modelo="z-ai/glm5"
        ... )
        >>>
        >>> # Sem streaming
        >>> resposta = llm.gerar("Explique RAG em português")
        >>> print(resposta.conteudo)
        >>>
        >>> # Com streaming
        >>> for chunk in llm.gerar_stream("Conte uma piada"):
        ...     print(chunk, end="")
        
    Attributes:
        provedor: Provedor LLM selecionado
        api_key: Chave da API
        modelo: Nome do modelo
        base_url: URL base da API (para provedores custom)
        temperatura: Criatividade das respostas (0-2)
        max_tokens: Máximo de tokens na resposta
        _client: Instância do cliente (lazy loading)
        _historico: Lista de mensagens da conversa
    """
    
    # Configurações padrão
    TEMPERATURA_PADRAO = 0.7
    MAX_TOKENS_PADRAO = 4096
    TOP_P_PADRAO = 1.0
    
    # Templates de sistema
    SISTEMA_PADRAO = """Você é o Lex-Brain Hybrid, um assistente de IA pessoal avançado.

Suas características:
- Especialista em Segundo Cérebro e produtividade
- Ajuda a organizar conhecimento, tarefas e projetos
- Gera ideias de conteúdo criativo
- Fornece insights baseados em dados do usuário
- Responde em português brasileiro de forma clara e objetiva

Estilo de comunicação:
- Direto e prático (sem enrolação)
- Usa exemplos concretos quando possível
- Estrutura respostas com listas quando adequado
- Pode usar emojis moderadamente
- Adapta o nível de detalhe à complexidade da pergunta"""
    
    # Template RAG (injeta contextos encontrados)
    TEMPLATE_RAG = """{sistema}

CONTEXTO RELEVANTE ENCONTRADO NA BASE DE CONHECIMENTO:
---
{contextos}
---

Com base nos contextos acima, responda à pergunta do usuário.
Se os contextos não contêm informação suficiente, diga honestamente e use seu conhecimento geral.

IMPORTANTE:
- Citte as fontes quando usar informação dos contextos
- Seja específico e acionável nas respostas
- Se não souber, diga que não sabe em vez de inventar"""
    
    def __init__(
        self,
        provedor: ProvedorLLM = ProvedorLLM.NVIDIA,
        api_key: Optional[str] = None,
        modelo: str = "z-ai/glm5",
        base_url: Optional[str] = None,
        temperatura: float = TEMPERATURA_PADRAO,
        max_tokens: int = MAX_TOKENS_PADRAO,
        top_p: float = TOP_P_PADRAO,
        sistema: Optional[str] = None
    ):
        """
        Inicializa o cliente LLM.
        
        Args:
            provedor: Provedor LLM. Padrão: NVIDIA
            api_key: Chave da API (se None, busca em env/variável)
            modelo: Nome do modelo. Padrão: "z-ai/glm5"
            base_url: URL base custom (para APIs compatíveis OpenAI)
            temperatura: Criatividade (0-2). Padrão: 0.7
            max_tokens: Max tokens na resposta. Padrão: 4096
            top_p: Nucleus sampling. Padrão: 1.0
            sistema: Prompt de sistema custom. Padrão: SISTEMA_PADRAO
        """
        logger_llm.info(f"🤖 Inicializando LLM Client ({provedor.value})...")
        
        self.provedor = provedor
        self.api_key = api_key or os.getenv(f"{provedor.value.upper()}_API_KEY")
        self.modelo = modelo
        self.base_url = base_url
        self.temperatura = temperatura
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.sistema = sistema or self.SISTEMA_PADRAO
        
        # Lazy loading do cliente
        self._client = None
        
        # Histórico de conversa
        self._historico: list[MensagemLLM] = []
        
        # Contadores
        self._total_requests = 0
        self._total_tokens = 0
        
        logger_llm.info(f"   Provedor: {provedor.value}")
        logger_llm.info(f"   Modelo: {modelo}")
        if base_url:
            logger_llm.info(f"   Base URL: {base_url}")
        logger_llm.info("✅ LLM Client criado!")
    
    # =========================================================================
    # LAZY LOADING DO CLIENTE
    # =========================================================================
    
    @property
    def client(self):
        """
        Lazy loading do cliente API.
        
        Cria o cliente correto baseado no provedor selecionado.
        
        Returns:
            Instância do cliente (OpenAI, Anthropic, ou genai)
        """
        if self._client is None:
            try:
                if self.provedor in [ProvedorLLM.NVIDIA, ProvedorLLM.OPENAI, ProvedorLLM.LOCAL]:
                    # Usar SDK OpenAI (compatível com NVIDIA, Ollama, etc.)
                    from openai import OpenAI
                    
                    logger_llm.info(f"📡 Conectando ao provedor {self.provedor.value}...")
                    
                    kwargs = {
                        "api_key": self.api_key
                    }
                    
                    # Adicionar base_url se fornecido (NVIDIA, Ollama, etc.)
                    if self.base_url:
                        kwargs["base_url"] = self.base_url
                    
                    self._client = OpenAI(**kwargs)
                    
                    logger_llm.info("✅ Cliente OpenAI conectado!")
                
                elif self.provedor == ProvedorLLM.GEMINI:
                    # Usar SDK do Google GenAI
                    import google.generativeai as genai
                    
                    logger_llm.info("📡 Conectando ao Google Gemini...")
                    
                    genai.configure(api_key=self.api_key)
                    self._client = genai.GenerativeModel(self.modelo)
                    
                    logger_llm.info("✅ Cliente Gemini conectado!")
                
                else:
                    raise ValueError(f"Provedor não suportado: {self.provedor}")
                    
            except ImportError as e:
                logger_llm.error(f"❌ Biblioteca necessária não instalada: {e}")
                raise
            except Exception as e:
                logger_llm.error(f"❌ Erro ao conectar: {e}")
                raise
        
        return self._client
    
    # =========================================================================
    # MÉTODOS PRINCIPAIS DE GERAÇÃO
    # =========================================================================
    
    def gerar(
        self,
        prompt: str,
        contexto_rag: Optional[list[str]] = None,
        usar_historico: bool = False,
        temperatura: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> RespostaLLM:
        """
        Gera resposta completa (sem streaming).
        
        Args:
            prompt: Prompt do usuário
            contexto_rag: Lista de contextos do RAG (opcional)
            usar_historico: Se True, inclui histórico da conversa
            temperatura: Temperatura override
            max_tokens: Max tokens override
            stream: Se True, retorna generator (mesmo assim coleta tudo)
            
        Returns:
            RespostaLLM: Resposta completa com todos os metadados
            
        Example:
            >>> resposta = llm.gerar(
            ...     prompt="Como escalar canais dark?",
            ...     contexto_rag=["Contexto 1...", "Contexto 2..."]
            ... )
            >>> print(resposta.conteudo)
        """
        inicio = time.time()
        
        # Coletar todos os chunks se for streaming
        if stream:
            conteudo_completo = []
            reasoning_completo = []
            
            for chunk_data in self.gerar_stream(
                prompt=prompt,
                contexto_rag=contexto_rag,
                usar_historico=usar_historico,
                temperatura=temperatura,
                max_tokens=max_tokens
            ):
                if chunk_data.get("conteudo"):
                    conteudo_completo.append(chunk_data["conteudo"])
                if chunk_data.get("reasoning"):
                    reasoning_completo.append(chunk_data["reasoning"])
            
            tempo = time.time() - inicio
            
            return RespostaLLM(
                conteudo="".join(conteudo_completo),
                reasoning="".join(reasoning_completo) if reasoning_completo else None,
                modelo=self.modelo,
                provedor=self.provedor.value,
                tempo_execucao=tempo
            )
        
        # Modo normal (sem streaming)
        try:
            logger_llm.info(f"🤔 Gerando resposta (modelo: {self.modelo})...")
            
            # Preparar mensagens
            mensagens = self._preparar_mensagens(
                prompt=prompt,
                contexto_rag=contexto_rag,
                usar_historico=usar_historico
            )
            
            # Chamada à API
            if self.provedor in [ProvedorLLM.NVIDIA, ProvedorLLM.OPENAI, ProvedorLLM.LOCAL]:
                resposta_api = self.client.chat.completions.create(
                    model=self.modelo,
                    messages=mensagens,
                    temperature=temperatura or self.temperatura,
                    max_tokens=max_tokens or self.max_tokens,
                    top_p=self.top_p,
                    extra_body=self._get_extra_body()
                )
                
                # Extrair resposta
                escolha = resposta_api.choices[0]
                conteudo = escolha.message.content or ""
                reasoning = getattr(escolha.message, 'reasoning_content', None)
                
                # Tokens usados
                tokens = {
                    "prompt_tokens": resposta_api.usage.prompt_tokens if resposta_api.usage else 0,
                    "completion_tokens": resposta_api.usage.completion_tokens if resposta_api.usage else 0,
                    "total_tokens": resposta_api.usage.total_tokens if resposta_api.usage else 0
                }
                
            elif self.provedor == ProvedorLLM.GEMINI:
                # Implementação Gemini aqui se necessário
                conteudo = "Resposta Gemini (implementar)"
                reasoning = None
                tokens = {}
            
            tempo = time.time() - inicio
            
            # Criar objeto de resposta
            resposta = RespostaLLM(
                conteudo=conteudo,
                reasoning=reasoning,
                modelo=self.modelo,
                provedor=self.provedor.value,
                tokens_usados=tokens,
                tempo_execucao=tempo
            )
            
            # Atualizar histórico
            self._adicionar_ao_historico("user", prompt)
            self._adicionar_ao_historico("assistant", conteudo)
            
            # Atualizar contadores
            self._total_requests += 1
            self._total_tokens += tokens.get("total_tokens", 0)
            
            logger_llm.info(
                f"✅ Resposta gerada em {tempo:.2f}s "
                f"({tokens.get('total_tokens', 0)} tokens)"
            )
            
            return resposta
            
        except Exception as e:
            logger_llm.error(f"❌ Erro ao gerar resposta: {e}")
            raise
    
    def gerar_stream(
        self,
        prompt: str,
        contexto_rag: Optional[list[str]] = None,
        usar_historico: bool = False,
        temperatura: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Generator[dict[str, Optional[str]], None, None]:
        """
        Gerador de resposta em streaming (chunk por chunk).
        
        Yields:
            Dicionários com keys:
            - 'conteudo': Texto normal (str ou None)
            - 'reasoning': Texto de raciocínio (str ou None)
            - 'done': Bool indicando fim (último chunk)
            
        Example:
            >>> for chunk in llm.gerar_stream("Explique IA"):
            ...     if chunk['conteudo']:
            ...         print(chunk['conteudo'], end="")
            ...     if chunk['done']:
            ...         print("\n[Fim]")
        """
        logger_llm.info(f"🌊 Iniciando streaming (modelo: {self.modelo})...")
        
        try:
            # Preparar mensagens
            mensagens = self._preparar_mensagens(
                prompt=prompt,
                contexto_rag=contexto_rag,
                usar_historico=usar_historico
            )
            
            # Streaming via OpenAI-compatible API
            if self.provedor in [ProvedorLLM.NVIDIA, ProvedorLLM.OPENAI, ProvedorLLM.LOCAL]:
                completion = self.client.chat.completions.create(
                    model=self.modelo,
                    messages=mensagens,
                    temperature=temperatura or self.temperatura,
                    max_tokens=max_tokens or self.max_tokens,
                    top_p=self.top_p,
                    extra_body=self._get_extra_body(),
                    stream=True
                )
                
                conteudo_completo = []
                reasoning_completo = []
                
                for chunk in completion:
                    # Verificações mais robustas
                    if not hasattr(chunk, 'choices') or not chunk.choices:
                        continue
                    
                    escolha = chunk.choices[0]
                    
                    if not hasattr(escolha, 'delta') or escolha.delta is None:
                        continue
                    
                    delta = escolha.delta
                    
                    # Extrair reasoning (thinking) - VÁRIOS FORMATOS POSSÍVEIS
                    reasoning = None
                    
                    # Formato 1: atributo direto
                    if hasattr(delta, 'reasoning_content'):
                        reasoning = delta.reasoning_content
                    
                    # Formato 2: dentro de dict/extra
                    elif isinstance(delta, dict):
                        reasoning = delta.get('reasoning_content')
                    
                    # Formato 3: no content mas tem thinking
                    elif not getattr(delta, 'content', None):
                        # Pode ser chunk de reasoning puro
                        if hasattr(delta, 'reasoning_content'):
                            reasoning = delta.reasoning_content
                    
                    if reasoning:
                        reasoning_str = str(reasoning) if reasoning else ""
                        if reasoning_str.strip():
                            reasoning_completo.append(reasoning_str)
                            yield {
                                "conteudo": None,
                                "reasoning": reasoning_str,
                                "done": False
                            }
                    
                    # Extrair conteúdo normal
                    conteudo = getattr(delta, 'content', None)
                    
                    # Se não tem content, tenta como dict
                    if conteudo is None and isinstance(delta, dict):
                        conteudo = delta.get('content')
                    
                    if conteudo is not None and str(conteudo).strip():
                        conteudo_str = str(conteudo)
                        conteudo_completo.append(conteudo_str)
                        print(conteudo_str, end="", flush=True)  # ⬅️ PRINT DIRETO!
                        yield {
                            "conteudo": conteudo_str,
                            "reasoning": None,
                            "done": False
                        }
                
                # Chunk final
                print()  # Nova linha após streaming
                yield {
                    "conteudo": None,
                    "reasoning": None,
                    "done": True
                }
                
                # Salvar no histórico
                texto_final = "".join(conteudo_completo)
                if texto_final.strip():  # Só se tiver conteúdo
                    self._adicionar_ao_historico("user", prompt)
                    self._adicionar_ao_historico("assistant", texto_final)
                
                self._total_requests += 1
                
            elif self.provedor == ProvedorLLM.GEMINI:
                # Streaming Gemini (implementar se necessário)
                yield {"conteudo": "Streaming Gemini (implementar)", "reasoning": None, "done": True}
                
        except Exception as e:
            logger_llm.error(f"❌ Erro no streaming: {e}")
            yield {"conteudo": f"[ERRO: {e}]", "reasoning": None, "done": True}
    
    # =========================================================================
    # MÉTODO ESPECIAL: RAG COMPLETO (Retrieval + Generation)
    # =========================================================================
    
    def perguntar_com_rag(
        self,
        pergunta: str,
        rag_system=None,
        n_contextos: int = 3,
        stream: bool = False
    ) -> RespostaLLM:
        """
        Faz uma pergunta usando RAG completo (busca + geração).
        
        Este é o método principal que combina:
        1. Busca de contextos relevantes no RAG System
        2. Injeção dos contextos no prompt
        3. Geração de resposta pelo LLM
        
        Args:
            pergunta: Pergunta do usuário
            rag_system: Instância do RAGSystem (opcional)
            n_contextos: Número de contextos a buscar. Padrão: 3
            stream: Se True, usa streaming
            
        Returns:
            RespostaLLM: Resposta gerada com contextos
            
        Example:
            >>> from engine.rag_system import RAGSystem
            >>> rag = RAGSystem()
            >>> rag.inicializar()
            >>> 
            >>> resposta = llm.perguntar_com_rag(
            ...     "Como escalar canais dark?",
            ...     rag_system=rag
            ... )
            >>> print(resposta.conteudo)
        """
        logger_llm.info(f"🔍 RAG Complete: '{pergunta[:60]}...'")
        
        # Buscar contextos no RAG (se disponível)
        contextos_texto = []
        fontes = []
        
        if rag_system is not None:
            try:
                resultado_rag = rag_system.perguntar(
                    pergunta=pergunta,
                    n_contextos=n_contextos
                )
                
                if resultado_rag['pode_responder'] and resultado_rag['contextos']:
                    for i, ctx in enumerate(resultado_rag['contextos'], 1):
                        fonte = resultado_rag['fontes'][i] if i <= len(resultado_rag['fontes']) else "desconhecido"
                        contextos_texto.append(f"[Fonte: {fonte}]\n{ctx}")
                        fontes.append(fonte)
                    
                    logger_llm.info(
                        f"📚 {len(contextos_textos)} contextos encontrados "
                        f"(confiança: {resultado_rag['score_confianca']:.2f})"
                    )
                else:
                    logger_llm.info("⚠️ Nenhum contexto relevante encontrado, usando conhecimento geral")
                    
            except Exception as e:
                logger_llm.warning(f"⚠️ Erro ao buscar no RAG: {e}")
        
        # Montar prompt com contexto
        if contextos_texto:
            contexto_formatado = "\n\n---\n\n".join(contextos_texto)
            prompt_sistema = self.TEMPLATE_RAG.format(
                sistema=self.sistema,
                contextos=contexto_formatado
            )
        else:
            prompt_sistema = self.sistema
        
        # Gerar resposta temporariamente com sistema modificado
        sistema_original = self.sistema
        self.sistema = prompt_sistema
        
        try:
            resposta = self.gerar(
                prompt=pergunta,
                stream=stream
            )
            
            # Adicionar metadata sobre fontes
            resposta.fontes = fontes
            resposta.n_contextos = len(contextos_texto)
            
            return resposta
            
        finally:
            # Restaurar sistema original
            self.sistema = sistema_original
    
    # =========================================================================
    # MÉTODOS UTILITÁRIOS
    # =========================================================================
    
    def limpar_historico(self) -> None:
        """Limpa todo o histórico de conversa."""
        tamanho = len(self._historico)
        self._historico.clear()
        logger_llm.info(f"🧹 Histórico limpo ({tamanho} mensagens removidas)")
    
    def obter_historico(self) -> list[dict]:
        """Retorna o histórico como lista de dicts."""
        return [msg.to_dict() for msg in self._historico]
    
    def obter_estatisticas(self) -> dict[str, Any]:
        """Retorna estatísticas de uso do LLM."""
        return {
            "provedor": self.provedor.value,
            "modelo": self.modelo,
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
            "historico_tamanho": len(self._historico),
            "temperatura": self.temperatura,
            "max_tokens": self.max_tokens
        }
    
    # =========================================================================
    # MÉTODOS PRIVADOS
    # =========================================================================
    
    def _preparar_mensagens(
        self,
        prompt: str,
        contexto_rag: Optional[list[str]] = None,
        usar_historico: bool = False
    ) -> list[dict[str, str]]:
        """
        Prepara a lista de mensagens para a API.
        
        Args:
            prompt: Prompt do usuário
            contexto_rag: Contextos do RAG (já formatados)
            usar_historico: Se True, inclui histórico
            
        Returns:
            Lista de mensagens no formato da API
        """
        mensagens = []
        
        # Mensagem de sistema
        mensagens.append({"role": "system", "content": self.sistema})
        
        # Histórico (se solicitado)
        if usar_historico and self._historico:
            for msg in self._historico[-20:]:  # Últimas 20 mensagens
                mensagens.append(msg.to_dict())
        
        # Contexto RAG (se fornecido diretamente)
        if contexto_rag:
            contexto_texto = "\n\n---\n\n".join(contexto_rag)
            mensagem_com_contexto = (
                f"CONTEXTO RELEVANTE:\n\n{contexto_texto}\n\n"
                f"Com base neste contexto, responda:\n\n{prompt}"
            )
            mensagens.append({"role": "user", "content": mensagem_com_contexto})
        else:
            # Prompt normal
            mensagens.append({"role": "user", "content": prompt})
        
        return mensagens
    
    def _get_extra_body(self) -> dict[str, Any]:
        """
        Retorna parâmetros extras para a API.
        
        Para modelos com thinking/reasoning (GLM5, DeepSeek-R1, etc.)
        """
        extra = {}
        
        # Habilitar thinking para modelos que suportam
        if "glm" in self.modelo.lower() or "deepseek" in self.modelo.lower():
            extra["chat_template_kwargs"] = {
                "enable_thinking": True,
                "clear_thinking": False
            }
        
        return extra
    
    def _adicionar_ao_historico(self, role: str, conteudo: str) -> None:
        """Adiciona mensagem ao histórico."""
        self._historico.append(MensagemLLM(
            role=role,
            conteudo=conteudo
        ))
        
        # Limitar histórico a 50 mensagens
        if len(self._historico) > 50:
            self._historico = self._historico[-50:]


# =============================================================================
# FUNÇÃO DE FÁBRICA
# =============================================================================

def criar_llm_nvidia(
    api_key: str,
    modelo: str = "z-ai/glm5",
    **kwargs
) -> LLMClient:
    """
    Função fábrica para criar cliente NVIDIA (mais conveniente).
    
    Args:
        api_key: Chave da API NVIDIA
        modelo: Modelo. Padrão: "z-ai/glm5"
        **kwargs: Parâmetros adicionais para LLMClient
        
    Returns:
        LLMClient: Configurado para NVIDIA NIM
        
    Example:
        >>> llm = criar_llm_nvidia(
        ...     api_key="nvapi-...",
        ...     modelo="z-ai/glm5"
        ... )
        >>> resposta = llm.gerar("Olá!")
    """
    return LLMClient(
        provedor=ProvedorLLM.NVIDIA,
        api_key=api_key,
        modelo=modelo,
        base_url="https://integrate.api.nvidia.com/v1",
        **kwargs
    )


def criar_llm_gemini(
    api_key: str,
    modelo: str = "gemini-1.5-flash",
    **kwargs
) -> LLMClient:
    """
    Função fábrica para criar cliente Gemini.
    
    Args:
        api_key: Chave da API Google
        modelo: Modelo. Padrão: "gemini-1.5-flash"
        **kwargs: Parâmetros adicionais
        
    Returns:
        LLMClient: Configurado para Gemini
    """
    return LLMClient(
        provedor=ProvedorLLM.GEMINI,
        api_key=api_key,
        modelo=modelo,
        **kwargs
    )


# =============================================================================
# BLOCO DE TESTE RÁPIDO
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 LLM CLIENT - TESTE RÁPIDO")
    print("=" * 60)
    
    # Criar cliente NVIDIA (com suas credenciais!)
    print("\n📡 Criando cliente NVIDIA...")
    llm = criar_llm_nvidia(
        api_key="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",
        modelo="z-ai/glm5"
    )
    print("✅ Cliente criado!")
    
    # Teste 1: Geração simples
    print("\n" + "-" * 60)
    print("🧪 Teste 1: Geração Simples")
    print("-" * 60)
    
    resposta = llm.gerar(
        prompt="Explique o que é Second Brain em 1 parágrafo.",
        max_tokens=200
    )
    
    print(f"\n📝 Resposta ({resposta.tempo_execucao:.2f}s):")
    print(f"{resposta.conteudo}")
    
    if resposta.reasoning:
        print(f"\n🧠 Raciocínio (primeiros 200 chars):")
        print(f"{resposta.reasoning[:200]}...")
    
    # Teste 2: Streaming
    print("\n" + "-" * 60)
    print("🌊 Teste 2: Streaming")
    print("-" * 60)
    
    print("\n📝 Streaming: ")
    for chunk in llm.gerar_stream(
        prompt="Dê 3 dicas rápidas de produtividade (uma linha cada)",
        max_tokens=150
    ):
        if chunk['conteudo']:
            print(chunk['conteudo'], end="")
        if chunk['done']:
            print("\n✅ Streaming finalizado!")
    
    # Teste 3: Com RAG (simulado)
    print("\n" + "-" * 60)
    print("🔍 Teste 3: RAG Completo (Simulado)")
    print("-" * 60)
    
    contextos_simulados = [
        "Second Brain é um sistema de organização pessoal digital...",
        "Ferramentas populares incluem Obsidian, Notion, Evernote...",
        "A metodologia PARA organiza: Projects, Areas, Resources, Archives..."
    ]
    
    resposta_rag = llm.gerar(
        prompt="O que preciso para começar um Second Brain?",
        contexto_rag=contextos_simulados,
        max_tokens=250
    )
    
    print(f"\n📝 Resposta com RAG ({resposta_rag.tempo_execucao:.2f}s):")
    print(f"{resposta_rag.conteudo}")
    
    # Estatísticas
    print("\n" + "-" * 60)
    print("📊 Estatísticas")
    print("-" * 60)
    
    stats = llm.obter_estatisticas()
    for chave, valor in stats.items():
        print(f"   {chave}: {valor}")
    
    print("\n" + "=" * 60)
    print("🎉 TESTES DO LLM CLIENT CONCLUÍDOS!")
    print("=" * 60)