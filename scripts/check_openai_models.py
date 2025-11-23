#!/usr/bin/env python3
"""Check available OpenAI models for current API key."""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

print("🔍 Checking available OpenAI models...")
print("=" * 60)

try:
    models = client.models.list()

    # Filter for chat models
    chat_models = [m for m in models.data if 'gpt' in m.id.lower()]

    print(f"\n📋 Available GPT models ({len(chat_models)}):\n")
    for model in sorted(chat_models, key=lambda x: x.id):
        print(f"   - {model.id}")

    print("\n" + "=" * 60)

except Exception as e:
    print(f"❌ Error: {e}")
