import re
import requests
import random
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from typing import Any, List, Optional, Sequence

app = FastAPI()

# Set your API key and endpoint
API_KEY = "528c5eb5-b087-412f-b945-54245a184edb-fb13e142eb590d68"
MODEL = "gemini-1.5-flash"
API_ENDPOINT = "https://llm.kindo.ai/v1/chat/completions"

# Add more diverse meeting settings
meeting_settings = [
    {"place": "a cozy coffee shop", "actions": ["order drinks", "find a table", "people-watch", "work on laptops", "engage in deep conversations"]},
    {"place": "an art gallery opening", "actions": ["admire paintings", "discuss art", "sip champagne", "network with artists", "take photos of exhibits"]},
    {"place": "a hiking trail", "actions": ["climb steep paths", "take photos", "rest at viewpoints", "identify local flora", "share trail mix"]},
    {"place": "a bustling farmers market", "actions": ["sample local produce", "chat with vendors", "buy fresh ingredients", "compare prices", "learn about sustainable farming"]},
    {"place": "a tech startup office", "actions": ["brainstorm ideas", "demo new products", "discuss industry trends", "collaborate on code", "attend stand-up meetings"]},
    {"place": "a beachside boardwalk", "actions": ["walk along the shore", "play arcade games", "eat ice cream", "watch street performers", "collect seashells"]},
    {"place": "a cozy bookstore", "actions": ["browse shelves", "recommend books", "attend author reading", "sip coffee in the reading nook", "join a book club discussion"]},
    {"place": "a rooftop bar", "actions": ["enjoy the view", "try craft cocktails", "network with professionals", "take selfies with the skyline", "dance to the DJ's music"]},
    {"place": "a community garden", "actions": ["plant vegetables", "learn about composting", "share gardening tips", "harvest ripe produce", "attend a gardening workshop"]},
    {"place": "a local music venue", "actions": ["listen to live bands", "dance to the music", "discuss fa vorite artists", "buy band merchandise", "request songs from the DJ"]},
    {"place": "Griffith Observatory", "actions": ["stargaze through telescopes", "watch a planetarium show", "hike nearby trails", "take photos of the Hollywood sign", "learn about space exploration"]},
    {"place": "Venice Beach", "actions": ["watch street performers", "shop at quirky boutiques", "rollerblade along the boardwalk", "work out at Muscle Beach", "try acro-yoga"]},
    {"place": "The Getty Center", "actions": ["admire the art collection", "explore the gardens", "enjoy panoramic views of LA", "attend a lecture or workshop", "have a picnic on the grounds"]},
    {"place": "Universal CityWalk", "actions": ["watch movies at the cinema", "enjoy live music performances", "try diverse cuisines", "shop at themed stores", "people-watch"]},
    {"place": "Runyon Canyon", "actions": ["hike with dogs", "spot celebrities", "practice outdoor yoga", "enjoy city views", "participate in group fitness classes"]},
    {"place": "The Grove", "actions": ["shop at high-end stores", "ride the trolley", "watch the dancing fountain show", "attend a celebrity book signing", "dine al fresco"]},
    {"place": "Melrose Trading Post", "actions": ["hunt for vintage finds", "haggle with vendors", "enjoy live music", "try food truck cuisine", "discover local artisans"]},
    {"place": "Santa Monica Pier", "actions": ["ride the Ferris wheel", "play carnival games", "watch street magicians", "fish off the pier", "take a trapeze class"]},
]

# Add random events
random_events = [
    "A group of friends walks by, laughing loudly.",
    "The smell of freshly baked bread wafts through the air.",
    "A child drops their ice cream cone nearby.",
    "Someone's phone starts ringing with an unusual ringtone.",
    "A street performer starts juggling colorful balls.",
    "A couple at a nearby table gets into a minor disagreement.",
    "The waiter accidentally spills a drink on a customer.",
    "A group of tourists asks for directions.",
    "Someone's dog starts barking excitedly.",
    "The sun peeks out from behind the clouds, brightening the day.",
    "A delivery person struggles with a large package.",
    "Two people recognize each other and have a warm reunion.",
    "A gust of wind blows some papers off a nearby table.",
    "Someone trips on the sidewalk but recovers gracefully.",
    "The aroma of fresh coffee fills the air as someone orders an espresso.",
]

# Define profiles for AI agents and normal people around the LA area
profiles = [
    {
        "name": "Alice",
        "age": 28,
        "occupation": "Graphic Designer",
        "traits": {
            "personality": ["creative", "outgoing", "adventurous"],
            "interests": ["art", "travel", "yoga"],
            "quirks": ["always carries a sketchbook", "obsessed with matcha lattes"]
        },
        "conversation_style": "enthusiastic and expressive"
    },
    {
        "name": "Bob",
        "age": 30,
        "occupation": "Software Engineer",
        "traits": {
            "personality": ["analytical", "introverted", "thoughtful"],
            "interests": ["technology", "sci-fi", "music"],
            "quirks": ["uses programming analogies in daily life", "collects vintage keyboards"]
        },
        "conversation_style": "thoughtful and slightly awkward"
    },
    {
        "name": "Maria",
        "age": 35,
        "occupation": "Yoga Instructor",
        "traits": {
            "personality": ["calm", "spiritual", "health-conscious"],
            "interests": ["meditation", "vegan cooking", "hiking"],
            "quirks": ["starts every conversation with a deep breath", "always barefoot when possible"]
        },
        "conversation_style": "serene and mindful"
    },
    {
        "name": "Jamal",
        "age": 26,
        "occupation": "Aspiring Actor",
        "traits": {
            "personality": ["charismatic", "ambitious", "adaptable"],
            "interests": ["improv comedy", "film history", "networking"],
            "quirks": ["practices accents in everyday conversations", "always 'on' as if being filmed"]
        },
        "conversation_style": "energetic and performative"
    },
    {
        "name": "Sophie",
        "age": 32,
        "occupation": "Environmental Lawyer",
        "traits": {
            "personality": ["passionate", "articulate", "determined"],
            "interests": ["climate activism", "sustainable living", "outdoor sports"],
            "quirks": ["brings her own reusable everything everywhere", "can't help but correct misconceptions about recycling"]
        },
        "conversation_style": "informative and persuasive"
    },
    {
        "name": "Ethan",
        "age": 29,
        "occupation": "Food Truck Owner",
        "traits": {
            "personality": ["friendly", "hardworking", "creative"],
            "interests": ["culinary fusion", "local agriculture", "food photography"],
            "quirks": ["describes people using food metaphors", "always carries hot sauce"]
        },
        "conversation_style": "warm and flavor-focused"
    }
]

# Function to create a detailed system prompt for an agent
def create_system_prompt(profile, meeting_place, other_person_name):
    system_prompt = f"You are {profile['name']}, a {profile['age']}-year-old {profile['occupation']}. "

    if 'traits' in profile:
        traits = profile['traits']
        if 'personality' in traits:
            system_prompt += f"Your personality is {', '.join(traits['personality'])}. "
        if 'interests' in traits:
            system_prompt += f"Your interests include {', '.join(traits['interests'])}. "
        if 'quirks' in traits:
            system_prompt += f"You have these quirks: {', '.join(traits['quirks'])}. "

    if 'conversation_style' in profile:
        system_prompt += f"Your conversation style is {profile['conversation_style']}. "

    system_prompt += f"You are meeting {other_person_name} at {meeting_place}. "
    system_prompt += "Initiate and engage in a natural, friendly conversation."

    return system_prompt

# Get a random meeting place
meeting_place = random.choice(meeting_settings)['place']

# Function to make API calls
def make_api_call(messages):
    headers = {
        "api-key": API_KEY,
        "content-type": "application/json"
    }
    
    data = {
        "model": MODEL,
        "messages": messages,
        "response_format": { "type": "json_object" }
    }
    
    print(f"Sending request to: {API_ENDPOINT}")
    print(f"Headers: {headers}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    response = requests.post(API_ENDPOINT, headers=headers, json=data)
    
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.text}")
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.status_code} - {response.text}"

def generate_conversation_prompt(profile: Dict, other_profile: Dict, setting: Dict, context: str) -> str:
    return f"""You are {profile['name']}, a {profile['age']}-year-old {profile['occupation']}. 
    Your personality is {', '.join(profile['traits']['personality'])}.
    Your interests include {', '.join(profile['traits']['interests'])}.
    You have these quirks: {', '.join(profile['traits']['quirks'])}.
    Your conversation style is {profile['conversation_style']}.

    You're meeting {other_profile['name']} at {setting['place']}. {context}

    Respond naturally and briefly (1-3 sentences), considering the setting and context. Be yourself!"""

def simulate_conversation(profile1: Dict, profile2: Dict, num_exchanges: int = 3) -> List[Dict]:
    conversation = []
    setting = random.choice(meeting_settings)
    context = f"You've just arrived at {setting['place']}."

    for i in range(num_exchanges):
        # Determine who speaks
        speaker = profile1 if i % 2 == 0 else profile2
        listener = profile2 if i % 2 == 0 else profile1

        # Generate prompt
        prompt = generate_conversation_prompt(speaker, listener, setting, context)

        # Make API call
        response = make_api_call([{"role": "system", "content": prompt}])

        # Add to conversation
        conversation.append({
            "speaker": speaker['name'],
            "message": response
        })

        # Randomly add actions or events
        if random.random() < 0.3:
            action = random.choice(setting['actions'])
            conversation.append({"action": f"{speaker['name']} decides to {action}."})
        elif random.random() < 0.2:
            event = random.choice(random_events)
            conversation.append({"event": event})
            context = f"Respond to this event: {event}"
        else:
            context = f"Continue the conversation naturally."

    return conversation

def analyze_compatibility(conversation: List[Dict]) -> str:
    analyzer_system_prompt = (
        "You are an AI relationship analyst. Analyze the following conversation between two individuals "
        "named Alice and Bob. Determine their compatibility based on their interaction, shared interests, "
        "personalities, and communication styles. Provide a detailed summary of their compatibility and "
        "the reasons for your assessment. Be very strict and look at this deeper than just the conversation. "
        "Compare them to see if they are long-term compatible and if they should go on another date."
    )

    conversation_text = "\n".join(
        f"{'Alice' if idx % 2 == 0 else 'Bob'}: {msg['message']}"
        for idx, msg in enumerate(conversation)
        if 'message' in msg
    )

    analyzer_messages = [
        {"role": "system", "content": analyzer_system_prompt},
        {"role": "user", "content": f"Analyze the following conversation that took place at {random.choice(meeting_settings)['place']}:\n\n{conversation_text}"}
    ]

    analysis = make_api_call(analyzer_messages)

    return analysis

class SimulationRequest(BaseModel):
    num_exchanges: int = Field(default=3, ge=1, le=10)
    profile1_index: int = Field(default=0, ge=0, lt=len(profiles))
    profile2_index: int = Field(default=1, ge=0, lt=len(profiles))

@app.post("/simulate_conversation")
async def run_simulation(request: SimulationRequest):
    profile1 = profiles[request.profile1_index]
    profile2 = profiles[request.profile2_index]
    
    conversation = simulate_conversation(profile1, profile2, request.num_exchanges)
    analysis = analyze_compatibility(conversation)
    
    # Restructure the conversation for easier viewing
    formatted_conversation = []
    for item in conversation:
        if "speaker" in item:
            formatted_conversation.append(f"{item['speaker']}: {item['message']}")
        elif "action" in item:
            formatted_conversation.append(f"Action: {item['action']}")
        elif "event" in item:
            formatted_conversation.append(f"Event: {item['event']}")

    return {
        "setting": random.choice(meeting_settings)['place'],
        "conversation": formatted_conversation,
        "analysis": analysis
    }

@app.post("/test_llm")
async def test_llm(question: str):
    test_message = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": question}
    ]
    response = make_api_call(test_message)
    return response

def generate_profile_building_prompt(current_profile: Dict, conversation_history: List[Dict]) -> str:
    prompt = f"""You are an AI assistant designed to build rich user profiles through natural conversation. 
    Your goal is to extract information about the user's personality, interests, quirks, life experiences, 
    values, and intentions for using the app.

    Current profile information:
    {json.dumps(current_profile, indent=2)}

    Conversation history:
    {json.dumps(conversation_history, indent=2)}

    Based on the conversation so far, generate the next question to ask the user. 
    The question should be natural, engaging, and aimed at uncovering deeper insights 
    about the user. Adapt your tone and focus based on what has been shared so far.

    Your response should be in the following format:
    Question: [Your generated question here]
    Focus: [The aspect of the profile you're trying to uncover (e.g., "life_experiences", "quirks", "values")]
    """
    return prompt

def update_profile(profile: Dict, focus: str, user_response: str) -> Dict:
    update_prompt = f"""Given the user's response to a question about their {focus}, 
    update the relevant part of their profile. Here's the current profile and the user's response:

    Current profile:
    {json.dumps(profile, indent=2)}

    User's response: "{user_response}"

    Focus: {focus}

    Please provide the updated profile section in JSON format.
    """
    
    update_response = make_api_call([{"role": "system", "content": update_prompt}])
    
    try:
        updated_section = json.loads(update_response)
        if isinstance(updated_section, dict):
            profile.update(updated_section)
    except json.JSONDecodeError:
        print(f"Error decoding LLM response: {update_response}")
    
    return profile

class UserProfileBot:
    def __init__(self):
        self.llm = OpenAI(temperature=0.7, model="gemini-1.5-flash")  # Using Gemini model
        self.user_profile = {}
        self.interview_state = "introduction"
        
        self.interview_prompt = PromptTemplate(
            "You are an AI interviewer building a user profile. Current profile: {profile}. "
            "Interview state: {state}. Based on this, ask the next most appropriate question "
            "to build out the user's profile. Ask only one question at a time."
        )
        
        self.process_response_prompt = PromptTemplate(
            "Given the user profile: {profile}, the current question: {question}, "
            "and the user's response: {response}, update the user profile with any new information. "
            "Return the updated profile as a JSON string."
        )

    def ask_question(self):
        prompt = self.interview_prompt.format(
            profile=json.dumps(self.user_profile),
            state=self.interview_state
        )
        response = self.llm.complete(prompt)
        return response.text

    def process_response(self, question, response):
        prompt = self.process_response_prompt.format(
            profile=json.dumps(self.user_profile),
            question=question,
            response=response
        )
        updated_profile = self.llm.complete(prompt)
        self.user_profile = json.loads(updated_profile.text)

    async def run_interview(self):
        conversation_history = ["AI: Hello! I'm here to learn more about you. Let's start the interview."]
        
        while True:
            question = self.ask_question()
            conversation_history.append(f"AI: {question}")
            
            user_response = await self.get_user_input(question)
            if user_response.lower() == "exit":
                break
            
            conversation_history.append(f"Human: {user_response}")
            self.process_response(question, user_response)
            
            if len(self.user_profile) >= 5:
                self.interview_state = "wrapping_up"
            
            if self.interview_state == "wrapping_up" and len(self.user_profile) >= 7:
                break
        
        conversation_history.append("\nAI: Thank you for your time! Here's the profile I've built:")
        conversation_history.append(json.dumps(self.user_profile, indent=2))
        return conversation_history, self.user_profile

    async def get_user_input(self, question):
        # In a real application, this would wait for user input
        # For this example, we'll simulate user responses
        return "Simulated user response"

@app.post("/build_profile")
async def build_profile():
    bot = UserProfileBot()
    conversation_history, user_profile = await bot.run_interview()
    return {"conversation_history": conversation_history, "user_profile": user_profile}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)