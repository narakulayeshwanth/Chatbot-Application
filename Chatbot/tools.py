from duckduckgo_search import DDGS
from openai import OpenAI
from config import OPENAI_API_KEY

try:
    client = OpenAI(api_key=OPENAI_API_KEY)
except:
    client = None

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Searches the internet for real-time information, news, and facts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generates a highly detailed image from a text prompt using DALL-E 3 and returns the image URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "A detailed text description of the image to generate."
                    }
                },
                "required": ["prompt"]
            }
        }
    }
]

def search_web(query):
    try:
        results = DDGS().text(query, max_results=3)
        return str(results)
    except Exception as e:
        return f"Search failed: {e}"

def generate_image(prompt):
    if not client: return "Image generation unavailable."
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        url = response.data[0].url
        return f"![Generated Image]({url})"
    except Exception as e:
        return f"Image generation failed: {e}"

def execute_tool_call(name, args):
    if name == "search_web":
        return search_web(args.get("query"))
    elif name == "generate_image":
        return generate_image(args.get("prompt"))
    return "Tool not found."
