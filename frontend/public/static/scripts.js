/* XLR8 UI - JavaScript */

const backendPort = 8000;
const backendBaseUrl = `${window.location.protocol}//${window.location.hostname}:${backendPort}`;

// State
let topics = [];
let isSearching = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeChatInterface();
    initializeResultsPage();
});

// Chat Interface Initialization
function initializeChatInterface() {
    const topicInput = document.getElementById('topicInput');
    const topicInputBottom = document.getElementById('topicInputBottom');
    const produceBtn = document.getElementById('produceNewspaper');
    const produceBtnBottom = document.getElementById('produceNewspaperBottom');
    
    if (!topicInput) return; // Not on chat page
    
    // Topic input - Enter key triggers search (initial state)
    if (topicInput) {
        topicInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !isSearching) {
                e.preventDefault();
                produceNewspaper();
            }
        });
    }
    
    // Topic input bottom - Enter key triggers search (after results)
    if (topicInputBottom) {
        topicInputBottom.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !isSearching) {
                e.preventDefault();
                produceNewspaper();
            }
        });
    }
    
    // Search buttons
    if (produceBtn) {
        produceBtn.addEventListener('click', produceNewspaper);
    }
    if (produceBtnBottom) {
        produceBtnBottom.addEventListener('click', produceNewspaper);
    }
    
    // Focus input on load
    if (topicInput) {
        topicInput.focus();
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

// Topic Management (kept for future use)
function addTopic() {
    // Reserved for future use
    return;
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
    // Get topic from either input (initial or bottom)
    const topicInput = document.getElementById('topicInput');
    const topicInputBottom = document.getElementById('topicInputBottom');
    const activeInput = topicInput?.value.trim() ? topicInput : topicInputBottom;
    const topic = activeInput?.value.trim();
    
    if (!topic) {
        showToast('Please enter a topic', 'warning');
        return;
    }
    
    if (isSearching) {
        return; // Prevent multiple simultaneous searches
    }
    
    isSearching = true;
    topics = [topic]; // Use single topic from input
    
    // Switch to chat mode (hide initial state, show results and bottom input)
    switchToChatMode();
    
    // Add user message to chat
    addUserMessage(topic);
    
    // Clear both inputs
    if (topicInput) topicInput.value = '';
    if (topicInputBottom) topicInputBottom.value = '';
    
    // Update button states
    const produceBtn = document.getElementById('produceNewspaper');
    const produceBtnBottom = document.getElementById('produceNewspaperBottom');
    if (produceBtn) {
        produceBtn.disabled = true;
        produceBtn.textContent = 'Searching...';
    }
    if (produceBtnBottom) {
        produceBtnBottom.disabled = true;
        produceBtnBottom.textContent = 'Searching...';
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
        isSearching = false;
        
        // Update button states
        if (produceBtn) {
            produceBtn.disabled = false;
            produceBtn.textContent = 'Search';
        }
        if (produceBtnBottom) {
            produceBtnBottom.disabled = false;
            produceBtnBottom.textContent = 'Search';
        }
        
        if (data.results && Array.isArray(data.results)) {
            if (data.results.length === 0) {
                addErrorMessage('No recent credible sources found. Try different topics or adjust the time range.');
                focusBottomInput();
                return;
            }
            // Render results inline
            renderResultsInline(data);
            // Store data for copy functions
            window.xlr8ResearchData = data;
        } else if (data.error) {
            addErrorMessage(`Error: ${data.error}`);
            showToast(`Error: ${data.error}`, 'danger');
        } else {
            addErrorMessage('Unexpected response format');
            showToast('Unexpected response format', 'danger');
        }
        
        // Scroll to bottom and focus bottom input
        setTimeout(() => {
            scrollToBottom();
            focusBottomInput();
        }, 100);
    })
    .catch((error) => {
        toggleLoading(false);
        isSearching = false;
        
        // Update button states
        if (produceBtn) {
            produceBtn.disabled = false;
            produceBtn.textContent = 'Search';
        }
        if (produceBtnBottom) {
            produceBtnBottom.disabled = false;
            produceBtnBottom.textContent = 'Search';
        }
        console.error('Error:', error);
        addErrorMessage(`Error: ${error.message}`);
        showToast(`Error: ${error.message}`, 'danger');
        
        // Focus bottom input
        setTimeout(() => focusBottomInput(), 100);
    });
}

// Switch from initial state to chat mode
function switchToChatMode() {
    const initialState = document.getElementById('initialState');
    const resultsContainer = document.getElementById('resultsContainer');
    const chatInputContainer = document.getElementById('chatInputContainer');
    
    if (initialState) {
        initialState.classList.add('hidden');
    }
    if (resultsContainer) {
        resultsContainer.classList.remove('hidden');
    }
    if (chatInputContainer) {
        chatInputContainer.classList.remove('hidden');
    }
}

// Focus bottom input
function focusBottomInput() {
    const topicInputBottom = document.getElementById('topicInputBottom');
    if (topicInputBottom) {
        topicInputBottom.focus();
    }
}

// Add user message to chat
function addUserMessage(topic) {
    const container = document.getElementById('resultsContainer');
    if (!container) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message chat-message--user';
    messageDiv.innerHTML = `
        <div class="chat-message__content">
            <p>${escapeHtml(topic)}</p>
        </div>
    `;
    container.appendChild(messageDiv);
    scrollToBottom();
}

// Add error message to chat
function addErrorMessage(message) {
    const container = document.getElementById('resultsContainer');
    if (!container) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message chat-message--error';
    messageDiv.innerHTML = `
        <div class="chat-message__content">
            <p class="muted">${escapeHtml(message)}</p>
        </div>
    `;
    container.appendChild(messageDiv);
    scrollToBottom();
}

// Render results inline (chat format)
function renderResultsInline(data) {
    const container = document.getElementById('resultsContainer');
    if (!container) return;
    
    const results = data.results || [];
    
    results.forEach((result, idx) => {
        if (result.error === 'INSUFFICIENT_SOURCES') {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'chat-message chat-message--error';
            errorDiv.innerHTML = `
                <div class="chat-message__content">
                    <p class="muted">Error: Insufficient sources found for "${escapeHtml(result.topic)}". Please try a different topic or time range.</p>
                </div>
            `;
            container.appendChild(errorDiv);
            return;
        }
        
        // Render result as assistant message
        const resultDiv = document.createElement('div');
        resultDiv.className = 'chat-message chat-message--assistant';
        resultDiv.innerHTML = renderSingleResult(result);
        container.appendChild(resultDiv);
        
        // Attach citation click handlers
        setTimeout(() => {
            resultDiv.querySelectorAll('.citation').forEach(cite => {
                cite.addEventListener('click', (e) => {
                    e.preventDefault();
                    const citeNum = parseInt(cite.textContent.match(/\d+/)?.[0]);
                    if (citeNum) {
                        scrollToSourceInChat(citeNum, resultDiv);
                    }
                });
            });
        }, 0);
    });
    
    scrollToBottom();
}

// Scroll to source within chat message
function scrollToSourceInChat(citeNum, container) {
    const sourceEl = container.querySelector(`#source-${citeNum}`);
    if (sourceEl) {
        sourceEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        sourceEl.style.background = 'var(--brand)';
        sourceEl.style.color = 'white';
        setTimeout(() => {
            sourceEl.style.background = '';
            sourceEl.style.color = '';
        }, 2000);
    }
}

// Scroll to bottom of chat
function scrollToBottom() {
    const container = document.getElementById('resultsContainer');
    if (container) {
        setTimeout(() => {
            container.scrollTop = container.scrollHeight;
        }, 100);
    }
}

// Render single result for chat (structured format)
function renderSingleResult(result) {
    const headline = result.headline || result.topic;
    const bullets = result.summary || [];
    const links = result.links || [];
    const whyItMatters = result.why_it_matters;
    const tags = result.tags || {};
    const insights = result.insights;
    
    // Build bullets HTML
    const bulletsHTML = bullets.map(bullet => {
        const text = bullet.bullet || '';
        const cites = bullet.cite || [];
        const citeLinks = cites.map(n => {
            const link = links.find(l => l.n === n);
            const title = link?.title || link?.url || '';
            return `<a href="#source-${n}" class="citation" data-cite="${n}" title="${escapeHtml(title)}">[${n}]</a>`;
        }).join('');
        return `<li style="margin-bottom: var(--space-sm); padding-left: var(--space-sm); line-height: 1.6;">${escapeHtml(text)} ${citeLinks}</li>`;
    }).join('');
    
    // Build sources HTML
    const sourcesHTML = links.map(link => {
        const source = result.sources?.find(s => s.url === link.url) || {};
        const domain = link.url ? new URL(link.url).hostname.replace('www.', '') : '';
        const faviconUrl = `https://www.google.com/s2/favicons?domain=${domain}&sz=16`;
        return `
            <div id="source-${link.n}" class="source-item" style="margin-bottom: var(--space-sm); padding: var(--space-sm); background: var(--card); border: 1px solid var(--border, rgba(0, 0, 0, 0.1)); border-radius: var(--radius-sm);">
                <div style="display: flex; align-items: start; gap: var(--space-sm);">
                    <img src="${faviconUrl}" alt="${escapeHtml(domain)}" style="width: 16px; height: 16px; margin-top: 2px; flex-shrink: 0;">
                    <div style="flex: 1; min-width: 0;">
                        <a href="${escapeHtml(link.url)}" target="_blank" rel="noopener noreferrer" style="color: var(--brand); text-decoration: none; font-weight: 500; word-break: break-word; display: block;">
                            ${escapeHtml(link.title || source.title || link.url)}
                        </a>
                        <div style="font-size: 0.8125rem; color: var(--muted); margin-top: 0.25rem;">
                            ${escapeHtml(domain)}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    // Build tags HTML
    const companies = Array.isArray(tags.companies) ? tags.companies : (tags.companies ? [tags.companies] : []);
    const regions = Array.isArray(tags.regions) ? tags.regions : (tags.regions ? [tags.regions] : []);
    const themes = Array.isArray(tags.themes) ? tags.themes : (tags.themes ? [tags.themes] : []);
    const tagsHTML = [
        ...companies.map(c => `<span class="badge badge--info" style="margin-right: var(--space-xs); margin-bottom: var(--space-xs);">${escapeHtml(c)}</span>`),
        ...regions.map(r => `<span class="badge badge--info" style="margin-right: var(--space-xs); margin-bottom: var(--space-xs);">${escapeHtml(r)}</span>`),
        ...themes.map(t => `<span class="badge badge--info" style="margin-right: var(--space-xs); margin-bottom: var(--space-xs);">${escapeHtml(t)}</span>`)
    ].join('');
    
    // Build insights HTML (reuse from renderResultsPage)
    const insightsHTML = buildInsightsHTML(insights, links);
    
    return `
        <div style="display: flex; flex-direction: column; gap: var(--space-md);">
            <!-- Headline -->
            <h3 style="margin: 0; color: var(--text); font-weight: 600; font-size: 1.25rem; line-height: 1.3;">${escapeHtml(headline)}</h3>
            
            <!-- Tags -->
            ${tagsHTML ? `<div style="display: flex; flex-wrap: wrap; gap: var(--space-xs); margin-bottom: var(--space-xs);">${tagsHTML}</div>` : ''}
            
            <!-- Why it matters -->
            ${whyItMatters ? `
                <div style="padding: var(--space-md); background: var(--card); border: 1px solid var(--border, rgba(0, 0, 0, 0.1)); border-radius: var(--radius-sm);">
                    <div class="badge badge--info" style="margin-bottom: var(--space-sm);">Why it matters</div>
                    <p style="margin: 0; color: var(--muted); line-height: 1.6;">${escapeHtml(whyItMatters)}</p>
                </div>
            ` : ''}
            
            <!-- Bullets -->
            <div style="margin: var(--space-md) 0;">
                <ul style="list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-sm);">
                    ${bulletsHTML}
                </ul>
            </div>
            
            <!-- Insights -->
            ${insightsHTML}
            
            <!-- Sources -->
            <div class="source-list" style="margin-top: var(--space-md);">
                <h4 style="margin-bottom: var(--space-md); color: var(--text); font-weight: 600; font-size: 1rem;">Sources</h4>
                <div style="display: flex; flex-direction: column; gap: var(--space-sm);">
                    ${sourcesHTML}
                </div>
            </div>
        </div>
    `;
}

// Build insights HTML (full rendering logic)
function buildInsightsHTML(insights, links) {
    if (!insights || insights.error) {
        if (insights && insights.error) {
            return `
                <div class="ghost-divider" style="margin: var(--space-lg) 0;"></div>
                <div class="insights-section" style="padding: var(--space-md); background: rgba(239, 68, 68, 0.1); border-radius: var(--radius); border: 1px solid var(--danger);">
                    <h4 style="margin-bottom: var(--space-sm); color: var(--danger); font-weight: 600;">Insights Generation Failed</h4>
                    <p style="color: var(--danger); font-size: 0.875rem;">${escapeHtml(insights.message || insights.error)}</p>
                </div>
            `;
        }
        return '';
    }
    
    // Full insights rendering (same as renderResultsPage)
    return `
        <div class="ghost-divider" style="margin: var(--space-lg) 0;"></div>
        <div class="insights-section" style="padding: var(--space-md); background: var(--panel); border-radius: var(--radius); border: 1px solid var(--border, rgba(0, 0, 0, 0.1));">
            <h4 style="margin-bottom: var(--space-md); color: var(--text); font-weight: 600; font-size: 1.125rem;">Market Insights</h4>
            
            ${insights.market_overview && insights.market_overview.trim() ? `
                <div class="insight-block" style="margin-bottom: var(--space-md);">
                    <h5 style="font-size: 0.9375rem; font-weight: 600; color: var(--text); margin-bottom: var(--space-xs);">Market Overview</h5>
                    <p style="color: var(--muted); line-height: 1.6;">${escapeHtml(insights.market_overview)}</p>
                </div>
            ` : ''}
            
            ${insights.key_segments && Array.isArray(insights.key_segments) && insights.key_segments.length > 0 ? `
                <div class="insight-block" style="margin-bottom: var(--space-md);">
                    <h5 style="font-size: 0.9375rem; font-weight: 600; color: var(--text); margin-bottom: var(--space-xs);">Key Segments</h5>
                    <ul style="list-style: none; padding: 0; margin: 0;">
                        ${insights.key_segments.map(seg => {
                            if (!seg || typeof seg !== 'object') return '';
                            return `
                            <li style="margin-bottom: var(--space-xs); padding-left: var(--space-sm); position: relative;">
                                <span style="font-weight: 500; color: var(--text);">${escapeHtml(seg.name || seg || 'Unknown')}</span>
                                ${seg.note ? `<span style="color: var(--muted);"> - ${escapeHtml(seg.note)}</span>` : ''}
                            </li>
                        `;
                        }).filter(x => x).join('')}
                    </ul>
                </div>
            ` : ''}
            
            ${insights.key_players && Array.isArray(insights.key_players) && insights.key_players.length > 0 ? `
                <div class="insight-block" style="margin-bottom: var(--space-md);">
                    <h5 style="font-size: 0.9375rem; font-weight: 600; color: var(--text); margin-bottom: var(--space-xs);">Key Players</h5>
                    <ul style="list-style: none; padding: 0; margin: 0;">
                        ${insights.key_players.map(player => {
                            if (!player || typeof player !== 'object') return '';
                            return `
                            <li style="margin-bottom: var(--space-xs); padding-left: var(--space-sm); position: relative;">
                                <span style="font-weight: 500; color: var(--text);">${escapeHtml(player.name || player || 'Unknown')}</span>
                                ${player.role ? `<span style="color: var(--muted);"> (${escapeHtml(player.role)})</span>` : ''}
                                ${player.signal ? `<div style="color: var(--muted); font-size: 0.875rem; margin-top: 0.25rem;">${escapeHtml(player.signal)}</div>` : ''}
                            </li>
                        `;
                        }).filter(x => x).join('')}
                    </ul>
                </div>
            ` : ''}
            
            ${insights.opportunities && Array.isArray(insights.opportunities) && insights.opportunities.length > 0 ? `
                <div class="insight-block" style="margin-bottom: var(--space-md);">
                    <h5 style="font-size: 0.9375rem; font-weight: 600; color: var(--text); margin-bottom: var(--space-xs);">Opportunities</h5>
                    <ul style="list-style: none; padding: 0; margin: 0;">
                        ${insights.opportunities.map(opp => {
                            if (!opp || typeof opp !== 'object') return '';
                            const citeLinks = (opp.cite || []).map(n => 
                                `<a href="#source-${n}" class="citation" data-cite="${n}">[${n}]</a>`
                            ).join(' ');
                            return `
                                <li style="margin-bottom: var(--space-xs); padding-left: var(--space-sm); position: relative;">
                                    <span style="color: var(--text);">${escapeHtml(opp.text || opp || '')}</span> ${citeLinks}
                                </li>
                            `;
                        }).filter(x => x).join('')}
                    </ul>
                </div>
            ` : ''}
            
            ${insights.risks && Array.isArray(insights.risks) && insights.risks.length > 0 ? `
                <div class="insight-block" style="margin-bottom: var(--space-md);">
                    <h5 style="font-size: 0.9375rem; font-weight: 600; color: var(--text); margin-bottom: var(--space-xs);">Risks</h5>
                    <ul style="list-style: none; padding: 0; margin: 0;">
                        ${insights.risks.map(risk => {
                            if (!risk || typeof risk !== 'object') return '';
                            const citeLinks = (risk.cite || []).map(n => 
                                `<a href="#source-${n}" class="citation" data-cite="${n}">[${n}]</a>`
                            ).join(' ');
                            return `
                                <li style="margin-bottom: var(--space-xs); padding-left: var(--space-sm); position: relative;">
                                    <span style="color: var(--text);">${escapeHtml(risk.text || risk || '')}</span> ${citeLinks}
                                </li>
                            `;
                        }).filter(x => x).join('')}
                    </ul>
                </div>
            ` : ''}
            
            ${insights.recommended_plays && Array.isArray(insights.recommended_plays) && insights.recommended_plays.length > 0 ? `
                <div class="insight-block" style="margin-bottom: var(--space-md);">
                    <h5 style="font-size: 0.9375rem; font-weight: 600; color: var(--text); margin-bottom: var(--space-xs);">Recommended Plays</h5>
                    <ul style="list-style: none; padding: 0; margin: 0;">
                        ${insights.recommended_plays.map(play => {
                            if (!play || typeof play !== 'object') return '';
                            const evidenceLinks = (play.evidence || []).map(n => 
                                `<a href="#source-${n}" class="citation" data-cite="${n}">[${n}]</a>`
                            ).join(' ');
                            return `
                                <li style="margin-bottom: var(--space-md); padding: var(--space-sm); background: var(--card); border: 1px solid var(--border, rgba(0, 0, 0, 0.1)); border-radius: var(--radius-sm);">
                                    <div style="font-weight: 600; color: var(--text); margin-bottom: var(--space-xs);">${escapeHtml(play.play_name || play.name || 'Unnamed Play')}</div>
                                    ${play.channels && Array.isArray(play.channels) && play.channels.length > 0 ? `
                                        <div style="margin-bottom: var(--space-xs);">
                                            <span style="font-size: 0.8125rem; color: var(--muted);">Channels: </span>
                                            ${play.channels.map(ch => `<span class="badge badge--info" style="margin-right: var(--space-xs);">${escapeHtml(ch)}</span>`).join('')}
                                        </div>
                                    ` : ''}
                                    ${play.angle && play.angle.trim() ? `
                                        <div style="color: var(--muted); font-size: 0.875rem; margin-bottom: var(--space-xs);">
                                            ${escapeHtml(play.angle)} ${evidenceLinks}
                                        </div>
                                    ` : ''}
                                </li>
                            `;
                        }).filter(x => x).join('')}
                    </ul>
                </div>
            ` : ''}
            
            ${insights.trend && typeof insights.trend === 'object' ? `
                <div class="insight-block" style="margin-bottom: var(--space-md); padding: var(--space-sm); background: var(--card); border: 1px solid var(--border, rgba(0, 0, 0, 0.1)); border-radius: var(--radius-sm);">
                    <h5 style="font-size: 0.9375rem; font-weight: 600; color: var(--text); margin-bottom: var(--space-xs);">Trend</h5>
                    ${insights.trend.momentum && insights.trend.momentum.trim() ? `
                        <div style="margin-bottom: var(--space-xs);">
                            <span style="color: var(--muted);">Momentum: </span>
                            <span style="font-weight: 500; color: var(--text);">${escapeHtml(insights.trend.momentum)}</span>
                        </div>
                    ` : ''}
                    ${insights.trend.signal_basis && insights.trend.signal_basis.trim() ? `
                        <div style="color: var(--muted); font-size: 0.875rem;">
                            ${escapeHtml(insights.trend.signal_basis)}
                        </div>
                    ` : ''}
                </div>
            ` : ''}
        </div>
    `;
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
        const insights = result.insights; // Insights from InsightsAgent
        
        // Debug: Log insights to console
        if (insights) {
            console.log('[DEBUG] Insights found for topic:', result.topic);
            console.log('[DEBUG] Insights structure:', Object.keys(insights));
            if (insights.error) {
                console.warn('[DEBUG] Insights has error:', insights.error, insights.message);
            } else {
                console.log('[DEBUG] Insights fields:', {
                    market_overview: !!insights.market_overview,
                    key_segments: insights.key_segments?.length || 0,
                    key_players: insights.key_players?.length || 0,
                    opportunities: insights.opportunities?.length || 0,
                    risks: insights.risks?.length || 0,
                    recommended_plays: insights.recommended_plays?.length || 0,
                    trend: !!insights.trend
                });
            }
            console.log('[DEBUG] Full insights:', JSON.stringify(insights, null, 2));
    } else {
            console.warn('[DEBUG] No insights found for topic:', result.topic);
            console.log('[DEBUG] Result keys:', Object.keys(result));
        }
        
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
                
                ${insights && !insights.error ? `
                    <div class="ghost-divider" style="margin: var(--space-lg) 0;"></div>
                    <div class="insights-section" style="padding: var(--space-md); background: var(--panel); border-radius: var(--radius); border: 1px solid var(--border);">
                        <h4 style="margin-bottom: var(--space-md); color: var(--text); font-weight: 600; font-size: 1.125rem;">Market Insights</h4>
                        
                        ${insights.market_overview && insights.market_overview.trim() ? `
                            <div class="insight-block" style="margin-bottom: var(--space-md);">
                                <h5 style="font-size: 0.9375rem; font-weight: 600; color: var(--text); margin-bottom: var(--space-xs);">Market Overview</h5>
                                <p style="color: var(--muted); line-height: 1.6;">${escapeHtml(insights.market_overview)}</p>
                            </div>
                        ` : ''}
                        
                        ${insights.key_segments && Array.isArray(insights.key_segments) && insights.key_segments.length > 0 ? `
                            <div class="insight-block" style="margin-bottom: var(--space-md);">
                                <h5 style="font-size: 0.9375rem; font-weight: 600; color: var(--text); margin-bottom: var(--space-xs);">Key Segments</h5>
                                <ul style="list-style: none; padding: 0; margin: 0;">
                                    ${insights.key_segments.map(seg => {
                                        if (!seg || typeof seg !== 'object') return '';
                                        return `
                                        <li style="margin-bottom: var(--space-xs); padding-left: var(--space-sm); position: relative;">
                                            <span style="font-weight: 500; color: var(--text);">${escapeHtml(seg.name || seg || 'Unknown')}</span>
                                            ${seg.note ? `<span style="color: var(--muted);"> - ${escapeHtml(seg.note)}</span>` : ''}
                                        </li>
                                    `;
                                    }).filter(x => x).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        
                        ${insights.key_players && Array.isArray(insights.key_players) && insights.key_players.length > 0 ? `
                            <div class="insight-block" style="margin-bottom: var(--space-md);">
                                <h5 style="font-size: 0.9375rem; font-weight: 600; color: var(--text); margin-bottom: var(--space-xs);">Key Players</h5>
                                <ul style="list-style: none; padding: 0; margin: 0;">
                                    ${insights.key_players.map(player => {
                                        if (!player || typeof player !== 'object') return '';
                                        return `
                                        <li style="margin-bottom: var(--space-xs); padding-left: var(--space-sm); position: relative;">
                                            <span style="font-weight: 500; color: var(--text);">${escapeHtml(player.name || player || 'Unknown')}</span>
                                            ${player.role ? `<span style="color: var(--muted);"> (${escapeHtml(player.role)})</span>` : ''}
                                            ${player.signal ? `<div style="color: var(--muted); font-size: 0.875rem; margin-top: 0.25rem;">${escapeHtml(player.signal)}</div>` : ''}
                                        </li>
                                    `;
                                    }).filter(x => x).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        
                        ${insights.opportunities && Array.isArray(insights.opportunities) && insights.opportunities.length > 0 ? `
                            <div class="insight-block" style="margin-bottom: var(--space-md);">
                                <h5 style="font-size: 0.9375rem; font-weight: 600; color: var(--text); margin-bottom: var(--space-xs);">Opportunities</h5>
                                <ul style="list-style: none; padding: 0; margin: 0;">
                                    ${insights.opportunities.map(opp => {
                                        if (!opp || typeof opp !== 'object') return '';
                                        const citeLinks = (opp.cite || []).map(n => 
                                            `<a href="#source-${n}" class="citation" data-cite="${n}">[${n}]</a>`
                                        ).join(' ');
                                        return `
                                            <li style="margin-bottom: var(--space-xs); padding-left: var(--space-sm); position: relative;">
                                                <span style="color: var(--text);">${escapeHtml(opp.text || opp || '')}</span> ${citeLinks}
                                            </li>
                                        `;
                                    }).filter(x => x).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        
                        ${insights.risks && Array.isArray(insights.risks) && insights.risks.length > 0 ? `
                            <div class="insight-block" style="margin-bottom: var(--space-md);">
                                <h5 style="font-size: 0.9375rem; font-weight: 600; color: var(--text); margin-bottom: var(--space-xs);">Risks</h5>
                                <ul style="list-style: none; padding: 0; margin: 0;">
                                    ${insights.risks.map(risk => {
                                        if (!risk || typeof risk !== 'object') return '';
                                        const citeLinks = (risk.cite || []).map(n => 
                                            `<a href="#source-${n}" class="citation" data-cite="${n}">[${n}]</a>`
                                        ).join(' ');
                                        return `
                                            <li style="margin-bottom: var(--space-xs); padding-left: var(--space-sm); position: relative;">
                                                <span style="color: var(--text);">${escapeHtml(risk.text || risk || '')}</span> ${citeLinks}
                                            </li>
                                        `;
                                    }).filter(x => x).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        
                        ${insights.recommended_plays && Array.isArray(insights.recommended_plays) && insights.recommended_plays.length > 0 ? `
                            <div class="insight-block" style="margin-bottom: var(--space-md);">
                                <h5 style="font-size: 0.9375rem; font-weight: 600; color: var(--text); margin-bottom: var(--space-xs);">Recommended Plays</h5>
                                <ul style="list-style: none; padding: 0; margin: 0;">
                                    ${insights.recommended_plays.map(play => {
                                        if (!play || typeof play !== 'object') return '';
                                        const evidenceLinks = (play.evidence || []).map(n => 
                                            `<a href="#source-${n}" class="citation" data-cite="${n}">[${n}]</a>`
                                        ).join(' ');
                                        return `
                                            <li style="margin-bottom: var(--space-md); padding: var(--space-sm); background: var(--card); border: 1px solid var(--border); border-radius: var(--radius-sm);">
                                                <div style="font-weight: 600; color: var(--text); margin-bottom: var(--space-xs);">${escapeHtml(play.play_name || play.name || 'Unnamed Play')}</div>
                                                ${play.channels && Array.isArray(play.channels) && play.channels.length > 0 ? `
                                                    <div style="margin-bottom: var(--space-xs);">
                                                        <span style="font-size: 0.8125rem; color: var(--muted);">Channels: </span>
                                                        ${play.channels.map(ch => `<span class="badge badge--info" style="margin-right: var(--space-xs);">${escapeHtml(ch)}</span>`).join('')}
                                                    </div>
                                                ` : ''}
                                                ${play.angle && play.angle.trim() ? `
                                                    <div style="color: var(--muted); font-size: 0.875rem; margin-bottom: var(--space-xs);">
                                                        ${escapeHtml(play.angle)} ${evidenceLinks}
                                                    </div>
                                                ` : ''}
                                            </li>
                                        `;
                                    }).filter(x => x).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        
                        ${insights.trend && typeof insights.trend === 'object' ? `
                            <div class="insight-block" style="margin-bottom: var(--space-md); padding: var(--space-sm); background: var(--card); border: 1px solid var(--border); border-radius: var(--radius-sm);">
                                <h5 style="font-size: 0.9375rem; font-weight: 600; color: var(--text); margin-bottom: var(--space-xs);">Trend</h5>
                                ${insights.trend.momentum && insights.trend.momentum.trim() ? `
                                    <div style="margin-bottom: var(--space-xs);">
                                        <span style="color: var(--muted);">Momentum: </span>
                                        <span style="font-weight: 500; color: var(--text);">${escapeHtml(insights.trend.momentum)}</span>
                                    </div>
                                ` : ''}
                                ${insights.trend.signal_basis && insights.trend.signal_basis.trim() ? `
                                    <div style="color: var(--muted); font-size: 0.875rem;">
                                        ${escapeHtml(insights.trend.signal_basis)}
                                    </div>
                                ` : ''}
                                ${insights.trend.news_volume_change ? `
                                    <div style="margin-top: var(--space-xs);">
                                        <span style="color: var(--muted);">News Volume: </span>
                                        <span style="font-weight: 500; color: var(--text);">${escapeHtml(insights.trend.news_volume_change)}</span>
                                    </div>
                                ` : ''}
                                ${insights.trend.new_companies && Array.isArray(insights.trend.new_companies) && insights.trend.new_companies.length > 0 ? `
                                    <div style="margin-top: var(--space-xs);">
                                        <span style="color: var(--muted);">New Companies: </span>
                                        <span style="color: var(--text);">${insights.trend.new_companies.map(c => escapeHtml(c)).join(', ')}</span>
                                    </div>
                                ` : ''}
                                ${insights.trend.fading_themes && Array.isArray(insights.trend.fading_themes) && insights.trend.fading_themes.length > 0 ? `
                                    <div style="margin-top: var(--space-xs);">
                                        <span style="color: var(--muted);">Fading Themes: </span>
                                        <span style="color: var(--text);">${insights.trend.fading_themes.map(t => escapeHtml(t)).join(', ')}</span>
                                    </div>
                                ` : ''}
                            </div>
                        ` : ''}
                        
                        ${insights.error ? `
                            <div class="insight-block" style="padding: var(--space-sm); background: rgba(239, 68, 68, 0.1); border-radius: var(--radius-sm); border: 1px solid var(--danger);">
                                <p style="color: var(--danger); font-size: 0.875rem;">Insights Error: ${escapeHtml(insights.message || insights.error)}</p>
                            </div>
                        ` : ''}
                    </div>
                ` : insights && insights.error ? `
                    <div class="ghost-divider" style="margin: var(--space-lg) 0;"></div>
                    <div class="insights-section" style="padding: var(--space-md); background: rgba(239, 68, 68, 0.1); border-radius: var(--radius); border: 1px solid var(--danger);">
                        <h4 style="margin-bottom: var(--space-sm); color: var(--danger); font-weight: 600;">Insights Generation Failed</h4>
                        <p style="color: var(--danger); font-size: 0.875rem;">${escapeHtml(insights.message || insights.error)}</p>
                    </div>
                ` : ''}
                
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
