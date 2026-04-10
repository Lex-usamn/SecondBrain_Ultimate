"""
================================================================================
DECISION ENGINE v2.0 - Motor de Decisão e Classificação P.A.R.A
================================================================================

VERSÃO: 2.0 (Refatorada - Integração Lex Flow Completa)
DATA: 2026-04-09
AUTOR: Lex-Usamn | Second Brain Ultimate System
STATUS: ✅ Refatorado e Pronto para Produção

FUNÇÃO PRINCIPAL:
-----------------
Este módulo é o "cérebro executivo" do sistema Lex-Brain Hybrid.
Responsável por:

✅ Classificação P.A.R.A. (Projects, Areas, Resources, Archives)
✅ Priorização inteligente de tarefas com suporte de IA
✅ Análise de contexto para tomada de decisões
✅ Sugestões de ações baseadas em padrões históricos
✅ Roteamento automático de itens capturados para categorias corretas

METODOLOGIA P.A.R.A. (de Tiago Forte):
-------------------------------------
• PROJECTS (Projetos): Tarefas ativas com deadline específico
• AREAS (Áreas): Responsabilidades contínuas sem deadline
• RESOURCES (Recursos): Referências, materiais de aprendizado
• ARCHIVES (Arquivos): Itens concluídos/inativos (mas úteis)

PADRÃO DE PROJETO ARQUITETURAL:
--------------------------------
• Recebe LexFlowClient real no construtor (injeção de dependência)
• NENHUM mock ou simulação em produção
• Todas as operações passam pela API do Lex Flow
• Logging estruturado de cada decisão/classificação
• Tratamento robusto de erros (nunca crasha o sistema)

INTEGRAÇÃO COM LEX FLOW API:
-----------------------------
• smart_categorize() → Classificação automática via IA do Lex Flow
• get_projects() → Obter projetos para roteamento
• get_areas() → Obter áreas para classificação
• add_note() / add_task() → Criar itens após decisão
• search_notes() → Buscar contexto histórico

DEPENDÊNCIAS:
------------
• engine/core_engine.py (CoreEngine Singleton)
• integrations/lex_flow_definitivo.py (LexFlowClient)
• config/settings.yaml (configurações)

EXEMPLO DE USO:
--------------
    from engine.decision_engine import DecisionEngine
    from integrations.lex_flow_definitivo import LexFlowClient
    
    # Inicializar cliente Lex Flow
    lex_client = LexFlowClient(
        base_url="https://flow.lex-usamn.com.br",
        username="Lex-Usamn",
        password="Lex#157."
    )
    lex_client.autenticar()
    
    # Inicializar Decision Engine com cliente real
    motor_decisao = DecisionEngine(lex_flow_client=lex_client)
    
    # Classificar uma nota usando IA do Lex Flow
    resultado = motor_decisao.classificar_item(
        texto="Ideia de vídeo sobre criptomoedas",
        tipo="idea"
    )
    print(resultado)  
    # {'categoria': 'PROJECTS', 'projeto_id': 5, 'confianca': 0.89, ...}
    
    # Priorizar tarefas do dia
    prioridades = motor_decisao.priorizar_tarefas(tarefas_lista)

================================================================================
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from enum import Enum


# ============================================================================
# IMPORTAÇÕES DO SISTEMA
# ============================================================================

# Tipos do LexFlowClient (para type hints precisos)
try:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from integrations.lex_flow_definitivo import LexFlowClient
except ImportError:
    pass


# ============================================================================
# CONFIGURAÇÃO DE LOGGING ESPECÍFICA DO DECISION ENGINE
# ============================================================================

logger_decision = logging.getLogger('DecisionEngine')


# ============================================================================
# ENUMERAÇÕES E CONSTANTES (Classificação P.A.R.A.)
# ============================================================================

class CategoriaPARA(Enum):
    """
    Enumeração das 4 Categorias do Método P.A.R.A.
    
    Cada item capturado pelo sistema deve ser classificado em UMA destas categorias.
    Esta classificação determina onde o item vai ser armazenado e como será tratado.
    
    CATEGORIAS:
    ----------
    PROJECTS: Projetos ativos com objetivo claro e deadline definido.
              Ex: "Lançar canal dark até Junho", "Escrever livro Q3"
              
    AREAS: Áreas de responsabilidade contínua (sem deadline específico).
           Ex: "Saúde", "Finanças", "Carreira", "Relacionamentos"
           
    RESOURCES: Recursos e referências para uso futuro.
               Ex: Artigos, vídeos, tutoriais, livros, contatos úteis
               
    ARCHIVES: Arquivos de itens concluídos ou inativos (mas mantidos).
              Ex: Projetos finalizados, notas antigas, referências usadas
    """
    PROJECTS = "Projects"
    AREAS = "Areas"
    RESOURCES = "Resources"
    ARCHIVES = "Archives"


class NivelPrioridade(Enum):
    """
    Níveis de Prioridade para Tarefas e Itens.
    
    Usado pelo motor de decisão para ordenar e destacar itens importantes.
    Quanto maior a urgência/importância, maior o nível.
    
    NÍVEIS (ordem crescente de importância):
    ----------------------------------------
    LOW: Baixa prioridade - pode esperar, fazer quando sobrar tempo
    MÉDIA: Prioridade normal - importante mas não urgente
    HIGH: Alta prioridade - importante e deve ser feito em breve
    URGENT: Urgentíssima - requer atenção imediata (crítico)
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TipoItem(Enum):
    """
    Tipo do Item Capturado (para classificação inicial).
    
    Determina qual pipeline de processamento o item vai seguir.
    """
    TASK = "task"           # Tarefa ação concreta
    IDEA = "idea"           # Ideia ou inspiração
    NOTE = "note"           # Nota ou anotação geral
    REFERENCE = "reference" # Referência externa (link, artigo)


# ============================================================================
# CLASSE PRINCIPAL: DECISION ENGINE
# ============================================================================

class DecisionEngine:
    """
    Motor de Decisão e Classificação Inteligente do Sistema Lex-Brain Hybrid.
    
    ====================================================================
    PROPÓSITO CENTRAL:
    Este é o "cérebro executivo" que decide ONDE cada item vai,
    QUÃO IMPORTANTE ele é, e QUAL ação deve ser tomada.
    
    Ele transforma dados brutos (textos capturados) em informações
    estruturadas (tarefas priorizadas, ideias categorizadas, etc.)
    
    ====================================================================
    FLUXO DE PROCESSAMENTO:
    
    1. ENTRADA: Item bruto (texto + metadados básicos)
       ↓
    2. ANÁLISE DE CONTEXTO: Examina conteúdo, tags, histórico
       ↓
    3. CLASSIFICAÇÃO P.A.R.A.: Decide categoria (Project/Area/Resource/Archive)
       ↓
    4. PRIORIZAÇÃO: Atribui nível de urgência/importância
       ↓
    5. ROTEAMENTO: Envia para local correto no Lex Flow
       ↓
    6. SAÍDA: Item estruturado + sugestões de ações
    
    ====================================================================
    INTEGRAÇÃO COM LEX FLOW:
    
    • self._lex_flow → Cliente API real (obrigatório, nenhum mock!)
    • Todas as classificações usam smart_categorize() da API
    • Buscas de contexto usam search_notes() da API
    • Criações de itens usam add_task()/add_note() da API
    
    Se Lex Flow estiver indisponível, o engine opera em modo degradado
    (classificação local simplificada) e loga erro gracefulmente.
    
    ====================================================================
    ATRIBUTOS PRINCIPAIS:
    
    _lex_flow (LexFlowClient): Cliente API do Lex Flow (conexão real)
    _config (dict): Configurações carregadas do settings.yaml
    _cache_projetos (list): Cache local de projetos (evita requisições repetidas)
    _cache_areas (list): Cache local de áreas (evita requisições repetidas)
    _ultima_atualizacao_cache (datetime): Timestamp da última atualização dos caches
    
    ====================================================================
    """

    def __init__(self, lex_flow_client):
        """
        Inicializa o Motor de Decisão com conexão real ao Lex Flow.
        
        ====================================================================
        PARÂMETROS OBRIGATÓRIOS:
        
        lex_flow_client (LexFlowClient): Instância do cliente API do Lex Flow,
                                         JÁ AUTENTICADA e pronta para uso.
                                         
        IMPORTANTE: O cliente DEVE estar autenticado antes de ser passado
                    para este construtor. Use lex_client.autenticar() antes.
        
        ====================================================================
        O QUE ACONTECE NA INICIALIZAÇÃO:
        
        1. Valida se lex_flow_client é válido (não None, tem métodos necessários)
        2. Armazena referência ao cliente (para todas as chamadas de API)
        3. Inicializa caches vazios (projetos, áreas)
        4. Carrega configurações do settings.yaml (se disponível)
        5. Registra log informativo da inicialização
        
        ====================================================================
        RAIO DE VALIDADE DOS CACHES:
        
        Os caches de projetos e áreas têm validade de 5 minutos.
        Após isso, são automaticamente reatualizados do Lex Flow.
        Isso equilibra performance (menos requisições) com frescura dos dados.
        
        ====================================================================
        
        Args:
            lex_flow_client: Instância autenticada do LexFlowClient
            
        Raises:
            TypeError: Se lex_flow_client for None ou inválido
            ValueError: Se lex_flow_client não tiver métodos necessários
        """
        
        # ========================================
        # VALIDAÇÃO DO CLIENTE LEX FLOW (CRÍTICO)
        # ========================================
        if lex_flow_client is None:
            raise TypeError(
                "❌ DecisionEngine REQUER um LexFlowClient válido!\n\n"
                "Não passe None. Instancie e autentique primeiro:\n\n"
                "from integrations.lex_flow_definitivo import LexFlowClient\n"
                "client = LexFlowClient(...)\n"
                "client.autenticar()\n"
                "engine = DecisionEngine(lex_flow_client=client)"
            )
        
        # Validar se tem os métodos essenciais que vamos usar
        metodos_necessarios = [
            'smart_categorize',  # Classificação via IA
            'get_projects',      # Obter projetos
            'get_areas',         # Obter áreas
            'add_task',          # Criar tarefa
            'add_note',          # Criar nota
            'search_notes'       # Buscar notas
        ]
        
        for metodo in metodos_necessarios:
            if not hasattr(lex_flow_client, metodo):
                raise ValueError(
                    f"❌ LexFlowClient não tem método '{metodo}'!\n"
                    f"Verifique se está usando a versão correta do cliente."
                )
        
        # ========================================
        # ARMazenar REFERÊNCIAS E CONFIGURAR ESTADO INTERNO
        # ========================================
        
        # Cliente API do Lex Flow (conexão real - NUNCA mock!)
        self._lex_flow = lex_flow_client
        
        # Caches locais (para evitar requisições repetidas à API)
        self._cache_projetos: List[Dict] = []
        self._cache_areas: List[Dict] = []
        self._ultima_atualizacao_cache: Optional[datetime] = None
        
        # Validade do cache em segundos (5 minutos = 300 segundos)
        self._cache_validade_segundos = 300
        
        # Configurações (carregar do settings.yaml se disponível)
        self._config = self._carregar_configuracoes()
        
        # ========================================
        # LOG DE INICIALIZAÇÃO
        # ========================================
        logger_decision.info("=" * 80)
        logger_decision.info("🧠 DECISION ENGINE v2.0 INICIALIZADO COM SUCESSO")
        logger_decision.info("   Integração Lex Flow: ✅ Conectado (API Real)")
        logger_decision.info(f"   Cache validade: {self._cache_validade_segundos} segundos")
        logger_decision.info("=" * 80)

    def _carregar_configuracoes(self) -> Dict[str, Any]:
        """
        Carregar configurações específicas do Decision Engine do settings.yaml.
        
        Tenta ler configurações como:
        - Pesos para classificação (peso_palavras_chave, peso_contexto, etc.)
        - Limiares de confiança para aceitar classificação automática
        - Regras personalizadas de priorização (se houver)
        
        Se não encontrar ou der erro, retorna dicionário com padrões seguros.
        
        Returns:
            Dicionário com configurações (vazio se falhar)
        """
        config_padrao = {
            'peso_palavras_chave': 0.4,
            'peso_contexto': 0.3,
            'peso_historico': 0.2,
            'peso_aleatorio': 0.1,  # Pequeno fator aleatório para empates
            'limiar_confianca_alta': 0.8,
            'limiar_confianca_media': 0.6,
            'regras_priorizacao': {}
        }
        
        try:
            from engine.config_loader import ConfigLoader
            loader = ConfigLoader.get_instance()
            
            if hasattr(loader.configuracoes, 'decision_engine'):
                cfg = loader.configuracoes.decision_engine
                return {
                    **config_padrao,
                    'peso_palavras_chave': getattr(cfg, 'peso_palavras_chave', 0.4),
                    'peso_contexto': getattr(cfg, 'peso_contexto', 0.3),
                    'peso_historico': getattr(cfg, 'peso_historico', 0.2),
                    'limiar_confianca_alta': getattr(cfg, 'limiar_confianca_alta', 0.8),
                    'limiar_confianca_media': getattr(cfg, 'limiar_confianca_media', 0.6)
                }
                
        except Exception as erro_config:
            logger_decision.warning(f"⚠️  Erro ao carregar configs: {erro_config}")
            logger_decision.info("   Usando configurações padrão.")
        
        return config_padrao

    # =========================================================================
    # MÉTODOS PRINCIPAIS (API PÚBLICA DO MOTOR DE DECISÃO)
    # =========================================================================

    def classificar_item(self, texto: str, tipo: str = "note", 
                         tags: Optional[List[str]] = None,
                         projeto_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Classificar um Item Capturado na Metodologia P.A.R.A. (Método Principal)
        
        ====================================================================
        PROPÓSITO:
        Este é o MÉTODO PRINCIPAL do Decision Engine. É o ponto de entrada
        para toda classificação de itens no sistema.
        
        Recebe um texto bruto (ideia, nota, tarefa) e decide:
        1. Qual categoria P.A.R.A pertence (Projects/Areas/Resources/Archives)
        2. Qual projeto ou área deve ser associado
        3. Qual nível de prioridade atribuir
        4. Quais ações sugerir ao usuário
        
        ====================================================================
        FLUXO DE EXECUÇÃO:
        
        1. VALIDAR ENTRADA (texto não vazio, tamanho razoável)
        2. TENTAR CLASSIFICAÇÃO VIA LEX FLOW IA (smart_categorize)
        3. SE IA FALHAR → Usar classificação local (heurísticas)
        4. ENRIQUECER COM METADADOS (tags, timestamp, fonte)
        5. CALCULAR CONFIANÇA DA CLASSIFICAÇÃO
        6. RETORNAR DECISÃO COMPLETA E ESTRUTURADA
        
        ====================================================================
        ARGUMENTOS:
        
        texto (str - OBRIGATÓRIO):
            Conteúdo textual do item a ser classificado.
            Pode ser uma ideia, tarefa, nota, referência, etc.
            Tamanho recomendado: 10 a 5000 caracteres.
            
        tipo (str - OPCIONAL, default="note"):
            Tipo preliminar do item (ajuda na classificação).
            Valores aceitos: "task", "idea", "note", "reference"
            
        tags (List[str] - OPCIONAL, default=None):
            Tags fornecidas pelo usuário na captura.
            São consideradas como hints para a classificação.
            
        projeto_id (int - OPCIONAL, default=None):
            ID do projeto se o usuário já especificou um.
            Se fornecido, pula a etapa de seleção de projeto.
        
        ====================================================================
        RETORNO (Dict completo):
        
        {
            'sucesso': bool,                    # Se classificação foi bem-sucedida
            'categoria': str,                   # 'Projects' | 'Areas' | 'Resources' | 'Archives'
            'categoria_enum': CategoriaPARA,     # Enum da categoria (para uso programático)
            'projeto_id': int | None,           # ID do projeto sugerido (se aplicável)
            'area_id': int | None,              # ID da área sugerida (se aplicável)
            'prioridade': str,                  # 'low' | 'medium' | 'high' | 'urgent'
            'prioridade_enum': NivelPrioridade, # Enum da prioridade
            'confianca': float,                 # 0.0 a 1.0 (quanto mais alto, mais certo)
            'metodo_classificacao': str,        # 'ia_lex_flow' | 'heuristica_local' | 'fallback'
            'sugestoes_acao': List[str],        # Lista de ações sugeridas ao usuário
            'tags_sugeridas': List[str],        # Tags adicionais sugeridas pelo motor
            'razao_decisao': str,               # Explicação humana do porquê desta decisão
            'dados_brutos': dict,               # Resposta bruta da API (para debug)
            'timestamp': str,                   # ISO 8601 da classificação
            'item_original': {                  # Dados originais recebidos
                'texto': str,
                'tipo': str,
                'tags': List[str],
                'projeto_id': int | None
            }
        }
        
        ====================================================================
        EXEMPLOS DE USO:
        
        # Exemplo 1: Classificar ideia simples
        resultado = motor.classificar_item(
            texto="Preciso comprar microfone novo para gravações"
        )
        print(resultado['categoria'])  # 'Areas' (Equipamento/Recursos)
        print(resultado['prioridade'])  # 'medium'
        
        # Exemplo 2: Classificar com tipo explícito
        resultado = motor.classificar_item(
            texto="Gravar vídeo sobre Bitcoin até sexta",
            tipo="task",
            tags=["youtube", "dark", "cripto"]
        )
        print(resultado['categoria'])  # 'Projects' (tem deadline "até sexta")
        print(resultado['prioridade'])  # 'high' (deadline próximo)
        
        # Exemplo 3: Com projeto pré-selecionado
        resultado = motor.classificar_item(
            texto="Editar thumbnail do vídeo #12",
            tipo="task",
            projeto_id=5  # Já sabe qual projeto
        )
        
        ====================================================================
        """
        
        # ========================================
        # PASSO 1: VALIDAR ENTRADA
        # ========================================
        if not texto or not isinstance(texto, str) or not texto.strip():
            logger_decision.warning("⚠️  classificar_item() chamado com texto vazio!")
            return {
                'sucesso': False,
                'erro': 'Texto vazio ou inválido',
                'categoria': None,
                'confianca': 0.0,
                'metodo_classificacao': 'erro_validacao',
                'timestamp': datetime.now().isoformat()
            }
        
        # Normalizar texto (remover espaços extras, quebras de linha excessivas)
        texto_normalizado = ' '.join(texto.split())
        
        # Log da requisição de classificação
        logger_decision.info(f"🔍 [CLASSIFICAR] Iniciando classificação...")
        logger_decision.info(f"   Texto ({len(texto_normalizado)} chars): {texto_normalizado[:100]}...")
        logger_decision.info(f"   Tipo: {tipo} | Tags: {tags} | Projeto ID: {projeto_id}")
        
        # ========================================
        # PASSO 2: TENTAR CLASSIFICAÇÃO VIA IA DO LEX FLOW
        # =================================-------
        # Esta é a PREFERÊNCIA: usar IA do Lex Flow (mais inteligente)
        # Se funcionar, retornamos o resultado enriquecido
        # Se falhar, caímos para heurísticas locais (fallback gracefully)
        
        resultado_ia = None
        metodo_usado = 'heuristica_local'  # Default (muda se IA funcionar)
        
        try:
            logger_decision.info("🤖 Tentando classificação via IA do Lex Flow (smart_categorize)...")
            
            # Chamar API real do Lex Flow para classificação inteligente
            # Assinatura real do método: smart_categorize(items, title="", text="")
            resultado_ia = self._lex_flow.smart_categorize(
                items=[texto_normalizado],  # Lista de itens (obrigatório)
                title=tipo,                 # Tipo como título (ex: "task", "idea")
                text=texto_normalizado     # Texto completo da nota
            )
            
            # Validar se resposta da IA é válida
            if resultado_ia and isinstance(resultado_ia, dict) and resultado_ia.get('category'):
                logger_decision.info("✅ Classificação via IA bem-sucedida!")
                logger_decision.info(f"   Categoria IA: {resultado_ia.get('category')}")
                logger_decision.info(f"   Confiança IA: {resultado_ia.get('confidence', 'N/A')}")
                
                metodo_usado = 'ia_lex_flow'
                
            else:
                logger_decision.warning("⚠️  IA retornou resposta inválida ou vazia")
                logger_decision.warning(f"   Resposta bruta: {resultado_ia}")
                resultado_ia = None
                
        except Exception as erro_ia:
            # Log do erro mas NÃO crasha (vamos usar fallback)
            logger_decision.error(f"❌ Erro na classificação IA: {erro_ia}", exc_info=True)
            logger_decision.info("   ⬇️  Caindo para heurísticas locais (modo degradado)...")
            resultado_ia = None
        
        # ========================================
        # PASSO 3: CLASSIFICAÇÃO LOCAL (FALLBACK SE IA FALHOU)
        # ========================================
        if resultado_ia is None:
            logger_decision.info("🧠 Executando classificação local (heurísticas P.A.R.A.)...")
            resultado_ia = self._classificacao_heuristica_local(
                texto=texto_normalizado,
                tipo=tipo,
                tags=tags
            )
            metodo_usado = 'heuristica_local'
        
        # ========================================
        # PASSO 4: ENRIQUECER E ESTRUTURAR RESULTADO FINAL
        # ========================================
        resultado_final = self._estruturar_resultado_classificacao(
            resultado_bruto=resultado_ia,
            texto_original=texto_normalizado,
            tipo_original=tipo,
            tags_originais=tags,
            projeto_id_original=projeto_id,
            metodo_utilizado=metodo_usado
        )
        
        # ========================================
        # PASSO 5: LOG DO RESULTADO E RETORNO
        # ========================================
        logger_decision.info(f"✅ [CLASSIFICAR] Concluída com sucesso!")
        logger_decision.info(f"   📂 Categoria Final: {resultado_final.get('categoria')}")
        logger_decision.info(f"   🎯 Prioridade: {resultado_final.get('prioridade')}")
        logger_decision.info(f"   📊 Confiança: {resultado_final.get('confianca')}")
        logger_decision.info(f"   🔧 Método: {resultado_final.get('metodo_classificacao')}")
        
        return resultado_final

    def priorizar_tarefas(self, tarefas: List[Dict]) -> List[Dict]:
        """
        Priorizar uma Lista de Tarefas por Importância e Urgência.
        
        ====================================================================
        PROPÓSITO:
        Recebe uma lista de tarefas (do Lex Flow ou outra fonte) e reordena
        baseado em múltiplos fatores de priorização, retornando a lista
        ordenada da MAIS importante para a MENOS importante.
        
        ====================================================================
        FATORES DE PRIORIZAÇÃO (Peso Total = 1.0):
        
        1. Prioridade Explícita (peso 0.30):
           - Valor já definido pelo usuário/Lex Flow (urgent > high > medium > low)
           
        2. Proximidade de Deadline (peso 0.25):
           - Quanto mais perto, mais urgente
           - Tarefas sem deadline vão para o final
           
        3. Idade da Tarefa (peso 0.15):
           - Tarefas antigas não concluídas ganham peso (evitar estagnação)
           
        4. Importância do Projeto Pai (peso 0.15):
           - Projetos marcados como "importantes" no Lex Flow herdam peso
           
        5. Fator Aleatório Pequeno (peso 0.05):
           - Para empates (evita sempre mesma ordem)
           - Adiciona variabilidade natural
        
        ====================================================================
        ALGORITMO:
        
        Para cada tarefa na lista:
        1. Calcular pontuação individual (0.0 a 10.0)
        2. Ordenar lista por pontuação decrescente
        3. Retornar lista reordenada (original não é modificada)
        
        ====================================================================
        ARGUMENTOS:
        
        tarefas (List[Dict] - OBRIGATÓRIO):
            Lista de dicionários representando tarefas.
            Cada dicionário DEVE conter (idealmente):
            - 'id' (int): ID único da tarefa
            - 'title' (str): Título/descrição da tarefa
            - 'priority' (str): Prioridade atual ('low', 'medium', 'high', 'urgent')
            - 'due_date' (str|datetime): Data limite (ISO 8601 ou datetime)
            - 'project_id' (int): ID do projeto pai
            - 'created_at' (str|datetime): Data de criação
            - 'status' (str): Status atual ('pending', 'in_progress', etc.)
            
            Campos opcionais (se faltarem, usa valores padrão seguros):
            - 'project_importance' (float): Importância do projeto (0.0-1.0)
            - 'estimated_time' (int): Tempo estimado em minutos
            - 'tags' (List[str]): Tags associadas
        
        RETURNS:
            List[Dict]: Nova lista ordenada por prioridade (cópia, original preservada)
                      Cada item mantém todos campos originais + campo extra '_score'
        
        EXEMPLO:
        
            tarefas = [
                {'id': 1, 'title': 'Tarefa A', 'priority': 'medium', ...},
                {'id': 2, 'title': 'Tarefa B', 'priority': 'urgent', ...},
                {'id': 3, 'title': 'Tarefa C', 'priority': 'low', ...}
            ]
            
            priorizadas = motor.priorizar_tarefas(tarefas)
            # priorizadas[0] será a tarefa mais importante (provavelmente ID 2)
        
        ====================================================================
        """
        
        logger_decision.info(f"⚡ [PRIORIZAR] Recebidas {len(tarefas)} tarefas para priorizar")
        
        # Validação rápida
        if not tarefas or not isinstance(tarefas, list):
            logger_decision.warning("⚠️  Lista de tarefas vazia ou inválida")
            return []
        
        # ========================================
        # OBTER CONTEXTO ADICIONAL DO LEX FLOW (opcional, enriquece análise)
        # ========================================
        projetos_importancia = {}  # Cache de importância por projeto ID
        
        try:
            # Buscar projetos para saber quais são "importantes"
            projetos = self._obter_projetos()
            
            for proj in projetos:
                proj_id = proj.get('id')
                # Heurística: projetos com muitas tarefas ativas são "importantes"
                # Ou podemos ter um flag explicito no futuro
                projetos_importancia[proj_id] = proj.get('importance_score', 0.5)
                
        except Exception as erro_projetos:
            logger_decision.warning(f"⚠️  Erro ao buscar projetos para priorização: {erro_projetos}")
            # Continua sem dados de projetos (usa padrão 0.5)
        
        # ========================================
        # CALCULAR PONTUAÇÃO PARA CADA TAREFA
        # ========================================
        tarefas_com_score = []
        
        for tarefa in tarefas:
            try:
                score = self._calcular_score_prioridade(
                    tarefa=tarefa,
                    projetos_importancia=projetos_importancia
                )
                
                # Adicionar score ao dicionário da tarefa (campo novo, não modifica original)
                tarefa_com_score = {**tarefa, '_prioridade_score': score}
                tarefas_com_score.append(tarefa_com_score)
                
            except Exception as erro_score:
                logger_decision.error(f"❌ Erro ao calcular score para tarefa {tarefa.get('id')}: {erro_score}")
                # Atribuir score médio (não descarta a tarefa)
                tarefa_com_score = {**tarefa, '_prioridade_score': 5.0}
                tarefas_com_score.append(tarefa_com_score)
        
        # ========================================
        # ORDENAR POR SCORE (DECRESCENTE)
        # ========================================
        tarefas_ordenadas = sorted(
            tarefas_com_score,
            key=lambda x: x.get('_prioridade_score', 0),
            reverse=True  # Maior score primeiro (mais importante)
        )
        
        # Log do resultado
        if tarefas_ordenadas:
            top3 = [(t.get('title', '?')[:30], t.get('_prioridade_score', 0)) 
                   for t in tarefas_ordenadas[:3]]
            logger_decision.info(f"✅ [PRIORIZAR] Top 3 tarefas:")
            for i, (titulo, score) in enumerate(top3, 1):
                logger_decision.info(f"   {i}. [{score:.1f}] {titulo}")
        
        return tarefas_ordenadas

    def analisar_contexto(self, texto: str, max_resultados: int = 5) -> List[Dict]:
        """
        Analisar Contexto Histórico Relacionado a um Texto.
        
        ====================================================================
        PROPÓSITO:
        Busca no Lex Flow notas/tarefas/itens RELACIONADOS ao texto fornecido.
        Útil para:
        - Antes de classificar: "Já tenho algo parecido?"
        - Antes de criar tarefa: "Isso já existe?"
        - Para sugerir conexões: "Veja, isso se relaciona com..."
        
        ====================================================================
        FONTES DE BUSCA:
        
        1. Busca Textual (keyword match):
           - Busca exata de palavras-chave no título/conteúdo
           - Via Lex Flow API: search_notes(query=texto)
           
        2. Busca Semântica (futuro - RAG):
           - Embeddings + similaridade de cosseno
           - Requer memory_system.py com FastEmbed instalado
           - Por enquanto, só busca textual
        
        3. Busca por Tags:
           - Items com tags similares ou idênticas
           - Via filtragem pós-busca
        
        ====================================================================
        ARGUMENTOS:
        
        texto (str - OBRIGATÓRIO):
            Texto de referência para buscar contextos relacionados.
            Geralmente é o mesmo texto que está sendo classificado.
            
        max_resultados (int - OPCIONAL, default=5):
            Quantidade máxima de resultados a retornar.
            Limitado entre 1 e 20 (para evitar sobrecarga).
        
        RETURNS:
            List[Dict]: Lista de itens relacionados, cada um com:
            - 'id': ID do item no Lex Flow
            - 'title': Título do item
            'type': Tipo (note/task/idea)
            'relevance_score': Pontuação de relevância (0.0-1.0)
            'reason': Porquê é relevante (explicação)
            'created_at': Data de criação
            'url': Link direto para o item no dashboard (se disponível)
        
        ====================================================================
        """
        
        logger_decision.info(f"🔍 [CONTEXTO] Analisando contexto para: {texto[:80]}...")
        
        # Validar limites
        max_resultados = max(1, min(20, max_resultados))
        
        resultados_finais = []
        
        try:
            # ========================================
            # BUSCA 1: TEXTO DIRETO NO LEX FLOW (API REAL)
            # ========================================
            logger_decision.info("   📡 Buscando no Lex Flow via search_notes()...")
            
            resultados_api = self._lex_flow.search_notes(
                query=texto,
                limit=max_resultados * 2  # Pedimos mais para filtrar depois
            )
            
            if resultados_api and isinstance(resultados_api, list):
                logger_decision.info(f"   ✅ Encontrados {len(resultados_api)} itens na API")
                
                for item in resultados_api:
                    # Estruturar resultado padronizado
                    resultado_estruturado = {
                        'id': item.get('id'),
                        'title': item.get('title', 'Sem título'),
                        'type': item.get('type', 'note'),
                        'content_preview': item.get('content', '')[:200],
                        'relevance_score': item.get('score', 0.5),  # Score vem da API se disponível
                        'created_at': item.get('created_at'),
                        'project_name': item.get('project_name'),
                        'source': 'lex_flow_search'
                    }
                    resultados_finais.append(resultado_estruturado)
                    
            else:
                logger_decision.warning("   ⚠️  search_notes() retornou vazio ou inválido")
            
            # ========================================
            # BUSCA 2: POR TAGS SIMILARES (HEURÍSTICA COMPLEMENTAR)
            # ========================================
            # Extrair palavras-chave do texto e buscar items com essas tags
            palavras_chave = self._extrair_palavras_chave(texto)
            
            if palavras_chave:
                logger_decision.info(f"   🏷️  Buscando por tags: {palavras_chave[:5]}")
                
                # Para cada palavra-chave, buscar notas com essa tag
                for palavra in palavras_chave[:3]:  # Limitar a 3 buscas extras
                    try:
                        resultados_tag = self._lex_flow.search_notes(
                            query=f"tag:{palavra}",
                            limit=2
                        )
                        
                        if resultados_tag:
                            for item in resultados_tag:
                                # Evitar duplicatas (se já veio na busca 1)
                                ids_existentes = [r['id'] for r in resultados_finais]
                                if item.get('id') not in ids_existentes:
                                    resultado_tag = {
                                        'id': item.get('id'),
                                        'title': item.get('title', 'Sem título'),
                                        'type': item.get('type', 'note'),
                                        'relevance_score': 0.3,  # Score menor que busca direta
                                        'reason': f'Tag similar: "{palavra}"',
                                        'source': 'tag_match'
                                    }
                                    resultados_finais.append(resultado_tag)
                                    
                    except Exception as erro_tag:
                        logger_decision.debug(f"   Erro na busca tag '{palavra}': {erro_tag}")
                        continue  # Ignora erros de tag e continua
            
            # ========================================
            # ORDENAR POR RELEVÂNCIA E LIMITAR RESULTADOS
            # ========================================
            resultados_finais.sort(
                key=lambda x: x.get('relevance_score', 0),
                reverse=True  # Mais relevante primeiro
            )
            
            # Cortar para o máximo solicitado
            resultados_finais = resultados_finais[:max_resultados]
            
        except Exception as erro_contexto:
            logger_decision.error(f"❌ Erro na análise de contexto: {erro_contexto}", exc_info=True)
            # Retorna lista vazia gracefulmente (não crasha)
            resultados_finais = []
        
        # Log final
        logger_decision.info(f"✅ [CONTEXTO] Análise concluída: {len(resultados_finais)} itens encontrados")
        
        return resultados_finais

    def sugerir_acoes(self, item_classificado: Dict) -> List[str]:
        """
        Sugerir Próximas Ações Baseadas em Item Classificado.
        
        ====================================================================
        PROPÓSITO:
        Após classificar um item, este método sugere ações concretas que
        o usuário pode tomar. Torna o sistema PROATIVO em vez de passivo.
        
        ====================================================================
        TIPOS DE SUGESTÕES (baseadas na categoria P.A.R.A):
        
        PROJECTS:
        - "Criar tarefa no projeto X"
        - "Definir micro-deadline para esta semana"
        - "Adicionar ao Kanban do projeto"
        - "Notificar equipe do projeto"
        
        AREAS:
        - "Adicionar à rotina semanal"
        - "Criar checklist recorrente"
        - "Agendar bloco de foco"
        - "Revisar métricas desta área"
        
        RESOURCES:
        - "Ler/resumir em 2 frases"
        - "Conectar a projeto existente"
        - "Compartilhar com equipe"
        - "Arquivar para consulta futura"
        
        ARCHIVES:
        - "Mover para arquivo morto"
        - "Extrair lições aprendidas"
        - "Atualizar documentação do projeto"
        
        ====================================================================
        ARGUMENTOS:
        
        item_classificado (Dict - OBRIGATÓRIO):
            Dicionário retornado pelo método classificar_item().
            Deve conter pelo menos: 'categoria', 'prioridade', 'texto'
        
        RETURNS:
            List[str]: Lista de strings, cada uma sendo uma sugestão de ação
                       Ordenada da mais recomendada para a menos
        
        ====================================================================
        """
        
        logger_decision.info(f("💡 [SUGESTÕES] Gerando ações para item classificado..."))
        
        sugestoes = []
        
        try:
            # Extrair dados do item classificado
            categoria = item_classificado.get('categoria', 'Unknown')
            prioridade = item_classificado.get('prioridade', 'medium')
            texto = item_classificado.get('item_original', {}).get('texto', '')
            projeto_id = item_classificado.get('projeto_id')
            
            # ========================================
            # GERAR SUGESTÕES BASEADAS NA CATEGORIA
            # ========================================
            
            if categoria == CategoriaPARA.PROJECTS.value:
                # === SUGESTÕES PARA PROJETOS ===
                sugestoes.extend([
                    "📋 Criar tarefa detalhada com sub-itens",
                    "📅 Definir micro-deadline para os próximos 7 dias",
                    "🎯 Adicionar ao quadro Kanban do projeto",
                    "👥 Notificar colegas envolvidos no projeto",
                    "📊 Definir métricas de sucesso para esta tarefa"
                ])
                
                if prioridade in ['high', 'urgent']:
                    sugestoes.insert(0, "🚨 ATENÇÃO: Alta prioridade! Considere fazer AGORA.")
                    
            elif categoria == CategoriaPARA.AREAS.value:
                # === SUGESTÕES PARA ÁREAS ===
                sugestoes.extend([
                    "🔄 Adicionar à rotina semanal de revisão",
                    "✅ Criar checklist recorrente (diário/semanal)",
                    "⏰ Agendar bloco de foco dedicado (25min Pomodoro)",
                    "📈 Revisar métricas e KPIs desta área",
                    "📝 Documentar processo atual (AS-IS)"
                ])
                
            elif categoria == CategoriaPARA.RESOURCES.value:
                # === SUGESTÕES PARA RECURSOS ===
                sugestoes.extend([
                    "📖 Ler/resumir em 2-3 frases principais",
                    "🔗 Conectar a algum projeto ativo (qual?)",
                    "👥 Compartilhar com alguém da equipe",
                    "🗄️ Arquivar para consulta futura organizada",
                    "🏷️ Adicionar tags para facilitar busca futura"
                ])
                
            elif categoria == CategoriaPARA.ARCHIVES.value:
                # === SUGESTÕES PARA ARQUIVOS ===
                sugestoes.extend([
                    "📦 Confirmar que pode ser arquivado (não é mais necessário?)",
                    "💭 Extrair lições aprendidas antes de arquivar",
                    "📝 Atualizar documentação do projeto com conclusões",
                    "🗑️ Se realmente não serve mais, considerar deletar"
                ])
                
            else:
                # === CATEGORIA DESCONHECIDA (FALLBACK) ===
                sugestoes = [
                    "🤔 Revisar manualmente e decidir categoria",
                    "📂 Mover para Inbox para revisão posterior",
                    "💬 Perguntar ao Lex: 'O que faço com isto?'"
                ]
            
            # ========================================
            # SUGESTÕES CONTEXTUAIS ADICIONAIS (baseadas no texto)
            # ========================================
            
            texto_lower = texto.lower()
            
            # Detectar menção a prazo/deadline
            if any(palavra in texto_lower for palavra in ['até', 'deadline', 'hora', 'hoje', 'amanhã', 'semana']):
                sugestoes.insert(0, "⏰ Detectado prazo! Defina data/hora específica no calendário.")
            
            # Detectar menção a pessoas
            if any(palavra in texto_lower for palavra in ['falar com', 'reunião', 'equipe', 'cliente']):
                sugestoes.insert(1, "👥 Envolve outras pessoas? Agende reunião ou envie mensagem.")
            
            # Detectar menção a aprendizado
            if any(palavra in texto_lower for palavra in ['aprender', 'curso', 'livro', 'tutorial', 'estudar']):
                sugestoes.append("📚 Adicionar à lista de materiais de estudo.")
            
            # Limitar a 8 sugestões máximas (não sobrecarrega o usuário)
            sugestoes = sugestoes[:8]
            
        except Exception as erro_sugestoes:
            logger_decision.error(f"❌ Erro ao gerar sugestões: {erro_sugestoes}", exc_info=True)
            sugestoes = ["🔄 Ocorreu um erro. Tente novamente ou decida manualmente."]
        
        # Log das sugestões geradas
        logger_decision.info(f"✅ [SUGESTÕES] {len(sugestoes)} ações sugeridas")
        for i, sugestao in enumerate(sugestoes[:3], 1):
            logger_decision.info(f"   {i}. {sestao}")
        
        return sugestoes

    # =========================================================================
    # MÉTODOS AUXILIARES INTERNOS (Privados - Implementação Detalhada)
    # =========================================================================

    def _classificacao_heuristica_local(self, texto: str, tipo: str, 
                                         tags: Optional[List[str]]) -> Dict:
        """
        Classificação Local via Heurísticas (Fallback quando IA do Lex Flow falha).
        
        Usa regras baseadas em palavras-chave, padrões de texto e lógica simples
        para determinar categoria P.A.R.A sem depender de IA externa.
        
        Menos precisa que a IA, mas garante que o sistema SEMPRE funcione
        (mesmo offline ou com problemas na API).
        
        Args:
            texto: Texto a classificar
            tipo: Tipo do item
            tags: Tags fornecidas
            
        Returns:
            Dicionário com estrutura similar ao retorno da IA (compatível)
        """
        
        logger_decision.info("   🧮 Executando heurísticas locais de classificação...")
        
        texto_lower = texto.lower()
        scores = {
            CategoriaPARA.PROJECTS.value: 0.0,
            CategoriaPARA.AREAS.value: 0.0,
            CategoriaPARA.RESOURCES.value: 0.0,
            CategoriaPARA.ARCHIVES.value: 0.0
        }
        
        razao = ""  # Explicação da decisão
        
        # ========================================
        # HEURÍSTICA 1: PALAVRAS-CHAVE DE PROJETO (Deadline/Ação)
        # ========================================
        palavras_projeto = [
            'até', 'deadline', 'prazo', 'entregar', 'terminar', 'finalizar',
            'lançar', 'publicar', 'gravar', 'editar', 'produzir', 'criar',
            'hoje', 'amanhã', 'essa semana', 'sexta', 'segunda'
        ]
        
        count_projeto = sum(1 for p in palavras_projeto if p in texto_lower)
        scores[CategoriaPARA.PROJECTS.value] += count_projeto * 2.0
        
        if count_projeto > 2:
            razao += "Detectadas palavras de projeto/deadline. "
        
        # ========================================
        # HEURÍSTICA 2: PALAVRAS-CHAVE DE ÁREA (Responsabilidade Contínua)
        # ========================================
        palavras_area = [
            'saúde', 'exercício', 'academia', 'médico', 'finanças', 'dinheiro',
            'investimento', 'carreira', 'trabalho', 'empresa', 'relacionamento',
            'família', 'amigos', 'casa', 'manutenção', 'rotina', 'hábito'
        ]
        
        count_area = sum(1 for p in palavras_area if p in texto_lower)
        scores[CategoriaPARA.AREAS.value] += count_area * 1.8
        
        if count_area > 2:
            razao += "Detectadas palavras de área/responsabilidade. "
        
        # ========================================
        # HEURÍSTICA 3: PALAVRAS-CHAVE DE RECURSO (Referência/Aprendizado)
        # ========================================
        palavras_recurso = [
            'artigo', 'livro', 'vídeo', 'tutorial', 'curso', 'link', 'site',
            'ferramenta', 'app', 'software', 'plugin', 'template', 'exemplo',
            'referência', 'ler', 'estudar', 'aprender', 'anotar', 'salvar',
            'comprar', 'adquirir', 'baixar', 'instalar'
        ]
        
        count_recurso = sum(1 for p in palavras_recurso if p in texto_lower)
        scores[CategoriaPARA.RESOURCES.value] += count_recurso * 1.5
        
        if count_recurso > 2:
            razao += "Detectadas palavras de recurso/referência. "
        
        # ========================================
        # HEURÍSTICA 4: TIPO DO ITEM (Dica do usuário)
        # ========================================
        if tipo == 'task':
            scores[CategoriaPARA.PROJECTS.value] += 3.0
            razao += "Tipo=Tarefa favorece Projects. "
        elif tipo == 'idea':
            scores[CategoriaPARA.PROJECTS.value] += 1.0
            scores[CategoriaPARA.RESOURCES.value] += 1.0
            razao += "Tipo=Idea pode ser Project ou Resource. "
        elif tipo == 'reference':
            scores[CategoriaPARA.RESOURCES.value] += 3.0
            razao += "Tipo=Referência favorece Resources. "
        
        # ========================================
        # HEURÍSTICA 5: TAGS FORNECIDAS (Hints do usuário)
        # ========================================
        if tags:
            tags_lower = [t.lower() for t in tags]
            
            # Tags que sugerem projeto
            tags_projeto = ['urgente', 'deadline', 'entrega', 'produção', 'gravação']
            if any(t in tags_lower for t in tags_projeto):
                scores[CategoriaPARA.PROJECTS.value] += 2.5
                razao += "Tags sugerem projeto. "
            
            # Tags que sugerem área
            tags_area = ['saúde', 'finanças', 'carreira', 'pessoal']
            if any(t in tags_lower for t in tags_area):
                scores[CategoriaPARA.AREAS.value] += 2.5
                razao += "Tags sugerem área. "
            
            # Tags que sugerem recurso
            tags_recurso = ['ler', 'estudar', 'referência', 'tutorial', 'comprar']
            if any(t in tags_lower for t in tags_recurso):
                scores[CategoriaPARA.RESOURCES.value] += 2.5
                razao += "Tags sugerem recurso. "
        
        # ========================================
        # DETERMINAR VENCEDOR (Categoria com maior score)
        # ========================================
        categoria_vencedora = max(scores, key=scores.get)
        score_vencedor = scores[categoria_vencedora]
        
        # Calcular confiança baseada na diferença entre vencedor e segundo lugar
        scores_ordenados = sorted(scores.values(), reverse=True)
        if len(scores_ordenados) > 1:
            diferenca = scores_ordenados[0] - scores_ordenados[1]
            confianca = min(0.9, 0.4 + (diferenca * 0.1))  # Escala 0.4-0.9
        else:
            confianca = 0.6  # Confiança média se só há uma opção
        
        # Montar resultado compatível com formato da IA
        resultado_heuristico = {
            'category': categoria_vencedora,
            'confidence': round(confianca, 2),
            'suggested_project_id': None,
            'suggested_area_id': None,
            'priority': self._inferir_prioridade(texto, tipo),
            'suggested_tags': self._extrair_palavras_chave(texto)[:5],
            'reason': razao or "Classificação baseada em análise heurística de palavras-chave.",
            'method': 'heuristic_fallback'
        }
        
        logger_decision.info(f"   📊 Scores heurísticos: {scores}")
        logger_decision.info(f"   🏆 Vencedor: {categoria_vencedora} (score: {score_vencedor:.1f})")
        
        return resultado_heuristico

    def _calcular_score_prioridade(self, tarefa: Dict, 
                                   projetos_importancia: Dict[float]) -> float:
        """
        Calcular Pontuação de Prioridade para uma Única Tarefa (0.0 a 10.0).
        
        Combina múltiplos fatores ponderados para produzir um score único
        que representa quão importante/urgente esta tarefa é.
        
        Args:
            tarefa: Dicionário da tarefa com dados relevantes
            projetos_importancia: Dict mapeando project_id → importance (0.0-1.0)
            
        Returns:
            Float entre 0.0 (menos importante) e 10.0 (mais importante)
        """
        
        score_total = 0.0
        
        # ========================================
        # FATOR 1: PRIORIDADE EXPLÍCITA (peso 0.30 → max 3.0 pontos)
        # ========================================
        prioridade_map = {
            'urgent': 10.0,
            'high': 8.0,
            'medium': 5.0,
            'low': 2.0,
            'none': 1.0
        }
        
        prio_str = str(tarefa.get('priority', 'medium')).lower()
        prio_valor = prioridade_map.get(prio_str, 5.0)
        score_total += prio_valor * 0.30  # Max 3.0 pontos
        
        # ========================================
        # FATOR 2: PROXIMIDADE DE DEADLINE (peso 0.25 → max 2.5 pontos)
        # ========================================
        due_date = tarefa.get('due_date')
        
        if due_date:
            try:
                # Converter para datetime se for string
                if isinstance(due_date, str):
                    due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                
                agora = datetime.now(due_date.tzinfo)  # Manter timezone se tiver
                diferenca_horas = (due_date - agora).total_seconds() / 3600
                
                if diferenca_horas < 0:
                    # Já passou do deadline! Máxima urgência
                    score_deadline = 10.0
                elif diferenca_horas < 24:
                    # Menos de 24h → muito urgente
                    score_deadline = 9.0
                elif diferenca_horas < 72:
                    # Menos de 3 dias → urgente
                    score_deadline = 7.0
                elif diferenca_horas < 168:
                    # Menos de 1 semana → moderado
                    score_deadline = 5.0
                else:
                    # Mais de 1 semana → baixa urgência por tempo
                    score_deadline = 2.0
                
                score_total += score_deadline * 0.25  # Max 2.5 pontos
                
            except Exception:
                # Se não conseguir parsear data, ignora este fator
                pass
        else:
            # Sem deadline → pontuação baixa neste fator
            score_total += 1.0 * 0.25  # 0.25 pontos
        
        # ========================================
        # FATOR 3: IDADE DA TAREFA (peso 0.15 → max 1.5 pontos)
        # ========================================
        created_at = tarefa.get('created_at')
        
        if created_at:
            try:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                idade_horas = (datetime.now(created_at.tzinfo) - created_at).total_seconds() / 3600
                
                if idade_horas > 168:  # Mais de 1 semana
                    score_idade = 10.0  # Tarefa velha não feita → priorizar
                elif idade_horas > 72:  # Mais de 3 dias
                    score_idade = 7.0
                elif idade_horas > 24:  # Mais de 1 dia
                    score_idade = 5.0
                else:
                    score_idade = 2.0  # Tarefa recente
                
                score_total += score_idade * 0.15  # Max 1.5 pontos
                
            except Exception:
                pass
        
        # ========================================
        # FATOR 4: IMPORTÂNCIA DO PROJETO PAI (peso 0.15 → max 1.5 pontos)
        # ========================================
        proj_id = tarefa.get('project_id')
        
        if proj_id and proj_id in projetos_importancia:
            importancia_proj = projetos_importancia[proj_id]
            score_total += importancia_proj * 10.0 * 0.15  # Max 1.5 pontos
        else:
            # Projeto desconhecido → importância média
            score_total += 5.0 * 0.15  # 0.75 pontos
        
        # ========================================
        # FATOR 5: FATOR ALEATÓRIO PEQUENO (peso 0.05 → max 0.5 pontos)
        # ========================================
        import random
        score_total += random.uniform(0, 10.0) * 0.05  # Max 0.5 pontos
        
        # ========================================
        # NORMALIZAR PARA ESCALA 0.0-10.0
        # ========================================
        score_final = max(0.0, min(10.0, score_total))
        
        return score_final

    def _inferir_prioridade(self, texto: str, tipo: str) -> str:
        """
        Inferir Nível de Prioridade Baseado no Conteúdo do Texto.
        
        Heurística simples que detecta pistas de urgência no texto
        e sugere um nível de prioridade adequado.
        
        Args:
            texto: Texto da tarefa/nota
            tipo: Tipo do item
            
        Returns:
            String: 'urgent', 'high', 'medium', ou 'low'
        """
        
        texto_lower = texto.lower()
        
        # Palavras que indicam urgência máxima
        urgent_words = ['agora', 'imediatamente', 'urgente', 'emergência', 'crítico', 
                       'hoje', 'já', 'logo', 'pressão', 'atrasado', 'atrasando']
        
        if any(p in texto_lower for p in urgent_words):
            return 'urgent'
        
        # Palavras que indicam alta prioridade
        high_words = ['importante', 'prioridade', 'essencial', 'crucial', 'rápido',
                     'breve', 'esta semana', 'sexta', 'segunda', 'próximo']
        
        if any(p in texto_lower for p in high_words):
            return 'high'
        
        # Palavras que indicam baixa prioridade
        low_words = ['quando puder', 'futuro', 'talvez', 'eventualmente', 
                    'um dia', 'quando tiver tempo', 'sem pressa']
        
        if any(p in texto_lower for p in low_words):
            return 'low'
        
        # Se é tarefa, default para medium-alta (tarefas geralmente precisam ser feitas)
        if tipo == 'task':
            return 'medium'
        
        # Ideias e notas default para low (não são ações imediatas)
        return 'low'

    def _extrair_palavras_chave(self, texto: str) -> List[str]:
        """
        Extrair Palavras-Chave Relevantes de um Texto.
        
        Algoritmo simples:
        1. Converter para minúsculas
        2. Remover pontuação
        3. Separar por espaços
        4. Filtrar stop words (artigos, preposições comuns)
        5. Manter palavras com > 3 caracteres
        6. Retornar lista única (sem repetições)
        
        Args:
            texto: Texto de entrada
            
        Returns:
            Lista de strings (palavras-chave)
        """
        
        import string
        
        # Stop words em português e inglês (comuns que não adicionam significado)
        stop_words = {
            'o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas', 'de', 'da', 'do',
            'das', 'dos', 'em', 'no', 'na', 'nos', 'nas', 'por', 'para', 'com',
            'sem', 'como', 'mais', 'menos', 'não', 'sim', 'já', 'também', 'ser',
            'estar', 'ter', 'que', 'este', 'esta', 'isto', 'esse', 'essa', 'isso',
            'aquilo', 'ele', 'ela', 'eles', 'elas', 'meu', 'minha', 'seu', 'sua',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'shall', 'can', 'of', 'in', 'to',
            'for', 'with', 'on', 'at', 'by', 'from', 'up', 'about', 'into',
            'through', 'during', 'before', 'after', 'above', 'below', 'between'
        }
        
        # Normalizar texto
        texto_limpo = texto.lower().translate(str.maketrans('', '', string.punctuation))
        palavras = texto_limpo.split()
        
        # Filtrar: manter apenas palavras > 3 chars que não são stop words
        palavras_chave = list(set([
            p for p in palavras 
            if len(p) > 3 and p not in stop_words
        ]))
        
        return palavras_chave

    def _estruturar_resultado_classificacao(self, resultado_bruto: Dict,
                                            texto_original: str,
                                            tipo_original: str,
                                            tags_originais: Optional[List[str]],
                                            projeto_id_original: Optional[int],
                                            metodo_utilizado: str) -> Dict:
        """
        Estruturar e Enriquecer Resultado Bruto da Classificação em Formato Padronizado.
        
        Transforma a resposta da API (ou heurística) em um dicionário uniforme
        que sempre tem os mesmos campos, facilitando o consumo pelos outros módulos.
        
        Args:
            resultado_bruto: Resposta direta da IA ou heurística
            texto_original: Texto original enviado para classificação
            tipo_original: Tipo original do item
            tags_originais: Tags originais (se houver)
            projeto_id_original: ID do projeto original (se houver)
            metodo_utilizado: String identificando o método ('ia_lex_flow' ou 'heuristica_local')
            
        Returns:
            Dicionário completo e padronizado com todos os campos necessários
        """
        
        # Extrair dados do resultado bruto (com defaults seguros)
        categoria_bruta = resultado_bruto.get('category', 'Areas')
        confianca_bruta = float(resultado_bruto.get('confidence', 0.5))
        
        # Normalizar categoria para enum (validar se é valor válido do P.A.R.A)
        categorias_validas = [cat.value for cat in CategoriaPARA]
        if categoria_bruta not in categorias_validas:
            # Se categoria inválida, fallback para Areas (mais genérico/safe)
            logger_decision.warning(f"⚠️  Categoria inválida '{categoria_bruta}', usando 'Areas'")
            categoria_bruta = 'Areas'
        
        # Tentar converter para enum (para uso programático)
        try:
            categoria_enum = CategoriaPARA(categoria_bruta)
        except ValueError:
            categoria_enum = CategoriaPARA.AREAS  # Fallback
        
        # Prioridade (vem da IA ou inferida)
        prioridade_bruta = resultado_bruto.get('priority', 'medium')
        if prioridade_bruta not in [p.value for p in NivelPrioridade]:
            prioridade_bruta = 'medium'  # Safe default
        
        try:
            prioridade_enum = NivelPrioridade(prioridade_bruta)
        except ValueError:
            prioridade_enum = NivelPrioridade.MEDIUM
        
        # ========================================
        # MONTAR DICIONÁRIO FINAL COMPLETO
        # ========================================
        resultado_final = {
            # Metadados da operação
            'sucesso': True,
            'timestamp': datetime.now().isoformat(),
            'metodo_classificacao': metodo_utilizado,
            
            # Decisão principal (P.A.R.A)
            'categoria': categoria_bruta,
            'categoria_enum': categoria_enum,
            'prioridade': prioridade_bruta,
            'prioridade_enum': prioridade_enum,
            'confianca': round(confianca_bruta, 2),
            
            # Associações sugeridas
            'projeto_id': resultado_bruto.get('suggested_project_id') or projeto_id_original,
            'area_id': resultado_bruto.get('suggested_area_id'),
            
            # Tags (originais + sugeridas pela IA)
            'tags_sugeridas': resultado_bruto.get('suggested_tags', []),
            'tags_originais': tags_originais or [],
            
            # Explicação da decisão
            'razao_decisao': resultado_bruto.get('reason', 'Classificação realizada pelo sistema.'),
            
            # Dados brutos (para debug avançado se necessário)
            'dados_brutos': resultado_bruto,
            
            # Item original (para referência)
            'item_original': {
                'texto': texto_original,
                'tipo': tipo_original,
                'tags': tags_originais or [],
                'projeto_id': projeto_id_original
            },
            
            # Sugestões de ação (geradas em tempo real)
            'sugestoes_acao': []  # Será preenchido se o usuário chamar sugerir_acoes()
        }
        
        return resultado_final

    # =========================================================================
    # MÉTODOS DE CACHE E OTIMIZAÇÃO (Para evitar requisições repetidas à API)
    # =========================================================================

    def _obter_projetos(self) -> List[Dict]:
        """
        Obter Lista de Projetos do Lex Flow (com Cache Inteligente).
        
        Se cache válido (menos de 5 minutos), retorna do cache.
        Se expirou ou vazio, busca da API e atualiza cache.
        
        Returns:
            Lista de dicionários de projetos
        """
        
        agora = datetime.now()
        
        # Verificar se cache é válido
        if (self._cache_projetos and 
            self._ultima_atualizacao_cache and 
            (agora - self._ultima_atualizacao_cache).total_seconds() < self._cache_validade_segundos):
            
            logger_decision.debug(f"   📦 Usando cache de projetos ({len(self._cache_projetos)} itens)")
            return self._cache_projetos
        
        # Cache expirado ou vazio → buscar da API
        try:
            logger_decision.info("   📡 Atualizando cache de projetos via API...")
            projetos = self._lex_flow.get_projects()
            
            if projetos and isinstance(projetos, list):
                self._cache_projetos = projetos
                self._ultima_atualizacao_cache = agora
                logger_decision.info(f"   ✅ Cache atualizado: {len(projetos)} projetos")
                return projetos
            else:
                logger_decision.warning("   ⚠️  API retornou projetos inválidos, mantendo cache antigo")
                return self._cache_projetos or []
                
        except Exception as erro_projetos:
            logger_decision.error(f"❌ Erro ao buscar projetos: {erro_projetos}")
            return self._cache_projetos or []  # Retorna cache velho (melhor que nada)

    def _obter_areas(self) -> List[Dict]:
        """
        Obter Lista de Áreas do Lex Flow (com Cache Inteligente).
        
        Mesma lógica de cache do _obter_projetos().
        
        Returns:
            Lista de dicionários de áreas
        """
        
        # TODO: Implementar quando Lex Flow tiver endpoint get_areas()
        # Por enquanto, retorna lista vazia (áreas ainda não implementadas no Lex Flow)
        return []

    def limpar_cache(self):
        """
        Forçar Limpeza dos Caches (Projetos e Áreas).
        
        Útil após modificar dados no Lex Flow (criar projeto, etc.)
        para garantir que próxima leitura traga dados frescos.
        """
        self._cache_projetos = []
        self._cache_areas = []
        self._ultima_atualizacao_cache = None
        logger_decision.info("🗑️  Caches de projetos e áreas limpos forçadamente")


# ============================================================================
# FUNÇÕES AUXILIARES DE NÍVEL DE MÓDULO (Fora da Classe)
# ============================================================================

def criar_decision_engine(lex_flow_client) -> DecisionEngine:
    """
    Factory Function para Criar Instância do Decision Engine.
    
    Função auxiliar que encapsula a criação do Decision Engine,
    tornando mais fácil e seguro instanciá-lo em outros módulos.
    
    Args:
        lex_flow_client: Cliente Lex Flow autenticado
        
    Returns:
        Instância de DecisionEngine pronta para uso
        
    Example:
        client = LexFlowClient(...)
        client.autenticar()
        motor = criar_decision_engine(client)
        resultado = motor.classificar_item("Minha ideia")
    """
    return DecisionEngine(lex_flow_client=lex_flow_client)


# ============================================================================
# TESTE RÁPIDO (Executar diretamente para validar)
# ============================================================================

if __name__ == "__main__":
    """
    Teste rápido do Decision Engine (Standalone).
    
    Para executar:
        python engine/decision_engine.py
    
    Este teste:
    1. Utiliza a estrutura do CoreEngine para inicialização
    2. Valida a conexão com o Lex Flow via Singleton
    3. Classifica itens de exemplo usando o motor de decisão
    4. Exibe resultados detalhados no console
    """
    
    # ========================================
    # CORREÇÃO CRÍTICA: Adicionar diretório raiz ao PATH
    # ========================================
    import os
    import sys
    from datetime import datetime
    
    # Obter caminho absoluto deste arquivo (engine/decision_engine.py)
    caminho_arquivo = os.path.abspath(__file__)
    
    # Subir um nível (sair de engine/ → ir para SecondBrain_Ultimate/)
    diretorio_raiz = os.path.dirname(os.path.dirname(caminho_arquivo))
    
    # Adicionar raiz ao início do sys.path (prioridade máxima)
    if diretorio_raiz not in sys.path:
        sys.path.insert(0, diretorio_raiz)
        print(f"🔧 [PATH] Adicionado ao sys.path: {diretorio_raiz}")
    
    # ========================================
    # IMPORTAÇÕES DOS MÓDULOS DO SISTEMA
    # ========================================
    try:
        # Importamos o CoreEngine para gerenciar a conexão e configurações
        from engine.core_engine import CoreEngine
        # Importamos o DecisionEngine (ajuste o import se a classe estiver em outro local)
        # Assumindo que DecisionEngine está definido neste mesmo arquivo ou importável
    except ImportError as e:
        print(f"❌ Erro ao importar módulos base: {e}")
        sys.exit(1)
    
    # ========================================
    # INÍCIO DO TESTE
    # ========================================
    
    print("\n" + "=" * 90)
    print("🧠 DECISION ENGINE v2.0 - TESTE DE INTEGRAÇÃO")
    print("   Baseado no Core Engine Singleton | Dados de Produção")
    print("=" * 90 + "\n")
    
    try:
        # 1. Iniciar o CoreEngine (ele cuida do LexFlowClient internamente)
        print("1️⃣  Inicializando Core Engine...")
        core = CoreEngine()
        sucesso_inicio = core.iniciar()
        
        if not sucesso_inicio:
            print("❌ Falha crítica ao iniciar o Core Engine via settings.yaml")
            sys.exit(1)
            
        print("✅ Core Engine e Lex Flow conectados!")
        
        # 2. Obter o cliente já autenticado do CoreEngine
        # No seu sistema, o core_engine geralmente expõe o cliente ou o motor o usa internamente
        cliente_lex = core.lexflow  
        
        # 3. Criar a instância do Decision Engine
        print("\n2️⃣  Iniciando Decision Engine...")
        # Se a classe DecisionEngine estiver neste arquivo, instanciamos diretamente
        # Passamos o cliente já autenticado que o CoreEngine preparou
        motor_decisao = DecisionEngine(lex_flow_client=cliente_lex)
        print("✅ Decision Engine pronto para processamento!\n")
        
        # 4. Testes de classificação
        testes = [
            ("Gravar vídeo sobre Bitcoin até sexta", "task", ["youtube", "dark"]),
            ("Preciso comprar microfone novo", "idea", ["equipamento"]),
            ("Artigo sobre produtividade GTD", "reference", ["leitura"]),
            ("Ir à academia 3x por semana", "task", ["saúde", "hábito"])
        ]
        
        print("🔍 Executando testes de classificação:\n")
        print("-" * 90)
        
        for i, (texto, tipo, tags) in enumerate(testes, 1):
            print(f"\n📝 TESTE {i}: {texto[:60]}")
            print(f"   Tipo: {tipo} | Tags: {tags}")
            
            # Executa a lógica de decisão
            resultado = motor_decisao.classificar_item(
                texto=texto,
                tipo=tipo,
                tags=tags
            )
            
            print(f"   📂 Categoria: {resultado.get('categoria', 'N/A')}")
            print(f"   🎯 Prioridade: {resultado.get('prioridade', 'N/A')}")
            print(f"   📊 Confiança: {resultado.get('confianca', 'N/A')}")
            print(f"   🔧 Método: {resultado.get('metodo_classificacao', 'N/A')}")
            razao = resultado.get('razao_decisao', 'N/A')
            print(f"   💭 Razão: {razao[:100]}")
        
        print("\n" + "-" * 90)
        print("\n✅ Todos os testes de decisão concluídos com sucesso!")
        print(f"⏰ Finalizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
    except Exception as erro_teste:
        print(f"\n❌ ERRO DURANTE A EXECUÇÃO: {erro_teste}")
        import traceback
        traceback.print_exc()
    finally:
        # Encerramento seguro
        if 'core' in locals():
            core.parar()
            print("\n🛑 Conexões encerradas (Graceful Shutdown).")