"""
Internationalization utilities for RoXX
"""

import json
from pathlib import Path
from typing import Dict, Optional

from roxx.utils.system import SystemManager


class I18n:
    """Internationalization manager"""

    def __init__(self, locale: str = "EN"):
        self.locale = locale.upper()
        self.translations: Dict = {}
        self.load_translations()

    def load_translations(self):
        """Load translations from JSON file"""
        # Search first in roxx/config/, then in share/
        config_dir = SystemManager.get_config_dir()
        possible_paths = [
            Path(__file__).parent.parent / "config" / "locales.json",
            config_dir / "locales.json",
            Path("/usr/local/share/dict.locales.json"),  # Legacy
        ]

        for path in possible_paths:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        self.translations = json.load(f)
                    return
                except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
                    # If error, continue with next file
                    continue

        # If no file found or all errors, use default translations
        self.translations = self._get_default_translations()

    def _get_default_translations(self) -> Dict:
        """Minimal default translations"""
        return {
            "app_title": {
                "EN": "RoXX Admin Console",
                "FR": "Console d'Administration RoXX"
            },
            "services": {
                "EN": "Services",
                "FR": "Services"
            },
            "status": {
                "EN": "Status",
                "FR": "État"
            },
            "start": {
                "EN": "Start",
                "FR": "Démarrer"
            },
            "stop": {
                "EN": "Stop",
                "FR": "Arrêter"
            },
            "restart": {
                "EN": "Restart",
                "FR": "Redémarrer"
            },
            "exit": {
                "EN": "Exit",
                "FR": "Quitter"
            }
        }

    def translate(self, key: str, default: Optional[str] = None) -> str:
        """
        Translate a key in the current language
        
        Args:
            key: Translation key (e.g. 'se_ti_001')
            default: Default value if key doesn't exist
        
        Returns:
            Translated text or the key itself if not found
        """
        if key in self.translations:
            return self.translations[key].get(self.locale, key)
        return default or key

    def set_locale(self, locale: str):
        """Change language"""
        self.locale = locale.upper()


# Global instance
_i18n = I18n()


def translate(key: str, default: Optional[str] = None) -> str:
    """Helper function to translate"""
    return _i18n.translate(key, default)


def set_locale(locale: str):
    """Change global language"""
    _i18n.set_locale(locale)


def get_locale() -> str:
    """Return current language"""
    return _i18n.locale
