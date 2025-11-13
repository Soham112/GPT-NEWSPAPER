/* XLR8 UI - JavaScript */

const backendPort = 8000;
const backendBaseUrl = `${window.location.protocol}//${window.location.hostname}:${backendPort}`;

// State
let topics = [];
let selectedLayout = 'layout_1.html';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeLandingPage();
    initializeResultsPage();
});

// Landing Page Initialization
function initializeLandingPage() {
    const topicInput = document.getElementById('topicInput');
    const addTopicBtn = document.getElementById('addTopicBtn');
    const produceBtn = document.getElementById('produceNewspaper');
    const layoutButtons = document.querySelectorAll('.pill-toggle__item');
    
    if (!topicInput) return; // Not on landing page
    
    // Topic input - Enter key adds topic
    topicInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addTopic();
        }
    });
    
    // Add topic button
    if (addTopicBtn) {
        addTopicBtn.addEventListener('click', addTopic);
    }
    
    // Layout selection
    layoutButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            layoutButtons.forEach(b => b.classList.remove('pill-toggle__item--active'));
            e.target.classList.add('pill-toggle__item--active');
            selectedLayout = e.target.getAttribute('data-layout');
        });
    });
    
    // Generate Response button
    if (produceBtn) {
        produceBtn.addEventListener('click', produceNewspaper);
    }
}

// Results Page Initialization
function initializeResultsPage() {
    const copyJSONBtn = document.getElementById('copyJSONBtn');
    const copyMarkdownBtn = document.getElementById('copyMarkdownBtn');
    
    if (!copyJSONBtn) return; // Not on results page
    
    // Copy buttons
    if (copyJSONBtn) {
        copyJSONBtn.addEventListener('click', () => copyJSON(window.xlr8ResearchData));
    }
    
    if (copyMarkdownBtn) {
        copyMarkdownBtn.addEventListener('click', () => copyMarkdown(window.xlr8ResearchData));
    }
    
    // Citation click handlers (delegated)
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('citation')) {
            e.preventDefault();
            const citeNum = parseInt(e.target.textContent.match(/\d+/)?.[0]);
            if (citeNum) {
                scrollToSource(citeNum);
            }
        }
    });
}

// Topic Management
function addTopic() {
    const topicInput = document.getElementById('topicInput');
    const topic = topicInput?.value.trim();
    
    if (!topic || topics.includes(topic)) {
        return;
    }
    
    topics.push(topic);
    topicInput.value = '';
    renderTopicChips();
}

function removeTopic(topic) {
    topics = topics.filter(t => t !== topic);
    renderTopicChips();
}

function renderTopicChips() {
    const container = document.getElementById('topicChips');
    if (!container) return;
    
    container.innerHTML = topics.map(topic => `
        <span class="chip chip--removable">
            ${escapeHtml(topic)}
            <button 
                type="button" 
                class="chip__remove" 
                onclick="removeTopic('${escapeHtml(topic)}')"
                aria-label="Remove ${escapeHtml(topic)}"
            >×</button>
        </span>
    `).join('');
}

// Generate Response
function produceNewspaper() {
    if (topics.length === 0) {
        showToast('Please add at least one topic.', 'warning');
        return;
    }
    
    const produceBtn = document.getElementById('produceNewspaper');
    if (produceBtn) {
        produceBtn.disabled = true;
        produceBtn.innerHTML = '<span style="opacity: 0.7;">Processing...</span>';
    }
    
    toggleLoading(true);
    
    const payload = {
        topics: topics,
        window: "week",
        k: 5,
        strict: true
    };
    
    fetch(`${backendBaseUrl}/research/v1`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        toggleLoading(false);
        if (produceBtn) {
            produceBtn.disabled = false;
            produceBtn.textContent = 'Generate Response';
        }
        
        if (data.results && Array.isArray(data.results)) {
            if (data.results.length === 0) {
                showEmptyState();
                return;
            }
            // Store data in sessionStorage and navigate to results page
            sessionStorage.setItem('xlr8ResearchData', JSON.stringify(data));
            window.location.href = 'newspaper.html';
        } else if (data.error) {
            showToast(`Error: ${data.error}`, 'danger');
        } else {
            showToast('Unexpected response format', 'danger');
        }
    })
    .catch((error) => {
        toggleLoading(false);
        if (produceBtn) {
            produceBtn.disabled = false;
            produceBtn.textContent = 'Generate Response';
        }
        console.error('Error:', error);
        showToast(`Error: ${error.message}`, 'danger');
    });
}

// Render Results Page
function renderResultsPage(data) {
    const container = document.getElementById('resultsContainer');
    const topicBadge = document.getElementById('topicBadge');
    
    if (!container) return;
    
    const results = data.results || [];
    
    // Set topic badge
    if (topicBadge && data.topics && data.topics.length > 0) {
        topicBadge.textContent = data.topics[0];
    }
    
    if (results.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state__icon">📰</div>
                <h3 class="empty-state__title">No recent credible sources found.</h3>
                <p class="muted">Try different topics or adjust the time range.</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = results.map((result, idx) => {
        if (result.error === 'INSUFFICIENT_SOURCES') {
            return `
                <div class="result-card">
                    <h3>${escapeHtml(result.topic)}</h3>
                    <p class="muted">Error: Insufficient sources found. Please try a different topic or time range.</p>
                </div>
            `;
        }
        
        const headline = result.headline || result.topic;
        const bullets = result.summary || [];
        const links = result.links || [];
        const whyItMatters = result.why_it_matters;
        const tags = result.tags || {};
        const qualityCheck = result.quality_check;
        
        // Build bullets HTML
        const bulletsHTML = bullets.map(bullet => {
            const text = bullet.bullet || '';
            const cites = bullet.cite || [];
            const citeLinks = cites.map(n => {
                const link = links.find(l => l.n === n);
                const title = link?.title || link?.url || '';
                return `<a href="#source-${n}" class="citation" data-cite="${n}" title="${escapeHtml(title)}">[${n}]</a>`;
            }).join(' ');
            
            return `
                <li class="bullet-item">
                    ${escapeHtml(text)} ${citeLinks}
                </li>
            `;
        }).join('');
        
        // Build sources list
        const sourcesHTML = links.map(link => {
            const url = link.url || '';
            const title = link.title || url;
            const domain = new URL(url).hostname.replace('www.', '');
            const faviconUrl = `https://www.google.com/s2/favicons?sz=32&domain=${domain}`;
            
            return `
                <a 
                    href="${escapeHtml(url)}" 
                    target="_blank" 
                    class="source-list__item" 
                    id="source-${link.n}"
                >
                    <img src="${faviconUrl}" alt="" class="source-list__favicon" onerror="this.style.display='none'">
                    <div class="source-list__content">
                        <div class="source-list__title">${escapeHtml(title)}</div>
                        <div class="source-list__meta">
                            <span class="source-list__domain">${escapeHtml(domain)}</span>
                        </div>
                    </div>
                </a>
            `;
        }).join('');
        
        // Build tags HTML
        let tagsHTML = '';
        if (tags.companies && tags.companies.length > 0) {
            tagsHTML += `<div class="badge badge--info" style="margin-right: var(--space-xs);">Companies: ${tags.companies.join(', ')}</div>`;
        }
        if (tags.regions && tags.regions.length > 0) {
            tagsHTML += `<div class="badge badge--info" style="margin-right: var(--space-xs);">Regions: ${tags.regions.join(', ')}</div>`;
        }
        if (tags.themes && tags.themes.length > 0) {
            tagsHTML += `<div class="badge badge--info" style="margin-right: var(--space-xs);">Themes: ${tags.themes.join(', ')}</div>`;
        }
        
        // Quality check badge
        if (qualityCheck) {
            const qualityClass = qualityCheck === 'PASS' ? 'badge--success' : 'badge--warning';
            tagsHTML += `<div class="badge ${qualityClass}" style="margin-left: var(--space-xs);">Quality: ${qualityCheck}</div>`;
        }
        
        return `
            <div class="result-card">
                <a href="#" class="result-card__headline">${escapeHtml(headline)}</a>
                
                ${tagsHTML ? `<div style="margin: var(--space-md) 0;">${tagsHTML}</div>` : ''}
                
                ${whyItMatters ? `
                    <div class="result-card__why-matters">
                        <div class="badge badge--info">Why it matters</div>
                        <p style="margin-top: var(--space-sm); color: var(--muted);">${escapeHtml(whyItMatters)}</p>
                    </div>
                ` : ''}
                
                <ul class="bullets">
                    ${bulletsHTML}
                </ul>
                
                <div class="source-list">
                    <h4 style="margin-bottom: var(--space-sm); color: var(--text);">Sources</h4>
                    ${sourcesHTML}
                </div>
            </div>
        `;
    }).join('');
    
    // Store data globally for copy functions
    window.xlr8ResearchData = data;
}

// Copy Functions
function copyJSON(data) {
    if (!data) {
        showToast('No data to copy', 'warning');
        return;
    }
    
    const json = JSON.stringify(data, null, 2);
    copyToClipboard(json, 'JSON');
}

function copyMarkdown(data) {
    if (!data) {
        showToast('No data to copy', 'warning');
        return;
    }
    
    const results = data.results || [];
    let markdown = '# XLR8 Research Report\n\n';
    
    results.forEach(result => {
        if (result.error) return;
        
        markdown += `## ${result.headline || result.topic}\n\n`;
        
        if (result.summary && result.summary.length > 0) {
            result.summary.forEach(bullet => {
                const text = bullet.bullet || '';
                const cites = bullet.cite || [];
                const citeStr = cites.length > 0 ? ` [${cites.join(',')}]` : '';
                markdown += `- ${text}${citeStr}\n`;
            });
            markdown += '\n';
        }
        
        if (result.why_it_matters) {
            markdown += `**Why it matters:** ${result.why_it_matters}\n\n`;
        }
        
        if (result.links && result.links.length > 0) {
            markdown += `### Sources\n\n`;
            result.links.forEach(link => {
                markdown += `${link.n}. [${link.title || link.url}](${link.url})\n`;
            });
            markdown += '\n';
        }
    });
    
    copyToClipboard(markdown, 'Markdown');
}

function copyToClipboard(text, format) {
    navigator.clipboard.writeText(text).then(() => {
        showToast(`${format} copied to clipboard!`, 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showToast('Failed to copy to clipboard', 'danger');
    });
}

// Scroll to Source
function scrollToSource(citeNum) {
    const sourceElement = document.getElementById(`source-${citeNum}`);
    if (sourceElement) {
        sourceElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Highlight briefly
        sourceElement.classList.add('source-list__item--active');
        setTimeout(() => {
            sourceElement.classList.remove('source-list__item--active');
        }, 2000);
    }
}

// Loading State
function toggleLoading(isLoading) {
    const loader = document.getElementById('loading');
    const loadingText = document.getElementById('loadingText');
    
    if (!loader) return;
    
    if (isLoading) {
        loader.classList.remove('hidden');
        if (loadingText) {
            loadingText.textContent = 'Looking for news...';
        }
    } else {
        loader.classList.add('hidden');
    }
}

// Toast Notification
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    toast.textContent = message;
    toast.className = `toast badge badge--${type}`;
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

// Empty State
function showEmptyState() {
    const container = document.getElementById('resultsContainer') || document.body;
    container.innerHTML = `
        <div class="empty-state">
            <div class="empty-state__icon">📰</div>
            <h3 class="empty-state__title">No recent credible sources found.</h3>
            <p class="muted empty-state__suggestions">
                Try different topics or adjust the time range.
            </p>
        </div>
    `;
}

// Utility: Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make removeTopic available globally for onclick handlers
window.removeTopic = removeTopic;
