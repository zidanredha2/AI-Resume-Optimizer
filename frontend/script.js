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
let currentDownloadUrl = null;

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
    const browseBtn = document.querySelector('.browse-btn');
    
    // Update accepted file types to include PDF
    if (resumeInput) {
        resumeInput.setAttribute('accept', '.docx, .pdf');
    }
    
    // Browse button click handler
    if (browseBtn) {
        browseBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (resumeInput) {
                resumeInput.click();
            }
        });
    }
    
    // Drop zone click handler (but not on browse button)
    if (dropZone) {
        dropZone.addEventListener('click', (e) => {
            // Don't trigger if clicking on browse button
            if (!e.target.classList || !e.target.classList.contains('browse-btn')) {
                if (resumeInput) {
                    resumeInput.click();
                }
            }
        });
        
        dropZone.addEventListener('dragover', handleDragOver);
        dropZone.addEventListener('dragleave', handleDragLeave);
        dropZone.addEventListener('drop', handleDrop);
    }
    
    if (resumeInput) {
        resumeInput.addEventListener('change', handleFileSelect);
    }
    
    // Main Buttons
    const tailorBtn = document.getElementById('tailorBtn');
    const copyBtn = document.getElementById('copyBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const newResumeBtn = document.getElementById('newResumeBtn');
    
    if (tailorBtn) tailorBtn.addEventListener('click', handleOptimize);
    if (copyBtn) copyBtn.addEventListener('click', handleCopy);
    if (downloadBtn) downloadBtn.addEventListener('click', handleDownload);
    if (newResumeBtn) newResumeBtn.addEventListener('click', resetForm);
    
    // Navigation Buttons
    const homeLink = document.getElementById('homeLink');
    const featuresLink = document.getElementById('featuresLink');
    const pricingLink = document.getElementById('pricingLink');
    
    if (homeLink) {
        homeLink.addEventListener('click', (e) => {
            e.preventDefault();
            window.scrollTo({ top: 0, behavior: 'smooth' });
            showSuccess('Welcome to AI Resume Tailor!');
        });
    }
    
    if (featuresLink) {
        featuresLink.addEventListener('click', (e) => {
            e.preventDefault();
            const resultsSection = document.getElementById('results');
            const uploadSection = document.querySelector('.upload-container');
            if (resultsSection && !resultsSection.classList.contains('hidden')) {
                resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else if (uploadSection) {
                uploadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
            showInfo('✨ Features: ATS Optimization, Keyword Matching, Resume Tailoring, PDF/DOCX Support');
        });
    }
    
    if (pricingLink) {
        pricingLink.addEventListener('click', (e) => {
            e.preventDefault();
            showInfo('💎 Pricing: Free during beta! Premium features coming soon.');
        });
    }
}

// Clear all results function
function clearResults() {
    console.log('Clearing previous results...');
    
    // Hide results container
    const resultsDiv = document.getElementById('results');
    if (resultsDiv) {
        resultsDiv.classList.add('hidden');
    }
    
    // Reset ATS score display
    const atsScore = document.getElementById('atsScore');
    if (atsScore) {
        atsScore.textContent = '0';
        atsScore.innerHTML = '0%';
        atsScore.title = '';
    }
    
    // Reset score bar
    const scoreBar = document.getElementById('scoreBar');
    if (scoreBar) {
        scoreBar.style.width = '0%';
    }
    
    // Reset keyword counts
    const keywordsCount = document.getElementById('keywordsCount');
    const missingCount = document.getElementById('missingCount');
    if (keywordsCount) keywordsCount.textContent = '0';
    if (missingCount) missingCount.textContent = '0';
    
    // Clear optimized resume content
    const tailoredResume = document.getElementById('tailoredResume');
    if (tailoredResume) {
        tailoredResume.textContent = '';
    }
    
    // Clear improvements summary
    const changesSummary = document.getElementById('changesSummary');
    if (changesSummary) {
        changesSummary.innerHTML = '';
    }
    
    // Clear keywords list
    const keywordsList = document.getElementById('keywordsList');
    if (keywordsList) {
        keywordsList.innerHTML = '';
    }
    
    // Remove before score element if exists
    const beforeScore = document.querySelector('.before-score');
    if (beforeScore) beforeScore.remove();
    
    // Remove ATS warning if exists
    const atsWarning = document.getElementById('atsWarning');
    if (atsWarning) atsWarning.remove();
    
    // Remove ethics warning if exists
    const ethicsWarning = document.getElementById('ethicsWarning');
    if (ethicsWarning) ethicsWarning.remove();
    
    // Reset download URL
    currentDownloadUrl = null;
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
    if (file && (file.name.endsWith('.docx') || file.name.endsWith('.pdf'))) {
        handleFileSelect({ target: { files: [file] } });
    } else {
        showError('Please upload a .docx or .pdf file');
    }
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // Clear previous results when new file is selected
    clearResults();
    
    // Check for both docx and pdf
    if (!file.name.endsWith('.docx') && !file.name.endsWith('.pdf')) {
        showError('Only .docx and .pdf files are supported');
        return;
    }
    
    // Increased file size limit to 10MB for PDFs
    if (file.size > 10 * 1024 * 1024) {
        showError('File size must be less than 10MB');
        return;
    }
    
    currentResumeFile = file;
    
    const fileName = document.getElementById('fileName');
    if (fileName) {
        const fileIcon = file.name.endsWith('.pdf') ? '📕' : '📄';
        fileName.textContent = `${fileIcon} ${file.name}`;
        fileName.classList.remove('hidden');
        fileName.style.display = 'block';
    }
    
    // Update drop zone content to show success
    const dropZoneContent = document.querySelector('.drop-zone-content p');
    if (dropZoneContent) {
        const originalText = dropZoneContent.textContent;
        dropZoneContent.textContent = '✓ Resume uploaded successfully!';
        setTimeout(() => {
            dropZoneContent.textContent = originalText;
        }, 2000);
    }
    
    console.log('File selected:', file.name, 'Type:', file.type);
    showSuccess(`"${file.name}" uploaded successfully!`);
    
    // Auto-scroll to job description section
    const jobSection = document.querySelector('.jd-card');
    if (jobSection) {
        setTimeout(() => {
            jobSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 500);
    }
}

// Main Optimization Function
async function handleOptimize() {
    console.log('Starting resume optimization...');
    
    // Validate inputs
    if (!currentResumeFile) {
        showError('Please upload a resume file first');
        return;
    }
    
    const jobDescription = document.getElementById('jobDescription')?.value;
    if (!jobDescription || !jobDescription.trim()) {
        showError('Please paste a job description');
        return;
    }
    
    // Clear previous results before new optimization
    clearResults();
    
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
        showError(error.message || 'Failed to optimize resume. Please make sure the backend server is running.');
    } finally {
        if (loadingOverlay) loadingOverlay.classList.add('hidden');
    }
}

// Display Results
function displayResults(data) {
    console.log('Displaying results...');
    
    // Store download URL if available
    if (data.download_url) {
        currentDownloadUrl = `${API_BASE_URL}${data.download_url}`;
        console.log('Download URL:', currentDownloadUrl);
    } else {
        currentDownloadUrl = null;
    }
    
    // Show results container
    const resultsDiv = document.getElementById('results');
    if (resultsDiv) resultsDiv.classList.remove('hidden');
    
    // Update ATS score display with before/after
    const atsScore = document.getElementById('atsScore');
    const scoreBar = document.getElementById('scoreBar');
    
    if (atsScore && data.before_score !== undefined) {
        // Show improvement with animation
        const improvement = data.score_improvement;
        const arrow = improvement >= 0 ? '↑' : '↓';
        const color = improvement >= 0 ? '#10b981' : '#ef4444';
        
        atsScore.innerHTML = `${data.ats_score}%<span style="font-size: 0.75rem; display: block; color: ${color}; margin-top: 0.25rem;">${arrow} ${Math.abs(improvement)}%</span>`;
        
        // Add tooltip with before/after info
        atsScore.title = `Before: ${data.before_score}% | After: ${data.ats_score}% | Improvement: ${improvement >= 0 ? '+' : ''}${data.score_improvement}%`;
        
        // Also display before score
        const statCard = document.querySelector('.stat-card:first-child');
        if (statCard && !document.querySelector('.before-score')) {
            const beforeSpan = document.createElement('div');
            beforeSpan.className = 'before-score';
            beforeSpan.style.fontSize = '0.7rem';
            beforeSpan.style.color = 'rgba(255,255,255,0.6)';
            beforeSpan.style.marginTop = '0.25rem';
            beforeSpan.innerHTML = `Before: ${data.before_score}%`;
            statCard.appendChild(beforeSpan);
        }
    } else if (atsScore) {
        atsScore.textContent = `${data.ats_score}%`;
    }
    
    if (scoreBar) {
        setTimeout(() => {
            scoreBar.style.width = `${data.ats_score}%`;
        }, 100);
    }
    
    // Update keyword counts with animation
    const keywordsCount = document.getElementById('keywordsCount');
    const missingCount = document.getElementById('missingCount');
    
    if (keywordsCount) {
        animateNumber(keywordsCount, 0, data.matched_keywords?.length || 0, 1000);
    }
    if (missingCount) {
        animateNumber(missingCount, 0, data.missing_keywords?.length || 0, 1000);
    }
    
    // Display optimized resume
    const tailoredResume = document.getElementById('tailoredResume');
    if (tailoredResume && data.optimized_resume) {
        let formattedResume = data.optimized_resume;
        formattedResume = formattedResume.replace(/\n{3,}/g, '\n\n');
        tailoredResume.textContent = formattedResume;
    }
    
    // Display ATS Warning if present (after clearing previous)
    if (data.ats_warning) {
        const warning = data.ats_warning;
        const insightsCard = document.querySelector('.insights-card');
        
        // Remove existing warning first
        const existingWarning = document.getElementById('atsWarning');
        if (existingWarning) existingWarning.remove();
        
        const warningDiv = document.createElement('div');
        warningDiv.id = 'atsWarning';
        warningDiv.style.marginBottom = '1rem';
        warningDiv.style.padding = '1rem';
        warningDiv.style.borderRadius = '0.5rem';
        
        // Set colors based on warning type
        if (warning.type === 'success') {
            warningDiv.style.background = 'rgba(16, 185, 129, 0.2)';
            warningDiv.style.border = '1px solid rgba(16, 185, 129, 0.3)';
        } else if (warning.type === 'warning') {
            warningDiv.style.background = 'rgba(245, 158, 11, 0.2)';
            warningDiv.style.border = '1px solid rgba(245, 158, 11, 0.3)';
        } else if (warning.type === 'error') {
            warningDiv.style.background = 'rgba(239, 68, 68, 0.2)';
            warningDiv.style.border = '1px solid rgba(239, 68, 68, 0.3)';
        } else {
            warningDiv.style.background = 'rgba(139, 92, 246, 0.2)';
            warningDiv.style.border = '1px solid rgba(139, 92, 246, 0.3)';
        }
        
        warningDiv.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 0.5rem;">${warning.message}</div>
            <div style="font-size: 0.875rem; margin-bottom: 0.5rem;">💡 ${warning.recommendation}</div>
            ${warning.action_needed ? '<div style="font-size: 0.75rem; color: rgba(255,255,255,0.7); margin-top: 0.5rem;">⚠️ Action Required: Consider upskilling or targeting different roles</div>' : ''}
        `;
        
        // Insert at the top of insights card
        const insightsTitle = insightsCard.querySelector('h3');
        if (insightsTitle) {
            insightsTitle.insertAdjacentElement('afterend', warningDiv);
        } else {
            insightsCard.insertBefore(warningDiv, insightsCard.firstChild);
        }
    }
    
    // Add Ethics Warning Banner (remove old one first)
    const resultCard = document.querySelector('.result-card');
    const existingEthicsWarning = document.getElementById('ethicsWarning');
    if (existingEthicsWarning) existingEthicsWarning.remove();
    
    if (resultCard) {
        const ethicsWarningDiv = document.createElement('div');
        ethicsWarningDiv.id = 'ethicsWarning';
        ethicsWarningDiv.style.margin = '1rem 0 0 0';
        ethicsWarningDiv.style.padding = '1rem';
        ethicsWarningDiv.style.background = 'rgba(245, 158, 11, 0.15)';
        ethicsWarningDiv.style.borderLeft = '4px solid #f59e0b';
        ethicsWarningDiv.style.borderRadius = '0.5rem';
        ethicsWarningDiv.style.fontSize = '0.875rem';
        
        ethicsWarningDiv.innerHTML = `
            <div style="display: flex; align-items: flex-start; gap: 0.75rem;">
                <div style="font-size: 1.25rem;">⚖️</div>
                <div>
                    <strong style="color: #fbbf24;">Honesty & Integrity Notice</strong><br>
                    <span style="color: rgba(255,255,255,0.9); font-size: 0.8rem;">
                        Only include skills and keywords you <strong>truly possess</strong>. Dishonestly adding keywords 
                        you don't have may help pass automated filters but will lead to <strong>failed interviews</strong>, 
                        <strong>embarrassment</strong>, and <strong>damaged professional reputation</strong>. 
                        Recruiters will verify your claims during technical assessments.
                    </span>
                    <div style="margin-top: 0.5rem; font-size: 0.75rem; color: rgba(255,255,255,0.6);">
                        💡 <em>Focus on your genuine strengths and use this tool to present them effectively, not to deceive.</em>
                    </div>
                </div>
            </div>
        `;
        
        // Insert after the result header
        const resultHeader = resultCard.querySelector('.result-header');
        if (resultHeader) {
            resultHeader.insertAdjacentElement('afterend', ethicsWarningDiv);
        } else {
            resultCard.insertBefore(ethicsWarningDiv, resultCard.firstChild);
        }
    }
    
    // Display improvements summary
    const changesSummary = document.getElementById('changesSummary');
    if (changesSummary && data.improvements) {
        changesSummary.innerHTML = `<pre style="white-space: pre-wrap; font-family: inherit; margin: 0; line-height: 1.6;">${data.improvements}</pre>`;
    }
    
    // Display keywords and tips in separate sections
    const keywordsList = document.getElementById('keywordsList');
    if (keywordsList) {
        keywordsList.innerHTML = '';
        
        // Section 1: Matched Keywords with honesty note
        if (data.matched_keywords && data.matched_keywords.length > 0) {
            const matchedSection = document.createElement('div');
            matchedSection.className = 'keywords-section';
            matchedSection.style.marginBottom = '1.5rem';
            matchedSection.style.padding = '1rem';
            matchedSection.style.background = 'rgba(16, 185, 129, 0.1)';
            matchedSection.style.borderRadius = '0.5rem';
            matchedSection.style.borderLeft = '3px solid #10b981';
            
            const matchedTitle = document.createElement('div');
            matchedTitle.innerHTML = '<strong style="font-size: 1rem; color: #10b981;">✅ Keywords Found in Your Resume</strong>';
            matchedTitle.style.marginBottom = '0.75rem';
            matchedSection.appendChild(matchedTitle);
            
            const matchedContainer = document.createElement('div');
            matchedContainer.style.display = 'flex';
            matchedContainer.style.flexWrap = 'wrap';
            matchedContainer.style.gap = '0.5rem';
            
            data.matched_keywords.slice(0, 20).forEach(keyword => {
                const badge = createKeywordBadge(keyword, 'matched');
                matchedContainer.appendChild(badge);
            });
            matchedSection.appendChild(matchedContainer);
            
            // Add honesty reminder for matched keywords
            const honestyNote = document.createElement('div');
            honestyNote.style.marginTop = '0.75rem';
            honestyNote.style.fontSize = '0.7rem';
            honestyNote.style.color = 'rgba(16, 185, 129, 0.7)';
            honestyNote.style.fontStyle = 'italic';
            honestyNote.innerHTML = '✓ These keywords were found in your original resume - keep only what you genuinely know';
            matchedSection.appendChild(honestyNote);
            
            keywordsList.appendChild(matchedSection);
        }
        
        // Section 2: Missing Keywords with warning
        if (data.missing_keywords && data.missing_keywords.length > 0) {
            const missingSection = document.createElement('div');
            missingSection.className = 'keywords-section';
            missingSection.style.marginBottom = '1.5rem';
            missingSection.style.padding = '1rem';
            missingSection.style.background = 'rgba(239, 68, 68, 0.1)';
            missingSection.style.borderRadius = '0.5rem';
            missingSection.style.borderLeft = '3px solid #ef4444';
            
            const missingTitle = document.createElement('div');
            missingTitle.innerHTML = '<strong style="font-size: 1rem; color: #ef4444;">⚠️ Keywords Not Found (Do NOT Add Dishonestly)</strong>';
            missingTitle.style.marginBottom = '0.75rem';
            missingSection.appendChild(missingTitle);
            
            const missingContainer = document.createElement('div');
            missingContainer.style.display = 'flex';
            missingContainer.style.flexWrap = 'wrap';
            missingContainer.style.gap = '0.5rem';
            
            data.missing_keywords.forEach(keyword => {
                const badge = createKeywordBadge(keyword, 'missing');
                missingContainer.appendChild(badge);
            });
            missingSection.appendChild(missingContainer);
            
            // Strong warning about adding false keywords
            const warningNote = document.createElement('div');
            warningNote.style.marginTop = '0.75rem';
            warningNote.style.padding = '0.5rem';
            warningNote.style.background = 'rgba(239, 68, 68, 0.2)';
            warningNote.style.borderRadius = '0.375rem';
            warningNote.style.fontSize = '0.75rem';
            warningNote.style.color = '#fca5a5';
            warningNote.innerHTML = '⚠️ <strong>WARNING:</strong> Only add these keywords to your resume if you have <strong>actual experience</strong> with these skills. Adding false information will be discovered in interviews and can cost you the job offer or damage your professional reputation.';
            missingSection.appendChild(warningNote);
            
            keywordsList.appendChild(missingSection);
        }
        
        // Section 3: Optimization Tips with ethics reminder
        const ethicsTips = [
            "Be honest about your skill level - don't claim 'expert' if you're 'beginner'",
            "Use action verbs to describe what you actually accomplished, not what you wish you did",
            "Quantify achievements with real numbers, not inflated ones",
            "Tailor your resume by highlighting relevant genuine experience, not by adding false claims",
            "If you're missing key skills, consider online courses or projects to gain them honestly",
            "Remember: Getting an interview for a job you're unqualified for wastes everyone's time"
        ];
        
        const tipsSection = document.createElement('div');
        tipsSection.className = 'tips-section';
        tipsSection.style.marginBottom = '1rem';
        tipsSection.style.padding = '1rem';
        tipsSection.style.background = 'rgba(124, 58, 237, 0.1)';
        tipsSection.style.borderRadius = '0.5rem';
        tipsSection.style.borderLeft = '3px solid #7c3aed';
        
        const tipsTitle = document.createElement('div');
        tipsTitle.innerHTML = '<strong style="font-size: 1rem; color: #a78bfa;">💡 Ethical Optimization Tips</strong>';
        tipsTitle.style.marginBottom = '0.75rem';
        tipsSection.appendChild(tipsTitle);
        
        const tipsList = document.createElement('div');
        tipsList.style.display = 'flex';
        tipsList.style.flexDirection = 'column';
        tipsList.style.gap = '0.5rem';
        
        ethicsTips.forEach((tip, index) => {
            const tipElement = document.createElement('div');
            tipElement.className = 'tip-item';
            tipElement.innerHTML = `${index + 1}. ${tip}`;
            tipElement.style.padding = '0.5rem';
            tipElement.style.background = 'rgba(255, 255, 255, 0.05)';
            tipElement.style.borderRadius = '0.375rem';
            tipElement.style.fontSize = '0.875rem';
            tipElement.style.color = 'rgba(255, 255, 255, 0.9)';
            tipElement.style.lineHeight = '1.5';
            tipsList.appendChild(tipElement);
        });
        
        tipsSection.appendChild(tipsList);
        keywordsList.appendChild(tipsSection);
    }
    
    // Scroll to results
    resultsDiv?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    // Show success message with improvement info
    if (data.before_score !== undefined) {
        showSuccess(`Resume optimized! Score: ${data.before_score}% → ${data.ats_score}% (+${data.score_improvement}%)`);
    } else {
        showSuccess(`Resume optimized! ATS Score: ${data.ats_score}%`);
    }
}

// Helper Functions
function createKeywordBadge(keyword, type) {
    const badge = document.createElement('span');
    badge.className = `keyword-badge ${type === 'missing' ? 'missing' : ''}`;
    badge.textContent = keyword;
    
    // Add styling for better visibility
    badge.style.padding = '0.375rem 0.875rem';
    badge.style.borderRadius = '2rem';
    badge.style.fontSize = '0.75rem';
    badge.style.fontWeight = '500';
    badge.style.display = 'inline-block';
    badge.style.transition = 'all 0.2s ease';
    
    if (type === 'missing') {
        badge.style.background = 'rgba(239, 68, 68, 0.2)';
        badge.style.border = '1px solid rgba(239, 68, 68, 0.3)';
        badge.style.color = '#fca5a5';
    } else {
        badge.style.background = 'rgba(16, 185, 129, 0.2)';
        badge.style.border = '1px solid rgba(16, 185, 129, 0.3)';
        badge.style.color = '#6ee7b7';
    }
    
    // Add hover effect
    badge.addEventListener('mouseenter', () => {
        badge.style.transform = 'translateY(-2px)';
        badge.style.cursor = 'pointer';
    });
    
    badge.addEventListener('mouseleave', () => {
        badge.style.transform = 'translateY(0)';
    });
    
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
        
        // Visual feedback on copy button
        const copyBtn = document.getElementById('copyBtn');
        if (copyBtn) {
            const originalHTML = copyBtn.innerHTML;
            copyBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M16.6667 5L7.5 14.1667L3.33333 10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg> Copied!';
            setTimeout(() => {
                copyBtn.innerHTML = originalHTML;
            }, 2000);
        }
    } catch (error) {
        console.error('Copy error:', error);
        showError('Failed to copy to clipboard');
    }
}

async function handleDownload() {
    // Check if we have a download URL from the backend (for DOCX)
    if (currentDownloadUrl) {
        try {
            const link = document.createElement('a');
            link.href = currentDownloadUrl;
            link.download = '';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            showSuccess('Optimized resume downloaded as DOCX!');
            return;
        } catch (error) {
            console.error('DOCX download error:', error);
            // Fall through to TXT download
        }
    }
    
    // Fallback to TXT download
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
        
        showSuccess('Resume downloaded as TXT file!');
    } catch (error) {
        console.error('Download error:', error);
        showError('Failed to download resume');
    }
}

function resetForm() {
    currentResumeFile = null;
    currentDownloadUrl = null;
    
    const fileName = document.getElementById('fileName');
    const jobDescription = document.getElementById('jobDescription');
    const resumeInput = document.getElementById('resumeInput');
    const dropZoneContent = document.querySelector('.drop-zone-content p');
    
    if (fileName) {
        fileName.classList.add('hidden');
        fileName.style.display = 'none';
    }
    if (jobDescription) jobDescription.value = '';
    if (resumeInput) resumeInput.value = '';
    if (dropZoneContent) {
        dropZoneContent.textContent = 'Drag & drop your resume here';
    }
    
    // Clear all results
    clearResults();
    
    window.scrollTo({ top: 0, behavior: 'smooth' });
    showSuccess('Ready to process a new resume!');
}

async function checkBackendHealth() {
    try {
        const response = await fetch(API_ENDPOINTS.health);
        const data = await response.json();
        
        if (response.ok) {
            console.log('Backend is healthy:', data);
            if (data.deepseek_configured) {
                showSuccess('✅ Backend connected! DeepSeek AI ready for optimization');
            } else if (data.openai_configured) {
                showSuccess('✅ Backend connected! AI optimization ready');
            } else {
                showInfo('Backend connected! Using smart keyword optimization');
            }
            
            // Show supported formats
            if (data.supported_formats) {
                console.log('Supported formats:', data.supported_formats);
            }
        } else {
            showError('Backend server is not responding properly');
        }
    } catch (error) {
        console.error('Backend health check failed:', error);
        showError('Cannot connect to backend server. Please make sure it\'s running on port 5000');
    }
}

// Particle Animation
function initParticles() {
    const canvas = document.getElementById('particleCanvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    let particles = [];
    let animationFrameId;
    
    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    
    class Particle {
        constructor() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 2 + 0.5;
            this.speedX = (Math.random() - 0.5) * 0.5;
            this.speedY = (Math.random() - 0.5) * 0.5;
            this.opacity = Math.random() * 0.5 + 0.2;
        }
        
        update() {
            this.x += this.speedX;
            this.y += this.speedY;
            
            if (this.x < 0) this.x = canvas.width;
            if (this.x > canvas.width) this.x = 0;
            if (this.y < 0) this.y = canvas.height;
            if (this.y > canvas.height) this.y = 0;
        }
        
        draw() {
            if (!ctx) return;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(0, 212, 255, ${this.opacity})`;
            ctx.fill();
        }
    }
    
    function init() {
        resizeCanvas();
        particles = [];
        for (let i = 0; i < 100; i++) {
            particles.push(new Particle());
        }
        animate();
    }
    
    function animate() {
        if (!ctx) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach(particle => {
            particle.update();
            particle.draw();
        });
        animationFrameId = requestAnimationFrame(animate);
    }
    
    window.addEventListener('resize', () => {
        resizeCanvas();
        init();
    });
    
    init();
    
    // Cleanup function
    return () => {
        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
        }
    };
}

// Toast notifications
function showError(message) {
    showToast(message, 'error');
}

function showSuccess(message) {
    showToast(message, 'success');
}

function showInfo(message) {
    showToast(message, 'info');
}

function showToast(message, type) {
    // Remove existing toast if any
    const existingToast = document.querySelector('.toast-message');
    if (existingToast) {
        existingToast.remove();
    }
    
    const toast = document.createElement('div');
    toast.className = `toast-message ${type}-toast`;
    toast.textContent = message;
    
    let gradient = '';
    if (type === 'error') {
        gradient = 'linear-gradient(135deg, #ef4444, #dc2626)';
    } else if (type === 'success') {
        gradient = 'linear-gradient(135deg, #10b981, #059669)';
    } else {
        gradient = 'linear-gradient(135deg, #3b82f6, #8b5cf6)';
    }
    
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${gradient};
        backdrop-filter: blur(10px);
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        z-index: 2000;
        animation: slideIn 0.3s ease;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        color: white;
        font-weight: 500;
        max-width: 400px;
        font-family: 'Inter', sans-serif;
    `;
    
    // Add animation styles if not present
    if (!document.querySelector('#toast-animations')) {
        const style = document.createElement('style');
        style.id = 'toast-animations';
        style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            @keyframes slideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}