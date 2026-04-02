import json
import requests
import os

class ResumeOptimizer:
    """Handle resume optimization using OpenAI API directly with requests"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/chat/completions"
    
    def optimize_resume(self, resume_text, job_description):
        """Optimize resume based on job description"""
        
        prompt = self._create_optimization_prompt(resume_text, job_description)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert ATS (Applicant Tracking System) resume optimizer. "
                               "Your task is to tailor resumes to match job descriptions perfectly. "
                               "Always respond with valid JSON only. Do not include any other text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Try to parse JSON response
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If response isn't valid JSON, create a structured response
                return {
                    "optimized_resume": content,
                    "ats_score": 75,
                    "matched_keywords": [],
                    "missing_keywords": [],
                    "improvements": "Resume has been optimized",
                    "optimization_tips": ["Review the optimized content"]
                }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def _create_optimization_prompt(self, resume_text, job_description):
        """Create the optimization prompt"""
        
        # Truncate text if too long
        max_length = 4000
        if len(resume_text) > max_length:
            resume_text = resume_text[:max_length] + "..."
        if len(job_description) > 2000:
            job_description = job_description[:2000] + "..."
        
        return f"""
You are optimizing a resume for ATS (Applicant Tracking System) compatibility.

**JOB DESCRIPTION:**
{job_description}

**ORIGINAL RESUME:**
{resume_text}

**TASK:**
Tailor this resume to maximize ATS score while keeping all information truthful.

**REQUIREMENTS:**
1. Extract key skills and requirements from the job description
2. Rewrite the professional summary to highlight matching qualifications
3. Enhance bullet points with relevant keywords from the job description
4. Add missing relevant skills (only if the candidate actually has them)
5. Keep the same basic structure but optimize content
6. Maintain truthful information - don't add false experience
7. Use ATS-friendly formatting (no tables, columns, or graphics)

**OUTPUT FORMAT (JSON only, no other text):**
{{
  "optimized_resume": "The complete optimized resume text",
  "ats_score": 85,
  "matched_keywords": ["keyword1", "keyword2"],
  "missing_keywords": ["keyword3", "keyword4"],
  "improvements": "Summary of key changes made",
  "optimization_tips": ["tip1", "tip2"]
}}

Return ONLY valid JSON. No other text.
"""

    def analyze_resume(self, resume_text):
        """Analyze resume without optimization (fallback)"""
        return {
            "word_count": len(resume_text.split()),
            "sections_found": self._detect_sections(resume_text),
            "suggestions": [
                "Add more quantifiable achievements",
                "Use action verbs at the start of bullet points",
                "Include relevant keywords from job descriptions"
            ],
            "current_score": 50
        }
    
    def _detect_sections(self, text):
        """Detect common resume sections"""
        sections = []
        section_keywords = {
            'summary': ['summary', 'profile', 'about'],
            'experience': ['experience', 'work', 'employment'],
            'education': ['education', 'academic'],
            'skills': ['skills', 'technologies', 'competencies'],
            'projects': ['projects', 'portfolio']
        }
        
        text_lower = text.lower()
        for section, keywords in section_keywords.items():
            if any(kw in text_lower for kw in keywords):
                sections.append(section)
        
        return sections