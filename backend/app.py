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
import random

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

# Common words to exclude from keyword extraction
COMMON_WORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us', 'is', 'was', 'are', 'been', 'has', 'had', 'were', 'their', 'they', 'your', 'you', 'develop', 'rich', 'applications'
}

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
                "content": "You are an expert ATS resume optimizer. COMPLETELY REWRITE the resume to match the job description. Always respond with valid JSON only. IMPORTANT: Use different action verbs for each bullet point and don't repeat the same skills in summary and core competencies."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "temperature": 0.8,
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
    
    # Create completely rewritten optimized resume (with varied content)
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
✓ Rewrote bullet points with varied action verbs and metrics
✓ Reorganized skills to prioritize job requirements"""

    optimization_tips = [
        "Add specific metrics (%, $, numbers) to your achievements",
        "Use varied action verbs at the start of each bullet point",
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
    """Extract ONLY relevant technical keywords from text - no common words"""
    keywords = []
    
    # Technical skills patterns (only these will be extracted)
    tech_patterns = {
        'Programming Languages': r'\b(Python|Java|JavaScript|TypeScript|Go|Rust|C\+\+|C#|Ruby|PHP|Swift|Kotlin|Scala|Dart|R|MATLAB|Perl|Haskell|Clojure|Elixir)\b',
        'Frontend': r'\b(React|Angular|Vue|Next\.js|Nuxt|Svelte|HTML5|CSS3|SCSS|SASS|Tailwind|Bootstrap|Material UI|jQuery|Webpack|Vite)\b',
        'Backend': r'\b(Node\.js|Django|Flask|Spring Boot|Express|FastAPI|Laravel|Rails|ASP\.NET|NestJS|Koa|Phoenix|Gin)\b',
        'Cloud': r'\b(AWS|Azure|GCP|Lambda|EC2|S3|RDS|CloudFormation|Terraform|CloudFront|Route53|VPC|IAM|CloudWatch)\b',
        'DevOps': r'\b(Docker|Kubernetes|Jenkins|GitLab CI|GitHub Actions|CircleCI|Ansible|Puppet|Chef|Prometheus|Grafana|ELK|Splunk)\b',
        'Database': r'\b(SQL|PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|DynamoDB|Cassandra|Oracle|MariaDB|Firebase|Neo4j|InfluxDB)\b',
        'Data Science': r'\b(Machine Learning|Deep Learning|AI|Artificial Intelligence|TensorFlow|PyTorch|Pandas|NumPy|Scikit-learn|LLM|LangChain|Hugging Face|Keras|OpenCV|NLTK)\b',
        'Methodologies': r'\b(Agile|Scrum|Kanban|SAFe|Lean|Waterfall|JIRA|Confluence|Trello|Asana|Monday\.com)\b',
        'Soft Skills': r'\b(Leadership|Communication|Teamwork|Problem Solving|Critical Thinking|Project Management|Time Management|Mentoring)\b',
        'Certifications': r'\b(AWS Certified|Azure Certified|Google Cloud Certified|CISSP|PMP|CKA|CKAD|CCNA|CCNP|Security\+|Network\+|CompTIA)\b'
    }
    
    # Extract from technical patterns only
    for category, pattern in tech_patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            clean_match = match.strip()
            if len(clean_match) > 1 and clean_match.lower() not in COMMON_WORDS:
                keywords.append(clean_match)
    
    # Remove duplicates while preserving order
    unique_keywords = []
    for kw in keywords:
        if kw.lower() not in [uk.lower() for uk in unique_keywords]:
            unique_keywords.append(kw)
    
    # Filter out any remaining common words or very short words
    filtered_keywords = [kw for kw in unique_keywords if len(kw) > 2 and kw.lower() not in COMMON_WORDS]
    
    return filtered_keywords[:30] if filtered_keywords else ['Python', 'JavaScript', 'React', 'AWS', 'SQL']

def create_completely_rewritten_resume(resume_text, job_description, job_keywords, missing_keywords):
    """Create a completely rewritten, tailored resume with varied content"""
    
    lines = resume_text.split('\n')
    optimized_parts = []
    
    # 1. Professional Summary (using different skills than core competencies)
    optimized_parts.append("PROFESSIONAL SUMMARY")
    
    job_lower = job_description.lower()
    exp_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)', job_lower)
    experience = f"{exp_match.group(1)}+ years" if exp_match else "proven"
    
    # Use different skills for summary (first 3-4 keywords)
    summary_skills = job_keywords[:3] if len(job_keywords) >= 3 else job_keywords
    if len(summary_skills) >= 2:
        skills_str = f"{summary_skills[0]} and {summary_skills[1]}"
    elif summary_skills:
        skills_str = summary_skills[0]
    else:
        skills_str = "relevant technologies"
    
    summary = f"Results-driven {summary_skills[0] if summary_skills else 'technology'} professional with {experience} of experience. "
    summary += f"Demonstrated success in delivering scalable solutions and driving business growth through {skills_str}. "
    summary += f"Passionate about building efficient systems and leading cross-functional teams to achieve exceptional results."
    
    optimized_parts.append(summary)
    optimized_parts.append("")
    
    # 2. Core Competencies (use remaining skills, different from summary)
    optimized_parts.append("CORE COMPETENCIES")
    
    # Use different skills than summary
    if len(job_keywords) > 3:
        competency_skills = job_keywords[2:12]  # Skip first 2 used in summary
    else:
        competency_skills = job_keywords.copy()
    
    # Add diverse skill categories
    all_skills = set(competency_skills)
    
    # Add varied skill types if missing
    skill_categories = {
        'Cloud': ['AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes'],
        'Database': ['PostgreSQL', 'MongoDB', 'Redis', 'MySQL'],
        'DevOps': ['CI/CD', 'Jenkins', 'Git', 'Terraform'],
        'Soft Skills': ['Team Leadership', 'Agile', 'Scrum', 'Project Management']
    }
    
    # Add diverse skills if we have less than 8
    if len(all_skills) < 8:
        for category, skills in skill_categories.items():
            for skill in skills:
                if skill not in all_skills and len(all_skills) < 12:
                    all_skills.add(skill)
    
    # Convert to list and limit
    skills_list = list(all_skills)[:12]
    optimized_parts.append(', '.join(skills_list))
    optimized_parts.append("")
    
    # 3. Professional Experience (varied action verbs)
    optimized_parts.append("PROFESSIONAL EXPERIENCE")
    
    # Extensive list of varied action verbs
    action_verbs = [
        'Led', 'Architected', 'Orchestrated', 'Pioneered', 'Transformed',
        'Engineered', 'Revolutionized', 'Spearheaded', 'Championed', 'Drove',
        'Delivered', 'Launched', 'Deployed', 'Integrated', 'Streamlined',
        'Optimized', 'Accelerated', 'Enhanced', 'Strengthened', 'Bolstered',
        'Negotiated', 'Collaborated', 'Mentored', 'Coached', 'Influenced'
    ]
    
    # Different metrics for variety
    metrics = [
        "resulting in 40% improvement in system performance",
        "leading to $750K annual cost reduction",
        "increasing user engagement by 55%",
        "reducing deployment time by 70%",
        "achieving 99.99% system availability",
        "boosting customer satisfaction by 45%",
        "cutting processing time by 50%",
        "generating $1.2M in additional revenue",
        "reducing technical debt by 35%",
        "improving team velocity by 60%"
    ]
    
    # Create varied bullet points
    used_verbs = set()
    used_metrics = set()
    used_skills = set()
    
    for i, keyword in enumerate(job_keywords[:6]):
        # Select unused verb
        available_verbs = [v for v in action_verbs if v not in used_verbs]
        verb = available_verbs[i % len(available_verbs)] if available_verbs else action_verbs[i % len(action_verbs)]
        used_verbs.add(verb)
        
        # Select unused metric
        available_metrics = [m for m in metrics if m not in used_metrics]
        metric = available_metrics[i % len(available_metrics)] if available_metrics else metrics[i % len(metrics)]
        used_metrics.add(metric)
        
        # Select unused skill for this bullet
        available_skills = [k for k in job_keywords if k not in used_skills]
        if available_skills:
            skill = available_skills[i % len(available_skills)]
            used_skills.add(skill)
        else:
            skill = keyword
        
        # Create varied bullet point structure
        bullet_templates = [
            f"• {verb} enterprise-wide {skill} implementation, {metric}",
            f"• {verb} cross-functional teams to deliver {skill} solutions, {metric}",
            f"• {verb} {skill} architecture modernization initiative, {metric}",
            f"• {verb} strategic {skill} migration project, {metric}"
        ]
        
        bullet = bullet_templates[i % len(bullet_templates)]
        optimized_parts.append(bullet)
    
    optimized_parts.append("")
    optimized_parts.append("• Mentored junior developers and conducted code reviews to maintain high quality standards")
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
    
    # 5. Certifications (if applicable)
    cert_keywords = ['certified', 'certification', 'aws', 'azure', 'google', 'scrum', 'agile']
    has_certs = any(cert in job_description.lower() for cert in cert_keywords)
    
    if has_certs:
        optimized_parts.append("CERTIFICATIONS")
        certs = []
        if 'aws' in job_description.lower():
            certs.append("AWS Certified Solutions Architect")
        if 'azure' in job_description.lower():
            certs.append("Microsoft Azure Certified")
        if 'scrum' in job_description.lower() or 'agile' in job_description.lower():
            certs.append("Certified Scrum Master (CSM)")
        if 'python' in job_description.lower():
            certs.append("Python Institute Certification")
        
        for cert in certs[:3]:
            optimized_parts.append(f"• {cert}")
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

                CRITICAL REQUIREMENTS:
                1. Use DIFFERENT action verbs for each bullet point (don't repeat "Led" or "Developed")
                2. Don't repeat the same skills in Professional Summary and Core Competencies
                3. Make each bullet point unique and impactful
                4. Add specific metrics and results

                JOB DESCRIPTION:
                {job_description[:2000]}

                ORIGINAL RESUME:
                {resume_text[:3000]}

                Return JSON:
                {{
                  "optimized_resume": "complete rewritten resume with varied content",
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
                    
                    job_keywords = extract_keywords_advanced(job_description)
                    resume_keywords_after = extract_keywords_advanced(result['optimized_resume'])
                    
                    matched_keywords = result.get('matched_keywords', [])
                    if not matched_keywords:
                        matched_keywords = [kw for kw in job_keywords if kw.lower() in [rk.lower() for rk in resume_keywords_after]]
                    
                    missing_keywords = result.get('missing_keywords', [])
                    if not missing_keywords:
                        missing_keywords = [kw for kw in job_keywords if kw.lower() not in [rk.lower() for rk in resume_keywords_after]]
                    
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
                            "Use varied action verbs for each bullet point",
                            "Don't repeat skills across sections",
                            "Add specific metrics to your achievements"
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
    print("AI RESUME OPTIMIZER BACKEND (Varied Content Generation)")
    print("="*60)
    print(f"Server running on: http://localhost:5000")
    print(f"DeepSeek AI: {'✓ Configured' if DEEPSEEK_API_KEY else '✗ Not configured'}")
    print(f"Supported formats: .docx, .pdf")
    print("\nImprovements:")
    print("  • Different action verbs for each bullet point")
    print("  • No skill repetition across sections")
    print("  • Varied metrics and achievements")
    print("  • More natural, professional language")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)