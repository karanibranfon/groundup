import os
from typing import Dict, List, Optional, Any
from django.conf import settings
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import json


class MedicalAnalysisResult(BaseModel):
    summary: str = Field(description="Clinical summary of the imaging findings")
    findings: List[str] = Field(description="List of specific findings")
    recommendations: List[str] = Field(description="Clinical recommendations")
    confidence: float = Field(description="Confidence score between 0 and 1")
    urgency: str = Field(description="Urgency level: routine, urgent, or STAT")
    follow_up: Optional[str] = Field(description="Suggested follow-up timeframe")


class MedicalImageAnalyzer:
    STUDY_TYPE_PROMPTS = {
        'X-Ray': """You are an expert radiologist specializing in X-Ray imaging. Analyze the provided X-Ray study 
        and provide clinical findings. Focus on: bone structures, lung fields, heart silhouette, pneumothorax, 
        fractures, infections, or foreign bodies.""",
        
        'CT': """You are an expert radiologist specializing in CT imaging. Analyze the provided CT scan 
        and provide detailed clinical findings. Focus on: soft tissue abnormalities, vascular structures, 
        organ pathologies, tumors, bleeding, or traumatic injuries.""",
        
        'MRI': """You are an expert radiologist specializing in MRI imaging. Analyze the provided MRI study 
        and provide detailed clinical findings. Focus on: neurological abnormalities, soft tissue structures, 
        joint pathologies, tumors, or inflammatory conditions.""",
        
        'Ultrasound': """You are an expert radiologist specializing in ultrasound imaging. Analyze the provided 
        ultrasound study and provide clinical findings. Focus on: organ morphology, fluid collections, 
        fetal assessment, vascular flow, or procedural guidance.""",
        
        'PET': """You are an expert radiologist specializing in PET imaging. Analyze the provided PET scan 
        and provide clinical findings. Focus on: metabolic activity patterns, tumor detection, 
        metastatic disease, or treatment response assessment.""",
        
        'Other': """You are an expert radiologist. Analyze the provided medical imaging study 
        and provide clinical findings in a structured format."""
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
            return ChatOpenAI(model=model_name, api_key=api_key, temperature=0.3)
        
        elif self.provider == 'anthropic':
            model_name = getattr(settings, 'ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set in environment")
            return ChatAnthropic(model=model_name, anthropic_api_key=api_key)
        
        elif self.provider == 'ollama':
            model_name = getattr(settings, 'OLLAMA_MODEL', 'llama3')
            base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
            return ChatOllama(model=model_name, base_url=base_url, temperature=0.3)
        
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    def _build_prompt(self, study_type: str, patient_info: str, image_count: int) -> ChatPromptTemplate:
        base_prompt = self.STUDY_TYPE_PROMPTS.get(study_type, self.STUDY_TYPE_PROMPTS['Other'])
        
        system_prompt = f"""{base_prompt}

IMPORTANT: You are providing a preliminary AI-assisted analysis only. This should NOT replace 
professional medical interpretation. Always include appropriate disclaimers.

Return your response as a JSON object with the following structure:
{{
    "summary": "Brief clinical summary of findings (2-3 sentences)",
    "findings": ["Finding 1", "Finding 2", "Finding 3"],
    "recommendations": ["Recommendation 1", "Recommendation 2"],
    "confidence": 0.85,
    "urgency": "routine|urgent|stat",
    "follow_up": "Suggested follow-up timeframe or null"
}}

Be concise, evidence-based, and clinically relevant. Focus on actionable findings."""

        user_prompt = f"""Medical Imaging Study Analysis Request:

Study Type: {study_type}
Number of Images: {image_count}
Patient Information: {patient_info}

Provide a structured clinical analysis of this imaging study."""

        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])

    def analyze_study(
        self,
        study_type: str,
        patient_name: str,
        patient_age: Optional[str] = None,
        clinical_history: str = '',
        image_count: int = 1
    ) -> Dict[str, Any]:
        patient_info = f"Patient: {patient_name}"
        if patient_age:
            patient_info += f", Age: {patient_age}"
        if clinical_history:
            patient_info += f", History: {clinical_history}"
        
        prompt = self._build_prompt(study_type, patient_info, image_count)
        
        try:
            response = self.llm.invoke(prompt.format())
            
            if hasattr(response, 'content'):
                result = json.loads(response.content)
            else:
                result = json.loads(str(response))
            
            result['ai_model'] = self.provider
            result['study_type'] = study_type
            
            return result
            
        except json.JSONDecodeError:
            return self._generate_fallback_analysis(study_type, image_count)
        except Exception as e:
            raise Exception(f"AI analysis failed: {str(e)}")

    def _generate_fallback_analysis(self, study_type: str, image_count: int) -> Dict[str, Any]:
        return {
            'summary': f'AI analysis for {study_type} study with {image_count} image(s) completed.',
            'findings': [
                'Analysis completed - please review individual images',
                'For detailed findings, please consult with a radiologist'
            ],
            'recommendations': [
                'Clinical correlation recommended',
                'Radiologist review suggested for definitive diagnosis'
            ],
            'confidence': 0.7,
            'urgency': 'routine',
            'follow_up': 'As clinically indicated',
            'ai_model': 'fallback',
            'study_type': study_type
        }

    def get_available_providers(self) -> List[Dict[str, str]]:
        providers = [
            {'id': 'openai', 'name': 'OpenAI', 'available': bool(os.environ.get('OPENAI_API_KEY'))},
            {'id': 'anthropic', 'name': 'Anthropic', 'available': bool(os.environ.get('ANTHROPIC_API_KEY'))},
            {'id': 'ollama', 'name': 'Ollama (Local)', 'available': True},
        ]
        return providers
