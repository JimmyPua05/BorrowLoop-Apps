from flask import Flask, request, jsonify, send_from_directory
from pricing_engine import suggest_price as _suggest_price
from otp_service import generate_otp, send_otp_email, verify_otp as _verify_otp


from flask_cors import CORS
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

app = Flask(__name__)
# Enable CORS so the browser can make requests to this backend
CORS(app)

print("Loading model and tokenizer... This might take a minute...")

base_model_name = "Qwen/Qwen2.5-1.5B-Instruct"
adapter_path = "./BorrowBot AI Model"

# Load the tokenizer from the adapter folder (which contains tokenizer configs)
tokenizer = AutoTokenizer.from_pretrained(adapter_path)

# Load the base model
model = AutoModelForCausalLM.from_pretrained(
    base_model_name,
    torch_dtype=torch.float16,  # Use float16 to save memory
    device_map="auto"           # Automatically map to GPU if available
)

# Apply your local LoRA adapter
model = PeftModel.from_pretrained(model, adapter_path)
print("Model loaded successfully! Server is ready.")


# Serve the main HTML page
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# Serve other static files (css, js)
@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_msg = data.get('message', '')
    
    # We use the Qwen chat template structure
    messages = [
        {"role": "system", "content": "You are BorrowBot, an AI customer support assistant for BorrowLoop—a peer-to-peer community sharing marketplace. Keep answers short and concise."},
        {"role": "user", "content": user_msg}
    ]
    
    # Apply chat template
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    
    # Generate the response
    with torch.no_grad():
        outputs = model.generate(
            **inputs, 
            max_new_tokens=150, 
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
    # Extract only the newly generated text (ignoring the input prompt)
    generated_ids = outputs[0][len(inputs.input_ids[0]):]
    reply = tokenizer.decode(generated_ids, skip_special_tokens=True)
    
    return jsonify({"reply": reply.strip()})

@app.route('/send-otp', methods=['POST'])
def send_otp():
    data  = request.json or {}
    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({"success": False, "message": "Email is required."}), 400
    otp    = generate_otp(email)
    result = send_otp_email(email, otp)
    return jsonify(result)


@app.route('/verify-otp', methods=['POST'])
def verify_otp_route():
    data  = request.json or {}
    email = data.get('email', '').strip().lower()
    otp   = data.get('otp', '').strip()
    if not email or not otp:
        return jsonify({"success": False, "message": "Email and OTP are required."}), 400
    result = _verify_otp(email, otp)
    return jsonify(result)



import re
def _local_llm_fallback(item_name, category, retail_value, condition):
    from datetime import datetime
    month = datetime.now().strftime("%B")
    
    prompt = (
        f"You are a rental pricing expert for BorrowLoop in Malaysia. "
        f"Suggest a daily_rate (number) and deposit (integer) for this item. "
        f"Item: {item_name or category}, Retail RM {retail_value}, Condition: {condition}, Month: {month}. "
        f"Return ONLY a JSON object with keys: daily_rate, deposit, monthly_earnings_est, seasonality_note, demand_note, confidence, reasoning. "
        f"No markdown formatting, just raw JSON."
    )
    
    messages = [
        {"role": "system", "content": "You are a pricing AI. Output valid JSON only, no other text."},
        {"role": "user", "content": prompt}
    ]
    
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs, 
            max_new_tokens=300, 
            temperature=0.1,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
        
    generated_ids = outputs[0][len(inputs.input_ids[0]):]
    reply = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    
    print(f"[local_llm] Output: {reply}")
    
    # Strip markdown code fences if present
    reply = re.sub(r"^```(?:json)?\s*", "", reply)
    reply = re.sub(r"\s*```$", "", reply.strip())
    
    import json
    try:
        data = json.loads(reply)
        data["powered_by"] = "local AI (BorrowBot)"
        # ensure safe minimums
        data["daily_rate"] = max(float(data.get("daily_rate", 2.0)), 2.0)
        data["deposit"] = max(int(data.get("deposit", 10)), 10)
        data["monthly_earnings_est"] = float(data.get("monthly_earnings_est", data["daily_rate"] * 6))
        return data
    except Exception as e:
        print(f"[local_llm] Parse failed: {e}")
        return None

@app.route('/suggest-price', methods=['POST'])
def suggest_price_api():
    data   = request.json or {}
    item_name    = data.get('item_name', '')
    category     = data.get('category', 'Tools')
    retail_value = float(data.get('retail_value', 100))
    condition    = data.get('condition', 'Good')
    
    result = _suggest_price(
        item_name    = item_name,
        category     = category,
        retail_value = retail_value,
        condition    = condition
    )
    
    # If Gemini failed and returned the formula, try local LLM!
    if result.get("powered_by") == "formula":
        print("[server] Gemini failed. Triggering local LLM fallback...")
        local_result = _local_llm_fallback(item_name, category, retail_value, condition)
        if local_result:
            return jsonify(local_result)
            
    return jsonify(result)


if __name__ == '__main__':
    # Run the server on port 5000
    app.run(host='0.0.0.0', port=5000)
