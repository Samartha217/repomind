from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY, LLM_MODEL


class QueryReformulator:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=OPENAI_API_KEY,
            temperature=0
        )
    
    def reformulate(self, query: str, chat_history: list[dict]) -> str:
        """Reformulate query using chat history for context."""
        
        # If no history, return query as-is
        if not chat_history:
            return query
        
        # Build history string
        history_str = ""
        for msg in chat_history[-6:]:  # Last 6 messages
            role = msg["role"]
            content = msg["content"][:500]  # Truncate long messages
            history_str += f"{role}: {content}\n"
        
        prompt = f"""Given the conversation history and a follow-up question, reformulate the question to be standalone.
The reformulated question should include all necessary context from the history.

Chat History:
{history_str}

Follow-up Question: {query}

Reformulated Question (standalone, no explanation):"""

        response = self.llm.invoke(prompt)
        reformulated = response.content.strip()
        
        return reformulated