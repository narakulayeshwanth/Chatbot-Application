import sys
import time
import re
from ai_engine import get_ai_response

def type_effect(text, delay=0.03):
    """Simulate a word-by-word or character-by-character typing effect."""
    # Split text into words and spaces using regex to preserve formatting
    tokens = re.findall(r'[\s\n]+|\S+', text)
    for token in tokens:
        sys.stdout.write(token)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def main():
    print("======================================================")
    print("🤖 lavangam.ai CLI Bot is running! (Type 'exit' to quit)")
    print("======================================================\n")
    
    history = []
    
    # Optional greeting
    greeting = "Hi, I'm lavangam.ai. I can help visualize data, parse files, or answer questions. How can I help you today?"
    print("Bot: ", end="")
    type_effect(greeting)
    
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.strip().lower() in ['exit', 'quit']:
                print("Bot: Goodbye!")
                break
            if not user_input.strip():
                continue
                
            print("Bot: ", end="", flush=True)
            
            # Get response from AI Engine
            response = get_ai_response(user_input, history)
            
            # Print with typing effect
            type_effect(response, delay=0.03)
            
            # Update history
            history.append({"user": user_input, "bot": response})
            
        except KeyboardInterrupt:
            print("\nBot: Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()
