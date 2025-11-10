import os
import json
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

# --- App Initialization ---
load_dotenv() # Make sure this is here
bot_token = os.environ.get("SLACK_BOT_TOKEN")
print(f"--- Is the bot token loaded? '{bot_token}' ---") # DEBUG LINE
app = App(token=bot_token)
SCORES_FILE = "leaderboard_scores.json"
TARGET_CHANNEL_ID = "C09LEUNKN30"

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
        is_image_posted = any(file.get("mimetype", "").startswith("image/") for file in files)

        if is_image_posted:
            logger.info(f"Image detected from user {user_id} in channel {channel_id}")
            scores = load_scores()
            scores[user_id] = scores.get(user_id, 0) + 1
            save_scores(scores)
            # Optional: React to the message to show it was counted
            try:
                client.reactions_add(
                    channel=channel_id,
                    timestamp=event["ts"],
                    name="white_check_mark"
                )
            except Exception as e:
                logger.error(f"Error adding reaction: {e}")


# --- Slash Command for Leaderboard ---

@app.command("/leaderboard")
def show_leaderboard(ack, say, command, client):
    ack()
    
    scores = load_scores()
    
    if not scores:
        say("The leaderboard is empty! Start posting images to get on the board.")
        return
    sorted_users = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    leaderboard_text = "*🏆 Image Leaderboard 🏆*\n\n"
    for i, (user_id, score) in enumerate(sorted_users):
        try:
            user_info = client.users_info(user=user_id)
            user_name = user_info["user"]["profile"]["display_name"] or user_info["user"]["name"]
            if i == 0:
                leaderboard_text += f"🥇 1. {user_name}: *{score} points*\n"
            elif i == 1:
                leaderboard_text += f"🥈 2. {user_name}: *{score} points*\n"
            elif i == 2:
                leaderboard_text += f"🥉 3. {user_name}: *{score} points*\n"
            else:
                leaderboard_text += f"   {i + 1}. {user_name}: {score} points\n"
        
        except Exception as e:
            leaderboard_text += f"   {i + 1}. Unknown User ({user_id}): {score} points\n"
            print(f"Could not fetch user info for {user_id}: {e}")

    say(leaderboard_text)


# --- Starting the Bot ---

if __name__ == "__main__":
    print("🤖 Bot is starting...")
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()