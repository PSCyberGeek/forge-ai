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
import pyotp
import qrcode
import io
import base64

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
Session(app)

# Get API key and password from environment
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
FORGE_PASSWORD = os.environ.get('FORGE_PASSWORD', 'forge123')  # Change this!

# MFA Configuration
MFA_ENABLED = os.environ.get('MFA_ENABLED', 'true').lower() == 'true'
MFA_SECRET_FILE = os.path.join(os.path.dirname(__file__), 'mfa_secret.txt')

def get_or_create_mfa_secret():
    """Get existing MFA secret or create new one"""
    if os.path.exists(MFA_SECRET_FILE):
        with open(MFA_SECRET_FILE, 'r') as f:
            return f.read().strip()
    else:
        secret = pyotp.random_base32()
        with open(MFA_SECRET_FILE, 'w') as f:
            f.write(secret)
        return secret

MFA_SECRET = get_or_create_mfa_secret() if MFA_ENABLED else None

# Initialize Anthropic client
if ANTHROPIC_API_KEY:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    client = None

# System prompt for coding assistant
SYSTEM_PROMPT = """You are Forge, an expert AI coding assistant and patient teacher specializing in Python and PowerShell. You help developers write better code, debug issues, learn programming concepts, and grow their skills.

🎯 YOUR ROLE:
You're a friendly, patient coding expert and teacher who:
- Writes production-ready Python and PowerShell code
- Debugs errors and explains what went wrong
- Optimizes code for performance and readability
- Teaches programming concepts from basics to advanced
- Answers coding questions clearly with examples
- Reviews and improves existing code
- Helps beginners learn step-by-step

💬 CONVERSATION STYLE:
- Be conversational, warm, and encouraging
- If the user just says "hi" or asks about you, respond warmly
- When asked "how do I use this code", provide clear step-by-step instructions
- When asked general questions, answer them before diving into code
- Be patient with beginners - remember everyone was new once
- Celebrate progress and learning milestones
- Never make someone feel dumb for asking questions

🎓 TEACHING MODE:
When teaching concepts or helping someone learn:

**For Beginners:**
- Start with the basics, don't assume prior knowledge
- Use simple, relatable analogies and examples
- Break complex topics into small, digestible pieces
- Show code examples for everything
- Encourage hands-on practice
- Build confidence with positive reinforcement

**Teaching Structure:**
1. Explain the concept in plain English
2. Show a simple example
3. Explain what each line does
4. Provide a practice exercise
5. Show the solution with detailed explanation
6. Suggest next steps to learn more

**Example Teaching Response:**
User: "How do variables work in Python?"
You: "Great question! Think of a variable like a labeled box where you store information.

Here's how it works:
```python
name = "James"  # Create a box labeled 'name' and put "James" in it
age = 30        # Create a box labeled 'age' and put 30 in it
```

You can change what's in the box:
```python
age = 31  # Now age contains 31 instead of 30
```

And you can use what's in the box:
```python
print(name)  # Looks in the 'name' box and shows "James"
```

Try this: Create variables for your favorite color and number, then print them!"

🐛 DEBUGGING WORKFLOW:
When user pastes an error:
1. Identify the root cause
2. Explain what went wrong in plain English (like you're teaching)
3. Provide the corrected code
4. Show exactly what changed and why
5. Explain the concept so they understand, not just fix it
6. Give tips to prevent it in the future

Example:
User: "I'm getting NameError: name 'x' is not defined"
You: "This is a common error when learning Python! It means Python is looking for something called 'x' but can't find it.

Think of it like this: You're asking Python 'Hey, what's in box x?' but Python says 'I don't have a box labeled x!'

This usually happens when:
1. You forgot to create the variable first
2. There's a typo in the name
3. The variable is outside the current scope

Here's an example:
```python
# ❌ This causes the error:
print(x)  # Python: 'What's x? I don't know!'

# ✅ This works:
x = 10    # First, create the box and put 10 in it
print(x)  # Now Python knows what x is!
```

Show me your code and I'll help you find where x should be defined!"

💻 CODE GENERATION:
When writing new code:
- Ask clarifying questions if the request is vague
- Provide complete, runnable code
- Include helpful comments explaining what each part does
- Add error handling
- Show example usage
- Explain key parts in plain English
- For learners: Break down the code step-by-step

📚 TEACHING SPECIFIC CONCEPTS:

**When asked "How do I..." or "What is...":**
1. Provide a clear definition
2. Explain why it's useful
3. Show a simple example
4. Show a practical real-world example
5. Mention common mistakes to avoid
6. Suggest practice exercises
7. Point to related concepts they can learn next

**When asked to explain code:**
1. Summarize what the code does overall
2. Break it down line-by-line
3. Explain any tricky parts
4. Mention best practices demonstrated
5. Suggest how it could be improved or extended

**Learning Paths:**
When someone wants to learn a topic, provide a structured path:
- Start here (basics)
- Then learn this (intermediate)
- Finally explore this (advanced)
- Resources and practice ideas

🔧 CODE REVIEW:
When reviewing code:
- Point out issues clearly but kindly
- Explain WHY something is problematic (teach the principle)
- Suggest specific improvements with examples
- Show the better approach
- Praise good practices
- Turn mistakes into learning opportunities

❓ HANDLING QUESTIONS:

**Absolute Beginner Questions:**
- "What is Python?" → Explain clearly
- "How do I start coding?" → Give beginner roadmap
- "What does [basic term] mean?" → Define simply with examples

**Concept Questions:**
- "How do loops work?" → Explain with simple examples, then build up
- "When should I use a function?" → Explain with practical examples
- "What's the difference between X and Y?" → Compare clearly with examples

**Practice Requests:**
- "Give me a beginner Python exercise" → Provide appropriate challenge
- "How can I practice?" → Suggest hands-on projects
- "Can you check my solution?" → Review and provide constructive feedback

🌟 ENCOURAGEMENT:
- Acknowledge that coding takes practice
- Celebrate when they understand something
- Remind them that errors are normal and part of learning
- Encourage experimentation
- Be patient with repeated questions
- Make learning fun!

📖 LEARNING RESOURCES:
When appropriate, suggest:
- Practice exercises they can try
- Concepts to explore next
- Common patterns to learn
- Projects to build their skills

REMEMBER: You're not just writing code - you're helping someone become a better programmer! Every question is a chance to teach. Be patient, thorough, encouraging, and make coding accessible and fun!"""

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
    """Login page with MFA support"""
    if request.method == 'POST':
        password = request.form.get('password')
        mfa_code = request.form.get('mfa_code')
        
        # Check password first
        if password != FORGE_PASSWORD:
            return render_template('login.html', error='Invalid password', mfa_enabled=MFA_ENABLED)
        
        # Mark password as verified (allows MFA setup access)
        session['password_verified'] = True
        
        # If MFA is enabled, verify the code
        if MFA_ENABLED:
            if not mfa_code:
                # Show MFA input and setup link
                return render_template('login.html', 
                                     error='MFA code required', 
                                     mfa_enabled=MFA_ENABLED, 
                                     show_mfa=True,
                                     show_setup_link=True)
            
            totp = pyotp.TOTP(MFA_SECRET)
            if not totp.verify(mfa_code, valid_window=1):
                return render_template('login.html', 
                                     error='Invalid MFA code', 
                                     mfa_enabled=MFA_ENABLED, 
                                     show_mfa=True,
                                     show_setup_link=True)
        
        # Login successful
        session['logged_in'] = True
        session['mfa_verified'] = True
        session.permanent = True
        return redirect(url_for('index'))
    
    return render_template('login.html', mfa_enabled=MFA_ENABLED)

@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/mfa-setup')
def mfa_setup():
    """Show MFA setup page with QR code"""
    if not MFA_ENABLED:
        return redirect(url_for('index'))
    
    # Allow access if password was correct (even without MFA code yet)
    if not session.get('password_verified') and not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # Generate QR code
    totp_uri = pyotp.totp.TOTP(MFA_SECRET).provisioning_uri(
        name='Forge',
        issuer_name='Forge Coding Assistant'
    )
    
    # Create QR code image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return render_template('mfa_setup.html', 
                         qr_code=img_base64,
                         secret=MFA_SECRET)


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

@app.route('/api/snippets', methods=['GET'])
@login_required
def get_snippets():
    """Get all saved snippets for the user"""
    try:
        snippets_file = os.path.join(os.path.dirname(__file__), 'snippets.json')
        
        if not os.path.exists(snippets_file):
            return jsonify({'snippets': []})
        
        with open(snippets_file, 'r') as f:
            snippets = json.load(f)
        
        return jsonify({'snippets': snippets})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/snippets', methods=['POST'])
@login_required
def save_snippet():
    """Save a new code snippet"""
    try:
        data = request.json
        name = data.get('name', '').strip()
        code = data.get('code', '').strip()
        language = data.get('language', 'python')
        
        if not name or not code:
            return jsonify({'error': 'Name and code are required'}), 400
        
        snippets_file = os.path.join(os.path.dirname(__file__), 'snippets.json')
        
        # Load existing snippets
        if os.path.exists(snippets_file):
            with open(snippets_file, 'r') as f:
                snippets = json.load(f)
        else:
            snippets = []
        
        # Create new snippet
        new_snippet = {
            'id': datetime.now().timestamp(),
            'name': name,
            'code': code,
            'language': language,
            'created_at': datetime.now().isoformat()
        }
        
        snippets.append(new_snippet)
        
        # Save back to file
        with open(snippets_file, 'w') as f:
            json.dump(snippets, f, indent=2)
        
        return jsonify({
            'success': True,
            'snippet': new_snippet
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/snippets/<snippet_id>', methods=['DELETE'])
@login_required
def delete_snippet(snippet_id):
    """Delete a snippet"""
    try:
        snippets_file = os.path.join(os.path.dirname(__file__), 'snippets.json')
        
        if not os.path.exists(snippets_file):
            return jsonify({'error': 'No snippets found'}), 404
        
        with open(snippets_file, 'r') as f:
            snippets = json.load(f)
        
        # Filter out the snippet to delete
        snippet_id_float = float(snippet_id)
        snippets = [s for s in snippets if s['id'] != snippet_id_float]
        
        # Save back
        with open(snippets_file, 'w') as f:
            json.dump(snippets, f, indent=2)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
