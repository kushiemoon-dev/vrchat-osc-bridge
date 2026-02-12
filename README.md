# VRChat OSC Bridge

Bridge HTTP vers OSC pour contrôler VRChat avec Lexis.

## ⚠️ Security Notice

**This bridge now includes:**
- 🔒 API Key authentication (required for all endpoints)
- 🚦 Rate limiting (prevents abuse)
- ✅ Input validation (prevents injection attacks)
- 📝 Audit logging (tracks all actions)

**IMPORTANT**: This is designed for local network use. Do NOT expose directly to the internet without additional security measures (HTTPS, firewall, VPN).

## Installation

### 1. Clone repository
```bash
git clone https://github.com/kushiemoon-dev/vrchat-osc-bridge.git
cd vrchat-osc-bridge
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
# Copy example configuration
cp .env.example .env

# Edit .env and set your values
# CRITICAL: Generate a secure API key:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy the output and paste it as API_KEY in .env
```

### 4. Enable OSC in VRChat
- Open VRChat
- Settings → OSC → **Enable**
- (Creates config file in `%APPDATA%\..\LocalLow\VRChat\VRChat\OSC\`)

### 5. Start the bridge
```bash
python bridge.py
```

## Configuration

All configuration is done via environment variables in `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `BRIDGE_HOST` | IP address to bind to | `0.0.0.0` |
| `BRIDGE_PORT` | Port to listen on | `8765` |
| `API_KEY` | **Required** - API key for authentication | None |
| `VRC_IP` | VRChat OSC IP | `127.0.0.1` |
| `VRC_PORT` | VRChat OSC port | `9000` |
| `RATE_LIMIT_PER_MINUTE` | Rate limit per minute | `60` |
| `RATE_LIMIT_PER_HOUR` | Rate limit per hour | `1000` |
| `FLASK_ENV` | Environment (`production` or `development`) | `production` |
| `DEBUG` | Debug mode | `false` |

## Usage Examples

**All endpoints now require authentication via Bearer token:**

### Chatbox
```bash
curl -X POST http://BRIDGE_IP:8765/chatbox \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"message": "Hello from Lexis! 🦊", "direct": true, "notify": true}'
```

### Movement
```bash
# Move forward
curl -X POST http://BRIDGE_IP:8765/move \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"vertical": 1.0, "horizontal": 0.0, "duration": 1.0}'
```

### Jump
```bash
curl -X POST http://BRIDGE_IP:8765/jump \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Screenshot
```bash
curl -X GET http://BRIDGE_IP:8765/screenshot \
  -H "Authorization: Bearer YOUR_API_KEY" \
  > screenshot.jpg
```

### Audio Recording & Transcription
```bash
# Record 5 seconds of audio
curl -X POST http://BRIDGE_IP:8765/listen \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"duration": 5}' \
  > recording.wav

# Record and transcribe with Whisper
curl -X POST http://BRIDGE_IP:8765/transcribe \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"duration": 5}'
```

## Endpoints

| Endpoint | Method | Rate Limit | Description |
|----------|--------|------------|-------------|
| `/health` | GET | 60/min | Health check |
| `/chatbox` | POST | 30/min | Send chatbox message |
| `/chatbox/typing` | POST | 60/min | Toggle typing indicator |
| `/move` | POST | 60/min | Move avatar |
| `/jump` | POST | 30/min | Make avatar jump |
| `/run` | POST | 60/min | Toggle running |
| `/avatar/parameter` | POST | 60/min | Set avatar parameter |
| `/voice` | POST | 60/min | Toggle voice/mute |
| `/raw` | POST | 10/min | Send raw OSC (whitelisted addresses) |
| `/launch` | POST | 5/hour | Launch VRChat world |
| `/screenshot` | GET | 5/hour | Capture screen |
| `/listen` | POST | 10/hour | Record audio |
| `/listen/devices` | GET | 20/min | List audio devices |
| `/transcribe` | POST | 10/hour | Record + transcribe with Whisper |

## Security Best Practices

1. **Never commit your `.env` file** - It contains secrets
2. **Use strong API keys** - Generate with the command above (32+ characters)
3. **Restrict network access** - Use firewall rules to limit who can connect
4. **Monitor audit logs** - Check for suspicious activity
5. **Keep dependencies updated** - Run `pip install -U -r requirements.txt` regularly
6. **Use HTTPS in production** - Set up reverse proxy (nginx, caddy) with SSL
7. **Limit API key distribution** - Only share with trusted systems
8. **Rotate keys regularly** - Change API key monthly or after exposure

## Rate Limits

To prevent abuse, the following rate limits are enforced:

| Category | Limit |
|----------|-------|
| Default | 60/minute, 1000/hour |
| Chatbox | 30/minute |
| Screenshot | 5/hour |
| Audio Recording | 10/hour |
| Transcription | 10/hour |
| World Launch | 5/hour |
| Raw OSC | 10/minute |

## Input Validation

All endpoints validate input to prevent attacks:

- **Chatbox**: Max 1000 characters
- **Movement**: Values clamped to -1.0 to 1.0
- **Avatar Parameters**: Alphanumeric names only
- **Raw OSC**: Whitelisted addresses only (`/chatbox/`, `/input/`, `/avatar/parameters/`)
- **World Launch**: Valid VRChat world ID format (`wrld_*`)

## Troubleshooting

### "API_KEY must be set in environment variables"
- Make sure you created `.env` file with `API_KEY=...`
- Verify the `.env` file is in the same directory as `bridge.py`
- Restart the bridge after editing `.env`

### "401 Unauthorized"
- Check that you're sending correct API key in `Authorization: Bearer ...` header
- Verify API key matches the one in your `.env` file
- Make sure there are no extra spaces or newlines in the API key

### "429 Too Many Requests"
- You've hit the rate limit
- Wait a few minutes and try again
- Consider adjusting rate limits in `.env` for your use case

### Screenshot/Audio not working
```bash
# Install optional dependencies
pip install Pillow sounddevice numpy scipy openai-whisper
```

## Client Configuration (Lexis)

On Lexis's server, configure the client:

```bash
# Set environment variables
export BRIDGE_HOST=your_bridge_ip
export BRIDGE_PORT=8765
export API_KEY=your_api_key_here

# Test connection
python lexis_control.py "Test message"
```

## Firewall Configuration

**Windows**: Allow Python through firewall for private networks only

**Linux** (iptables):
```bash
# Allow only from specific IP
iptables -A INPUT -p tcp --dport 8765 -s YOUR_TRUSTED_IP -j ACCEPT
iptables -A INPUT -p tcp --dport 8765 -j DROP
```

**Linux** (firewalld):
```bash
# Allow port 8765
firewall-cmd --permanent --add-port=8765/tcp
firewall-cmd --reload
```

## Optional Features

### Whisper Transcription

Install Whisper for audio transcription:
```bash
pip install openai-whisper
```

Models available (trade-off between speed and accuracy):
- `tiny` - Fastest, lowest accuracy
- `base` - Default, good balance
- `small` - Better accuracy
- `medium` - High accuracy, slower
- `large` - Best accuracy, slowest

Configure in `.env`:
```env
WHISPER_MODEL=base
```

## Development

### Running in Debug Mode

```bash
# In .env
DEBUG=true
FLASK_ENV=development
```

### Testing Authentication

```bash
# Should fail (no auth)
curl http://localhost:8765/health

# Should succeed
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:8765/health
```

## License

MIT License - See LICENSE file for details

## Credits

Created for Lexis 🦊
