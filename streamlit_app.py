import streamlit as st
import requests
import json
from datetime import datetime
import re
import os
import time
import base64

BASE_URL = "https://apim.workato.com/workatop329/workato-chatapi-v1"

############################################################
# Session State Initialization
############################################################
def init_session_state():
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ""
    if 'current_chat_id' not in st.session_state:
        st.session_state.current_chat_id = None
    if 'selected_agent_id' not in st.session_state:
        st.session_state.selected_agent_id = None
    if 'selected_kb_id' not in st.session_state:
        st.session_state.selected_kb_id = None
    # For agent creation/editing modal
    if 'show_create_agent_modal' not in st.session_state:
        st.session_state.show_create_agent_modal = False
    if 'edit_agent_mode' not in st.session_state:
        st.session_state.edit_agent_mode = False
    if 'edit_agent_data' not in st.session_state:
        st.session_state.edit_agent_data = {}
    # For chat messages
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    # For Chat tab new flow
    # 'list' to show conversation list, 'details' to show a single conversation
    if 'chat_view' not in st.session_state:
        st.session_state.chat_view = 'list'
    # For Function Registries
    if 'selected_function_registry_id' not in st.session_state:
        st.session_state.selected_function_registry_id = None
    if 'function_registry_view' not in st.session_state:
        st.session_state.function_registry_view = 'list'
    if 'show_create_function_registry_modal' not in st.session_state:
        st.session_state.show_create_function_registry_modal = False


init_session_state()

############################################################
# Helper function for API calls
############################################################
def make_request(method, endpoint, data=None, params=None):
    """
    A helper function to make requests to the specified endpoint.
    """
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

############################################################
# UI Layout
############################################################
# Sidebar
with st.sidebar:
    st.header("API Configuration")
    st.session_state.api_key = st.text_input("API Key", type="password")
    st.info("Contact Bennett Goh for a key")
    st.markdown("---")
    st.markdown("**Current Session**")
    st.write(f"Active Chat: {st.session_state.current_chat_id or 'None'}")
    st.write(f"Selected Agent: {st.session_state.selected_agent_id or 'None'}")

############################################################
# Landing Page when API key is missing
############################################################
if not st.session_state.api_key:
    st.title("Workato Copilot Playground")
    st.markdown(
        """
        ## Welcome! 
        To get started:
        1. Enter your API key in the sidebar 🔑  
        2. Select a feature from the tabs above 👆  
        3. Start interacting with the APIs 🚀
        
        *Contact Bennett if you need an API key*
        """
    )
    st.image("https://cdn-icons-png.flaticon.com/512/2092/2092683.png", width=200)

else:
    ############################################################
    # Main Tabs (only show if we have an API key)
    ############################################################
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Agents", "Chat", "Functions", "Knowledge Bases", "Search"])

    ############################################################
    # Tab 1 - Agent Management
    ############################################################
    with tab1:
        st.header("Agent Management")
        st.info("Give your agent instructions, knowledge and functions. Then chat with it in the next tab.")

        # Fetch all agents
        agents_response = make_request("GET", "/agents")
        agent_records = agents_response.get("Records", [])

        # Also fetch function registries for picklist
        func_registries_resp = make_request("GET", "/functions")
        registry_list = func_registries_resp.get("function_registries", [])
        # We'll store them as { ID: ID } for a selectbox, or { ID: Name } if you have a name field
        registry_map = {}
        for reg in registry_list:
            rid = reg.get("function_registry_id", "")
            registry_map[rid] = rid  # or reg.get("name", rid)

        # Function to parse knowledge field
        def parse_agent_knowledge(agent_record):
            if not agent_record.get("knowledge"):
                return []
            try:
                parsed = json.loads(agent_record["knowledge"])
                return parsed if isinstance(parsed, list) else []
            except:
                return []

        # Functions to show/hide the creation modal
        def open_create_agent_modal(edit=False, agent_data=None):
            st.session_state.show_create_agent_modal = True
            st.session_state.edit_agent_mode = edit
            st.session_state.edit_agent_data = agent_data if agent_data else {}

        def close_create_agent_modal():
            st.session_state.show_create_agent_modal = False
            st.session_state.edit_agent_mode = False
            st.session_state.edit_agent_data = {}

        with st.expander("View / Update Agents"):
            if agent_records:
                for agent in agent_records:
                    kb_list = parse_agent_knowledge(agent)
                    with st.container():
                        col1, col2 = st.columns([5,3])
                        with col1:
                            st.markdown(f"**Name**: {agent.get('Agent_Name', '')}")
                            st.markdown(f"**ID**: {agent.get('Agent_ID', '')}")
                            st.markdown(f"**Description**: {agent.get('description', '')}")
                            st.markdown(f"**Instruction**: {agent.get('instruction', '')}")
                            if kb_list:
                                st.markdown(f"**Knowledge Bases**: {', '.join(kb_list)}")
                            else:
                                st.markdown("**Knowledge Bases**: None")
                            # If you show function_registry_id, you can do so here:
                            fr_id = agent.get("functions", None)
                            st.markdown(f"**Function Registry**: {fr_id if fr_id else 'None'}")
                        with col2:
                            if st.button("Edit", key=f"edit_{agent['Agent_ID']}"):
                                open_create_agent_modal(
                                    edit=True,
                                    agent_data={
                                        'agent_id': agent.get('Agent_ID', ''),
                                        'agent_name': agent.get('Agent_Name', ''),
                                        'agent_description': agent.get('description', ''),
                                        'agent_instruction': agent.get('instruction', ''),
                                        'knowledge_bases': kb_list,
                                        'functions': agent.get("functions", "")
                                    }
                                )
                        st.markdown("---")
            else:
                st.info("No agents found.")

        if st.button("Create New Agent"):
            open_create_agent_modal(edit=False)

        # Modal simulation
        if st.session_state.show_create_agent_modal:
            st.write("---")
            if st.session_state.edit_agent_mode:
                st.subheader("Edit Agent")
            else:
                st.subheader("Create New Agent")

            with st.form("create_or_update_agent_form", clear_on_submit=False):
                agent_id = st.session_state.edit_agent_data.get('agent_id', '')
                agent_name = st.text_input(
                    "Agent Name",
                    value=st.session_state.edit_agent_data.get('agent_name', '')
                )
                agent_description = st.text_area(
                    "Description",
                    value=st.session_state.edit_agent_data.get('agent_description', '')
                )
                agent_instruction = st.text_area(
                    "Instructions",
                    value=st.session_state.edit_agent_data.get('agent_instruction', '')
                )

                # Knowledge base selection
                kbs_response = make_request("GET", "/knowledge")
                kb_options = [kb.get("knowledge_base_id", "") for kb in kbs_response.get("knowledge_bases", [])]

                selected_kbs = st.multiselect(
                    "Select Knowledge Bases",
                    options=kb_options,
                    default=st.session_state.edit_agent_data.get('knowledge_bases', [])
                )

                selected_registry_id = st.selectbox(
                    "Select Function Registry",
                    options=["None"] + list(registry_map.keys()),
                    index=0
                    if not st.session_state.edit_agent_data.get("functions")
                    else (list(registry_map.keys()).index(st.session_state.edit_agent_data.get("functions")) + 1),
                    format_func=lambda x: x if x != "None" else "None"
                )

                submitted = st.form_submit_button("Save")
                if submitted:
                    upsert_data = {
                        "agent_name": agent_name,
                        "agent_description": agent_description,
                        "agent_instruction": agent_instruction,
                        "knowledge_bases": selected_kbs
                    }
                    if agent_id:
                        upsert_data["agent_id"] = agent_id
                    
                    if selected_registry_id != "None":
                        upsert_data["function_registry_id"] = selected_registry_id

                    resp = make_request("PUT", "/agents", data=upsert_data)
                    if "agent_id" in resp:
                        st.success(f"Agent upserted successfully! ID: {resp['agent_id']}")
                        close_create_agent_modal()
                        st.rerun()
                    else:
                        st.error(f"Error upserting agent: {resp.get('error_reason', 'Unknown error')}")

            if st.button("Cancel"):
                close_create_agent_modal()
                st.rerun()

    ############################################################
    # Tab 2 - Chat Interface
    ############################################################
    with tab2:
        st.header("Chat Interface")

        # Helper: load conversation
        def load_conversation(chat_id):
            history = make_request("GET", "/agents/chats/history", params={"chat_id": chat_id})
            st.session_state.messages = []
            for step in history.get("steps", []):
                role = "user" if step["payload"].get("step_type") == "user_message" else "assistant"
                st.session_state.messages.append({
                    "role": role,
                    "content": step["payload"].get("content", ""),
                    "timestamp": step.get("created_at", "")
                })

        def back_to_list():
            st.session_state.chat_view = 'list'
            st.session_state.current_chat_id = None
            st.session_state.messages = []

        # Always get agents for the dropdown
        agents_for_chat = make_request("GET", "/agents")
        agent_list_dropdown = {
            a.get("Agent_ID", ""): a.get("Agent_Name", "Unknown") 
            for a in agents_for_chat.get("Records", [])
        }

        # If no agents exist, show a warning
        if not agent_list_dropdown:
            st.warning("No agents available. Please create an agent first.")
        else:
            # Let user choose an agent
            selected_agent = st.selectbox(
                "Select Agent",
                options=["None"] + list(agent_list_dropdown.keys()),
                format_func=lambda x: agent_list_dropdown.get(x, x) if x != "None" else "Select an Agent",
            )

            if selected_agent == "None":
                st.info("Please select an agent to view or create conversations.")
            else:
                st.session_state.selected_agent_id = agent_list_dropdown[selected_agent]
                

                if st.session_state.chat_view == 'list':
                    # Show list of existing conversations
                    st.subheader(f"Conversations for Agent: {agent_list_dropdown[selected_agent]}")

                    # Button for new conversation
                    if st.button("Start New Conversation"):
                        st.session_state.chat_view = 'details'
                        st.session_state.current_chat_id = None
                        st.session_state.messages = []
                        st.rerun()

                    # Get existing chats
                    conv_response = make_request("GET", "/agents/chats", params={"agent_id": selected_agent})
                    chat_records = conv_response.get("Records", [])

                    if chat_records:
                        st.write("### Past Conversations")
                        for c in chat_records:
                            chat_id = c["chat_id"]
                            chat_label = f"Chat {chat_id} ({c['Created_at']})"
                            if st.button(chat_label, key=f"chat_{chat_id}"):
                                st.session_state.current_chat_id = chat_id
                                load_conversation(chat_id)
                                st.session_state.chat_view = 'details'
                                st.rerun()
                    else:
                        st.info("No past conversations for this agent.")

                elif st.session_state.chat_view == 'details':
                    # Show the conversation detail
                    st.button("← Back", on_click=back_to_list, key="back_chat")
                    if st.session_state.current_chat_id:
                        st.subheader(f"Conversation: {st.session_state.current_chat_id}")
                    else:
                        st.subheader("New Conversation")

                    # Display existing messages
                    for message in st.session_state.messages:
                        with st.chat_message(message["role"]):
                            st.markdown(message["content"])
                            if message.get("timestamp"):
                                st.caption(f"_{message['timestamp']}_")

                    # Chat input
                    prompt = st.chat_input("Type your message...")
                    if prompt:
                        # Add user message to local state
                        st.session_state.messages.append({
                            "role": "user",
                            "content": prompt,
                            "timestamp": datetime.now().isoformat()
                        })

                        payload = {
                            "agent_id": selected_agent,
                            "user_email": "user@example.com",  # or from user input
                            "incoming_steps": [
                                {
                                    "payload": {
                                        "step_type": "human_message",
                                        "content": prompt
                                    }
                                }
                            ]
                        }
                        if st.session_state.current_chat_id:
                            payload["chat_id"] = st.session_state.current_chat_id

                        response = make_request("POST", "/agents/chats/send", data=payload)

                        if "agent_response" in response:
                            # Put the initial list of agent responses in a variable
                            agent_responses = response["agent_response"]

                            # Loop until there are no more agent_responses left to process
                            while agent_responses:
                                new_agent_responses = []

                                # Process each response in this batch
                                for resp in agent_responses:
                                    # 1) If this response has plain text content, show it
                                    if resp.get("content", ""):
                                        st.session_state.messages.append({
                                            "role": "assistant",
                                            "content": resp.get("content", ""),
                                            "timestamp": datetime.now().isoformat()
                                        })

                                    # 2) Check for a tool call
                                    tool_call_id = resp.get("tool_call_id", "")
                                    tool_call_name = resp.get("tool_call_name", "")
                                    if tool_call_id:
                                        tool_payload = {
                                            "verb": resp.get("APIM_VERB", ""),
                                            "endpoint": resp.get("APIM_ENDPOINT", ""),
                                            "tool_call_id": tool_call_id,
                                            "tool_call_name": tool_call_name,
                                            "args": resp.get("args", ""),
                                            "function_registry_id": resp.get("Function_registry_id", "")
                                        }
                                        
                                        # Execute the tool call (in your example, we mock a response)
                                        tool_response = make_request("POST", "/tools/execute", data=tool_payload)
                                        # tool_response = ["confluence"]  # placeholder or real response

                                        # Send the tool result back to the conversation
                                        send_tool_resp_payload = {
                                            "agent_id": selected_agent,
                                            "chat_id": st.session_state.current_chat_id,
                                            "user_email": "user@example.com",
                                            "incoming_steps": [
                                                {
                                                    "payload": {
                                                        "step_type": "tool_execution_response",
                                                        "tool_call_id": f"{tool_call_id}",
                                                        "content": f"{tool_response}"
                                                    }
                                                }
                                            ]
                                        }
                                        followup_response = make_request("POST", "/agents/chats/send", data=send_tool_resp_payload)

                                        # Locally display that the function was called
                                        st.session_state.messages.append({
                                            "role": "assistant",
                                            "content": f"`Executed function - {tool_call_name}`",
                                            "timestamp": datetime.now().isoformat()
                                        })

                                        # 3) The follow-up may include further agent_responses (tool calls, text, etc.)
                                        #    Collect them to process on the next iteration
                                        if "agent_response" in followup_response:
                                            new_agent_responses.extend(followup_response["agent_response"])

                                # Update agent_responses with all new ones discovered on this pass
                                agent_responses = new_agent_responses

                        # If new chat, store chat ID
                        if "chat_id" in response and not st.session_state.current_chat_id:
                            st.session_state.current_chat_id = response["chat_id"]

                        st.rerun()

    ############################################################
    # Tab 3 - Function Registries
    ############################################################
    with tab3:
        st.header("Function Registries")

        def load_function_registries():
            return make_request("GET", "/functions")

        def load_function_registry_swagger(function_registry_id):
            return requests.request(
                method="GET",
                url=f"{BASE_URL}/functions/swagger",
                headers={"API-Token": st.session_state.api_key},
                params={"function_registry_id": function_registry_id}
            )
        def load_registry_functions(registry_id):
            # new function to get function list
            return make_request("GET", "/functions/function-list", params={"function_registry_id": registry_id})

        def back_to_registry_list():
            st.session_state.function_registry_view = 'list'
            st.session_state.selected_function_registry_id = None

        # create function registry modal triggers
        def open_create_function_registry_modal():
            st.session_state.show_create_function_registry_modal = True

        def close_create_function_registry_modal():
            st.session_state.show_create_function_registry_modal = False

        if st.session_state.function_registry_view == 'list':
            st.subheader("List of Function Registries")
            st.info("View existing registries of API collections. To create your own, download the swagger and upload it here with an API token.")
            st.divider()

            registry_response = load_function_registries()
            registry_list = registry_response.get("function_registries", [])

            if not registry_list:
                st.info("No function registries found.")
            else:
                for registry in registry_list:
                    with st.container():
                        registry_id = registry.get("function_registry_id", "")
                        st.markdown(f"**Registry ID:** {registry_id}")
                        st.markdown(f"**Created at:** {registry.get('created_at', '')}")
                        st.markdown(f"**Updated at:** {registry.get('updated_at', '')}")
                        if st.button("View Details", key=f"view_{registry_id}"):
                            st.session_state.selected_function_registry_id = registry_id
                            st.session_state.function_registry_view = 'details'
                            st.rerun()
                        st.markdown("---")

            if st.button("Upsert Function Registry"):
                open_create_function_registry_modal()

            if st.session_state.show_create_function_registry_modal:
                st.write("---")
                st.subheader("Upsert Function Registry")
                with st.form("create_function_registry_form"):
                    new_registry_id = st.text_input("Enter Registry ID (unique). Provide an existing ID to update it.")
                    new_registry_api_token = st.text_input("Enter API Token", type="password")
                    swagger_file = st.file_uploader("Upload Swagger JSON", type=["json"])

                    submitted = st.form_submit_button("Create")
                    if submitted:
                        if not new_registry_id:
                            st.error("Registry ID is required")
                        elif not new_registry_api_token:
                            st.error("API Token is required")
                        elif not swagger_file:
                            st.error("Swagger file is required")
                        else:
                            try:
                                swagger_content = swagger_file.read().decode("utf-8")
                                upsert_data = {
                                    "function_registry_id": new_registry_id,
                                    "api_token": new_registry_api_token,
                                    "swagger": swagger_content
                                }
                                resp = make_request("POST", "/functions/upsert", data=upsert_data)
                                if "function_registry_id" in resp:
                                    st.success(f"Function Registry '{resp['function_registry_id']}' created successfully!")
                                    close_create_function_registry_modal()
                                    st.rerun()
                                else:
                                    st.error(f"Error creating function registry: {resp.get('message', 'Unknown error')}")
                            except Exception as e:
                                st.error(f"Error reading swagger file: {str(e)}")

                if st.button("Cancel", key="cancel_create"):
                    close_create_function_registry_modal()
                    st.rerun()

        elif st.session_state.function_registry_view == 'details':
            registry_id = st.session_state.selected_function_registry_id
            st.button("← Back", on_click=back_to_registry_list, key="back_registry")
            st.subheader(f"Function Registry Details: {registry_id}") 

            # Display a download link for swagger
            if registry_id:
                swagger_response = load_function_registry_swagger(registry_id)
                if swagger_response.ok:
                    try:
                        # It's possible the swagger is a raw JSON
                        swagger_text = swagger_response.text
                        # Provide a download button
                        b64 = base64.b64encode(swagger_text.encode()).decode()
                        href = f'<a href="data:application/json;base64,{b64}" download="{registry_id}_swagger.json">Download Swagger</a>'
                        st.markdown(href, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Error processing swagger: {str(e)}")
                else:
                    st.warning("Unable to load swagger for this registry.")

                function_list_resp = load_registry_functions(registry_id)
                if "chat_functions" in function_list_resp:
                    st.write("### Functions in this registry")
                    for fn_obj in function_list_resp["chat_functions"]:
                        fn_data = fn_obj.get("chat_function", {})
                        with st.expander(f"{fn_data.get('name', 'Unknown')} (ID: {fn_data.get('id', '')})"):
                            st.write(f"**Description**: {fn_data.get('description', '')}")
                            imd = fn_data.get('internal_metadata', {})
                            st.write("**HTTP Verb**:", imd.get('verb', ''))
                            st.write("**Endpoint**:", imd.get('apim_endpoint', ''))
                            st.write("**Input Schema**:")
                            st.json(fn_data.get('input_schema', {}))
                            st.write("**Output Schema**:")
                            st.json(fn_data.get('output_schema', {}))
                else:
                    st.info("No functions found in this registry.")

            st.info("API token is not shown. Go to Workato AHQ Product if you want to see that.")
    ############################################################
    # Tab 4 - Knowledge Bases
    ############################################################
    with tab4:
        st.header("Knowledge Base Management")

        with st.expander("Create Knowledge Base"):
            with st.form("create_kb"):
                kb_id = st.text_input("KB ID")
                name = st.text_input("Name")
                description = st.text_area("Description")
                create_submitted = st.form_submit_button("Create")

                if create_submitted:
                    response = make_request(
                        "PUT",
                        "/knowledge",
                        data={
                            "data": {
                                "knowledge_base_id": kb_id,
                                "name": name,
                                "description": description
                            }
                        }
                    )
                    if not response.get("error"):
                        st.success("KB created!")
                        st.rerun()
                    else:
                        st.error(response.get("error", "Unknown error"))

        with st.expander("Upload Document"):
            kbs_data = make_request("GET", "/knowledge")
            kb_options_map = {kb["knowledge_base_id"]: kb["name"] for kb in kbs_data.get("knowledge_bases", [])}

            selected_kb_id = st.selectbox(
                "Select KB",
                options=list(kb_options_map.keys()),
                format_func=lambda x: kb_options_map[x] if x in kb_options_map else "Unknown"
            )

            existing_docs = []  # placeholder

            uploaded_file = st.file_uploader(
                "Upload ZIP File",
                type=["zip"],
                accept_multiple_files=False,
                help="ZIP filename will be used as document ID (special characters converted to underscores)"
            )

            custom_id = st.text_input("Custom Document ID (optional)",
                                      help="Override auto-generated ID from filename")

            if st.button("📤 Upload ZIP") and uploaded_file is not None:
                try:
                    if custom_id:
                        document_id = custom_id
                    else:
                        raw_id = os.path.splitext(uploaded_file.name)[0]
                        document_id = re.sub(r"[^a-zA-Z0-9_-]", "_", raw_id).strip("_")
                        if not document_id:
                            document_id = f"doc_{int(time.time())}"

                    suffix = 1
                    original_id = document_id
                    while any(d.get("document_id") == document_id for d in existing_docs):
                        document_id = f"{original_id}_{suffix}"
                        suffix += 1

                    zip_bytes = uploaded_file.getvalue()
                    encoded_zip = base64.b64encode(zip_bytes).decode("utf-8")

                    resp = make_request(
                        "PUT",
                        "/knowledge/document",
                        data={
                            "document_id": document_id,
                            "knowledge_base_id": selected_kb_id,
                            "document": encoded_zip
                        }
                    )

                    if not resp.get("error"):
                        st.success(f"""
                            **Upload successful!**  
                            📁 File: {uploaded_file.name}  
                            🏷️ Document ID: `{document_id}`
                        """)
                        st.balloons()
                    else:
                        st.error(f"Upload failed: {resp.get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error processing ZIP file: {str(e)}")

        with st.expander("View Knowledge Bases"):
            kbs_view_data = make_request("GET", "/knowledge")
            if kbs_view_data.get("knowledge_bases"):
                for kb in kbs_view_data["knowledge_bases"]:
                    st.write(f"**{kb['name']}** ({kb['knowledge_base_id']})")
                    st.write(kb.get("description", ""))
                    st.markdown("---")

    ############################################################
    # Tab 5 - Search
    ###########################################################
    with tab5:
        st.header("Knowledge Search")

        kb_all_data = make_request("GET", "/knowledge")
        kb_ids = [kb["knowledge_base_id"] for kb in kb_all_data.get("knowledge_bases", [])]

        search_type = st.radio("Search Type", ["Semantic", "Exact", "Q&A"], horizontal=True)
        selected_kbs_for_search = st.multiselect("Select Knowledge Bases", options=kb_ids, default=kb_ids)

        if search_type == "Semantic":
            query = st.text_input("Search Query")
            num_results = st.number_input("Number of Results", value=3)
            if st.button("Search"):
                response = make_request(
                    "POST",
                    "/knowledge/documents/semantic",
                    data={
                        "query": query,
                        "knowledge_base_ids_to_query": selected_kbs_for_search,
                        "number_of_chunks_to_retrieve": num_results
                    }
                )
                for chunk in response.get("retrieved_chunks", []):
                    st.write(f"**KB:** {chunk['knowledge_base_id']}")
                    st.write(chunk.get("content", ""))

        elif search_type == "Exact":
            text = st.text_input("Exact Text")
            num_results = st.number_input("Number of Results", value=3)
            if st.button("Search"):
                response = make_request(
                    "POST",
                    "/knowledge/documents/exact",
                    data={
                        "text": text,
                        "knowledge_base_ids_to_query": selected_kbs_for_search,
                        "num_of_chunks_to_retrieve": num_results
                    }
                )
                for chunk in response.get("retrieved_chunks", []):
                    st.write(f"**KB:** {chunk['knowledge_base_id']}")
                    st.write(chunk.get("content", ""))

        else:  # Q&A
            question = st.text_input("Question")
            if st.button("Ask"):
                response = make_request(
                    "POST",
                    "/knowledge/documents/ask",
                    data={
                        "knowledge_base_ids_reto_query": selected_kbs_for_search,
                        "question": question
                    }
                )
                st.write(f"**Answer:** {response.get('answer', 'No answer found')}")

    st.markdown("---")
    st.caption("Workato Copilot Playground | Created with Streamlit and Deepseek :-) ")
