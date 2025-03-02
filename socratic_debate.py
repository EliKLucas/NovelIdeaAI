import aiohttp
import asyncio
from bs4 import BeautifulSoup
import ollama
import json
from datetime import datetime
import random
from typing import List, Dict, Tuple
import logging
import textwrap
from difflib import SequenceMatcher
from collections import Counter
import numpy as np
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("""
    Error: Required packages not installed.
    Please run the following commands on your Oracle Cloud server:
    
    pip install sentence-transformers numpy
    
    Note: This will download the all-MiniLM-L6-v2 model (about 90MB) 
    to ~/.cache/torch/sentence_transformers/
    """)
    raise

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class WikiTopicGenerator:
    def __init__(self):
        self.random_url = "https://en.wikipedia.org/wiki/Special:Random"
    
    async def get_random_topics(self, num_topics: int = 2) -> List[str]:
        topics = []
        async with aiohttp.ClientSession() as session:
            for _ in range(num_topics):
                try:
                    async with session.get(self.random_url, allow_redirects=True) as response:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        topic = soup.find(id='firstHeading').text
                        topics.append(topic)
                except Exception as e:
                    logging.error(f"Error fetching Wikipedia topic: {e}")
                    topics.append("Backup Topic")
        return topics

class NoveltyDetector:
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model
        self.novelty_log = []
    
    def keyword_diversity(self, new_text: str, previous_text: str) -> float:
        """Measures how different the word usage is between two texts."""
        new_words = set(new_text.lower().split())
        prev_words = set(previous_text.lower().split())
        
        overlap = len(new_words & prev_words) / max(len(new_words | prev_words), 1)
        return 1 - overlap  # Higher value = more diverse

    def topic_shift_penalty(self, new_text: str, previous_text: str) -> float:
        """Encourages topic evolution by penalizing minimal change in word focus."""
        new_word_counts = Counter(new_text.lower().split())
        prev_word_counts = Counter(previous_text.lower().split())
        
        shared_words = sum(min(new_word_counts[w], prev_word_counts[w]) for w in new_word_counts)
        total_words = sum(new_word_counts.values())
        
        return 1 - (shared_words / total_words)  # Higher value = stronger topic shift

    def get_embedding(self, text: str) -> np.ndarray:
        return self.embedding_model.encode(text)

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def novelty_score(self, new_text: str, previous_text: str) -> float:
        """Combines semantic novelty, keyword diversity, and topic shift score."""
        if not new_text or not previous_text:
            return 1.0  # Assume novel if no prior comparison exists

        sem_novelty = 1 - self.cosine_similarity(self.get_embedding(new_text), self.get_embedding(previous_text))
        key_div = self.keyword_diversity(new_text, previous_text)
        topic_shift = self.topic_shift_penalty(new_text, previous_text)

        score = (sem_novelty * 0.5) + (key_div * 0.25) + (topic_shift * 0.25)  # Weighted combination
        
        self.novelty_log.append(score)
        self._check_novelty_trend()
        
        return score

    def _check_novelty_trend(self):
        """Monitors novelty trends and suggests interventions."""
        if len(self.novelty_log) > 5:  # Check last 5 iterations
            avg_novelty = sum(self.novelty_log[-5:]) / 5
            if avg_novelty < 0.15:
                logging.warning("⚠️ Persistent novelty decline detected!")
                return self._get_intervention()
        return None

    def _get_intervention(self) -> str:
        """Returns a random intervention strategy when novelty is too low."""
        interventions = [
            "Provide a counterexample to challenge your previous argument.",
            "Introduce an entirely new cultural analogy unrelated to previous themes.",
            "Reformat your response into a structured debate: Claim → Counterpoint → Conclusion.",
            "Consider an opposing viewpoint that directly challenges the main premise.",
            "Analyze the topic through a completely different theoretical framework."
        ]
        return random.choice(interventions)

class SocraticBot:
    def __init__(self, host: str = "http://207.211.161.65:8080"):
        self.client = ollama.Client(host=host)
        self.perspectives = ["Functional", "Structural", "Psychological", "Historical", "Symbolic"]
        # Load MiniLM model for embeddings
        self.embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.novelty_detector = NoveltyDetector(self.embedding_model)
        
    def get_embedding(self, text: str) -> np.ndarray:
        """Generate an embedding vector for a given text."""
        if not text:
            return np.zeros(384)  # Model outputs 384-dimensional vectors
        return self.embedding_model.encode(text)

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute the cosine similarity between two vectors."""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def novelty_score(self, new_text: str, previous_text: str) -> float:
        """Calculate novelty score based on semantic similarity."""
        new_vec = self.get_embedding(new_text)
        prev_vec = self.get_embedding(previous_text)
        similarity = self.cosine_similarity(new_vec, prev_vec)
        novelty = 1 - similarity  # Higher = more novel
        return novelty

    def force_new_perspective(self) -> str:
        """Selects a new perspective for the discussion if redundancy is detected."""
        return random.choice(self.perspectives)
    
    def similarity_check(self, new_text: str, old_text: str) -> float:
        """Compares similarity between two iterations."""
        if not new_text or not old_text:
            return 0
        return SequenceMatcher(None, new_text, old_text).ratio() * 100

    async def generate_response(self, prompt: str, role: str, previous_response: str = None) -> str:
        """Generate bot response and check novelty."""
        try:
            # Generate a response
            response = self.client.chat(
                model="llama2",
                messages=[{
                    "role": "system",
                    "content": f"You are {role}. {self.get_role_instructions(role)}"
                }, {
                    "role": "user",
                    "content": prompt
                }]
            )
            response_text = response.message.content

            # If there's a previous response, calculate novelty
            if previous_response:
                novelty = self.novelty_detector.novelty_score(response_text, previous_response)
                logging.info(f"Novelty Score: {novelty:.2f}")

                # If novelty is too low, force a perspective shift
                if novelty < 0.3:
                    intervention = self.novelty_detector._get_intervention()
                    new_perspective = self.force_new_perspective()
                    prompt = f"Using a {new_perspective} perspective and following this instruction: {intervention}\n{prompt}"
                    logging.info(f"Forcing new perspective: {new_perspective}")
                    logging.info(f"Intervention: {intervention}")

                    response = self.client.chat(
                        model="llama2",
                        messages=[{
                            "role": "system",
                            "content": f"You are {role}. {self.get_role_instructions(role)}"
                        }, {
                            "role": "user",
                            "content": prompt
                        }]
                    )
                    response_text = response.message.content
                    logging.info(f"Generated new response after perspective shift.")

            return response_text
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return f"Error: {str(e)}"

    def get_role_instructions(self, role: str) -> str:
        instructions = {
            "connector": """
            You are Bot A, the Connector. Your role is to:
            1. Find meaningful connections between seemingly unrelated topics
            2. Generate clear, logical statements explaining these connections
            3. Use analogies and examples to strengthen your arguments
            Be creative but maintain logical consistency.
            """,
            "evaluator": """
            You are Bot B, the Evaluator. Your role is to:
            1. Analyze the logical strength of connections
            2. Identify specific weaknesses or gaps in reasoning
            3. Suggest concrete improvements
            Be constructive but thorough in your critique.
            """,
            "decider": """
            You are Bot C, the Decider. Your role is to:
            1. Compare initial and refined arguments
            2. Choose the stronger reasoning
            3. Suggest modifications to topics for better discussion
            Be impartial and focus on logical strength.
            """
        }
        return instructions.get(role, "No specific instructions available.")

class DiscussionManager:
    def __init__(self):
        self.topic_generator = WikiTopicGenerator()
        self.bot = SocraticBot()
        self.log_file = "discussion_logs.json"
        self.session_log = {
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "topics": [],
            "iterations": []
        }
        self.wrapper = textwrap.TextWrapper(
            width=80,
            initial_indent="    ",
            subsequent_indent="    ",
            break_long_words=False,
            break_on_hyphens=False
        )

    def format_response(self, text: str) -> str:
        """Format response text to fit nicely on screen."""
        if text is None:
            return "No argument yet"
        return "\n".join(self.wrapper.fill(line) for line in text.split("\n"))

    async def get_topics_from_input(self) -> List[str]:
        """Handles various forms of user input to determine discussion topics."""
        print("\nEnter two concepts to compare (press Enter for random topics)")
        print("Examples: ")
        print("- 'Compare cats and democracy'")
        print("- 'quantum physics, jazz music'")
        print("- 'relate A: coffee B: sunrise'")
        print("- Just press Enter for random topics")
        
        user_input = input("\nYour input: ").strip()
        
        # Handle empty input - fetch both topics from Wikipedia
        if not user_input or user_input.lower() in ['random', 'you decide', 'you choose']:
            print("\nFetching random topics from Wikipedia...")
            return await self.topic_generator.get_random_topics()
        
        # Try to extract two topics from various input formats
        topics = []
        
        # Common separators and patterns
        separators = ['and', ',', 'vs', 'versus', 'to', 'with', ';']
        prefixes = ['compare', 'relate', 'connect', 'between']
        
        # Remove common prefixes
        for prefix in prefixes:
            if user_input.lower().startswith(prefix):
                user_input = user_input[len(prefix):].strip()
                break
        
        # Look for "A:" and "B:" pattern
        if 'a:' in user_input.lower() and 'b:' in user_input.lower():
            parts = user_input.lower().split('b:')
            first = parts[0].split('a:')[1].strip()
            second = parts[1].strip()
            topics = [first, second]
        else:
            # Try common separators
            for separator in separators:
                if separator in user_input.lower():
                    topics = [t.strip() for t in user_input.split(separator, 1)]
                    break
            
            # If no separator found, treat the whole input as one topic
            if not topics:
                topics = [user_input.strip()]
        
        # If only one topic provided, ask for second
        if len(topics) == 1:
            print(f"\nGot first topic: {topics[0]}")
            second_topic = input("Enter second topic (or press Enter to let me choose): ").strip()
            
            if not second_topic:
                print("\nFinding a related topic...")
                # Use Bot C to suggest a related topic
                prompt = f"Given the concept '{topics[0]}', suggest a contrasting or complementary concept that would make for an interesting comparison. Respond with ONLY the concept, no explanation."
                second_topic = await self.bot.generate_response(prompt, "decider")
                print(f"I chose: {second_topic}")
            
            topics.append(second_topic)
        
        return topics

    async def run_discussion(self, max_iterations: int = 3):
        self.session_log["topics"] = await self.get_topics_from_input()
        print("\n" + "="*80)
        print(f"Starting discussion with topics: {self.session_log['topics'][0]} and {self.session_log['topics'][1]}")
        print("="*80 + "\n")

        # Keep track of the best argument and its embedding
        current_best_argument = None
        current_best_embedding = None

        for i in range(max_iterations):
            print(f"\nIteration {i + 1}:")
            print("-"*40)
            iteration_log = {"iteration": i + 1}
            
            # Bot A: Generate or refine connection
            print("\nBot A (Connector) is thinking...")
            if current_best_argument is None:
                prompt = f"Find a meaningful connection between these topics: {self.session_log['topics'][0]} and {self.session_log['topics'][1]}"
            else:
                prompt = f"Building upon this previous argument: '{current_best_argument}'\nRefine and improve this connection between {self.session_log['topics'][0]} and {self.session_log['topics'][1]}. Focus on making the connection more specific and stronger."
            
            connection = await self.bot.generate_response(prompt, "connector", current_best_argument)
            connection_embedding = self.bot.novelty_detector.get_embedding(connection)
            print(f"\nBot A: {self.format_response(connection)}\n")
            iteration_log["bot_a_connection"] = connection
            
            # Novelty Check: Compare against previous best
            if current_best_embedding is not None:
                novelty_score = 1 - self.bot.novelty_detector.cosine_similarity(connection_embedding, current_best_embedding)
                logging.info(f"Novelty Score for Iteration {i + 1}: {novelty_score:.2f}")
                iteration_log["novelty_score"] = novelty_score

                if novelty_score < 0.3:
                    print("\n🚨 Low novelty detected! Forcing a perspective shift...")
                    intervention = self.bot.novelty_detector._get_intervention()
                    new_perspective = self.bot.force_new_perspective()
                    prompt = f"Using a {new_perspective} perspective and following this instruction: {intervention}\n{prompt}"
                    print(f"\nIntervention: {intervention}")
                    connection = await self.bot.generate_response(prompt, "connector")
                    print(f"\nBot A (New Perspective): {self.format_response(connection)}\n")
                    connection_embedding = self.bot.novelty_detector.get_embedding(connection)
                    iteration_log["perspective_shift"] = new_perspective
                    iteration_log["intervention"] = intervention
            
            # Bot B: Evaluate
            print("\nBot B (Evaluator) is analyzing...")
            critique = await self.bot.generate_response(
                f"Evaluate this connection, comparing it to the previous best argument if it exists:\nPrevious best: {current_best_argument if current_best_argument else 'None'}\nNew argument: {connection}",
                "evaluator"
            )
            print(f"\nBot B: {self.format_response(critique)}\n")
            iteration_log["bot_b_critique"] = critique
            
            # Bot A: Refine based on critique
            print("\nBot A is refining the argument...")
            refined = await self.bot.generate_response(
                f"Using the previous best argument as a foundation: '{current_best_argument if current_best_argument else 'None'}'\n" +
                f"And considering this critique: {critique}\n" +
                "Refine your connection. Focus on building upon strengths while addressing the specific weaknesses identified.",
                "connector"
            )
            print(f"\nBot A (Refined): {self.format_response(refined)}\n")
            iteration_log["bot_a_refined"] = refined
            
            # Bot C: Decide and update best argument
            print("\nBot C (Decider) is evaluating...")
            decision_prompt = f"""Compare these arguments and decide which is strongest:
1. Previous best argument: {current_best_argument if current_best_argument else 'None'}
2. New connection: {connection}
3. Refined version: {refined}

Choose the strongest version and explain why. If the improvement is negligible, state this explicitly."""

            decision = await self.bot.generate_response(decision_prompt, "decider")
            print(f"\nBot C: {self.format_response(decision)}\n")
            iteration_log["bot_c_decision"] = decision
            
            # Update the current best argument based on Bot C's decision
            if "refined version" in decision.lower() or "refined argument" in decision.lower():
                current_best_argument = refined
                current_best_embedding = self.bot.novelty_detector.get_embedding(refined)
            elif "new connection" in decision.lower():
                current_best_argument = connection
                current_best_embedding = connection_embedding
            
            self.session_log["iterations"].append(iteration_log)
            self.save_log()
            
            print("\n" + "="*80)
            print(f"Completed iteration {i + 1}")
            print(f"Current best argument: {self.format_response(current_best_argument)}")
            print("="*80 + "\n")

    def save_log(self):
        try:
            # Try to load existing logs
            try:
                with open(self.log_file, 'r') as f:
                    all_logs = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                all_logs = {"discussions": []}
            
            # Check if this session already exists
            session_exists = False
            for log in all_logs["discussions"]:
                if log["session_id"] == self.session_log["session_id"]:
                    log.update(self.session_log)
                    session_exists = True
                    break
            
            # If session doesn't exist, append it
            if not session_exists:
                all_logs["discussions"].append(self.session_log)
            
            # Save all logs
            with open(self.log_file, 'w') as f:
                json.dump(all_logs, f, indent=2)
                
        except Exception as e:
            logging.error(f"Error saving log: {e}")

async def main():
    print("""
🤖 Welcome to the Socratic Debate System! 🤖

This system will generate an intelligent discussion between three AI bots:
• Bot A (Connector): Finds connections between concepts
• Bot B (Evaluator): Analyzes and critiques connections
• Bot C (Decider): Guides discussion and ensures novelty

The discussion can use:
• Your chosen concepts
• Random Wikipedia topics
• A mix (you provide one, we choose one)
    """)

    manager = DiscussionManager()
    await manager.run_discussion()

    print("\nWould you like to start another discussion? (y/n)")
    while input().lower().strip() in ['y', 'yes']:
        await manager.run_discussion()
        print("\nWould you like to start another discussion? (y/n)")

    print("\nThank you for using the Socratic Debate System! 👋")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDiscussion terminated by user. Goodbye! 👋")
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        logging.error(f"Error in main execution: {e}", exc_info=True) 