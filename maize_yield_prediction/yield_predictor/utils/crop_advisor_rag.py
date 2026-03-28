"""
CropAdvisorRAG - Fine-tuned Qwen3.5 with RAG for agricultural recommendations
"""

import os
import pickle
import torch
import faiss
import numpy as np
import warnings
from typing import Dict, List, Any
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from sentence_transformers import SentenceTransformer

# Suppress known non-critical warnings
warnings.filterwarnings('ignore', message='Found missing adapter keys')


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
            from transformers import AutoConfig
            
            # Use the Unsloth variant - matches adapter training base
            base_model_id = "unsloth/Qwen3.5-0.8B"
            
            print(f"Loading {base_model_id} with configuration fix...")
            
            # 1. Load config separately first
            config = AutoConfig.from_pretrained(
                base_model_id, 
                trust_remote_code=True
            )
            
            # 2. Fix: Manually inject nested text attributes to the top level
            # Qwen 3.5 nests these in text_config, but standard loaders look at the root
            if hasattr(config, 'text_config'):
                for key, value in vars(config.text_config).items():
                    setattr(config, key, value)
            
            # 3. Load base model with corrected config
            base_model = AutoModelForCausalLM.from_pretrained(
                base_model_id,
                config=config,
                device_map="auto",
                torch_dtype=torch.float16 if torch.backends.mps.is_available() else torch.float32,
                trust_remote_code=True
            )
            
            print("✓ Base model loaded from cache")
            
            # 4. Load LoRA adapter if path provided
            if self.model_path and os.path.exists(self.model_path):
                self.model = PeftModel.from_pretrained(base_model, self.model_path)
                print(f"✓ Loaded fine-tuned LoRA adapter from {self.model_path}")
            else:
                self.model = base_model
                print("⚠ Using base model (no fine-tuned adapter found)")
            
            # 5. Load tokenizer
            tokenizer_path = self.model_path if self.model_path and os.path.exists(self.model_path) else base_model_id
            self.tokenizer = AutoTokenizer.from_pretrained(
                tokenizer_path, 
                trust_remote_code=True
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            print("✓ Qwen model + LoRA adapter loaded successfully")
                
        except Exception as e:
            print(f"⚠ Error loading model: {e}")
            print("⚠ Falling back to RAG-enhanced recommendations without model")
            self.model = None
            self.tokenizer = None
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
    
    def _generate_response(self, messages: list, max_new_tokens: int = 250) -> str:
        """Generate response using the fine-tuned model with messages format."""
        if not (self.model and self.tokenizer):
            return ''
        
        try:
            import re
            
            # Apply chat template - disable thinking mode
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            
            inputs = self.tokenizer(
                [text],
                return_tensors='pt',
                padding=True,
                return_attention_mask=True,
            )
            input_ids = inputs['input_ids'].to(self.model.device)
            attention_mask = inputs['attention_mask'].to(self.model.device)
            
            # Get the token ID for <think> to use as a bad word
            think_token_ids = self.tokenizer.encode('<think>', add_special_tokens=False)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=max_new_tokens,
                    temperature=0.7,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    # Suppress <think> token to force non-thinking output
                    suppress_tokens=think_token_ids if think_token_ids else None,
                )
            
            new_tokens = outputs[0][input_ids.shape[1]:]
            response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
            
            # Safety net: strip any think block that got through
            response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
            
            return response
            
        except Exception as e:
            print(f'Generation error: {e}')
            return ''
    
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
        
        # If model is not available, use RAG-enhanced fallback
        if not self.model:
            return self._rag_enhanced_fallback(context, relevant_docs)
        
        # Build prompt for the model
        # Extract title and content from documents (they are dicts)
        doc_texts = []
        for doc in relevant_docs:
            if isinstance(doc, dict):
                title = doc.get('title', '')
                content = doc.get('content', '').strip()
                doc_texts.append(f"[{title}]\n{content}")
            else:
                doc_texts.append(str(doc))
        context_text = "\n\n".join(doc_texts) if doc_texts else ""
        
        # Build messages for chat template
        messages = [
            {
                'role': 'system',
                'content': (
                    'You are an agricultural advisor for Kenyan smallholder farmers. '
                    'Give direct, practical advice. Do not use <think> blocks. '
                    'Respond with exactly 3 numbered recommendations.'
                )
            },
            {
                'role': 'user', 
                'content': (
                    f'Crop: {crop}, Location: {location}, Kenya\n'
                    f'Predicted yield: {yield_pred:.2f} t/ha\n'
                    f'Temperature: {temp}°C, Rainfall: {rainfall}mm\n'
                    f'Soil pH: {soil_ph}, Fertilizer: {fertilizer} kg/ha\n\n'
                    f'Agricultural context:\n{context_text}\n\n'
                    f'Provide 3 specific, actionable recommendations:'
                )
            }
        ]
        
        # Generate response with message format (reduced tokens to avoid repetition)
        response = self._generate_response(messages, max_new_tokens=250)
        
        # Debug: print raw model output
        print(f"🤖 RAG MODEL RAW OUTPUT:\n{response}\n")
        
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
    
    def _rag_enhanced_fallback(self, context: Dict[str, Any], relevant_docs: List[str]) -> Dict[str, Any]:
        """
        Enhanced fallback that uses RAG documents when model isn't loaded.
        """
        crop = context.get("crop", "maize")
        yield_pred = context.get("yield", 0)
        rainfall = context.get("rainfall", 500)
        temp = context.get("temp", 20)
        soil_ph = context.get("soil_ph", 6.5)
        fertilizer = context.get("fertilizer", 100)
        
        # Base recommendations
        recommendations = []
        
        # Add RAG-based recommendations if available
        if relevant_docs:
            print(f"📚 Using {len(relevant_docs)} RAG documents for recommendations")
            for doc in relevant_docs[:1]:  # Use first doc
                # Extract content from document dict
                doc_content = doc.get('content', '') if isinstance(doc, dict) else str(doc)
                if crop in doc_content.lower():
                    # Extract first sentence or key point
                    first_line = doc_content.strip().split('\n')[0].strip()
                    recommendations.append(f"Kenya agricultural data: {first_line[:120]}...")
        
        # Add context-specific recommendations
        if yield_pred < 1.5:
            recommendations.append(f"Your predicted {crop} yield ({yield_pred:.2f} t/ha) is below average. Consider: increasing fertilizer application, improving soil preparation, and selecting high-yield varieties.")
        elif yield_pred < 2.5:
            recommendations.append(f"Moderate yield predicted ({yield_pred:.2f} t/ha). Optimize with: timely planting, balanced NPK fertilization (current: {fertilizer} kg/ha), and proper spacing.")
        else:
            recommendations.append(f"Good yield potential ({yield_pred:.2f} t/ha). Maintain by: following recommended practices, monitoring for pests/diseases, and ensuring adequate moisture.")
        
        if rainfall < 600:
            recommendations.append(f"Low rainfall season ({rainfall}mm predicted). Implement water conservation: mulching, drought-resistant varieties, and supplementary irrigation if possible.")
        elif rainfall > 1200:
            recommendations.append(f"High rainfall expected ({rainfall}mm). Prepare for: improved drainage, fungal disease prevention, and timely weeding to prevent waterlogging.")
        
        if soil_ph < 5.5:
            recommendations.append(f"Acidic soil (pH {soil_ph}). Apply lime to raise pH to 6.0-6.5 for optimal {crop} growth and nutrient availability.")
        elif soil_ph > 7.5:
            recommendations.append(f"Alkaline soil (pH {soil_ph}). Consider organic matter addition and sulfur application to lower pH for better {crop} performance.")
        
        # Take top 4 recommendations
        recommendations = recommendations[:4]
        
        # If still no recommendations, use defaults
        if not recommendations:
            recommendations = [
                f"Plant {crop} at the beginning of the rainy season for optimal germination",
                "Apply balanced fertilizer based on soil test results",
                "Monitor weather conditions and adjust farming practices accordingly",
                "Practice crop rotation to maintain soil health"
            ]
        
        risk_level = self._assess_risk_level(context)
        
        return {
            "recommendations": recommendations,
            "risk_level": risk_level,
            "risk_reason": self._get_risk_reason(context, risk_level),
            "rag_docs_used": len(relevant_docs)
        }
    
    def _parse_recommendations(self, response: str) -> List[str]:
        """Parse the model response into structured recommendations."""
        try:
            import re
            lines = response.split('\n')
            recommendations = []
            
            for line in lines:
                line = line.strip()
                # Strip markdown bold markers
                line = re.sub(r'\*\*.*?\*\*:?\s*', '', line).strip()
                # Skip bullets that are just headers or very short
                line = line.lstrip('0123456789.-• ').strip()
                # Only keep substantial lines that don't end with colon (headers)
                if len(line) > 25 and not line.endswith(':'):
                    recommendations.append(line)
                if len(recommendations) >= 3:
                    break
            
            # Ensure we have at least some recommendations
            if not recommendations:
                recommendations = [
                    "Apply balanced NPK fertilizer based on soil test results.",
                    "Ensure adequate water management and drainage.",
                    "Monitor for pests and diseases regularly.",
                ]
            
            return recommendations[:3]  # Return max 3 recommendations
            
        except Exception:
            return [
                "Follow good agricultural practices for optimal yield.",
                "Monitor soil and weather conditions regularly.",
                "Consider consulting local agricultural extension services."
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