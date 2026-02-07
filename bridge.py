#!/usr/bin/env python3
"""
VRChat OSC Bridge - Lexis Edition 🦊
Receives HTTP commands and forwards them to VRChat via OSC.

Run on the machine where VRChat is running.
Requires: pip install python-osc flask
"""

from flask import Flask, request, jsonify, send_file
from pythonosc import udp_client
import time
import io
import subprocess
import webbrowser

# Try to import screenshot library
try:
    from PIL import ImageGrab
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False
    print("⚠️  PIL not installed - screenshot disabled. Run: pip install Pillow")

app = Flask(__name__)

# VRChat OSC settings (localhost because VRChat only listens locally)
VRC_IP = "127.0.0.1"
VRC_PORT = 9000
osc = udp_client.SimpleUDPClient(VRC_IP, VRC_PORT)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "vrchat-bridge"})

@app.route('/chatbox', methods=['POST'])
def chatbox():
    """Send a message to VRChat chatbox"""
    data = request.json
    message = data.get('message', '')
    direct = data.get('direct', True)  # True = send immediately, False = open keyboard
    notify = data.get('notify', True)  # Play notification sound
    
    # /chatbox/input s b n
    osc.send_message("/chatbox/input", [message, direct, notify])
    return jsonify({"status": "sent", "message": message})

@app.route('/chatbox/typing', methods=['POST'])
def chatbox_typing():
    """Toggle typing indicator"""
    data = request.json
    typing = data.get('typing', True)
    osc.send_message("/chatbox/typing", typing)
    return jsonify({"status": "ok", "typing": typing})

@app.route('/move', methods=['POST'])
def move():
    """Move the avatar"""
    data = request.json
    vertical = data.get('vertical', 0)      # -1 to 1 (back to forward)
    horizontal = data.get('horizontal', 0)  # -1 to 1 (left to right)
    look = data.get('look', 0)              # -1 to 1 (turn left/right)
    duration = data.get('duration', 0.5)    # How long to move (seconds)
    
    # Send movement
    osc.send_message("/input/Vertical", float(vertical))
    osc.send_message("/input/Horizontal", float(horizontal))
    if look != 0:
        osc.send_message("/input/LookHorizontal", float(look))
    
    # Hold for duration
    if duration > 0:
        time.sleep(duration)
        # Reset to stop moving
        osc.send_message("/input/Vertical", 0.0)
        osc.send_message("/input/Horizontal", 0.0)
        osc.send_message("/input/LookHorizontal", 0.0)
    
    return jsonify({"status": "moved", "vertical": vertical, "horizontal": horizontal})

@app.route('/jump', methods=['POST'])
def jump():
    """Make the avatar jump"""
    osc.send_message("/input/Jump", 1)
    time.sleep(0.1)
    osc.send_message("/input/Jump", 0)
    return jsonify({"status": "jumped"})

@app.route('/run', methods=['POST'])
def run():
    """Toggle running"""
    data = request.json
    running = data.get('running', True)
    osc.send_message("/input/Run", 1 if running else 0)
    return jsonify({"status": "ok", "running": running})

@app.route('/avatar/parameter', methods=['POST'])
def avatar_parameter():
    """Set an avatar parameter (for expressions, etc)"""
    data = request.json
    param_name = data.get('name', '')
    value = data.get('value', 0)
    
    osc.send_message(f"/avatar/parameters/{param_name}", value)
    return jsonify({"status": "set", "parameter": param_name, "value": value})

@app.route('/voice', methods=['POST'])
def voice():
    """Toggle voice/mute"""
    data = request.json
    unmute = data.get('unmute', True)
    osc.send_message("/input/Voice", 1 if unmute else 0)
    return jsonify({"status": "ok", "unmute": unmute})

@app.route('/raw', methods=['POST'])
def raw_osc():
    """Send a raw OSC message"""
    data = request.json
    address = data.get('address', '')
    args = data.get('args', [])
    
    osc.send_message(address, args)
    return jsonify({"status": "sent", "address": address, "args": args})

@app.route('/launch', methods=['POST'])
def launch_world():
    """Launch a VRChat world by URL or world ID"""
    data = request.json
    url = data.get('url', '')
    world_id = data.get('world_id', '')
    
    if url:
        # Direct URL (vrchat://launch?... or https://vrchat.com/home/world/...)
        launch_url = url
        if url.startswith('https://vrchat.com/home/world/'):
            # Convert web URL to launch URL
            # Extract world ID from URL like https://vrchat.com/home/world/wrld_xxx
            parts = url.split('/')
            for i, part in enumerate(parts):
                if part.startswith('wrld_'):
                    world_id = part
                    break
    
    if world_id and not url:
        launch_url = f"vrchat://launch?ref=vrchat.com&id={world_id}"
    elif not url:
        return jsonify({"error": "Provide 'url' or 'world_id'"}), 400
    
    try:
        # Open the VRChat URL - this will trigger VRChat to join the world
        webbrowser.open(launch_url)
        return jsonify({"status": "launched", "url": launch_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/screenshot', methods=['GET'])
def screenshot():
    """Capture and return a screenshot"""
    if not SCREENSHOT_AVAILABLE:
        return jsonify({"error": "PIL not installed. Run: pip install Pillow"}), 500
    
    try:
        # Capture the screen
        img = ImageGrab.grab()
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=70)
        img_bytes.seek(0)
        
        return send_file(img_bytes, mimetype='image/jpeg')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🦊 VRChat OSC Bridge - Lexis Edition")
    print(f"   OSC target: {VRC_IP}:{VRC_PORT}")
    print(f"   Listening on: 0.0.0.0:8765")
    print()
    print("Endpoints:")
    print("  POST /chatbox     - Send chatbox message")
    print("  POST /move        - Move avatar")
    print("  POST /jump        - Jump")
    print("  POST /avatar/parameter - Set avatar param")
    print("  POST /raw         - Raw OSC message")
    print("  POST /launch      - Join a world (url or world_id)")
    print("  GET  /screenshot  - Capture screen (needs Pillow)")
    print()
    app.run(host='0.0.0.0', port=8765, debug=False)
