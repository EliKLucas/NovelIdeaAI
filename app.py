from flask import Flask, render_template, request, jsonify, session
import random
import time
import wikipediaapi

app = Flask(__name__)
app.secret_key = "super_secret_key"

wiki_wiki = wikipediaapi.Wikipedia(
    user_agent="MyDebateApp/1.0 (https://github.com/your-repo; contact: your-email@example.com)", 
    language="en"
)

# Default debate topics
DEBATE_TOPICS = [
    "Should artificial intelligence be regulated?",
    "Is social media beneficial or harmful to society?",
    "Should cryptocurrency replace traditional banking?",
    "Does technology improve human relationships?",
    "Should governments impose stricter climate change policies?",
]

# Opposing perspectives
DEBATE_POSITIONS = [
    ("I strongly support this stance", "I completely oppose this viewpoint"),
    ("This approach is the future", "This approach is deeply flawed"),
    ("The economic benefits outweigh the risks", "The ethical concerns are too great"),
    ("We must embrace this technology", "We should be cautious about this technology"),
]

# Wikipedia summary function
def get_wikipedia_summary(topic):
    page = wiki_wiki.page(topic)
    return page.summary[:500] if page.exists() else None

# Mediator selects topic and positions
def mediator_choose_topic(user_topic=None):
    topic = user_topic if user_topic else random.choice(DEBATE_TOPICS)
    position_a, position_b = random.choice(DEBATE_POSITIONS)
    return topic, position_a, position_b

# Personality styles for the bots
BOT_PERSONALITIES = {
    "logical": {
        "intro": ["From a purely logical perspective,", "If we analyze the facts,", "Based on reason and evidence,"],
        "emphasis": ["It’s undeniable that", "We must acknowledge that", "It’s clear that"],
        "response": ["Therefore,", "Logically speaking,", "Thus, the rational conclusion is that"]
    },
    "emotional": {
        "intro": ["I feel strongly that", "It’s obvious to anyone that", "We can’t ignore that"],
        "emphasis": ["Frankly,", "Truthfully,", "In all honesty,"],
        "response": ["And that’s why", "It’s upsetting that", "It’s shocking that"]
    },
    "sarcastic": {
        "intro": ["Oh, of course,", "Sure, let’s just ignore reality,", "As if"],
        "emphasis": ["Clearly,", "Obviously,", "Yeah, right,"],
        "response": ["And I’m sure that’ll work out great,", "Because history has never shown otherwise,", "That’s totally believable,"]
    }
}

# Function to get a random tone
def get_personality_tone(personality):
    return random.choice(BOT_PERSONALITIES[personality]["intro"]), random.choice(BOT_PERSONALITIES[personality]["emphasis"]), random.choice(BOT_PERSONALITIES[personality]["response"])

# Synonyms for avoiding topic repetition
TOPIC_SYNONYMS = ["this issue", "this policy", "this technology", "this concept", "this strategy"]

# Dynamic argument generator
def format_natural_argument(topic, personality):
    intro, emphasis, response = get_personality_tone(personality)
    
    topic_synonym = random.choice(TOPIC_SYNONYMS)
    
    argument_templates = [
        f"{intro} {topic_synonym} is a game-changer because it impacts everything from education to healthcare.",
        f"{emphasis} without {topic_synonym}, we risk falling behind in critical areas like technology and innovation.",
        f"{response} the evidence overwhelmingly supports the benefits of adopting {topic_synonym}."
    ]

    return " ".join(random.sample(argument_templates, len(argument_templates)))  # Rearranges sentence order dynamically

# Bot A: Argument with conversational personality
def bot_a_argument(topic, position, previous_statement=None):
    research = get_wikipedia_summary(topic)
    personality = random.choice(["logical", "emotional"])  # Bot A is either logical or emotional
    argument = format_natural_argument(topic, personality)

    response = f"I strongly believe that {argument}"

    if previous_statement:
        response = f"I hear what you’re saying about '{previous_statement}', but I have to counter that: {argument}"
    
    if research:
        response += f" Also, according to Wikipedia, '{research}'"

    return response

# Bot B: Counterargument with sarcastic or logical personality
def bot_b_counterargument(topic, position, previous_statement):
    research = get_wikipedia_summary(topic)
    personality = random.choice(["sarcastic", "logical"])  # Bot B can be sarcastic or logical
    counter_argument = format_natural_argument(topic, personality)

    response = f"I appreciate your enthusiasm, but let's be real. {counter_argument}"

    if previous_statement:
        response = f"You said '{previous_statement}', but let’s be honest: {counter_argument}"

    if research:
        response += f" In fact, Wikipedia states: '{research}'"

    return response

# Mediator compromise function
def mediator_summarize_compromise(topic, argument_a, argument_b):
    compromise_templates = [
        f"A balanced approach to {topic} may involve partial regulation while allowing flexibility for innovation.",
        f"While strong arguments exist on both sides, a middle-ground solution could be to implement trial policies before full-scale adoption of {topic}.",
        f"Instead of a binary decision, {topic} could be adapted with safeguards to address concerns raised by both proponents and critics.",
        f"The best path forward for {topic} might involve collaborative efforts between industry experts and policymakers to create a sustainable framework."
    ]
    
    return f"Considering both perspectives on {topic}, a fair resolution could be: " + random.choice(compromise_templates)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    user_data = request.get_json()
    if not user_data:
        return jsonify({"error": "Invalid request, no JSON received."}), 400

    user_topic = user_data.get("user_topic", None)
    topic, position_a, position_b = mediator_choose_topic(user_topic)

    argument_a = bot_a_argument(topic, position_a)
    time.sleep(1)
    argument_b = bot_b_counterargument(topic, position_b, argument_a)

    session["topic"] = topic
    session["position_a"] = position_a
    session["position_b"] = position_b
    session["arguments"] = [(argument_a, argument_b)]
    session["iterations"] = 1

    return jsonify({
        "topic": topic,
        "position_a": position_a,
        "position_b": position_b,
        "arguments": session["arguments"]
    })

@app.route("/refine", methods=["POST"])
def refine():
    if "topic" not in session:
        return jsonify({"error": "No debate found, generate one first!"})

    topic = session["topic"]
    position_a = session["position_a"]
    position_b = session["position_b"]
    
    previous_argument_a, previous_argument_b = session["arguments"][-1]

    summary_a = previous_argument_b.split(".")[0] if "." in previous_argument_b else previous_argument_b
    summary_b = previous_argument_a.split(".")[0] if "." in previous_argument_a else previous_argument_a

    argument_a = bot_a_argument(topic, position_a, summary_a)
    argument_b = bot_b_counterargument(topic, position_b, summary_b)

    session["arguments"].append((argument_a, argument_b))
    session["iterations"] += 1

    return jsonify({
        "arguments": session["arguments"]
    })

@app.route("/compromise", methods=["POST"])
def compromise():
    if "iterations" not in session or session["iterations"] < 3:
        return jsonify({"error": "More debate is needed before reaching a compromise."})

    topic = session["topic"]
    argument_a, argument_b = session["arguments"][-1]

    compromise_statement = mediator_summarize_compromise(topic, argument_a, argument_b)

    return jsonify({
        "compromise": compromise_statement
    })

if __name__ == "__main__":
    app.run(debug=True)
