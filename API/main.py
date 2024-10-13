import requests
import pyttsx3
import json
API_KEY = "f0ceb869-cc12-43df-bcb3-1d9fc1035789-986ca3b0ef3d65a6"
MODEL = "gemini-1.5-flash"
API_ENDPOINT = "https://llm.kindo.ai/v1/chat/completions"  # Example endpoint

headers = {
    "api-key": API_KEY,
    "content-type": "application/json"
}

# Function to encode image to base64
def encode_image(image_path):
    import base64
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def run_image_analysis():
    # Path to your image
    image_path = "neddy.jpeg"

    # Encoding the image
    base64_image = encode_image(image_path)

    data = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image, who this person is and list thier interests and hobbies in JSON format"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
    }

    response = requests.post(API_ENDPOINT, headers=headers, json=data)

    if response.status_code == 200:
        print(response.json())
    else:
        print(f"Error: {response.status_code}")

def speak_text(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)  # Adjust speaking rate
    engine.setProperty('volume', 0.8)  # Adjust volume
    engine.say(text)
    engine.runAndWait()

def speak_text(text):
    engine = pyttsx3.init()
    
    # Get current properties
    rate = engine.getProperty('rate')
    volume = engine.getProperty('volume')
    voices = engine.getProperty('voices')
    
    # Print current properties
    print(f"Current rate: {rate}")
    print(f"Current volume: {volume}")
    print(f"Available voices: {len(voices)}")
    
    # Adjust properties
    engine.setProperty('rate', 150)  # Speed of speech
    engine.setProperty('volume', 0.8)  # Volume (0.0 to 1.0)

    # Use default voice
    engine.say(f"This is a test using the default voice. {text}")
    engine.runAndWait()
    
    # Try female voice if available
    for i, voice in enumerate(voices):
        engine.setProperty('voice', voice.id)
        engine.say(f"This is voice number {i + 1}. {text}")
        engine.runAndWait()

def main():
    while True:
        user_input = input("Press Enter to analyze an image, or type 'quit' to exit: ")
        if user_input.lower() == 'quit':
            break

        result = run_image_analysis()
        if result:
            try:
                content = result['choices'][0]['message']['content']
                data = json.loads(content)
                description = data.get('description', 'No description available.')
                interests = ', '.join(data.get('interests', ['No interests found']))
                
                speak_text(f"Description: {description}")
                speak_text(f"Interests: {interests}")
            except (KeyError, json.JSONDecodeError):
                speak_text("Sorry, I couldn't process the image analysis result.")

if __name__ == "__main__":
    test_text = "How is it?"
    speak_text(test_text)
