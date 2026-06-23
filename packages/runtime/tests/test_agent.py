from annulus_runtime.agent import _prepend_system_context


def test_prepend_system_context_returns_flat_message_list():
    messages = [{"role": "user", "content": "Hello"}]
    updated = _prepend_system_context(messages, "repo context")
    assert updated == [
        {"role": "system", "content": "repo context"},
        {"role": "user", "content": "Hello"},
    ]
    assert not any(isinstance(m, list) for m in updated)
