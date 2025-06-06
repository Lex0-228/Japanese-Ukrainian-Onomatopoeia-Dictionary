from flask import Flask, request, jsonify, render_template
from find_ukr import find_ukrainian_words
from find_similar import find_ukr_matches_for_jp_input

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search")
def search():
    query = request.args.get("query", "").strip()
    lang = request.args.get("lang", "jp").strip()
    category = request.args.get("category", "").strip()

    if not query and not category:
        return jsonify({"results": [], "message": "Порожній запит: введіть слово або оберіть категорію"})

    if lang == "ukr":
        result = find_ukrainian_words(query_text=query, category=category)
    else:
        result = find_ukr_matches_for_jp_input(query_text=query, category=category)

    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)
