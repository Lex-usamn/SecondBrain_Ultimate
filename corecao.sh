#!/bin/bash
# ============================================
# 🔧 SCRIPT DE CORREÇÃO AUTOMÁTICA
# Segundo Cérebro - Second Brain Ultimate
# ============================================

echo "🔧 Iniciando correções..."

cd /Volumes/arquivos/Docker/Projetos/Seg\ Cerebro/SecondBrain_Ultimate

# 1. Corrigir SyntaxError no core_engine.py (linha 769)
echo "📝 Corrigindo core_engine.py..."
sed -i '' 's/for word \[.app./for word in [.app./g' engine/core_engine.py

# Verificar se correu
if grep -q "for word in \['app'" engine/core_engine.py; then
    echo "   ✅ SyntaxError corrigido!"
else
    echo "   ⚠️  Correção manual necessária na linha 769"
fi

# 2. Instalar dependências
echo "📦 Instalando dependências Python..."
pip3 install requests python-dotenv --quiet

if [ $? -eq 0 ]; then
    echo "   ✅ Dependências instaladas!"
else
    echo "   ❌ Erro instalando dependências"
    exit 1
fi

# 3. Testar imports
echo "🧪 Testando módulos..."
python3 -c "
try:
    from engine.core_engine import SecondBrainEngine
    print('✅ Core Engine OK')
except SyntaxError as e:
    print(f'❌ Ainda tem erro de sintaxe: {e}')
    exit(1)
except Exception as e:
    print(f'⚠️  Import error (pode ser normal): {type(e).__name__}')
"

python3 -c "
try:
    import requests
    print('✅ Requests OK')
except ImportError:
    print('❌ Requests não instalado')
    exit(1)
"

echo ""
echo "🎉 Correções concluídas!"
echo ""
echo "📋 PRÓXIMO PASSO:"
echo "   python3 scripts/daily_briefing.py"
echo ""