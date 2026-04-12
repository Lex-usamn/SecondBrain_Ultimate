"""
==============================================================================
ENGINE PACKAGE - Pacote Principal do Motor do Lex-Brain Hybrid
==============================================================================

Este pacote contém todos os módulos centrais do sistema.

⚠️ IMPORTANTE: Não importamos as classes aqui para evitar circular imports!
   Importe diretamente dos módulos:
   - from engine.core_engine import CoreEngine
   - from engine.rag_system import RAGSystem
   - etc.

Autor: Lex-Brain Hybrid
Versão: v2.1 (com RAG - sem circular imports)
==============================================================================
"""

__version__ = "2.1.0"
__author__ = "Lex-Brain Hybrid"

# Metadados do pacote
__all__ = [
    "CoreEngine",
    "CaptureSystem", 
    "DecisionEngine",
    "MemorySystem",
    "AutomationSystem",
    "InsightGenerator",
    "SchedulerSystem",
    "RAGSystem",
]