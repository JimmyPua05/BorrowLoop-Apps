# BorrowLoop 🔄

BorrowLoop is a peer-to-peer (P2P) community sharing and rental marketplace built for the Malaysian community. Our platform encourages sustainable living and resource sharing by making it incredibly easy to list, rent, and borrow everyday items.

## 🌟 Key Features

To eliminate the friction of listing items and providing customer support, BorrowLoop integrates powerful AI features:

### 1. Smart Pricing Engine 🧠
When a user lists an item, they often don't know how much to charge. Our AI-driven pricing engine solves this by analyzing the item category, retail value, condition, and current seasonal demand to automatically recommend:
- **Daily Rental Rate**
- **Suggested Deposit**
- **Estimated Monthly Earnings**

**Tri-level Fallback Architecture:**
- **Primary:** Powered by **Google Gemini API** (`gemini-3.5-flash`) for highly accurate market analysis and pricing suggestions.
- **Secondary (Formula Fallback):** If the external API is unreachable, the system gracefully degrades to a robust rule-based formula adjusted for seasonality and condition.
- **Tertiary (Local LLM):** A locally deployed, fine-tuned **Qwen 2.5-1.5B-Instruct** model (via LoRA) provides on-device AI pricing inference to ensure the core workflow is never interrupted.

### 2. BorrowBot: AI Customer Support 🤖
A responsive AI assistant embedded directly into the platform. BorrowBot is fine-tuned to answer user queries concisely and accurately regarding platform rules, borrowing etiquette, and dispute resolution.

### 3. Secure Verification 🔐
Built-in OTP (One-Time Password) email verification system ensures all users are authenticated, maintaining a high-trust community environment.

## 🛠️ Technology Stack

**Backend & AI:**
- **Python & Flask:** Core backend framework and API routing.
- **PyTorch & Transformers (Hugging Face):** Used for loading and running the local LLM.
- **PEFT (Parameter-Efficient Fine-Tuning):** For applying custom LoRA adapter weights to the local Qwen model.
- **Google Gemini API:** For advanced, cloud-based pricing intelligence.

**Frontend:**
- **HTML5, CSS3, Vanilla JavaScript:** Lightweight, responsive user interface.

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Anaconda / Miniconda (recommended)
- WSL (if running on Windows)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Kimii-Dev/BorrowLoop-Apps.git
   cd BorrowLoop-Apps
   ```

2. **Set up the environment:**
   Create a `.env` file in the root directory and add your API keys:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-3.5-flash
   ```

3. **Install dependencies:**
   *(Ensure you have `flask`, `flask_cors`, `torch`, `transformers`, `peft`, and `python-dotenv` installed)*
   ```bash
   pip install flask flask-cors torch transformers peft python-dotenv
   ```

4. **Run the application:**
   ```bash
   python server.py
   ```
   The server will start at `http://0.0.0.0:5000`. Open this in your browser to access BorrowLoop!


