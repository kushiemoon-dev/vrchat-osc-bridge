#!/usr/bin/env python3
"""
Lexis VRChat Control - Client side
Runs on Lexis's server to send commands to the bridge.
"""

import urllib.request
import urllib.error
import json
import sys

# Bridge configuration
BRIDGE_HOST = "localhost"
BRIDGE_PORT = 8765
BRIDGE_URL = f"http://{BRIDGE_HOST}:{BRIDGE_PORT}"

def send_command(endpoint, data=None):
    """Send a command to the bridge"""
    url = f"{BRIDGE_URL}{endpoint}"
    
    if data is None:
        data = {}
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.URLError as e:
        return {"error": str(e)}

def health_check():
    """Check if bridge is running"""
    try:
        req = urllib.request.Request(f"{BRIDGE_URL}/health")
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except:
        return {"error": "Bridge not reachable"}

def chatbox(message, direct=True, notify=True):
    """Send a message to VRChat chatbox"""
    return send_command("/chatbox", {
        "message": message,
        "direct": direct,
        "notify": notify
    })

def typing(is_typing=True):
    """Show typing indicator"""
    return send_command("/chatbox/typing", {"typing": is_typing})

def move(vertical=0, horizontal=0, look=0, duration=0.5):
    """Move the avatar"""
    return send_command("/move", {
        "vertical": vertical,
        "horizontal": horizontal,
        "look": look,
        "duration": duration
    })

def jump():
    """Jump!"""
    return send_command("/jump", {})

def run(running=True):
    """Toggle running"""
    return send_command("/run", {"running": running})

def set_parameter(name, value):
    """Set avatar parameter"""
    return send_command("/avatar/parameter", {
        "name": name,
        "value": value
    })

def raw_osc(address, args):
    """Send raw OSC message"""
    return send_command("/raw", {
        "address": address,
        "args": args
    })

# Quick test
if __name__ == "__main__":
    print("🦊 Lexis VRChat Control")
    print(f"   Bridge: {BRIDGE_URL}")
    print()
    
    # Health check
    result = health_check()
    if "error" in result:
        print(f"❌ Bridge not reachable: {result['error']}")
        sys.exit(1)
    
    print("✅ Bridge connected!")
    
    # Test chatbox
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        print(f"📤 Sending: {message}")
        result = chatbox(message)
        print(f"   Result: {result}")
    else:
        print()
        print("Usage: python lexis_control.py <message>")
        print("   or import and use functions directly")
