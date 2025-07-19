from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import asyncio
import openai
import anthropic
import google.generativeai as genai
from .config import settings


class AIResponse(BaseModel):
    content: str
    model: str
    provider: str
    usage: Optional[Dict[str, Any]] = None


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        pass


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str):
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            default_headers={"OpenAI-Beta": "assistants=v2"}
        )
        self.assistant_id = "asst_gdVxdkcSfEE1I7bpkXChUUuY"  # BI assistant with vector store
        self.user_threads: Dict[str, str] = {}  # Store thread_id per user session
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            return AIResponse(
                content=response.choices[0].message.content,
                model=model,
                provider="openai",
                usage=response.usage.dict() if response.usage else None
            )
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def generate_response_with_assistant(
        self,
        user_message: str,
        user_id: str = "default_user",
        **kwargs
    ) -> AIResponse:
        """Generate response using the assistants API with thread management and domain restriction"""
        try:
            # Add domain restriction to ensure only Worker Operations BI questions
            domain_check = self._check_domain_relevance(user_message)
            if not domain_check["is_relevant"]:
                return AIResponse(
                    content=f"I'm specifically designed to help with Worker Operations Business Intelligence questions. {domain_check['suggestion']}",
                    model="domain-filter",
                    provider="openai",
                    usage={"filtered": True}
                )
            
            # Get or create thread for this user
            thread_id = await self.get_or_create_thread(user_id)
            
            # Add domain-aware context to user message
            from datetime import datetime
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_year = datetime.now().year
            current_month = datetime.now().strftime("%B")
            
            enhanced_message = f"""CONTEXT: This is a Worker Operations Business Intelligence query.

CURRENT DATE: {current_date} (Today's date is {current_date}, current year is {current_year}, current month is {current_month})

USER QUERY: {user_message}

INSTRUCTIONS: Only provide responses related to Worker Operations data analysis, SQL queries for the available tables, and business insights. Do not assist with general coding, unrelated topics, or non-BI requests. When the user mentions time periods like "this month", "this year", or "recent", use the current date context provided above."""
            
            # Add user message to thread
            await self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=enhanced_message,
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            
            # Create and run the assistant
            run = await self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            
            # Wait for completion with timeout
            timeout_seconds = 45  # 45 second timeout - more reasonable
            start_time = asyncio.get_event_loop().time()
            
            while run.status in ["queued", "in_progress", "cancelling"]:
                current_time = asyncio.get_event_loop().time()
                if current_time - start_time > timeout_seconds:
                    raise Exception(f"Assistant run timed out after {timeout_seconds} seconds")
                
                await asyncio.sleep(1)  # Check every 1 second
                run = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id,
                    extra_headers={"OpenAI-Beta": "assistants=v2"}
                )
            
            if run.status == "completed":
                # Get the assistant's response
                messages = await self.client.beta.threads.messages.list(
                    thread_id=thread_id,
                    order="desc",
                    limit=1,
                    extra_headers={"OpenAI-Beta": "assistants=v2"}
                )
                
                assistant_message = messages.data[0]
                # Handle different content formats in v2 API
                if hasattr(assistant_message.content[0], 'text'):
                    if hasattr(assistant_message.content[0].text, 'value'):
                        content = assistant_message.content[0].text.value
                    else:
                        content = assistant_message.content[0].text
                else:
                    content = str(assistant_message.content[0])
                
                return AIResponse(
                    content=content,
                    model="gpt-4-turbo",  # Assistants API uses gpt-4-turbo
                    provider="openai",
                    usage={"thread_id": thread_id}
                )
            else:
                raise Exception(f"Assistant run failed with status: {run.status}")
                
        except Exception as e:
            raise Exception(f"OpenAI Assistant API error: {str(e)}")
    
    def _check_domain_relevance(self, user_message: str) -> Dict[str, Any]:
        """Check if the user message is relevant to Worker Operations BI - smart filtering"""
        message_lower = user_message.lower().strip()
        
        # Always allow basic conversational inputs
        basic_greetings = [
            'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
            'thanks', 'thank you', 'bye', 'goodbye', 'ok', 'okay', 'yes', 'no'
        ]
        
        if any(greeting in message_lower for greeting in basic_greetings):
            return {"is_relevant": True, "suggestion": ""}
        
        # Allow short messages (likely conversational)
        if len(message_lower.split()) <= 3:
            return {"is_relevant": True, "suggestion": ""}
        
        # Explicitly block only obvious non-BI requests
        forbidden_patterns = [
            'write a function', 'create a script', 'python code', 'javascript code',
            'programming', 'machine learning', 'ai model', 'deep learning',
            'recipe', 'cooking', 'weather', 'news', 'movie', 'book', 'travel',
            'health advice', 'medical advice', 'legal advice', 'personal advice',
            'relationship', 'entertainment', 'game', 'sport', 'politics',
            'write me a', 'create me a', 'build me a', 'develop a'
        ]
        
        # Only block if it clearly matches forbidden patterns
        for pattern in forbidden_patterns:
            if pattern in message_lower:
                return {
                    "is_relevant": False,
                    "suggestion": "I'm specifically designed for Worker Operations Business Intelligence. Please ask me about agent performance, productivity metrics, scheduling adherence, or other operational data analysis questions."
                }
        
        # Check for BI-related keywords (more comprehensive)
        bi_keywords = [
            'agent', 'agents', 'performance', 'productivity', 'adherence', 'schedule', 'supervisor',
            'ticket', 'tickets', 'metric', 'metrics', 'report', 'analysis', 'data', 'query', 'database',
            'trend', 'trends', 'insight', 'dashboard', 'chart', 'statistics', 'count',
            'average', 'total', 'sum', 'percentage', 'rate', 'efficiency', 'operations',
            'worker', 'workers', 'employee', 'employees', 'staff', 'team', 'teams', 'manager', 
            'aht', 'csat', 'qa', 'quality', 'score', 'rating', 'review', 'weekly', 'monthly',
            'top', 'bottom', 'best', 'worst', 'highest', 'lowest', 'compare', 'comparison',
            'how many', 'show me', 'list', 'find', 'who', 'what', 'where', 'when', 'which',
            'kim', 'table', 'column', 'row', 'field'
        ]
        
        # If it contains BI keywords, definitely allow
        if any(keyword in message_lower for keyword in bi_keywords):
            return {"is_relevant": True, "suggestion": ""}
        
        # For everything else that doesn't match forbidden patterns, allow it
        # This ensures we're permissive rather than restrictive
        return {"is_relevant": True, "suggestion": ""}
    
    async def get_or_create_thread(self, user_id: str) -> str:
        """Get existing thread or create a new one for the user"""
        if user_id not in self.user_threads:
            thread = await self.client.beta.threads.create(
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            self.user_threads[user_id] = thread.id
        return self.user_threads[user_id]
    
    def get_available_models(self) -> List[str]:
        return ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-3-sonnet-20240229",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        try:
            # Convert messages format for Claude
            claude_messages = []
            system_message = None
            
            for message in messages:
                if message["role"] == "system":
                    system_message = message["content"]
                else:
                    claude_messages.append({
                        "role": message["role"],
                        "content": message["content"]
                    })
            
            response = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_message,
                messages=claude_messages,
                **kwargs
            )
            
            return AIResponse(
                content=response.content[0].text,
                model=model,
                provider="anthropic",
                usage=response.usage.dict() if response.usage else None
            )
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")
    
    def get_available_models(self) -> List[str]:
        return ["claude-3-sonnet-20240229", "claude-3-haiku-20240307", "claude-3-opus-20240229"]


class GoogleProvider(AIProvider):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.client = genai
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str = "gemini-pro",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        try:
            model_instance = genai.GenerativeModel(model)
            
            # Convert messages to Gemini format
            conversation = []
            for message in messages:
                if message["role"] == "user":
                    conversation.append(message["content"])
                elif message["role"] == "assistant":
                    conversation.append(message["content"])
            
            prompt = "\n".join(conversation)
            
            response = await model_instance.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            )
            
            return AIResponse(
                content=response.text,
                model=model,
                provider="google",
                usage={"prompt_tokens": 0, "completion_tokens": 0}  # Gemini doesn't provide usage info
            )
        except Exception as e:
            raise Exception(f"Google API error: {str(e)}")
    
    def get_available_models(self) -> List[str]:
        return ["gemini-pro", "gemini-pro-vision"]


class AIProviderManager:
    def __init__(self):
        self.providers: Dict[str, AIProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        if settings.openai_api_key:
            self.providers["openai"] = OpenAIProvider(settings.openai_api_key)
        
        if settings.anthropic_api_key:
            self.providers["anthropic"] = AnthropicProvider(settings.anthropic_api_key)
        
        if settings.google_api_key:
            self.providers["google"] = GoogleProvider(settings.google_api_key)
    
    def get_provider(self, provider_name: str) -> AIProvider:
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not available or not configured")
        return self.providers[provider_name]
    
    def get_available_providers(self) -> List[str]:
        return list(self.providers.keys())
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        provider: str = None,
        model: str = None,
        **kwargs
    ) -> AIResponse:
        if provider is None:
            provider = settings.default_ai_provider
        
        ai_provider = self.get_provider(provider)
        
        if model is None:
            model = ai_provider.get_available_models()[0]
        
        return await ai_provider.generate_response(messages, model, **kwargs)
    
    async def generate_response_with_assistant(
        self,
        user_message: str,
        user_id: str = "default_user",
        provider: str = "openai",
        **kwargs
    ) -> AIResponse:
        """Generate response using the assistants API"""
        ai_provider = self.get_provider(provider)
        
        if isinstance(ai_provider, OpenAIProvider):
            return await ai_provider.generate_response_with_assistant(user_message, user_id, **kwargs)
        else:
            raise ValueError(f"Assistants API not supported by provider: {provider}")


# Global instance
ai_manager = AIProviderManager()