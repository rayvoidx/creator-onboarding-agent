#!/usr/bin/env python3
"""
설정 검증 스크립트

모든 모델 설정과 Pinecone 설정이 올바르게 적용되었는지 확인합니다.
"""

import sys
import os

# 프로젝트 루트를 PYTHONPATH에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import get_settings


def verify_settings():
    """설정 검증"""
    settings = get_settings()

    print("=" * 60)
    print("Configuration Verification Report")
    print("=" * 60)

    # 1. LLM Model Variables
    print("\n[1] LLM Model Variables")
    print("-" * 40)
    print(f"  ANTHROPIC_MODEL_NAME: {settings.ANTHROPIC_MODEL_NAME}")
    print(f"  GEMINI_MODEL_NAME: {settings.GEMINI_MODEL_NAME}")
    print(f"  OPENAI_MODEL_NAME: {settings.OPENAI_MODEL_NAME}")

    # 2. Default LLM Configurations
    print("\n[2] Default LLM Configurations")
    print("-" * 40)
    print(f"  DEFAULT_LLM_MODEL: {settings.DEFAULT_LLM_MODEL}")
    print(f"  FAST_LLM_MODEL: {settings.FAST_LLM_MODEL}")
    print(f"  DEEP_LLM_MODEL: {settings.DEEP_LLM_MODEL}")
    print(f"  FALLBACK_LLM_MODEL: {settings.FALLBACK_LLM_MODEL}")

    # 3. Embedding Models
    print("\n[3] Embedding Models")
    print("-" * 40)
    print(f"  EMBEDDING_MODEL_NAME: {settings.EMBEDDING_MODEL_NAME}")
    print(f"  GEMINI_EMBEDDING_MODEL_NAME: {settings.GEMINI_EMBEDDING_MODEL_NAME}")
    print(f"  VOYAGE_EMBEDDING_MODEL_NAME: {settings.VOYAGE_EMBEDDING_MODEL_NAME}")
    print(f"  DEFAULT_EMBEDDING_PROVIDER: {settings.DEFAULT_EMBEDDING_PROVIDER}")

    # 4. API Keys Status
    print("\n[4] API Keys Status")
    print("-" * 40)
    print(f"  OPENAI_API_KEY: {'✓ Set' if settings.OPENAI_API_KEY else '✗ Not Set'}")
    print(f"  ANTHROPIC_API_KEY: {'✓ Set' if settings.ANTHROPIC_API_KEY else '✗ Not Set'}")
    print(f"  GOOGLE_API_KEY: {'✓ Set' if settings.GOOGLE_API_KEY else '✗ Not Set'}")
    print(f"  VOYAGE_API_KEY: {'✓ Set' if settings.VOYAGE_API_KEY else '✗ Not Set'}")
    print(f"  PINECONE_API_KEY: {'✓ Set' if settings.PINECONE_API_KEY else '✗ Not Set'}")

    # 5. Vector DB Configuration
    print("\n[5] Vector DB Configuration (Pinecone)")
    print("-" * 40)
    print(f"  VECTOR_DB_PROVIDER: {settings.VECTOR_DB_PROVIDER}")
    print(f"  PINECONE_INDEX_NAME: {settings.PINECONE_INDEX_NAME}")
    print(f"  PINECONE_NAMESPACE: {settings.PINECONE_NAMESPACE}")
    print(f"  PINECONE_ENVIRONMENT: {settings.PINECONE_ENVIRONMENT}")

    # 6. Agent Model Configurations
    print("\n[6] Agent Model Configurations")
    print("-" * 40)
    agent_configs = settings.AGENT_MODEL_CONFIGS
    for agent_type, config in agent_configs.items():
        models = config.get('llm_models', [])
        vector_db = config.get('vector_db', 'not set')
        print(f"  {agent_type}:")
        print(f"    - Models: {', '.join(models[:2])}")
        print(f"    - Vector DB: {vector_db}")

    # 7. LLM Configs Property
    print("\n[7] LLM_CONFIGS Property")
    print("-" * 40)
    llm_configs = settings.LLM_CONFIGS
    print(f"  anthropic_model: {llm_configs.get('anthropic_model')}")
    print(f"  gemini_model: {llm_configs.get('gemini_model')}")
    print(f"  openai_model: {llm_configs.get('openai_model')}")

    # 8. VECTOR_DB_CONFIG Property
    print("\n[8] VECTOR_DB_CONFIG Property")
    print("-" * 40)
    vdb_config = settings.VECTOR_DB_CONFIG
    print(f"  provider: {vdb_config.get('provider')}")
    print(f"  pinecone_index_name: {vdb_config.get('pinecone_index_name')}")
    print(f"  pinecone_namespace: {vdb_config.get('pinecone_namespace')}")
    print(f"  embedding_provider: {vdb_config.get('embedding_provider')}")
    print(f"  voyage_embedding_model: {vdb_config.get('voyage_embedding_model')}")

    print("\n" + "=" * 60)

    # Summary
    issues = []

    # Check critical settings
    if settings.VECTOR_DB_PROVIDER != 'pinecone':
        issues.append("VECTOR_DB_PROVIDER is not set to 'pinecone'")

    if not settings.PINECONE_API_KEY:
        issues.append("PINECONE_API_KEY is not set (required for Pinecone)")

    if not settings.VOYAGE_API_KEY and settings.DEFAULT_EMBEDDING_PROVIDER == 'voyage':
        issues.append("VOYAGE_API_KEY is not set but voyage is default embedding provider")

    # Check all agents use Pinecone
    for agent_type, config in agent_configs.items():
        if config.get('vector_db') != 'pinecone':
            issues.append(f"Agent '{agent_type}' is not configured to use Pinecone")

    if issues:
        print("\n⚠️  Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✓ All configurations verified successfully!")

    print("=" * 60)

    return len(issues) == 0


if __name__ == "__main__":
    success = verify_settings()
    sys.exit(0 if success else 1)
