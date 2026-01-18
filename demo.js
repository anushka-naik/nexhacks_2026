import { RealtimeVision } from '@overshoot/sdk';

const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const resultsDiv = document.getElementById('results');
const video = document.getElementById('video');

let vision;
let interactionStartTime;

startBtn.addEventListener('click', async () => {
    try {
        resultsDiv.textContent = 'Initializing...';
        interactionStartTime = Date.now();
        
        vision = new RealtimeVision({
            apiUrl: 'https://cluster1.overshoot.ai/api/v0.2',
            apiKey: 'ovs_3772889fffcda11d2bf1af93acc126a3', 
            prompt: `You are creating a factual memory log. Record only observable, concrete details of people, objects, and actions currently in focus.

PEOPLE: Height (tall/average/short), build (slim/average/heavy), facial hair (beard/mustache/clean-shaven), hair (color, length, style), age estimate, clothing (colors, types like "blue shirt", "black jacket"), glasses, accessories.

OBJECTS: Item name, color, size (large/small), material (metal/plastic/wood/glass), condition (new/old/worn), current state ("open laptop", "closed book", "half-full mug").

ACTIONS: Use clear action verbs - "picked up phone", "placed mug on table", "typing on keyboard", "reading document", "standing up", "walking toward door".

ENVIRONMENT: Room type (office/kitchen/bedroom), furniture present (desk/chair/table), lighting (bright/dim).

SEQUENCE OF EVENTS: Track order of actions - "first opened laptop, then placed coffee beside it, then started typing".

REPETITION/FREQUENCY: Note repeated actions - "checked phone 3 times", "refilled water bottle twice in 10 minutes".

VISIBLE TEXT/LABELS: Read and record any text - brand names, document titles, signs, screen content, labels, logos, writing on objects.

POSITION CHANGES: Track object movement - "laptop moved from desk to lap", "chair pulled closer to table", "book relocated from shelf to desk".

CONSUMPTION/USAGE: Record state changes - "mug was full, now half-empty", "bottle opened", "food partially eaten", "paper stack reduced".

BEFORE/AFTER STATES: Note transformations - "door was closed, now open", "lights were off, now on", "screen was blank, now displaying content".

IDENTIFYING MARKERS: Capture unique identifiers - room numbers, name badges, ID cards, license plates, serial numbers, distinctive logos or symbols.

TIME: Mark timestamp for each observation and note duration when relevant.

Write factual descriptions as memory entries. No subjective interpretations. Focus on what can be definitively seen and would be useful to remember later.`,
            onResult: async (result) => {
                console.log('Overshoot Result:', result);
                const structuredData = await transformToStructuredFormat(result.result);
                console.log('Structured Data:', structuredData);

                try {
                    const resp = await fetch("http://localhost:5000/overshoot_event", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify(structuredData)
                    });
                    const saved = await resp.json();
                    console.log('Saved to backend:', saved);
                    resultsDiv.textContent = JSON.stringify(saved, null, 2);
                } catch (err) {
                    console.error('Backend save error:', err);
                    resultsDiv.textContent = 'Backend error: ' + err.message;
                }
            }
        });

        await vision.start();
        
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
        
        startBtn.disabled = true;
        stopBtn.disabled = false;
        resultsDiv.textContent = 'Camera started. Results will appear here...';
        
    } catch (error) {
        console.error('Error:', error);
        resultsDiv.textContent = 'Error: ' + error.message;
    }
});

stopBtn.addEventListener('click', async () => {
    try {
        await vision.stop();
        
        const stream = video.srcObject;
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            video.srcObject = null;
        }
        
        startBtn.disabled = false;
        stopBtn.disabled = true;
        resultsDiv.textContent = 'Camera stopped.';
        
    } catch (error) {
        console.error('Error:', error);
    }
});

imessageBtn.addEventListener('click', async () => {
    try {
        resultsDiv.textContent = 'Sending demo iMessage...';
        const resp = await fetch("http://localhost:5000/demo-imessage", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: "This is a test message triggered from the Frontend Demo!" })
        });
        const data = await resp.json();
        if (resp.ok) {
            resultsDiv.textContent = 'iMessage sent! ' + JSON.stringify(data, null, 2);
        } else {
            resultsDiv.textContent = 'Error sending iMessage: ' + data.error + (data.details ? ' ' + data.details : '');
        }
    } catch (err) {
        console.error('iMessage error:', err);
        resultsDiv.textContent = 'Error: ' + err.message;
    }
});

async function transformToStructuredFormat(overshootOutput) {
    try {
        const interactionDuration = (Date.now() - interactionStartTime) / 1000;
        
        const response = await fetch("https://api.openai.com/v1/chat/completions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
             
            },
            body: JSON.stringify({
                model: "gpt-4o",
                messages: [
                    {
                        role: "user",
                        content: `Transform this vision observation into the exact JSON structure below. Extract objects, colors, models, and location type from the description.

Vision observation: ${JSON.stringify(overshootOutput)}

Required JSON structure:
{
  "user_id": "user_001",
  "timestamp": "${new Date().toISOString()}",
  "vision": {
    "objects": ["list of objects seen"],
    "approx_model": "approximate model/type if identifiable",
    "color": "dominant colors",
    "confidence": 0.85
  },
  "video": {
    "intent": "observing",
    "keywords": ["relevant", "keywords"],
    "sentiment": "neutral"
  },
  "context": {
    "location_type": "home|office|dealership|outdoors|unknown",
    "interaction_duration_sec": ${interactionDuration}
  }
}

Return ONLY valid JSON, no markdown, no explanation.`
                    }
                ],
                temperature: 0.3
            })
        });

        const data = await response.json();
        const jsonText = data.choices[0].message.content
            .replace(/```json|```/g, "")
            .trim();
        
        return JSON.parse(jsonText);
        
    } catch (error) {
        console.error('Transform error:', error);
        // Fallback structure
        return {
            user_id: "user_001",
            timestamp: new Date().toISOString(),
            vision: {
                objects: ["error transforming"],
                confidence: 0
            },
            video: {
                intent: "error"
            },
            context: {
                location_type: "unknown",
                interaction_duration_sec: (Date.now() - interactionStartTime) / 1000
            }
        };
    }
}
