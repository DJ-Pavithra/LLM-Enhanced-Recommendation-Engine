import json
from openai import AsyncOpenAI
from app.core.config import settings

class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def analyze_query(self, query: str):
        """
        Convert natural language query into structured intent.
        Output: JSON { "category": str, "features": list, "budget": str, "intent": str, "use_case": str }
        """
        prompt = f"""
        Extract structured info from this e-commerce search query: "{query}"
        Return strictly JSON with keys: 
        - category (str)
        - features (list of strings)
        - budget (str or null)
        - intent (informational/transactional/gift)
        - use_case (str, e.g. "gaming", "programming", "running")
        
        If specific fields aren't mentioned, infer them if possible or use null.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a shopping assistant api. Respond in JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"LLM Error: {e}")
            return {"category": "general", "features": [], "budget": None, "intent": "general", "use_case": None}

    async def explain_recommendation(self, user_profile: str, item_name: str, score: float):
        """
        Generate structured explanation.
        Output: JSON { "reason": str, "match_factors": list }
        """
        prompt = f"""
        User Profile: {user_profile}
        Item: {item_name}
        Relevance: {score:.2f}
        
        Why is this recommended? Return JSON:
        {{
            "reason": "1 short sentence explaining the match based on user history/preferences.",
            "match_factors": ["List", "3", "Key", "Factors", "e.g. Brand Affinity", "Price Match"]
        }}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful recommender system. Respond in JSON only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"reason": "Recommended based on your browsing history.", "match_factors": ["Similar Items"]}

    async def analyze_user_profile(self, history_summary: str):
        """
        Generate profile persona from transaction history.
        Output: JSON { "persona": str, "price_sensitivity": str, "best_time": str }
        """
        prompt = f"""
        Analyze this user based on their purchase history:
        {history_summary}
        
        Return JSON:
        {{
            "persona": "Short description (e.g. Tech-savvy buyer)",
            "price_sensitivity": "Low/Moderate/High",
            "best_time": "Best time to recommend (e.g. Weekends)"
        }}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a data analyst. Respond in JSON only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.5
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"persona": "Valued Customer", "price_sensitivity": "Unknown", "best_time": "Anytime"}

    async def generate_cold_start_questions(self):
        """Generate 3 clarifying questions for a new user."""
        return [
            "What type of products are you looking for today?",
            "Do you have a specific budget in mind?",
            "Are you shopping for yourself or for a gift?"
        ]

llm_service = LLMService()
