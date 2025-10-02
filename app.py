from flask import Flask, render_template_string, request, jsonify
from dotenv import load_dotenv
import urllib.request
import urllib.error
import json
import time
import os
import logging

load_dotenv()

app = Flask(__name__)

# Configure logging
# Note: In a production environment, you might want to use level=logging.INFO or higher.
logging.basicConfig(level=logging.DEBUG)

MAX_RETRIES = 3

# Using gemini-2.5-flash for broader access and stability, resolving the 404 error.
MODEL_NAME = "gemini-2.5-flash" 

# Cleaned HTML_TEMPLATE to remove non-breaking space characters (U+00A0)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Intent Analyzer</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f7f9fb;
        }
        .container-card {
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.05);
        }
        .status-positive { background-color: #d1fae5; color: #065f46; }
        .status-negative { background-color: #fee2e2; color: #991b1b; }
        .status-neutral { background-color: #fffbeb; color: #92400e; }
        .status-mixed { background-color: #e0f2fe; color: #075985; }
        .status-default { background-color: #e5e7eb; color: #4b5563; }
    </style>
</head>
<body class="p-4 sm:p-8">
    <div class="min-h-screen flex flex-col items-center">
        <header class="w-full max-w-4xl text-center mb-10 mt-4">
            <h1 class="text-4xl font-extrabold text-gray-900 mb-2">AI Intent Analyzer Dashboard</h1>
            <p class="text-lg text-gray-600">Analyze Social Data. Predict User Needs using the Gemini API.</p>
            <div class="h-1 bg-indigo-500 w-24 mx-auto rounded-full mt-4"></div>
        </header>
        <div id="app-container" class="w-full max-w-4xl grid gap-6 md:grid-cols-2">
            <div class="container-card bg-white p-6 rounded-xl border border-gray-100">
                <h2 class="text-2xl font-semibold text-indigo-700 mb-4">Input User Text</h2>
                <div id="error-message" class="hidden bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
                    <strong class="font-bold">Input Required:</strong>
                    <span class="block sm:inline">Please enter text to analyze.</span>
                </div>
                <textarea
                    id="text-input"
                    rows="8"
                    placeholder="Paste a social media post or customer query here..."
                    class="w-full p-3 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 transition duration-150 mb-4 text-gray-800"
                >I just downloaded the new update and I love the dark mode feature! It makes using the app so much easier at night.</textarea>
                <button 
                    id="analyze-button"
                    class="w-full py-3 px-4 rounded-full text-white font-bold transition duration-300 shadow-md bg-indigo-600 hover:bg-indigo-700 shadow-indigo-500/50"
                >
                    Run Intent Analysis
                </button>
            </div>
            <div class="container-card bg-white p-6 rounded-xl shadow-lg border border-gray-100">
                <h2 class="text-2xl font-semibold text-green-700 mb-4">Analysis Results</h2>
                <div id="results-output" class="bg-gray-50 p-4 rounded-lg min-h-[250px] flex flex-col justify-between">
                    <p id="placeholder" class="text-gray-400 py-12 text-center">
                        Analysis results will appear here after processing.
                    </p>
                    <div id="loading" class="hidden text-center py-12 text-indigo-500 font-medium">
                        <div class="animate-spin inline-block w-6 h-6 border-4 border-t-4 border-indigo-500 border-t-transparent rounded-full mb-3"></div>
                        Processing with Gemini...
                    </div>
                    <div id="result-content" class="hidden">
                        <p id="result-text" class="text-gray-700 whitespace-pre-wrap mb-4"></p>
                        <div class="mt-4 pt-4 border-t border-gray-200">
                            <span class="font-semibold text-gray-900">Sentiment:</span>
                            <span id="sentiment-display" class="ml-2 px-3 py-1 rounded-full text-sm font-medium status-default">
                                Unknown
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <footer class="mt-12 text-sm text-gray-500">
            Powered by Google Gemini Models.
        </footer>
    </div>
    <script>
        const input = document.getElementById('text-input');
        const button = document.getElementById('analyze-button');
        const loading = document.getElementById('loading');
        const placeholder = document.getElementById('placeholder');
        const resultContent = document.getElementById('result-content');
        const resultText = document.getElementById('result-text');
        const sentimentDisplay = document.getElementById('sentiment-display');
        const errorMessage = document.getElementById('error-message');

        const SENTIMENT_STYLES = {
            'POSITIVE': 'status-positive',
            'NEGATIVE': 'status-negative',
            'NEUTRAL': 'status-neutral',
            'MIXED': 'status-mixed',
            'UNKNOWN': 'status-default',
            'ERROR': 'status-negative', // Use negative style for errors
        };

        // Function to parse the sentiment from the model's text response
        function extractSentiment(text) {
            // Matches the line that starts with 'Sentiment:' followed by one of the keywords
            const match = text.match(/Sentiment:\s*(Positive|Negative|Neutral|Mixed)/i);
            return match ? match[1].toUpperCase() : 'UNKNOWN';
        }
        
        function hideError() {
            errorMessage.classList.add('hidden');
        }

        button.addEventListener('click', async () => {
            hideError();
            const userPrompt = input.value.trim();
            
            if (!userPrompt) {
                errorMessage.classList.remove('hidden');
                return;
            }

            // UI state: Disable button and show loading
            button.disabled = true;
            button.classList.remove('bg-indigo-600', 'hover:bg-indigo-700');
            button.classList.add('bg-indigo-300', 'cursor-not-allowed');
            button.textContent = 'Analyzing...';
            
            placeholder.classList.add('hidden');
            resultContent.classList.add('hidden');
            loading.classList.remove('hidden');

            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ userPrompt: userPrompt })
                });

                if (!response.ok) {
                    const errorJson = await response.json().catch(() => ({}));
                    const errorMessage = errorJson.error || `HTTP error! status: ${response.status}`;
                    throw new Error(errorMessage);
                }
                
                const result = await response.json();
                
                if (result.error) {
                    throw new Error(result.error);
                }

                const text = result.text || 'Error: Could not process request.';
                
                resultText.textContent = text;
                const sentiment = extractSentiment(text);

                // Update sentiment display and styling
                sentimentDisplay.textContent = sentiment;
                Object.values(SENTIMENT_STYLES).forEach(c => sentimentDisplay.classList.remove(c));
                sentimentDisplay.classList.add(SENTIMENT_STYLES[sentiment] || SENTIMENT_STYLES['UNKNOWN']);

                resultContent.classList.remove('hidden');

            } catch (error) {
                // Display specific error message
                resultText.textContent = `Error processing intent: ${error.message}`;
                sentimentDisplay.textContent = 'ERROR';
                Object.values(SENTIMENT_STYLES).forEach(c => sentimentDisplay.classList.remove(c));
                sentimentDisplay.classList.add(SENTIMENT_STYLES['ERROR']);
                resultContent.classList.remove('hidden');
            } finally {
                // Reset UI state
                button.disabled = false;
                button.classList.remove('bg-indigo-300', 'cursor-not-allowed');
                button.classList.add('bg-indigo-600', 'hover:bg-indigo-700');
                button.textContent = 'Run Intent Analysis';
                loading.classList.add('hidden');
            }
        });
        
        input.addEventListener('input', hideError);
    </script>
</body>
</html>
"""

def call_gemini_with_retry(api_url, payload, api_key, max_retries=MAX_RETRIES):
    """
    Calls the Gemini API with exponential backoff for transient errors.
    Uses urllib.request as no external libraries are assumed.
    """
    delay = 1
    # Append the API key to the URL
    url = f"{api_url}?key={api_key}"
    data = json.dumps(payload).encode('utf-8')

    # Simple class to mimic a response object for easier error handling
    class Response:
        def __init__(self, status_code, text):
            self.status_code = status_code
            self.text = text

        def json(self):
            return json.loads(self.text)

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as http_response:
                response_text = http_response.read().decode('utf-8')
                # Success
                return Response(http_response.status, response_text)
        except urllib.error.HTTPError as e:
            # Check for server errors (5xx) which are often transient
            is_transient_error = e.code >= 500
            if attempt == max_retries - 1 or not is_transient_error:
                # Re-raise client errors (4xx) immediately or if max retries reached
                raise e
            # Wait and retry for transient errors
            app.logger.debug(f"Transient error ({e.code}) on attempt {attempt + 1}. Retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2 # Exponential backoff
        except urllib.error.URLError as e:
            # Network or connection errors
            if attempt == max_retries - 1:
                raise e
            app.logger.debug(f"Network error on attempt {attempt + 1}. Retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2

    raise Exception("Max retries exceeded without successful response from Gemini API.")

@app.route("/")
def index():
    # Render the main HTML dashboard template
    return render_template_string(HTML_TEMPLATE)

@app.route("/analyze", methods=["POST"])
def analyze_intent():
    try:
        data = request.get_json()
        user_prompt = data.get('userPrompt')

        if not user_prompt:
            return jsonify({'error': 'No userPrompt provided'}), 400

        API_KEY = os.environ.get('GEMINI_API_KEY', '')

        app.logger.debug(f"Using model: {MODEL_NAME}")

        if not API_KEY:
            app.logger.error("Configuration Error: Gemini API Key not found in environment variables.")
            return jsonify({'error': 'Configuration Error: Gemini API Key not found. Please set GEMINI_API_KEY in your environment.'}), 500

        # System Instruction: Defines the model's role and output format.
        system_prompt = f"""You are a specialized AI Intent Analyzer. Your task is to analyze the user's provided text and provide two distinct, single-line classifications, followed by a brief 2-3 sentence summary of your analysis.
1. **User Intent:** Determine the primary goal or reason behind the user's text (e.g., 'Product Praise', 'Technical Support Issue', 'Request for Feature', 'General Inquiry').
2. **Sentiment:** Determine the overall sentiment (Positive, Negative, Neutral, or Mixed).
Format your response *exactly* as follows:
User Intent: [CLASSIFICATION]
Sentiment: [Positive|Negative|Neutral|Mixed]
[2-3 sentence summary of the text's implications and key findings.]"""

        # Construct the API payload using the systemInstruction field (Best Practice)
        payload = {
            "contents": [
                {
                    # The actual user query
                    "parts": [{"text": f"Analyze the following User Text:\n---\n{user_prompt}"}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            }
        }
        
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"

        # Call the API with retry logic
        response = call_gemini_with_retry(api_url, payload, API_KEY)
        
        gemini_result = response.json()

        # Extract the generated text
        text = gemini_result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'Analysis failed to return text.')
        
        return jsonify({'text': text})

    except urllib.error.HTTPError as e:
        error_response = f"API Error ({e.code}): {e.reason}."
        try:
            # Attempt to read the error body for more specific details
            error_response_body = e.read().decode('utf-8')
            error_details = json.loads(error_response_body).get('error', {}).get('message', 'No specific message available.')
            app.logger.error(f"Full Gemini Error Response: {error_response_body}")
            return jsonify({'error': f"API Error: {e.code}. Details: {error_details}"}), e.code
        except Exception:
            app.logger.error(f"Failed to parse detailed error response.")
            return jsonify({'error': error_response}), 500
    except urllib.error.URLError as e:
        app.logger.error(f"Network Error: {e}")
        return jsonify({'error': f'Failed to connect to the analysis service: {e}'}), 500
    except Exception as e:
        app.logger.error(f"Internal Error: {e}", exc_info=True)
        return jsonify({'error': f'An unexpected internal error occurred: {e}'}), 500

if __name__ == "__main__":
    # Setting host='0.0.0.0' makes the application externally accessible
    # In a production environment, debug should be False
    app.run(debug=True, host='0.0.0.0', port=8082)
