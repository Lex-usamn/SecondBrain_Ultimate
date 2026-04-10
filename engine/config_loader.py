"""
Config Loader - Carrega configurações centralizadas
------------------------------------------
Lê settings.yaml e variáveis ambiente (.env)
Fornece acesso global às configurações do sistema
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class SystemConfig:
    """Configurações do sistema (dataclass para type hints)"""
    
    # Sistema
    name: str = "LEX-BRAIN HYBRID"
    version: str = "1.0"
    environment: str = "development"
    debug: bool = True
    
    # Usuário
    user_name: str = "Lex-Usamn"
    user_email: str = ""
    timezone: str = "America/Sao_Paulo"
    language: str = "pt-BR"
    
    # Lex Flow
    lex_flow_base_url: str = ""
    lex_flow_username: str = ""
    lex_flow_password: str = ""
    lex_flow_timeout: int = 30
    lex_flow_max_retries: int = 3
    lex_flow_vault_path: str = ""
    lex_flow_auto_login: bool = True
    
    # Database
    db_type: str = "sqlite"
    db_sqlite_path: str = "data/second_brain.db"
    
    # RAG
    rag_enabled: bool = False
    
    # Telegram
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_user_chat_id: str = ""
    
    # AI
    ai_primary_provider: str = "claude"
    ai_primary_model: str = "claude-sonnet-4-20250514"
    ai_primary_api_key: str = ""
    
    # Automation
    automation_enabled: bool = False
    
    # Logging
    log_level: str = "INFO"
    log_file_path: str = "logs/second_brain.log"


class ConfigLoader:
    """
    Carregador de configurações singleton
    
    Uso:
        config = ConfigLoader.get_instance()
        print(config.lex_flow_base_url)
    """
    
    _instance = None
    _config: SystemConfig = None
    _raw_config: Dict = {}
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._load_config()
        self._initialized = True
        
        print(f"📋 Config carregada: {self._config.name} v{self._config.version}")
        print(f"   Ambiente: {self._config.environment}")
        print(f"   Debug: {self._config.debug}")
    
    @classmethod
    def get_instance(cls) -> 'ConfigLoader':
        """Obter instância singleton"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @property
    def config(self) -> SystemConfig:
        """Acessar configurações tipadas"""
        return self._config
    
    @property
    def raw(self) -> Dict:
        """Acessar configurações brutas (dict)"""
        return self._raw_config
    
    def _load_config(self):
        """Carregar configurações de YAML + ENV"""
        
        # 1. Caminho do arquivo YAML
        config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        
        # 2. Carregar YAML se existir
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self._raw_config = yaml.safe_load(f) or {}
            print(f"✅ Config YAML carregada: {config_path}")
        else:
            print(f"⚠️  Config YAML não encontrada: {config_path}")
            print("   Usando valores padrão.")
            self._raw_config = {}
        
        # 3. Carregar variáveis ambiente (.env)
        self._load_env_vars()
        
        # 4. Popular dataclass
        self._populate_dataclass()
    
    def _load_env_vars(self):
        """
        Carregar variáveis de ambiente
        Substitui ${VAR} nos valores do YAML
        """
        env_mapping = {
            'TELEGRAM_BOT_TOKEN': ['telegram', 'bot_token'],
            'TELEGRAM_USER_CHAT_ID': ['telegram', 'user_chat_id'],
            'DISCORD_BOT_TOKEN': ['discord', 'bot_token'],
            'DISCORD_GUILD_ID': ['discord', 'guild_id'],
            'CLAUDE_API_KEY': ['ai', 'primary', 'api_key'],
            'GEMINI_API_KEY': ['ai', 'secondary', 'api_key'],
            'POSTGRES_PASSWORD': ['database', 'postgresql', 'password'],
        }
        
        for env_var, yaml_path in env_mapping.items():
            value = os.environ.get(env_var)
            
            if value:
                # Substituir no dict aninhado
                self._set_nested_value(yaml_path, value)
                
                if self._config_is_debug():
                    print(f"   🔑 ENV: {env_var} ✓")
    
    def _set_nested_value(self, path: list, value: Any):
        """Definir valor em dict aninhado"""
        current = self._raw_config
        
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[path[-1]] = value
    
    def _populate_dataclass(self):
        """Preencher SystemConfig com valores do YAML"""
        
        cfg_dict = self._raw_config
        
        # Sistema
        system = cfg_dict.get('system', {})
        user = cfg_dict.get('user', {})
        
        # Lex Flow
        lex_flow = cfg_dict.get('lex_flow', {})
        
        # Database
        database = cfg_dict.get('database', {})
        sqlite_cfg = database.get('sqlite', {})
        
        # RAG
        rag = cfg_dict.get('rag', {})
        
        # Telegram
        telegram = cfg_dict.get('telegram', {})
        
        # AI
        ai = cfg_dict.get('ai', {})
        ai_primary = ai.get('primary', {})
        
        # Automation
        automation = cfg_dict.get('automation', {})
        
        # Logging
        logging_cfg = cfg_dict.get('logging', {})
        
        # Criar instancia do dataclass
        self._config = SystemConfig(
            # Sistema
            name=system.get('name', 'LEX-BRAIN HYBRID'),
            version=system.get('version', '1.0'),
            environment=system.get('environment', 'development'),
            debug=system.get('debug', True),
            
            # Usuário
            user_name=user.get('name', 'Lex-Usamn'),
            user_email=user.get('email', ''),
            timezone=user.get('timezone', 'America/Sao_Paulo'),
            language=user.get('language', 'pt-BR'),
            
            # Lex Flow
            lex_flow_base_url=lex_flow.get('base_url', ''),
            lex_flow_username=lex_flow.get('username', ''),
            lex_flow_password=lex_flow.get('password', ''),
            lex_flow_timeout=lex_flow.get('timeout', 30),
            lex_flow_max_retries=lex_flow.get('max_retries', 3),
            lex_flow_vault_path=lex_flow.get('vault_path', ''),
            lex_flow_auto_login=lex_flow.get('auto_login', True),
            
            # Database
            db_type=database.get('type', 'sqlite'),
            db_sqlite_path=sqlite_cfg.get('path', 'data/second_brain.db'),
            
            # RAG
            rag_enabled=rag.get('enabled', False),
            
            # Telegram
            telegram_enabled=telegram.get('enabled', False),
            telegram_bot_token=telegram.get('bot_token', ''),
            telegram_user_chat_id=telegram.get('user_chat_id', ''),
            
            # AI
            ai_primary_provider=ai_primary.get('provider', 'claude'),
            ai_primary_model=ai_primary.get('model', 'claude-sonnet-4-20250514'),
            ai_primary_api_key=ai_primary.get('api_key', ''),
            
            # Automation
            automation_enabled=automation.get('enabled', False),
            
            # Logging
            log_level=logging_cfg.get('level', 'INFO'),
            log_file_path=logging_cfg.get('file', {}).get('path', 'logs/second_brain.log'),
        )
    
    def _config_is_debug(self) -> bool:
        """Verificar se modo debug está ativo"""
        return self._raw_config.get('system', {}).get('debug', False)
    
    def get_lex_flow_config(self) -> Dict:
        """Retornar config formatada para LexFlowClient"""
        return {
            'base_url': self._config.lex_flow_base_url,
            'username': self._config.lex_flow_username,
            'password': self._config.lex_flow_password,
            'timeout': self._config.lex_flow_timeout,
            'max_retries': self._config.lex_flow_max_retries,
            'vault_path': self._config.lex_flow_vault_path,
        }
    
    def reload(self):
        """Recarregar configurações (útil para hot-reload em dev)"""
        self._initialized = False
        self._load_config()
        self._initialized = True
        print("🔄 Config recarregada!")


# -----------------------------------------------
# FUNÇÃO CONVENIENTE PARA USO RÁPIDO
# -----------------------------------------------

def get_config() -> ConfigLoader:
    """Obter instância do carregador de config"""
    return ConfigLoader.get_instance()


def get_settings() -> SystemConfig:
    """Obter configurações tipadas diretamente"""
    return ConfigLoader.get_instance().config


# -----------------------------------------------
# TESTE RÁPIDO
# -----------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("⚙️  CONFIG LOADER - TESTE")
    print("=" * 70 + "\n")
    
    # Carregar config
    loader = get_config()
    settings = get_settings()
    
    print(f"Sistema: {settings.name} v{settings.version}")
    print(f"Ambiente: {settings.environment}")
    print(f"Usuário: {settings.user_name} ({settings.user_email})")
    print(f"Timezone: {settings.timezone}")
    print(f"\nLex Flow URL: {settings.lex_flow_base_url}")
    print(f"DB Type: {settings.db_type}")
    print(f"DB Path: {settings.db_sqlite_path}")
    print(f"Telegram: {'✅ Ativado' if settings.telegram_enabled else '❌ Desativado'}")
    print(f"AI Provider: {settings.ai_primary_provider} ({settings.ai_primary_model})")
    print(f"\nLog Level: {settings.log_level}")
    print(f"Log File: {settings.log_file_path}")
    
    print("\n" + "=" * 70)
    print("✅ CONFIG LOADER FUNCIONANDO!")
    print("=" * 70 + "\n")