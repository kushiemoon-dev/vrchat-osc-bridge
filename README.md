<div align="center">

# VRChat OSC Bridge

**Production-ready HTTP-to-OSC bridge for VRChat control**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

[Features](#features) • [Quick Start](#quick-start) • [API Reference](#api-reference) • [Security](#security) • [Documentation](#documentation)

---

</div>

## Overview

VRChat OSC Bridge is a secure, production-ready HTTP server that translates HTTP requests into OSC (Open Sound Control) messages for VRChat. Perfect for building chatbots, automation tools, or external VRChat integrations.

**Built for production with enterprise-grade security:**
- API key authentication on all endpoints
- Smart rate limiting to prevent abuse
- Input validation & sanitization
- Comprehensive audit logging
- CORS protection & secure defaults

## Features

### Core Functionality
- **Chatbox Control** - Send messages, show typing indicators
- **Avatar Movement** - Control walking, running, jumping, looking
- **Avatar Parameters** - Set custom avatar parameters
- **World Navigation** - Launch into specific VRChat worlds
- **Screen Capture** - Take screenshots remotely
- **Audio Recording** - Capture audio streams
- **AI Transcription** - Real-time speech-to-text with Whisper

### Enterprise Security
- **API Key Authentication** - Required for all endpoints
- **Rate Limiting** - Configurable per-endpoint limits
- **Input Validation** - Pydantic schemas prevent injection attacks
- **Audit Logging** - Track all sensitive operations
- **Whitelist Protection** - Raw OSC addresses restricted
- **CORS Configuration** - Controlled cross-origin access

### Developer Experience
- **Environment-based config** - No hardcoded secrets
- **Detailed error messages** - Easy debugging
- **Comprehensive logging** - Production-ready monitoring
- **Clean API design** - RESTful endpoints
- **Python client included** - `lexis_control.py`

## Quick Start

### Prerequisites
- Python 3.8 or higher
- VRChat with OSC enabled
- pip or virtualenv

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/kushiemoon-dev/vrchat-osc-bridge.git
cd vrchat-osc-bridge

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env

# 5. Generate secure API key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy output to .env as API_KEY=...

# 6. Enable OSC in VRChat
# VRChat → Settings → OSC → Enable

# 7. Start the bridge
python bridge.py
```

### First Request

```bash
# Send a test message
curl -X POST http://localhost:8765/chatbox \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"message": "Hello VRChat!"}'
```

## API Reference

### Authentication

All endpoints require API key authentication via Bearer token:

```bash
Authorization: Bearer YOUR_API_KEY
```

### Endpoints

#### Chatbox

**Send Message**
```bash
POST /chatbox
{
  "message": "Hello world!",
  "direct": true,    # Send immediately (true) or open keyboard (false)
  "notify": true     # Play notification sound
}
```

**Typing Indicator**
```bash
POST /chatbox/typing
{
  "typing": true  # Show/hide typing indicator
}
```

#### Movement & Controls

**Move Avatar**
```bash
POST /move
{
  "vertical": 1.0,    # -1 to 1 (backward/forward)
  "horizontal": 0.0,  # -1 to 1 (left/right)
  "look": 0.0,        # -1 to 1 (turn left/right)
  "duration": 0.5     # How long to move (seconds)
}
```

**Jump**
```bash
POST /jump
```

**Run Toggle**
```bash
POST /run
{
  "running": true
}
```

**Voice Toggle**
```bash
POST /voice
{
  "unmute": true
}
```

#### Avatar Parameters

```bash
POST /avatar/parameter
{
  "name": "VoiceLevel",  # Alphanumeric names only
  "value": 0.5           # -1.0 to 1.0
}
```

#### World Navigation

```bash
POST /launch
{
  "world_id": "wrld_xxx-xxx-xxx",  # VRChat world ID
  "url": "vrchat://launch?..."     # Or direct launch URL
}
```

#### Media Capture

**Screenshot**
```bash
GET /screenshot
# Returns JPEG image
```

**Audio Recording**
```bash
POST /listen
{
  "duration": 5  # Seconds (max 30)
}
# Returns WAV audio file
```

**Speech Transcription**
```bash
POST /transcribe
{
  "duration": 5,          # Seconds (max 30)
  "device_id": null       # Optional: specific audio device
}
# Returns: {"text": "transcribed speech", "language": "en"}
```

**List Audio Devices**
```bash
GET /listen/devices
# Returns list of available audio input devices
```

#### System

**Health Check**
```bash
GET /health
# Returns: {"status": "ok", "service": "vrchat-bridge"}
```

**Raw OSC** (Advanced)
```bash
POST /raw
{
  "address": "/chatbox/input",  # Whitelisted addresses only
  "args": ["message", true]
}
```

### Rate Limits

| Endpoint | Limit | Reason |
|----------|-------|--------|
| Default | 60/min, 1000/hour | General protection |
| `/chatbox` | 30/min | Prevent spam |
| `/screenshot` | 5/hour | Resource intensive |
| `/listen` | 10/hour | Resource intensive |
| `/transcribe` | 10/hour | AI processing costs |
| `/launch` | 5/hour | User experience |
| `/raw` | 10/min | Security critical |

## Security

### Configuration

All sensitive configuration via environment variables (`.env`):

```bash
# Required
API_KEY=your_secure_32_char_key_here

# Optional
BRIDGE_HOST=0.0.0.0                # IP to bind to
BRIDGE_PORT=8765                   # Port to listen on
VRC_IP=127.0.0.1                   # VRChat OSC IP
VRC_PORT=9000                      # VRChat OSC port
RATE_LIMIT_PER_MINUTE=60           # Global rate limit
RATE_LIMIT_PER_HOUR=1000           # Global rate limit
ALLOWED_ORIGINS=*                   # CORS origins (comma-separated)
FLASK_ENV=production               # production or development
DEBUG=false                        # Debug mode
WHISPER_MODEL=base                 # Whisper model (tiny/base/small/medium/large)
WHISPER_DEVICE=cpu                 # cpu or cuda
```

### Best Practices

1. **Generate Strong API Keys**
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Never Commit Secrets**
   - `.env` is gitignored
   - Use `.env.example` as template

3. **Restrict Network Access**
   - Use firewall rules
   - Bind to specific IPs only
   - Consider VPN for remote access

4. **Use HTTPS in Production**
   - Deploy behind nginx/caddy
   - Use Let's Encrypt certificates
   - Never expose HTTP to internet

5. **Monitor Logs**
   - Check audit logs regularly
   - Set up log aggregation
   - Alert on suspicious patterns

6. **Rotate API Keys**
   - Monthly rotation recommended
   - Immediate rotation if exposed
   - Use different keys per client

### Input Validation

All inputs are validated and sanitized:

- **Chatbox**: Max 1000 chars, UTF-8 validated
- **Movement**: Clamped to -1.0 to 1.0 range
- **Parameters**: Alphanumeric names only
- **OSC Addresses**: Strict whitelist (`/chatbox/`, `/input/`, `/avatar/parameters/`)
- **World IDs**: Regex validated (`wrld_` format)
- **Durations**: Capped at 30 seconds

### Network Security

**Firewall Configuration (Linux)**
```bash
# iptables - Allow only from specific IP
sudo iptables -A INPUT -p tcp --dport 8765 -s TRUSTED_IP -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8765 -j DROP

# firewalld
sudo firewall-cmd --permanent --add-port=8765/tcp --source=TRUSTED_IP
sudo firewall-cmd --reload
```

**Windows Firewall**
- Allow Python through Windows Firewall
- Restrict to "Private Networks" only

## Documentation

### Using the Python Client

The included `lexis_control.py` provides a Python interface:

```python
import os
os.environ['BRIDGE_HOST'] = 'localhost'
os.environ['BRIDGE_PORT'] = '8765'
os.environ['API_KEY'] = 'your_api_key'

from lexis_control import chatbox, move, jump, set_parameter

# Send message
chatbox("Hello from Python!")

# Move forward for 1 second
move(vertical=1.0, duration=1.0)

# Jump
jump()

# Set avatar parameter
set_parameter("VoiceLevel", 0.8)
```

### Error Handling

**401 Unauthorized**
- Missing or invalid API key
- Check `Authorization: Bearer ...` header
- Verify API key in `.env`

**400 Bad Request**
- Invalid input data
- Check request schema
- Validate parameter types/ranges

**429 Too Many Requests**
- Rate limit exceeded
- Wait before retrying
- Adjust limits in `.env` if needed

**500 Internal Server Error**
- Server-side issue
- Check logs for details
- File issue on GitHub

### Advanced Configuration

**Custom Rate Limits**
```bash
# In .env
RATE_LIMIT_PER_MINUTE=120  # Double the default
RATE_LIMIT_PER_HOUR=5000
```

**CORS Configuration**
```bash
# In .env
ALLOWED_ORIGINS=https://example.com,https://app.example.com
```

**Debug Mode**
```bash
# In .env
DEBUG=true
FLASK_ENV=development
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements.txt

# Test authentication
curl http://localhost:8765/health  # Should fail (401)
curl -H "Authorization: Bearer YOUR_KEY" http://localhost:8765/health  # Should succeed

# Test rate limiting
for i in {1..100}; do curl -H "Authorization: Bearer YOUR_KEY" http://localhost:8765/health; done
```

### Project Structure

```
vrchat-osc-bridge/
├── bridge.py              # Main server
├── lexis_control.py       # Python client
├── requirements.txt       # Dependencies
├── .env.example          # Config template
├── .gitignore            # Git exclusions
├── LICENSE               # MIT License
└── README.md             # This file
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **VRChat** for the OSC protocol
- **python-osc** for OSC implementation
- **Flask** for HTTP server
- **Whisper** for speech recognition
- Built for **Lexis**

## Support

- **Issues**: [GitHub Issues](https://github.com/kushiemoon-dev/vrchat-osc-bridge/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kushiemoon-dev/vrchat-osc-bridge/discussions)

---

<div align="center">

Made with ❤️ for the VRChat community

[⬆ Back to Top](#vrchat-osc-bridge)

</div>
