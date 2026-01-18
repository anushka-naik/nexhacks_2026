#!/bin/bash

# Second Brain Demo - Pre-flight Check
# Verifies all dependencies and configurations are ready

echo "🔍 Second Brain Demo - Pre-flight Check"
echo "========================================"
echo ""

ERRORS=0

# Check Python
echo -n "✓ Checking Python... "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo "Found $PYTHON_VERSION"
else
    echo "❌ Python 3 not found"
    ERRORS=$((ERRORS + 1))
fi

# Check Node.js
echo -n "✓ Checking Node.js... "
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "Found $NODE_VERSION"
else
    echo "❌ Node.js not found"
    ERRORS=$((ERRORS + 1))
fi

# Check npm
echo -n "✓ Checking npm... "
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "Found v$NPM_VERSION"
else
    echo "❌ npm not found"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# Check backend dependencies
echo "📦 Checking Backend Dependencies..."
cd backend

if [ -f "requirements.txt" ]; then
    echo -n "  • Flask... "
    if python3 -c "import flask" 2>/dev/null; then
        echo "✓"
    else
        echo "❌ (run: pip install flask)"
        ERRORS=$((ERRORS + 1))
    fi

    echo -n "  • Neo4j Driver... "
    if python3 -c "import neo4j" 2>/dev/null; then
        echo "✓"
    else
        echo "❌ (run: pip install neo4j)"
        ERRORS=$((ERRORS + 1))
    fi

    echo -n "  • Token Company SDK... "
    if python3 -c "import tokenc" 2>/dev/null; then
        echo "✓"
    else
        echo "❌ (run: pip install tokenc)"
        ERRORS=$((ERRORS + 1))
    fi

    echo -n "  • Sentence Transformers... "
    if python3 -c "import sentence_transformers" 2>/dev/null; then
        echo "✓"
    else
        echo "❌ (run: pip install sentence-transformers)"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "❌ requirements.txt not found"
    ERRORS=$((ERRORS + 1))
fi

# Check .env file
echo -n "  • .env configuration... "
if [ -f ".env" ]; then
    if grep -q "TOKENC_API_KEY" .env && grep -q "NEO4J_URI" .env; then
        echo "✓"
    else
        echo "⚠️  Missing keys in .env"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "❌ .env file missing"
    ERRORS=$((ERRORS + 1))
fi

cd ..

echo ""

# Check frontend dependencies
echo "📦 Checking Frontend Dependencies..."
if [ -f "package.json" ]; then
    echo -n "  • node_modules... "
    if [ -d "node_modules" ]; then
        echo "✓"
    else
        echo "❌ (run: npm install)"
        ERRORS=$((ERRORS + 1))
    fi

    echo -n "  • Overshoot SDK... "
    if [ -d "node_modules/@overshoot" ]; then
        echo "✓"
    else
        echo "❌ (run: npm install)"
        ERRORS=$((ERRORS + 1))
    fi

    echo -n "  • Vite... "
    if [ -d "node_modules/vite" ]; then
        echo "✓"
    else
        echo "❌ (run: npm install)"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "❌ package.json not found"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# Check ports
echo "🔌 Checking Ports..."
echo -n "  • Port 5000 (Backend)... "
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Already in use (kill existing process)"
else
    echo "✓ Available"
fi

echo -n "  • Port 5173 (Frontend)... "
if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Already in use (kill existing process)"
else
    echo "✓ Available"
fi

echo ""
echo "========================================"

if [ $ERRORS -eq 0 ]; then
    echo "✅ All checks passed! Ready for demo."
    echo ""
    echo "To start demo:"
    echo "  ./start-demo.sh"
    echo ""
    echo "Or manually:"
    echo "  Terminal 1: cd backend && python app.py"
    echo "  Terminal 2: npm run dev"
    exit 0
else
    echo "❌ Found $ERRORS issue(s). Please fix before demo."
    echo ""
    echo "Quick fix:"
    echo "  cd backend && pip install -r requirements.txt"
    echo "  cd .. && npm install"
    exit 1
fi
