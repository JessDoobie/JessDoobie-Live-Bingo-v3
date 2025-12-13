from flask import Flask, render_template, request
import random

app = Flask(__name__)

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


if __name__ == "__main__":
    app.run()

