"""Simple Hello World utility module."""


def hello_world() -> str:
    """Return a simple Hello World greeting.

    Returns:
        str: Hello World message
    """
    return "Hello World"


def hello_user(name: str) -> str:
    """Return a personalized greeting.

    Args:
        name: The name to greet

    Returns:
        str: Personalized greeting message
    """
    return f"Hello {name}!"


def get_greeting(name: str = "World") -> str:
    """Get a greeting with optional name parameter.

    Args:
        name: The name to greet (defaults to "World")

    Returns:
        str: Greeting message
    """
    return f"Hello {name}!"
