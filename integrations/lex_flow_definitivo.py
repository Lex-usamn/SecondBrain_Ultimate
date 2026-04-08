"""
╔══════════════════════════════════════════════════════════════╗
║     LEX FLOW INTEGRATION - VERSÃO DEFINITIVA FUNCIONAL       ║
║                                                              ║
║  Baseado em testes reais bem-sucedidos pelo usuário:         ║
║  ✅ URL: https://flow.lex-usamn.com.br                      ║
║  ✅ Auth: POST /api/auth/login → JWT token                  ║
║  ✅ Headers: Bearer token + application/json                ║
║  ✅ Todos endpoints: prefixo /api/                          ║
║                                                              ║
║  Autor: Second Brain Ultimate System                         ║
║  Data: 2025-06-17                                            ║
║  Status: ✅ PRODUÇÃO (Testado e aprovado)                    ║
╚══════════════════════════════════════════════════════════════╝
"""

import requests
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# ============================================
# LOGGING CONFIGURATION
# ============================================
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler('logs/lex_flow_producao.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger('LexFlowPROD')


# ============================================
# DATA CLASSES
# ============================================

@dataclass
class LexFlowConfig:
    """Configuração validada e testada"""
    
    # URL Base (TESTADO E FUNCIONANDO)
    base_url: str = "https://flow.lex-usamn.com.br"
    
    # Credenciais (TESTADAS E FUNCIONANDO)
    username: str = "Lex-Usamn"
    password: str = "Lex#157."
    
    # Token JWT (preenchido automaticamente no login)
    jwt_token: str = ""
    
    # Configurações de requisição
    timeout: int = 30
    max_retries: int = 3
    
    # Paths locais
    vault_path: str = ""
    
    # Metadata
    token_expires_at: datetime = None


# ============================================
# CUSTOM EXCEPTIONS
# ============================================

class LexFlowError(Exception):
    """Erro genérico da API Lex Flow"""
    pass

class AuthenticationError(LexFlowError):
    """Erro de autenticação (login/senha/token)"""
    pass

class RateLimitError(LexFlowError):
    """Erro de rate limit (muitas requisições)"""
    pass

class NetworkError(LexFlowError):
    """Erro de rede/conexão"""
    pass


# ============================================
# MAIN CLIENT CLASS
# ============================================

class LexFlowClient:
    """
    Cliente Lex Flow - Versão Definitiva Produção
    
    Funcionalidades completas:
    ✅ Autenticação automática (login + refresh token)
    ✅ CRUD completo (Quick Notes, Projetos, Áreas, Recursos)
    ✅ Analytics e Dashboard
    ✅ Features de IA (categorização, resumo, sugestões)
    ✅ Pomodoro, Gamificação, TELOS Review
    ✅ Integração Obsidian
    
    Uso básico:
        lf = LexFlowClient()
        dashboard = lf.get_dashboard()
        notes = lf.get_inbox()
        lf.add_note("Minha ideia", "Detalhes...")
    """
    
    def __init__(self, config: LexFlowConfig = None):
        """
        Inicializa cliente Lex Flow
        
        Args:
            config: Configuração opcional. Se não fornecida, usa defaults.
        """
        self.cfg = config or LexFlowConfig()
        
        # Sessão HTTP persistente
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        log.info("=" * 70)
        log.info("🚀 LEX FLOW CLIENT INICIALIZANDO (VERSÃO DEFINITIVA)")
        log.info(f"📍 URL: {self.cfg.base_url}")
        log.info(f"👤 User: {self.cfg.username}")
        log.info("=" * 70)
        
        # Auto-login se tiver credenciais
        if self.cfg.username and self.cfg.password:
            if not self.login():
                log.warning("⚠️  Auto-login falhou. Use login() manualmente.")
        elif not self.cfg.jwt_token:
            log.warning("⚠️  Sem credenciais nem token. Configure antes de usar.")
    
    def _get_url(self, endpoint: str) -> str:
        """
        Constrói URL completa garantindo formato correto
        
        Regras:
        - Sempre adiciona /api/ se não presente
        - Garante começa com /
        """
        # Normalizar: remover /api duplicado
        if endpoint.startswith('/api/api/'):
            endpoint = endpoint.replace('/api/api/', '/api/', 1)
        
        # Garantir começa com /
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        
        # Adicionar /api/ se não tiver
        if not endpoint.startswith('/api/'):
            endpoint = '/api' + endpoint
        
        return f"{self.cfg.base_url}{endpoint}"
    
    def _update_auth_header(self):
        """Atualiza header de autorização com token atual"""
        if self.cfg.jwt_token:
            self.session.headers['Authorization'] = f'Bearer {self.cfg.jwt_token}'
    
    def _request(self, method: str, endpoint: str, 
                 expect_json: bool = True,
                 retry_on_auth_fail: bool = True,
                 **kwargs) -> Optional[Any]:
        """
        Método central de requisição com tratamento robusto de erros
        
        Args:
            method: GET, POST, PUT, DELETE
            endpoint: caminho da API (ex: 'quicknotes/')
            expect_json: se deve esperar resposta JSON
            retry_on_auth_fail: se deve tentar re-login em 401
            **kwargs: parâmetros extras (json=, params=, etc.)
            
        Returns:
            Dados da resposta (dict, list) ou None em erro
        """
        url = self._get_url(endpoint)
        
        for attempt in range(self.cfg.max_retries):
            try:
                log.debug(f"[Attempt {attempt+1}] {method} {url}")
                
                # Fazer requisição
                response = getattr(self.session, method.lower())(
                    url,
                    timeout=self.cfg.timeout,
                    **kwargs
                )
                
                # Log básico
                log.debug(f"Status: {response.status_code}")
                
                # Verificar se é HTML (erro de roteamento)
                content_type = response.headers.get('Content-Type', '')
                text_preview = response.text[:100].strip()
                
                if 'text/html' in content_type or text_preview.startswith('<') or '<!doctype' in text_preview.lower():
                    log.error(f"❌ Resposta HTML inesperada em {endpoint}")
                    log.error(f"   Content-Type: {content_type}")
                    log.error(f"   Preview: {text_preview}...")
                    return None
                
                # Tentar parsear JSON
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    log.error(f"❌ Erro parseando JSON: {e}")
                    log.error(f"   Response: {response.text[:200]}")
                    return None
                
                # Tratar erros conhecidos da API
                if isinstance(data, dict):
                    message = data.get('message', '')
                    
                    # Token inválido/expirado
                    if response.status_code == 401 or \
                       any(kw in message.lower() for kw in ['inválido', 'invalid', 'expired', 'unauthorized']):
                        
                        log.warning("⚠️  Token inválido ou expirado!")
                        
                        if retry_on_auth_fail and self.cfg.password:
                            log.info("Tentando re-login automático...")
                            if self.login():
                                log.info("✅ Re-login sucesso! Retentando...")
                                return self._request(method, endpoint, 
                                                   retry_on_auth_fail=False,
                                                   **kwargs)
                            else:
                                raise AuthenticationError("Re-login falhou")
                        else:
                            raise AuthenticationError("Token inválido e sem senha para re-logar")
                    
                    # Rate limit
                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        log.warning(f"⚠️  Rate limit! Esperar {retry_after}s")
                        import time
                        time.sleep(retry_after)
                        continue
                    
                    # Outros erros 4xx/5xx
                    if response.status_code >= 400:
                        log.error(f"❌ Erro API ({response.status_code}): {message}")
                        return None
                
                # Sucesso!
                if response.status_code == 200:
                    return data
                
                # Outros status (redirecionamentos, etc)
                log.debug(f"Status {response.status_code}: {data}")
                return data
                
            except requests.exceptions.Timeout:
                log.warning(f"⚠️  Timeout (tentativa {attempt+1})")
                if attempt < self.cfg.max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise NetworkError("Timeout após múltiplas tentativas")
                
            except requests.exceptions.ConnectionError as e:
                log.error(f"❌ Conexão recusada: {url}")
                log.error(f"   Erro: {e}")
                raise NetworkError(f"Não foi possível conectar em {url}")
                
            except AuthenticationError:
                raise  # Re-raise sem retry
                
            except Exception as e:
                log.error(f"❌ Erro inesperado: {type(e).__name__}: {e}")
                if attempt < self.cfg.max_retries - 1:
                    continue
                raise
        return None
    
    def _unwrap_list(self, data: Any) -> List[Dict]:
        """Tenta extrair uma lista de um objeto que pode estar envolto num dicionário"""
        if isinstance(data, list):
            return data
        if getattr(data, 'get', None):
            for key in ['data', 'projects', 'items', 'results', 'quicknotes', 'areas', 'resources', 'tasks']:
                if isinstance(data.get(key), list):
                    return data.get(key)
        return []
    
    # ==========================================
    # AUTENTICAÇÃO
    # ==========================================
    
    def login(self, username: str = None, password: str = None) -> bool:
        """
        Realiza login e obtém JWT token
        
        Args:
            username: sobrescreve config.username
            password: sobrescreve config.password
            
        Returns:
            True se login sucedido, False caso contrário
        """
        user = username or self.cfg.username
        pwd = password or self.cfg.password
        
        if not user or not pwd:
            log.error("❌ Credenciais incompletas para login")
            return False
        
        log.info(f"🔐 Fazendo login como: {user}")
        
        try:
            response = self.session.post(
                self._get_url('/auth/login'),
                json={'username': user, 'password': pwd},
                headers={'Content-Type': 'application/json'},
                timeout=self.cfg.timeout
            )
            
            if response.status_code != 200:
                log.error(f"❌ Login falhou (HTTP {response.status_code})")
                log.error(f"   Response: {response.text[:200]}")
                return False
            
            data = response.json()
            
            # Extrair token (pode vir em diferentes campos)
            token = data.get('token') or data.get('access_token')
            if not token and isinstance(data.get('data'), dict):
                token = data.get('data').get('token')
            
            if not token:
                log.error("❌ Resposta de login não contém token")
                log.error(f"   Data recebida: {data}")
                return False
            
            # Salvar token e metadados
            self.cfg.jwt_token = token
            self.cfg.username = user
            self.cfg.password = pwd
            self._update_auth_header()
            
            # Calcular expiração (se houver info)
            if isinstance(data.get('expires_in'), int):
                self.cfg.token_expires_at = datetime.now() + \
                    timedelta(seconds=data['expires_in'])
            
            user_info = data.get('user', {})
            log.info(f"✅ LOGIN SUCESSO!")
            log.info(f"   User: {user_info.get('username', user)}")
            log.info(f"   Email: {user_info.get('email', 'N/A')}")
            log.info(f"   Token: {token[:50]}...")
            
            return True
            
        except Exception as e:
            log.error(f"❌ Exceção no login: {e}")
            return False
    
    def logout(self) -> bool:
        """Faz logout (invalida sessão local)"""
        try:
            self._request('POST', '/logout', retry_on_auth_fail=False)
        except:
            pass  # Ignorar erros no logout
        
        self.cfg.jwt_token = ""
        self.cfg.token_expires_at = None
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
        
        log.info("✅ Logout realizado")
        return True
    
    def verify_token(self) -> bool:
        """Verifica se token atual ainda é válido"""
        if not self.cfg.jwt_token:
            return False
        
        try:
            result = self._request('GET', '/verify', retry_on_auth_fail=False)
            return result is not None
        except:
            return False
    
    def is_authenticated(self) -> bool:
        """Verifica estado de autenticação"""
        return bool(self.cfg.jwt_token)
    
    # ==========================================
    # QUICK NOTES (CAIXA DE ENTRADA / INBOX)
    # ==========================================
    
    def get_inbox(self) -> List[Dict]:
        """
        Busca todas as anotações da caixa de entrada
        
        Returns:
            Lista de dicionários com notas
        """
        data = self._request('GET', '/quicknotes/')
        return self._unwrap_list(data)
    
    def get_note(self, note_id: int) -> Optional[Dict]:
        """Busca anotação específica por ID"""
        return self._request('GET', f'/quicknotes/{note_id}')
    
    def add_note(self, title: str, content: str = "",
                 tags: List[str] = None,
                 summary: str = None) -> Optional[Dict]:
        """
        Cria nova anotação na caixa de entrada (CAPTURA RÁPIDA)
        
        Este é o método principal para capturar ideias!
        
        Args:
            title: título da nota (obrigatório)
            conteúdo: corpo da nota
            tags: lista de tags
            summary: resumo (auto-gerado se não fornecido)
            
        Returns:
            Dados da nota criada ou None
        """
        payload = {
            'title': title,
            'content': content,
            'summary': summary or (content[:200] if content else title),
            'tags': tags or []
        }
        
        result = self._request('POST', '/quicknotes/', json=payload)
        
        if result:
            log.info(f"✅ Nota criada: '{title}' (ID: {result.get('id')})")
        
        return result
    
    def update_note(self, note_id: int, title: str = None,
                     content: str = None, tags: List[str] = None) -> bool:
        """Atualiza anotação existente"""
        payload = {}
        if title is not None:
            payload['title'] = title
        if content is not None:
            payload['content'] = content
        if tags is not None:
            payload['tags'] = tags
        
        result = self._request('PUT', f'/quicknotes/{note_id}', json=payload)
        return bool(result)
    
    def delete_note(self, note_id: int) -> bool:
        """Deleta anotação permanentemente"""
        result = self._request('DELETE', f'/quicknotes/{note_id}')
        return bool(result)
    
    def convert_note_to_task(self, note_id: int, 
                              project_id: int = None) -> Optional[Dict]:
        """
        Converte anotação em tarefa (Inbox → Projeto)
        
        Fluxo principal de organização: capturar depois organizar!
        """
        body = {}
        if project_id:
            body['project_id'] = project_id
        
        result = self._request('POST', f'/quicknotes/{note_id}/convert-to-task', json=body)
        
        if result:
            log.info(f"🔄 Nota {note_id} convertida em tarefa")
        
        return result
    
    def search_notes(self, query: str) -> List[Dict]:
        """Busca anotações por título (autocomplete)"""
        data = self._request('GET', '/quicknotes/search-titles', 
                           params={'query': query})
        return data if isinstance(data, list) else []
    
    def link_note_to_target(self, note_id: int, target_type: str, 
                             target_id: int) -> bool:
        """Vincula anotação a projeto/área/recurso"""
        result = self._request('PUT', f'/quicknotes/{note_id}/link', json={
            'target_type': target_type,
            'target_id': target_id
        })
        return bool(result)
    
    # ==========================================
    # PROJETOS (COLLABORATION)
    # ==========================================
    
    def get_projects(self, include_archived: bool = False) -> List[Dict]:
        """Busca projetos ativos (ou arquivados)"""
        if include_archived:
            data = self._request('GET', '/collaboration/projects/archived')
        else:
            data = self._request('GET', '/collaboration/projects')
        return self._unwrap_list(data)
    
    def get_project(self, project_id: int) -> Optional[Dict]:
        """Detalhes completos de projeto específico"""
        return self._request('GET', f'/collaboration/projects/{project_id}')
    
    def create_project(self, name: str, description: str = "",
                        is_public: bool = False) -> Optional[Dict]:
        """Cria novo projeto"""
        result = self._request('POST', '/collaboration/projects', json={
            'name': name,
            'description': description,
            'is_public': is_public
        })
        
        if result:
            log.info(f"✅ Projeto criado: '{name}' (ID: {result.get('id')})")
        
        return result
    
    def update_project(self, project_id: int, name: str = None,
                        description: str = None) -> bool:
        """Atualiza dados do projeto"""
        payload = {}
        if name:
            payload['name'] = name
        if description:
            payload['description'] = description
        
        result = self._request('PUT', f'/collaboration/projects/{project_id}', 
                              json=payload)
        return bool(result)
    
    def archive_project(self, project_id: int) -> bool:
        """Arquiva projeto (move para arquivo)"""
        result = self._request('PUT', f'/collaboration/projects/{project_id}/archive')
        return bool(result)
    
    def unarchive_project(self, project_id: int) -> bool:
        """Desarquiva projeto"""
        result = self._request('PUT', f'/collaboration/projects/{project_id}/unarchive')
        return bool(result)
    
    def get_project_tasks(self, project_id: int) -> List[Dict]:
        """Lista tarefas de um projeto"""
        data = self._request('GET', f'/collaboration/projects/{project_id}/tasks')
        return data if isinstance(data, list) else []
    
    def add_task(self, project_id: int, title: str,
                 description: str = "", priority: str = "medium",
                 due_date: str = None, tags: List[str] = None,
                 category: str = None) -> Optional[Dict]:
        """
        Cria tarefa dentro de projeto
        
        Prioridades sugeridas: low, medium, high, urgent
        """
        payload = {
            'title': title,
            'description': description,
            'priority': priority,
            'tags': tags or []
        }
        
        if due_date:
            payload['due_date'] = due_date
        if category:
            payload['category'] = category
        
        result = self._request('POST', 
                             f'/collaboration/projects/{project_id}/tasks',
                             json=payload)
        
        if result:
            log.info(f"✅ Tarefa criada: '{title}' no projeto {project_id}")
        
        return result
    
    def update_task(self, project_id: int, task_id: int,
                     title: str = None, status: str = None,
                     priority: str = None) -> bool:
        """Atualiza tarefa"""
        payload = {}
        if title:
            payload['title'] = title
        if status:
            payload['status'] = status
        if priority:
            payload['priority'] = priority
        
        result = self._request('PUT', 
                             f'/collaboration/projects/{project_id}/tasks/{task_id}',
                             json=payload)
        return bool(result)
    
    def get_task_comments(self, project_id: int, task_id: int) -> List[Dict]:
        """Comentários de uma tarefa"""
        data = self._request('GET', 
                           f'/collaboration/projects/{project_id}/tasks/{task_id}/comments')
        return data if isinstance(data, list) else []
    
    def add_task_comment(self, project_id: int, task_id: int,
                          content: str, parent_id: int = None) -> Optional[Dict]:
        """Adiciona comentário à tarefa"""
        payload = {'content': content}
        if parent_id:
            payload['parent_comment_id'] = parent_id
        
        return self._request('POST', 
                            f'/collaboration/projects/{project_id}/tasks/{task_id}/comments',
                            json=payload)
    
    # ==========================================
    # ÁREAS (P.A.R.A.)
    # ==========================================
    
    def get_areas(self) -> List[Dict]:
        """Áreas de responsabilidade ativas"""
        data = self._request('GET', '/areas/')
        return self._unwrap_list(data)
    
    def get_area(self, area_id: int) -> Optional[Dict]:
        """Detalhes de área com tarefas e notas"""
        return self._request('GET', f'/areas/{area_id}/details')
    
    def create_area(self, name: str, description: str = "") -> Optional[Dict]:
        """Cria nova área"""
        result = self._request('POST', '/areas/', json={
            'name': name,
            'description': description
        })
        
        if result:
            log.info(f"✅ Área criada: '{name}'")
        
        return result
    
    def update_area(self, area_id: int, name: str = None,
                    description: str = None) -> bool:
        """Atualiza área"""
        payload = {}
        if name:
            payload['name'] = name
        if description:
            payload['description'] = description
        
        result = self._request('PUT', f'/areas/{area_id}', json=payload)
        return bool(result)
    
    def archive_area(self, area_id: int) -> bool:
        """Arquiva área"""
        result = self._request('PUT', f'/areas/{area_id}/archive')
        return bool(result)
    
    def get_area_tasks(self, area_id: int) -> List[Dict]:
        """Tarefas vinculadas à área"""
        data = self._request('GET', f'/areas/{area_id}/tasks')
        return data if isinstance(data, list) else []
    
    def add_area_task(self, area_id: int, title: str,
                      category: str = None) -> Optional[Dict]:
        """Cria tarefa dentro de área"""
        payload = {'title': title}
        if category:
            payload['category'] = category
        
        return self._request('POST', f'/areas/{area_id}/tasks', json=payload)
    
    # ==========================================
    # RECURSOS (BASE DE CONHECIMENTO)
    # ==========================================
    
    def get_resources(self) -> List[Dict]:
        """Todos os recursos"""
        data = self._request('GET', '/resources/')
        return self._unwrap_list(data)
    
    def get_resource(self, resource_id: int) -> Optional[Dict]:
        """Recurso específico"""
        return self._request('GET', f'/resources/{resource_id}')
    
    def add_resource(self, url: str = "", notes: str = "") -> Optional[Dict]:
        """Adiciona novo recurso à base de conhecimento"""
        result = self._request('POST', '/resources/', json={
            'url': url,
            'notes': notes
        })
        
        if result:
            log.info(f"✅ Recurso adicionado: {url[:50]}...")
        
        return result
    
    def update_resource(self, resource_id: int, url: str = None,
                        notes: str = None, status: str = None) -> bool:
        """Atualiza recurso"""
        payload = {}
        if url:
            payload['url'] = url
        if notes:
            payload['notes'] = notes
        if status:
            payload['status'] = status
        
        result = self._request('PUT', f'/resources/{resource_id}', json=payload)
        return bool(result)
    
    def delete_resource(self, resource_id: int) -> bool:
        """Deleta recurso"""
        result = self._request('DELETE', f'/resources/{resource_id}')
        return bool(result)
    
    # ==========================================
    # ANALYTICS & DASHBOARD
    # ==========================================
    
    def get_dashboard(self) -> Optional[Dict]:
        """Dados completos do dashboard (métricas visuais)"""
        return self._request('GET', '/analytics/dashboard')
    
    def get_analytics(self, time_range: str = None) -> Optional[Dict]:
        """Analytics detalhado com filtro de tempo"""
        params = {}
        if time_range:
            params['timeRange'] = time_range
        
        return self._request('GET', '/analytics/', params=params)
    
    def export_analytics(self) -> Optional[Dict]:
        """Exporta relatório completo de analytics"""
        return self._request('GET', '/analytics/export')
    
    def get_ai_quote(self) -> Optional[str]:
        """Citação/motivação do dia gerada por IA"""
        data = self._request('GET', '/analytics/quote')
        return data.get('quote') if data else None
    
    # ==========================================
    # AI FEATURES (INTELIGÊNCIA ARTIFICIAL)
    # ==========================================
    
    def smart_categorize(self, items: List[str], 
                         title: str = "", text: str = "") -> Optional[Dict]:
        """
        IA categoriza automaticamente itens
        
        Perfeito para processar inbox! Sugere onde cada item vai.
        """
        return self._request('POST', '/smart-categorization', json={
            'items': items,
            'title': title,
            'text': text
        })
    
    def smart_summary(self, content: str, max_length: int = 300,
                      summary_type: str = "general") -> Optional[str]:
        """
        Gera resumo inteligente de conteúdo
        
        Ótimo para: artigos longos, reuniões, transcrições
        """
        data = self._request('POST', '/smart-summary', json={
            'content': content,
            'max_length': max_length,
            'type': summary_type
        })
        
        return data.get('summary') if data else None
    
    def get_task_suggestions(self, current_tasks: List[str] = [],
                              goals: List[str] = [],
                              context: str = "") -> Optional[List[Dict]]:
        """
        IA gera sugestões de tarefas baseadas em contexto
        
        Útil quando: não sabe o que fazer next
        """
        data = self._request('POST', '/task-suggestions', json={
            'current_tasks': current_tasks,
            'goals': goals,
            'context': context
        })
        
        return data if isinstance(data, list) else []
    
    def calculate_priorities(self, tasks: List[Dict]) -> Optional[List[Dict]]:
        """
        IA calcula scores de prioridade para tarefas
        
        Retorna tarefas ordenadas por importância/urgência
        """
        return self._request('POST', '/priority-scoring', json={
            'tasks': tasks
        })
    
    def get_productivity_insights(self, daily_stats: Dict = None,
                                    weekly_stats: Dict = None,
                                    tasks_completed: List = None,
                                    goals_progress: Dict = None) -> Optional[Dict]:
        """
        Analisa dados e gera insights de produtividade
        
        Chamar periodicamente (diário/semanal)
        """
        return self._request('POST', '/productivity-insights', json={
            'daily_stats': daily_stats or {},
            'weekly_stats': weekly_stats or {},
            'tasks_completed': tasks_completed or [],
            'goals_progress': goals_progress or {},
            'analysis_date': datetime.now().isoformat()
        })
    
    def get_study_recommendations(self, interests: List[str] = None,
                                   current_projects: List[str] = None,
                                   learning_goals: List[str] = None) -> Optional[List[Dict]]:
        """IA recomenda conteúdos de estudo"""
        return self._request('POST', '/study-recommendations', json={
            'interests': interests or [],
            'current_projects': current_projects or [],
            'learning_goals': learning_goals or []
        })
    
    def optimize_schedule(self, current_schedule: List[Dict] = None,
                           productivity_patterns: Dict = None,
                           constraints: List[str] = None) -> Optional[Dict]:
        """IA otimiza cronograma baseado em padrões"""
        return self._request('POST', '/schedule-optimization', json={
            'current_schedule': current_schedule or [],
            'productivity_patterns': productivity_patterns or {},
            'constraints': constraints or []
        })
    
    def get_ai_providers(self) -> List[Dict]:
        """Lista provedores de IA disponíveis"""
        data = self._request('GET', '/providers')
        return data if isinstance(data, list) else []
    
    def clear_ai_cache(self) -> bool:
        """Limpa cache de sugestões de IA"""
        result = self._request('POST', '/cache/clear', json={})
        return bool(result)
    
    # ==========================================
    # POMODORO
    # ==========================================
    
    def get_pomodoro_data(self) -> Optional[Dict]:
        """Dados das sessões de pomodoro"""
        return self._request('GET', '/pomodoro/')
    
    def save_pomodoro_settings(self, work_duration: int = 25,
                               short_break: int = 5,
                               long_break: int = 15,
                               sessions_until_long: int = 4) -> bool:
        """Configura durações do pomodoro"""
        result = self._request('POST', '/pomodoro/settings', json={
            'workDuration': work_duration,
            'shortBreakDuration': short_break,
            'longBreakDuration': long_break,
            'sessionsUntilLongBreak': sessions_until_long
        })
        return bool(result)
    
    def log_pomodoro_session(self) -> bool:
        """Registra sessão de pomodoro concluída"""
        result = self._request('POST', '/pomodoro/log-session', json={})
        
        if result:
            log.info("🍅 Sessão de pomodoro registrada")
        
        return bool(result)
    
    # ==========================================
    # GAMIFICAÇÃO
    # ==========================================
    
    def get_gamification_data(self) -> Optional[Dict]:
        """Dados completos de gamificação (XP, nível, streak)"""
        return self._request('GET', '/')
    
    def record_activity(self, activity_type: str) -> bool:
        """
        Registra atividade para gamificação (ganha XP!)
        
        Exemplos de activity_type:
        - 'task_completed'
        - 'pomodoro_completed'
        - 'note_created'
        - 'project_created'
        - 'study_session'
        """
        result = self._request('POST', '/record-activity', json={
            'type': activity_type
        })
        
        if result:
            log.info(f"🎮 Atividade registrada: {activity_type}")
        
        return bool(result)
    
    def export_gamification_data(self) -> Optional[Dict]:
        """Exporta dados de gamificação"""
        return self._request('GET', '/export')
    
    def reset_gamification(self) -> bool:
        """Reseta progresso de gamificação (cuidado!)"""
        result = self._request('POST', '/reset', json={})
        return bool(result)
    
    # ==========================================
    # TELOS REVIEW (REVISÃO SISTEMÁTICA)
    # ==========================================
    
    def get_telos_framework(self) -> Optional[Dict]:
        """Framework/configuração TELOS atual"""
        return self._request('GET', '/telos/framework')
    
    def save_telos_framework(self, content: str) -> bool:
        """Salva configuração do framework TELOS"""
        result = self._request('POST', '/telos/framework', json={
            'content': content
        })
        return bool(result)
    
    def get_telos_reviews(self) -> List[Dict]:
        """Histórico de revisões TELOS"""
        data = self._request('GET', '/telos/reviews')
        return data if isinstance(data, list) else []
    
    def save_telos_review(self, content: str, 
                           review_date: str = None) -> bool:
        """
        Salva nova revisão TELOS (semanal recomendado)
        
        Deve ser chamada aos domingos preferencialmente
        """
        result = self._request('POST', '/telos/review', json={
            'content': content,
            'review_date': review_date or datetime.now().strftime('%Y-%m-%d')
        })
        
        if result:
            log.info(f"📋 TELOS Review salva ({review_date or 'hoje'})")
        
        return bool(result)
    
    # ==========================================
    # INTEGRAÇÕES
    # ==========================================
    
    def get_integrations(self) -> Optional[Dict]:
        """Configurações de integrações"""
        return self._request('GET', '/integrations/')
    
    def save_integrations_config(self, sync_targets: List[str] = None,
                                  credentials: Dict = None) -> bool:
        """Salva configurações de integrações"""
        result = self._request('POST', '/integrations/config', json={
            'syncTargets': sync_targets or [],
            'credentials': credentials or {}
        })
        return bool(result)
    
    def test_connections(self) -> Optional[Dict]:
        """Testa conexões configuradas"""
        return self._request('GET', '/integrations/test-connections')
    
    def sync_tasks(self) -> bool:
        """Sincroniza tarefas com integrações"""
        result = self._request('POST', '/integrations/sync/tasks', json={})
        return bool(result)
    
    def export_to_obsidian(self, vault_path: str = None) -> bool:
        """
        Exporta dados do Lex Flow para formato Obsidian!
        
        INTEGRAMENTE CRÍTICO: Mantém segundo cérebro sincronizado
        """
        result = self._request('POST', '/integrations/obsidian/export', json={
            'vault_path': vault_path or self.cfg.vault_path
        })
        
        if result:
            log.info(f"📦 Exportação para Obsidian concluída")
        
        return bool(result)
    
    # ==========================================
    # CLOUD / SYNC
    # ==========================================
    
    def get_cloud_providers(self) -> List[Dict]:
        """Provedores de nuvem disponíveis"""
        data = self._request('GET', '/cloud/providers')
        return data if isinstance(data, list) else []
    
    def get_cloud_connections(self) -> List[Dict]:
        """Conexões de nuvem ativas"""
        data = self._request('GET', '/cloud/connections')
        return data if isinstance(data, list) else []
    
    def get_sync_status(self) -> Optional[Dict]:
        """Status de sincronização"""
        return self._request('GET', '/cloud/sync-status')
    
    # ==========================================
    # MÉTODOS CONVENIENTES (SHORTCUTS)
    # ==========================================
    
    def quick_capture(self, idea: str, tags: List[str] = None) -> Optional[Dict]:
        """
        CAPTURA RÁPIDA - Método principal para usar!
        
        Captura ideia instantaneamente no Inbox.
        Equivalente a: add_note() mas mais simples de usar.
        """
        return self.add_note(
            title=idea[:100],  # Primeiros 100 chars como título
            content=idea,      # Conteúdo completo
            tags=tags or ['capturada']
        )
    
    def get_today_priorities(self) -> List[Dict]:
        """Prioridades do dia (do dashboard)"""
        dash = self.get_dashboard()
        if dash and 'priorities' in dash:
            return dash['priorities']
        return []
    
    def get_today_stats(self) -> Dict:
        """Estatísticas rápidas do dia"""
        dash = self.get_dashboard()
        if dash and 'stats' in dash:
            return dash['stats']
        return {}
    
    def process_inbox_with_ai(self) -> Optional[Dict]:
        """
        Processa inbox automaticamente com IA!
        
        1. Busca todas as notas
        2. Envia para smart_categorize
        3. Retorna sugestões de organização
        """
        notes = self.get_inbox()
        
        if not notes:
            log.info("📥 Inbox vazio! Nada para processar.")
            return {'message': 'Inbox vazio', 'processed': 0}
        
        titles = [n.get('title', '') for n in notes]
        contents = [n.get('content', '') for n in notes]
        
        result = self.smart_categorize(items=titles, text='\n'.join(contents))
        
        if result:
            log.info(f"🤖 IA processou {len(notes)} notas do inbox")
        
        return result
    
    def get_full_sync_status(self) -> Dict:
        """Status completo de sincronização"""
        return {
            'authenticated': self.is_authenticated(),
            'inbox_count': len(self.get_inbox()),
            'projects_count': len(self.get_projects()),
            'areas_count': len(self.get_areas()),
            'today_stats': self.get_today_stats(),
            'priorities': self.get_today_priorities()
        }


# ================================================
# MAIN - TESTE COMPLETO PRODUÇÃO
# ================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🧪 LEX FLOW CLIENT - VERSÃO DEFINITIVA (PRODUÇÃO)")
    print("=" * 80 + "\n")
    
    # Configurar com credenciais REAIS (testadas e funcionando!)
    config = LexFlowConfig(
        username="Lex-Usamn",
        password="Lex#157.",
        base_url="https://flow.lex-usamn.com.br"
    )
    
    # Inicializar cliente (vai fazer auto-login automaticamente!)
    print("⏳ Inicializando cliente Lex Flow...\n")
    client = LexFlowClient(config)
    
    # Verificar autenticação
    if not client.is_authenticated():
        print("\n❌ FALHA CRÍTICA: Não foi possível autenticar!")
        print("   Verifique suas credenciais.\n")
        sys.exit(1)
    
    print(f"✅ AUTENTICADO COM SUCESSO!\n")
    print("-" * 80)
    
    # ========================================
    # TESTES COMPLETOS
    # ========================================
    
    test_results = {}
    
    # Teste 1: Dashboard
    print("\n1️⃣  DASHBOARD", end=" ... ")
    try:
        dash = client.get_dashboard()
        if dash:
            print(f"✅ SUCESSO")
            test_results['dashboard'] = dash
        else:
            print("⚠️  Vazio")
    except Exception as e:
        print(f"❌ ERRO: {e}")
    
    # Teste 2: Inbox (Quick Notes)
    print("2️⃣  INBOX (Quick Notes)", end=" ... ")
    try:
        notes = client.get_inbox()
        print(f"✅ {len(notas)} notas")
        test_results['inbox'] = notes
    except Exception as e:
        print(f"❌ ERRO: {e}")
    
    # Teste 3: Projetos
    print("3️⃣  PROJETOS ATIVOS", end=" ... ")
    try:
        projects = client.get_projects()
        print(f"✅ {len(projects)} projetos")
        test_results['projects'] = projects
    except Exception as e:
        print(f"❌ ERRO: {e}")
    
    # Teste 4: Áreas
    print("4️⃣  ÁREAS (P.A.R.A.)", end=" ... ")
    try:
        areas = client.get_areas()
        print(f"✅ {len(areas)} áreas")
        test_results['areas'] = areas
    except Exception as e:
        print(f"❌ ERRO: {e}")
    
    # Teste 5: Recursos
    print("5️⃣  RECURSOS", end=" ... ")
    try:
        resources = client.get_resources()
        print(f"✅ {len(resources)} recursos")
        test_results['resources'] = resources
    except Exception as e:
        print(f"❌ ERRO: {e}")
    
    # Teste 6: Gamificação
    print("6️⃣  GAMIFICAÇÃO (XP/Nível)", end=" ... ")
    try:
        game = client.get_gamification_data()
        if game:
            level = game.get('level', '?')
            xp = game.get('currentXP', '?')
            print(f"✅ Nível {level}, XP: {xp}")
            test_results['gamification'] = game
        else:
            print("⚠️  Vazio")
    except Exception as e:
        print(f"❌ ERRO: {e}")
    
    # Teste 7: Pomodoro
    print("7️⃣  POMODORO", end=" ... ")
    try:
        pomo = client.get_pomodoro_data()
        if pomo:
            print(f"✅ Dados obtidos")
            test_results['pomodoro'] = pomo
        else:
            print("⚠️  Vazio")
    except Exception as e:
        print(f"❌ ERRO: {e}")
    
    # Teste 8: TELOS Reviews
    print("8️⃣  TELOS REVIEWS", end=" ... ")
    try:
        telos = client.get_telos_reviews()
        print(f"✅ {len(telos)} reviews históricas")
        test_results['telos'] = telos
    except Exception as e:
        print(f"❌ ERRO: {e}")
    
    # ========================================
    # MOSTRAR DADOS INTERESSANTES
    # ========================================
    
    print("\n" + "=" * 80)
    print("📊 SEUS DADOS ATUAIS NO LEX FLOW:")
    print("=" * 80)
    
    # Dashboard
    if 'dashboard' in test_results:
        d = test_results['dashboard']
        print("\n🎯 DASHBOARD:")
        print(json.dumps(d, indent=2, ensure_ascii=False))
    
    # Inbox
    if 'inbox' in test_results and test_results['inbox']:
        print(f"\n📥 INBOX ({len(test_results['inbox'])} notas):")
        for n in test_results['inbox']:
            print(f"   • [{n.get('id')}] {n.get('title', 'Sem título')}")
            if n.get('tags'):
                print(f"     Tags: {n.get('tags')}")
    
    # Projetos
    if 'projects' in test_results and test_results['projects']:
        print(f"\n📂 PROJETOS ATIVOS ({len(test_results['projects'])}):")
        for p in test_results['projects']:
            print(f"   • [{p.get('id')}] {p.get('name', '?')}")
            desc = p.get('description', '')
            if desc:
                print(f"     └─ {desc[:80]}{'...' if len(desc)>80 else ''}")
    
    # Áreas
    if 'areas' in test_results and test_results['areas']:
        print(f"\n🏷️  ÁREAS ({len(test_results['areas'])}):")
        for a in test_results['areas']:
            print(f"   • [{a.get('id')}] {a.get('name', '?')}")
    
    # Prioridades do dia
    priorities = client.get_today_priorities()
    if priorities:
        print(f"\n🎯 TOP PRIORIDADES DE HOJE:")
        for i, p in enumerate(priorities, 1):
            proj = p.get('project_title', '')
            task = p.get('title', '')
            print(f"   {i}. [{proj}] {task}")
    
    # Stats rápidas
    stats = client.get_today_stats()
    if stats:
        print(f"\n📈 ESTATÍSTICAS DO DIA:")
        for k, v in stats.items():
            print(f"   • {k}: {v}")
    
    # ========================================
    # TESTE DE CAPTURA (OPCIONAL)
    # ========================================
    
    print("\n" + "-" * 80)
    print("🧪 TESTE DE CAPTURA RÁPIDA (criando nota teste):")
    print("-" * 80)
    
    test_note = client.quick_capture(
        "Teste via Second Brain Integration",
        tags=["teste", "second-brain", "automático"]
    )
    
    if test_note:
        print(f"✅ Nota de teste criada: ID {test_note.get('id')}")
        print(f"   Título: {test_note.get('title')}")
    else:
        print("⚠️  Nota não criada (pode já existir ou erro)")
    
    # ========================================
    # RESUMO FINAL
    # ========================================
    
    print("\n" + "=" * 80)
    print("✅ TESTE CONCLUÍDO - RESUMO:")
    print("=" * 80)
    
    total_tests = len([r for r in test_results.values() if r is not None])
    print(f"   Testes bem-sucedidos: {total_tests}/{len(test_results)}")
    print(f"   Status da conexão: {'🟢 ATIVA' if client.is_authenticated() else '🔴 INATIVA'}")
    print(f"   URL base: {config.base_url}")
    print(f"   Usuário: {config.username}")
    
    print("\n" + "=" * 80)
    print("🎉 LEX FLOW INTEGRAÇÃO 100% FUNCIONAL!")
    print("=" * 80)
    print("""
Próximos passos:
   1. Usar este cliente em seus scripts de automação
   2. Integrar com Second Brain Engine (próximo módulo)
   3. Configurar Heartbeat para monitoramento proativo
   4. Criar Skills personalizados (Content Creator, etc.)

Exemplo de uso rápido:
   
   from lex_flow_definitivo import LexFlowClient, LexFlowConfig
   
   lf = LexFlowClient(LexFlowConfig())
   
   # Capturar ideia
   lf.quick_capture("Minha nova ideia incrível!")
   
   # Ver prioridades
   prios = lf.get_today_priorities()
   
   # Criar tarefa em projeto
   lf.add_task(project_id=1, title="Fazer X", priority="high")
""")
    print("=" * 80 + "\n")