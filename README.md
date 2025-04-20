# Financial Analysis AI Demo

A sleek web interface for analyzing financial transactions using Google's Gemini AI.

## Features

- Clean, minimalist black and white UI
- Configure API key and custom prompts
- Upload images for receipt analysis
- Chatbot-style interaction with the AI
- Well-formatted ASCII table results

## Setup

1. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

2. Add your api and set your model in the .env file
   
3. Run the Flask application:
   ```
   python app.py
   ```

3. Open your browser and navigate to `http://127.0.0.1:5000`

## Usage

1. Enter your Gemini API key in the designated field
2. Customize the system prompt if needed (default is provided)
3. Enter a description of your transaction or upload an image of a receipt
4. Click "Analyze" to process the data
5. View the formatted results in the chat panel

## Requirements

- Python 3.7+
- Flask
- Google Generative AI library
- Internet connection for API access

## Note

You need a valid Google Gemini API key to use this application. You can obtain one from the [Google AI Studio](https://makersuite.google.com/app/apikey). 
