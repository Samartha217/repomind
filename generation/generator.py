from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY, LLM_MODEL
from retrieval.context_builder import build_context, build_sources_list


class Generator:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=OPENAI_API_KEY,
            temperature=0.1
        )
        
        self.system_prompt = """You are a helpful code assistant that answers questions about a codebase.

Rules:
1. Answer based ONLY on the provided code context
2. Always reference specific files and line numbers when explaining
3. If the context doesn't contain enough information, say so
4. Be concise but thorough
5. Use code snippets from the context when helpful
6. Format file references as: `filename.py` (lines X-Y)"""

    def generate(self, query: str, chunks: list[dict], chat_history: list[dict] = None) -> dict:
        """Generate response using retrieved context."""
        
        # Build context from chunks
        context = build_context(chunks)
        sources = build_sources_list(chunks)
        
        # Build messages
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add chat history if exists
        if chat_history:
            for msg in chat_history[-6:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Add current query with context
        user_message = f"""Context from codebase:
{context}

Question: {query}

Answer based on the code context above:"""
        
        messages.append({"role": "user", "content": user_message})
        
        # Generate response
        response = self.llm.invoke(messages)
        
        return {
            "answer": response.content,
            "sources": sources
        }