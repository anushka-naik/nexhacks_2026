import streamlink
import cv2

# Twitch stream URL
twitch_url = "https://www.twitch.tv/ishowspeed"

# Open stream
streams = streamlink.streams(twitch_url)
stream = streams["best"]  # or "720p", "480p", etc.

# Get the actual video URL
stream_url = stream.to_url()

cap = cv2.VideoCapture(stream_url)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    cv2.imshow("Twitch Stream", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
