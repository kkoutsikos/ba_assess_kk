# section-2/agent.py

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_ollama import ChatOllama
from tools import agent_tools

class State(TypedDict):
    messages: Annotated[list, add_messages]

print("[INFO] Initializing Agent with Llama 3.1...")
llm = ChatOllama(model="llama3.1", temperature=0)
llm_with_tools = llm.bind_tools(agent_tools)

def chatbot_node(state: State):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot_node)
graph_builder.add_node("tools", ToolNode(tools=agent_tools))

graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")

app = graph_builder.compile()

if __name__ == "__main__":
    print("\n" + "="*50)
    print("      INVOICE AI AGENT READY")
    print("      Type 'exit' to quit.")
    print("="*50)
    
    # We maintain the thread state so the agent remembers the conversation context
    config = {"configurable": {"thread_id": "1"}}
    
    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Exiting agent...")
                break
            if not user_input.strip():
                continue
            
            # Stream the events to show the tool calls in real-time
            events = app.stream(
                {"messages": [("user", user_input)]}, 
                config, 
                stream_mode="values"
            )
            
            # Capture the final message
            for event in events:
                last_message = event["messages"][-1]
            
            # Print the final LLM text response
            print(f"\nAgent: {last_message.content}")
            
        except KeyboardInterrupt:
            print("\nExiting agent...")
            break
        except Exception as e:
            print(f"\n[ERROR] An unexpected error occurred: {e}")