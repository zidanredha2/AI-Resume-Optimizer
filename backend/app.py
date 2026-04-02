import os
import json
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import docx
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Allow all CORS requests

# Configuration
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'docx'}
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_docx(filepath):
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(filepath)
        text = []
        for para in doc.paragraphs:
            if para.text.strip():
                text.append(para.text)
        return '\n'.join(text)
    except Exception as e:
        raise Exception(f"Failed to extract text: {str(e)}")

def call_openai_api(prompt):
    """Call OpenAI API using requests"""
    if not OPENAI_API_KEY:
        return None
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are an expert resume optimizer. Respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Try to parse JSON
        try:
            return json.loads(content)
        except:
            # If not valid JSON, return structured fallback
            return {
                "optimized_resume": content,
                "ats_score": 75,
                "matched_keywords": [],
                "missing_keywords": [],
                "improvements": "Resume has been optimized",
                "optimization_tips": ["Review the optimized content"]
            }
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return None

def optimize_without_ai(resume_text, job_description):
    """Fallback optimization without AI"""
    # Extract keywords
    job_keywords = extract_keywords(job_description)
    resume_keywords = extract_keywords(resume_text)
    
    # Find missing keywords
    missing_keywords = [kw for kw in job_keywords if kw not in resume_keywords]
    
    # Calculate ATS score
    if job_keywords:
        ats_score = int((len(set(resume_keywords) & set(job_keywords)) / len(job_keywords)) * 100)
    else:
        ats_score = 70
    
    # Create optimized resume
    optimized = create_optimized_resume(resume_text, missing_keywords)
    
    return {
        "optimized_resume": optimized,
        "ats_score": ats_score,
        "matched_keywords": list(set(resume_keywords) & set(job_keywords)),
        "missing_keywords": missing_keywords[:10],
        "improvements": f"Added {len(missing_keywords)} missing keywords to improve ATS score",
        "optimization_tips": [
            "Add more specific technical skills from the job description",
            "Use action verbs to start each bullet point",
            "Quantify your achievements with numbers and percentages",
            "Include a professional summary at the top"
        ]
    }

def extract_keywords(text):
    """Extract common keywords from text"""
    common_keywords = [
        'Python', 'Java', 'JavaScript', 'TypeScript', 'React', 'Angular', 'Vue', 'Node.js',
        'Django', 'Flask', 'Spring', 'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes',
        'Jenkins', 'Git', 'CI/CD', 'SQL', 'MongoDB', 'PostgreSQL', 'MySQL', 'Redis',
        'Machine Learning', 'AI', 'Deep Learning', 'TensorFlow', 'PyTorch', 'Pandas',
        'Data Science', 'Analytics', 'Agile', 'Scrum', 'Kanban', 'JIRA', 'Leadership',
        'Project Management', 'Communication', 'Teamwork', 'Problem Solving'
    ]
    
    found = []
    text_lower = text.lower()
    
    for keyword in common_keywords:
        if keyword.lower() in text_lower:
            found.append(keyword)
    
    return found

def create_optimized_resume(resume_text, missing_keywords):
    """Create optimized version of resume"""
    lines = resume_text.split('\n')
    optimized_lines = []
    skills_added = False
    
    for line in lines:
        optimized_lines.append(line)
        
        # Add missing keywords to skills section
        if 'skills' in line.lower() and missing_keywords and not skills_added:
            optimized_lines.append(f"Additional Skills: {', '.join(missing_keywords[:5])}")
            skills_added = True
    
    # Add summary if missing keywords exist
    if missing_keywords and not any('summary' in l.lower() or 'profile' in l.lower() for l in optimized_lines):
        optimized_lines.insert(0, "PROFESSIONAL SUMMARY")
        optimized_lines.insert(1, f"Experienced professional with expertise in {', '.join(missing_keywords[:3])}. "
                                 f"Proven track record of delivering high-quality results.")
        optimized_lines.insert(2, "")
    
    return '\n'.join(optimized_lines)

@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    """Health check endpoint"""
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    return jsonify({
        "status": "healthy",
        "message": "AI Resume Optimizer is running",
        "openai_configured": bool(OPENAI_API_KEY),
        "endpoints": ["/health", "/api/optimize", "/api/analyze"]
    })

@app.route('/api/optimize', methods=['POST', 'OPTIONS'])
def optimize_resume():
    """Optimize resume endpoint"""
    
    # Handle preflight CORS request
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    file_path = None
    
    try:
        # Check if file is present
        if 'resume' not in request.files:
            return jsonify({"error": "No resume file provided"}), 400
        
        file = request.files['resume']
        job_description = request.form.get('job_description', '')
        
        # Validate inputs
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not job_description:
            return jsonify({"error": "Job description is required"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Only .docx files are allowed"}), 400
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Extract text from resume
        resume_text = extract_text_from_docx(file_path)
        
        if not resume_text.strip():
            return jsonify({"error": "Could not extract text from resume"}), 400
        
        # Try AI optimization if API key is available
        if OPENAI_API_KEY:
            try:
                # Create prompt
                prompt = f"""
                Optimize this resume for the job description. Return JSON only.

                Job Description: {job_description[:1500]}

                Resume: {resume_text[:3000]}

                Return JSON: {{"optimized_resume": "full text", "ats_score": 0-100, "matched_keywords": [], "missing_keywords": [], "improvements": "", "optimization_tips": []}}
                """
                
                result = call_openai_api(prompt)
                if result:
                    return jsonify({
                        "success": True,
                        **result
                    }), 200
            except Exception as e:
                print(f"AI optimization failed, using fallback: {e}")
        
        # Fallback to keyword-based optimization
        result = optimize_without_ai(resume_text, job_description)
        
        return jsonify({
            "success": True,
            **result
        }), 200
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
        
    finally:
        # Clean up temporary file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze_resume():
    """Analyze resume endpoint"""
    
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    file_path = None
    
    try:
        if 'resume' not in request.files:
            return jsonify({"error": "No resume file provided"}), 400
        
        file = request.files['resume']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Only .docx files are allowed"}), 400
        
        # Save and process file
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Extract text
        resume_text = extract_text_from_docx(file_path)
        
        # Analyze
        word_count = len(resume_text.split())
        sections = []
        
        section_keywords = {
            'summary': ['summary', 'profile'],
            'experience': ['experience', 'work'],
            'education': ['education'],
            'skills': ['skills', 'technologies']
        }
        
        for section, keywords in section_keywords.items():
            if any(kw in resume_text.lower() for kw in keywords):
                sections.append(section)
        
        suggestions = []
        if word_count < 300:
            suggestions.append("Add more details to your experience section")
        if 'summary' not in sections:
            suggestions.append("Add a professional summary section")
        if 'skills' not in sections:
            suggestions.append("Add a skills section with relevant technologies")
        
        return jsonify({
            "success": True,
            "analysis": {
                "word_count": word_count,
                "sections_found": sections,
                "suggestions": suggestions,
                "current_score": 70 if sections else 50
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

if __name__ == '__main__':
    print("\n" + "="*60)
    print("AI RESUME OPTIMIZER BACKEND")
    print("="*60)
    print(f"Server running on: http://localhost:5000")
    print(f"Debug mode: ON")
    print(f"OpenAI: {'Configured' if OPENAI_API_KEY else 'Not configured (using fallback)'}")
    print(f"Max file size: 5MB")
    print("="*60)
    print("\nAvailable endpoints:")
    print("  GET  /health - Health check")
    print("  POST /api/optimize - Optimize resume")
    print("  POST /api/analyze - Analyze resume")
    print("\nTip: Add OPENAI_API_KEY to .env file for AI-powered optimization")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)