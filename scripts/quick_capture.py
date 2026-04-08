#!/usr/bin/env python3
"""
Quick Capture Script - Captura Ultra-Rápida via CLI
====================================================

Captura ideias, notas e pensamentos instantaneamente
no seu Second Brain.

Uso:
    python scripts/quick_capture.py "Minha ideia aqui"
    python scripts/quick_capture.py "Idea" --tags video,youtube --source telegram
    echo "Minha ideia" | python scripts/quick_capture.py -

Autor: Second Brain Ultimate System
"""

import sys
import os
import argparse

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.core_engine import SecondBrainEngine


def main():
    parser = argparse.ArgumentParser(description='Quick Capture - Second Brain Ultimate')
    parser.add_argument('content', help='Content to capture (or "-" for stdin)')
    parser.add_argument('--tags', nargs='*', default=[], help='Tags for the capture')
    parser.add_argument('--source', default='cli', help='Source of capture')
    parser.add_argument('--vault', default='./', help='Path to Obsidian vault')
    args = parser.parse_args()
    
    # Ler do stdin se "-"
    if args.content == '-':
        content = sys.stdin.read().strip()
    else:
        content = args.content
    
    if not content.strip():
        print("❌ Content cannot be empty")
        sys.exit(1)
    
    # Criar engine
    engine = SecondBrainEngine(vault_path=args.vault)
    
    if not engine.initialize():
        print("❌ Failed to initialize engine")
        sys.exit(1)
    
    # Capturar
    result = engine.quick_capture(
        content=content,
        source=args.source,
        tags=args.tags
    )
    
    if result['success']:
        print(f"✅ Captured successfully!")
        print(f"   ID: {result['item_id']}")
        print(f"   Project: {result.get('suggested_project', 'Inbox')}")
        if result.get('ai_enriched'):
            print(f"   🤖 AI-enriched: Yes")
    else:
        print(f"❌ Capture failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()