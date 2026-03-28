import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig
from peft import PeftModel

# 1. Paths
base_model_id = "Qwen/Qwen3.5-0.8B"
lora_adapter_path = "./qwen35_cropai_lora_final"

print("Loading specialized CropAI model...")

# 2. Load and Fix Configuration
config = AutoConfig.from_pretrained(base_model_id, trust_remote_code=True)
if hasattr(config, "text_config"):
    for key, value in vars(config.text_config).items():
        setattr(config, key, value)

# 3. Load Base Model
model = AutoModelForCausalLM.from_pretrained(
    base_model_id,
    config=config,
    device_map="auto",
    torch_dtype=torch.float16 if torch.backends.mps.is_available() else torch.float32,
    trust_remote_code=True
)

# 4. Attach your LoRA "Backpack"
model = PeftModel.from_pretrained(model, lora_adapter_path)
tokenizer = AutoTokenizer.from_pretrained(base_model_id, trust_remote_code=True)

print("Model successfully merged! Testing prediction...")

# 5. Run a Test Prompt
prompt = "How do I optimize maize yield in a region with low rainfall?"
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

with torch.no_grad():
    outputs = model.generate(**inputs, max_new_tokens=100)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)

print("\n--- AI Response ---")
print(response)
