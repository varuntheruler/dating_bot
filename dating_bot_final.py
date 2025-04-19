import streamlit as st
import google.generativeai as genai
import json
import os
import random

# ---- Gemini Setup ----
# Use environment variable or directly set the API key
api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyAV_22naAZmsXDGbZoAu-GB2Q8GU4XkuBM")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# ---- File for storing memory ----
MEMORY_FILE = "user_memory.json"

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

# ---- Streamlit Layout ----
st.set_page_config(page_title="AI Dating Bot", page_icon="❤️", layout="centered")
st.title("AI Dating Chat Buddy")

# ---- Sidebar Setup ----
with st.sidebar:
    st.header("Customize Your AI Date")

    if st.button("Reset Memory"):
        reset_memory()
        st.session_state.chat_started = False
        st.session_state.message_ratings = {}
        st.rerun()

    if not st.session_state.chat_started:
        user_name = st.text_input("Your Name", value="Alex")
        user_gender = st.radio("Your Gender", ["Male", "Female", "Non-binary", "Other"])
        bot_gender = st.radio("Bot Gender", ["Male", "Female", "Neutral"])

        bot_names = {
            "Male": ["Leo", "Max", "Aiden"],
            "Female": ["Luna", "Ava", "Mia"],
            "Neutral": ["Sky", "River", "Alex"]
        }
        bot_name = st.selectbox("Select AI Bot Name", bot_names[bot_gender])

        if st.button("Start Chat"):
            greeting = f"Hey {user_name}, it's so nice to meet you. You look absolutely stunning today!"
            st.session_state.chat_history = [{"role": "model", "parts": [greeting]}]
            st.session_state.chat_model = model.start_chat(history=st.session_state.chat_history)
            st.session_state.chat_started = True

            # Save memory
            user_data = {
                "user_name": user_name,
                "user_gender": user_gender,
                "bot_name": bot_name,
                "bot_gender": bot_gender,
                "chat_history": st.session_state.chat_history,
                "message_ratings": st.session_state.message_ratings
            }
            save_memory(user_data)
            st.rerun()
    else:
        st.success("Memory loaded! You can reset it in the sidebar.")
        
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
                    
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(f"### {emoji}")
                with col2:
                    st.markdown(f"### {message}")

# ---- Main Chat Area ----
if st.session_state.chat_started:
    user_name = user_data["user_name"] 
    bot_name = user_data["bot_name"]

    st.subheader(f"Chatting with {bot_name}")

    # Display chat history
    for i, msg in enumerate(st.session_state.chat_history):
        role = "assistant" if msg["role"] == "model" else "user"
        speaker_name = bot_name if role == "assistant" else user_name
        
        with st.chat_message(role):
            # Display the message
            if role == "assistant":
                st.markdown(f"{msg['parts'][0]}")
            else:
                st.markdown(f"{msg['parts'][0]}")
            
            # Show "Get feedback" button for user messages only
            if role == "user" and str(i) not in st.session_state.message_ratings:
                msg_index = str(i)
                button_key = f"rate_btn_{msg_index}"
                
                if st.button("Get feedback", key=button_key):
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

    # Chat input
    user_input = st.chat_input("Say something...")
    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "parts": [user_input]})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Generate bot response
        with st.spinner(f"{bot_name} is typing..."):
            response = st.session_state.chat_model.send_message(user_input)
            st.session_state.chat_history.append({"role": "model", "parts": [response.text]})
        
        with st.chat_message("assistant"):
            st.markdown(response.text)

        # Save updated history
        user_data["chat_history"] = st.session_state.chat_history
        save_memory(user_data)
        st.rerun()  # Refresh to show the rate button

    # ---- Suggestion Button ----
    if st.button("I'm stuck, suggest something to say"):
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
            with st.expander("Message ideas"):
                st.markdown(suggestion_response.text)
