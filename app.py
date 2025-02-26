from flask import Flask, render_template, request, jsonify, session
import random
import requests

app = Flask(__name__)
app.secret_key = "super_secret_key"  # Required for storing session data

# Wikipedia API Helper Functions
def get_wikipedia_summary(topic):
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ', '_')}"

    try:
        response = requests.get(url).json()
        summary = response.get("extract")

        if summary:
            return summary.strip()
        else:
            return f"No Wikipedia summary available for {topic}."

    except Exception as e:
        print(f"Error fetching summary for {topic}: {e}")
        return f"Could not retrieve Wikipedia summary for {topic}."

def generate_topics():
    url = "https://en.wikipedia.org/api/rest_v1/page/random/title"
    
    for _ in range(3):  # Try fetching valid topics up to 3 times
        try:
            response1 = requests.get(url).json()
            response2 = requests.get(url).json()
            
            topic1 = response1.get("title", "").strip()
            topic2 = response2.get("title", "").strip()

            if topic1 and topic2 and topic1 != topic2:
                return topic1, topic2  # Ensure topics are valid and not identical

        except Exception as e:
            print("Error fetching topics:", e)

    # If Wikipedia API fails 3 times, use fallback topics
    fallback_topics = [
        ("Artificial Intelligence", "Human Evolution"),
        ("Quantum Mechanics", "Cryptocurrency"),
        ("Ancient Philosophy", "Space Exploration"),
        ("Neuroscience", "Virtual Reality"),
        ("Genetic Engineering", "Cybersecurity")
    ]
    
    return random.choice(fallback_topics)


# AI Bot A - Proposes Relationship
def bot_a_propose_relationship(topic1, topic2):
    summary1 = get_wikipedia_summary(topic1)
    summary2 = get_wikipedia_summary(topic2)
    return f"{topic1} ({summary1}) is connected to {topic2} ({summary2}) through shared themes in science, culture, or methodology."

# AI Bot B - Critiques and Asks a Question
def bot_b_critique_and_question(statement, topic1, topic2):
    questions = [
        f"How does {topic1} conceptually influence {topic2}?",
        f"What real-world applications exist that link {topic1} and {topic2}?",
        f"Are there any historical cases where {topic1} directly impacted {topic2}?",
        f"How would a researcher prove that {topic1} and {topic2} are related?",
        f"What underlying principles or theories make the relationship between {topic1} and {topic2} stronger?"
    ]
    return f"{statement} However, {random.choice(questions)}"

# AI Bot A - Answers Its Own Question
def bot_a_answer_question(statement, topic1, topic2):
    answers = [
        f"One example is how {topic1} has been studied in {topic2}-related fields.",
        f"Researchers have found that {topic1} and {topic2} share common foundational concepts.",
        f"Studies suggest that {topic1} might actually improve the way we approach {topic2}.",
        f"There is evidence that {topic1} has contributed to advancements in {topic2}.",
        f"In interdisciplinary studies, {topic1} has been used as a model for understanding {topic2}."
    ]
    return f"{statement} {random.choice(answers)}"

# AI Bot B - Further Critiques and Expands
def bot_b_critique_and_expand(statement, topic1, topic2):
    critiques = [
        f"This argument could be stronger by citing specific cases where {topic1} was applied to {topic2}.",
        f"More details about how {topic1} is scientifically studied in relation to {topic2} would help.",
        f"While {topic1} and {topic2} share some conceptual links, proving causation remains a challenge.",
        f"A deeper exploration of how these fields have intersected in history would improve this connection.",
        f"This relationship needs concrete examples to be truly convincing."
    ]
    return f"{statement} {random.choice(critiques)}"

@app.route("/")
def index():
    if "topics" not in session:
        session["topics"] = generate_topics()
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    session["topics"] = generate_topics()
    topic1, topic2 = session["topics"]
    
    # Start iterative refinement loop
    initial_relationship = bot_a_propose_relationship(topic1, topic2)
    critique1 = bot_b_critique_and_question(initial_relationship, topic1, topic2)
    refined1 = bot_a_answer_question(critique1, topic1, topic2)
    critique2 = bot_b_critique_and_expand(refined1, topic1, topic2)
    
    # Store latest refinement
    session["relationship"] = critique2

    return jsonify({
        "topic1": topic1,
        "topic2": topic2,
        "initial_idea": initial_relationship
    })

@app.route("/refine", methods=["POST"])
def refine():
    if "relationship" not in session:
        return jsonify({"error": "No relationship found, generate topics first!"})

    topic1, topic2 = session["topics"]

    # Continue iterative refinement loop
    critique = bot_b_critique_and_question(session["relationship"], topic1, topic2)
    refined = bot_a_answer_question(critique, topic1, topic2)
    expanded = bot_b_critique_and_expand(refined, topic1, topic2)

    # Store latest refinement
    session["relationship"] = expanded

    return jsonify({
        "refined_idea": session["relationship"]
    })

if __name__ == "__main__":
    app.run(debug=True)
