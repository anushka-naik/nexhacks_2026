// Configuration
const BACKEND_URL = 'http://localhost:5000';
let config = null;
let analysisInterval = null;
let currentChannel = null;

// DOM Elements
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const channelInput = document.getElementById('channelInput');
const statusDiv = document.getElementById('statusDiv');
const resultsDiv = document.getElementById('results');
const videoFrame = document.getElementById('videoFrame');
const streamInfo = document.getElementById('streamInfo');

// Utility Functions
function updateStatus(message, type = 'info') {
    statusDiv.className = `status ${type}`;
    statusDiv.innerHTML = type === 'info' ? `<span class="spinner"></span> ${message}` : message;
}

function updateResults(data) {
    const timestamp = new Date().toLocaleTimeString();
    const formatted = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    resultsDiv.textContent = `[${timestamp}]\n${formatted}\n\n${resultsDiv.textContent}`;
}

// Load configuration from backend
async function loadConfig() {
    try {
        updateStatus('Connecting to backend server...', 'info');
        const response = await fetch(`${BACKEND_URL}/api/config`);
        
        if (!response.ok) {
            throw new Error('Backend server not responding');
        }
        
        config = await response.json();
        updateStatus('Backend connected successfully!', 'success');
        startBtn.disabled = false;
        return true;
    } catch (error) {
        console.error('Config load error:', error);
        updateStatus('❌ Backend not running! Start Flask server first: python twitch_backend.py', 'error');
        startBtn.disabled = true;
        return false;
    }
}

// Get Twitch stream information
async function getStreamInfo(channel) {
    try {
        const response = await fetch(`${BACKEND_URL}/api/twitch/stream-info/${encodeURIComponent(channel)}`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to get stream info');
        }
        
        return await response.json();
    } catch (error) {
        throw new Error(`Twitch API Error: ${error.message}`);
    }
}

// Capture frame from video for analysis
function captureFrame() {
    try {
        // Since we're using an iframe, we'll use a different approach
        // We'll capture the entire iframe area
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Set canvas size to match video frame
        canvas.width = 1280;
        canvas.height = 720;
        
        // Note: Due to CORS restrictions, we can't directly capture iframe content
        // In production, you'd need to use the Twitch Player API or run this on the backend
        
        // For now, return a placeholder - in production this would be actual frame data
        return canvas.toDataURL('image/jpeg', 0.8);
    } catch (error) {
        console.error('Frame capture error:', error);
        return null;
    }
}

// Send frame to Overshoot for analysis
async function analyzeFrame(frameData) {
    try {
        const response = await fetch(`${BACKEND_URL}/api/overshoot/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                frame: frameData,
                prompt: 'Describe what you see in this Twitch stream. Focus on: game being played, actions happening, UI elements, chat activity, and any interesting events.'
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Analysis failed');
        }
        
        return await response.json();
    } catch (error) {
        throw new Error(`Analysis Error: ${error.message}`);
    }
}

// Start continuous analysis
function startAnalysis() {
    // Analyze every 5 seconds
    analysisInterval = setInterval(async () => {
        try {
            updateResults({
                status: 'analyzing',
                message: 'Capturing and analyzing frame...',
                channel: currentChannel
            });
            
            const frameData = captureFrame();
            
            if (frameData) {
                const result = await analyzeFrame(frameData);
                updateResults({
                    status: 'success',
                    channel: currentChannel,
                    analysis: result
                });
            } else {
                updateResults({
                    status: 'info',
                    message: 'Frame capture skipped (CORS limitation - see console)'
                });
            }
        } catch (error) {
            console.error('Analysis cycle error:', error);
            updateResults({
                status: 'error',
                message: error.message
            });
        }
    }, 5000); // Analyze every 5 seconds
}

// Stop analysis
function stopAnalysis() {
    if (analysisInterval) {
        clearInterval(analysisInterval);
        analysisInterval = null;
    }
}

// Start button handler
startBtn.addEventListener('click', async () => {
    const channel = channelInput.value.trim();
    
    if (!channel) {
        updateStatus('Please enter a Twitch channel name', 'error');
        return;
    }
    
    if (!config) {
        updateStatus('Configuration not loaded. Please refresh the page.', 'error');
        return;
    }
    
    try {
        startBtn.disabled = true;
        currentChannel = channel;
        
        updateStatus(`Fetching stream info for ${channel}...`, 'info');
        
        // Get stream information
        const streamData = await getStreamInfo(channel);
        
        if (!streamData.is_live) {
            throw new Error('Stream is offline or channel not found');
        }
        
        // Update UI with stream info
        streamInfo.innerHTML = `
            <div class="live-badge">● LIVE</div>
            <div style="margin-top: 10px;">
                <strong>Title:</strong> ${streamData.title}<br>
                <strong>Game:</strong> ${streamData.game_name}<br>
                <strong>Viewers:</strong> ${streamData.viewer_count.toLocaleString()}
            </div>
        `;
        
        // Load Twitch embed player
        videoFrame.src = streamData.playback_urls.embed_url;
        
        updateStatus(`✅ Streaming ${channel} - AI analysis starting...`, 'success');
        updateResults({
            status: 'started',
            channel: channel,
            stream_info: {
                title: streamData.title,
                game: streamData.game_name,
                viewers: streamData.viewer_count
            }
        });
        
        // Start AI analysis
        startAnalysis();
        
        stopBtn.disabled = false;
        
    } catch (error) {
        console.error('Start error:', error);
        updateStatus(`❌ Error: ${error.message}`, 'error');
        startBtn.disabled = false;
        currentChannel = null;
    }
});

// Stop button handler
stopBtn.addEventListener('click', () => {
    stopAnalysis();
    
    videoFrame.src = '';
    streamInfo.innerHTML = '';
    currentChannel = null;
    
    updateStatus('Stream stopped', 'info');
    updateResults({ status: 'stopped' });
    
    startBtn.disabled = false;
    stopBtn.disabled = true;
});

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    loadConfig();
});