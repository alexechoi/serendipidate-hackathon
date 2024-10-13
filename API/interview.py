import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import asyncio
import httpx
import os
from dotenv import load_dotenv
import logging
import random

# Import Firebase modules
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()  # Load environment variables

API_KEY = "KEY"
API_KEYS = [
    "KEY",
]
MODEL = "gemini-1.5-flash"
# MODEL1 = "groq/llama-3.1-70b-versatile"
MODEL1 = "azure/gpt-4o-mini"
API_ENDPOINT = "https://llm.kindo.ai/v1/chat/completions"

# Initialize Firebase Admin SDK
cred = credentials.Certificate('serviceAccountKey.json')  # Ensure the path is correct
firebase_admin.initialize_app(cred)

# Get Firestore client
db = firestore.client()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend's URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Answer(BaseModel):
    content: str

class InterviewState:
    def __init__(self):
        self.conversation_log: List[Dict[str, str]] = []
        self.covered_topics: set = set()
        self.question_count: int = 0
        self.last_topic: Optional[str] = None  # Add this line

interview_states = {}  # Key: user_id, Value: InterviewState instance
max_questions = 10

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add this new class definition
class SimulationRequest(BaseModel):
    user_id1: str
    user_id2: str
    num_exchanges: int = 10

def format_conversation_log(conversation_log):
    formatted = ""
    for msg in conversation_log:
        role = msg['role']
        content = msg['content']
        if role == 'assistant':
            formatted += f"Assistant: {content}\n"
        elif role == 'user':
            formatted += f"User: {content}\n"
    return formatted

@app.post("/start_interview")
async def start_interview(user_id: str):
    logger.info(f"Starting interview for user_id: {user_id}")
    interview_states[user_id] = InterviewState()
    initial_question, topic = await generate_question([], set())
    interview_states[user_id].conversation_log.append({"role": "assistant", "content": initial_question})
    if topic:
        interview_states[user_id].last_topic = topic  # Set the last topic
    logger.info(f"Initial question for user_id {user_id}: {initial_question}")
    return {"message": "Interview started", "initial_question": initial_question}

@app.get("/next_question")
async def next_question(user_id: str):
    logger.info(f"Generating next question for user_id: {user_id}")
    interview_state = interview_states.get(user_id)
    if not interview_state:
        logger.error(f"Invalid user_id: {user_id}")
        raise HTTPException(status_code=400, detail="Invalid user_id")
    
    if interview_state.question_count >= max_questions:
        logger.info(f"Interview completed for user_id: {user_id}")
        return {"message": "Interview completed"}
    
    question = await generate_question(interview_state.conversation_log, interview_state.covered_topics)
    interview_state.question_count += 1
    logger.info(f"Next question for user_id {user_id}: {question}")
    return {"question": question}

@app.post("/submit_answer")
async def submit_answer(user_id: str, answer: Answer):
    logger.info(f"Submitting answer for user_id: {user_id}")
    logger.info(f"Answer content: {answer.content}")
    interview_state = interview_states.get(user_id)
    if not interview_state:
        logger.error(f"Invalid user_id: {user_id}")
        raise HTTPException(status_code=400, detail="Invalid user_id")
    
    interview_state.conversation_log.append({"role": "user", "content": answer.content})

    # Update covered_topics based on the last topic
    if interview_state.last_topic:
        interview_state.covered_topics.add(interview_state.last_topic)
        interview_state.last_topic = None
    
    if interview_state.question_count >= max_questions:
        logger.info(f"Interview completed for user_id: {user_id}")
        return {"message": "Interview completed"}
    
    next_question, topic = await generate_question(interview_state.conversation_log, interview_state.covered_topics)
    interview_state.conversation_log.append({"role": "assistant", "content": next_question})
    interview_state.question_count += 1

    # Set the last topic for the next question
    if topic:
        interview_state.last_topic = topic

    logger.info(f"Next question for user_id {user_id}: {next_question}")
    return {"next_question": next_question}

async def make_api_call(messages):
    selected_api_key = random.choice(API_KEYS)  # Select a random API key
    headers = {
        "api-key": selected_api_key,
        "content-type": "application/json"
    }
    
    data = {
        "model": MODEL1,
        "messages": messages
    }

    logger.info(f"Messages: {messages}")
    
    async with httpx.AsyncClient(timeout=500.0) as client:
        response = await client.post(API_ENDPOINT, headers=headers, json=data)

    logger.info(f"Make API call response: {response}")
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.status_code} - {response.text}"

async def make_api_call_generate_profile(messages):
    selected_api_key = random.choice(API_KEYS)  # Select a random API key
    headers = {
        "api-key": selected_api_key,
        "content-type": "application/json"
    }
    
    data = {
        "model": MODEL,
        "messages": messages,
        "response_format": {"type": "json_object"}
    }
        
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(API_ENDPOINT, headers=headers, json=data)
            logger.info(f"Make API call response status: {response.status_code}")
            
            if response.status_code == 200:
                response = response.json()
                return response["choices"][0]["message"]["content"]
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return f"Error: {response.status_code} - {response.text}"
        except httpx.ReadTimeout:
            logger.error("API call timed out after 120 seconds")
            return "Error: API call timed out"
        except Exception as e:
            logger.error(f"Unexpected error during API call: {str(e)}")
            return f"Error: {str(e)}"

async def generate_question(conversation_log, covered_topics):
    required_topics = [
        "Name", "Gender", "Sexuality", "Age Group"
    ]
    
    possible_topics = [
        "Emotional Dependency", "Imagination and Fantasy", "Sentimental Attachment",
        "Expectations Management", "Spontaneity vs Routine", "Self-Narrative",
        "Physical Affection", "Curiosity and Learning Style", "Playfulness",
        "Empathy and Boundaries", "Individuality in Relationships", "Comfort with Boredom",
        "Attitude Toward Authority", "Comfort Rituals", "Gift Preferences",
        "Food and Shared Meals", "Emotional Risk Taking", "Adaptability to Changes",
        "Detail Orientation vs Big Picture", "Openness to Sharing Thoughts",
        "Handling Criticism", "Creativity and Art", "Patience Level",
        "Attitude Towards Aging", "Repetition and Habits", "Kindness to Strangers",
        "Fantasy vs Reality", "Handling Awkward Situations", "Appreciation of Beauty",
        "Technology and Connectivity", "Conflict Resolution Style",
        "Handling Success and Failure", "Openness to Growth",
        "Location and Lifestyle Preferences", "Interests and Hobbies",
        "Education and Intellectual Compatibility", "Social Preferences",
        "Family Dynamics", "Past Relationships", "Religion and Spiritual Beliefs",
        "Relationship Preferences", "Activity Preferences", "Education Level", 
        "Diet", "Smoking Habits", "Drinking Habits", "Spirituality and Religion"
    ]
    
    # First, ensure all required topics are covered
    for topic in required_topics:
        if topic not in covered_topics:
            return f"What is your {topic.lower()}?", topic  # Return the topic

    # If all required topics are covered, proceed with other topics
    remaining_topics = [topic for topic in possible_topics if topic not in covered_topics]

    formatted_conversation = format_conversation_log(conversation_log)

    if not conversation_log:  # If this is the first question
        system_prompt = """You are an AI assistant designed to build a comprehensive user dating profile through conversation.
Ask an open-ended question to start the conversation and learn about the user.
Focus on their interests, personality, background, experiences, values, or goals.
Ensure the question is engaging, natural, and encourages a detailed response, yet is remarkably simple."""
    else:
        system_prompt = f"""You are an AI assistant designed to build a comprehensive user dating profile through conversation.
Based on the previous conversation, identify areas that haven't been discussed yet and ask an open-ended question about one of the following topics: {', '.join(remaining_topics)}.
Focus on their interests, personality, background, experiences, values, or goals.
Ensure the question is engaging, natural, and encourages detailed responses. Do not reiterate or respond to their question. Your questions should be short and to the point and emulate real human conversation. 
Previous conversation:
{conversation_log}"""

    system_prompt += "\nAsk your next question:"

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    response = await make_api_call(messages)
    return response, None

@app.get("/generate_profile")
async def generate_profile(user_id: str):
    logger.info(f"Generating profile for user_id: {user_id}")
    interview_state = interview_states.get(user_id)
    if not interview_state:
        logger.error(f"Invalid user_id: {user_id}")
        raise HTTPException(status_code=400, detail="Invalid user_id")
    
    system_prompt = f"""You are an AI assistant designed to build a comprehensive user profile through conversation. 
Here is the conversation log: {interview_state.conversation_log} |
Your task is to take the conversation log and convert it into a JSON object that contains the user's profile.
Abide by the following JSON structure: {{
    "UserID": {{
        "BasicInfo": {{
            "Gender": "Male",
            "Sexuality": "Heterosexual",
            "AgeGroup": "18-24", "25-34", "35-44", "45-54", "55+",
            "RelationshipPreference": "Monogamous",
            "LocationPreference": "Urban",
            "Name": str,
            "Username": just put the name here too,
            "Bio": str about the users life experiecne and self description
        }},
        "ProfileInfo": {{
            "Username": str just put the name here too,
        }},
        "Lifestyle": {{
            "SmokingHabits": ["Non-smoker", "Occasional smoker", "Smoker"],
            "DrinkingHabits": ["Non-drinker", "Social drinker", "Regular drinker"],
            "Diet": ["Omnivore", "Vegetarian", "Vegan"],
            "ActivityLevel": ["Active", "Moderate", "Relaxed"],
            "Interests": [
                "Outdoor activities",
                "Arts and culture",
                "Reading and writing",
                "Fitness and sports",
                "Traveling",
                "Gaming",
                "Music and concerts",
                "Cooking and food"
            ]
        }},
        "Personality": {{
            "SocialStyle": ["Extroverted", "Introverted", "Ambivert"],
            "EmotionalExpression": ["Open", "Reserved", "Selective"],
            "ConflictResolution": ["Avoidant", "Direct", "Compromising"],
            "Spontaneity": ["Spontaneous", "Planner", "Flexible"],
            "OpennessToExperience": ["High", "Moderate", "Low"]
        }},
        "Values": {{
            "FamilyOrientation": ["Family-oriented", "Independent", "Balanced",
            "ReligionSpirituality": ["Religious", "Spiritual but not religious", "Not religious",
            "EducationImportance": ["Very important", "Somewhat important", "Not important",
            "CareerAmbition": ["Highly ambitious", "Moderately ambitious", "Laid-back"
        }},
        "RelationshipPreferences": {{
            "PhysicalAffection": "Very affectionate", "Somewhat affectionate", "Not very affectionate",
            "CommunicationStyle": "Direct", "Indirect", "Mixed",
            "IndividualityInRelationship": "Shares most activities", "Keeps some independence", "Maintains strong individuality"
        }}
    }}
}}"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Generate a user profile based on the conversation log. Infer as much information as possible from the conversation log."}
    ]

    logger.info(f"Calling API to generate profile for user_id: {user_id}")
    response = await make_api_call_generate_profile(messages)
    
    # if isinstance(response, str) and response.startswith("Error"):
    #     logger.error(f"API call failed: {response}")
    #     raise HTTPException(status_code=500, detail=response)

    try:
        # Check if the response starts with the specific string
        # if isinstance(response, str):
        #     # Extract the JSON part from the string
        #     json_str = response.split('```json', 1)[1].rsplit('```', 1)[0].strip()
        #     profile_data = json.loads(json_str)
        # else:
        #     # Parse the response as JSON
        print("DEBUG: " , response)
        profile_data = json.loads(response)
        
        logger.info(f"Profile data parsed successfully")
        logger.info(f"Successfully generated profile for user_id: {user_id}")

        # Store the profile in Firestore under the user's document
        try:
            user_doc_ref = db.collection('users1').document(user_id)
            user_doc_ref.set(profile_data, merge=True)
            logger.info(f"Profile stored in Firestore for user_id: {user_id}")
        except Exception as e:
            logger.error(f"Error storing profile in Firestore: {e}")
            raise HTTPException(status_code=500, detail="Error storing profile in Firestore")

        return {"profile": profile_data}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing profile JSON: {e}")
        logger.error(f"Raw content causing the error: {response}")
        raise HTTPException(status_code=500, detail="Error parsing profile JSON")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(f"Raw content: {response}")
        raise HTTPException(status_code=500, detail="Unexpected error occurred")

def main():
    print("Welcome to the User Profile Chatbot!")
    print("I'll ask you some questions to get to know you better. Type 'quit' at any time to exit.")
    
    conversation_log = []
    covered_topics = set()
    question_count = 0
    max_questions = 10

    while question_count < max_questions:
        question = generate_question(conversation_log, covered_topics)
        if not question:
            break  # Exit if the API call failed

        print("\nChatbot:", question)
        conversation_log.append(f"Chatbot: {question}")

        # Update covered topics based on the question
        for topic in covered_topics.copy():
            if topic.lower() in question.lower():
                covered_topics.add(topic)

        user_input = input("You: ").strip()
        conversation_log.append(f"You: {user_input}")
        if user_input.lower() == 'quit':
            break

        question_count += 1

    print("\nThank you for chatting with me! Here's a log of our conversation:")
    for entry in conversation_log:
        print(entry)

    return generate_profile(conversation_log)

# Add these new functions
def generate_conversation_prompt(profile: Dict, other_profile: Dict, setting: Dict, context: str, conversation_history: List[Dict]) -> str:
    username = profile["UserID"].get("ProfileInfo", {}).get("Username") or \
               profile["UserID"].get("BasicInfo", {}).get("Username") or \
               profile["UserID"].get("BasicInfo", {}).get("Name", "User")
    
    other_username = other_profile.get("UserID", {}).get("ProfileInfo", {}).get("Username") or \
                     other_profile.get("UserID", {}).get("BasicInfo", {}).get("Username") or \
                     other_profile.get("UserID", {}).get("BasicInfo", {}).get("Name", "Another user")

    prompt = f"""You are {username}, on a date with {other_username} at {setting['place']}. 
    Your profile:
    {json.dumps(profile['UserID'], indent=2)}

    Remember:
    1. Be yourself and speak naturally, as if in a real conversation.
    2. Keep responses brief (1-3 sentences) unless the context demands more.
    3. React to the setting, context, and previous messages.
    4. Show interest in {other_username} by asking questions occasionally.
    5. Use contractions, casual language, and even light humor if it fits your personality.

    Current context: {context}

    Conversation history:
    """

    for item in conversation_history[-5:]:  # Only include the last 5 exchanges for brevity
        if "speaker" in item:
            prompt += f"{item['speaker']}: {item['message']}\n"
        elif "action" in item:
            prompt += f"Action: {item['action']}\n"
        elif "event" in item:
            prompt += f"Event: {item['event']}\n"

    prompt += f"\nRespond as {username}:"

    return prompt
async def simulate_conversation(profile1: Dict, profile2: Dict, setting: Dict, num_exchanges: int = 10) -> List[Dict]:
    conversation = []
    context = f"You've just arrived at {setting['place']}. The atmosphere is {random.choice(['lively', 'relaxed', 'romantic', 'bustling'])}."

    for i in range(num_exchanges):
        speaker = profile1 if i % 2 == 0 else profile2
        listener = profile2 if i % 2 == 0 else profile1

        prompt = generate_conversation_prompt(speaker, listener, setting, context, conversation)
        response = await make_api_call([{"role": "system", "content": prompt}])
        
        speaker_username = (speaker.get("UserID", {}).get("ProfileInfo", {}).get("Username") or
                            speaker.get("UserID", {}).get("BasicInfo", {}).get("Username") or
                            speaker.get("UserID", {}).get("BasicInfo", {}).get("Name", "User"))
        
        conversation.append({
            "speaker": speaker_username,
            "message": response
        })

        # Introduce random events less frequently
        if random.random() < 0.15:
            if random.random() < 0.7:  # 70% chance for an action, 30% for an event
                action = random.choice(setting['actions'])
                conversation.append({"action": f"{speaker_username} {action}."})
                context = f"React to {speaker_username}'s action: {action}"
            else:
                event = random.choice(random_events)
                conversation.append({"event": event})
                context = f"React to this event: {event}"
        else:
            context = "Continue the conversation naturally, considering the setting and previous messages. and the user description"

    return conversation

async def analyze_compatibility(conversation: List[Dict], profile1: Dict, profile2: Dict) -> str:
    # Extract usernames safely
    username1 = (profile1.get("UserID", {}).get("ProfileInfo", {}).get("Username") or
                 profile1.get("UserID", {}).get("BasicInfo", {}).get("Username") or
                 profile1.get("UserID", {}).get("BasicInfo", {}).get("Name", "User1"))
    
    username2 = (profile2.get("UserID", {}).get("ProfileInfo", {}).get("Username") or
                 profile2.get("UserID", {}).get("BasicInfo", {}).get("Username") or
                 profile2.get("UserID", {}).get("BasicInfo", {}).get("Name", "User2"))

    analyzer_system_prompt = f"""You are an AI relationship analyst. Analyze the following conversation between 
    {username1} and {username2}. Determine their compatibility based on 
    their interaction, shared interests, personalities, and communication styles. Provide a detailed summary of 
    their compatibility and the reasons for your assessment. Be very strict and look at this deeper than just 
    the conversation. Compare them to see if they are long-term compatible and if they should go on another date.

    Profile 1: {json.dumps(profile1, indent=2)}
    Profile 2: {json.dumps(profile2, indent=2)}

    You should output an confidence score between 0 and 100 on why they are compatiable or not. 
    You should also output a detailed summary of the pros and cons of the relationsihp.
    Adhere to the following JSON structure and only return the JSON object. DO NOT INCLUDE ANY OTHER TEXT, besides the JSON object:
    {{
        "compatibility_score": int,
        "summary": short summary of pros and cons of the relationship
    }}
    """

    conversation_text = "\n".join(
        f"{msg['speaker']}: {msg['message']}"
        for msg in conversation
        if 'message' in msg
    )

    analyzer_messages = [
        {"role": "system", "content": analyzer_system_prompt},
        {"role": "user", "content": f"Analyze the following conversation:\n\n{conversation_text}"}
    ]

    analysis = await make_api_call(analyzer_messages)
    compatibility_score = None

    # First, try to parse as JSON
    try:
        analysis_json = json.loads(analysis)
        compatibility_score = analysis_json.get("compatibility_score")
        if compatibility_score is not None:
            compatibility_score = int(compatibility_score)
    except json.JSONDecodeError:
        pass

    # If JSON parsing failed or didn't yield a score, try regex
    if compatibility_score is None:
        match = re.search(r'\"compatibility_score\":\s*(\d+)', analysis)
        if match:
            compatibility_score = int(match.group(1))
        else:
            match = re.search(r'"compatibility_score":\s*(\d+)', analysis)
            if match:
                compatibility_score = int(match.group(1))

    # If we found a score, ensure it's in the response
    if compatibility_score is not None:
        try:
            analysis_json = json.loads(analysis)
            analysis_json["compatibility_score"] = compatibility_score
            analysis = json.dumps(analysis_json)
        except json.JSONDecodeError:
            analysis = json.dumps({
                "compatibility_score": compatibility_score,
                "summary": analysis
            })

    return analysis

# Add this new endpoint
@app.post("/simulate_conversation")
async def run_simulation(request: SimulationRequest):
    # Retrieve user profiles from Firestore
    user1_doc = db.collection('users1').document(request.user_id1).get()
    user2_doc = db.collection('users1').document(request.user_id2).get()

    if not user1_doc.exists or not user2_doc.exists:
        raise HTTPException(status_code=404, detail="One or both user profiles not found")

    profile1 = user1_doc.to_dict()
    profile2 = user2_doc.to_dict()
    # return profile1, profile2
    results = []
    
    for setting in meeting_settings:
        conversation = await simulate_conversation(profile1, profile2, setting, request.num_exchanges)
        analysis = await analyze_compatibility(conversation, profile1, profile2)
        
        # Parse the analysis string into a JSON object
        try:
            analysis_json = json.loads(analysis)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse analysis JSON: {analysis}")
            analysis_json = {"compatibility_score": None, "summary": "Error parsing analysis"}

        formatted_conversation = []
        for item in conversation:
            if "speaker" in item:
                formatted_conversation.append(f"{item['speaker']}: {item['message']}")
            elif "action" in item:
                formatted_conversation.append(f"Action: {item['action']}")
            elif "event" in item:
                formatted_conversation.append(f"Event: {item['event']}")

        conversation_data = {
            "setting": setting,
            "conversation": formatted_conversation,
            "analysis": analysis_json,
            "users": [request.user_id1, request.user_id2],
            "compatibility": analysis_json.get("compatibility_score")
        }

        # Store conversation data in Firebase
        db.collection("users1").document(request.user_id1).collection("conversations").add(conversation_data)
        db.collection("users").document(request.user_id2).collection("conversations").add(conversation_data)

        results.append(conversation_data)

    return results

# Add these lists at the end of the file
meeting_settings = [
    # {"place": "Venice Beach", "actions": ["walk along the boardwalk", "watch street performers", "visit Muscle Beach"]},
    # {"place": "Griffith Observatory", "actions": ["stargaze", "enjoy the city view", "explore the exhibits"]},
    # {"place": "The Grove", "actions": ["window shop", "ride the trolley", "people-watch at the fountain"]},
    # {"place": "LACMA", "actions": ["admire art installations", "take photos at Urban Light", "discuss favorite pieces"]},
    # {"place": "Grand Central Market", "actions": ["try different food stalls", "people-watch", "discuss culinary preferences"]},
    # {"place": "Runyon Canyon", "actions": ["hike", "enjoy the view", "spot celebrities"]},
    {"place": "Santa Monica Pier", "actions": ["ride the Ferris wheel", "play arcade games", "watch the sunset"]},
    {"place": "Echo Park Lake", "actions": ["rent a pedal boat", "have a picnic", "feed the ducks"]},
    # {"place": "The Getty Center", "actions": ["explore the gardens", "admire the architecture", "discuss art"]},
    # {"place": "Melrose Avenue", "actions": ["shop at vintage stores", "take photos at colorful walls", "people-watch"]},
    # {"place": "Hollywood Walk of Fame", "actions": ["find favorite stars", "take photos with street performers", "visit Grauman's Chinese Theatre"]},
    # {"place": "Abbot Kinney Boulevard", "actions": ["browse boutique shops", "try trendy restaurants", "admire street art"]},
    # {"place": "The Broad", "actions": ["view contemporary art", "take selfies in the Infinity Mirror Rooms", "discuss modern artists"]},
    # {"place": "Exposition Park", "actions": ["visit the Natural History Museum", "stroll through the Rose Garden", "check out the Space Shuttle Endeavour"]},
    # {"place": "Little Tokyo", "actions": ["shop for anime merchandise", "eat at a ramen shop", "visit the Japanese American National Museum"]},
    # {"place": "The Last Bookstore", "actions": ["explore the book tunnels", "hunt for vinyl records", "admire the book sculptures"]},
    # {"place": "Koreatown", "actions": ["sing karaoke", "enjoy Korean BBQ", "relax at a Korean spa"]},
    # {"place": "Olvera Street", "actions": ["try authentic Mexican food", "shop for traditional crafts", "learn about LA history"]},
    {"place": "Malibu Beach", "actions": ["sunbathe", "surf", "celebrity-spot"]},
    # {"place": "Universal CityWalk", "actions": ["watch a movie", "enjoy live music", "dine at themed restaurants"]},
]

random_events = [
    "A gentle breeze picks up.",
    "Someone's phone starts ringing.",
    "A child laughs loudly nearby.",
    "A delivery person walks by with a stack of packages.",
    "The sound of construction work can be heard faintly.",
    "Someone drops their keys and scrambles to pick them up.",
    "A leaf falls from a nearby tree.",
    "Someone sneezes loudly.",
    "A group of tourists asks for directions.",
    "The smell of food wafts from a nearby restaurant.",
    "A jogger runs past, breathing heavily.",
    "A street musician starts playing in the distance.",
    "The crosswalk signal changes, prompting people to cross.",
    "A car alarm goes off briefly before being silenced.",
    "A gust of wind blows a piece of paper down the street.",
    "A couple walks by holding hands.",
    "Someone takes a selfie nearby.",
    "A person checks their watch and hurries along.",
    "The sound of laughter comes from a nearby group.",
    "A bird chirps from a nearby tree or building.",
    "Someone's bag splits open, spilling contents on the ground.",
    "A person struggles with an umbrella on a windy day.",
    "The smell of coffee drifts from a nearby cafe.",
    "A street cleaner passes by.",
    "Someone stops to tie their shoelace.",
    "A person fumbles with their wallet at a nearby vendor.",
    "The sound of a camera shutter clicking is heard.",
    "A group of friends greet each other enthusiastically.",
]

async def run_matching_simulation(user_id: str):
    logger.info(f"Starting matching simulation for user_id: {user_id}")
    
    try:
        # Retrieve the user's profile
        user_doc = db.collection('users1').document(user_id).get()
        if not user_doc.exists:
            logger.error(f"User with ID {user_id} not found")
            raise ValueError(f"User with ID {user_id} not found")

        user_profile = user_doc.to_dict()
        logger.info(f"Retrieved user profile: {json.dumps(user_profile, indent=2)}")

        user_basic_info = user_profile.get('UserID', {}).get('BasicInfo', {})
        logger.info(f"User basic info: {json.dumps(user_basic_info, indent=2)}")

        # Define matching criteria
        user_gender = user_basic_info.get('Gender', [])
        logger.info(f"User gender: {user_gender}")

        # Query for potential matches
        matches_query = db.collection('users1')
        logger.info(f"user_gender: {user_gender}")
        if user_gender.lower() == 'male':
            logger.info("Querying for Female matches")
            matches_query = db.collection('users1').where('UserID.BasicInfo.Gender', 'array_contains', 'Female')
        elif user_gender.lower() == 'female':
            logger.info("Querying for Male matches")
            matches_query = db.collection('users1').where('UserID.BasicInfo.Gender', 'array_contains', 'Male')
        else:
            logger.warning(f"Unhandled gender: {user_gender}")
            return []

        logger.info(f"Executing query")
        potential_matches = list(matches_query.stream())
        logger.info(f"Query returned {len(potential_matches)} potential matches")

        # If no matches found, try an alternative query
        if not potential_matches:
            logger.info("No matches found with array_contains. Trying alternative query.")
            matches_query = db.collection('users1')
            if 'Male' in user_gender:
                matches_query = matches_query.where('UserID.BasicInfo.Gender', '==', 'Female')
            elif 'Female' in user_gender:
                matches_query = matches_query.where('UserID.BasicInfo.Gender', '==', 'Male')
            logger.info(f"Executing alternative query")
            potential_matches = list(matches_query.stream())
            logger.info(f"Alternative query returned {len(potential_matches)} potential matches")

        # Remove the user from potential matches
        potential_matches = [match for match in potential_matches if match.id != user_id]
        logger.info(f"After removing self, found {len(potential_matches)} potential matches")

        # Log details of potential matches
        for i, match in enumerate(potential_matches):
            match_data = match.to_dict()
            logger.info(f"Potential match {i+1}:")
            logger.info(f"  ID: {match.id}")
            logger.info(f"  Data: {json.dumps(match_data, indent=2)}")

        simulation_results = []
        async def simulate_conversation(match):
            logger.info(f"Processing potential match: {match.id}")
            match_profile = match.to_dict()
            logger.info(f"Match profile: {json.dumps(match_profile, indent=2)}")
            
            # Simulate conversation
            simulation_request = SimulationRequest(user_id1=user_id, user_id2=match.id, num_exchanges=10)
            logger.info(f"Simulating conversation between {user_id} and {match.id}")
            conversation_results = await run_simulation(simulation_request)
            logger.info(f"Conversation simulation results: {conversation_results}")
            
            return {
                'match_id': match.id,
                'match_profile': match_profile,
                'conversation_results': conversation_results
            }

        # Process matches in batches of 3
        batch_size = 3
        simulation_results = []

        for i in range(0, len(potential_matches), batch_size):
            batch = potential_matches[i:i+batch_size]
            
            # Use asyncio.gather to run simulations concurrently for the batch
            tasks = [simulate_conversation(match) for match in batch]
            batch_results = await asyncio.gather(*tasks)
            
            simulation_results.extend(batch_results)
            
            # Add a small delay between batches to avoid rate limiting
            if i + batch_size < len(potential_matches):
                await asyncio.sleep(1)  # 1 second delay between batches

        logger.info(f"Completed simulations. Total results: {len(simulation_results)}")

        logger.info(f"Completed simulations. Total results: {len(simulation_results)}")

        # Sort results by compatibility score
        sorted_results = sorted(simulation_results, 
                                key=lambda x: x['conversation_results'][0]['analysis']['compatibility_score'], 
                                reverse=True)
        logger.info("Sorted simulation results")

        # Store overall results in Firestore
        overall_results = {
            'user_id': user_id,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'matches': [{
                'match_id': result['match_id'],
                'compatibility_score': result['conversation_results'][0]['analysis']['compatibility_score']
            } for result in sorted_results]
        }
        db.collection('matching_results').add(overall_results)

        return sorted_results

    except Exception as e:
        logger.error(f"Error in matching simulation: {str(e)}")
        raise

# Add this new endpoint to run the matching simulation
@app.post("/run_matching_simulation")
async def api_run_matching_simulation(user_id: str):
    try:
        results = await run_matching_simulation(user_id)
        return {"message": "Matching simulation completed successfully", "results": results}
    except Exception as e:
        logger.error(f"Error in matching simulation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in matching simulation: {str(e)}")

# You can call this function from your main routine or create a new endpoint
if __name__ == "__main__":
    user_id_to_match = "example_user_id"  # Replace with actual user ID
    asyncio.run(run_matching_simulation(user_id_to_match))

async def fetch_sorted_conversations(user_id: str):
    try:
        # Get Firestore client
        db = firestore.client()

        # Query for conversations where the user is involved
        conversations = db.collection("users1").document(user_id).collection("conversations").stream()

        # Convert to list and sort by compatibility score
        conversation_list = []
        for conv in conversations:
            conv_data = conv.to_dict()
            # Ensure compatibility score exists and is a number
            if 'compatibility' in conv_data and isinstance(conv_data['compatibility'], (int, float)):
                conversation_list.append(conv_data)
            else:
                logging.warning(f"Conversation {conv.id} for user {user_id} has invalid compatibility score")

        # Sort conversations by compatibility score in descending order
        sorted_conversations = sorted(conversation_list, key=lambda x: x['compatibility'], reverse=True)

        return sorted_conversations

    except Exception as e:
        logging.error(f"Error fetching conversations for user {user_id}: {str(e)}")
        raise

@app.get("/user_conversations/{user_id}")
async def get_user_conversations(user_id: str):
    try:
        sorted_conversations = await fetch_sorted_conversations(user_id)
        return {"conversations": sorted_conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching conversations: {str(e)}")