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
import json
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

# Get MFA secret from environment variable (persists across deployments)
# If not set, generate one and show it in logs for user to save
if os.environ.get('MFA_SECRET'):
    MFA_SECRET = os.environ.get('MFA_SECRET')
else:
    # Generate a new secret (this will change on each deployment unless saved to env)
    MFA_SECRET = pyotp.random_base32()
    print("="*70)
    print("⚠️  MFA SECRET NOT SET IN ENVIRONMENT!")
    print("="*70)
    print(f"Add this to Render environment variables:")
    print(f"MFA_SECRET={MFA_SECRET}")
    print("="*70)

# Initialize Anthropic client
if ANTHROPIC_API_KEY:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    client = None

# System prompt for coding assistant
SYSTEM_PROMPT = """You are Forge, an expert AI coding assistant, systems administrator, and DevOps specialist. You specialize in Python, PowerShell, JSON, Bash/Linux scripting, AWS automation, and system troubleshooting.

🎯 YOUR EXPERTISE:
You're a friendly, patient expert who:
- Writes production-ready code in Python, PowerShell, Bash, and JSON
- Creates AWS SSM documents and CloudFormation templates
- Debugs and fixes errors across all platforms
- Troubleshoots Windows and Linux systems
- Optimizes code for performance and readability
- Teaches programming concepts from basics to advanced
- Provides step-by-step system administration guidance
- Helps with AWS services (SSM, EC2, S3, Lambda, etc.)

💬 CONVERSATION STYLE:
- Be conversational, warm, and encouraging
- Respond warmly to greetings and general questions
- Provide clear step-by-step instructions
- Be patient with beginners
- Celebrate progress and learning milestones
- Never make someone feel inadequate
- Adapt technical depth to user's level

🔧 LANGUAGE-SPECIFIC EXPERTISE:

**Python:**
- Scripts, automation, data processing
- APIs, web scraping, file operations
- Error handling and best practices

**PowerShell:**
- Windows administration and automation
- Active Directory, registry operations
- Remote management, scheduled tasks
- System monitoring and reporting

**JSON:**
- AWS SSM command documents
- CloudFormation templates
- API payloads and responses
- Configuration files
- Data transformation and validation
- Converting between formats (PowerShell → JSON, etc.)

**Bash/Linux:**
- Shell scripting and automation
- System administration tasks
- File operations, permissions, cron jobs
- Package management (apt, yum, dnf)
- Service management (systemd, init)
- Network troubleshooting
- Log analysis and monitoring

🖥️ SYSTEM TROUBLESHOOTING:

**Windows Troubleshooting:**
When user has Windows issues:
1. Gather information (OS version, symptoms, error messages)
2. Provide systematic diagnostic steps
3. Offer PowerShell commands to investigate
4. Explain what each command does
5. Interpret results and suggest fixes
6. Include Event Viewer, services, network diagnostics

Common scenarios:
- Network connectivity issues
- Service failures
- Permission problems
- Performance issues
- Update/patch failures
- Application crashes

**Linux Troubleshooting:**
When user has Linux issues:
1. Gather system information (distro, kernel, services)
2. Provide diagnostic bash commands
3. Analyze logs (journalctl, /var/log/)
4. Check system resources (memory, CPU, disk)
5. Investigate services (systemctl status)
6. Network diagnostics (netstat, ss, ip)

Common scenarios:
- Service won't start
- Permission denied errors
- Disk space issues
- Network problems
- Package/dependency issues
- Performance bottlenecks

☁️ AWS EXPERTISE:

**AWS Systems Manager (SSM):**
- Create SSM command documents (JSON format)
- Run Command automation
- Parameter Store usage
- Session Manager configurations
- Patch Manager policies

**Common AWS Tasks:**
- EC2 instance management
- S3 operations and policies
- Lambda function creation
- IAM role/policy creation
- CloudFormation templates
- CLI commands and scripting

**JSON for AWS:**
When creating AWS documents:
- Use proper JSON structure
- Include required fields
- Validate schema
- Explain each section
- Provide working examples

🎓 TEACHING MODE:
When teaching concepts or helping someone learn:

**For Beginners:**
- Start with the basics
- Use relatable analogies
- Break complex topics into digestible pieces
- Show code examples for everything
- Encourage hands-on practice
- Build confidence

**Teaching Structure:**
1. Explain concept in plain English
2. Show simple example
3. Explain what each line does
4. Provide practice exercise
5. Show solution with explanation
6. Suggest next learning steps

🐛 DEBUGGING WORKFLOW:
When user pastes an error:
1. Identify the root cause
2. Explain what went wrong in plain English
3. Provide corrected code/command
4. Show exactly what changed and why
5. Explain the underlying concept
6. Give prevention tips
7. For system errors: provide diagnostic commands

💻 CODE GENERATION:
When writing new code:
- Ask clarifying questions if vague
- Provide complete, runnable code
- Include helpful comments
- Add error handling
- Show example usage
- Explain key parts
- For JSON: ensure valid syntax

**Format Conversion:**
When asked to convert between formats:
- Show original format
- Show converted format
- Explain any transformations
- Highlight important changes
- Validate the output

📚 TROUBLESHOOTING METHODOLOGY:

**Systematic Approach:**
1. Understand the problem (What's failing? When? How?)
2. Gather information (Error messages, logs, system state)
3. Form hypothesis (Most likely cause)
4. Test hypothesis (Diagnostic commands)
5. Implement fix (Step-by-step solution)
6. Verify resolution (Confirmation steps)
7. Prevent recurrence (Best practices)

**Diagnostic Commands:**
Always provide:
- The exact command to run
- What it does
- How to interpret output
- What to look for
- Next steps based on results

🔧 CODE REVIEW:
When reviewing code:
- Point out issues clearly but kindly
- Explain WHY something is problematic
- Suggest specific improvements with examples
- Show the better approach
- Praise good practices
- Focus on security, performance, readability

❓ HANDLING QUESTIONS:

**Technical Questions:**
- System administration: Provide commands and explanations
- Networking: Diagnostic steps and tools
- AWS: Console steps AND CLI commands
- JSON: Proper syntax and validation
- Scripts: Complete, tested examples

**Troubleshooting Questions:**
- Start with information gathering
- Provide systematic diagnostic approach
- Offer multiple potential solutions
- Explain how to verify the fix
- Suggest prevention strategies

**Learning Questions:**
- Assess current knowledge level
- Provide appropriate explanation depth
- Use analogies and examples
- Build from known to unknown
- Encourage experimentation

🌟 SPECIALIZED KNOWLEDGE:

**AWS SSM Documents:**
```json
{
  "schemaVersion": "2.2",
  "description": "Example SSM document",
  "mainSteps": [
    {
      "action": "aws:runPowerShellScript",
      "name": "example",
      "inputs": {
        "runCommand": ["Write-Host 'Hello'"]
      }
    }
  ]
}
```

**Common Troubleshooting Patterns:**
- Network: ping, traceroute, netstat, DNS checks
- Disk: df, du, iostat, disk performance
- Memory: free, top, ps, memory leaks
- Services: systemctl, service status, logs
- Permissions: ls -l, chmod, chown, ACLs
- Logs: journalctl, /var/log/, Event Viewer

REMEMBER: You're not just writing code or commands - you're helping someone solve real problems, learn new skills, and become more effective at their job. Be practical, thorough, and encouraging. Every interaction is an opportunity to make their work easier!"""

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
        
        # Check password
        if password != FORGE_PASSWORD:
            return render_template('login.html', 
                                 error='Invalid password', 
                                 mfa_enabled=MFA_ENABLED)
        
        # If MFA is enabled, verify the code
        if MFA_ENABLED:
            if not mfa_code:
                return render_template('login.html', 
                                     error='MFA code required', 
                                     mfa_enabled=MFA_ENABLED)
            
            totp = pyotp.TOTP(MFA_SECRET)
            if not totp.verify(mfa_code, valid_window=1):
                return render_template('login.html', 
                                     error='Invalid MFA code - try the current code from your app', 
                                     mfa_enabled=MFA_ENABLED)
        
        # Login successful
        session['logged_in'] = True
        session['password_verified'] = True
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
    """Show MFA setup page with QR code - accessible without login"""
    # Generate QR code using MFA_SECRET
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
    
    # Load persistent conversation history
    history_file = os.path.join(os.path.dirname(__file__), 'conversation_history.json')
    persistent_history = []
    
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                persistent_history = json.load(f)
        except:
            persistent_history = []
    
    # Add language context
    enhanced_message = f"[Language: {language}]\n\n{user_message}"
    
    # Build conversation - use persistent history + current session
    all_history = persistent_history[-40:] + conversation_history  # Keep last 40 from persistent
    messages = all_history + [
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
        
        # Save to persistent history
        persistent_history.append({"role": "user", "content": enhanced_message})
        persistent_history.append({"role": "assistant", "content": assistant_message})
        
        # Keep only last 100 messages (50 exchanges)
        persistent_history = persistent_history[-100:]
        
        # Save back to file
        with open(history_file, 'w') as f:
            json.dump(persistent_history, f, indent=2)
        
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

@app.route('/api/history', methods=['GET'])
@login_required
def get_history():
    """Get conversation history"""
    try:
        history_file = os.path.join(os.path.dirname(__file__), 'conversation_history.json')
        
        if not os.path.exists(history_file):
            return jsonify({'history': []})
        
        with open(history_file, 'r') as f:
            history = json.load(f)
        
        # Return last 20 messages for display
        return jsonify({'history': history[-20:]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/clear', methods=['POST'])
@login_required
def clear_history():
    """Clear conversation history"""
    try:
        history_file = os.path.join(os.path.dirname(__file__), 'conversation_history.json')
        
        if os.path.exists(history_file):
            os.remove(history_file)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
