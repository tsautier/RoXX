# Test de la Console Python RoXX

Ce document explique comment tester la nouvelle console Python.

## Installation Rapide

```powershell
# Dans le répertoire RoXX
cd c:\RoXX

# Installer les dépendances
pip install -r requirements.txt
```

## Lancement de la Console

```powershell
# Méthode 1: Module Python
python -m roxx

# Méthode 2: Script direct
python roxx\cli\console.py
```

## Fonctionnalités Testées

### ✅ Multi-OS
- Détection automatique de l'OS (Windows/Linux/macOS)
- Chemins adaptés par OS
- Gestion des services selon l'OS

### ✅ Interface TUI
- Menu interactif avec Rich
- Tables formatées
- Couleurs et icônes
- Navigation au clavier

### ✅ Gestion des Services
- Statut en temps réel
- Démarrage/Arrêt/Redémarrage
- Support systemctl (Linux), sc (Windows), launchctl (macOS)

### ✅ Informations Système
- CPU, RAM, Disque
- Informations OS
- Utilisation en temps réel

### ✅ Internationalisation
- Support EN/FR
- Chargement depuis locales.json
- Changement de langue à la volée

## Prochaines Étapes

1. Tester sur Linux (WSL ou VM)
2. Migrer le script `setup`
3. Migrer les scripts d'authentification (push.sh, totp.sh)
4. Créer des packages installables
