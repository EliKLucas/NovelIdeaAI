from flask import Flask, render_template, request, jsonify
import ollama
import random

app = Flask(__name__)

# Default debate topics
DEBATE_TOPICS = [
    "Should artificial intelligence be regulated?",
    "Is social media beneficial or harmful to society?",
]

DEBATE_POSITIONS = [
    ("I strongly support this stance", "I completely oppose this viewpoint"),
]

def ollama_generate_response(prompt, timeout=30):
    try:
        print(f"Attempting to generate response with prompt: {prompt[:100]}...")
        response = ollama.chat(
            model="llama2",
            messages=[{"role": "user", "content": prompt}],
            options={"timeout": timeout}
        )
        print("Successfully generated response")
        return response['message']['content']
    except Exception as e:
        print(f"Error in ollama_generate_response: {str(e)}")
        raise

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    try:
        print("Generate endpoint hit!")
        user_data = request.get_json()
        if not user_data:
            return jsonify({"error": "Invalid request, no JSON received."}), 400

        user_topic = user_data.get("user_topic", None)
        topic = user_topic if user_topic else random.choice(DEBATE_TOPICS)
        position_a, position_b = random.choice(DEBATE_POSITIONS)

        prompt = f"""
        You are a skilled debater. The debate topic is '{topic}'.
        You are arguing in favor of the position: '{position_a}'.
        Construct a strong argument supporting this position.
        """
        
        argument_a = ollama_generate_response(prompt)
        
        counter_prompt = f"""
        You are a skilled debater. The debate topic is '{topic}'.
        You are arguing against the position: '{position_b}'.
        The opponent said: {argument_a}
        Construct a strong counterargument.
        """
        
        argument_b = ollama_generate_response(counter_prompt)

        return jsonify({
            "topic": topic,
            "position_a": position_a,
            "position_b": position_b,
            "arguments": [(argument_a, argument_b)]
        })
    except Exception as e:
        print(f"Error in generate endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)  # Note: Using port 5001