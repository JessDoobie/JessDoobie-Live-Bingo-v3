
from flask import Flask, render_template, request
import random

app = Flask(__name__)

def generate_card():
    card = {}
    ranges = {
        "B": range(1,16),
        "I": range(16,31),
        "N": range(31,46),
        "G": range(46,61),
        "O": range(61,76)
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
        cards = [generate_card() for _ in range(count)]
        return render_template("cards.html", name=name, cards=cards, count=count)
    return render_template("index.html")

if __name__ == "__main__":
    app.run()
