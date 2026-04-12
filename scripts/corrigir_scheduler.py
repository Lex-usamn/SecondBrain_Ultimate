"""
🔧 CORREÇÃO AUTOMÁTICA - scheduler.py TYPE_CHECKING BUG
=========================================================

Este script corrige todos os type hints que estão causando NameError
por usarem classes importadas via TYPE_CHECKING sem aspas.

Execute este script NA PASTA RAIZ do projeto!
"""

import re
import sys
from pathlib import Path

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

ARQUIVO_ALVO = Path("engine/scheduler.py")

# Padrões de type hints que precisam de aspas (classes importadas via TYPE_CHECKING)
PADROES_CORRIGIR = [
    # Formato: (padrão_regex, substituição)
    (r'Optional\[MemorySystem\]', 'Optional["MemorySystem"]'),
    (r'Optional\[InsightGenerator\]', 'Optional["InsightGenerator"]'),
    (r'Optional\[LexFlowClient\]', 'Optional["LexFlowClient"]'),
    (r'Optional\[CoreEngine\]', 'Optional["CoreEngine"]'),
    (r'"SchedulerSystem"', '"SchedulerSystem"'),  # Já está correto
    (r'List\[Insight\]', 'List["Insight"]'),
    (r'List\[WeeklySummary\]', 'List["WeeklySummary"]'),
    (r'Dict\[str, Any\]', 'Dict[str, Any]'),  # Built-in, não precisa aspas
]

# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def corrigir_scheduler():
    """
    Corrige automaticamente todos os type hints no scheduler.py
    que estão faltando aspas (forward references).
    """
    
    print("=" * 70)
    print("🔧 CORREÇÃO AUTOMÁTICA - engine/scheduler.py")
    print("=" * 70)
    
    # Verificar se arquivo existe
    if not ARQUIVO_ALVO.exists():
        print(f"❌ ERRO: Arquivo não encontrado: {ARQUIVO_ALVO}")
        print(f"   Execute este script na pasta raiz do projeto!")
        return False
    
    # Ler conteúdo atual
    print(f"\n📂 Lendo arquivo: {ARQUIVO_ALVO}")
    try:
        conteudo = ARQUIVO_ALVO.read_text(encoding="utf-8")
        linhas = conteudo.split('\n')
    except Exception as e:
        print(f"❌ ERRO ao ler arquivo: {e}")
        return False
    
    print(f"   ✅ Arquivo lido ({len(linhas)} linhas)")
    
    # ========================================================================
    # ANÁLISE E CORREÇÃO
    # ========================================================================
    
    correcoes_feitas = []
    novo_conteudo_lista = []
    total_correcoes = 0
    
    for linha_num, linha in enumerate(linhas, 1):
        linha_original = linha
        linha_modificada = linha
        
        # Verificar cada padrão
        for padrao_regex, substituicao in PADROES_CORRIGIR:
            if re.search(padrao_regex, linha_modificada):
                # Aplicar a substituição
                nova_linha = re.sub(padrao_regex, substituicao, linha_modificada)
                
                if nova_linha != linha_modificada:
                    # Registrar o que foi alterado antes de atualizar a linha modificada
                    match_original = re.search(padrao_regex, linha_original)
                    if match_original:
                        # CORREÇÃO DO BUG: Removido re.search desnecessário que causava o NameError
                        # e corrigida a variável 'substituicao'
                        correcoes_feitas.append({
                            'linha': linha_num,
                            'original': match_original.group(),
                            'corrigido': substituicao
                        })
                        total_correcoes += 1
                    
                    linha_modificada = nova_linha
        
        novo_conteudo_lista.append(linha_modificada)
    
    # Unir as linhas novamente
    novo_conteudo = '\n'.join(novo_conteudo_lista)
    
    # ========================================================================
    # RELATÓRIO
    # ========================================================================
    
    print("\n" + "=" * 70)
    print("📊 RELATÓRIO DE CORREÇÕES")
    print("=" * 70)
    
    if total_correcoes == 0:
        print("\n✅ NENHUMA CORREÇÃO NECESSÁRIA!")
        print("   O arquivo já está com os type hints corretos.")
        return True
    
    print(f"\n🔍 Total de correções: {total_correcoes}")
    print("\nDetalhes:")
    print("-" * 70)
    
    for correcao in correcoes_feitas:
        print(f"   Linha {correcao['linha']:4d}: {correcao['original']:<30} → {correcao['corrigido']}")
    
    # ========================================================================
    # APLICAR CORREÇÕES (COM BACKUP!)
    # ========================================================================
    
    print("\n" + "=" * 70)
    print("💾 APLICANDO CORREÇÕES...")
    print("=" * 70)
    
    # Criar backup
    backup_file = ARQUIVO_ALVO.with_suffix('.py.backup')
    try:
        backup_file.write_text(conteudo, encoding="utf-8")
        print(f"\n✅ Backup criado: {backup_file}")
        
        # Escrever arquivo corrigido
        ARQUIVO_ALVO.write_text(novo_conteudo, encoding="utf-8")
        print(f"✅ Arquivo corrigido: {ARQUIVO_ALVO}")
    except Exception as e:
        print(f"❌ ERRO ao gravar arquivos: {e}")
        return False
    
    # ========================================================================
    # VALIDAÇÃO BÁSICA
    # ========================================================================
    
    print("\n" + "=" * 70)
    print("✅ VALIDAÇÃO")
    print("=" * 70)
    
    try:
        # Tentar compilar o arquivo corrigido para checar sintaxe
        compile(novo_conteudo, str(ARQUIVO_ALVO), 'exec')
        print("\n✅ SUCESSO! Arquivo sintaticamente correto.")
        print("\n🚀 Agora você pode executar:")
        print("   python iniciar_scheduler.py")
        return True
        
    except SyntaxError as e:
        print(f"\n❌ ERRO DE SINTAXE após correção: {e}")
        print("\n⚠️  Restaurando backup...")
        ARQUIVO_ALVO.write_text(conteudo, encoding="utf-8")
        print("   ✅ Backup restaurado.")
        return False

# ============================================================================
# EXECUÇÃO
# ============================================================================

if __name__ == "__main__":
    try:
        sucesso = corrigir_scheduler()
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        sucesso = False
    
    print("\n" + "=" * 70)
    if sucesso:
        print("🎉 CORREÇÃO CONCLUÍDA COM SUCESSO!")
    else:
        print("❌ FALHA NA CORREÇÃO - Verifique os logs acima")
    print("=" * 70)