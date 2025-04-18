import os
import base64
from flask import Flask, render_template, request, jsonify, session
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file if present

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SERVER_PORT'] = 5001  # Change port to avoid conflict
app.secret_key = os.urandom(24)  # For session management

# Hardcoded API key - replace with your actual key or get from environment
API_KEY = os.getenv('GEMINI_API_KEY', '')

# Default model - get from environment or use default
DEFAULT_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')

# Default prompts
DEFAULT_SYSTEM_PROMPT = """

You are a financial assistant that extracts and records one or more transaction records from user input, which may be in text, image, or voice format.

Your task is to identify the following fields for each transaction:
- transaction_type: "expense" or "revenue"
- category: e.g., "food", "shopping", "transportation", etc.
- date: in YYYY-MM-DD format
- time: in HH:MM 24-hour format
- details: short description of the transaction
- amount: numeric value
- currency: e.g., "HKD", "USD", "RMB"
- payment_method: e.g., "Octopus", "Visa", "Alipay", "Cash", etc.

If the input is an image, apply OCR to extract the text.  
If the input is voice, transcribe it before analysis.

If multiple transactions are found, extract each one as a separate JSON object.

If any field is missing or unclear, can you guess it first if possible. But do not inlcude in the JSON file. Instead, clearly ask the user for clarification in a friendly way.

Always output the extracted data in a JSON array, wrapped in triple backticks, like this:

```json
[
  {
    "transaction_type": "",
    "category": "",
    "date": "",
    "time": "",
    "details": "",
    "amount": 0,
    "currency": "",
    "payment_method": ""
  },
  ...
]
```

and then show output question or clarification outside the JSON array.
"""

@app.route('/')
def index():
    # Initialize session chat history if it doesn't exist
    if 'chat_history' not in session:
        session['chat_history'] = []
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    system_prompt = request.form.get('system_prompt', DEFAULT_SYSTEM_PROMPT)
    user_prompt = request.form.get('user_prompt', '')
    
    # Debug info
    app.logger.info(f"Received request: System prompt length: {len(system_prompt)}, User prompt: {user_prompt[:50]}...")
    
    try:
        genai.configure(api_key=API_KEY)
        
        model = genai.GenerativeModel(DEFAULT_MODEL)
        app.logger.info(f"Using model: {DEFAULT_MODEL}")
        
        if 'chat_history' not in session:
            session['chat_history'] = []
            
        chat_history = session['chat_history'][-5:] if session['chat_history'] else []
        
        content = system_prompt
        
        image_uploaded = False
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename:
                try:
                    app.logger.info(f"Processing image: {image_file.filename}")
                    image_data = image_file.read()
                    
                    # For images, we need to use multimodal generation
                    image_parts = [
                        content,
                        {"mime_type": image_file.content_type or "image/jpeg", 
                         "data": base64.b64encode(image_data).decode('utf-8')}
                    ]
                    
                    # Add user prompt if provided
                    if user_prompt:
                        image_parts.append(user_prompt)
                        
                    # Add chat history context if available
                    history_text = ""
                    if chat_history:
                        history_text = "Previous conversation:\n"
                        for entry in chat_history:
                            if entry['type'] == 'user':
                                history_text += f"User: {entry['text']}\n"
                            else:
                                history_text += f"Assistant: {entry['text']}\n"
                        image_parts.insert(0, history_text)
                    
                    app.logger.info("Sending request to model with image")
                    response = model.generate_content(image_parts)
                    image_uploaded = True
                except Exception as e:
                    app.logger.error(f"Error processing image: {str(e)}")
                    return jsonify({"error": f"Image processing failed: {str(e)}"}), 500
        
        # Check if audio was uploaded
        audio_uploaded = False
        if 'audio' in request.files and not image_uploaded:
            audio_file = request.files['audio']
            if audio_file and audio_file.filename:
                try:
                    app.logger.info(f"Processing audio: {audio_file.filename}")
                    audio_data = audio_file.read()
                    
                    # First prompt to tell Gemini that this is audio data that needs to be transcribed
                    transcription_prompt = f"{content}\n\nThe following is an audio file that contains speech describing financial transaction(s). Please transcribe the audio first, then extract the transaction details based on the transcription."
                    
                    # For audio, we also use multimodal generation
                    audio_parts = [
                        transcription_prompt,
                        {"mime_type": audio_file.content_type or "audio/mpeg", 
                         "data": base64.b64encode(audio_data).decode('utf-8')}
                    ]
                    
                    # Add user prompt if provided
                    if user_prompt:
                        audio_parts.append(f"Additional context from user: {user_prompt}")
                        
                    # Add chat history context if available
                    history_text = ""
                    if chat_history:
                        history_text = "Previous conversation:\n"
                        for entry in chat_history:
                            if entry['type'] == 'user':
                                history_text += f"User: {entry['text']}\n"
                            else:
                                history_text += f"Assistant: {entry['text']}\n"
                        audio_parts.insert(0, history_text)
                    
                    app.logger.info("Sending request to model with audio")
                    response = model.generate_content(audio_parts)
                    audio_uploaded = True
                except Exception as e:
                    app.logger.error(f"Error processing audio: {str(e)}")
                    return jsonify({"error": f"Audio processing failed: {str(e)}"}), 500
        
        # If no image or audio was processed, handle text-only input
        if not image_uploaded and not audio_uploaded:
            # Text-only input
            # Add chat history context if available
            if chat_history:
                history_text = "Previous conversation:\n"
                for entry in chat_history:
                    if entry['type'] == 'user':
                        history_text += f"User: {entry['text']}\n"
                    else:
                        history_text += f"Assistant: {entry['text']}\n"
                content = f"{history_text}\n\nSystem: {content}"
            
            if user_prompt:
                full_prompt = f"{content}\n\nUser: {user_prompt}"
            else:
                full_prompt = content
            
            app.logger.info("Sending text-only request to model")
            response = model.generate_content(full_prompt)
        
        # Add this exchange to chat history
        chat_history.append({'type': 'user', 'text': user_prompt})
        chat_history.append({'type': 'assistant', 'text': response.text})
        
        # Update session
        session['chat_history'] = chat_history
        
        app.logger.info(f"Response length: {len(response.text)}")
        return jsonify({"response": response.text})
    
    except Exception as e:
        app.logger.error(f"Error in analyze route: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/clear_history', methods=['POST'])
def clear_history():
    session['chat_history'] = []
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(debug=True, port=5001) 