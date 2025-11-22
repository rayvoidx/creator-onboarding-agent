import asyncio
import pytest  # type: ignore[import-not-found]

from src.rag.generation_engine import GenerationEngine


class FailingModel:
    def __init__(self, fails: int = 1, text: str = "ok"):
        self._fails = fails
        self._text = text

    async def ainvoke(self, _messages):
        if self._fails > 0:
            self._fails -= 1
            raise RuntimeError("temporary failure")
        class Resp:
            content = self._text
        return Resp()


@pytest.mark.asyncio
async def test_fallback_cascades_to_next_model():
    eng = GenerationEngine({
        'retry': {'max_retries': 1, 'backoff_ms': 1},
        'fallback_order': ['selected', 'fallback']
    })
    # Inject models
    eng.models.clear()
    eng.default_model = 'primary'
    eng.fallback_model = 'backup'
    eng.models['primary'] = FailingModel(fails=1)  # will fail
    eng.models['backup'] = FailingModel(fails=0, text='from-backup')  # will succeed

    result = await eng.generate(prompt="hi", model_name='primary')
    assert 'from-backup' in result


@pytest.mark.asyncio
async def test_retry_succeeds_without_fallback():
    eng = GenerationEngine({'retry': {'max_retries': 2, 'backoff_ms': 1}})
    eng.models.clear()
    eng.default_model = 'only'
    eng.models['only'] = FailingModel(fails=1, text='eventually')

    result = await eng.generate(prompt="hi", model_name='only')
    assert 'eventually' in result


