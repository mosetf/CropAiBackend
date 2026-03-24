"""
CropAdvisorRAG - Fine-tuned Qwen3.5 with RAG for agricultural recommendations
"""

import os
import pickle
import torch
import faiss
import numpy as np
from typing import Dict, List, Any
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from sentence_transformers import SentenceTransformer


class CropAdvisorRAG:
    def __init__(self, model_path: str = None, rag_data_path: str = None):
        """
        Initialize the RAG-enabled crop advisor.
        
        Args:
            model_path: Path to the fine-tuned LoRA adapter
            rag_data_path: Path to RAG data files (FAISS index, documents, embedder)
        """
        self.model_path = model_path
        self.rag_data_path = rag_data_path or os.path.join(os.path.dirname(__file__), "..", "..", "rag_data")
        
        self.model = None
        self.tokenizer = None
        self.embedder = None
        self.faiss_index = None
        self.documents = None
        
        self._load_model()
        self._load_rag_components()
    
    def _load_model(self):
        """Load the fine-tuned Qwen model with LoRA adapters."""
        try:
            # Load base model
            base_model = AutoModelForCausalLM.from_pretrained(
                "Qwen/Qwen2.5-0.5B-Instruct",
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True
            )
            
            # Load LoRA adapter if path provided
            if self.model_path and os.path.exists(self.model_path):
                self.model = PeftModel.from_pretrained(base_model, self.model_path)
                print(f"✓ Loaded fine-tuned model from {self.model_path}")
            else:
                self.model = base_model
                print("⚠ Using base model (no fine-tuned adapter found)")
            
            # Load tokenizer
            tokenizer_path = self.model_path if self.model_path and os.path.exists(self.model_path) else "Qwen/Qwen2.5-0.5B-Instruct"
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, trust_remote_code=True)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
        except Exception as e:
            print(f"Error loading model: {e}")
            # Fallback to basic mode without model
            self.model = None
            self.tokenizer = None
    
    def _load_rag_components(self):
        """Load RAG components: embedder, FAISS index, and documents."""
        try:
            # Load embedder name
            embedder_path = os.path.join(self.rag_data_path, "rag_embedder_name.txt")
            if os.path.exists(embedder_path):
                with open(embedder_path, 'r') as f:
                    embedder_name = f.read().strip()
                self.embedder = SentenceTransformer(embedder_name)
                print(f"✓ Loaded embedder: {embedder_name}")
            
            # Load FAISS index
            index_path = os.path.join(self.rag_data_path, "rag_index.faiss")
            if os.path.exists(index_path):
                self.faiss_index = faiss.read_index(index_path)
                print(f"✓ Loaded FAISS index with {self.faiss_index.ntotal} documents")
            
            # Load documents
            docs_path = os.path.join(self.rag_data_path, "rag_docs.pkl")
            if os.path.exists(docs_path):
                with open(docs_path, 'rb') as f:
                    self.documents = pickle.load(f)
                print(f"✓ Loaded {len(self.documents)} documents")
                
        except Exception as e:
            print(f"Warning: RAG components not fully loaded: {e}")
            self.embedder = None
            self.faiss_index = None
            self.documents = []
    
    def _retrieve_relevant_docs(self, query: str, top_k: int = 2) -> List[str]:
        """Retrieve relevant documents for the query."""
        if not all([self.embedder, self.faiss_index, self.documents]):
            return []
        
        try:
            # Encode query
            query_embedding = self.embedder.encode([query])
            query_embedding = query_embedding.astype('float32')
            
            # Search FAISS index
            scores, indices = self.faiss_index.search(query_embedding, top_k)
            
            # Return relevant documents
            relevant_docs = []
            for idx in indices[0]:
                if 0 <= idx < len(self.documents):
                    relevant_docs.append(self.documents[idx])
            
            return relevant_docs
            
        except Exception as e:
            print(f"Error retrieving documents: {e}")
            return []
    
    def _generate_response(self, prompt: str, max_length: int = 512) -> str:
        """Generate response using the fine-tuned model."""
        if not self.model or not self.tokenizer:
            return self._fallback_response()
        
        try:
            # Tokenize input
            inputs = self.tokenizer.encode(prompt, return_tensors="pt")
            if inputs.shape[1] > 1800:  # Truncate if too long
                inputs = inputs[:, :1800]
            
            # Generate response
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_new_tokens=max_length,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
            return response.strip()
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return self._fallback_response()
    
    def _fallback_response(self) -> str:
        """Fallback response when model is not available."""
        return "Model temporarily unavailable. Please ensure proper soil preparation, adequate fertilization, and monitor weather conditions for optimal yield."
    
    def get_recommendations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get crop recommendations based on context.
        
        Args:
            context: Dictionary with crop, location, yield, weather, soil data
            
        Returns:
            Dictionary with recommendations, risk level, and reasoning
        """
        crop = context.get("crop", "maize")
        location = context.get("location", "")
        yield_pred = context.get("yield", 0)
        temp = context.get("temp", 20)
        rainfall = context.get("rainfall", 500)
        soil_ph = context.get("soil_ph", 6.5)
        fertilizer = context.get("fertilizer", 100)
        
        # Create query for RAG retrieval
        query = f"{crop} production {location} yield improvement fertilizer soil management"
        
        # Retrieve relevant documents
        relevant_docs = self._retrieve_relevant_docs(query, top_k=2)
        context_text = "\n".join(relevant_docs) if relevant_docs else ""
        
        # Build prompt for the model
        prompt = f"""Below is an instruction that describes a task, paired with input that provides context. Write a response.

### Instruction:
You are an agricultural advisor for Kenyan farmers. Provide 3 specific, actionable recommendations to improve {crop} yield based on the current conditions.

### Input:
Location: {location}
Crop: {crop}
Predicted yield: {yield_pred:.2f} t/ha
Temperature: {temp}°C
Rainfall: {rainfall}mm
Soil pH: {soil_ph}
Fertilizer applied: {fertilizer} kg/ha

Agricultural context:
{context_text}

### Response:
Based on your {crop} production in {location}, here are three key recommendations:

1."""
        
        # Generate response
        response = self._generate_response(prompt, max_length=300)
        
        # Parse recommendations (basic parsing)
        recommendations = self._parse_recommendations(response)
        
        # Determine risk level
        risk_level = self._assess_risk_level(context)
        
        return {
            "recommendations": recommendations,
            "risk_level": risk_level,
            "risk_reason": self._get_risk_reason(context, risk_level),
            "full_response": response
        }
    
    def _parse_recommendations(self, response: str) -> List[str]:
        """Parse the model response into structured recommendations."""
        try:
            lines = response.split('\n')
            recommendations = []
            
            for line in lines:
                line = line.strip()
                # Look for numbered recommendations
                if line and (line.startswith(('1.', '2.', '3.', '- ', '• ')) or len(recommendations) < 3):
                    # Clean up the recommendation
                    rec = line.lstrip('123456789.- •').strip()
                    if len(rec) > 10:  # Ignore very short lines
                        recommendations.append(rec)
                        if len(recommendations) >= 3:
                            break
            
            # Ensure we have at least some recommendations
            if not recommendations:
                recommendations = [
                    "Apply balanced NPK fertilizer based on soil test results",
                    "Ensure adequate water management and drainage",
                    "Monitor for pests and diseases regularly"
                ]
            
            return recommendations[:3]  # Return max 3 recommendations
            
        except Exception:
            return [
                "Follow good agricultural practices for optimal yield",
                "Monitor soil and weather conditions regularly",
                "Consider consulting local agricultural extension services"
            ]
    
    def _assess_risk_level(self, context: Dict[str, Any]) -> str:
        """Assess risk level based on context."""
        temp = context.get("temp", 20)
        rainfall = context.get("rainfall", 500)
        soil_ph = context.get("soil_ph", 6.5)
        
        risk_factors = 0
        
        # Temperature risk
        if temp < 15 or temp > 35:
            risk_factors += 1
        
        # Rainfall risk
        if rainfall < 300 or rainfall > 1500:
            risk_factors += 1
        
        # Soil pH risk
        if soil_ph < 5.5 or soil_ph > 8.0:
            risk_factors += 1
        
        if risk_factors >= 2:
            return "high"
        elif risk_factors == 1:
            return "medium"
        else:
            return "low"
    
    def _get_risk_reason(self, context: Dict[str, Any], risk_level: str) -> str:
        """Get explanation for risk assessment."""
        if risk_level == "high":
            return "Multiple environmental factors may impact yield"
        elif risk_level == "medium":
            return "Some conditions may affect optimal growth"
        else:
            return "Conditions are generally favorable for good yield"