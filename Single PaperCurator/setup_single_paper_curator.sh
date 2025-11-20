#!/bin/bash
# Single Paper Curator - 빠른 설정 스크립트

echo "=================================================="
echo "  Single Paper Curator - Quick Setup"
echo "=================================================="
echo ""

# 1. .streamlit 폴더 생성
echo "📁 Creating .streamlit directory..."
mkdir -p .streamlit

# 2. secrets.toml 템플릿 생성
echo "📝 Creating secrets template..."
cat > .streamlit/secrets.toml << 'EOF'
# Single Paper Curator - Secrets Configuration
# 아래 값들을 실제 API 키로 교체하세요

NOTION_TOKEN = "your_notion_integration_token_here"
PAPERS_DATABASE_ID = "your_papers_database_id_here"
GEMINI_API_KEY = "your_gemini_api_key_here"
EOF

echo "✅ Template created at .streamlit/secrets.toml"
echo ""

# 3. .gitignore 업데이트
echo "🔒 Updating .gitignore..."
if ! grep -q ".streamlit/secrets.toml" .gitignore 2>/dev/null; then
    echo ".streamlit/secrets.toml" >> .gitignore
    echo "✅ Added .streamlit/secrets.toml to .gitignore"
else
    echo "✅ .streamlit/secrets.toml already in .gitignore"
fi

echo ""
echo "=================================================="
echo "  Setup Complete!"
echo "=================================================="
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Edit .streamlit/secrets.toml with your API keys:"
echo "   - NOTION_TOKEN: Get from https://www.notion.so/my-integrations"
echo "   - PAPERS_DATABASE_ID: Your Notion Papers Database ID"
echo "   - GEMINI_API_KEY: Get from https://makersuite.google.com/app/apikey"
echo ""
echo "2. Install dependencies (if not already installed):"
echo "   pip install -r requirements.txt"
echo ""
echo "3. Run the app:"
echo "   streamlit run single_paper_curator.py"
echo ""
echo "=================================================="
