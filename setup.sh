#!/bin/bash
echo "🚀 Setting up KAGE OS..."
mkdir -p ~/.kage/memories
pip install -r requirements.txt
echo ""
echo "⚠️  Set environment variables in .env file:"
echo "  TELEGRAM_BOT_TOKEN=your_token"
echo "  KAGE_LLM_PROVIDER=groq"
echo "  KAGE_LLM_API_KEY=your_key"
echo ""
echo "✅ Setup complete. Run: python kage_cli.py start"
