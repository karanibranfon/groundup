import os
import json
from typing import Dict, List, Optional, Any
from django.conf import settings
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field


class GeneratedBlogContent(BaseModel):
    title: str = Field(description="The title of the blog post")
    excerpt: str = Field(description="A brief summary of the blog post (2-3 sentences)")
    content: str = Field(description="The full blog post content in Markdown format")
    category: str = Field(description="The most appropriate category for this content")
    tags: List[str] = Field(description="List of 3-5 relevant tags for the post")
    keywords: List[str] = Field(description="List of SEO keywords for the post")


class HealthcareAIBlogWriter:
    LENGTH_CONFIG = {
        'short': {'min_words': 300, 'max_words': 500},
        'medium': {'min_words': 500, 'max_words': 1000},
        'long': {'min_words': 1000, 'max_words': 2000},
    }

    TONE_CONFIG = {
        'professional': 'professional and authoritative',
        'friendly': 'friendly and approachable',
        'educational': 'clear and educational',
        'empathetic': 'compassionate and understanding',
    }

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or getattr(settings, 'LLM_PROVIDER', 'openai')
        self.llm = self._initialize_llm()

    def _initialize_llm(self):
        if self.provider == 'openai':
            model_name = getattr(settings, 'OPENAI_MODEL', 'gpt-4o')
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in environment")
            return ChatOpenAI(model=model_name, api_key=api_key, temperature=0.7)
        
        elif self.provider == 'anthropic':
            model_name = getattr(settings, 'ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set in environment")
            return ChatAnthropic(model=model_name, anthropic_api_key=api_key)
        
        elif self.provider == 'ollama':
            model_name = getattr(settings, 'OLLAMA_MODEL', 'llama3')
            base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
            return ChatOllama(model=model_name, base_url=base_url, temperature=0.7)
        
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    def _build_prompt(self, topic: str, category: str, target_audience: str, tone: str, length: str) -> ChatPromptTemplate:
        length_config = self.LENGTH_CONFIG.get(length, self.LENGTH_CONFIG['medium'])
        tone_desc = self.TONE_CONFIG.get(tone, self.TONE_CONFIG['educational'])
        
        healthcare_categories = [
            'General Health', 'Disease Prevention', 'Treatment Options',
            'Wellness & Lifestyle', 'Mental Health', 'Nutrition',
            'Fitness & Exercise', 'Medical Technology', 'Healthcare Policy',
            'Patient Care', 'Emergency Medicine', 'Pediatrics',
            'Geriatrics', "Women's Health", "Men's Health"
        ]
        
        if category and category not in healthcare_categories:
            healthcare_categories.insert(0, category)
        
        system_prompt = f"""You are an expert healthcare content writer with deep medical knowledge and excellent communication skills. You write accurate, trustworthy, and accessible healthcare content.

Your content follows these guidelines:
- Accuracy: All medical information must be evidence-based and accurate
- Clarity: Use plain language that's accessible to general audiences
- Safety: Include appropriate disclaimers about consulting healthcare professionals
- Structure: Use clear headings, bullet points, and formatting for readability

Write blog content targeting {length_config['min_words']}-{length_config['max_words']} words in a {tone_desc} tone."""

        user_prompt = f"""Generate a comprehensive healthcare blog post about: {topic}

{"Target audience: " + target_audience if target_audience else ""}

Available categories (or use a new appropriate one):
{', '.join(healthcare_categories)}

Return your response as a JSON object with the following structure:
{{
    "title": "Engaging, SEO-friendly title",
    "excerpt": "2-3 sentence summary for the post preview",
    "content": "Full blog post in Markdown format with proper headings, lists, and structure",
    "category": "Most appropriate category from the list",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
}}

IMPORTANT: The content must be original, informative, and suitable for health-conscious readers.
Include relevant medical disclaimers where appropriate.
Use proper Markdown formatting with ## for main sections and ### for subsections."""

        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])

    def generate_blog_post(
        self,
        topic: str,
        category_name: str = '',
        target_audience: str = '',
        tone: str = 'educational',
        length: str = 'medium'
    ) -> Dict[str, Any]:
        prompt = self._build_prompt(topic, category_name, target_audience, tone, length)
        parser = JsonOutputParser(pydantic_schema=GeneratedBlogContent)
        
        chain = prompt | self.llm | parser
        
        try:
            result = chain.invoke({})
            result['ai_model'] = self.provider
            result['generation_params'] = {
                'topic': topic,
                'category': category_name,
                'target_audience': target_audience,
                'tone': tone,
                'length': length
            }
            return result
        except Exception as e:
            raise Exception(f"Failed to generate content: {str(e)}")

    def get_available_providers(self) -> List[Dict[str, str]]:
        providers = [
            {'id': 'openai', 'name': 'OpenAI', 'available': bool(os.environ.get('OPENAI_API_KEY'))},
            {'id': 'anthropic', 'name': 'Anthropic', 'available': bool(os.environ.get('ANTHROPIC_API_KEY'))},
            {'id': 'ollama', 'name': 'Ollama (Local)', 'available': True},
        ]
        return providers
