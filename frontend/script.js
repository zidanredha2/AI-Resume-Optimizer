// API Configuration
const API_BASE_URL = 'http://localhost:5000';
const API_ENDPOINTS = {
    optimize: `${API_BASE_URL}/api/optimize`,
    analyze: `${API_BASE_URL}/api/analyze`,
    keywords: `${API_BASE_URL}/api/keywords`,
    health: `${API_BASE_URL}/health`
};

// Global variables
let currentResumeFile = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('Application initialized');
    initParticles();
    initEventListeners();
    checkBackendHealth();
});

// Event Listeners Setup
function initEventListeners() {
    // File upload handlers
    const dropZone = document.getElementById('dropZone');
    const resumeInput = document.getElementById('resumeInput');
    
    if (dropZone) {
        dropZone.addEventListener('click', () => resumeInput?.click());
        dropZone.addEventListener('dragover', handleDragOver);
        dropZone.addEventListener('dragleave', handleDragLeave);
        dropZone.addEventListener('drop', handleDrop);
    }
    
    if (resumeInput) {
        resumeInput.addEventListener('change', handleFileSelect);
    }
    
    // Buttons
    const tailorBtn = document.getElementById('tailorBtn');
    const copyBtn = document.getElementById('copyBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const newResumeBtn = document.getElementById('newResumeBtn');
    
    if (tailorBtn) tailorBtn.addEventListener('click', handleOptimize);
    if (copyBtn) copyBtn.addEventListener('click', handleCopy);
    if (downloadBtn) downloadBtn.addEventListener('click', handleDownload);
    if (newResumeBtn) newResumeBtn.addEventListener('click', resetForm);
}

// File Handling
function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.currentTarget.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    const dropZone = e.currentTarget;
    dropZone.classList.remove('drag-over');
    
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.docx')) {
        handleFileSelect({ target: { files: [file] } });
    } else {
        showError('Please upload a .docx file');
    }
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    if (!file.name.endsWith('.docx')) {
        showError('Only .docx files are supported');
        return;
    }
    
    currentResumeFile = file;
    
    const fileName = document.getElementById('fileName');
    if (fileName) {
        fileName.textContent = `📄 ${file.name}`;
        fileName.classList.remove('hidden');
    }
    
    console.log('File selected:', file.name);
}

// Main Optimization Function
async function handleOptimize() {
    console.log('Starting resume optimization...');
    
    // Validate inputs
    if (!currentResumeFile) {
        showError('Please upload a resume file');
        return;
    }
    
    const jobDescription = document.getElementById('jobDescription')?.value;
    if (!jobDescription || !jobDescription.trim()) {
        showError('Please paste a job description');
        return;
    }
    
    // Show loading overlay
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) loadingOverlay.classList.remove('hidden');
    
    // Prepare form data
    const formData = new FormData();
    formData.append('resume', currentResumeFile);
    formData.append('job_description', jobDescription);
    
    try {
        console.log('Sending request to backend...');
        
        const response = await fetch(API_ENDPOINTS.optimize, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || data.message || 'Optimization failed');
        }
        
        console.log('Optimization successful:', data);
        displayResults(data);
        
    } catch (error) {
        console.error('Optimization error:', error);
        showError(error.message || 'Failed to optimize resume. Please try again.');
    } finally {
        if (loadingOverlay) loadingOverlay.classList.add('hidden');
    }
}

// Display Results
function displayResults(data) {
    console.log('Displaying results...');
    
    // Show results container
    const resultsDiv = document.getElementById('results');
    if (resultsDiv) resultsDiv.classList.remove('hidden');
    
    // Update ATS score
    const atsScore = document.getElementById('atsScore');
    const scoreBar = document.getElementById('scoreBar');
    
    if (atsScore) {
        animateNumber(atsScore, 0, data.ats_score, 1000);
    }
    if (scoreBar) {
        scoreBar.style.width = `${data.ats_score}%`;
    }
    
    // Update keyword counts
    const keywordsCount = document.getElementById('keywordsCount');
    const missingCount = document.getElementById('missingCount');
    
    if (keywordsCount) {
        keywordsCount.textContent = data.matched_keywords?.length || 0;
    }
    if (missingCount) {
        missingCount.textContent = data.missing_keywords?.length || 0;
    }
    
    // Display optimized resume
    const tailoredResume = document.getElementById('tailoredResume');
    if (tailoredResume && data.optimized_resume) {
        tailoredResume.textContent = data.optimized_resume;
    }
    
    // Display improvements summary
    const changesSummary = document.getElementById('changesSummary');
    if (changesSummary && data.improvements) {
        changesSummary.innerHTML = `<strong>✨ Optimization Summary:</strong><br>${data.improvements}`;
    }
    
    // Display keywords
    const keywordsList = document.getElementById('keywordsList');
    if (keywordsList) {
        keywordsList.innerHTML = '';
        
        // Show matched keywords
        if (data.matched_keywords && data.matched_keywords.length > 0) {
            const matchedTitle = document.createElement('div');
            matchedTitle.innerHTML = '<strong>✅ Matched Keywords:</strong>';
            keywordsList.appendChild(matchedTitle);
            
            data.matched_keywords.forEach(keyword => {
                const badge = createKeywordBadge(keyword, 'matched');
                keywordsList.appendChild(badge);
            });
        }
        
        // Show missing keywords
        if (data.missing_keywords && data.missing_keywords.length > 0) {
            const missingTitle = document.createElement('div');
            missingTitle.innerHTML = '<strong>⚠️ Missing Keywords to Add:</strong>';
            missingTitle.style.marginTop = '1rem';
            keywordsList.appendChild(missingTitle);
            
            data.missing_keywords.forEach(keyword => {
                const badge = createKeywordBadge(keyword, 'missing');
                keywordsList.appendChild(badge);
            });
        }
        
        // Show optimization tips
        if (data.optimization_tips && data.optimization_tips.length > 0) {
            const tipsTitle = document.createElement('div');
            tipsTitle.innerHTML = '<strong>💡 Optimization Tips:</strong>';
            tipsTitle.style.marginTop = '1rem';
            keywordsList.appendChild(tipsTitle);
            
            data.optimization_tips.forEach(tip => {
                const tipElement = document.createElement('div');
                tipElement.className = 'tip-item';
                tipElement.textContent = `• ${tip}`;
                tipElement.style.marginTop = '0.5rem';
                tipElement.style.fontSize = '0.875rem';
                tipElement.style.color = 'rgba(255,255,255,0.8)';
                keywordsList.appendChild(tipElement);
            });
        }
    }
    
    // Scroll to results
    resultsDiv?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    showSuccess(`Resume optimized! ATS Score: ${data.ats_score}%`);
}

// Helper Functions
function createKeywordBadge(keyword, type) {
    const badge = document.createElement('span');
    badge.className = `keyword-badge ${type === 'missing' ? 'missing' : ''}`;
    badge.textContent = keyword;
    return badge;
}

function animateNumber(element, start, end, duration) {
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const current = Math.floor(start + (end - start) * progress);
        element.textContent = current;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

async function handleCopy() {
    const tailoredResume = document.getElementById('tailoredResume');
    if (!tailoredResume?.textContent) {
        showError('No resume content to copy');
        return;
    }
    
    try {
        await navigator.clipboard.writeText(tailoredResume.textContent);
        showSuccess('Resume copied to clipboard!');
    } catch (error) {
        showError('Failed to copy to clipboard');
    }
}

async function handleDownload() {
    const tailoredResume = document.getElementById('tailoredResume');
    if (!tailoredResume?.textContent) {
        showError('No resume content to download');
        return;
    }
    
    try {
        const blob = new Blob([tailoredResume.textContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'optimized_resume.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showSuccess('Resume downloaded successfully!');
    } catch (error) {
        showError('Failed to download resume');
    }
}

function resetForm() {
    currentResumeFile = null;
    
    const fileName = document.getElementById('fileName');
    const jobDescription = document.getElementById('jobDescription');
    const resumeInput = document.getElementById('resumeInput');
    const results = document.getElementById('results');
    const scoreBar = document.getElementById('scoreBar');
    
    if (fileName) fileName.classList.add('hidden');
    if (jobDescription) jobDescription.value = '';
    if (resumeInput) resumeInput.value = '';
    if (results) results.classList.add('hidden');
    if (scoreBar) scoreBar.style.width = '0%';
    
    window.scrollTo({ top: 0, behavior: 'smooth' });
    showSuccess('Ready to process a new resume!');
}

async function checkBackendHealth() {
    try {
        const response = await fetch(API_ENDPOINTS.health);
        const data = await response.json();
        
        if (response.ok) {
            console.log('Backend is healthy:', data);
            if (!data.openai_configured) {
                showError('OpenAI API key not configured. Please check backend .env file');
            }
        } else {
            showError('Backend server is not responding properly');
        }
    } catch (error) {
        console.error('Backend health check failed:', error);
        showError('Cannot connect to backend server. Please make sure it\'s running on port 5000');
    }
}

// Particle Animation (keep your existing particle code)
function initParticles() {
    // ... your existing particle animation code ...
    console.log('Particles initialized');
}

// Toast notifications
function showError(message) {
    showToast(message, 'error');
}

function showSuccess(message) {
    showToast(message, 'success');
}

function showToast(message, type) {
    const toast = document.createElement('div');
    toast.className = `${type}-toast`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'error' ? 'linear-gradient(135deg, #ef4444, #dc2626)' : 'linear-gradient(135deg, #10b981, #059669)'};
        backdrop-filter: blur(10px);
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        z-index: 2000;
        animation: slideIn 0.3s ease;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        color: white;
        font-weight: 500;
        max-width: 400px;
    `;
    
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}