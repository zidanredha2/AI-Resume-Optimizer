import os
import json
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import docx
import requests
import PyPDF2
from io import BytesIO
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'docx', 'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# DeepSeek Configuration
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

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
        raise Exception(f"Failed to extract text from DOCX: {str(e)}")

def extract_text_from_pdf(filepath):
    """Extract text from PDF file"""
    try:
        text = []
        with open(filepath, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text.strip():
                    text.append(page_text)
        return '\n'.join(text)
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

def extract_text_from_file(filepath, filename):
    """Extract text based on file type"""
    if filename.lower().endswith('.docx'):
        return extract_text_from_docx(filepath)
    elif filename.lower().endswith('.pdf'):
        return extract_text_from_pdf(filepath)
    else:
        raise Exception("Unsupported file format")

def calculate_ats_score(resume_text, job_description):
    """Calculate ATS score for a resume against job description"""
    job_keywords = extract_keywords_advanced(job_description)
    resume_keywords = extract_keywords_advanced(resume_text)
    
    if not job_keywords:
        return 50
    
    # Calculate match percentage
    job_keywords_lower = [k.lower() for k in job_keywords]
    resume_keywords_lower = [k.lower() for k in resume_keywords]
    
    matched = sum(1 for kw in job_keywords_lower if kw in resume_keywords_lower)
    score = int((matched / len(job_keywords)) * 100)
    
    # Bonus for metrics and action verbs
    has_metrics = bool(re.search(r'\d+%|\$\d+|\d+\s*(percent|increase|decrease|improve|reduce)', resume_text, re.I))
    action_verbs = ['led', 'developed', 'created', 'implemented', 'designed', 'built', 'managed', 'achieved', 'delivered']
    action_count = sum(1 for verb in action_verbs if re.search(rf'\b{verb}\b', resume_text.lower()))
    
    if has_metrics:
        score += 10
    if action_count >= 3:
        score += 5
    
    return min(95, score)

def get_ats_warning(before_score, after_score, matched_keywords, missing_keywords):
    """Generate warning message based on ATS score"""
    if after_score >= 80:
        return {
            "type": "success",
            "message": "✅ Your resume has a strong chance of passing ATS filters!",
            "recommendation": "Proceed with confidence. Your resume is well-tailored to this position.",
            "action_needed": False
        }
    elif after_score >= 60:
        return {
            "type": "warning",
            "message": "⚠️ Your resume has a moderate chance of passing ATS filters.",
            "recommendation": f"Consider adding these {len(missing_keywords)} missing keywords and gaining experience in: {', '.join(missing_keywords[:5])}",
            "action_needed": True
        }
    elif after_score >= 40:
        return {
            "type": "error",
            "message": "🔴 Your resume has a low chance of passing ATS filters.",
            "recommendation": f"Your resume is missing {len(missing_keywords)} critical keywords. Consider upskilling in: {', '.join(missing_keywords[:7])}. Review the job requirements carefully.",
            "action_needed": True
        }
    else:
        return {
            "type": "critical",
            "message": "❗ Your resume is unlikely to pass ATS screening.",
            "recommendation": f"Your skills don't match this role well. Missing {len(missing_keywords)} key requirements including: {', '.join(missing_keywords[:8])}. Consider gaining experience in these areas before applying, or target different roles that match your current skills.",
            "action_needed": True
        }

def call_deepseek_api(prompt):
    """Call DeepSeek API for resume optimization"""
    if not DEEPSEEK_API_KEY:
        return None
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system", 
                "content": "You are an expert ATS resume optimizer. COMPLETELY REWRITE the resume to match the job description. Always respond with valid JSON only."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 4000
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        try:
            return json.loads(content)
        except:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except:
                    pass
            return None
    except Exception as e:
        print(f"DeepSeek API error: {e}")
        return None

def optimize_without_ai(resume_text, job_description):
    """Advanced fallback optimization without AI"""
    # Extract keywords
    job_keywords = extract_keywords_advanced(job_description)
    resume_keywords = extract_keywords_advanced(resume_text)
    
    # Calculate BEFORE score
    before_score = calculate_ats_score(resume_text, job_description)
    
    # Find missing keywords
    missing_keywords = [kw for kw in job_keywords if kw.lower() not in [rk.lower() for rk in resume_keywords]]
    matched_keywords = [kw for kw in resume_keywords if kw.lower() in [jk.lower() for jk in job_keywords]]
    
    # Create completely rewritten optimized resume
    optimized = create_completely_rewritten_resume(resume_text, job_description, job_keywords, missing_keywords)
    
    # Calculate AFTER score
    after_score = calculate_ats_score(optimized, job_description)
    score_improvement = after_score - before_score
    
    # Get ATS warning
    ats_warning = get_ats_warning(before_score, after_score, matched_keywords, missing_keywords)
    
    # Generate improvements summary
    improvements = f"""📊 Score Improvement: {before_score}% → {after_score}% (+{score_improvement}%)

✓ Completely rewritten professional summary tailored to job requirements
✓ Added {len(matched_keywords)} relevant keywords from job description
✓ Rewrote bullet points with action verbs and metrics
✓ Reorganized skills to prioritize job requirements"""

    optimization_tips = [
        "Add specific metrics (%, $, numbers) to your achievements",
        "Use strong action verbs at the start of each bullet point",
        "Quantify your impact (e.g., 'Increased sales by 40%')",
        "Tailor your professional summary for each application",
        "Keep your resume to 1 page for best ATS results"
    ]
    
    return {
        "optimized_resume": optimized,
        "ats_score": after_score,
        "before_score": before_score,
        "score_improvement": score_improvement,
        "matched_keywords": matched_keywords[:15],
        "missing_keywords": missing_keywords[:10],
        "improvements": improvements,
        "optimization_tips": optimization_tips,
        "ats_warning": ats_warning
    }

def extract_keywords_advanced(text):
    """Extract keywords from text using advanced patterns"""
    keywords = []
    
    tech_patterns = {
        'Languages': r'\b(Python|Java|JavaScript|TypeScript|Go|Rust|C\+\+|C#|Ruby|PHP|Swift|Kotlin|Scala)\b',
        'Frontend': r'\b(React|Angular|Vue|Next\.js|Nuxt|Svelte|HTML5|CSS3|SCSS|Tailwind|Bootstrap)\b',
        'Backend': r'\b(Node\.js|Django|Flask|Spring Boot|Express|FastAPI|Laravel|Rails|ASP\.NET)\b',
        'Cloud': r'\b(AWS|Azure|GCP|Lambda|EC2|S3|RDS|CloudFormation|Terraform|CloudFront)\b',
        'DevOps': r'\b(Docker|Kubernetes|Jenkins|GitLab CI|GitHub Actions|CircleCI|Ansible|Prometheus|Grafana)\b',
        'Database': r'\b(SQL|PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|DynamoDB|Cassandra|Oracle)\b',
        'Data Science': r'\b(Machine Learning|Deep Learning|AI|TensorFlow|PyTorch|Pandas|NumPy|Scikit-learn|LLM)\b',
        'Methodologies': r'\b(Agile|Scrum|Kanban|SAFe|Lean|Waterfall|JIRA|Confluence)\b',
        'Soft Skills': r'\b(Leadership|Communication|Teamwork|Problem Solving|Critical Thinking|Project Management)\b'
    }
    
    for category, pattern in tech_patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        keywords.extend([m for m in matches if len(m) > 1])
    
    cap_words = re.findall(r'\b[A-Z][a-z]+(?:[+.#][A-Za-z0-9]+)?\b', text)
    for word in cap_words:
        if len(word) > 2 and word.lower() not in ['The', 'And', 'For', 'With', 'This', 'That']:
            keywords.append(word)
    
    unique_keywords = list(dict.fromkeys(keywords))[:30]
    
    return unique_keywords if unique_keywords else ['Python', 'JavaScript', 'React', 'AWS', 'SQL']

def create_completely_rewritten_resume(resume_text, job_description, job_keywords, missing_keywords):
    """Create a completely rewritten, tailored resume"""
    
    lines = resume_text.split('\n')
    optimized_parts = []
    
    # 1. Professional Summary
    optimized_parts.append("PROFESSIONAL SUMMARY")
    
    job_lower = job_description.lower()
    exp_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)', job_lower)
    experience = f"{exp_match.group(1)}+ years" if exp_match else "proven"
    
    top_skills = job_keywords[:4] if job_keywords else ["relevant technologies"]
    skills_str = ', '.join(top_skills)
    
    summary = f"Results-driven professional with {experience} of experience in {skills_str}. "
    summary += f"Demonstrated success in delivering high-impact solutions and driving business growth. "
    summary += f"Expertise spans {skills_str} with strong focus on achieving measurable results."
    
    optimized_parts.append(summary)
    optimized_parts.append("")
    
    # 2. Core Competencies
    optimized_parts.append("CORE COMPETENCIES")
    
    prioritized_skills = []
    for keyword in job_keywords[:10]:
        if keyword not in prioritized_skills:
            prioritized_skills.append(keyword)
    
    common_skills = ['Team Leadership', 'Project Management', 'Problem Solving', 'Communication']
    for skill in common_skills:
        if skill not in prioritized_skills:
            prioritized_skills.append(skill)
    
    optimized_parts.append(', '.join(prioritized_skills[:12]))
    optimized_parts.append("")
    
    # 3. Professional Experience
    optimized_parts.append("PROFESSIONAL EXPERIENCE")
    
    action_verbs = ['Led', 'Developed', 'Architected', 'Implemented', 'Optimized', 
                    'Spearheaded', 'Achieved', 'Delivered', 'Launched', 'Managed',
                    'Created', 'Designed', 'Built', 'Improved', 'Increased', 'Reduced']
    
    metrics = [
        "resulting in 25% increase in efficiency",
        "leading to $500K annual savings",
        "improving performance by 40%",
        "reducing processing time by 60%",
        "achieving 99.9% uptime",
        "increasing user satisfaction by 35%"
    ]
    
    for i, keyword in enumerate(job_keywords[:5]):
        verb = action_verbs[i % len(action_verbs)]
        metric = metrics[i % len(metrics)]
        optimized_parts.append(f"• {verb} {keyword} initiatives, {metric}")
    
    optimized_parts.append("")
    
    # 4. Education
    optimized_parts.append("EDUCATION")
    
    education_found = False
    in_education = False
    for line in lines:
        if 'education' in line.lower():
            in_education = True
            continue
        if in_education and line.strip() and len(line) < 100:
            optimized_parts.append(line)
            education_found = True
            break
    
    if not education_found:
        optimized_parts.append("Bachelor's Degree in Computer Science or related field")
    
    optimized_parts.append("")
    
    return '\n'.join(optimized_parts)

@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    return jsonify({
        "status": "healthy",
        "message": "AI Resume Optimizer is running",
        "deepseek_configured": bool(DEEPSEEK_API_KEY),
        "supported_formats": ["docx", "pdf"],
        "endpoints": ["/health", "/api/optimize", "/api/analyze"]
    })

@app.route('/api/optimize', methods=['POST', 'OPTIONS'])
def optimize_resume():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    file_path = None
    
    try:
        if 'resume' not in request.files:
            return jsonify({"error": "No resume file provided"}), 400
        
        file = request.files['resume']
        job_description = request.form.get('job_description', '')
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not job_description:
            return jsonify({"error": "Job description is required"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Only .docx and .pdf files are allowed"}), 400
        
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        resume_text = extract_text_from_file(file_path, filename)
        
        if not resume_text.strip():
            return jsonify({"error": "Could not extract text from resume"}), 400
        
        # Calculate BEFORE score
        before_score = calculate_ats_score(resume_text, job_description)
        
        # Try DeepSeek API
        if DEEPSEEK_API_KEY:
            try:
                prompt = f"""
                You are an expert resume writer. COMPLETELY REWRITE this resume to match the job description.

                JOB DESCRIPTION:
                {job_description[:2000]}

                ORIGINAL RESUME:
                {resume_text[:3000]}

                REQUIREMENTS:
                1. COMPLETELY REWRITE the professional summary
                2. Rewrite EACH bullet point with metrics
                3. Use strong action verbs
                4. Reorder skills to prioritize job requirements

                Return JSON:
                {{
                  "optimized_resume": "complete rewritten resume",
                  "matched_keywords": ["keyword1", "keyword2"],
                  "missing_keywords": [],
                  "improvements": "summary of changes",
                  "optimization_tips": ["tip1", "tip2"]
                }}
                """
                
                result = call_deepseek_api(prompt)
                if result and result.get('optimized_resume'):
                    after_score = calculate_ats_score(result['optimized_resume'], job_description)
                    score_improvement = after_score - before_score
                    
                    # Get matched and missing keywords
                    job_keywords = extract_keywords_advanced(job_description)
                    resume_keywords_after = extract_keywords_advanced(result['optimized_resume'])
                    
                    matched_keywords = result.get('matched_keywords', [])
                    if not matched_keywords:
                        matched_keywords = [kw for kw in job_keywords if kw.lower() in [rk.lower() for rk in resume_keywords_after]]
                    
                    missing_keywords = result.get('missing_keywords', [])
                    if not missing_keywords:
                        missing_keywords = [kw for kw in job_keywords if kw.lower() not in [rk.lower() for rk in resume_keywords_after]]
                    
                    # Get ATS warning
                    ats_warning = get_ats_warning(before_score, after_score, matched_keywords, missing_keywords)
                    
                    return jsonify({
                        "success": True,
                        "ats_score": after_score,
                        "before_score": before_score,
                        "score_improvement": score_improvement,
                        "optimized_resume": result.get('optimized_resume'),
                        "matched_keywords": matched_keywords[:15],
                        "missing_keywords": missing_keywords[:10],
                        "improvements": result.get('improvements', f'Score improved from {before_score}% to {after_score}%'),
                        "optimization_tips": result.get('optimization_tips', [
                            "Add specific metrics to your achievements",
                            "Use action verbs at the start of bullet points",
                            "Quantify your impact with numbers"
                        ]),
                        "ats_warning": ats_warning
                    }), 200
            except Exception as e:
                print(f"DeepSeek API failed: {e}")
        
        # Fallback optimization
        result = optimize_without_ai(resume_text, job_description)
        
        return jsonify({
            "success": True,
            **result
        }), 200
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
        
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze_resume():
    """Analyze resume endpoint with PDF support"""
    
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
            return jsonify({"error": "Only .docx and .pdf files are allowed"}), 400
        
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        resume_text = extract_text_from_file(file_path, filename)
        
        word_count = len(resume_text.split())
        sections = []
        
        section_keywords = {
            'summary': ['summary', 'profile', 'objective'],
            'experience': ['experience', 'work', 'employment'],
            'education': ['education', 'academic', 'university'],
            'skills': ['skills', 'technologies', 'competencies']
        }
        
        for section, keywords in section_keywords.items():
            if any(kw in resume_text.lower() for kw in keywords):
                sections.append(section)
        
        has_metrics = bool(re.search(r'\d+%|\$\d+|\d+\s*(percent|increase|decrease)', resume_text, re.I))
        
        suggestions = []
        if word_count < 300:
            suggestions.append("Add more details to your experience section")
        if word_count > 800:
            suggestions.append("Resume is too long - consider condensing to 1-2 pages")
        if 'summary' not in sections:
            suggestions.append("Add a professional summary section")
        if 'skills' not in sections:
            suggestions.append("Add a skills section with relevant technologies")
        if not has_metrics:
            suggestions.append("Add quantifiable achievements with specific numbers")
        
        score = 50
        if sections:
            score += len(sections) * 10
        if has_metrics:
            score += 15
        if 300 <= word_count <= 600:
            score += 10
        
        return jsonify({
            "success": True,
            "analysis": {
                "word_count": word_count,
                "sections_found": sections,
                "suggestions": suggestions[:5],
                "current_score": min(95, score)
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
    print("AI RESUME OPTIMIZER BACKEND (with Before/After Scores & Warnings)")
    print("="*60)
    print(f"Server running on: http://localhost:5000")
    print(f"DeepSeek AI: {'✓ Configured' if DEEPSEEK_API_KEY else '✗ Not configured'}")
    print(f"Supported formats: .docx, .pdf")
    print("\nATS Scoring:")
    print("  • BEFORE score = Original resume against job description")
    print("  • AFTER score = Optimized resume against job description")
    print("  • Score improvement shows optimization effectiveness")
    print("  • Warnings for low ATS scores with skill recommendations")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)