from flask import Flask, render_template, request, redirect, url_for
import random

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
# SHORT LINK → PLAY
# -----------------------------
@app.route("/play")
def play():
    return redirect(url_for("index"))


# -----------------------------
# PRIVATE CALLER PAGE
# -----------------------------
@app.route("/caller")
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
