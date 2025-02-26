from flask import Flask, render_template, request, jsonify, session
import random
import requests

app = Flask(__name__)
app.secret_key = "super_secret_key"  # Required for storing session data

# Sample relationship patterns (initial relationship logic)
RELATIONSHIP_PATTERNS = [
    "{} and {} are connected through technological innovation.",
    "The principles of {} have surprising parallels with {}.",
    "{} has influenced {} in unexpected ways over history.",
    "{} and {} share common principles in problem-solving.",
    "Scientists have studied how {} can improve our understanding of {}."
]

# Common critiques (to improve relationships)
CRITIQUE_PATTERNS = [
    "The connection between {} and {} seems weak; consider their historical interactions.",
    "A stronger relationship could be drawn by considering their impact on society.",
    "The explanation lacks depth in how {} directly influences {}.",
    "This relationship could be improved by referencing real-world examples.",
    "The connection is interesting but needs more specificity regarding shared principles."
]

# Refinement strategies (ways to improve a relationship)
REFINEMENT_PATTERNS = [
    "Expanding on this idea, researchers have found significant cross-disciplinary studies between {} and {}.",
    "A deeper examination shows that {} actually plays a critical role in shaping {} through shared methodologies.",
    "By analyzing historical contexts, we see that {} influenced {} in ways not initially apparent.",
    "Experts argue that {}'s principles can be directly applied to {} in multiple domains.",
    "Recent studies have explored how {} could revolutionize advancements in {}."
]

# Function to generate two random topics
def generate_topics():
    url = "https://en.wikipedia.org/api/rest_v1/page/random/title"

    try:
        topic1_response = requests.get(url).json()
        topic2_response = requests.get(url).json()

        # Extract the first item title correctly
        topic1 = topic1_response.get("items", [{}])[0].get("title", "Unknown Topic 1")
        topic2 = topic2_response.get("items", [{}])[0].get("title", "Unknown Topic 2")

        # Replace underscores with spaces for readability
        topic1 = topic1.replace("_", " ")
        topic2 = topic2.replace("_", " ")

    except Exception as e:
        print("Error fetching topics from Wikipedia:", e)
        topic1, topic2 = "Backup Topic 1", "Backup Topic 2"

    return topic1, topic2

# Function to generate a simple relationship (first pass)
def generate_relationship(topic1, topic2):
    return random.choice(RELATIONSHIP_PATTERNS).format(topic1, topic2)

# Function to critique the relationship (first AI's role)
def critique_relationship(statement, topic1, topic2):
    return random.choice(CRITIQUE_PATTERNS).format(topic1, topic2)

# Function to refine the relationship (second AI's role, fixing critique)
def refine_relationship(statement, critique, topic1, topic2):
    return f"{statement} {critique} {random.choice(REFINEMENT_PATTERNS).format(topic1, topic2)}"

@app.route("/")
def index():
    if "topics" not in session:
        session["topics"] = generate_topics()

    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    session["topics"] = generate_topics()
    topic1, topic2 = session["topics"]
    session["relationship"] = generate_relationship(topic1, topic2)

    return jsonify({
        "topic1": topic1,
        "topic2": topic2,
        "initial_idea": session["relationship"]
    })

@app.route("/refine", methods=["POST"])
def refine():
    if "relationship" not in session:
        return jsonify({"error": "No relationship found, generate topics first!"})

    topic1, topic2 = session["topics"]
    critique = critique_relationship(session["relationship"], topic1, topic2)
    session["relationship"] = refine_relationship(session["relationship"], critique, topic1, topic2)

    return jsonify({
        "refined_idea": session["relationship"]
    })

if __name__ == "__main__":
    app.run(debug=True)
