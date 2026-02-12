#!/usr/bin/env python3
"""
VRChat OSC Bridge - Lexis Edition 🦊
Receives HTTP commands and forwards them to VRChat via OSC.

Run on the machine where VRChat is running.
Requires: pip install python-osc flask flask-httpauth flask-limiter python-dotenv pydantic flask-cors
"""

from flask import Flask, request, jsonify, send_file
from flask_httpauth import HTTPTokenAuth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from pythonosc import udp_client
from pydantic import BaseModel, ValidationError, Field, validator
from dotenv import load_dotenv
import time
import io
import subprocess
import webbrowser
import os
import platform
import logging
from functools import wraps

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise ValueError("❌ API_KEY must be set in environment variables (.env file)")

DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
FLASK_ENV = os.getenv('FLASK_ENV', 'production')

# Setup logging
logging.basicConfig(
    level=logging.INFO if FLASK_ENV == 'production' else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
audit_logger = logging.getLogger('audit')

# Try to import screenshot library
try:
    from PIL import ImageGrab
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False
    print("⚠️  PIL not installed - screenshot disabled. Run: pip install Pillow")

# Try to import audio recording library
try:
    import sounddevice as sd
    import numpy as np
    try:
        from scipy.io.wavfile import write as write_wav
    except ImportError:
        # Fallback: use wave module
        import wave
        def write_wav(filename, rate, data):
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(rate)
                wf.writeframes(data.tobytes())
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("⚠️  Audio libs not installed - voice disabled. Run: pip install sounddevice numpy scipy")

# Initialize Flask app
app = Flask(__name__)

# CORS configuration (restrict in production)
CORS(app, resources={
    r"/*": {
        "origins": os.getenv('ALLOWED_ORIGINS', '*').split(','),
        "methods": ["POST", "GET"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# API Key Authentication
auth = HTTPTokenAuth(scheme='Bearer')

@auth.verify_token
def verify_token(token):
    return token == API_KEY

# Rate Limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[
        f"{os.getenv('RATE_LIMIT_PER_MINUTE', 60)} per minute",
        f"{os.getenv('RATE_LIMIT_PER_HOUR', 1000)} per hour"
    ],
    storage_uri="memory://"
)

# Pydantic validation schemas
class ChatboxRequest(BaseModel):
    message: str = Field(..., max_length=1000, min_length=1)
    direct: bool = True
    notify: bool = True

class MoveRequest(BaseModel):
    vertical: float = Field(..., ge=-1.0, le=1.0)
    horizontal: float = Field(..., ge=-1.0, le=1.0)
    look: float = Field(default=0.0, ge=-1.0, le=1.0)
    duration: float = Field(default=0.5, ge=0.0, le=10.0)

class AvatarParameterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9_]+$')
    value: float = Field(..., ge=-1.0, le=1.0)

class RawOSCRequest(BaseModel):
    address: str = Field(..., min_length=1, max_length=200)
    args: list = Field(default_factory=list, max_items=10)

    @validator('address')
    def validate_address(cls, v):
        # Whitelist of allowed OSC addresses
        allowed_prefixes = [
            '/chatbox/',
            '/input/',
            '/avatar/parameters/'
        ]
        if not any(v.startswith(prefix) for prefix in allowed_prefixes):
            raise ValueError(f'OSC address {v} not allowed')
        return v

class LaunchWorldRequest(BaseModel):
    url: str = Field(default='', max_length=500)
    world_id: str = Field(default='', pattern=r'^(wrld_[a-f0-9-]+)?$')

    @validator('world_id', 'url')
    def validate_not_empty(cls, v, values, field):
        if field.name == 'url' and not v and not values.get('world_id'):
            raise ValueError('Either url or world_id must be provided')
        return v

# VRChat OSC settings (localhost because VRChat only listens locally)
VRC_IP = os.getenv('VRC_IP', '127.0.0.1')
VRC_PORT = int(os.getenv('VRC_PORT', 9000))
osc = udp_client.SimpleUDPClient(VRC_IP, VRC_PORT)

@app.route('/health', methods=['GET'])
@auth.login_required
def health():
    """Health check endpoint - AUTHENTICATED"""
    return jsonify({"status": "ok", "service": "vrchat-bridge"})

@app.route('/chatbox', methods=['POST'])
@auth.login_required
@limiter.limit("30 per minute")
def chatbox():
    """Send a message to VRChat chatbox - AUTHENTICATED & RATE LIMITED"""
    try:
        # Validate request
        data = ChatboxRequest(**request.json)

        # Audit log
        audit_logger.info(f"Chatbox message sent: {data.message[:50]}...")

        # Send to VRChat
        osc.send_message("/chatbox/input", [data.message, data.direct, data.notify])
        return jsonify({"status": "sent", "message": data.message})

    except ValidationError as e:
        logger.warning(f"Validation error in chatbox: {e}")
        return jsonify({"error": "Invalid request", "details": str(e)}), 400

    except Exception as e:
        logger.error(f"Error in chatbox endpoint", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/chatbox/typing', methods=['POST'])
@auth.login_required
@limiter.limit("60 per minute")
def chatbox_typing():
    """Toggle typing indicator - AUTHENTICATED & RATE LIMITED"""
    try:
        data = request.json or {}
        typing = data.get('typing', True)
        osc.send_message("/chatbox/typing", typing)
        return jsonify({"status": "ok", "typing": typing})
    except Exception as e:
        logger.error("Error in chatbox_typing", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/move', methods=['POST'])
@auth.login_required
@limiter.limit("60 per minute")
def move():
    """Move the avatar - AUTHENTICATED & RATE LIMITED"""
    try:
        # Validate request
        data = MoveRequest(**request.json)

        # Send movement
        osc.send_message("/input/Vertical", float(data.vertical))
        osc.send_message("/input/Horizontal", float(data.horizontal))
        if data.look != 0:
            osc.send_message("/input/LookHorizontal", float(data.look))

        # Hold for duration
        if data.duration > 0:
            time.sleep(data.duration)
            # Reset to stop moving
            osc.send_message("/input/Vertical", 0.0)
            osc.send_message("/input/Horizontal", 0.0)
            osc.send_message("/input/LookHorizontal", 0.0)

        return jsonify({"status": "moved", "vertical": data.vertical, "horizontal": data.horizontal})

    except ValidationError as e:
        logger.warning(f"Validation error in move: {e}")
        return jsonify({"error": "Invalid request", "details": str(e)}), 400

    except Exception as e:
        logger.error("Error in move endpoint", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/jump', methods=['POST'])
@auth.login_required
@limiter.limit("30 per minute")
def jump():
    """Make the avatar jump - AUTHENTICATED & RATE LIMITED"""
    try:
        osc.send_message("/input/Jump", 1)
        time.sleep(0.1)
        osc.send_message("/input/Jump", 0)
        return jsonify({"status": "jumped"})
    except Exception as e:
        logger.error("Error in jump endpoint", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/run', methods=['POST'])
@auth.login_required
@limiter.limit("60 per minute")
def run():
    """Toggle running - AUTHENTICATED & RATE LIMITED"""
    try:
        data = request.json or {}
        running = data.get('running', True)
        osc.send_message("/input/Run", 1 if running else 0)
        return jsonify({"status": "ok", "running": running})
    except Exception as e:
        logger.error("Error in run endpoint", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/avatar/parameter', methods=['POST'])
@auth.login_required
@limiter.limit("60 per minute")
def avatar_parameter():
    """Set an avatar parameter - AUTHENTICATED & RATE LIMITED"""
    try:
        # Validate request
        data = AvatarParameterRequest(**request.json)

        # Send to VRChat
        osc.send_message(f"/avatar/parameters/{data.name}", data.value)
        return jsonify({"status": "set", "parameter": data.name, "value": data.value})

    except ValidationError as e:
        logger.warning(f"Validation error in avatar_parameter: {e}")
        return jsonify({"error": "Invalid request", "details": str(e)}), 400

    except Exception as e:
        logger.error("Error in avatar_parameter endpoint", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/voice', methods=['POST'])
@auth.login_required
@limiter.limit("60 per minute")
def voice():
    """Toggle voice/mute - AUTHENTICATED & RATE LIMITED"""
    try:
        data = request.json or {}
        unmute = data.get('unmute', True)
        osc.send_message("/input/Voice", 1 if unmute else 0)
        return jsonify({"status": "ok", "unmute": unmute})
    except Exception as e:
        logger.error("Error in voice endpoint", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/raw', methods=['POST'])
@auth.login_required
@limiter.limit("10 per minute")
def raw_osc():
    """Send a raw OSC message - AUTHENTICATED & HEAVILY RATE LIMITED"""
    try:
        # Validate request with strict whitelist
        data = RawOSCRequest(**request.json)

        # Audit log critical action
        audit_logger.warning(f"Raw OSC message sent: {data.address} with args {data.args}")

        # Send to VRChat
        osc.send_message(data.address, data.args)
        return jsonify({"status": "sent", "address": data.address, "args": data.args})

    except ValidationError as e:
        logger.warning(f"Validation error in raw_osc: {e}")
        return jsonify({"error": "Invalid request - address not in whitelist", "details": str(e)}), 400

    except Exception as e:
        logger.error("Error in raw_osc endpoint", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/launch', methods=['POST'])
@auth.login_required
@limiter.limit("5 per hour")
def launch_world():
    """Launch a VRChat world - AUTHENTICATED & HEAVILY RATE LIMITED"""
    try:
        # Validate request
        data = LaunchWorldRequest(**request.json)

        url = data.url
        world_id = data.world_id

        if url:
            # Direct URL (vrchat://launch?... or https://vrchat.com/home/world/...)
            launch_url = url
            if url.startswith('https://vrchat.com/home/world/'):
                # Convert web URL to launch URL
                parts = url.split('/')
                for part in parts:
                    if part.startswith('wrld_'):
                        world_id = part
                        break

        if world_id and not url:
            launch_url = f"vrchat://launch?ref=vrchat.com&id={world_id}"
        elif not url:
            return jsonify({"error": "Provide 'url' or 'world_id'"}), 400

        # Audit log
        audit_logger.warning(f"World launch requested: {launch_url}")

        # Open the VRChat URL
        if platform.system() == 'Windows':
            os.startfile(launch_url)
        else:
            webbrowser.open(launch_url)

        return jsonify({"status": "launched", "url": launch_url})

    except ValidationError as e:
        logger.warning(f"Validation error in launch_world: {e}")
        return jsonify({"error": "Invalid request", "details": str(e)}), 400

    except Exception as e:
        logger.error("Error in launch_world endpoint", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/screenshot', methods=['GET'])
@auth.login_required
@limiter.limit("5 per hour")
def screenshot():
    """Capture and return a screenshot - AUTHENTICATED & HEAVILY RATE LIMITED"""
    if not SCREENSHOT_AVAILABLE:
        return jsonify({"error": "PIL not installed. Run: pip install Pillow"}), 500

    try:
        # Audit log
        audit_logger.warning("Screenshot requested")

        # Capture the screen
        img = ImageGrab.grab()

        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=70)
        img_bytes.seek(0)

        return send_file(img_bytes, mimetype='image/jpeg')

    except Exception as e:
        logger.error("Error in screenshot endpoint", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/listen', methods=['POST'])
@auth.login_required
@limiter.limit("10 per hour")
def listen():
    """Record audio for a few seconds - AUTHENTICATED & HEAVILY RATE LIMITED"""
    if not AUDIO_AVAILABLE:
        return jsonify({"error": "Audio libs not installed. Run: pip install sounddevice numpy scipy"}), 500

    try:
        data = request.json or {}
        duration = min(data.get('duration', 5), 30)  # Cap at 30 seconds
        sample_rate = 44100

        # Audit log
        audit_logger.warning(f"Audio recording requested: {duration}s")

        logger.info(f"Recording {duration}s of audio...")
        # Record audio from default input (microphone or loopback)
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()  # Wait for recording to finish
        logger.info("Recording complete!")

        # Convert to WAV bytes
        wav_bytes = io.BytesIO()
        write_wav(wav_bytes, sample_rate, recording)
        wav_bytes.seek(0)

        return send_file(wav_bytes, mimetype='audio/wav')

    except Exception as e:
        logger.error("Error in listen endpoint", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/listen/devices', methods=['GET'])
@auth.login_required
@limiter.limit("20 per minute")
def list_audio_devices():
    """List available audio devices - AUTHENTICATED"""
    if not AUDIO_AVAILABLE:
        return jsonify({"error": "Audio libs not installed"}), 500

    try:
        devices = sd.query_devices()
        device_list = []
        for i, d in enumerate(devices):
            device_list.append({
                "id": i,
                "name": d['name'],
                "inputs": d['max_input_channels'],
                "outputs": d['max_output_channels'],
                "default_input": i == sd.default.device[0],
                "default_output": i == sd.default.device[1]
            })
        return jsonify({"devices": device_list})

    except Exception as e:
        logger.error("Error in list_audio_devices endpoint", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/transcribe', methods=['POST'])
@auth.login_required
@limiter.limit("10 per hour")
def transcribe():
    """Record audio and transcribe with Whisper - AUTHENTICATED & HEAVILY RATE LIMITED"""
    if not AUDIO_AVAILABLE:
        return jsonify({"error": "Audio libs not installed"}), 500

    temp_path = None
    try:
        import whisper
        import tempfile

        data = request.json or {}
        duration = min(data.get('duration', 5), 30)  # Cap at 30 seconds
        device_id = data.get('device_id', None)  # Optional: specify input device
        sample_rate = 16000  # Whisper prefers 16kHz

        # Audit log
        audit_logger.warning(f"Transcription requested: {duration}s")

        # Create secure temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            temp_path = tmp.name

        # Set restrictive permissions (owner read/write only)
        os.chmod(temp_path, 0o600)

        logger.info(f"Recording {duration}s of audio...")

        # Set device if specified
        if device_id is not None:
            recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate,
                             channels=1, dtype='float32', device=device_id)
        else:
            recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate,
                             channels=1, dtype='float32')
        sd.wait()
        logger.info("Recording complete!")

        # Save to file
        write_wav(temp_path, sample_rate, (recording * 32767).astype(np.int16))
        logger.info(f"Saved to {temp_path}")

        logger.info("Transcribing with Whisper...")
        model_name = os.getenv('WHISPER_MODEL', 'base')
        model = whisper.load_model(model_name)
        # Auto-detect language (don't force French)
        result = model.transcribe(temp_path, fp16=False)

        text = result['text'].strip()
        logger.info(f"Transcription: {text}")

        return jsonify({
            "status": "ok",
            "text": text,
            "language": result.get('language', 'unknown')
        })

    except ImportError as e:
        logger.error(f"Import error in transcribe: {e}")
        return jsonify({"error": "Whisper not installed. Run: pip install openai-whisper"}), 500

    except Exception as e:
        logger.error("Error in transcribe endpoint", exc_info=True)
        return jsonify({"error": "Transcription failed"}), 500

    finally:
        # ALWAYS cleanup temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                logger.info(f"Cleaned up {temp_path}")
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup {temp_path}: {cleanup_error}")

if __name__ == '__main__':
    print("🦊 VRChat OSC Bridge - Lexis Edition (Secured)")
    print(f"   OSC target: {VRC_IP}:{VRC_PORT}")
    print(f"   Listening on: {os.getenv('BRIDGE_HOST', '0.0.0.0')}:{os.getenv('BRIDGE_PORT', 8765)}")
    print(f"   Environment: {FLASK_ENV}")
    print(f"   Debug mode: {DEBUG}")
    print(f"   Authentication: ENABLED (API Key required)")
    print(f"   Rate limiting: ENABLED")
    print()
    print("🔒 Security Features:")
    print("  ✅ API Key authentication on all endpoints")
    print("  ✅ Rate limiting to prevent abuse")
    print("  ✅ Input validation with Pydantic")
    print("  ✅ Audit logging for sensitive operations")
    print("  ✅ Secure temporary file handling")
    print()
    print("Endpoints:")
    print("  GET  /health      - Health check")
    print("  POST /chatbox     - Send chatbox message")
    print("  POST /move        - Move avatar")
    print("  POST /jump        - Jump")
    print("  POST /avatar/parameter - Set avatar param")
    print("  POST /raw         - Raw OSC message (whitelisted)")
    print("  POST /launch      - Join a world (url or world_id)")
    print("  GET  /screenshot  - Capture screen (5/hour limit)")
    print("  POST /listen      - Record audio (10/hour limit)")
    print("  GET  /listen/devices - List audio devices")
    print("  POST /transcribe  - Record + transcribe (10/hour limit)")
    print()
    logger.info("Starting VRChat OSC Bridge")

    app.run(
        host=os.getenv('BRIDGE_HOST', '0.0.0.0'),
        port=int(os.getenv('BRIDGE_PORT', 8765)),
        debug=DEBUG
    )
