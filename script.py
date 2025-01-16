import os
from dotenv import load_dotenv
import streamlit as st
from mistralai import Mistral
import httpx
from snowflake.snowpark import Session
from snowflake.core import Root

# Load environment variables
load_dotenv()

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

        # Print the response (the fetched chunks) for debugging purposes
        print("Cortex Search Response:", resp.to_json())

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
        Always mention the source (file URL) in response .
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
            background-color: #f8f9fa;
            font-family: "Arial", sans-serif;
        }

        /* Title styling */
        .stMarkdown h1 {
            color: #007bff;
            text-align: center;
            font-weight: bold;
            font-size: 2.5rem;
            margin-bottom: 20px;
        }

        /* Chatbox styling */
        .stChatMessage {
            margin: 10px 0;
            padding: 10px 15px;
            border-radius: 10px;
            background-color: #ffffff;
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
        }

        .stChatMessage.user {
            background-color: #e9ecef;
            text-align: right;
        }

        .stChatMessage.assistant {
            background-color: #007bff;
            color: #ffffff;
            overflow:hidden;

        }

        /* Example query buttons */
        .stButton button {
            background-color: #007bff;
            color: #ffffff;
            font-size: 14px;
            font-weight: bold;
            margin: 5px 0;
            border: none;
            border-radius: 5px;
            padding: 10px 15px;
        }

        .stButton button:hover {
            background-color: #0056b3;
        }

        /* Chat input box styling */
        .stChatInput textarea {
            border: 1px solid #007bff;
            border-radius: 5px;
            padding: 10px;
            font-size: 16px;
        }

        .stChatInput button {
            background-color: #007bff;
            color: #ffffff;
            border: none;
            padding: 10px 15px;
            font-size: 16px;
            border-radius: 5px;
            margin-top: 5px;
        }

        .stChatInput button:hover {
            background-color: #0056b3;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# Streamlit application
def main():
    add_custom_css()  # Add custom CSS for styling
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
        "What are the top tourist spots in Pakistan?",
        "Tell me about the history of Lahore.",
        "What is the best time to visit Hunza Valley?",
        "Are there any famous cultural festivals in Pakistan?",
        "What are the recommended foods to try in Karachi?",
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
    main()
