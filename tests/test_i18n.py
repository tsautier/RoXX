"""
Unit tests for I18n system
"""

import pytest
from pathlib import Path

from roxx.utils.i18n import I18n, translate, set_locale, get_locale


class TestI18n:
    """Test internationalization functionality"""
    
    def test_init_default_locale(self):
        """Test I18n initialization with default locale"""
        i18n = I18n()
        assert i18n.locale == "EN"
    
    def test_init_custom_locale(self):
        """Test I18n initialization with custom locale"""
        i18n = I18n(locale="FR")
        assert i18n.locale == "FR"
    
    def test_translate_existing_key(self):
        """Test translating an existing key"""
        i18n = I18n(locale="EN")
        result = i18n.translate("app_title", "Default")
        assert isinstance(result, str)
    
    def test_translate_missing_key(self):
        """Test translating a missing key"""
        i18n = I18n()
        result = i18n.translate("nonexistent_key", "Default Value")
        assert result == "Default Value"
    
    def test_set_locale(self):
        """Test changing locale"""
        i18n = I18n(locale="EN")
        i18n.set_locale("FR")
        assert i18n.locale == "FR"
    
    def test_global_translate(self):
        """Test global translate function"""
        result = translate("app_title", "Default")
        assert isinstance(result, str)
    
    def test_global_set_locale(self):
        """Test global set_locale function"""
        set_locale("FR")
        assert get_locale() == "FR"
        
        # Reset to EN
        set_locale("EN")
        assert get_locale() == "EN"
    
    def test_default_translations(self):
        """Test default translations are loaded"""
        i18n = I18n()
        
        # These should exist in default translations
        assert i18n.translate("services") is not None
        assert i18n.translate("status") is not None
        assert i18n.translate("exit") is not None
