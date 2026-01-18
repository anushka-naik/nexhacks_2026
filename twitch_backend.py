from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# Twitch API Credentials
CLIENT_ID = "6jxxo9vhq12twxx93aio8jnzdqnl09"
CLIENT_SECRET = "3zj2vvcgn98tc8d3pqnrvpzwb4a974"

# API Keys
OPENAI_API_KEY = "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"
OVERSHOOT_API_KEY = "ovs_3772889fffcda11d2bf1af93acc126a3"

# Cache for Twitch token
_twitch_token = None

def get_twitch_token():
    """Get and cache Twitch OAuth token"""
    global _twitch_token
    
    if _twitch_token:
        return _twitch_token
    
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    
    try:
        resp = requests.post(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        _twitch_token = data['access_token']
        return _twitch_token
    except Exception as e:
        print(f"Error getting Twitch token: {e}")
        return None

@app.route('/api/config', methods=['GET'])
def get_config():
    """Return API keys to the client"""
    return jsonify({
        "openai_key": OPENAI_API_KEY,
        "overshoot_key": OVERSHOOT_API_KEY,
        "twitch_client_id": CLIENT_ID
    })

@app.route('/api/twitch/stream-info/<channel>', methods=['GET'])
def get_stream_info(channel):
    """Get Twitch stream information and playback URL"""
    token = get_twitch_token()
    
    if not token:
        return jsonify({"error": "Failed to authenticate with Twitch"}), 500
    
    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }
    
    try:
        # Get stream info to check if channel is live
        streams_url = f"https://api.twitch.tv/helix/streams?user_login={channel}"
        streams_resp = requests.get(streams_url, headers=headers, timeout=10)
        streams_resp.raise_for_status()
        
        stream_data = streams_resp.json()
        
        if not stream_data.get('data'):
            return jsonify({
                "error": "Stream is offline or channel not found",
                "is_live": False
            }), 404
        
        stream_info = stream_data['data'][0]
        
        # Return stream info and playback URL
        return jsonify({
            "is_live": True,
            "channel": channel,
            "title": stream_info.get('title', ''),
            "viewer_count": stream_info.get('viewer_count', 0),
            "game_name": stream_info.get('game_name', ''),
            "thumbnail_url": stream_info.get('thumbnail_url', ''),
            # Multiple playback options for reliability
            "playback_urls": {
                # Embedding approach (most reliable)
                "embed_url": f"https://player.twitch.tv/?channel={channel}&parent=localhost&muted=true",
                # HLS approach (requires token)
                "hls_url": f"https://usher.ttvnw.net/api/channel/hls/{channel}.m3u8?client_id={CLIENT_ID}&token={token}&sig=&allow_source=true&fast_bread=true"
            },
            "token": token,
            "client_id": CLIENT_ID
        })
        
    except Exception as e:
        print(f"Error getting stream info: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/overshoot/analyze', methods=['POST'])
def analyze_frame():
    """Send frame to Overshoot API for analysis"""
    try:
        data = request.json
        frame_data = data.get('frame')
        prompt = data.get('prompt', 'Describe what you see in this frame')
        
        if not frame_data:
            return jsonify({"error": "No frame data provided"}), 400
        
        # Call Overshoot API
        overshoot_url = "https://cluster1.overshoot.ai/api/v0.2/analyze"
        headers = {
            "Authorization": f"Bearer {OVERSHOOT_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "image": frame_data,
            "prompt": prompt
        }
        
        response = requests.post(overshoot_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                "error": f"Overshoot API error: {response.status_code}",
                "details": response.text
            }), response.status_code
            
    except Exception as e:
        print(f"Error in analyze_frame: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "twitch-overshoot-backend"})

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Twitch + Overshoot Backend Server")
    print("=" * 60)
    print("📡 Server starting on http://localhost:5000")
    print("📚 Endpoints:")
    print("   - GET  /api/config")
    print("   - GET  /api/twitch/stream-info/<channel>")
    print("   - POST /api/overshoot/analyze")
    print("   - GET  /health")
    print("=" * 60)
    print("⚠️  Make sure to install: pip install flask flask-cors requests")
    print("=" * 60)
    app.run(debug=True, port=5000, host='0.0.0.0')