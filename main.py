import os
from dotenv import load_dotenv
import streamlit as st
from mistralai import Mistral
import httpx
from snowflake.snowpark import Session
from snowflake.core import Root
import time

# Load environment variables
load_dotenv()
st.set_page_config(layout="centered", 
                   page_icon="🤖",
                   page_title="Tourist Guide Bot")
# Snowflake connection setup
account = os.getenv("ACCOUNT")
user = os.getenv("USER")
password = os.getenv("PASSWORD")
role = os.getenv("ROLE", "ACCOUNTADMIN")
database = os.getenv("DATABASE", "MEDICALCHATBOT")
warehouse = os.getenv("WAREHOUSE", "COMPUTE_WH")
schema = os.getenv("SCHEMA", "PUBLIC")

# Initialize Snowflake session
CONNECTION_PARAMETERS = {
    "account": account,
    "user": user,
    "password": password,
    "role": role,
    "database": database,
    "warehouse": warehouse,
    "schema": schema,
}

try:
    session = Session.builder.configs(CONNECTION_PARAMETERS).create()
    root = Root(session)  # Initialize Root object for accessing Snowflake services
    print("Session created successfully.")
except Exception as e:
    print(f"Error creating session: {e}")

# Initialize Mistral client
api_key = os.getenv("MISTRAL_API_KEY", "your_api_key")
model = "mistral-large-latest"
client = Mistral(api_key=api_key)

# Define the Mistral response generation logic
def get_response(user_message):
    try:
        # Use Cortex Search to query the Snowflake database
        my_service = (
            root
            .databases["MEDICALCHATBOT"]
            .schemas["PUBLIC"]
            .cortex_search_services["CC_SEARCH_SERVICE_CS"]
        )

        # Perform search with the query
        resp = my_service.search(
            query=user_message,
            columns=["CHUNK", "FILE_URL", "CATEGORY"],  # Fetch CHUNK, FILE_URL, and CATEGORY
            limit=20,
        )

        # Extract the fetched context (chunks), file URLs, and categories from the response
        results = resp.results  # Use the `results` property to get the results
        if results:
            context_data = "\n".join(
                [f"{item['CHUNK']} (Source: {item['CATEGORY']})" for item in results]
            )  # Include both file URL and category as the source
        else:
            context_data = "No relevant data found."

        # Include the context in the system prompt
        system_prompt = f"""
        You are a tourist guide for Pakistan, named PakGuider. Use the provided context from official Government of Pakistan documents to answer user queries.
        If the required information is not in the context, clearly state that.
        Always mention the source (file URL) in response .Don't recommend any sort of
        external link that is not in the context.
        Below is the context that might help you answer the user's query:
        <context>
        {context_data}
        </context>
        <question>
        {user_message}
        </question>
        Answer:
        """

        # Combine system prompt with user message
        messages = [
            {"role": "system", "content": system_prompt}
        ] + st.session_state["messages"] + [{"role": "user", "content": user_message}]
        
        response = client.chat.complete(
            model=model,
            messages=messages,
            max_tokens=1000,
            safe_prompt=True  # Activates the safety prompt
        )
        return response.choices[0].message.content
    except httpx.ConnectError:
        return "There was a connection error. Please check your internet connection and try again."
    except Exception as e:
        return f"An unexpected error occurred: {e}"

# Custom CSS Styling Function
def add_custom_css():
    st.markdown(
        """
        <style>
        /* General layout styling */
        body {
            background-color: #f4f4f4;  /* Light greyish background */
            font-family: "Arial", sans-serif;
        }

        /* Title styling */
        .stMarkdown h1 {
            color: #006400;  /* Dark green, reflecting Pakistan's flag */
            text-align: center;
            font-weight: bold;
            font-size: 2.5rem;
            margin-bottom: 20px;
            font-family: 'Roboto', sans-serif;
        }

        /* Chatbox styling */
        .stChatMessage {
            margin: 10px 0;
            padding: 10px 15px;
            border-radius: 10px;
            background-color: #ffffff;  /* White background for messages */
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
        }

        .stChatMessage.user {
            background-color: #e9ecef;
            text-align: right;
            border: 2px solid #28a745;  /* Green border for user messages */
        }

        .stChatMessage.assistant {
            background-color: #006400;  /* Dark green background */
            color: #ffffff;  /* White text */
            overflow: hidden;
            border: 2px solid #28a745;  /* Green border for assistant messages */
        }

        /* Customize the color of the user and assistant icons */
        .stChatMessage.user .stChatMessageIcon {
            color: #28a745;  /* Green icon for user */
        }

        .stChatMessage.assistant .stChatMessageIcon {
            color: #ffffff;  /* White icon for assistant */
        }

        /* Example query buttons (styled with green and white, reflecting the flag colors) */
        .stButton button {
            background-color: #28a745;  /* Green background (Pakistan flag green) */
            color: #ffffff;  /* White text */
            font-size: 14px;
            font-weight: bold;
            margin: 5px 0;
            border: none;
            border-radius: 5px;
            padding: 10px 15px;
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
        }

        .stButton button:hover {
            background-color: #006400;  /* Darker green on hover */
        }

        /* Chat input box styling */
        .stChatInput textarea {
            border: 2px solid #006400;  /* Dark green border */
            border-radius: 5px;
            padding: 10px;
            font-size: 16px;
        }

        .stChatInput button {
            background-color: #006400;  /* Dark green button */
            color: #ffffff;
            border: none;
            padding: 10px 15px;
            font-size: 16px;
            border-radius: 5px;
            margin-top: 5px;
        }

        .stChatInput button:hover {
            background-color: #28a745;  /* Lighter green on hover */
        }

        /* Footer styling */
        .stFooter {
            text-align: center;
            font-size: 14px;
            color: #006400;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )





# Simulate a loading process with a progress bar
def loading_screen_with_progress():
    if not st.session_state.get("loading_shown"):  # Check if the loading screen has already been displayed
        loading_container = st.empty()  # Create a container to hold the loading screen

        with loading_container.container():  # Use container() to manage grouped elements
            st.title("🌏 Loading PakGuider")
            progress_bar = st.progress(0)
            status_text = st.markdown("")  # Placeholder for status text

            for i in range(101):  # Iterate from 0 to 100
                time.sleep(0.05)  # Simulate work by pausing for a short time
                progress_bar.progress(i)  # Update the progress bar
                status_text.markdown(f"**Loading... {i}%**")  # Update the status text dynamically

            status_text.markdown("**Loading complete!**")  # Final message after loading

        time.sleep(1)  # Optional delay for better visibility
        loading_container.empty()  # Clear the entire container

        # Set the flag to prevent the loading screen from showing again
        st.session_state["loading_shown"] = True

# Streamlit application
def main():
   
    
    add_custom_css()  # Add custom CSS for styling8
    
    # Render the background video HTML
    st.title("🌏 Pakistan Tourist Guide Chatbot")
    st.markdown(
        """
        <p style="text-align: left; font-size: 16px;">
        Welcome! I'm <strong>PakGuider</strong>, your personal tourist guide for exploring Pakistan.  
        Ask me about beautiful places, cultural events, or anything related to tourism in Pakistan. 🌟
        </p>
        """,
        unsafe_allow_html=True,
    )

    # Example queries
    example_queries = [
        "What is the visa policy for visiting the country?",
        "Are there any important contacts?",
        "What is the best time to visit Pakistan?",
        "What are policies regarding vaccinations?",
        "What types of clothes to wear season-wise?",
    ]

    # Initialize session state for input field
    if "input_value" not in st.session_state:
        st.session_state["input_value"] = ""  # Default input field value

    # Display example queries as buttons
    st.markdown("### Example Queries:")
    col1, col2, col3 = st.columns(3)
    for i, query in enumerate(example_queries):
        with [col1, col2, col3][i % 3]:
            if st.button(query):  # If a button is clicked
                st.session_state["input_value"] = query  # Set the input field value to the query

    # Initialize session state for messages
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "assistant", "content": "Hi! I'm here to help you with tourism-related questions about Pakistan!"}
        ]

    # Display chat history
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input field
    user_input = st.chat_input(
        "Your question:",  # Label for the input field
        key="chat_input",  # Unique key for the input field
    )

    # Process input when user presses Enter or when a query is set
    if st.session_state["input_value"]:
        user_input = st.session_state["input_value"]
        st.session_state["input_value"] = ""  # Reset the value for future use

    if user_input:
        # Add user message to session state
        st.session_state["messages"].append({"role": "user", "content": user_input})

        # Display user input in chat
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get assistant response
        with st.spinner("Assistant is typing..."):
            assistant_response = get_response(user_input)

        # Add assistant response to session state
        st.session_state["messages"].append({"role": "assistant", "content": assistant_response})

        # Display assistant response in chat
        with st.chat_message("assistant"):
            st.markdown(assistant_response)

if __name__ == "__main__":
    # Ensure the loading screen displays only once
    if "loading_shown" not in st.session_state:
        st.session_state["loading_shown"] = False  # Initialize flag for loading screen
        loading_screen_with_progress()  # Show loading screen before app content
    
    main()
