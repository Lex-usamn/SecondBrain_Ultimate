#!/usr/bin/env python3
"""
Daily Briefing Script - Seu Briefing Matinal Automático
=========================================================

Gera e exibe seu briefing diário completo com:
- Top 3 prioridades
- Status dos projetos
- Inbox pendente
- Insights e motivação
- Sugestão do que fazer agora

Uso:
    python scripts/daily_briefing.py              # Briefing completo
    python scripts/daily_briefing.py --json       # Saída em JSON
    python scripts/daily_briefing.py --quiet      # Só essencial

Autor: Second Brain Ultimate System
"""

import sys
import os
import json
import argparse

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.core_engine import SecondBrainEngine, create_engine


def main():
    parser = argparse.ArgumentParser(description='Daily Briefing - Second Brain Ultimate')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--quiet', action='store_true', help='Only show essential info')
    parser.add_argument('--vault', default='./', help='Path to Obsidian vault')
    args = parser.parse_args()
    
    print("🌅 Iniciando Daily Briefing...\n")
    
    # Criar e inicializar engine
    engine = SecondBrainEngine(vault_path=args.vault)
    
    if not engine.initialize():
        print("❌ Falha ao inicializar Second Brain Engine")
        sys.exit(1)
    
    # Gerar briefing
    briefing = engine.get_daily_briefing()
    
    if args.json:
        # Saída JSON
        print(json.dumps(briefing.to_dict(), indent=2, ensure_ascii=False))
    else:
        # Saída formatada (Markdown)
        print(briefing.to_markdown())
        
        if not args.quiet:
            print("\n" + "=" * 70)
            suggestion = engine.what_should_i_do_now()
            print(f"\n💭 **SUGESTÃO IMEDIATA:** {suggestion['action']}")
            print(f"   📊 Por quê: {suggestion['reasoning']}")
            print(f"   ⚡ Esforço: {suggestion['effort']} | Impacto: {suggestion['impact']}")
            print("=" * 70)


if __name__ == "__main__":
    main()