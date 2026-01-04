import random
import time
import uuid
from collections import deque, Counter

from flask import Flask, render_template, request, jsonify, url_for

app = Flask(__name__)

# -----------------------------
# Helpers
# -----------------------------
def now_label():
    return time.strftime("%I:%M:%S %p").lstrip("0")

def touch():
    GAME["updated_at"] = time.time()

# -----------------------------
# Shared one-game state
# -----------------------------
GAME = {
    "called": [],                 # all called balls, e.g. ["B12", "N44", ...]
    "last5": deque(maxlen=5),     # last 5 called
    "remaining": [],              # shuffled deck of remaining balls
    "bingo_calls": deque(maxlen=10),  # recent bingo calls
    "ready": set(),               # set of player_id who are ready
    "reactions": Counter(),       # emoji->count
    "auto_delay": 0,              # seconds
    "auto_enabled": False,
    "updated_at": time.time(),
}

# Store player cards in memory (player_id -> card dict)
PLAYER_CARDS = {}

# -----------------------------
# Bingo deck + card generation
# -----------------------------
def build_deck():
    deck = []
    for n in range(1, 16):
        deck.append(f"B{n}")
    for n in range(16, 31):
        deck.append(f"I{n}")
    for n in range(31, 46):
        deck.append(f"N{n}")
    for n in range(46, 61):
        deck.append(f"G{n}")
    for n in range(61, 76):
        deck.append(f"O{n}")
    random.shuffle(deck)
    return deck

def new_game():
    GAME["called"].clear()
    GAME["last5"].clear()
    GAME["remaining"] = build_deck()
    GAME["bingo_calls"].clear()
    GAME["ready"].clear()
    GAME["reactions"].clear()
    GAME["auto_delay"] = 0
    GAME["auto_enabled"] = False
    touch()

def generate_card():
    # Classic 5x5 with FREE center
    cols = {
        "B": random.sample(range(1, 16), 5),
        "I": random.sample(range(16, 31), 5),
        "N": random.sample(range(31, 46), 5),
        "G": random.sample(range(46, 61), 5),
        "O": random.sample(range(61, 76), 5),
    }
    # Make a 5x5 grid in row-major order
    grid = []
    for r in range(5):
        row = [
            cols["B"][r],
            cols["I"][r],
            cols["N"][r],
            cols["G"][r],
            cols["O"][r],
        ]
        grid.append(row)
    grid[2][2] = "FREE"
    return grid

def get_next_ball():
    if not GAME["remaining"]:
        return None
    ball = GAME["remaining"].pop(0)
    return ball

# initialize a fresh game at startup
new_game()

# -----------------------------
# Pages
# -----------------------------
@app.route("/")
def home():
    # Just redirect the root to the caller page
    return """
    <script>
      window.location.href = "/caller";
    </script>
    """


@app.route("/caller")
def caller_page():
    return render_template("caller.html")

@app.route("/player")
def player_redirect():
    # Create a player id and redirect to that player's page
    player_id = "p_" + uuid.uuid4().hex[:10]
    PLAYER_CARDS[player_id] = generate_card()
    touch()
    return render_template("player.html", player_id=player_id, card=PLAYER_CARDS[player_id])

@app.route("/player/<player_id>")
def player_page(player_id):
    if player_id not in PLAYER_CARDS:
        # If someone refreshes with unknown id, make them a card anyway
        PLAYER_CARDS[player_id] = generate_card()
        touch()
    return render_template("player.html", player_id=player_id, card=PLAYER_CARDS[player_id])

# -----------------------------
# API: shared state
# -----------------------------
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
        "remaining_count": len(GAME["remaining"]),
    })

# -----------------------------
# API: host actions
# -----------------------------
@app.route("/api/next", methods=["POST"])
def api_next():
    data = request.get_json(silent=True) or {}
    min_ready = int(data.get("min_ready", 0))

    if len(GAME["ready"]) < min_ready:
        return jsonify({"ok": False, "reason": "not_ready", "ready_count": len(GAME["ready"])}), 409

    ball = get_next_ball()
    if not ball:
        return jsonify({"ok": False, "reason": "no_balls_left"}), 409

    GAME["called"].append(ball)
    GAME["last5"].append(ball)

    # reset readiness after each call
    GAME["ready"].clear()

    touch()
    return jsonify({"ok": True, "ball": ball, "last5": list(GAME["last5"])})

@app.route("/api/auto", methods=["POST"])
def api_auto():
    data = request.get_json(silent=True) or {}
    GAME["auto_delay"] = int(data.get("delay", 0))
    GAME["auto_enabled"] = bool(data.get("enabled", False))
    touch()
    return jsonify({"ok": True})

@app.route("/api/new_game", methods=["POST"])
def api_new_game():
    new_game()
    return jsonify({"ok": True})

# -----------------------------
# API: player actions
# -----------------------------
@app.route("/api/ready", methods=["POST"])
def api_ready():
    data = request.get_json(silent=True) or {}
    player_id = str(data.get("player_id", "unknown"))
    ready = bool(data.get("ready", True))

    if ready:
        GAME["ready"].add(player_id)
    else:
        GAME["ready"].discard(player_id)

    touch()
    return jsonify({"ok": True, "ready_count": len(GAME["ready"])})

@app.route("/api/bingo", methods=["POST"])
def api_bingo():
    data = request.get_json(silent=True) or {}
    player_id = str(data.get("player_id", "unknown"))

    GAME["bingo_calls"].appendleft({
        "player_id": player_id,
        "time": now_label(),
    })
    touch()
    return jsonify({"ok": True})

@app.route("/api/reaction", methods=["POST"])
def api_reaction():
    data = request.get_json(silent=True) or {}
    emoji = str(data.get("emoji", "👀"))
    GAME["reactions"][emoji] += 1
    touch()
    return jsonify({"ok": True, "reactions": dict(GAME["reactions"])})

@app.route("/api/new_player_card", methods=["POST"])
def api_new_player_card():
    data = request.get_json(silent=True) or {}
    player_id = str(data.get("player_id", ""))

    # If player_id not provided, create a new player
    if not player_id:
        player_id = "p_" + uuid.uuid4().hex[:10]

    PLAYER_CARDS[player_id] = generate_card()
    touch()
    return jsonify({
        "ok": True,
        "player_id": player_id,
        "url": url_for("player_page", player_id=player_id)
    })

if __name__ == "__main__":
    app.run(debug=True)

