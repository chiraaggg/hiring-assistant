from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from .groq_llm import GroqLLM
from .tools import ALL_TOOLS

# Create the LLM
llm = GroqLLM()

# Memory (optional but recommended)
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Create the agent
agent = initialize_agent(
    tools=ALL_TOOLS,
    llm=llm,
    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
    verbose=True,
    memory=memory,
)

# PUBLIC FUNCTION CALLED BY FASTAPI
async def run_agent(query: str):
    """Run a user query through the agent and return the text output."""
    result = await agent.arun(query)
    return result
