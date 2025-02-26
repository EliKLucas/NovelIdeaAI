from flask import Flask, render_template, request, jsonify, session
import ollama
import time
import random

app = Flask(__name__)
app.secret_key = "super_secret_key"  # Required for session storage

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

# Function to interact with Ollama (Llama 3)
def ollama_generate_response(prompt, timeout=30):
    try:
        print(f"Attempting to generate response with prompt: {prompt[:100]}...") # Debug log
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
            options={"timeout": timeout}
        )
        print("Successfully generated response") # Debug log
        return response['message']['content']
    except Exception as e:
        print(f"Error in ollama_generate_response: {str(e)}") # Debug log
        raise

# Mediator selects a debate topic and assigns positions
def mediator_choose_topic(user_topic=None):
    topic = user_topic if user_topic else random.choice(DEBATE_TOPICS)
    position_a, position_b = random.choice(DEBATE_POSITIONS)
    return topic, position_a, position_b

# Bot A: Generate an argument using Llama 3
def bot_a_argument(topic, position, previous_statement=None):
    prompt = f"""
    You are a skilled debater. The debate topic is '{topic}'.
    You are arguing **in favor** of the position: '{position}'.
    
    - Construct a strong argument supporting this position.
    - If the opponent previously said something, respond critically to their claim.
    """
    
    if previous_statement:
        prompt += f"\nOpponent's previous statement: '{previous_statement}'\nAddress their argument directly."

    argument = ollama_generate_response(prompt)
    return argument

# Bot B: Generate a counterargument using Llama 3
def bot_b_counterargument(topic, position, previous_statement):
    prompt = f"""
    You are a skilled debater. The debate topic is '{topic}'.
    You are arguing **against** the position: '{position}'.
    
    - Construct a strong counterargument against this position.
    - If the opponent previously said something, respond critically to their claim.
    """
    
    if previous_statement:
        prompt += f"\nOpponent's previous statement: '{previous_statement}'\nAddress their argument directly."

    counter_argument = ollama_generate_response(prompt)
    return counter_argument

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
def generate():
    if session.get('generating'):
        return jsonify({"error": "A debate is already being generated"}), 429
    
    try:
        session['generating'] = True
        print("Generate endpoint hit!") # Debug log
        user_data = request.get_json()
        if not user_data:
            print("No JSON data received") # Debug log
            return jsonify({"error": "Invalid request, no JSON received."}), 400

        print(f"Received user data: {user_data}") # Debug log
        user_topic = user_data.get("user_topic", None)
        
        print("Choosing topic...") # Debug log
        topic, position_a, position_b = mediator_choose_topic(user_topic)
        print(f"Selected topic: {topic}") # Debug log

        print("Generating Bot A argument...") # Debug log
        try:
            argument_a = bot_a_argument(topic, position_a)
            print("Bot A argument generated successfully") # Debug log
        except Exception as e:
            print(f"Error generating Bot A argument: {str(e)}") # Debug log
            return jsonify({"error": "Failed to generate Bot A's argument"}), 500

        print("Generating Bot B argument...") # Debug log
        try:
            argument_b = bot_b_counterargument(topic, position_b, argument_a)
            print("Bot B argument generated successfully") # Debug log
        except Exception as e:
            print(f"Error generating Bot B argument: {str(e)}") # Debug log
            return jsonify({"error": "Failed to generate Bot B's argument"}), 500

        # Store in session
        session["topic"] = topic
        session["position_a"] = position_a
        session["position_b"] = position_b
        session["arguments"] = [(argument_a, argument_b)]
        session["iterations"] = 1

        print("Successfully completed generate request") # Debug log
        return jsonify({
            "topic": topic,
            "position_a": position_a,
            "position_b": position_b,
            "arguments": session["arguments"]
        })
    except Exception as e:
        print(f"Error in generate endpoint: {str(e)}") # Debug log
        return jsonify({"error": str(e)}), 500
    finally:
        session['generating'] = False

@app.route("/refine", methods=["POST"])
def refine():
    if "topic" not in session:
        return jsonify({"error": "No debate found, generate one first!"})

    topic = session["topic"]
    position_a = session["position_a"]
    position_b = session["position_b"]

    previous_argument_a, previous_argument_b = session["arguments"][-1]

    # Generate new arguments based on previous round
    argument_a = bot_a_argument(topic, position_a, previous_argument_b)
    argument_b = bot_b_counterargument(topic, position_b, argument_a)

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

if __name__ == "__main__":
    app.run(debug=True)
