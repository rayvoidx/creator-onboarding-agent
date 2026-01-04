"""Tests for hello utility module."""

import pytest

from src.utils.hello import hello_world, hello_user, get_greeting


class TestHelloWorld:
    """Test cases for hello_world function."""
    
    def test_hello_world_returns_correct_message(self):
        """Test that hello_world returns the correct greeting."""
        result = hello_world()
        assert result == "Hello World"
        
    def test_hello_world_returns_string(self):
        """Test that hello_world returns a string."""
        result = hello_world()
        assert isinstance(result, str)


class TestHelloUser:
    """Test cases for hello_user function."""
    
    def test_hello_user_with_name(self):
        """Test that hello_user returns personalized greeting."""
        result = hello_user("Alice")
        assert result == "Hello Alice!"
        
    def test_hello_user_with_empty_name(self):
        """Test that hello_user works with empty string."""
        result = hello_user("")
        assert result == "Hello !"
        
    def test_hello_user_with_special_characters(self):
        """Test that hello_user works with special characters."""
        result = hello_user("José")
        assert result == "Hello José!"


class TestGetGreeting:
    """Test cases for get_greeting function."""
    
    def test_get_greeting_default(self):
        """Test that get_greeting returns default greeting."""
        result = get_greeting()
        assert result == "Hello World!"
        
    def test_get_greeting_with_name(self):
        """Test that get_greeting returns personalized greeting."""
        result = get_greeting("Bob")
        assert result == "Hello Bob!"
        
    def test_get_greeting_with_empty_name(self):
        """Test that get_greeting works with empty string."""
        result = get_greeting("")
        assert result == "Hello !"
        
    def test_get_greeting_with_none(self):
        """Test that get_greeting works with None."""
        result = get_greeting(None)
        assert result == "Hello None!"