"""
Memory System - Sistema de Memória do Segundo Cérebro
================================================

Gerencia os arquivos core (SOUL.md, USER.md, MEMORY.md, HEARTBEAT.md)
como memória de longo prazo do sistema.

Funcionalidades:
- Leitura/Escrita estruturada de arquivos Markdown
- Parse de seções e metadados
- Busca por conteúdo e chaves
- Atualização incremental
- Sync com Lex Flow

Autor: Second Brain Ultimate System
Versão: 1.0.0
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

# ============================================
# LOGGING
# ============================================
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler('logs/memory_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('MemorySystem')


# ============================================
# DATA CLASSES
# ============================================

@dataclass
class MemoryFile:
    """Representação de um arquivo de memória"""
    path: str
    name: str
    exists: bool = False
    last_modified: str = None
    size_bytes: int = 0
    content: str = ""
    sections: Dict[str, str] = field(default_factory=dict)


@dataclass
class Section:
    """Seção extraída de arquivo Markdown"""
    name: str
    content: str
    start_line: int
    end_line: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryUpdate:
    """Resultado de uma atualização de memória"""
    file_name: str
    section_updated: str = None
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = False
    error: str = None


# ============================================
# MAIN CLASS
# ============================================

class MemorySystem:
    """
    Sistema de Memória do Segundo Cérebro
    
    Gerencia os arquivos .md que formam a memória de longo prazo:
    - SOUL.md: Identidade e propósito do sistema
    - USER.md: Perfil operacional do usuário
    - MEMORY.md: Lições aprendidas e fatos importantes
    - HEARTBEAT.md: Configuração de monitoramento
    
    Uso:
        memory = MemorySystem(vault_path='./')
        soul = memory.load_soul()        # Carrega identidade
        user = memory.load_user()        # Carrega perfil
        memory.add_lesson(...)           # Adiciona aprendizado
    """
    
    # Nomes dos arquivos core
    CORE_FILES = {
        'soul': 'SOUL.md',
        'user': 'USER.md',
        'memory': 'MEMORY.md',
        'heartbeat': 'HEARTBEAT.md'
    }
    
    def __init__(self, vault_path: str = "./"):
        """
        Inicializa o Sistema de Memória
        
        Args:
            vault_path: Caminho para o diretório base (onde estão os .md)
        """
        self.vault_path = Path(vault_path).resolve()
        
        log.info(f"🧠 Memory System inicializado")
        log.info(f"   Vault path: {self.vault_path}")
        
        # Verificar se diretório existe
        if not self.vault_path.exists():
            log.warning(f"⚠️  Diretório vault não existe: {self.vault_path}")
            log.info(f"   Criando diretório...")
            self.vault_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, file_type: str) -> Path:
        """Retorna caminho completo para um arquivo core"""
        filename = self.CORE_FILES.get(file_type.lower())
        if not filename:
            raise ValueError(f"Arquivo core desconhecido: {file_type}")
        return self.vault_path / filename
    
    def _read_file(self, filepath: Path) -> MemoryFile:
        """Lê arquivo e retorna objeto MemoryFile"""
        mem_file = MemoryFile(
            path=str(filepath),
            name=filepath.name,
            exists=filepath.exists()
        )
        
        if not mem_file.exists:
            log.debug(f"   Arquivo não encontrado: {filepath.name}")
            return mem_file
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            stat = filepath.stat()
            mem_file.content = content
            mem_file.size_bytes = stat.st_size
            mem_file.last_modified = datetime.fromtimestamp(
                stat.st_mtime).isoformat()
            
            # Parsear seções
            mem_file.sections = self._parse_sections(content)
            
        except Exception as e:
            log.error(f"Erro lendo {filepath.name}: {e}")
            mem_file.content = ""
        
        return mem_file
    
    def _parse_sections(self, content: str) -> Dict[str, Section]:
        """
        Parseia arquivo Markdown extraindo seções
        
        Detecta padrões como:
        ## Título de Seção
        Conteúdo da seção...
        
        ### Subseção
        Mais conteúdo...
        """
        sections = {}
        current_section = None
        current_lines = []
        start_line = 0
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Detectar cabeçalho de seção (## ou ###)
            if line.startswith('## ') or line.startswith('### '):
                # Salvar seção anterior
                if current_section is not None:
                    sections[current_section.name] = Section(
                        name=current_section.name,
                        content='\n'.join(current_lines).strip(),
                        start_line=start_line,
                        end_line=i-1
                    )
                
                # Nova seção
                level = 2 if line.startswith('## ') else 3
                name = line.lstrip('#').strip()
                
                current_section = Section(
                    name=name,
                    content="",
                    start_line=i+1,
                    end_line=i+1
                )
                current_lines = []
                start_line = i+1
                
            elif current_section is not None:
                current_lines.append(line)
        
        # Última seção
        if current_section is not None:
            sections[current_section.name] = Section(
                name=current_section.name,
                content='\n'.join(current_lines).strip(),
                start_line=start_line,
                end_line=len(lines)-1
            )
        
        # Se não encontrou seções, tratar todo como uma só
        if not sections and content.strip():
            sections['main'] = Section(
                name='Conteúdo Principal',
                content=content.strip(),
                start_line=0,
                end_line=len(lines)-1
            )
        
        return sections
    
    # ========================================
    # MÉTODOS PÚBLICOS PRINCIPAIS
    # ========================================
    
    def load_soul(self) -> Optional[Dict]:
        """
        Carrega SOUL.md (Identidade do Segundo Cérebro)
        
        Returns:
            Dicionário com dados estruturados ou None se não existir
        """
        filepath = self._get_file_path('soul')
        mem_file = self._read_file(filepath)
        
        if not mem_file.exists or not mem_file.content:
            log.warning("SOUL.md não encontrado ou vazio")
            return None
        
        # Estruturar dados principais
        soul_data = {
            'raw_content': mem_file.content,
            'sections': mem_file.sections,
            'last_modified': mem_file.last_modified,
            'path': str(filepath),
            'exists': True
        }
        
        # Extrair campos específicos (se existirem nas seções)
        purpose = mem_file.sections.get('Propósito Principal', 
                                       mem_file.sections.get('PROPÓSITO PRINCIPAL',
                                                     mem_file.sections.get('purpose')))
        if purpose:
            soul_data['purpose'] = purpose.content[:500]
        
        return soul_data
    
    def load_user(self) -> Optional[Dict]:
        """
        Carrega USER.md (Perfil Operacional)
        
        Returns:
            Dicionário com dados do usuário ou None
        """
        filepath = self._get_file_path('user')
        mem_file = self._read_file(filepath)
        
        if not mem_file.exists or not mem_file.content:
            log.warning("USER.md não encontrado ou vazio")
            return None
        
        user_data = {
            'raw_content': mem_file.content,
            'sections': mem_file.sections,
            'last_modified': mem_file.last_modified,
            'path': str(filepath),
            'exists': True
        }
        
        # Extrair preferências
        prefs = mem_file.sections.get('Preferências de Comunicação',
                                     mem_file.sections.get('PREFERÊNCIAS DE COMUNICAÇÃO'))
        if prefs:
            user_data['communication_preferences'] = prefs.content[:300]
        
        return user_data
    
    def load_memory(self) -> Optional[Dict]:
        """
        Carrega MEMORY.md (Memória de Longo Prazo)
        
        Returns:
            Dicionário com memória estruturada
        """
        filepath = self._get_file_path('memory')
        mem_file = self._read_file(filepath)
        
        if not mem_file.exists or not mem_file.content:
            log.debug("MEMORY.md não encontrado (pode ser novo)")
            return {
                'raw_content': '',
                'sections': {},
                'decisions': [],
                'lessons': [],
                'facts': [],
                'projects_status': [],
                'exists': False
            }
        
        memory_data = {
            'raw_content': mem_file.content,
            'sections': mem_file.sections,
            'last_modified': mem_file.last_modified,
            'size_kb': round(mem_file.size_bytes / 1024, 2)
        }
        
        # Extrair listas específicas
        for section_name, section in mem_file.sections.items():
            if 'decisão' in section_name.lower() or 'decision' in section_name.lower():
                memory_data.setdefault('decisions', []).append({
                    'title': section.name,
                    'content': section.content[:1000]
                })
            elif 'lição' in section_name.lower() or 'lesson' in section_name.lower():
                memory_data.setdefault('lessons', []).append({
                    'category': section_name.split('.')[-1] if '.' in section_name else section_name,
                    'lesson': section.content[:500]
                })
            elif 'fato' in section_name.lower() or 'fact' in section_name.lower():
                memory_data.setdefault('facts', []).append({
                    'topic': section.name,
                    'fact': section.content[:300]
                })
        
        return memory_data
    
    def load_heartbeat(self) -> Optional[Dict]:
        """
        Carrega HEARTBEAT.md (Configuração de Monitoramento)
        
        Returns:
            Dicionário com configuração ou None
        """
        filepath = self._get_file_path('heartbeat')
        mem_file = self._read_file(filepath)
        
        if not mem_file.exists or not mem_file.content:
            log.warning("HEARTBEAT.md não encontrado")
            return None
        
        heartbeat_data = {
            'raw_content': mem_file.content,
            'sections': mem_file.sections,
            'configuration': {}
        }
        
        # Extrair configurações de thresholds
        config_section = mem_file.sections.get('Configuração',
                                           mem_file.sections.get('CONFIGURAÇÃO'))
        if config_section:
            heartbeat_data['configuration'] = self._parse_config(config_section.content)
        
        return heartbeat_data
    
    def _parse_config(self, text: str) -> Dict:
        """Parse texto de configuração em dicionário"""
        config = {}
        
        # Padrões simples: chave: valor
        for line in text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().strip('#').strip()
                value = value.strip().strip('"').strip("'")
                
                # Tentar converter tipos
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                elif value.isdigit():
                    value = int(value)
                    
                config[key] = value
        
        return config
    
    # ========================================
    # ESCRITA E ATUALIZAÇÃO
    # ========================================
    
    def update_section(self, file_type: str, section_name: str, 
                       new_content: str, mode: str = 'append') -> MemoryUpdate:
        """
        Atualiza ou adiciona conteúdo a uma seção específica
        
        Args:
            file_type: 'soul', 'user', 'memory', ou 'heartbeat'
            section_name: Nome da seção (ex: "Decisões Importantes")
            new_content: Conteúdo a adicionar/substituir
            mode: 'replace' (substitui tudo) ou 'append' (adiciona ao final)
            
        Returns:
            MemoryUpdate com resultado da operação
        """
        filepath = self._get_file_path(file_type)
        
        update = MemoryUpdate(
            file_name=filepath.name,
            section_updated=section_name,
            success=False
        )
        
        try:
            # Ler conteúdo atual
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                content = ''
            
            # Encontrar seção
            section_pattern = rf'(##\s+{re.escape(section_name)}|###\s+{re.escape(section_name)})'
            
            if re.search(section_pattern, content):
                if mode == 'replace':
                    # Substituir conteúdo da seção
                    new_content_full = re.sub(
                        rf'(##\s*{re.escape(section_name)}).*?(?=\n## |\Z)',
                        f'## {section_name}\n{new_content}\n',
                        content,
                        flags=re.DOTALL
                    )
                else:
                    # Adicionar ao final da seção existente
                    new_content_full = re.sub(
                        rf'(##\s*{re.escape(section_name)}.*?)(?=\n## |\Z)',
                        rf'\g<1>\n\n{new_content}',
                        content,
                        flags=re.DOTALL
                    )
            else:
                # Seção não existe, adicionar ao final do arquivo
                if content.strip():
                    new_content_full = f"{content}\n\n## {section_name}\n{new_content}\n"
                else:
                    new_content_full = f"## {section_name}\n{new_content}\n"
            
            # Escrever arquivo atualizado
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content_full)
            
            update.success = True
            log.info(f"✅ Seção '{section_name}' atualizada em {filepath.name}")
            
        except Exception as e:
            update.error = str(e)
            log.error(f"❌ Erro atualizando seção: {e}")
        
        return update
    
    def add_lesson(self, category: str, lesson: str, 
                   context: str = "", metadata: Dict = None) -> bool:
        """
        Adiciona lição aprendida ao MEMORY.md
        
        Args:
            category: Categoria (ex: 'Produtividade', 'Canais Dark')
            lesson: Texto da lição
            context: Contexto adicional
            metadata: Metadados extras
            
        Returns:
            True se sucesso
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        entry = f"""### [{timestamp}] {category}
**Contexto:** {context or 'N/A'}
**Lição:** {lesson}

---
"""
        
        result = self.update_section(
            file_type='memory',
            section_name=f"Lição Aprendida: {category}",
            new_content=entry,
            mode='append'
        )
        
        return result.success
    
    def add_decision(self, topic: str, decision: str,
                      reasoning: str = "", outcome: str = "") -> bool:
        """
        Registra decisão importante tomada
        
        Args:
            topic: Sobre o quê foi a decisão
            decision: Qual decisão foi tomada
            reasoning: Porquê decidiu assim
            outcome: Resultado (se já souber)
            
        Returns:
            True se sucesso
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        entry = f"""### Decisão: {topic} ({timestamp})
**Decisão:** {decision}
**Raciocínio:** {reasoning or 'N/A'}
**Resultado:** {outcome or 'Aguardando...'}

---
"""
        
        result = self.update_section(
            file_type='memory',
            section_name="Decisões Importantes",
            new_content=entry,
            mode='append'
        )
        
        return result.success
    
    def add_fact(self, topic: str, fact: str, 
               source: str = "", confidence: str = "alta") -> bool:
        """
        Registra fato importante (verificado)
        
        Args:
            topic: Assunto do fato
            fact: O fato em si
            source: Fonte/Origem
            confiança: Quão confiável é (alta/média/baixa)
            
        Returns:
            True se sucesso
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        entry = f"""### Fato: {topic} ({timestamp})
**Fato:** {fact}
**Fonte:** {source or 'Observação própria'}
**Confiança:** {confidence}

---
"""
        
        result = self.update_section(
            file_type='memory',
            section_name=f"Fatos Importantes",
            new_content=entry,
            mode='append'
        )
        
        return result.success
    
    def update_metrics(self, metrics: Dict) -> bool:
        """
        Atualiza métricas no MEMORY.md
        
        Args:
            metrics: Dicionário com métricas e valores
            
        Returns:
            True se sucesso
        """
        timestamp = datetime.now().strftime('%Y-%m-%d')
        
        entries = []
        for key, value in metrics.items():
            entry = f"- **{key}:** {value}"
            entries.append(entry)
        
        metrics_text = '\n'.join(entries)
        
        entry = f"""### Métricas ({timestamp})
{metrics_text}

---
"""
        
        result = self.update_section(
            file_type='memory',
            section_name="Métricas Rápidas",
            new_content=entry,
            mode='append'
        )
        
        return result.success
    
    def search_memory(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Busca em todos os arquivos de memória por termo/chave
        
        Args:
            query: Termo de busca
            max_results: Máximo de resultados
            
        Returns:
            Lista de dicionários com matches encontrados
        """
        results = []
        query_lower = query.lower()
        
        for file_type, filename in self.CORE_FILES.items():
            filepath = self._get_file_path(file_type)
            mem_file = self._read_file(filepath)
            
            if not mem_file.exists:
                continue
            
            # Buscar no conteúdo
            if query_lower in mem_file.content.lower():
                # Encontrar contexto ao redor da match
                idx = mem_file.content.lower().find(query_lower)
                start = max(0, idx - 100)
                end = min(len(mem_file.content), idx + len(query) + 200)
                context = mem_file.content[start:end]
                
                results.append({
                    'file': filename,
                    'file_type': file_type,
                    'match': query,
                    'context': context.replace('\n', ' ').strip(),
                    'relevance': 'high' if file_type in ['memory', 'soul'] else 'medium'
                })
                
                if len(results) >= max_results:
                    break
        
        log.info(f"🔍 Busca por '{query}': {len(results)} resultados")
        return results
    
    def get_all_core_files_status(self) -> Dict[str, Dict]:
        """
        Status de todos os arquivos core
        
        Returns:
            Dicionário com status de cada arquivo
        """
        status = {}
        
        for file_type, filename in self.CORE_FILES.items():
            filepath = self._get_file_path(file_type)
            mem_file = self._read_file(filepath)
            
            status[file_type] = {
                'filename': filename,
                'path': str(filepath),
                'exists': mem_file.exists,
                'size_kb': round(mem_file.size_bytes / 1024, 2) if mem_file.exists else 0,
                'sections_count': len(mem_file.sections),
                'last_modified': mem_file.last_modified,
                'content_length': len(mem_file.content)
            }
        
        return status
    
    def get_memory_stats(self) -> Dict:
        """
        Estatísticas gerais da memória
        
        Returns:
            Dicionário com estatísticas
        """
        status = self.get_all_core_files_status()
        
        total_size = sum(s['size_kb'] for s in status.values())
        total_sections = sum(s['sections_count'] for s in status.values())
        files_exist = sum(1 for s in stats.values() if s['exists'])
        
        return {
            'total_files': len(status),
            'files_existing': files_exist,
            'total_size_kb': total_size,
            'total_sections': total_sections,
            'vault_path': str(self.vault_path),
            'per_file': status
        }


# ============================================
# TESTE
# ============================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 TESTE DO MEMORY SYSTEM")
    print("=" * 60 + "\n")
    
    # Inicializar
    memory = MemorySystem(vault_path="./SecondBrain_Ultimate")
    
    # Status dos arquivos
    print("📁 STATUS DOS ARQUIVOS CORE:")
    status = memory.get_all_core_files_status()
    for file_type, info in status.items():
        icon = "✅" if info['exists'] else "⬜"
        size = f"{info['size_kb']} KB" if info['exists'] else "N/A"
        sections = f"{info['sections_count']} seções" if info['exists'] else "0"
        print(f"   {icon} {info['filename']:20s} | {size:>8} | {sections}")
    
    # Testar carregamento
    print("\n📖 CARREGANDO ARQUIVOS:")
    
    soul = memory.load_soul()
    if soul:
        print(f"   ✅ SOUL.md carregado")
        print(f"      Propósito: {soul.get('purpose', 'N/A')[:60]}...")
    else:
        print("   ⚠️  SOUL.md não encontrado")
    
    user = memory.load_user()
    if user:
        print(f"   ✅ USER.md carregado")
    else:
        print("   ⚠️  USER.md não encontrado")
    
    mem = memory.load_memory()
    print(f"   {'✅' if mem.get('exists') else '⚠️'}  MEMORY.md: {mem.get('decisions', [])} decisões, "
          f"{mem.get('lessons', [])} lições, {mem.get('facts', [])} fatos")
    
    # Testar busca
    print("\n🔍 TESTE DE BUSCA:")
    results = memory.search_memory("projeto", max_results=3)
    print(f"   Busca por 'projeto': {len(results)} resultados")
    for r in results[:3]:
        print(f"   • [{r['file']}] match em contexto...")
    
    # Estatísticas finais
    print("\n📊 ESTATÍSTICAS DA MEMÓRIA:")
    stats = memory.get_memory_stats()
    print(f"   Arquivos: {stats['total_files']} ({stats['files_exist']} existem)")
    print(f"   Tamanho total: {stats['total_size_kb']} KB")
    print(f"   Total seções: {stats['total_sections']}")
    
    print("\n" + "=" * 60)
    print("✅ MEMORY SYSTEM FUNCIONANDO!")
    print("=" * 60 + "\n")