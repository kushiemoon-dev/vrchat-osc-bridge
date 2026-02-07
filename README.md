# VRChat OSC Bridge - Lexis Edition 🦊

Bridge HTTP → OSC pour permettre à Lexis de contrôler un avatar VRChat.

## Setup (Windows)

### 1. Installer Python
Si pas déjà fait: https://www.python.org/downloads/

### 2. Installer les dépendances
```cmd
pip install python-osc flask
```

### 3. Activer OSC dans VRChat
- Ouvre VRChat
- Settings → OSC → **Enable**
- (Il crée un fichier config dans `%APPDATA%\..\LocalLow\VRChat\VRChat\OSC\`)

### 4. Lancer le bridge
```cmd
python bridge.py
```

Le bridge écoute sur le port **8765**.

## Test rapide

Depuis un autre PC (ex: Lexis):
```bash
# Envoyer un message dans le chatbox
curl -X POST http://localhost:8765/chatbox \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello from Lexis! 🦊"}'

# Faire sauter l'avatar
curl -X POST http://localhost:8765/jump

# Avancer pendant 1 seconde
curl -X POST http://localhost:8765/move \
  -H "Content-Type: application/json" \
  -d '{"vertical": 1, "duration": 1}'
```

## Endpoints

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/health` | GET | Health check |
| `/chatbox` | POST | Envoyer un message (`message`, `direct`, `notify`) |
| `/chatbox/typing` | POST | Indicateur de frappe (`typing`) |
| `/move` | POST | Déplacer (`vertical`, `horizontal`, `look`, `duration`) |
| `/jump` | POST | Sauter |
| `/run` | POST | Courir (`running`) |
| `/avatar/parameter` | POST | Paramètre avatar (`name`, `value`) |
| `/voice` | POST | Toggle mute (`unmute`) |
| `/raw` | POST | OSC brut (`address`, `args`) |

## Firewall

Windows va probablement demander l'autorisation pour Python. 
Accepte pour "Réseaux privés" uniquement.

## Sécurité

⚠️ Ce bridge n'a PAS d'authentification. Ne l'expose pas sur Internet!
C'est safe sur un réseau local privé.
