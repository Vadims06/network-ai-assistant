# Copyright (c) 2025 Vadim Semenov

import logging
from openai import OpenAI
import os
import streamlit as st
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain.memory.buffer import ConversationBufferMemory
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

ospf_isis_mcp_url = os.getenv("OSPF_ISIS_MCP_URL", "")
topolograph_api_key = os.getenv("TOPOLOGRAPH_API_KEY", "")
model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")

client = OpenAI()


def call_mcp_server(ospf_isis_mcp_url, input_text):
    """Calls the MCP server with the given URL and input."""
    try:
        headers = {}
        if topolograph_api_key:
            headers["Authorization"] = f"Bearer {topolograph_api_key}"
            headers["Accept"] = "application/json, text/event-stream"
            headers["Content-Type"] = "application/json"
        st.info(f"Processing request...")
        response = client.responses.create(
            model=model_name,
            tools=[
                {
                    "type": "mcp",
                    "server_label": "OSPF_ISIS_Analyser",
                    "server_url": f"{ospf_isis_mcp_url}/mcp",
                    "require_approval": "never",
                    "headers": headers,
                },
            ],
            input=input_text,
        )
        logging.debug(f"Response: {response.output_text}")
        logging.debug(f"Input tokens: {response.usage.input_tokens}")
        logging.debug(f"Output tokens: {response.usage.output_tokens}")
        logging.debug(f"Total tokens: {response.usage.total_tokens}")
        return response.output_text
    except Exception as e:
        logging.exception(f"An error occurred: {e}")
        return f"An error occurred: {e}"

def build_prompt_from_memory(memory, system_prompt: str, current_input: str) -> str:
    """
    Builds the agent prompt from conversation memory and current input.
    """
    # get conversation history from memory
    chat_history = memory.chat_memory.messages
    
    lines = [f"[System Prompt]: {system_prompt}"]
    
    # add conversation history
    for msg in chat_history:
        if isinstance(msg, HumanMessage):
            lines.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            lines.append(f"Assistant: {msg.content}")
    
    # add current user message
    lines.append(f"User: {current_input}")
    
    return "\n".join(lines)

def ospf_isis_mcp_main():
    """Tests the MCP server with memory support."""
    st.title("OSPF/IS-IS Network AI Assistant")


    system_prompt = (
        "You are a highly skilled network engineer and an expert in OSPFv2 (RFC 2328) and IS-IS (RFC 1195 / RFC 3784).\n"
        "GENERAL RULES:\n"
        "- If a request mentions OSPF or IS-IS, or asks for network status or characteristics, always use the available MCP tools.\n"
        "- Do not invent information. Use only data returned from the database or MCP tools.\n"
        "* Graph Working Principles:\n"
        "- Topolograph stores snapshots of the network as graphs.\n"
        "- If a user asks about “networks” in a general way for the first time (e.g. “what networks are connected to you?”), interpret this as referring to graphs (snapshots) in Topolograph.\n"
        "- Interpret “network” literally (as subnets or node-terminated networks) when the user explicitly asks about subnets/networks in the graph/protocol/area or connected to a node and use the tool for listing networks\n"
        "- To answer any question about network state, first identify the most relevant snapshot/graph. Use MCP tools to search and filter snapshots.\n"
        "- If no graph name, nor protocol, nor area is specified, query all snapshots for all protocols.\n"
        "- If multiple protocols or areas exist and the user does not specify, ask the user to clarify which protocol or area to use.\n"
        "- In case of multiple adjacency events, print single up/down events first."
        "- Always use the 'graph_time' exactly as returned by MCP. Never modify or reinterpret it.\n"
        "* Answer Formatting Instructions:\n"
        "- Do not wrap the tool output in Markdown code blocks or add explanatory text.\n"
        "- Add maximum 1 sentence commentary outside of the required output as a last sentence in the answer.\n"
        "- If you output less data than the tool output, indicate how much is left and not included in the answer.\n"
        "- Add filters,used arguments in the latest request to MCP at the end of the answer as a string splitted by commas.\n"
        "- Sort graphs by 'graph_time' in ascending order.\n"
        "- Always include the graph parameters at the beginning of the answer: protocol, area, and snapshot creation time.\n"
        "- Do not include x,y coordinates in the answer.\n"
        "- Use verbose output.\n"
        "* Output Strategy:\n"
        "- Mark in bold fields in the output that are returned by the tool.\n"
        "- Format Results for the events only as a table.\n"
        "- Format graphs output as a bullet points with additional information about the graph inside the bullet point.\n"
        "- Reply in the language of the user's question."
    )

    # initialize memory
    if "memory" not in st.session_state:
        st.session_state.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            input_key="input"
        )
        # add system message to the memory
        st.session_state.memory.chat_memory.add_message(
            SystemMessage(content=system_prompt)
        )
    
    # initialize conversation history for display
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    # show conversation history
    for msg in st.session_state.messages:
        if isinstance(msg, HumanMessage):
            st.chat_message("user").write(msg.content)
        elif isinstance(msg, AIMessage):
            st.chat_message("assistant").write(msg.content)


    if prompt := st.chat_input("Enter your question..."):

        # add user message to the memory
        user_msg = HumanMessage(content=prompt)
        st.session_state.memory.chat_memory.add_message(user_msg)
        
        # add user message to the conversation history
        st.session_state.messages.append(user_msg)
        
        print(f"\n\n==> user_msg:\n{user_msg}")
        print(f"\n\n==> prompt:\n{prompt}")
        
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            # build prompt with memory
            full_prompt = build_prompt_from_memory(
                memory=st.session_state.memory,
                system_prompt=system_prompt,
                current_input=prompt
            )
            print(f"\n\n==> full prompt:\n{full_prompt}")
            
            # call MCP server
            output_text = call_mcp_server(ospf_isis_mcp_url, full_prompt)
            
            # add answer to the memory
            ai_msg = AIMessage(content=output_text)
            st.session_state.memory.chat_memory.add_message(ai_msg)
            
            # add answer to the conversation history
            st.session_state.messages.append(ai_msg)
            
            with st.chat_message("assistant"):
                st.markdown(output_text)
                
        except Exception as e:
            error_msg = f"An error occurred: {e}"
            st.chat_message("assistant").write(error_msg)
            
            # add error message to the memory
            error_ai_msg = AIMessage(content=error_msg)
            st.session_state.memory.chat_memory.add_message(error_ai_msg)
            st.session_state.messages.append(error_ai_msg)
    
    # add button to clear the conversation history
    if st.button("Clear conversation history"):
        st.session_state.memory.clear()
        st.rerun()