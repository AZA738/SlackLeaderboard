import os
import json
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

# --- App Initialization ---
load_dotenv() # Make sure this is here
bot_token = os.environ.get("SLACK_BOT_TOKEN")
print(f"--- Is the bot token loaded? '{bot_token}' ---") # DEBUG LINE
app = App(token=bot_token)
SCORES_FILE = "leaderboard_scores.json"
SNIPED_FILE = "sniped_scores.json"
TARGET_CHANNEL_ID = "C09LEUNKN30"

# --- Helper functions ---
def load_json(path):
    """Loads a JSON file or returns an empty dict if missing."""
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    """Saves data to a JSON file."""
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

# --- Data Handling Functions ---

def load_scores():
    """Loads scores from the JSON file. If the file doesn't exist, returns an empty dictionary."""
    if not os.path.exists(SCORES_FILE):
        return {}
    with open(SCORES_FILE, "r") as f:
        return json.load(f)

def save_scores(scores):
    """Saves the scores dictionary to the JSON file."""
    with open(SCORES_FILE, "w") as f:
        json.dump(scores, f, indent=4)

# --- Event Listener for Images ---

@app.event("message")
def handle_message_events(body, logger, client):
    """Listens for any message and checks if it's an image in the target channel."""
    event = body.get("event", {})
    channel_id = event.get("channel")
    user_id = event.get("user")

    if channel_id == TARGET_CHANNEL_ID and user_id:
        files = event.get("files", [])
        text = event.get("text", "")
        is_image_posted = any(file.get("mimetype", "").startswith("image/") for file in files)

        if is_image_posted:
            # Find mentioned users in the text
            mentioned_users = re.findall(r"<@([A-Z0-9]+)>", text)

            if not mentioned_users:
                client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=event["ts"],
                    text="⚠️ Please tag the person you sniped using @username!"
                )
                return

            # Update sniper's score
            sniper_scores = load_json(SCORES_FILE)
            sniper_scores[user_id] = sniper_scores.get(user_id, 0) + 1
            save_json(SCORES_FILE, sniper_scores)

            # Update sniped users’ scores
            sniped_scores = load_json(SNIPED_FILE)
            for sniped_id in mentioned_users:
                sniped_scores[sniped_id] = sniped_scores.get(sniped_id, 0) + 1
                save_json(SNIPED_FILE, sniped_scores)

            try:
                client.reactions_add(
                    channel=channel_id,
                    timestamp=event["ts"],
                    name="white_check_mark"
                )
            except Exception as e:
                logger.error(f"Error adding reaction: {e}")


# --- /leaderboard (snipers) ---
@app.command("/leaderboard")
def show_leaderboard(ack, say, command, client):
    ack()
    show_scoreboard(say, client, SCORES_FILE, "🏆 *Sniper Leaderboard* 🏆", "snipes")

# --- /snipedboard (sniped) ---
@app.command("/snipedboard")
def show_snipedboard(ack, say, command, client):
    ack()
    show_scoreboard(say, client, SNIPED_FILE, "🎯 *Sniped Leaderboard* 🎯", "times caught lacking")

# --- Shared leaderboard display ---
def show_scoreboard(say, client, file_path, title, unit):
    scores = load_json(file_path)
    if not scores:
        say(f"The {title.lower()} is empty!")
        return

    sorted_users = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    text = f"{title}\n\n"
    for i, (uid, score) in enumerate(sorted_users):
        try:
            user_info = client.users_info(user=uid)
            name = user_info["user"]["profile"]["display_name"] or user_info["user"]["name"]
        except:
            name = f"Unknown ({uid})"
        medals = ["🥇", "🥈", "🥉"]
        medal = medals[i] if i < 3 else "  "
        text += f"{medal} {i+1}. {name}: *{score} {unit}*\n"

    say(text)


# --- Starting the Bot ---

if __name__ == "__main__":
    print("🤖 Bot is starting...")
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()