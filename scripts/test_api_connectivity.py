#!/usr/bin/env python3
"""Test API connectivity for all external services."""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env", override=True)

async def test_openai():
    """Test OpenAI API connectivity."""
    print("\n🔍 Testing OpenAI API...")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": "Say 'OK' only"}],
            max_completion_tokens=10
        )
        print(f"   ✅ OpenAI: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"   ❌ OpenAI Error: {e}")
        return False

async def test_anthropic():
    """Test Anthropic API connectivity."""
    print("\n🔍 Testing Anthropic API...")
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            # Latest fast Claude (Anthropic official model list)
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say 'OK' only"}]
        )
        print(f"   ✅ Anthropic: {response.content[0].text}")
        return True
    except Exception as e:
        print(f"   ❌ Anthropic Error: {e}")
        return False

async def test_gemini():
    """Test Google Gemini API connectivity."""
    print("\n🔍 Testing Google Gemini API...")
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        # Use a known working model for testing
        model_name = "gemini-2.5-flash"
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'OK' only")
        print(f"   ✅ Gemini ({model_name}): {response.text.strip()}")
        return True
    except Exception as e:
        print(f"   ❌ Gemini Error: {e}")
        return False

async def test_pinecone():
    """Test Pinecone connectivity."""
    print("\n🔍 Testing Pinecone...")
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        indexes = pc.list_indexes()
        index_names = [idx.name for idx in indexes]
        print(f"   ✅ Pinecone: Connected, indexes: {index_names}")
        return True
    except Exception as e:
        print(f"   ❌ Pinecone Error: {e}")
        return False

async def test_voyage():
    """Test Voyage AI embeddings."""
    print("\n🔍 Testing Voyage AI Embeddings...")
    try:
        import httpx
        response = httpx.post(
            "https://api.voyageai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {os.getenv('VOYAGE_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "input": "test",
                "model": "voyage-3-lite"
            },
            timeout=30
        )
        if response.status_code == 200:
            print(f"   ✅ Voyage AI: Connected")
            return True
        else:
            print(f"   ❌ Voyage AI: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Voyage AI Error: {e}")
        return False

async def test_brave_search():
    """Test Brave Search API."""
    print("\n🔍 Testing Brave Search API...")
    try:
        import httpx
        response = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "X-Subscription-Token": os.getenv("BRAVE_API_KEY"),
                "Accept": "application/json"
            },
            params={"q": "test", "count": 1},
            timeout=30
        )
        if response.status_code == 200:
            print(f"   ✅ Brave Search: Connected")
            return True
        else:
            print(f"   ❌ Brave Search: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Brave Search Error: {e}")
        return False

async def test_supadata():
    """Test Supadata MCP API."""
    print("\n🔍 Testing Supadata MCP...")
    try:
        import httpx
        # Test with a simple URL fetch
        response = httpx.get(
            "https://api.supadata.ai/v1/youtube/transcript",
            headers={
                "x-api-key": os.getenv("SUPADATA_API_KEY"),
            },
            params={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "text": "true"},
            timeout=30
        )
        if response.status_code in [200, 400, 422]:  # 400/422 means API is responding
            print(f"   ✅ Supadata: Connected (status: {response.status_code})")
            return True
        else:
            print(f"   ❌ Supadata: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Supadata Error: {e}")
        return False

async def test_database():
    """Test PostgreSQL database connection."""
    print("\n🔍 Testing PostgreSQL Database...")
    try:
        import psycopg2
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        conn.close()
        print(f"   ✅ PostgreSQL: Connected")
        return True
    except Exception as e:
        print(f"   ⚠️  PostgreSQL: {e}")
        return False

async def main():
    print("=" * 60)
    print("🚀 API Connectivity Test")
    print("=" * 60)

    results = {}

    # Test all APIs
    results["OpenAI"] = await test_openai()
    results["Anthropic"] = await test_anthropic()
    results["Gemini"] = await test_gemini()
    results["Pinecone"] = await test_pinecone()
    results["Voyage AI"] = await test_voyage()
    results["Brave Search"] = await test_brave_search()
    results["Supadata"] = await test_supadata()
    results["PostgreSQL"] = await test_database()

    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, status in results.items():
        icon = "✅" if status else "❌"
        print(f"   {icon} {name}")

    print(f"\n   Total: {passed}/{total} passed")
    print("=" * 60)

    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
