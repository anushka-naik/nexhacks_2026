from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
import os
import subprocess
import os.path as osp


app = Flask(__name__)
CORS(app)


def send_imessage_observation_notification(user_id: str, summary: str):
    phone = os.environ.get("IMESSAGE_PHONE")
    if not phone:
        return False

    script_path = osp.join(osp.dirname(osp.dirname(__file__)), "imessage_notify.js")
    message = f"New observation for {user_id}: {summary}"[:240]

    try:
        result = subprocess.run(
            ["node", script_path, phone, message],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        err = f"Error running iMessage script: {e}"
        print(err)
        return False, "", err


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})


@app.route("/demo-imessage", methods=["GET", "POST"])
def demo_imessage():
    user_id = request.args.get("user_id", "demo_user")
    message = request.args.get("message", "This is a demo iMessage notification.")

    ok, out, err = send_imessage_observation_notification(user_id=user_id, summary=message)
    if not ok:
        return jsonify({"success": False, "error": "IMESSAGE_PHONE not configured, or send failed", "stdout": out, "stderr": err}), 500

    return jsonify(
        {
            "success": True,
            "user_id": user_id,
            "message": message,
            "stdout": out,
            "stderr": err,
        }
    ), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
