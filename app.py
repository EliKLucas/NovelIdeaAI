from flask import Flask, render_template, request, jsonify, session
import sqlite3
from functools import wraps
import os
import ollama
import time
import random
from flask import g
from sqlite3 import IntegrityError
from ollama import Client
from tenacity import retry, stop_after_attempt, wait_exponential

app = Flask(__name__)
app.secret_key = "super_secret_key"  # Required for session storage

# Add this after your imports
OLLAMA_HOST = "http://207.211.161.65:8080"
ollama_client = Client(
    host=OLLAMA_HOST,
    timeout=120
)

# Database setup
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('debate.db')
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Initialize database
def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

# Credit system functions (temporary bypass)
def check_credits(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

def deduct_credit():
    pass  # Temporarily disabled

def get_remaining_credits():
    return 50  # Temporary fixed value

# Default debate topics
DEBATE_TOPICS = [
    "Should artificial intelligence be regulated?",
    "Is social media beneficial or harmful to society?",
    "Should cryptocurrency replace traditional banking?",
    "Does technology improve human relationships?",
    "Should governments impose stricter climate change policies?",
]

# Opposing perspectives for debates
DEBATE_POSITIONS = [
    ("I strongly support this stance", "I completely oppose this viewpoint"),
    ("This approach is the future", "This approach is deeply flawed"),
    ("The economic benefits outweigh the risks", "The ethical concerns are too great"),
    ("We must embrace this technology", "We should be cautious about this technology"),
]

# Add at the top of your file
BOT_PERSONALITIES = [
    {
        "name": "The Logical Analyst",
        "style": "Using data-driven arguments and precise logical reasoning",
        "tone": "methodical and authoritative"
    },
    {
        "name": "The Passionate Advocate",
        "style": "Drawing on emotional appeals and real-world implications",
        "tone": "passionate and compelling"
    },
    {
        "name": "The Strategic Debater",
        "style": "Employing rhetorical techniques and strategic argumentation",
        "tone": "confident and persuasive"
    },
    {
        "name": "The Revolutionary Thinker",
        "style": "Challenging conventional wisdom with bold new perspectives",
        "tone": "bold and provocative"
    }
]

# Function to interact with Ollama (Llama 3)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def ollama_generate_response(prompt, max_length=150, timeout=120):
    try:
        print(f"Attempting to connect to Ollama at {OLLAMA_HOST}")
        print(f"Attempting to generate response with prompt: {prompt[:100]}...")
        
        response = ollama_client.chat(
            model="llama2",
            messages=[{
                "role": "user", 
                "content": f"{prompt}\nPlease keep your response under {max_length} words."
            }],
            options={
                "timeout": timeout,
                "num_predict": max_length * 6
            }
        )
        print("Successfully generated response")
        return response['message']['content']
    except Exception as e:
        print(f"Error in ollama_generate_response: {str(e)}")
        raise

# Mediator selects a debate topic and assigns positions
def mediator_choose_topic(user_topic=None):
    topic = user_topic if user_topic else random.choice(DEBATE_TOPICS)
    position_a, position_b = random.choice(DEBATE_POSITIONS)
    return topic, position_a, position_b

# Bot A: Generate an argument using Llama 3
def bot_a_argument(topic, position_a):
    personality = random.choice(BOT_PERSONALITIES)
    prompt = f"""
    You are {personality['name']}, a fierce debater {personality['style']}.
    Speaking with {personality['tone']}, deliver a powerful opening argument.
    
    Topic: '{topic}'
    Your position: '{position_a}'
    
    IMPORTANT DEBATE RULES:
    - Start with a bold, attention-grabbing statement
    - Use assertive language ("I assert", "It is clear", "The evidence proves")
    - Never apologize or hedge your position
    - Speak with absolute conviction
    - Challenge opposing viewpoints preemptively
    - End with a strong concluding statement
    
    Make your argument compelling and authoritative.
    """
    return ollama_generate_response(prompt), personality

# Bot B: Generate a counterargument using Llama 3
def bot_b_counterargument(topic, position_b, argument_a):
    personality = random.choice(BOT_PERSONALITIES)
    prompt = f"""
    You are {personality['name']}, a masterful debater {personality['style']}.
    Speaking with {personality['tone']}, demolish your opponent's argument.
    
    Topic: '{topic}'
    Your position: '{position_b}'
    Opponent's argument: '{argument_a}'
    
    IMPORTANT DEBATE RULES:
    - Begin with a powerful rebuttal
    - Directly attack the weakest points in their argument
    - Use decisive language ("This is fundamentally flawed", "The facts clearly show")
    - Never concede points or apologize
    - Speak with unwavering confidence
    - End by reinforcing your superior position
    
    Deliver a devastating counterargument that leaves no room for doubt.
    """
    return ollama_generate_response(prompt), personality

# Mediator: Generate a compromise based on both arguments
def mediator_summarize_compromise(topic, argument_a, argument_b):
    prompt = f"""
    The debate topic is '{topic}'.
    Bot A argued: '{argument_a}'
    Bot B counter-argued: '{argument_b}'

    - Your task is to generate a **compromise** between these two perspectives.
    - The compromise should acknowledge the strengths of both arguments while suggesting a balanced resolution.
    """
    
    compromise = ollama_generate_response(prompt)
    return compromise

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
@check_credits
def generate():
    try:
        print("Generate endpoint hit!")
        print(f"Using Ollama host: {OLLAMA_HOST}")
        user_data = request.get_json()
        if not user_data:
            return jsonify({"error": "Invalid request, no JSON received."}), 400

        user_topic = user_data.get("user_topic", None)
        print(f"User topic: {user_topic}")
        topic, position_a, position_b = mediator_choose_topic(user_topic)
        print(f"Selected topic: {topic}")

        # Generate only Bot A's response first
        print("Attempting to generate Bot A's response...")
        argument_a, personality_a = bot_a_argument(topic, position_a)
        print("Successfully generated Bot A's response")

        return jsonify({
            "topic": topic,
            "position_a": position_a,
            "position_b": position_b,
            "argument_a": argument_a,
            "personality_a": personality_a
        })
    except Exception as e:
        print(f"Error in generate endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/counter_argument", methods=["POST"])
def counter_argument():
    try:
        data = request.get_json()
        topic = data.get("topic")
        position_b = data.get("position_b")
        argument_a = data.get("argument_a")

        # Generate Bot B's response
        argument_b, personality_b = bot_b_counterargument(topic, position_b, argument_a)

        return jsonify({
            "argument_b": argument_b,
            "personality_b": personality_b
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/refine", methods=["POST"])
def refine():
    if "topic" not in session:
        return jsonify({"error": "No debate found, generate one first!"})

    topic = session["topic"]
    position_a = session["position_a"]
    position_b = session["position_b"]

    previous_argument_a, previous_argument_b = session["arguments"][-1]

    # Generate new arguments based on previous round
    argument_a, personality_a = bot_a_argument(topic, position_a, previous_argument_b)
    argument_b, personality_b = bot_b_counterargument(topic, position_b, argument_a)

    session["arguments"].append((argument_a, argument_b))
    session["iterations"] += 1

    return jsonify({
        "arguments": session["arguments"]
    })

@app.route("/compromise", methods=["POST"])
def compromise():
    if "topic" not in session:
        return jsonify({"error": "No debate found, generate one first!"}), 400
    
    try:
        topic = session["topic"]
        # Get the last set of arguments from the debate
        argument_a, argument_b = session["arguments"][-1]
        
        print("Generating compromise...") # Debug log
        compromise_statement = mediator_summarize_compromise(topic, argument_a, argument_b)
        print("Compromise generated successfully") # Debug log
        
        return jsonify({
            "compromise": compromise_statement
        })
    except Exception as e:
        print(f"Error generating compromise: {str(e)}") # Debug log
        return jsonify({"error": f"Failed to generate compromise: {str(e)}"}), 500

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
        
    db = get_db()
    try:
        db.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            [username, generate_password_hash(password)]
        )
        db.commit()
        return jsonify({"message": "Registration successful"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 409

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE username = ?', [username]
    ).fetchone()
    
    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        return jsonify({
            "message": "Login successful",
            "credits": user['credits']
        })
    return jsonify({"error": "Invalid credentials"}), 401

if __name__ == "__main__":
    app.run(debug=True)
