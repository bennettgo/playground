import streamlit as st
import requests
from datetime import datetime

BASE_URL = "https://apim.workato.com/workatop329/workato-chatapi-v1"

def init_session_state():
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ""
    if 'current_chat_id' not in st.session_state:
        st.session_state.current_chat_id = None
    if 'selected_agent_id' not in st.session_state:
        st.session_state.selected_agent_id = None
    if 'selected_kb_id' not in st.session_state:
        st.session_state.selected_kb_id = None

init_session_state()

# Helper function for API calls
def make_request(method, endpoint, data=None, params=None):
    headers = {"API-Token": st.session_state.api_key}
    try:
        response = requests.request(
            method=method,
            url=f"{BASE_URL}{endpoint}",
            headers=headers,
            json=data,
            params=params
        )
        return response.json() if response.content else {}
    except Exception as e:
        return {"error": str(e)}

# Sidebar for API key and basic info
with st.sidebar:
    st.header("API Configuration")
    st.session_state.api_key = st.text_input("API Key", type="password")
    st.markdown("---")
    st.markdown("**Current Session**")
    st.write(f"Active Chat: {st.session_state.current_chat_id or 'None'}")
    st.write(f"Selected Agent: {st.session_state.selected_agent_id or 'None'}")

# Main app tabs
tab1, tab2, tab3, tab4 = st.tabs(["Agents", "Chat", "Knowledge Bases", "Search"])

with tab1:  # Agents tab
    st.header("Agent Management")
    
    with st.expander("Create New Agent"):
        with st.form("create_agent"):
            name = st.text_input("Agent Name")
            description = st.text_area("Description")
            instructions = st.text_area("Instructions")
            if st.form_submit_button("Create Agent"):
                response = make_request("PUT", "/agents", data={
                    "agent_name": name,
                    "agent_description": description,
                    "agent_instruction": instructions
                })
                if "agent_id" in response:
                    st.success(f"Agent created! ID: {response['agent_id']}")

    with st.expander("View Agents"):
        agents = make_request("GET", "/agents")
        if agents.get("Records"):
            for agent in agents["Records"]:
                col1, col2 = st.columns([1,3])
                with col1:
                    st.write(f"**{agent['Agent_Name']}**")
                    st.write(f"ID: {agent['Agent_ID']}")
                with col2:
                    st.write(agent["description"])
                st.markdown("---")

with tab2:  # Chat tab
    st.header("Chat Interface")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Select Agent
    agents = make_request("GET", "/agents")
    agent_list = {a["Agent_ID"]: a["Agent_Name"] for a in agents.get("Records", [])}
    selected_agent = st.selectbox(
        "Select Agent", 
        options=list(agent_list.keys()), 
        format_func=lambda x: agent_list.get(x, "Unknown")
    )
    st.session_state.selected_agent_id = selected_agent

    # Chat management
    col1, col2 = st.columns(2)
    with col1:
        if selected_agent:
            chats = make_request("GET", "/agents/chats", params={"agent_id": selected_agent})
            chat_options = {c["chat_id"]: f"Chat {c['chat_id']} ({c['Created_at']})" 
                          for c in chats.get("Records", [])}
            
            selected_chat = st.selectbox(
                "Existing Chats",
                options=["New Chat"] + list(chat_options.keys()),
                format_func=lambda x: "Start new chat" if x == "New Chat" else chat_options.get(x, "Unknown")
            )
            
    with col2:
        if selected_agent and st.button("💬 Start New Conversation"):
            st.session_state.current_chat_id = None
            st.session_state.messages = []
            st.rerun()

    # Load selected chat history
    if st.session_state.api_key and selected_chat and selected_chat != "New Chat":
        if st.session_state.current_chat_id != selected_chat:
            st.session_state.current_chat_id = selected_chat
            history = make_request("GET", "/agents/chats/history", params={"chat_id": selected_chat})
            st.session_state.messages = []
            for step in history.get("steps", []):
                role = "user" if step["payload"]["step_type"] == "user_message" else "assistant"
                st.session_state.messages.append({
                    "role": role,
                    "content": step["payload"]["content"],
                    "timestamp": step["created_at"]
                })

    # Display chat messages - ABOVE the input
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            st.caption(f"_{message.get('timestamp', '')}_")

    # Handle user input - PROCESS FIRST BEFORE DISPLAYING MESSAGES
    if prompt := st.chat_input("Type your message...", key=f"input_{st.session_state.current_chat_id}"):
        # Add user message to chat history
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat()
        })

        # Prepare API payload
        data = {
            "agent_id": selected_agent,
            "user_email": "user@example.com",
            "user_message": prompt
        }
        if st.session_state.current_chat_id:
            data["chat_id"] = st.session_state.current_chat_id

        # Get agent response
        response = make_request("POST", "/agents/chats/send", data=data)
        
        if "agent_response" in response:
            # Add assistant response to chat history
            for resp in response["agent_response"]:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": resp["content"],
                    "timestamp": datetime.now().isoformat()
                })

            # Update current chat ID if new conversation
            if "chat_id" in response and not st.session_state.current_chat_id:
                st.session_state.current_chat_id = response["chat_id"]
                
        # Force rerun to show updated messages above input
        st.rerun()
                        
with tab3:  # Knowledge Bases tab
    st.header("Knowledge Base Management")
    
    with st.expander("Create Knowledge Base"):
        with st.form("create_kb"):
            kb_id = st.text_input("KB ID")
            name = st.text_input("Name")
            description = st.text_area("Description")
            if st.form_submit_button("Create"):
                response = make_request("PUT", "/knowledge", data={
                    "data": {
                        "knowledge_base_id": kb_id,
                        "name": name,
                        "description": description
                    }
                })
                st.success("KB created!" if not response else "Error")

    with st.expander("Upload Document"):
        kbs = make_request("GET", "/knowledge")
        kb_options = {kb["knowledge_base_id"]: kb["name"] for kb in kbs.get("knowledge_bases", [])}
        selected_kb = st.selectbox("Select KB", options=list(kb_options.keys()), format_func=lambda x: kb_options[x])
        doc_id = st.text_input("Document ID")
        content = st.text_area("Content")
        if st.button("Upload"):
            response = make_request("PUT", "/knowledge/document", data={
                "document_id": doc_id,
                "knowledge_base_id": selected_kb,
                "document": content
            })
            st.success("Document uploaded!" if not response else "Error")

    with st.expander("View Knowledge Bases"):
        kbs = make_request("GET", "/knowledge")
        if kbs.get("knowledge_bases"):
            for kb in kbs["knowledge_bases"]:
                st.write(f"**{kb['name']}** ({kb['knowledge_base_id']})")
                st.write(kb["description"])
                st.markdown("---")

with tab4:  # Search tab
    st.header("Knowledge Search")
    
    search_type = st.radio("Search Type", ["Semantic", "Exact", "Q&A"])
    kbs = make_request("GET", "/knowledge")
    kb_options = [kb["knowledge_base_id"] for kb in kbs.get("knowledge_bases", [])]
    selected_kbs = st.multiselect("Select Knowledge Bases", options=kb_options)
    
    if search_type == "Semantic":
        query = st.text_input("Search Query")
        num_results = st.number_input("Number of Results", value=3)
        if st.button("Search"):
            response = make_request("POST", "/knowledge/documents/semantic", data={
                "query": query,
                "knowledge_base_ids_to_query": selected_kbs,
                "number_of_chunks_to_retrieve": num_results
            })
            for chunk in response.get("retrieved_chunks", []):
                st.write(f"**{chunk['knowledge_base_id']}**")
                st.write(chunk["content"])
    
    elif search_type == "Exact":
        text = st.text_input("Exact Text")
        num_results = st.number_input("Number of Results", value=3)
        if st.button("Search"):
            response = make_request("POST", "/knowledge/documents/exact", data={
                "text": text,
                "knowledge_base_ids_to_query": selected_kbs,
                "num_of_chunks_to_retrieve": num_results
            })
            for chunk in response.get("retrieved_chunks", []):
                st.write(f"**{chunk['knowledge_base_id']}**")
                st.write(chunk["content"])
    
    elif search_type == "Q&A":
        question = st.text_input("Question")
        if st.button("Ask"):
            response = make_request("POST", "/knowledge/documents/ask", data={
                "knowledge_base_ids_to_query": selected_kbs,
                "question": question
            })
            st.write(f"Answer: {response.get('answer', 'No answer found')}")

st.markdown("---")
st.caption("Workato AI API Playground | Created with Streamlit")