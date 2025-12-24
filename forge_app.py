"""
FORGE - AI Coding Assistant Web App
Cloud-hosted coding expert for Python and PowerShell
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_session import Session
import anthropic
import subprocess
import os
import secrets
import sys
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
Session(app)

# Get API key and password from environment
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
FORGE_PASSWORD = os.environ.get('FORGE_PASSWORD', 'forge123')  # Change this!

# Initialize Anthropic client
if ANTHROPIC_API_KEY:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    client = None

# System prompt for coding assistant
SYSTEM_PROMPT = """You are Forge, an expert AI coding assistant specializing in Python and PowerShell.

Your expertise:
- Writing clean, efficient, production-ready code
- Debugging and fixing errors
- Optimizing performance
- Explaining complex code clearly
- Following best practices
- Security-conscious coding
- Clear documentation

Guidelines:
- Provide complete, runnable code
- Include helpful comments
- Explain your reasoning
- Point out potential issues
- Suggest improvements
- Be concise but thorough

When user asks you to fix/debug code:
- Identify the issue
- Provide corrected code
- Explain what was wrong
- Suggest prevention tips

When writing new code:
- Ask clarifying questions if needed
- Provide multiple approaches when relevant
- Include error handling
- Add helpful docstrings/comments"""

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    """Main application page"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == FORGE_PASSWORD:
            session['logged_in'] = True
            session.permanent = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """Handle chat requests to AI"""
    if not client:
        return jsonify({'error': 'API key not configured'}), 500
    
    data = request.json
    user_message = data.get('message', '')
    language = data.get('language', 'python')
    conversation_history = data.get('history', [])
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Add language context
    enhanced_message = f"[Language: {language}]\n\n{user_message}"
    
    # Build conversation
    messages = conversation_history + [
        {"role": "user", "content": enhanced_message}
    ]
    
    try:
        # Call Claude
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        
        assistant_message = response.content[0].text
        
        return jsonify({
            'response': assistant_message,
            'success': True
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/api/execute', methods=['POST'])
@login_required
def execute_code():
    """Execute Python or PowerShell code"""
    data = request.json
    code = data.get('code', '')
    language = data.get('language', 'python')
    
    if not code:
        return jsonify({'error': 'No code provided'}), 400
    
    try:
        if language == 'python':
            # Execute Python
            result = subprocess.run(
                [sys.executable, '-c', code],
                capture_output=True,
                text=True,
                timeout=30,
                cwd='/tmp'
            )
        elif language == 'powershell':
            # Execute PowerShell
            result = subprocess.run(
                ['pwsh', '-Command', code],
                capture_output=True,
                text=True,
                timeout=30
            )
        else:
            return jsonify({'error': 'Unsupported language'}), 400
        
        return jsonify({
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode,
            'success': result.returncode == 0
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'error': 'Execution timeout (30s limit)',
            'success': False
        }), 400
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'api_configured': client is not None
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
