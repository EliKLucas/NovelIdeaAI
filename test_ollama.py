from ollama import Client
import sys

client = Client(host='http://207.211.161.65:8080')

try:
    # First, try to get models
    print("Testing models list...")
    response = client.list()
    print(f"Models: {response}")
    
    # Finally, try a simple chat
    print("\nTesting chat...")
    response = client.chat(
        model='llama2',
        messages=[{'role': 'user', 'content': 'Hi!'}]
    )
    print(f"Chat response: {response}")

except Exception as e:
    print(f"Error type: {type(e)}")
    print(f"Error message: {str(e)}")
    print(f"Full error: {repr(e)}")
    sys.exit(1)
