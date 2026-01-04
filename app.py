from flask import Flask, render_template, request, redirect, url_for
import time
from collections import deque, Counter
from flask import jsonify

# -----------------------------
# Shared Game State (one room)
# -----------------------------
GAME = {
    "called": [],                      # full history
    "last5": deque(maxlen=5),           # last 5 called
    "bingo_calls": deque(maxlen=10),    # recent bingo calls (timestamps etc)
    "ready": set(),                    # players who clicked Ready (store player_id)
    "reactions": Counter(),            # emoji->count
    "auto_delay": 0,                   # seconds (0 means manual)
    "auto_enabled": False,             # auto-call on/off
    "updated_at": time.time(),         # simple change marker
}
def touch_game():
    GAME["updated_at"] = time.time()
@app.route("/api/state")
def api_state():
    return jsonify({
        "called": GAME["called"],
        "last5": list(GAME["last5"]),
        "bingo_calls": list(GAME["bingo_calls"]),
        "ready_count": len(GAME["ready"]),
        "reactions": dict(GAME["reactions"]),
        "auto_delay": GAME["auto_delay"],
        "auto_enabled": GAME["auto_enabled"],
        "updated_at": GAME["updated_at"],
    })
@app.route("/api/ready", methods=["POST"])
def api_ready():
    data = request.get_json(force=True)
    player_id = str(data.get("player_id", "unknown"))
    is_ready = bool(data.get("ready", True))

    if is_ready:
        GAME["ready"].add(player_id)
    else:
        GAME["ready"].discard(player_id)

    touch_game()
    return jsonify({"ok": True, "ready_count": len(GAME["ready"])})
@app.route("/api/bingo", methods=["POST"])
def api_bingo():
    data = request.get_json(force=True)
    player_id = str(data.get("player_id", "unknown"))
    card_id = str(data.get("card_id", ""))

    ts = time.strftime("%I:%M:%S %p").lstrip("0")
    GAME["bingo_calls"].appendleft({
        "player_id": player_id,
        "card_id": card_id,
        "time": ts
    })

    touch_game()
    return jsonify({"ok": True})
@app.route("/api/reaction", methods=["POST"])
def api_reaction():
    data = request.get_json(force=True)
    emoji = str(data.get("emoji", "👀"))

    # Count it
    GAME["reactions"][emoji] += 1

    touch_game()
    return jsonify({"ok": True, "reactions": dict(GAME["reactions"])})
@app.route("/api/auto", methods=["POST"])
def api_auto():
    data = request.get_json(force=True)
    GAME["auto_delay"] = int(data.get("delay", 0))
    GAME["auto_enabled"] = bool(data.get("enabled", False))
    touch_game()
    return jsonify({"ok": True})
@app.route("/api/auto", methods=["POST"])
def api_auto():
    data = request.get_json(force=True)
    GAME["auto_delay"] = int(data.get("delay", 0))
    GAME["auto_enabled"] = bool(data.get("enabled", False))
    touch_game()
    return jsonify({"ok": True})
@app.route("/api/next", methods=["POST"])
def api_next():
    data = request.get_json(force=True)
    min_ready = int(data.get("min_ready", 0))  # set to your player count if you want "all ready"

    # Gate calling next ball if not enough are ready
    if len(GAME["ready"]) < min_ready:
        return jsonify({"ok": False, "reason": "not_ready", "ready_count": len(GAME["ready"])}), 409

    # --- CALL YOUR EXISTING LOGIC HERE ---
    # Example: new_ball = get_next_ball()
    new_ball = get_next_ball()  # <-- rename this to your actual function

    if not new_ball:
        return jsonify({"ok": False, "reason": "no_balls_left"}), 409

    GAME["called"].append(new_ball)
    GAME["last5"].append(new_ball)

    # When a ball is called, reset readiness (so players must confirm again)
    GAME["ready"].clear()

    touch_game()
    return jsonify({"ok": True, "ball": new_ball, "last5": list(GAME["last5"])})


app = Flask(__name__)

# -----------------------------
# Bingo Card Generator
# -----------------------------
def generate_card():
    card = {}
    ranges = {
        "B": range(1, 16),
        "I": range(16, 31),
        "N": range(31, 46),
        "G": range(46, 61),
        "O": range(61, 76)
    }

    for letter, nums in ranges.items():
        card[letter] = random.sample(list(nums), 5)

    card["N"][2] = "FREE"
    return card


# -----------------------------
# Home / Bingo Page
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form["name"]
        count = int(request.form["count"])

        prefix = name.upper().replace(" ", "")[:5]
        cards = []

        for i in range(1, count + 1):
            card_id = f"{prefix}-{i:02d}"
            cards.append({
                "id": card_id,
                "data": generate_card()
            })

        return render_template("cards.html", name=name, cards=cards)

    return render_template("index.html")


# -----------------------------
# SHORT LINK → PLAY (PUBLIC)
# https://your-site.onrender.com/play
# -----------------------------
@app.route("/play")
def play():
    return redirect(url_for("index"))


# -----------------------------
# PRIVATE CALLER PAGE (HIDDEN)
# https://your-site.onrender.com/bingo-admin
# -----------------------------
@app.route("/bingo-admin")
def caller():
    return render_template("caller.html")


# -----------------------------
# OPTIONAL: SHORT LINK → DISCORD
# -----------------------------
# DISCORD_INVITE_URL = "https://discord.gg/YOURCODE"
#
# @app.route("/discord")
# def discord():
#     return redirect(DISCORD_INVITE_URL)


# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    app.run()
