import streamlit as st
import google.generativeai as genai
import json
import os
import random

# ---- Streamlit Page Configuration ----
st.set_page_config(
    page_title="AI Dating Buddy",
    page_icon="❤️",
    layout="wide",  # Using wide layout for better mobile adaptation
    initial_sidebar_state="collapsed"  # Start with sidebar collapsed on mobile
)

# ---- Gemini Setup ----
# Use environment variable or directly set the API key
api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyAV_22naAZmsXDGbZoAu-GB2Q8GU4XkuBM")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# ---- File for storing memory ----
MEMORY_FILE = "user_memory.json"

# ---- CSS for Mobile Responsiveness ----
st.markdown("""
<style>
    /* Mobile-friendly adjustments */
    @media (max-width: 768px) {
        .stButton>button {
            width: 100%;
            height: 50px;
            font-size: 16px;
            margin: 5px 0;
        }
        .stTextInput>div>div>input {
            font-size: 16px;
            height: 50px;
        }
        h1 {
            font-size: 1.8rem !important;
        }
        h2 {
            font-size: 1.5rem !important;
        }
        h3 {
            font-size: 1.2rem !important;
        }
        .stExpander {
            width: 100%;
        }
        /* Ensure chat bubbles are readable on mobile */
        .stChatMessage {
            padding: 10px !important;
            margin: 5px 0 !important;
        }
        /* Better spacing */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
    }
    /* General styling improvements */
    .chat-container {
        max-width: 800px;
        margin: 0 auto;
    }
    .emoji-rating {
        font-size: 24px;
    }
    .feedback-text {
        font-style: italic;
        color: #555;
    }
</style>
""", unsafe_allow_html=True)

# ---- Helper Functions ----
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f)

def reset_memory():
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)

def rate_message_human_like(message, chat_history, bot_name, user_name):
    """Rate message in a human-like way focusing on conversational flow"""
    # Get recent conversation context (last 5 messages)
    recent_context = []
    for msg in chat_history[-5:]:
        speaker = bot_name if msg["role"] == "model" else user_name
        recent_context.append(f"{speaker}: {msg['parts'][0]}")
    
    context_str = "\n".join(recent_context)
    
    prompt = f"""
    You are {bot_name}'s friend who's secretly watching their dating chat with {user_name}. 
    {user_name} just sent this message: "{message}"
    
    Recent conversation:
    {context_str}
    
    Give a quick human-like reaction to how this message works in the conversation flow.
    Rate from 1-10 but don't explicitly mention the rating scale.
    Be casual, use slang, and talk like a real friend would - not an AI.
    Avoid saying things like "as an AI" or mentioning prompts.
    Keep it short (max 15 words), authentic and conversational.
    
    Examples of good responses:
    - "That's gold! They're definitely going to love that response."
    - "Hmm, kinda flat. Maybe try showing more personality?"
    - "Perfect follow-up! You're totally vibing with them."
    """
    
    response = model.generate_content(prompt)
    
    # Add rating number (but don't show explicitly to user)
    sentiment_prompt = f"""
    On a scale of 1-10, rate the dating message quality based on this assessment: "{response.text}"
    Give ONLY the numerical rating, nothing else.
    """
    
    rating_response = model.generate_content(sentiment_prompt)
    try:
        # Try to extract just the numerical rating
        rating_num = int(rating_response.text.strip().split('/')[0].strip())
        # Keep in range 1-10
        rating_num = max(1, min(10, rating_num))
    except:
        # If we can't extract a clean number, make a guess based on the length 
        # of the message (simple fallback)
        rating_num = 5
    
    return {"text": response.text, "score": rating_num}

# ---- Load or Create Memory ----
user_data = load_memory()

# ---- Session Setup ----
if "chat_history" not in st.session_state:
    st.session_state.chat_history = user_data.get("chat_history", [])
if "chat_model" not in st.session_state:
    st.session_state.chat_model = model.start_chat(history=st.session_state.chat_history)
if "chat_started" not in st.session_state:
    st.session_state.chat_started = bool(user_data)
if "message_ratings" not in st.session_state:
    st.session_state.message_ratings = user_data.get("message_ratings", {})
if "user_id" not in st.session_state:
    # For multi-user support, generate a unique ID if needed
    st.session_state.user_id = user_data.get("user_id", str(random.randint(10000, 99999)))

# ---- Main Layout ----
# Create a more responsive layout
col_main, col_side = st.columns([3, 1], gap="small")

# Main Column - Chat Interface
with col_main:
    if st.session_state.chat_started:
        user_name = user_data["user_name"] 
        bot_name = user_data["bot_name"]
        
        st.markdown(f"<h1 class='chat-title'>Chat with {bot_name}</h1>", unsafe_allow_html=True)
        
        # Container for better mobile visualization of chat
        with st.container():
            # Display chat history
            for i, msg in enumerate(st.session_state.chat_history):
                role = "assistant" if msg["role"] == "model" else "user"
                speaker_name = bot_name if role == "assistant" else user_name
                
                with st.chat_message(role):
                    # Display the message
                    st.markdown(f"{msg['parts'][0]}")
                    
                    # Show feedback options for user messages only
                    if role == "user" and str(i) not in st.session_state.message_ratings:
                        msg_index = str(i)
                        button_key = f"rate_btn_{msg_index}"
                        
                        if st.button("Get feedback", key=button_key, help="Get feedback on how effective your message is"):
                            with st.spinner("Getting feedback..."):
                                rating = rate_message_human_like(
                                    msg["parts"][0], 
                                    st.session_state.chat_history[:i+1],
                                    bot_name,
                                    user_name
                                )
                                st.session_state.message_ratings[msg_index] = rating
                                # Save updated ratings
                                user_data["message_ratings"] = st.session_state.message_ratings
                                save_memory(user_data)
                                st.rerun()
                    
                    # Show rating feedback if available
                    if role == "user" and str(i) in st.session_state.message_ratings:
                        rating = st.session_state.message_ratings[str(i)]
                        
                        # Get appropriate emoji based on score
                        score = rating["score"]
                        if score >= 8:
                            emoji = "🔥"
                        elif score >= 6:
                            emoji = "👍"
                        elif score >= 4:
                            emoji = "😐"
                        else:
                            emoji = "😬"
                        
                        # Display the feedback with the emoji as a caption
                        feedback = f"{emoji} {rating['text']}"
                        st.caption(feedback)

            # Chat input - larger and more touch-friendly on mobile
            user_input = st.chat_input("Say something...", key="chat_input")
            if user_input:
                # Add user message to history
                st.session_state.chat_history.append({"role": "user", "parts": [user_input]})
                with st.chat_message("user"):
                    st.markdown(user_input)

                # Generate bot response with a mobile-friendly spinner
                with st.spinner(f"{bot_name} is typing..."):
                    response = st.session_state.chat_model.send_message(user_input)
                    st.session_state.chat_history.append({"role": "model", "parts": [response.text]})
                
                with st.chat_message("assistant"):
                    st.markdown(response.text)

                # Save updated history
                user_data["chat_history"] = st.session_state.chat_history
                save_memory(user_data)
                st.rerun()  # Refresh to show the rate button
                
            # Suggestion Button - Full width for better mobile tapping
            if st.button("I'm stuck, suggest something to say", use_container_width=True):
                with st.spinner("Getting ideas..."):
                    recent_messages = st.session_state.chat_history[-6:]
                    context = []
                    for msg in recent_messages:
                        speaker = bot_name if msg["role"] == "model" else user_name
                        context.append(f"{speaker}: {msg['parts'][0]}")
                    
                    context_str = "\n".join(context)
                    
                    prompt = f"""
                    You're {user_name}'s wingman/wingwoman helping them chat with {bot_name} on a dating app.
                    Based on this recent conversation, suggest 3 interesting things {user_name} could say next.
                    Be specific to the conversation, not generic. Make suggestions feel authentic and natural.
                    
                    Recent conversation:
                    {context_str}
                    
                    Format as a numbered list with 3 options. Each option should be 1-2 sentences max.
                    """
                    
                    suggestion_response = model.generate_content(prompt)
                    with st.expander("Message ideas", expanded=True):
                        st.markdown(suggestion_response.text)
    else:
        # Welcome screen when chat not started
        st.markdown("<h1 style='text-align: center;'>AI Dating Chat Buddy</h1>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <p style='font-size: 18px;'>Start by setting up your chat in the sidebar!</p>
            <p>(Click the > arrow at the top-left if on mobile)</p>
        </div>
        """, unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.markdown("<h2>Your Chat Settings</h2>", unsafe_allow_html=True)
    
    # Display user stats if chat has started
    if st.session_state.chat_started:
        st.success("Chat started!")
        
        # Display user's average rating with emoji
        if st.session_state.message_ratings:
            ratings = [r["score"] for r in st.session_state.message_ratings.values()]
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                
                # Rating emoji based on average
                if avg_rating >= 8:
                    emoji = "🔥"
                    message = "You're killing it!"
                elif avg_rating >= 6:
                    emoji = "😊"
                    message = "Going pretty well!"
                elif avg_rating >= 4:
                    emoji = "😐"
                    message = "Room for improvement"
                else:
                    emoji = "😬"
                    message = "Might need to step it up"
                    
                st.markdown(f"<div style='display: flex; align-items: center;'>"
                           f"<div style='font-size: 24px; margin-right: 10px;'>{emoji}</div>"
                           f"<div><b>{message}</b></div></div>", 
                           unsafe_allow_html=True)
        
        # Reset button more prominent on mobile
        if st.button("Reset Chat", use_container_width=True, help="This will erase the current conversation"):
            reset_memory()
            st.session_state.chat_started = False
            st.session_state.message_ratings = {}
            st.rerun()
    else:
        # Initial setup form - more mobile-friendly
        with st.form("setup_form"):
            st.subheader("Set Up Your Chat")
            
            user_name = st.text_input("Your Name", value="Alex")
            user_gender = st.radio("Your Gender", ["Male", "Female", "Non-binary", "Other"])
            
            st.subheader("Configure Your AI Date")
            bot_gender = st.radio("Bot Gender", ["Male", "Female", "Neutral"])

            bot_names = {
                "Male": ["Leo", "Max", "Aiden", "James", "Ryan"],
                "Female": ["Luna", "Ava", "Mia", "Emma", "Sofia"],
                "Neutral": ["Sky", "River", "Alex", "Jordan", "Quinn"]
            }
            bot_name = st.selectbox("Select AI Bot Name", bot_names[bot_gender])
            
            # Form submit button - full width for mobile
            submit_button = st.form_submit_button("Start Chat", use_container_width=True)
            
            if submit_button:
                greeting = f"Hey {user_name}, it's so nice to meet you. You look absolutely stunning today!"
                st.session_state.chat_history = [{"role": "model", "parts": [greeting]}]
                st.session_state.chat_model = model.start_chat(history=st.session_state.chat_history)
                st.session_state.chat_started = True

                # Save memory
                user_data = {
                    "user_id": st.session_state.user_id,
                    "user_name": user_name,
                    "user_gender": user_gender,
                    "bot_name": bot_name,
                    "bot_gender": bot_gender,
                    "chat_history": st.session_state.chat_history,
                    "message_ratings": st.session_state.message_ratings
                }
                save_memory(user_data)
                st.rerun()

# Footer for mobile users
st.markdown("""
<div style='margin-top: 30px; text-align: center; color: #666;'>
    <hr>
    <p>AI Dating Chat Buddy - Swipe right on conversation skills!</p>
</div>
""", unsafe_allow_html=True)