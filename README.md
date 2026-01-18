# Prototype App - Personal Second Brain

A wearable-camera scene understanding system that processes video streams to extract observations and provide proactive suggestions.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the `_prototype` directory with the following variables:

```env
# User identification
USER_ID=your_user_id

# Video stream URL (can be RTSP, HTTP, local file, or webcam index)
VIDEO_URL=0  # Use 0 for default webcam, or rtsp://... or http://... or /path/to/video.mp4

# Neo4j Database Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# OpenAI API Key (must be set in your environment or .env)
OPENAI_API_KEY=your_openai_api_key
```

### 3. Start Neo4j Database

Make sure you have Neo4j running. You can:
- Install Neo4j Desktop: https://neo4j.com/download/
- Use Docker: `docker run -p 7474:7474 -p 7687:7687 neo4j:latest`
- Use Neo4j Aura (cloud): https://neo4j.com/cloud/aura/

### 4. Run the Application

From the `_prototype` directory:

```bash
python main.py
```

## Video Stream Options

The `VIDEO_URL` environment variable accepts:

- **Webcam**: `0` (default camera) or `1`, `2`, etc. for other cameras
- **RTSP Stream**: `rtsp://camera-ip:port/stream`
- **HTTP Stream**: `http://camera-ip/video.mjpg`
- **Local Video File**: `/path/to/video.mp4`

## Additional Tools

### Tasks CLI

To add tasks manually:

```bash
python tasks_cli.py
```

This will prompt you for a task title and optional place hint.

## How It Works

1. **Video Processing**: Captures frames from the video stream every 2 seconds
2. **Vision Analysis**: Uses GPT-5.2 vision model to extract:
   - User activity
   - Place context
   - Entities (places, people, objects, apps, topics)
   - Summary
3. **Graph Storage**: Stores observations in Neo4j as events with relationships
4. **Proactive Suggestions**: Every 8 seconds, analyzes recent events, tasks, and routines to suggest actions

## Output

The app prints:
- `[EVENT]` - New observations extracted from frames
- `[PROACTIVE ...]` - Suggestions when relevant
