import random
import time
import uuid
from collections import deque, Counter

from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)

# -----------------------------
# One shared game state (single room)
# -----------------------------
GAME = {
    "called": [],                 # full history e.g. ["B12","N44",...]
    "last5": deque(maxlen=5),     # last 5 called
    "remaining": [],              # shuffled deck
    "bingo_calls": deque(maxlen=15),
    "ready": set(),               # player_ids who clicked ready
    "reactions": Counter(),       # emoji -> count
    "auto_delay": 0,              # seconds
    "auto_enabled": False,
    "updated_at": time.time(),
}

# player_id -> {"name": str, "cards": [5x5grid, ...]}
PLAYERS = {}


# -----------------------------
# Helpers
# -----------------------------
def touch():
    GAME["updated_at"] = time.time()


def now_label():
    return time.strftime("%I:%M:%S %p").lstrip("0")


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
    # Classic 5x5 bingo card with FREE center
    cols = {
        "B": random.sample(range(1, 16), 5),
        "I": random.sample(range(16, 31), 5),
        "N": random.sample(range(31, 46), 5),
        "G": random.sample(range(46, 61), 5),
        "O": random.sample(range(61, 76), 5),
    }
    grid = []
    for r in range(5):
        grid.append([cols["B"][r], cols["I"][r], cols["N"][r], cols["G"][r], cols["O"][r]])
    grid[2][2] = "FREE"
    return grid


def get_next_ball():
    if not GAME["remaining"]:
        return None
    return GAME["remaining"].pop(0)


# Start fresh on boot
new_game()

# -----------------------------
# Pages
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def home():
    """
    Matches your index.html:
      <form method="POST">
        <input name="name">
        <input name="count" type="number">
      </form>
    """
    if request.method == "GET":
        return render_template("index.html")

    # POST from index.html
    name = (request.form.get("name") or "Player").strip()

    try:
        count = int(request.form.get("count") or 1)
    except ValueError:
        count = 1

    # Match your form constraint 1–10
    count = max(1, min(count, 10))

    player_id = "p_" + uuid.uuid4().hex[:10]
    cards = [generate_card() for _ in range(count)]
    PLAYERS[player_id] = {"name": name, "cards": cards}
    touch()

    return redirect(url_for("player_cards", player_id=player_id))


@app.route("/caller")
def caller_page():
    return render_template("caller.html")


@app.route("/cards")
def cards_entry():
    # If someone visits /cards directly, send them to the join page
    return redirect(url_for("home"))


@app.route("/cards/<player_id>")
def player_cards(player_id):
    # If they refresh with an unknown id, give them 1 card
    if player_id not in PLAYERS:
        PLAYERS[player_id] = {"name": "Player", "cards": [generate_card()]}
        touch()

    player = PLAYERS[player_id]
    return render_template(
        "cards.html",
        player_id=player_id,
        player_name=player["name"],
        cards=player["cards"],
        total_cards=len(player["cards"]),
    )


# -----------------------------
# API: shared state
# -----------------------------
@app.route("/api/state")
def api_state():
    return jsonify({
        "called": GAME["called"],
        "last5": list(GAME["last5"]),
        "remaining_count": len(GAME["remaining"]),
        "bingo_calls": list(GAME["bingo_calls"]),
        "ready_count": len(GAME["ready"]),
        "reactions": dict(GAME["reactions"]),
        "auto_delay": GAME["auto_delay"],
        "auto_enabled": GAME["auto_enabled"],
        "updated_at": GAME["updated_at"],
    })


# -----------------------------
# API: caller actions
# -----------------------------
@app.route("/api/next", methods=["POST"])
def api_next():
    data = request.get_json(silent=True) or {}

    # If you ever want to enforce readiness, pass min_ready > 0 from caller page JS
    min_ready = int(data.get("min_ready", 0))
    if len(GAME["ready"]) < min_ready:
        return jsonify({"ok": False, "reason": "not_ready", "ready_count": len(GAME["ready"])}), 409

    ball = get_next_ball()
    if not ball:
        return jsonify({"ok": False, "reason": "no_balls_left"}), 409

    GAME["called"].append(ball)
    GAME["last5"].append(ball)

    # reset readiness after each call so players re-confirm
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
        "time": now_label()
    })
    touch()
    return jsonify({"ok": True})


@app.route("/api/reaction", methods=["POST"])
def api_reaction():
    data = request.get_json(silent=True) or {}
    emoji = str(data.get("emoji", "👀"))
    GAME["reactions"][emoji] += 1
    touch()
    return jsonify({"ok": True})


@app.route("/api/new_card", methods=["POST"])
def api_new_card():
    """
    Regenerate NEW cards for an existing player (same player link).
    If the player had 4 cards, they get 4 new ones.
    """
    data = request.get_json(silent=True) or {}
    player_id = str(data.get("player_id", ""))

    if not player_id or player_id not in PLAYERS:
        return jsonify({"ok": False, "reason": "unknown_player"}), 400

    count = len(PLAYERS[player_id]["cards"])
    PLAYERS[player_id]["cards"] = [generate_card() for _ in range(count)]
    touch()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True)
