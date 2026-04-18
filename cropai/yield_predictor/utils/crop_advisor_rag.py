import os
import pickle
import torch
import faiss
import numpy as np
import warnings
import logging
from typing import Dict, List, Any
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)
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
        self.model_ready = False
        self.rag_ready = False

        self._load_model()
        self._load_rag_components()
        self.model_ready = self.model is not None
        self.rag_ready = all([self.embedder, self.faiss_index, self.documents])
    
    def _load_model(self):
        """Load the fine-tuned Qwen model with LoRA adapters."""
        from transformers import AutoConfig

        base_model_id = "unsloth/Qwen3.5-0.8B"

        logger.info(f"Loading base model: {base_model_id}")
        config = AutoConfig.from_pretrained(
            base_model_id,
            trust_remote_code=True
        )

        if hasattr(config, 'text_config'):
            for key, value in vars(config.text_config).items():
                setattr(config, key, value)

        use_mps = torch.backends.mps.is_available()
        dtype = torch.float16 if use_mps else torch.float32
        device = "mps" if use_mps else "cpu"

        logger.info(f"Loading on {device} with dtype={dtype}")
        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_id,
            config=config,
            device_map={"": device},
            torch_dtype=dtype,
            trust_remote_code=True,
        )

        if self.model_path and os.path.exists(self.model_path):
            logger.info(f"Loading LoRA adapter from: {self.model_path}")
            self.model = PeftModel.from_pretrained(base_model, self.model_path)
            logger.info("LoRA adapter loaded successfully")
        else:
            logger.warning(
                f"LoRA adapter path not found: {self.model_path}. "
                f"Using base model without fine-tuning."
            )
            self.model = base_model

        self.model.eval()  # Set to inference mode
        logger.info(f"Model ready on {self.model.device}")

        self.tokenizer = AutoTokenizer.from_pretrained(
            base_model_id,
            trust_remote_code=True
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
    
    def _load_rag_components(self):
        """Load RAG components: embedder, FAISS index, and documents."""
        embedder_path = os.path.join(self.rag_data_path, "rag_embedder_name.txt")
        if os.path.exists(embedder_path):
            with open(embedder_path, 'r') as f:
                embedder_name = f.read().strip()
            logger.info(f"Loading SentenceTransformer embedder: {embedder_name}")
            self.embedder = SentenceTransformer(embedder_name)
            logger.info("Embedder loaded successfully")
        else:
            logger.warning(f"Embedder config not found: {embedder_path}")

        index_path = os.path.join(self.rag_data_path, "rag_index.faiss")
        if os.path.exists(index_path):
            self.faiss_index = faiss.read_index(index_path)
            logger.info(f"FAISS index loaded from: {index_path}")

        docs_path = os.path.join(self.rag_data_path, "rag_docs.pkl")
        if os.path.exists(docs_path):
            with open(docs_path, 'rb') as f:
                self.documents = pickle.load(f)
            logger.info(f"RAG documents loaded: {len(self.documents)} docs")
        else:
            logger.warning(f"RAG docs not found: {docs_path}")
    
    def _retrieve_relevant_docs(self, query: str, top_k: int = 2) -> List[str]:
        """Retrieve relevant documents for the query."""
        if not all([self.embedder, self.faiss_index, self.documents]):
            return []
        
        query_embedding = self.embedder.encode([query])
        query_embedding = query_embedding.astype('float32')
        
        scores, indices = self.faiss_index.search(query_embedding, top_k)
        
        relevant_docs = []
        for idx in indices[0]:
            if 0 <= idx < len(self.documents):
                relevant_docs.append(self.documents[idx])
        
        return relevant_docs
    
    def _generate_response(self, messages: list, max_new_tokens: int = 250) -> str:
        """Generate response using the fine-tuned model with messages format."""
        if not (self.model and self.tokenizer):
            raise RuntimeError("Model or tokenizer not initialized")
        
        import re
        
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
                suppress_tokens=think_token_ids if think_token_ids else None,
            )
        
        new_tokens = outputs[0][input_ids.shape[1]:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
        return response
    
    def get_recommendations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get crop recommendations based on context.
        Uses RAG retrieval when available, otherwise generates directly from the model.

        Args:
            context: Dictionary with crop, location, yield, weather, soil data

        Returns:
            Dictionary with recommendations, risk level, and reasoning
        """
        if not self.model_ready:
            raise RuntimeError("Model not loaded — cannot generate recommendations")

        crop = context.get("crop", "maize")
        location = context.get("location", "")
        yield_pred = context.get("yield", 0)
        temp = context.get("temp", 20)
        rainfall = context.get("rainfall", 500)
        soil_ph = context.get("soil_ph", 6.5)
        fertilizer = context.get("fertilizer", 100)
        
        query = f"{crop} production {location} yield improvement fertilizer soil management"
        relevant_docs = self._retrieve_relevant_docs(query, top_k=2)
        
        if not self.model:
            raise RuntimeError("Model not initialized - cannot generate recommendations")
        
        doc_texts = []
        for doc in relevant_docs:
            if isinstance(doc, dict):
                title = doc.get('title', '')
                content = doc.get('content', '').strip()
                doc_texts.append(f"[{title}]\n{content}")
            else:
                doc_texts.append(str(doc))
        context_text = "\n\n".join(doc_texts) if doc_texts else ""
        
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
        
        response = self._generate_response(messages, max_new_tokens=250)
        recommendations = self._parse_recommendations(response)
        risk_level = self._assess_risk_level(context)
        
        return {
            "recommendations": recommendations,
            "risk_level": risk_level,
            "risk_reason": self._get_risk_reason(context, risk_level),
            "full_response": response
        }
    
    def _parse_recommendations(self, response: str) -> List[str]:
        """Parse the model response into structured recommendations."""
        import re
        lines = response.split('\n')
        recommendations = []
        
        for line in lines:
            line = line.strip()
            line = re.sub(r'\*\*.*?\*\*:?\s*', '', line).strip()
            line = line.lstrip('0123456789.-• ').strip()
            if len(line) > 25 and not line.endswith(':'):
                recommendations.append(line)
            if len(recommendations) >= 3:
                break
        
        if not recommendations:
            raise ValueError("Failed to parse recommendations from model response")
        
        return recommendations[:3]
    
    def _assess_risk_level(self, context: Dict[str, Any]) -> str:
        """Assess risk level based on context."""
        temp = context.get("temp", 20)
        rainfall = context.get("rainfall", 500)
        soil_ph = context.get("soil_ph", 6.5)
        
        risk_factors = 0
        if temp < 15 or temp > 35:
            risk_factors += 1
        if rainfall < 300 or rainfall > 1500:
            risk_factors += 1
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