#!/bin/bash

# ============================================
# Setup Script - Second Brain Ultimate
# ============================================
# Este script configura todo o ambiente automaticamente
# Autor: Second Brain System
# Data: 2025-06-17

echo "🚀 Iniciando setup do Second Brain Ultimate..."
echo "=============================================="

# Cores para output (se disponível)
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Função para printar status
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verificar se Python 3 está instalado
echo ""
echo "📋 Verificando Python 3..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Python encontrado: $PYTHON_VERSION"
else
    print_error "Python 3 não encontrado! Por favor instale primeiro."
    exit 1
fi

# Verificar se pip3 está instalado
echo ""
echo "📋 Verificando pip3..."
if command -v pip3 &> /dev/null; then
    print_success "pip3 encontrado"
else
    print_warning "pip3 não encontrado. Instalando..."
    python3 -m ensurepip --upgrade
    if [ $? -eq 0 ]; then
        print_success "pip3 instalado com sucesso"
    else
        print_error "Falha ao instalar pip3"
        exit 1
    fi
fi

# Criar estrutura de pastas (se não existir)
echo ""
echo "📁 Verificando estrutura de pastas..."
mkdir -p config
mkdir -p integrations
mkdir -p logs
mkdir -p skills
mkdir -p data/vector_store
print_success "Pastas criadas/verificadas"

# Verificar se requirements.txt existe
echo ""
echo "📋 Verificando requirements.txt..."
if [ -f "requirements.txt ]; then
    print_success "requirements.txt encontrado"
else
    print_warning "requirements.txt não encontrado. Criando..."
    cat > requirements.txt << 'EOF'
# Segundo Cérebro Ultimate - Dependências Python
requests>=2.31.0
python-dotenv>=1.0.0
python-dateutil>=2.8.2
colorlog>=6.7.0
EOF
    print_success "requirements.txt criado"
fi

# Criar ambiente virtual
echo ""
echo "🐍 Criando ambiente virtual Python..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        print_success "Ambiente virtual criado: venv/"
    else
        print_error "Falha ao criar ambiente virtual"
        exit 1
    fi
else
    print_warning "Ambiente virtual já existe (venv/)"
fi

# Ativar ambiente virtual e instalar dependências
echo ""
echo "📦 Instalando dependências Python..."
source venv/bin/activate

if [ -f "requirements.txt" ]; then
    pip3 install -q -r requirements.txt
    if [ $? -eq 0 ]; then
        print_success "Dependências instaladas com sucesso!"
    else
        print_error "Falha ao instalar algumas dependências"
        echo "   Tente manualmente: pip3 install requests python-dotenv"
    fi
else
    print_error "requirements.txt não encontrado"
    exit 1
fi

# Verificar/arquivo .env
echo ""
echo "🔐 Verificando configuração (.env)..."
if [ -f ".env" ]; then
    print_success ".env encontrado"
    
    # Verificar se tem token preenchido
    if grep -q "LEX_FLOW_TOKEN=" .env && grep -q "LEX_FLOW_TOKEN=$" .env; then
        print_warning ".env existe mas LEX_FLOW_TOKEN está vazio!"
        echo "   Edite o arquivo .env e preencha suas credenciais:"
        echo "   nano config/.env"
    else
        print_success "Configuração parece ok"
    fi
else
    print_warning ".env não encontrado"
    if [ -f "config/.env.example" ]; then
        echo "   Copiando de .env.example..."
        cp config/.env.example .env
        print_success ".env criado a partir do template"
        echo "   ⚠️  Lembre-se de editar e preencher suas credenciais!"
    fi
fi

# Criar pasta de logs se necessário
touch logs/.gitkeep 2>/dev/null || true

# Testar importação do módulo principal
echo ""
echo "🧪 Testando importação dos módulos..."
python3 << 'TEST_EOF'
try:
    import requests
    import json
    from datetime import datetime
    from dotenv import load_dotenv
    print("✅ Todos os imports básicos funcionaram!")
except ImportError as e:
    print(f"❌ Erro no import: {e}")
    exit(1)
TEST_EOF

if [ $? -eq 0 ]; then
    print_success "Teste de importação passou!"
else
    print_error "Teste de importação falhou"
fi

# Resumo final
echo ""
echo "=============================================="
echo "🎉 SETUP CONCLUÍDO!"
echo "=============================================="
echo ""
echo "Próximos passos:"
echo ""
echo "1️⃣  Ative o ambiente virtual (sempre que for usar):"
echo "    source venv/bin/activate"
echo ""
echo "2️⃣  Configure suas credenciais:"
echo "    nano .env"
echo "    (preencha LEX_FLOW_USERNAME e LEX_FLOW_PASSWORD)"
echo ""
echo "3️⃣  Teste a conexão com Lex Flow:"
echo "    python3 integrations/lex_flow_client.py"
echo ""
echo "4️⃣  Quando funcionar, desative o ambiente (opcional):"
echo "    deactivate"
echo ""
echo "=============================================="
echo "💡 Dica: Adicione ao seu ~/.zshrc ou ~/.bashrc:"
echo "    alias sb='cd /Volumes/arquivos/Docker/Projetos/Seg\\ Cerebro/SecondBrain_Ultimate && source venv/bin/activate'"
echo "    Assim basta digitar 'sb' para entrar no ambiente!"
echo "=============================================="