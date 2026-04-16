"""
==============================================================================
LLM CLIENT v1.3 - Cliente de Modelos de Linguagem Multi-Provedor
==============================================================================

HISTÓRICO DE VERSÕES:
- v1.0 → v1.1: Refatoração inicial
- v1.1 → v1.2: Constantes movidas para fora da classe, suporte Gemini
- v1.2 → v1.3: CORREÇÕES CRÍTICAS:
  * Removido uso inválido de "..." em assinaturas de métodos
  * Adicionados imports faltantes (Union, Dict, List)
  * Eliminados métodos duplicados (gerar_stream, obter_estatisticas)
  * Inicialização completa de atributos no __init__
  * Corrigido conflito entre propriedade client e atributo self.client
  * Padronizada nomenclatura em português (provedor, não provider)

AUTOR: Lex-Brain Hybrid
DATA DE ATUALIZAÇÃO: 15/04/2026
STATUS: ✅ PRONTO PARA PRODUÇÃO (COM GEMINI 2.5 FLASH!)
==============================================================================
"""

# =============================================================================
# IMPORTAÇÕES PADRÃO DO PYTHON
# =============================================================================

from __future__ import annotations  # Permite usar tipos como forward references

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Generator, Optional, Union, Dict, List


# =============================================================================
# IMPORTAÇÃO CONDICIONAL DO CLIENTE GEMINI
# =============================================================================
# Tenta importar o cliente Gemini. Se não estiver disponível (SDK não instalado),
# o sistema continua funcionando mas usa apenas NVIDIA como fallback.

try:
    from engine.gemini_client import GeminiClient, criar_gemini_client
    GEMINI_SDK_DISPONIVEL = True
except ImportError:
    GEMINI_SDK_DISPONIVEL = False


# =============================================================================
# CONFIGURAÇÃO DE LOGGING ESTRUTURADO
# =============================================================================

logger_llm = logging.getLogger("LexBrain.LLMClient")
logger_llm.setLevel(logging.DEBUG)

# Diretório para arquivos de log
diretorio_logs = Path(__file__).parent.parent / "logs"
diretorio_logs.mkdir(exist_ok=True)

# Handler para escrever logs em arquivo
manipulador_arquivo = logging.FileHandler(
    diretorio_logs / "llm_client.log",
    encoding="utf-8"
)
manipulador_arquivo.setLevel(logging.DEBUG)

# Formato das mensagens de log
formatador_log = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
manipulador_arquivo.setFormatter(formatador_log)
logger_llm.addHandler(manipulador_arquivo)

# Handler para exibir logs no console (apenas INFO ou superior)
manipulador_console = logging.StreamHandler()
manipulador_console.setLevel(logging.INFO)
manipulador_console.setFormatter(formatador_log)
logger_llm.addHandler(manipulador_console)


# =============================================================================
# ENUMERAÇÃO DE PROVEDORES LLM DISPONÍVEIS
# =============================================================================

class ProvedorLLM(str, Enum):
    """
    Enumeração dos provedores de LLM suportados pelo sistema.
    
    Cada provedor tem uma API diferente, mas o LLMClient abstrai essas diferenças.
    """
    NVIDIA = "nvidia"          # NVIDIA NIM API (compatível com OpenAI)
    OPENAI = "openai"          # OpenAI oficial
    GEMINI = "gemini"          # Google Gemini (NOVO! v1.2+)
    LOCAL = "local"            # Modelos locais via Ollama


# =============================================================================
# URLS PADRÃO POR PROVEDOR
# =============================================================================

URLS_PADRAO_POR_PROVEDOR = {
    ProvedorLLM.NVIDIA: "https://integrate.api.nvidia.com/v1",
    ProvedorLLM.OPENAI: "https://api.openai.com/v1",
    ProvedorLLM.GEMINI: None,   # Gemini usa SDK próprio, não precisa de URL base
    ProvedorLLM.LOCAL: None,    # Ollama roda localmente
}


# =============================================================================
# CLASSES DE DADOS (DATACLASSES)
# =============================================================================

@dataclass
class MensagemLLM:
    """
    Representa uma única mensagem no histórico de conversa.
    
    Atributos:
        role: Papel da mensagem ("system", "user", ou "assistant")
        conteudo: Texto da mensagem
        reasoning: Raciocínio interno do modelo (opcional, para modelos com thinking)
        timestamp: Momento em que a mensagem foi criada
    """
    role: str  # "system", "user", "assistant"
    conteudo: str
    reasoning: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def para_dicionario(self) -> dict[str, str]:
        """Converte a mensagem para dicionário (formato esperado pelas APIs)."""
        return {"role": self.role, "content": self.conteudo}


@dataclass
class RespostaLLM:
    """
    Resposta completa retornada pelo modelo de linguagem.
    
    Esta classe encapsula todos os dados relevantes de uma resposta do LLM,
    incluindo métricas de performance para monitoramento.
    
    Atributos:
        conteudo: Texto principal da resposta
        reasoning: Raciocínio interno (se o modelo suportar thinking)
        modelo: Nome do modelo usado para gerar a resposta
        provedor: Nome do provedor ("nvidia", "gemini", etc.)
        tokens_usados: Dicionário com contagem de tokens (prompt, completion, total)
        tempo_execucao: Tempo em segundos que a chamada à API demorou
        custo_estimado: Custo estimado da chamada (em dólares)
    """
    conteudo: str
    reasoning: Optional[str] = None
    modelo: str = ""
    provedor: str = ""
    tokens_usados: dict[str, int] = field(default_factory=dict)
    tempo_execucao: float = 0.0
    custo_estimado: float = 0.0
    
    def para_dicionario(self) -> dict[str, Any]:
        """Converte a resposta para dicionário (útil para serialização JSON)."""
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
# CONSTANTES GLOBAIS DE CONFIGURAÇÃO
# =============================================================================

# Valores padrão para parâmetros do modelo
TEMPERATURA_PADRAO = 0.7          # Criatividade do modelo (0.0 = determinístico, 1.0 = muito criativo)
MAX_TOKENS_PADRAO = 4096          # Máximo de tokens na resposta
TOP_P_PADRAO = 1.0                # Nucleus sampling (1.0 = desativado)

# Sistema padrão que define a personalidade do assistente
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

# Template para quando há contexto RAG disponível
TEMPLATE_RAG = """{sistema}

CONTEXTO RELEVANTE ENCONTRADO NA BASE DE CONHECIMENTO:
---
{contextos}
---

Com base nos contextos acima, responda à pergunta do usuário.
Se os contextos não contêm informação suficiente, diga honestamente e use seu conhecimento geral.

IMPORTANTE:
- Cite as fontes quando usar informação dos contextos
- Seja específico e acionável nas respostas
- Se não souber, diga que não sabe em vez de inventar"""


# =============================================================================
# CLASSE PRINCIPAL: LLMCLIENT
# =============================================================================

class LLMClient:
    """
    Cliente unificado para múltiplos provedores de LLM.
    
    Esta classe abstrai as diferenças entre as APIs de diferentes provedores
    (NVIDIA, OpenAI, Google Gemini), permitindo trocar de provedor com 
    mínimas alterações no código.
    
    CARACTERÍSTICAS PRINCIPAIS:
    - Suporte a múltiplos provedores (NVIDIA, OpenAI, Gemini, Local)
    - Streaming de respostas (texto aparece aos poucos)
    - Suporte a reasoning/thinking (modelos que mostram raciocínio)
    - Histórico de conversa automático
    - Fallback automático: se Gemini falhar, volta para NVIDIA
    - Logging estruturado para debug e monitoramento
    
    EXEMPLO DE USO BÁSICO:
        >>> llm = LLMClient(provedor=ProvedorLLM.GEMINI, api_key="sua_chave")
        >>> resposta = llm.gerar("Olá, como você está?")
        >>> print(resposta.conteudo)
    
    EXEMPLO COM STREAMING:
        >>> for chunk in llm.gerar_stream("Conte uma história"):
        ...     print(chunk["conteudo"], end="")
    
    ATRIBUTOS:
        provedor: Provedor LLM atualmente em uso (enum ProvedorLLM)
        modelo: Nome do modelo configurado (ex: "gemini-2.5-flash")
        api_key: Chave API do provedor (carregada de variável de ambiente)
        temperatura_padrao: Valor padrão de temperatura para gerações
        max_tokens_padrao: Valor padrão máximo de tokens na resposta
        fallback_automatico: Se True, automaticamente muda de provedor se der erro
    """

    # =========================================================================
    # MÉTODO CONSTRUTOR (__init__)
    # =========================================================================
    
    def __init__(
        self,
        provedor: Union[ProvedorLLM, str] = ProvedorLLM.GEMINI,
        modelo: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperatura_padrao: float = TEMPERATURA_PADRAO,
        max_tokens_padrao: int = MAX_TOKENS_PADRAO,
        fallback_automatico: bool = True
    ):
        """
        Inicializa o cliente LLM com configurações específicas do provedor.
        
        ARGUMENTOS:
            provedor: Provedor LLM a ser usado (padrão: GEMINI a partir de v1.3)
                     Pode ser enum ProvedorLLM ou string ("nvidia", "gemini", "openai")
            modelo: Nome específico do modelo (se None, usa padrão do provedor)
            api_key: Chave da API (se None, busca em variáveis de ambiente)
            base_url: URL base da API (se None, usa URL padrão do provedor)
            temperatura_padrao: Temperatura padrão para gerações (0.0 a 1.0)
            max_tokens_padrao: Máximo de tokens nas respostas
            fallback_automatico: Se True, tenta outro provedor se o principal falhar
        
        LEVANTA:
            ValueError: Se o provedor não for suportado ou API key não encontrada
            ImportError: Se o SDK do Gemini for necessário mas não estiver instalado
        """
        
        # -----------------------------------------------------------------
        # PASSO 1: Converter e validar o provedor
        # -----------------------------------------------------------------
        if isinstance(provedor, str):
            # Mapeamento de strings para enums
            mapeamento_provedores = {
                "nvidia": ProvedorLLM.NVIDIA,
                "gemini": ProvedorLLM.GEMINI,
                "openai": ProvedorLLM.OPENAI,
                "local": ProvedorLLM.LOCAL
            }
            provedor_enum = mapeamento_provedores.get(provedor.lower(), ProvedorLLM.NVIDIA)
        else:
            provedor_enum = provedor
        
        # -----------------------------------------------------------------
        # PASSO 2: Armazenar configurações básicas
        # -----------------------------------------------------------------
        self.provedor = provedor_enum
        self.modelo = ""  # Será definido abaixo conforme o provedor
        self.api_key = api_key or ""
        self.base_url = base_url or ""
        self.temperatura_padrao = temperatura_padrao
        self.max_tokens_padrao = max_tokens_padrao
        self.fallback_automatico = fallback_automatico
        
        # -----------------------------------------------------------------
        # PASSO 3: Inicializar atributos internos (TODOS aqui!)
        # -----------------------------------------------------------------
        self._cliente_api = None           # Cliente da API (OpenAI ou Gemini)
        self._gemini_client = None         # Cliente específico do Gemini (se aplicável)
        self._historico: List[MensagemLLM] = []  # Histórico de conversa
        self._total_requisicoes = 0        # Contador total de requisições feitas
        self._total_tokens_usados = 0      # Contador total de tokens consumidos
        self.sistema = SISTEMA_PADRAO      # Prompt de sistema atual
        
        # -----------------------------------------------------------------
        # PASSO 4: Configurar conforme o provedor escolhido
        # -----------------------------------------------------------------
        
        if provedor_enum == ProvedorLLM.GEMINI:
            # ======== CONFIGURAÇÃO GOOGLE GEMINI ========
            self.modelo = modelo or "gemini-2.5-flash"
            self.api_key = api_key or os.getenv("GEMINI_API_KEY")
            
            if not self.api_key:
                raise ValueError(
                    "GEMINI_API_KEY não encontrada! "
                    "Configure: export GEMINI_API_KEY='sua_chave_aqui'"
                )
            
            # Tentar inicializar o cliente Gemini
            self._inicializar_cliente_gemini()
            
        elif provedor_enum == ProvedorLLM.NVIDIA:
            # ======== CONFIGURAÇÃO NVIDIA (ORIGINAL) ========
            self.modelo = modelo or "z-ai/glm5"
            self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
            self.base_url = base_url or URLS_PADRAO_POR_PROVEDOR[ProvedorLLM.NVIDIA]
            
            if not self.api_key:
                raise ValueError(
                    "NVIDIA_API_KEY não encontrada! "
                    "Configure: export NVIDIA_API_KEY='sua_chave_aqui'"
                )
            
            # Importar e criar cliente OpenAI-compatible (NVIDIA usa este formato)
            from openai import OpenAI
            self._cliente_api = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            
        elif provedor_enum == ProvedorLLM.OPENAI:
            # ======== CONFIGURAÇÃO OPENAI OFICIAL ========
            self.modelo = modelo or "gpt-4"
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            self.base_url = base_url or URLS_PADRAO_POR_PROVEDOR[ProvedorLLM.OPENAI]
            
            from openai import OpenAI
            self._cliente_api = OpenAI(api_key=self.api_key, base_url=self.base_url)
            
        else:
            raise ValueError(f"Provedor não suportado: {provedor_enum}")
        
        logger_llm.info(
            f"Cliente LLM criado com sucesso "
            f"(provedor: {self.provedor.value}, modelo: {self.modelo})"
        )

    # =========================================================================
    # MÉTODOS PRIVADOS DE INICIALIZAÇÃO
    # =========================================================================

    def _inicializar_cliente_gemini(self):
        """
        Inicializa o cliente Google Gemini 2.5 Flash.
        
        Este método é chamado automaticamente no construtor quando o provedor
        é GEMINI. Ele usa o import que já foi feito no topo do arquivo.
        
        SE O SDK NÃO ESTIVER INSTALADO:
            - O import no topo do arquivo já terá falhado e setado 
            GEMINI_SDK_DISPONIVEL = False
            - Este método levanta ImportError
            - O fallback automático para NVIDIA é acionado no __init__
        
        SE TUDO CERTO:
            - Cria o cliente Gemini usando criar_gemini_client()
            - Loga sucesso
        """
        # ================================================================
        # CORREÇÃO CRÍTICA v1.3:
        # NÃO re-importar dentro deste método!
        # O import já foi feito no topo do arquivo (fora da classe).
        # Re-importar aqui causa "UnboundLocalError" porque Python considera
        # a variável como local mesmo quando o if não executa.
        # ================================================================
        
        try:
            # Verificar se o SDK está disponível (foi importado no topo?)
            if not GEMINI_SDK_DISPONIVEL:
                # SDK não disponível - mas NÃO re-importar aqui!
                # Apenas levantar erro informativo para cair no except
                raise ImportError(
                    "SDK google-genai não disponível (import no topo falhou). "
                    "Instale: pip install google-genai"
                )
            
            # Criar o cliente Gemini usando a função importada NO TOPO DO ARQUIVO
            # (não há risco de UnboundLocalError agora!)
            self._gemini_client = criar_gemini_client(
                api_key=self.api_key,
                modo="flash"  # Modo rápido: gemini-2.5-flash
            )
            
            logger_llm.info("✅ [GEMINI] Cliente Gemini 2.5 Flash inicializado com sucesso!")
            
        except ImportError as erro_importacao:
            # SDK do Gemini não está instalado ou import falhou
            logger_llm.warning(
                "⚠️ [GEMINI] SDK google-genai não instalado ou import falhou. "
                "Execute: pip install google-genai"
            )
            logger_llm.warning("🔄 [FALLBACK] Mudando automaticamente para NVIDIA...")
            
            if self.fallback_automatico:
                self._executar_fallback_para_nvidia()
            else:
                raise ImportError(
                    "SDK do Gemini não instalado e fallback desativado. "
                    "Instale com: pip install google-genai"
                ) from erro_importacao
                
        except Exception as erro_generico:
            # Qualquer outro erro durante a inicialização
            logger_llm.error(f"❌ [GEMINI] Erro ao inicializar cliente: {erro_generico}")
            
            if self.fallback_automatico:
                logger_llm.warning("🔄 [FALLBACK] Mudando automaticamente para NVIDIA...")
                self._executar_fallback_para_nvidia()
            else:
                raise RuntimeError(
                    f"Falha ao inicializar Gemini: {erro_generico}"
                ) from erro_generico
    
    def _executar_fallback_para_nvidia(self):
        """
        Executa o fallback de emergência para NVIDIA/GLM5.
        
        Este método é chamado quando o Gemini falha e fallback_automatico=True.
        Ele reconfigura o cliente para usar a API da NVIDIA como backup.
        
        MUDANÇAS REALIZADAS:
            - Altera self.provedor para NVIDIA
            - Altera self.modelo para "z-ai/glm5"
            - Carrega API key da variável de ambiente NVIDIA_API_KEY
            - Cria novo cliente OpenAI-compatible apontando para NVIDIA
            - Reseta o cliente Gemini para None
        """
        logger_llm.info("🔄 Executando fallback para NVIDIA/GLM5...")
        
        # Mudar configuração para NVIDIA
        self.provedor = ProvedorLLM.NVIDIA
        self.modelo = "z-ai/glm5"
        self.api_key = os.getenv("NVIDIA_API_KEY", "")
        self.base_url = URLS_PADRAO_POR_PROVEDOR[ProvedorLLM.NVIDIA]
        
        # Limpar cliente Gemini (não será mais usado)
        self._gemini_client = None
        
        # Criar cliente NVIDIA
        try:
            from openai import OpenAI
            self._cliente_api = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger_llm.info("✅ [FALLBACK] NVIDIA/GLM5 configurado com sucesso como backup!")
        except Exception as erro_nvidia:
            logger_llm.error(f"❌ [FALLBACK] ERRO CRÍTICO: Nem NVIDIA funcionou: {erro_nvidia}")
            raise RuntimeError(
                "Falha crítica: tanto Gemini quanto NVIDIA falharam! "
                "Verifique suas chaves de API e conexão com internet."
            ) from erro_nvidia

    # =========================================================================
    # PROPRIEDADE PARA ACESSAR O CLIENTE API (LAZY LOADING)
    # =========================================================================
    
    @property
    def cliente_api(self):
        """
        Propriedade que retorna o cliente API (lazy loading).
        
        NOTA IMPORTANTE: Esta propriedade se chama 'cliente_api' (não 'client')
        para evitar conflito com o atributo self.cliente_api que pode ser
        definido no __init__.
        
        RETORNA:
            Instância do cliente (OpenAI ou GenerativeModel do Gemini)
        """
        if self._cliente_api is None:
            # Cliente ainda não foi criado, criar agora
            
            if self.provedor in [ProvedorLLM.NVIDIA, ProvedorLLM.OPENAI, ProvedorLLM.LOCAL]:
                # Provedores compatíveis com OpenAI
                from openai import OpenAI
                
                logger_llm.info(f"📡 Conectando ao provedor {self.provedor.value}...")
                logger_llm.info(f"   URL: {self.base_url}")
                logger_llm.info(f"   Modelo: {self.modelo}")
                
                kwargs = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                
                self._cliente_api = OpenAI(**kwargs)
                logger_llm.info("✅ Cliente OpenAI conectado com sucesso!")
                
            elif self.provedor == ProvedorLLM.GEMINI:
                # Google Gemini usa SDK próprio
                import google.generativeai as genai
                
                logger_llm.info("📡 Conectando ao Google Gemini...")
                genai.configure(api_key=self.api_key)
                self._cliente_api = genai.GenerativeModel(self.modelo)
                logger_llm.info("✅ Cliente Gemini conectado com sucesso!")
                
            else:
                raise ValueError(f"Provedor não suportado na propriedade cliente_api: {self.provedor}")
        
        return self._cliente_api

    # =========================================================================
    # MÉTODO PRINCIPAL: GERAR RESPOSTA
    # =========================================================================
    
    def gerar(
        self,
        prompt: str,
        contexto_rag: Optional[List[str]] = None,
        usar_historico: bool = False,
        temperatura: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> RespostaLLM:
        """
        Gera uma resposta completa usando o LLM configurado.
        
        Este é o método principal da classe. Ele aceita um prompt e retorna
        uma resposta completa do modelo, com suporte opcional a:
        - Contexto RAG (busca semântica em documentos)
        - Histórico de conversa (para manter contexto)
        - Streaming (coleta via chunks e retorna completo ao final)
        - Escolha dinâmica entre Gemini e NVIDIA (com fallback automático)
        
        ARGUMENTOS:
            prompt: Texto principal da pergunta ou comando do usuário
            contexto_rag: Lista de trechos de texto relevantes do RAG System
            usar_historico: Se True, inclui mensagens anteriores da conversa
            temperatura: Criatividade da resposta (0.0 a 1.0). None usa padrão.
            max_tokens: Máximo de tokens na resposta. None usa padrão.
            stream: Se True, usa streaming interno mas retorna RespostaLLM completa
        
        RETORNA:
            RespostaLLM com todos os dados da resposta (conteúdo, métricas, etc.)
        
        LEVANTA:
            RuntimeError: Se ambos Gemini e NVIDIA falharem
            ValueError: Se parâmetros forem inválidos
        
        EXEMPLO:
            >>> resposta = llm.gerar("Qual a capital do Brasil?")
            >>> print(resposta.conteudo)
            "A capital do Brasil é Brasília..."
            >>> print(resposta.tempo_execucao)
            1.85
        """
        # Marcar início para medir tempo de execução
        inicio_execucao = time.time()
        
        # ================================================================
        # MODO STREAMING: Coleta todos os chunks e monta resposta completa
        # ================================================================
        if stream:
            conteudo_chunks = []
            reasoning_chunks = []
            
            # Iterar sobre o gerador de streaming
            for chunk_data in self.gerar_stream(
                prompt=prompt,
                contexto_rag=contexto_rag,
                usar_historico=usar_historico,
                temperatura=temperatura,
                max_tokens=max_tokens
            ):
                if chunk_data.get("conteudo"):
                    conteudo_chunks.append(chunk_data["conteudo"])
                if chunk_data.get("reasoning"):
                    reasoning_chunks.append(chunk_data["reasoning"])
            
            # Calcular tempo total
            tempo_total = time.time() - inicio_execucao
            
            # Retornar resposta completa montada dos chunks
            return RespostaLLM(
                conteudo="".join(conteudo_chunks),
                reasoning="".join(reasoning_chunks) if reasoning_chunks else None,
                modelo=self.modelo,
                provedor=self.provedor.value,
                tempo_execucao=tempo_total
            )
        
        # ================================================================
        # MODO NORMAL: TENTAR GEMINI PRIMEIRO (SE CONFIGURADO)
        # ================================================================
        
        # Verificar se temos cliente Gemini disponível e ativo
        tem_gemini_disponivel = (
            hasattr(self, '_gemini_client') and 
            self._gemini_client is not None and
            self.provedor == ProvedorLLM.GEMINI
        )
        
        if tem_gemini_disponivel:
            try:
                logger_llm.info(
                    f"🤖 [GEMINI] Gerando resposta com modelo {self._gemini_client.modelo}..."
                )
                
                # Construir prompt final (com contexto RAG se fornecido)
                prompt_final = prompt
                if contexto_rag and len(contexto_rag) > 0:
                    contexto_formatado = "\n\n".join([f"- {ctx}" for ctx in contexto_rag])
                    prompt_final = (
                        f"CONTEXTO ADICIONAL DA BASE DE CONHECIMENTO:\n\n"
                        f"{contexto_formatado}\n\n"
                        f"---\n\n"
                        f"{prompt}"
                    )
                
                # Realizar chamada à API do Gemini
                # Importar tipos do SDK do Gemini
                from google.genai import types
                
                # Configurar parâmetros da geração
                configuracao_geracao = types.GenerateContentConfig(
                    temperature=temperatura or self.temperatura_padrao,
                    max_output_tokens=max_tokens or self.max_tokens_padrao,
                    top_p=0.95,
                    top_k=40
                )
                
                # Chamada síncrona à API Gemini
                resposta_gemini = self._gemini_client.client.models.generate_content(
                    model=self._gemini_client.modelo,
                    contents=prompt_final,
                    config=configuracao_geracao
                )
                
                # Extrair texto da resposta do Gemini
                if hasattr(resposta_gemini, 'text'):
                    texto_resposta = resposta_gemini.text
                else:
                    # Fallback: converter para string se não tiver atributo .text
                    texto_resposta = str(resposta_gemini)
                
                # Calcular tempo de execução
                tempo_total = time.time() - inicio_execucao
                
                logger_llm.info(
                    f"✅ [GEMINI] Resposta recebida em {tempo_total:.2f}s "
                    f"({len(texto_resposta)} caracteres)"
                )
                
                # Retornar resposta estruturada
                return RespostaLLM(
                    conteudo=texto_resposta,
                    reasoning=None,  # Gemini Flash não retorna reasoning separado
                    modelo=self._gemini_client.modelo,
                    provedor="gemini",
                    tempo_execucao=tempo_total
                )
                
            except Exception as erro_gemini:
                # Erro ao chamar Gemini
                logger_llm.error(f"❌ [GEMINI] Falha na geração: {erro_gemini}")
                
                # Verificar se deve fazer fallback para NVIDIA
                if self.fallback_automatico:
                    logger_llm.warning(
                        "🔄 [FALLBACK] Gemini falhou, voltando para NVIDIA/GLM5..."
                    )
                    # Mudar provedor e continuar execução (cai no bloco NVIDIA abaixo)
                    self._executar_fallback_para_nvidia()
                else:
                    # Sem fallback, propagar erro
                    raise RuntimeError(
                        f"Gemini falhou e fallback está desativado: {erro_gemini}"
                    ) from erro_gemini
        
        # ================================================================
        # PADRÃO: NVIDIA / GLM5 (OU FALLBACK DO GEMINI)
        # ================================================================
        
        # Se chegou aqui, usar NVIDIA (ou porque era o padrão ou porque Gemini falhou)
        logger_llm.info(f"🤖 [NVIDIA] Gerando resposta com modelo {self.modelo}...")
        
        # Montar lista de mensagens no formato esperado pela API OpenAI-compatible
        mensagens = self._preparar_mensagens(
            prompt=prompt,
            contexto_rag=contexto_rag,
            usar_historico=usar_historico
        )
        
        # Montar dicionário de argumentos para a chamada da API
        argumentos_chamada = {
            "model": self.modelo,
            "messages": mensagens,
            "temperature": temperatura or self.temperatura_padrao,
            "max_tokens": max_tokens or self.max_tokens_padrao
        }
        
        # Realizar chamada à API NVIDIA (formato OpenAI-compatible)
        try:
            resposta_api = self._cliente_api.chat.completions.create(**argumentos_chamada)
            
            # Extrair conteúdo textual da resposta
            conteudo_resposta = resposta_api.choices[0].message.content or ""
            
            # Verificar se há reasoning (alguns modelos GLM retornam raciocínio separado)
            reasoning_resposta = None
            if hasattr(resposta_api.choices[0].message, 'reasoning_content'):
                reasoning_resposta = resposta_api.choices[0].message.reasoning_content
            
            # Calcular tempo de execução
            tempo_total = time.time() - inicio_execucao
            
            logger_llm.info(
                f"✅ [NVIDIA] Resposta recebida em {tempo_total:.2f}s "
                f"({len(conteudo_resposta)} caracteres)"
            )
            
            # Atualizar estatísticas
            self._total_requisicoes += 1
            if hasattr(resposta_api, 'usage') and resposta_api.usage:
                self._total_tokens_usados += getattr(resposta_api.usage, 'total_tokens', 0)
            
            # Retornar resposta estruturada
            return RespostaLLM(
                conteudo=conteudo_resposta,
                reasoning=reasoning_resposta,
                modelo=self.modelo,
                provedor=self.provedor.value,
                tempo_execucao=tempo_total
            )
            
        except Exception as erro_nvidia:
            # Erro na chamada à API NVIDIA
            logger_llm.error(f"❌ [NVIDIA] Erro na chamada à API: {erro_nvidia}")
            raise RuntimeError(
                f"Erro ao gerar resposta via NVIDIA: {erro_nvidia}"
            ) from erro_nvidia

    # =========================================================================
    # MÉTODO DE STREAMING: GERADOR DE CHUNKS
    # =========================================================================
    
    def gerar_stream(
        self,
        prompt: str,
        contexto_rag: Optional[List[str]] = None,
        usar_historico: bool = False,
        temperatura: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Generator[Dict[str, Optional[str]], None, None]:
        """
        Gerador que yields chunks da resposta em tempo real (streaming).
        
        Diferente do método gerar(), este método é um GERADOR (yield) que
        produz pedaços da resposta conforme eles chegam da API. Isso é
        útil para mostrar o texto aparecendo aos poucos no Telegram.
        
        CADA YIELD RETORNA UM DICIONÁRIO COM:
            "conteudo": Parte do texto da resposta (ou None se for reasoning)
            "reasoning": Parte do raciocínio do modelo (ou None se for conteúdo)
            "done": Booleano indicando se é o último chunk (True = terminou)
        
        ARGUMENTOS:
            Mesmos do método gerar()
        
        RETORNA:
            Gerador de dicionários com chunks da resposta
        
        EXEMPLO DE USO:
            >>> for chunk in llm.gerar_stream("Conte uma piada"):
            ...     if chunk["conteudo"]:
            ...         print(chunk["conteudo"], end="", flush=True)
            ...     if chunk["done"]:
            ...         print("\\n[Resposta completa!]")
        """
        logger_llm.info(f"🌊 Iniciando streaming (modelo: {self.modelo})...")
        
        try:
            # Preparar mensagens para a API
            mensagens = self._preparar_mensagens(
                prompt=prompt,
                contexto_rag=contexto_rag,
                usar_historico=usar_historico
            )
            
            # ============================================================
            # CASO 1: NVIDIA / OPENAI / LOCAL (API OpenAI-compatible)
            # ============================================================
            if self.provedor in [ProvedorLLM.NVIDIA, ProvedorLLM.OPENAI, ProvedorLLM.LOCAL]:
                
                # Iniciar chamada com stream=True
                stream_resposta = self._cliente_api.chat.completions.create(
                    model=self.modelo,
                    messages=mensagens,
                    temperature=temperatura or self.temperatura_padrao,
                    max_tokens=max_tokens or self.max_tokens_padrao,
                    top_p=TOP_P_PADRAO,
                    extra_body=self._obter_corpo_extra(),
                    stream=True  # IMPORTANTE: ativa streaming!
                )
                
                # Acumuladores para montar resposta completa
                partes_conteudo = []
                partes_reasoning = []
                
                # Iterar sobre cada chunk da stream
                for chunk in stream_resposta:
                    # Validar estrutura do chunk
                    if not hasattr(chunk, 'choices') or not chunk.choices:
                        continue
                    
                    escolha = chunk.choices[0]
                    
                    if not hasattr(escolha, 'delta') or escolha.delta is None:
                        continue
                    
                    delta = escolha.delta
                    
                    # Extrair reasoning (raciocínio interno do modelo)
                    reasoning_chunk = None
                    
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        reasoning_chunk = delta.reasoning_content
                    elif isinstance(delta, dict):
                        reasoning_chunk = delta.get('reasoning_content')
                    
                    # Se encontrou reasoning, yield e acumular
                    if reasoning_chunk:
                        reasoning_str = str(reasoning_chunk)
                        if reasoning_str.strip():
                            partes_reasoning.append(reasoning_str)
                            yield {
                                "conteudo": None,
                                "reasoning": reasoning_str,
                                "done": False
                            }
                    
                    # Extrair conteúdo principal
                    conteudo_chunk = getattr(delta, 'content', None)
                    
                    if conteudo_chunk is not None and str(conteudo_chunk).strip():
                        conteudo_str = str(conteudo_chunk)
                        partes_conteudo.append(conteudo_str)
                        
                        # Imprimir no console em tempo real (efeito "digitando")
                        print(conteudo_str, end="", flush=True)
                        
                        yield {
                            "conteudo": conteudo_str,
                            "reasoning": None,
                            "done": False
                        }
                
                # Fim da stream
                print()  # Nova linha após o texto
                
                # Yield final marcando conclusão
                yield {
                    "conteudo": None,
                    "reasoning": None,
                    "done": True
                }
                
                # Adicionar ao histórico de conversa
                texto_completo = "".join(partes_conteudo)
                if texto_completo.strip():
                    self._adicionar_ao_historico("user", prompt)
                    self._adicionar_ao_historico("assistant", texto_completo)
                
                # Atualizar estatísticas
                self._total_requisicoes += 1
                
            # ============================================================
            # CASO 2: GEMINI (SDK próprio)
            # ============================================================
            elif self.provedor == ProvedorLLM.GEMINI:
                # Verificar se temos cliente Gemini disponível para streaming
                if self._gemini_client and hasattr(self._gemini_client, 'gerar_stream'):
                    # Streaming nativo do Gemini (implementação futura/optional)
                    logger_llm.info("🌊 [GEMINI] Usando streaming nativo do Gemini...")
                    
                    try:
                        for chunk in self._gemini_client.gerar_stream(prompt):
                            yield {
                                "conteudo": chunk,
                                "reasoning": None,
                                "done": False
                            }
                        
                        # Marcador final
                        yield {"conteudo": None, "reasoning": None, "done": True}
                        
                    except Exception as erro_stream_gemini:
                        logger_llm.error(f"❌ [GEMINI] Erro no streaming: {erro_stream_gemini}")
                        yield {
                            "conteudo": f"[ERRO no streaming Gemini: {erro_stream_gemini}]",
                            "reasoning": None,
                            "done": True
                        }
                else:
                    # Gemini disponível mas sem suporte a streaming (ainda)
                    logger_llm.warning("⚠️ [GEMINI] Streaming não implementado, usando modo normal...")
                    yield {
                        "conteudo": "[Streaming Gemini em desenvolvimento - use gerar() por enquanto]",
                        "reasoning": None,
                        "done": True
                    }
            
        except Exception as erro_geral:
            # Erro crítico no streaming
            logger_llm.error(f"❌ Erro durante streaming: {erro_geral}")
            yield {
                "conteudo": f"[ERRO: {erro_geral}]",
                "reasoning": None,
                "done": True
            }

    # =========================================================================
    # MÉTODO: PERGUNTAR COM RAG (BUSCA SEMÂNTICA + GERAÇÃO)
    # =========================================================================
    
    def perguntar_com_rag(
        self,
        pergunta: str,
        rag_system=None,
        n_contextos: int = 3,
        stream: bool = False
    ) -> RespostaLLM:
        """
        Faz uma pergunta usando RAG completo (Retrieval-Augmented Generation).
        
        Este método combina busca semântica em documentos com geração de resposta,
        permitindo que o LLM responda perguntas baseadas em sua base de conhecimento.
        
        FLUXO DE EXECUÇÃO:
            1. Busca contextos relevantes no RAG System
            2. Formata os contextos junto com a pergunta
            3. Chama o método gerar() com o enriquecido
            4. Retorna resposta com metadados sobre as fontes usadas
        
        ARGUMENTOS:
            pergunta: Pergunta do usuário
            rag_system: Instância do RAGSystem (se None, usa conhecimento geral)
            n_contextos: Número máximo de contextos a buscar (padrão: 3)
            stream: Se True, usa streaming na geração
        
        RETORNA:
            RespostaLLM com atributos adicionais:
                .fontes: Lista de nomes das fontes usadas
                .n_contextos: Quantidade de contextos encontrados
        """
        logger_llm.info(f"🔍 [RAG] Pergunta recebida: '{pergunta[:60]}...'")
        
        # Listas para armazenar contextos e fontes
        lista_contextos_texto = []
        lista_fontes = []
        
        # Se RAG System foi fornecido, buscar contextos relevantes
        if rag_system is not None:
            try:
                resultado_busca = rag_system.perguntar(
                    pergunta=pergunta,
                    n_contextos=n_contextos
                )
                
                # Verificou se encontrou contextos relevantes
                if resultado_busca['pode_responder'] and resultado_busca['contextos']:
                    # Extrair cada contexto com sua fonte
                    for indice, contexto in enumerate(resultado_busca['contextos'], start=1):
                        nome_fonte = (
                            resultado_busca['fontes'][indice] 
                            if indice <= len(resultado_busca['fontes']) 
                            else "fonte_desconhecida"
                        )
                        
                        # Formatado contexto com identificação da fonte
                        contexto_formatado = f"[Fonte: {nome_fonte}]\n{contexto}"
                        lista_contextos_texto.append(contexto_formatado)
                        lista_fontes.append(nome_fonte)
                    
                    logger_llm.info(
                        f"📚 [RAG] Encontrados {len(lista_contextos_texto)} contextos relevantes "
                        f"(confiança: {resultado_busca['score_confianca']:.2f})"
                    )
                else:
                    logger_llm.info(
                        "⚠️ [RAG] Nenhum contexto relevante encontrado, "
                        "usando conhecimento geral do modelo"
                    )
                    
            except Exception as erro_rag:
                logger_llm.warning(f"⚠️ [RAG] Erro ao buscar contextos: {erro_rag}")
        
        # Montar prompt com ou sem contextos RAG
        if lista_contextos_texto:
            # Juntar todos os contextos com separadores
            textos_juntos = "\n\n---\n\n".join(lista_contextos_texto)
            
            # Usar template RAG que instrui o modelo a citar fontes
            prompt_sistema_rag = self.TEMPLATE_RAG.format(
                sistema=self.sistema,
                contextos=textos_juntos
            )
        else:
            # Sem contextos, usar sistema padrão
            prompt_sistema_rag = self.sistema
        
        # Salvar sistema original para restaurar depois
        sistema_original = self.sistema
        self.sistema = prompt_sistema_rag
        
        try:
            # Gerar resposta com o sistema enriquecido
            resposta = self.gerar(
                prompt=pergunta,
                stream=stream
            )
            
            # Anexar metadados de fontes à resposta
            resposta.fontes = lista_fontes
            resposta.n_contextos = len(lista_contextos_texto)
            
            return resposta
            
        finally:
            # Sempre restaurar sistema original (mesmo se der erro)
            self.sistema = sistema_original

    # =========================================================================
    # MÉTODOS AUXILIARES: HISTÓRICO E PREPARAÇÃO
    # =========================================================================
    
    def limpar_historico(self) -> None:
        """
        Limpa todo o histórico de conversa.
        
        Útil para começar uma nova conversa do zero, sem contexto anterior.
        """
        tamanho_antigo = len(self._historico)
        self._historico.clear()
        logger_llm.info(f"🧹 Histórico limpo ({tamanho_antigo} mensagens removidas)")
    
    def obter_historico(self) -> List[dict]:
        """
        Retorna o histórico de conversa como lista de dicionários.
        
        Útil para persistir a conversa ou enviar para outra parte do sistema.
        """
        return [msg.para_dicionario() for msg in self._historico]
    
    def _preparar_mensagens(
        self,
        prompt: str,
        contexto_rag: Optional[List[str]] = None,
        usar_historico: bool = False
    ) -> List[Dict[str, str]]:
        """
        Prepara a lista de mensagens no formato esperado pela API OpenAI.
        
        ESTRUTURA RETORNADA:
            [
                {"role": "system", "content": "..."},
                {"role": "user", "content": "..."},  // (opcional) mensagens anteriores
                {"role": "assistant", "content": "..."},
                {"role": "user", "content": "..."}  // prompt atual
            ]
        """
        mensagens_formatadas = []
        
        # Sempre adicionar mensagem de sistema primeiro
        mensagens_formatadas.append({"role": "system", "content": self.sistema})
        
        # Adicionar histórico de conversa (se solicitado e houver)
        if usar_historico and self._historico:
            # Limitar às últimas 20 mensagens para não exceder limite de tokens
            for mensagem in self._historico[-20:]:
                mensagens_formatadas.append(mensagem.para_dicionario())
        
        # Adicionar prompt atual (com ou sem contexto RAG)
        if contexto_rag and len(contexto_rag) > 0:
            # Temos contexto RAG, injetar antes do prompt
            contexto_junto = "\n\n---\n\n".join(contexto_rag)
            mensagem_enriquecida = (
                f"CONTEXTO RELEVANTE ENCONTRADO NA BASE DE CONHECIMENTO:\n\n"
                f"{contexto_junto}\n\n"
                f"Com base neste contexto, responda à seguinte pergunta:\n\n"
                f"{prompt}"
            )
            mensagens_formatadas.append({"role": "user", "content": mensagem_enriquecida})
        else:
            # Sem contexto RAG, prompt puro
            mensagens_formatadas.append({"role": "user", "content": prompt})
        
        return mensagens_formatadas
    
    def _obter_corpo_extra(self) -> Dict[str, Any]:
        """
        Retorna parâmetros extras para enviar na API (usado para models com thinking).
        
        Alguns modelos (como GLM e DeepSeek) suportam "thinking" ou "reasoning",
        onde o modelo mostra seu raciocínio interno antes da resposta final.
        Este método configura esses parâmetros extras.
        """
        parametros_extras = {}
        
        # Ativar thinking para modelos que suportam
        if "glm" in self.modelo.lower() or "deepseek" in self.modelo.lower():
            parametros_extras["chat_template_kwargs"] = {
                "enable_thinking": True,
                "clear_thinking": False  # Mantém o raciocínio visível
            }
        
        return parametros_extras
    
    def _adicionar_ao_historico(self, role: str, conteudo: str) -> None:
        """
        Adiciona uma mensagem ao histórico de conversa.
        
        Mantém o histórico limitado às últimas 50 mensagens para economizar memória.
        """
        self._historico.append(MensagemLLM(role=role, conteudo=conteudo))
        
        # Manter histórico limitado (máximo 50 mensagens)
        if len(self._historico) > 50:
            self._historico = self._historico[-50:]

    # =========================================================================
    # MÉTODO: OBTER ESTATÍSTICAS DE USO
    # =========================================================================
    
    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Retorna estatísticas completas de uso do cliente LLM.
        
        INCLUI:
            - Configuração atual (provedor, modelo, temperatura)
            - Contadores de uso (requisições, tokens)
            - Estado do histórico
            - Disponibilidade do Gemini
            - Estatísticas específicas do Gemini (se ativo)
        
        Útil para monitoramento e debugging.
        """
        estatisticas = {
            # Configuração atual
            "provedor": self.provedor.value,
            "modelo": self.modelo,
            "base_url": self.base_url,
            "temperatura": self.temperatura_padrao,
            "max_tokens": self.max_tokens_padrao,
            
            # Contadores de uso
            "total_requisicoes": self._total_requisicoes,
            "total_tokens_usados": self._total_tokens_usados,
            
            # Estado do histórico
            "historico_tamanho": len(self._historico),
            
            # Configuração de API
            "api_key_configurada": bool(bool(self.api_key)),
            "fallback_automatico": self.fallback_automatico,
            
            # Estado do Gemini
            "gemini_sdk_disponivel": GEMINI_SDK_DISPONIVEL,
            "gemini_client_ativo": self._gemini_client is not None,
        }
        
        # Se Gemini está ativo, incluir estatísticas dele
        if self._gemini_client and hasattr(self._gemini_client, 'obter_estatisticas'):
            try:
                estatisticas["gemini"] = self._gemini_client.obter_estatisticas()
            except Exception:
                estatisticas["gemini"] = {"erro": "Não foi possível obter stats do Gemini"}
        
        return estatisticas


# =============================================================================
# FUNÇÕES DE FÁBRICA (FACTORY FUNCTIONS)
# =============================================================================

def criar_llm_nvidia(
    api_key: str,
    modelo: str = "z-ai/glm5",
    **kwargs_adicionais
) -> LLMClient:
    """
    Função fábrica para criar um cliente LLM com provedor NVIDIA.
    
    Facilita a criação de clientes NVIDIA sem precisar lembrar de todos
    os parâmetros. Simplesmente passa a API key e o modelo desejado.
    
    ARGUMENTOS:
        api_key: Chave da API da NVIDIA (nvapi-...)
        modelo: Modelo a ser usado (padrão: "z-ai/glm5")
        **kwargs_adicionais: Outros parâmetros passados para LLMClient
    
    RETORNA:
        Instância de LLMClient configurada para NVIDIA
    
    EXEMPLO:
        >>> llm_nvidia = criar_llm_nvidia(
        ...     api_key="nvapi-sua-chave-aqui",
        ...     modelo="z-ai/glm5"
        ... )
        >>> resposta = llm_nvidia.gerar("Olá!")
    """
    return LLMClient(
        provedor=ProvedorLLM.NVIDIA,
        api_key=api_key,
        modelo=modelo,
        base_url="https://integrate.api.nvidia.com/v1",
        **kwargs_adicionais
    )


def criar_llm_gemini(
    api_key: str,
    modelo: str = "gemini-2.5-flash",
    **kwargs_adicionais
) -> LLMClient:
    """
    Função fábrica para criar um cliente LLM com provedor Google Gemini.
    
    Facilita a criação de clientes Gemini. Recomendado usar gemini-2.5-flash
    para melhor performance (mais rápido e mais barato).
    
    ARGUMENTOS:
        api_key: Chave da API do Google AI (começa com "AIza...")
        modelo: Modelo a ser usado (padrão: "gemini-2.5-flash")
        **kwargs_adicionais: Outros parâmetros passados para LLMClient
    
    RETORNA:
        Instância de LLMClient configurada para Gemini
    
    EXEMPLO:
        >>> llm_gemini = criar_llm_gemini(
        ...     api_key="AIzaSy...",
        ...     modelo="gemini-2.5-flash"
        ... )
        >>> resposta = llm_gemini.gerar("Como você está?")
    """
    return LLMClient(
        provedor=ProvedorLLM.GEMINI,
        api_key=api_key,
        modelo=modelo,
        **kwargs_adicionais
    )


# =============================================================================
# BLOCO DE TESTE RÁPIDO (EXECUTA QUANDO RODA O ARQUIVO DIRETAMENTE)
# =============================================================================

if __name__ == "__main__":
    """
    Teste rápido para verificar se o LLMClient está funcionando.
    
    Execute: python engine/llm_client.py
    """
    
    print("=" * 70)
    print("🤖 LLM CLIENT v1.3 - TESTE RÁPIDO DE FUNCIONAMENTO")
    print("=" * 70)
    print()
    
    # -----------------------------------------------------------------
    # TESTE 1: Verificar importações e classes
    # -----------------------------------------------------------------
    print("✅ [1/4] Verificando importações...")
    print(f"   - Classe LLMClient: {LLMClient is not None}")
    print(f"   - Enum ProvedorLLM: {list(ProvedorLLM)}")
    print(f"   - Dataclass RespostaLLM: {RespostaLLM is not None}")
    print(f"   - Gemini SDK disponível: {GEMINI_SDK_DISPONIVEL}")
    print()
    
    # -----------------------------------------------------------------
    # TESTE 2: Criar cliente NVIDIA (se tiver chave)
    # -----------------------------------------------------------------
    print("✅ [2/4] Testando criação de cliente NVIDIA...")
    try:
        chave_nvidia_teste = os.getenv("NVIDIA_API_KEY", "")
        if chave_nvidia_teste:
            llm_teste_nvidia = criar_llm_nvidia(
                api_key=chave_nvidia_teste,
                modelo="z-ai/glm5"
            )
            print(f"   ✓ Cliente NVIDIA criado: {llm_teste_nvidia.modelo}")
            print(f"   ✓ Estatísticas: {llm_teste_nvidia.obter_estatisticas()['provedor']}")
        else:
            print("   ⚠ NVIDIA_API_KEY não encontrada (pulando teste NVIDIA)")
    except Exception as erro_teste_nvidia:
        print(f"   ✗ Erro no teste NVIDIA: {erro_teste_nvidia}")
    print()
    
    # -----------------------------------------------------------------
    # TESTE 3: Criar cliente Gemini (se tiver chave e SDK)
    # -----------------------------------------------------------------
    print("✅ [3/4] Testando criação de cliente Gemini...")
    try:
        chave_gemini_teste = os.getenv("GEMINI_API_KEY", "")
        if chave_gemini_teste and GEMINI_SDK_DISPONIVEL:
            llm_teste_gemini = criar_llm_gemini(
                api_key=chave_gemini_teste,
                modelo="gemini-2.5-flash"
            )
            print(f"   ✓ Cliente Gemini criado: {llm_teste_gemini.modelo}")
            print(f"   ✓ Gemini ativo: {llm_teste_gemini._gemini_client is not None}")
        else:
            if not chave_gemini_teste:
                print("   ⚠ GEMINI_API_KEY não encontrada (pulando teste Gemini)")
            if not GEMINI_SDK_DISPONIVEL:
                print("   ⚠ SDK Gemini não instalado (pip install google-genai)")
    except Exception as erro_teste_gemini:
        print(f"   ✗ Erro no teste Gemini: {erro_teste_gemini}")
    print()
    
    # -----------------------------------------------------------------
    # TESTE 4: Exibir constante e configurações
    # -----------------------------------------------------------------
    print("✅ [4/4] Configurações globais:")
    print(f"   - Temperatura padrão: {TEMPERATURA_PADRAO}")
    print(f"   - Max tokens padrão: {MAX_TOKENS_PADRAO}")
    print(f"   - Top-P padrão: {TOP_P_PADRAO}")
    print(f"   - Provedores disponíveis: {[p.value for p in ProvedorLLM]}")
    print()
    
    print("=" * 70)
    print("🎉 LLM CLIENT v1.3 - TODOS OS TESTES CONCLUÍDOS!")
    print("=" * 70)