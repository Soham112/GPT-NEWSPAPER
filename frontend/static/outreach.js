/* Outreach Agent - JavaScript */

const backendBaseUrl = `${window.location.protocol}//${window.location.hostname}:8000`;
let sessionId = sessionStorage.getItem('outreachSessionId') || null;
let isStreaming = false;
let useStreaming = false; // Can be enabled via config or env check

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeOutreach();
});

function initializeOutreach() {
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const clientSelect = document.getElementById('clientSelect');
    
    // Send button click
    sendButton.addEventListener('click', sendMessage);
    
    // Enter key in input
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Client selection change
    if (clientSelect) {
        clientSelect.addEventListener('change', handleClientChange);
        loadClients();
    }
    
    // Add Client button (placeholder for now)
    const addClientBtn = document.getElementById('addClientBtn');
    if (addClientBtn) {
        addClientBtn.addEventListener('click', () => {
            showToast('Add Client feature coming soon', 'info');
        });
    }
    
    // KPI click handlers
    document.querySelectorAll('.kpi--clickable').forEach(kpi => {
        kpi.addEventListener('click', () => {
            const kpiType = kpi.dataset.kpi;
            showKPIModal(kpiType);
        });
    });
    
    // Filter button handlers
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const filterType = btn.dataset.filter;
            const filterValue = btn.dataset.value;
            
            // Update active state
            btn.closest('.filter-group').querySelectorAll('.filter-btn').forEach(b => {
                b.classList.remove('filter-btn--active');
            });
            btn.classList.add('filter-btn--active');
            
            // Update filter
            currentFilters[filterType] = filterValue;
            
            // Reload data if client is selected
            const clientSelect = document.getElementById('clientSelect');
            if (clientSelect && clientSelect.value) {
                const selectedOption = clientSelect.options[clientSelect.selectedIndex];
                const clientName = selectedOption.dataset.clientName || selectedOption.textContent.split(' (')[0];
                loadClientData(clientSelect.value, clientName);
            }
        });
    });
    
    // Modal close handler
    const modalClose = document.getElementById('modalClose');
    const modal = document.getElementById('kpiModal');
    if (modalClose && modal) {
        modalClose.addEventListener('click', () => {
            modal.style.display = 'none';
        });
        modal.querySelector('.modal__overlay')?.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }
    
    // Focus input on load
    messageInput.focus();
}

function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const prompt = messageInput.value.trim();
    
    if (!prompt || isStreaming) {
        return;
    }
    
    // Clear input and disable button
    messageInput.value = '';
    sendButton.disabled = true;
    isStreaming = true;
    
    // Add user message bubble
    addBubble('user', prompt);
    
    // Scroll to bottom
    scrollChatToBottom();
    
    // Check if streaming is enabled
    if (useStreaming) {
        sendMessageStream(prompt);
    } else {
        sendMessageSync(prompt);
    }
}

function sendMessageSync(prompt) {
    const sendButton = document.getElementById('sendButton');
    
    // Show typing indicator
    const typingId = addTypingIndicator();
    
    fetch(`${backendBaseUrl}/api/outreach/ask`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            prompt: prompt,
            session_id: sessionId
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        removeTypingIndicator(typingId);
        
        // Update session ID
        if (data.session_id) {
            sessionId = data.session_id;
            sessionStorage.setItem('outreachSessionId', sessionId);
        }
        
        // Render response
        renderResponse(data.text);
        
        sendButton.disabled = false;
        isStreaming = false;
        scrollChatToBottom();
    })
    .catch(error => {
        removeTypingIndicator(typingId);
        addBubble('error', `Couldn't reach Outreach Agent. ${error.message}`);
        sendButton.disabled = false;
        isStreaming = false;
        scrollChatToBottom();
    });
}

function sendMessageStream(prompt) {
    const sendButton = document.getElementById('sendButton');
    
    // Create agent bubble for streaming
    const bubbleId = addBubble('agent', '');
    const bubbleElement = document.getElementById(bubbleId);
    
    fetch(`${backendBaseUrl}/api/outreach/ask/stream`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            prompt: prompt,
            session_id: sessionId
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        function readChunk() {
            return reader.read().then(({ done, value }) => {
                if (done) {
                    sendButton.disabled = false;
                    isStreaming = false;
                    scrollChatToBottom();
                    return;
                }
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep incomplete line in buffer
                
                lines.forEach(line => {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.type === 'session' && data.session_id) {
                                sessionId = data.session_id;
                                sessionStorage.setItem('outreachSessionId', sessionId);
                            } else if (data.type === 'chunk' && data.text) {
                                bubbleElement.textContent += data.text;
                                scrollChatToBottom();
                            } else if (data.type === 'done') {
                                // Process final response
                                processResponse(bubbleElement.textContent);
                            } else if (data.type === 'error') {
                                bubbleElement.className = 'bubble bubble--error';
                                bubbleElement.textContent = `Error: ${data.error}`;
                            }
                        } catch (e) {
                            console.error('Error parsing SSE:', e);
                        }
                    }
                });
                
                return readChunk();
            });
        }
        
        return readChunk();
    })
    .catch(error => {
        bubbleElement.className = 'bubble bubble--error';
        bubbleElement.textContent = `Couldn't reach Outreach Agent. ${error.message}`;
        sendButton.disabled = false;
        isStreaming = false;
        scrollChatToBottom();
    });
}

function renderResponse(text) {
    // Parse and render response
    const { insights, kpis, sources } = parseResponse(text);
    
    // Create agent bubble with insights
    const bubbleId = addBubble('agent', insights);
    const bubbleElement = document.getElementById(bubbleId);
    
    // Update KPIs if present
    if (kpis) {
        updateKPIs(kpis);
    }
    
    // Add sources if present
    if (sources && sources.length > 0) {
        addSources(bubbleElement, sources);
    }
}

function processResponse(text) {
    // Process final response after streaming
    const { insights, kpis, sources } = parseResponse(text);
    const chatMessages = document.getElementById('chatMessages');
    const lastBubble = chatMessages.lastElementChild;
    
    if (lastBubble && lastBubble.classList.contains('bubble--agent')) {
        // Update existing bubble
        lastBubble.innerHTML = formatInsights(insights);
        
        // Update KPIs
        if (kpis) {
            updateKPIs(kpis);
        }
        
        // Add sources
        if (sources && sources.length > 0) {
            addSources(lastBubble, sources);
        }
    }
}

function parseResponse(text) {
    // Parse response text to extract insights, KPIs, and sources
    let insights = text;
    let kpis = null;
    let sources = [];
    
    // Extract KPIs line: "KPIs: LinkedIn: <n> | Email: <n> | Calls: <n> | HubSpot: <n>"
    const kpiMatch = text.match(/KPIs:\s*LinkedIn:\s*(\d+)\s*\|\s*Email:\s*(\d+)\s*\|\s*Calls:\s*(\d+)\s*\|\s*HubSpot:\s*(\d+)/i);
    if (kpiMatch) {
        kpis = {
            linkedin: parseInt(kpiMatch[1]),
            email: parseInt(kpiMatch[2]),
            calls: parseInt(kpiMatch[3]),
            hubspot: parseInt(kpiMatch[4])
        };
        // Remove KPIs line from insights
        insights = text.replace(/KPIs:.*$/m, '').trim();
    }
    
    // Extract Sources line: "Sources: <id1>, <id2>, <id3>"
    const sourcesMatch = text.match(/Sources:\s*(.+)/i);
    if (sourcesMatch) {
        sources = sourcesMatch[1].split(',').map(s => s.trim()).filter(s => s);
        // Remove Sources line from insights
        insights = insights.replace(/Sources:.*$/m, '').trim();
    }
    
    return { insights, kpis, sources };
}

function formatInsights(text) {
    // Enhanced formatting for markdown-like text with bold, sections, lists, and citations
    let formatted = text;
    
    // Process in sections to handle nested structures
    const lines = text.split('\n');
    let output = [];
    let inList = false;
    let inSection = false;
    
    lines.forEach((line, index) => {
        const trimmed = line.trim();
        if (!trimmed) {
            // Empty line - close current list if open
            if (inList) {
                output.push('</ul>');
                inList = false;
            }
            return;
        }
        
        // Check for section headers (lines ending with : and not starting with - or *)
        if (trimmed.endsWith(':') && !trimmed.match(/^[-*•]\s+/) && !trimmed.match(/^\d+\.\s+/)) {
            // Close any open list
            if (inList) {
                output.push('</ul>');
                inList = false;
            }
            // Close previous section if open
            if (inSection) {
                output.push('</div>');
            }
            // Format as section header
            const headerText = formatTextWithBold(trimmed.slice(0, -1));
            output.push(`<div class="response-section"><h4 class="response-section__title">${headerText}</h4>`);
            inSection = true;
        }
        // Check for bullet points (-, *, or •)
        else if (trimmed.match(/^[-*•]\s+/)) {
            if (!inList) {
                output.push('<ul class="response-list">');
                inList = true;
            }
            const listContent = formatTextWithBold(trimmed.replace(/^[-*•]\s+/, ''));
            output.push(`<li class="response-list__item">${listContent}</li>`);
        }
        // Check for numbered lists
        else if (trimmed.match(/^\d+\.\s+/)) {
            if (!inList) {
                output.push('<ul class="response-list response-list--numbered">');
                inList = true;
            }
            const listContent = formatTextWithBold(trimmed.replace(/^\d+\.\s+/, ''));
            output.push(`<li class="response-list__item">${listContent}</li>`);
        }
        // Regular paragraph
        else {
            // Close any open list
            if (inList) {
                output.push('</ul>');
                inList = false;
            }
            // Check if we need to close a section
            if (index > 0 && lines[index - 1].trim().endsWith(':')) {
                // This is content under a section
                const formattedText = formatTextWithBold(trimmed);
                output.push(`<p class="response-section__content">${formattedText}</p>`);
            } else {
                const formattedText = formatTextWithBold(trimmed);
                output.push(`<p>${formattedText}</p>`);
            }
        }
    });
    
    // Close any open lists
    if (inList) {
        output.push('</ul>');
    }
    // Close any open sections
    if (inSection) {
        output.push('</div>');
    }
    
    return output.join('');
}

function formatTextWithBold(text) {
    // Format bold text (**text**) and handle citations [ID]
    let formatted = escapeHtml(text);
    
    // Format bold text: **text** or *text*
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\*([^*]+)\*/g, '<strong>$1</strong>');
    
    // Format citations: [ID] or [ID1, ID2] as clickable chips
    formatted = formatted.replace(/\[([A-Z0-9,\s]+)\]/g, (match, ids) => {
        const citationIds = ids.split(',').map(id => id.trim()).filter(id => id);
        return citationIds.map(id => `<span class="citation-chip" title="Source: ${id}">[${id}]</span>`).join(' ');
    });
    
    return formatted;
}

function updateKPIs(kpis) {
    document.getElementById('kpi-linkedin').textContent = kpis.linkedin;
    document.getElementById('kpi-email').textContent = kpis.email;
    document.getElementById('kpi-calls').textContent = kpis.calls;
    document.getElementById('kpi-hubspot').textContent = kpis.hubspot;
}

function addSources(bubbleElement, sources) {
    const sourcesDiv = document.createElement('div');
    sourcesDiv.className = 'sources';
    
    sources.forEach(source => {
        const chip = document.createElement('span');
        chip.className = 'source-chip';
        chip.textContent = source;
        sourcesDiv.appendChild(chip);
    });
    
    bubbleElement.appendChild(sourcesDiv);
}

function addBubble(type, content) {
    const chatMessages = document.getElementById('chatMessages');
    const bubble = document.createElement('div');
    const bubbleId = `bubble-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    bubble.id = bubbleId;
    bubble.className = `bubble bubble--${type}`;
    
    if (type === 'agent' && content) {
        bubble.innerHTML = formatInsights(content);
    } else {
        bubble.textContent = content;
    }
    
    chatMessages.appendChild(bubble);
    scrollChatToBottom();
    
    return bubbleId;
}

function addTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    const indicator = document.createElement('div');
    const indicatorId = `typing-${Date.now()}`;
    indicator.id = indicatorId;
    indicator.className = 'typing-indicator';
    indicator.innerHTML = '<span></span><span></span><span></span>';
    chatMessages.appendChild(indicator);
    scrollChatToBottom();
    return indicatorId;
}

function removeTypingIndicator(indicatorId) {
    const indicator = document.getElementById(indicatorId);
    if (indicator) {
        indicator.remove();
    }
}

function scrollChatToBottom() {
    const chat = document.getElementById('chatMessages');
    chat.scrollTop = chat.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// --- Client Selection and Data Loading ---

function loadClients() {
    fetch(`${backendBaseUrl}/api/outreach/clients`)
        .then(response => response.json())
        .then(data => {
            const clientSelect = document.getElementById('clientSelect');
            if (!clientSelect) return;
            
            // Clear existing options except the first one
            clientSelect.innerHTML = '<option value="">Select a client...</option>';
            
            // Add clients
            if (data.clients && data.clients.length > 0) {
                data.clients.forEach(client => {
                    const option = document.createElement('option');
                    option.value = client.company_id;
                    option.textContent = `${client.name} (${client.company_id})`;
                    option.dataset.clientName = client.name;
                    clientSelect.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('Error loading clients:', error);
            showToast('Failed to load clients', 'danger');
        });
}

// Store current filters and client data
let currentFilters = { channel: '', status: '', days: '' };
let currentClientData = null;

function handleClientChange(event) {
    const clientSelect = event.target;
    const clientId = clientSelect.value;
    const selectedOption = clientSelect.options[clientSelect.selectedIndex];
    const clientName = selectedOption.dataset.clientName || selectedOption.textContent.split(' (')[0];
    
    if (!clientId) {
        // Clear data when no client selected
        clearClientData();
        hideCompanyDashboard();
        return;
    }
    
    // Reset filters
    currentFilters = { channel: '', status: '', days: '' };
    resetFilters();
    
    // Show company dashboard
    showCompanyDashboard(clientName);
    
    // Show loading state
    const activityList = document.getElementById('activityList');
    if (activityList) {
        activityList.innerHTML = '<p class="muted">Loading client data...</p>';
    }
    
    // Fetch client data
    loadClientData(clientId, clientName);
}

function loadClientData(clientId, clientName) {
    // Build query string from filters
    const params = new URLSearchParams();
    if (currentFilters.channel) params.append('channel', currentFilters.channel);
    if (currentFilters.status) params.append('status', currentFilters.status);
    if (currentFilters.days) params.append('days', currentFilters.days);
    
    const url = `${backendBaseUrl}/api/outreach/clients/${clientId}${params.toString() ? '?' + params.toString() : ''}`;
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showToast(`Error: ${data.error}`, 'danger');
                return;
            }
            
            currentClientData = data;
            
            // Update company name in dashboard (use name from API if available)
            const displayName = data.metrics?.client_name || clientName;
            showCompanyDashboard(displayName);
            
            // Update KPIs with trends
            if (data.metrics) {
                updateKPIsFromMetrics(data.metrics);
            }
            
            // Update client summary
            if (data.summary) {
                updateClientSummary(data.summary, displayName);
            }
            
            // Update top contacts
            if (data.top_contacts) {
                updateTopContacts(data.top_contacts);
            }
            
            // Update contacts table
            if (data.contacts_with_details) {
                updateContactsTable(data.contacts_with_details);
            }
            
            // Update activities
            const activityList = document.getElementById('activityList');
            if (data.activities && activityList) {
                renderActivities(data.activities);
            }
        })
        .catch(error => {
            console.error('Error loading client data:', error);
            showToast('Failed to load client data', 'danger');
            const activityList = document.getElementById('activityList');
            if (activityList) {
                activityList.innerHTML = '<p class="muted">Error loading activities</p>';
            }
        });
}

function showCompanyDashboard(companyName) {
    const companyDashboard = document.getElementById('companyDashboard');
    const titleElement = document.getElementById('companyDashboardTitle');
    const subtitleElement = document.getElementById('companyDashboardSubtitle');
    
    if (companyDashboard && titleElement && subtitleElement) {
        titleElement.textContent = `${companyName} Dashboard`;
        subtitleElement.textContent = `Viewing outreach data for ${companyName}`;
        companyDashboard.style.display = 'flex';
    }
}

function hideCompanyDashboard() {
    const companyDashboard = document.getElementById('companyDashboard');
    if (companyDashboard) {
        companyDashboard.style.display = 'none';
    }
}

function updateKPIsFromMetrics(metrics) {
    // Update LinkedIn KPI
    const linkedinValue = metrics.linkedin_outreach || 0;
    document.getElementById('kpi-linkedin').textContent = linkedinValue;
    updateKPITrend('linkedin', 'linkedin_outreach', linkedinValue, metrics.trends);
    
    // Update Email KPI
    const emailValue = metrics.email_sends || 0;
    document.getElementById('kpi-email').textContent = emailValue;
    updateKPITrend('email', 'email_sends', emailValue, metrics.trends);
    
    // Update Calls KPI
    const callsValue = metrics.calls_placed || 0;
    document.getElementById('kpi-calls').textContent = callsValue;
    updateKPITrend('calls', 'calls_placed', callsValue, metrics.trends);
    
    // Update HubSpot KPI
    const hubspotValue = metrics.hubspot_activities || 0;
    document.getElementById('kpi-hubspot').textContent = hubspotValue;
    updateKPITrend('hubspot', 'hubspot_activities', hubspotValue, metrics.trends);
}

function updateKPITrend(kpiId, trendKey, value, trends) {
    const trendElement = document.getElementById(`kpi-${kpiId}-trend`);
    if (!trendElement) return;
    
    if (trends && trends[trendKey]) {
        const trend = trends[trendKey];
        const arrow = trend.direction === 'up' ? '▲' : trend.direction === 'down' ? '▼' : '—';
        const sign = trend.change_absolute >= 0 ? '+' : '';
        const trendClass = trend.direction === 'up' ? 'kpi__trend--up' : 
                          trend.direction === 'down' ? 'kpi__trend--down' : 
                          'kpi__trend--neutral';
        
        trendElement.className = `kpi__trend ${trendClass}`;
        trendElement.innerHTML = `
            <span class="kpi__trend-arrow">${arrow}</span>
            <span>${Math.abs(trend.change_percent)}% vs last month</span>
            <span>(${sign}${trend.change_absolute})</span>
        `;
    } else {
        trendElement.innerHTML = '';
    }
}

function updateClientSummary(summary, clientName) {
    const summarySection = document.getElementById('clientSummary');
    const titleElement = document.getElementById('clientSummaryTitle');
    
    if (summarySection && titleElement) {
        titleElement.textContent = `${clientName} at a glance:`;
        summarySection.style.display = 'block';
        
        document.getElementById('summary-decision-makers').textContent = summary.decision_makers_engaged || 0;
        document.getElementById('summary-activities-week').textContent = summary.activities_this_week || 0;
        document.getElementById('summary-pending').textContent = summary.pending_followups || 0;
        document.getElementById('summary-revived').textContent = summary.cold_leads_revived || 0;
        document.getElementById('summary-score').textContent = summary.engagement_score || 0;
    }
}

function updateTopContacts(contacts) {
    const topContactsSection = document.getElementById('topContacts');
    const topContactsList = document.getElementById('topContactsList');
    const viewAllBtn = document.getElementById('viewAllContactsBtn');
    
    if (!topContactsSection || !topContactsList) return;
    
    if (contacts.length === 0) {
        topContactsSection.style.display = 'none';
        return;
    }
    
    topContactsSection.style.display = 'block';
    if (viewAllBtn) viewAllBtn.style.display = 'inline-flex';
    
    topContactsList.innerHTML = contacts.map(contact => {
        const engagementClass = `contact-card__engagement--${contact.engagement_level.toLowerCase()}`;
        return `
            <div class="contact-card">
                <div class="contact-card__info">
                    <div class="contact-card__name">${escapeHtml(contact.name)}</div>
                    <div class="contact-card__title">${escapeHtml(contact.title || '')}</div>
                </div>
                <div class="contact-card__meta">
                    <div class="contact-card__interactions">${contact.interaction_count} interactions</div>
                    <span class="contact-card__engagement ${engagementClass}">${contact.engagement_level}</span>
                </div>
            </div>
        `;
    }).join('');
}

function updateContactsTable(contacts) {
    const contactsTableSection = document.getElementById('contactsTableSection');
    const contactsTableBody = document.getElementById('contactsTableBody');
    
    if (!contactsTableSection || !contactsTableBody) return;
    
    if (contacts.length === 0) {
        contactsTableSection.style.display = 'none';
        return;
    }
    
    contactsTableSection.style.display = 'block';
    
    contactsTableBody.innerHTML = contacts.map(contact => {
        const status = contact.status || 'Not Started';
        const statusClass = `contact-status--${status.toLowerCase().replace(' ', '-')}`;
        const channels = contact.channels || [];
        const lastContacted = formatLastContacted(contact.last_contacted);
        
        // Build channels HTML
        const channelsHTML = channels.length > 0 
            ? channels.map(channel => {
                const channelLower = channel.toLowerCase();
                let channelClass = 'channel-badge';
                let channelLabel = channel;
                let channelIcon = '';
                
                if (channelLower.includes('linkedin')) {
                    channelClass += ' channel-badge--linkedin';
                    channelLabel = 'LinkedIn';
                    channelIcon = '<svg class="channel-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>';
                } else if (channelLower.includes('email')) {
                    channelClass += ' channel-badge--email';
                    channelLabel = 'Email';
                    channelIcon = '<svg class="channel-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>';
                } else if (channelLower.includes('call')) {
                    channelClass += ' channel-badge--call';
                    channelLabel = 'Call';
                    channelIcon = '<svg class="channel-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>';
                } else if (channelLower.includes('hubspot')) {
                    channelClass += ' channel-badge--hubspot';
                    channelLabel = 'HubSpot';
                }
                
                return `<span class="${channelClass}">${channelIcon}${channelLabel}</span>`;
            }).join('')
            : '<span class="muted">None</span>';
        
        return `
            <tr>
                <td>
                    <input type="checkbox" class="contact-row__checkbox" data-contact-id="${escapeHtml(contact.contact_id)}">
                </td>
                <td>
                    <div class="contact-row__name">${escapeHtml(contact.name)}</div>
                    <div class="contact-row__title">${escapeHtml(contact.title || '')}</div>
                </td>
                <td class="contact-row__company">${escapeHtml(contact.company_id || '')}</td>
                <td>
                    <span class="contact-status ${statusClass}">${escapeHtml(status)}</span>
                </td>
                <td>
                    <div class="contact-channels">${channelsHTML}</div>
                </td>
                <td>
                    <span class="contact-last-contacted ${lastContacted.never ? 'contact-last-contacted--never' : ''}">${escapeHtml(lastContacted.text)}</span>
                </td>
                <td>
                    <button class="contact-row__menu-btn" aria-label="More options"></button>
                </td>
            </tr>
        `;
    }).join('');
}

function formatLastContacted(isoString) {
    if (!isoString) {
        return { text: 'Never', never: true };
    }
    
    try {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) {
            const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
            if (diffHours === 0) {
                const diffMins = Math.floor(diffMs / (1000 * 60));
                return { text: diffMins <= 1 ? 'Just now' : `${diffMins} minutes ago`, never: false };
            }
            return { text: diffHours === 1 ? '1 hour ago' : `${diffHours} hours ago`, never: false };
        } else if (diffDays === 1) {
            return { text: 'Yesterday', never: false };
        } else if (diffDays < 7) {
            return { text: `${diffDays} days ago`, never: false };
        } else if (diffDays < 30) {
            const weeks = Math.floor(diffDays / 7);
            return { text: `${weeks} ${weeks === 1 ? 'week' : 'weeks'} ago`, never: false };
        } else {
            const months = Math.floor(diffDays / 30);
            return { text: `${months} ${months === 1 ? 'month' : 'months'} ago`, never: false };
        }
    } catch (e) {
        return { text: 'Unknown', never: false };
    }
}

function renderActivities(activities) {
    const activityList = document.getElementById('activityList');
    if (!activityList) return;
    
    if (activities.length === 0) {
        activityList.innerHTML = '<p class="muted">No activities found</p>';
        return;
    }
    
    // Timeline layout
    activityList.innerHTML = activities.map(activity => {
        let timestamp;
        try {
            const date = new Date(activity.timestamp || activity.datetime);
            timestamp = date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            const dateOnly = date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric'
            });
        } catch (e) {
            timestamp = activity.timestamp || 'Unknown';
        }
        
        const statusClass = activity.status?.toLowerCase() === 'success' ? 'success' : 
                           activity.status?.toLowerCase() === 'pending' ? 'warning' : 'danger';
        
        const dateOnly = new Date(activity.timestamp || activity.datetime).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric'
        });
        
        return `
            <div class="activity-item activity-item--timeline">
                <div class="activity-item__date">${dateOnly}</div>
                <div class="activity-item__content">
                    <div class="activity-item__header">
                        <span class="activity-item__channel">${escapeHtml(activity.channel)}</span>
                        <span class="activity-item__type">${escapeHtml(activity.type)}</span>
                        <span class="activity-item__status activity-item__status--${statusClass}">${escapeHtml(activity.status)}</span>
                    </div>
                    <div class="activity-item__summary">${escapeHtml(activity.summary || activity.notes || '')}</div>
                    <div class="activity-item__meta">
                        <span class="activity-item__timestamp">${timestamp}</span>
                        <span class="activity-item__id">${escapeHtml(activity.activity_id)}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function clearClientData() {
    // Reset KPIs
    document.getElementById('kpi-linkedin').textContent = '-';
    document.getElementById('kpi-email').textContent = '-';
    document.getElementById('kpi-calls').textContent = '-';
    document.getElementById('kpi-hubspot').textContent = '-';
    
    // Clear trends
    ['linkedin', 'email', 'calls', 'hubspot'].forEach(kpi => {
        const trendEl = document.getElementById(`kpi-${kpi}-trend`);
        if (trendEl) trendEl.innerHTML = '';
    });
    
    // Clear activities
    const activityList = document.getElementById('activityList');
    if (activityList) {
        activityList.innerHTML = '<p class="muted">Select a client to view activities</p>';
    }
    
    // Hide sections
    hideCompanyDashboard();
    const summarySection = document.getElementById('clientSummary');
    const topContactsSection = document.getElementById('topContacts');
    const contactsTableSection = document.getElementById('contactsTableSection');
    if (summarySection) summarySection.style.display = 'none';
    if (topContactsSection) topContactsSection.style.display = 'none';
    if (contactsTableSection) contactsTableSection.style.display = 'none';
    
    currentClientData = null;
}

function resetFilters() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        if (btn.dataset.value === '') {
            btn.classList.add('filter-btn--active');
        } else {
            btn.classList.remove('filter-btn--active');
        }
    });
}

function showKPIModal(kpiType) {
    if (!currentClientData || !currentClientData.metrics) return;
    
    const modal = document.getElementById('kpiModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    if (!modal || !modalTitle || !modalBody) return;
    
    const metrics = currentClientData.metrics;
    const kpiLabels = {
        linkedin: 'LinkedIn Outreach',
        email: 'Email Campaigns',
        calls: 'Calls Placed',
        hubspot: 'HubSpot Activities'
    };
    
    const kpiData = {
        linkedin: {
            value: metrics.linkedin_outreach,
            label: 'LinkedIn Outreach',
            details: [
                { label: 'Total Outreach', value: metrics.linkedin_outreach },
                { label: 'Engagement Score', value: metrics.engagement_score }
            ]
        },
        email: {
            value: metrics.email_sends,
            label: 'Email Campaigns',
            details: [
                { label: 'Emails Sent', value: metrics.email_sends },
                { label: 'Emails Opened', value: metrics.email_opens },
                { label: 'Replies Received', value: metrics.email_replies },
                { label: 'Success Rate', value: metrics.email_sends > 0 ? `${Math.round((metrics.email_replies / metrics.email_sends) * 100)}%` : '0%' },
                { label: 'Campaigns Contributing', value: currentClientData.campaigns?.filter(c => c.channel_primary === 'Email' || c.type === 'Email').length || 0 }
            ]
        },
        calls: {
            value: metrics.calls_placed,
            label: 'Calls Placed',
            details: [
                { label: 'Total Calls', value: metrics.calls_placed },
                { label: 'Meetings Booked', value: metrics.meetings_booked },
                { label: 'Conversion Rate', value: metrics.calls_placed > 0 ? `${Math.round((metrics.meetings_booked / metrics.calls_placed) * 100)}%` : '0%' }
            ]
        },
        hubspot: {
            value: metrics.hubspot_activities,
            label: 'HubSpot Activities',
            details: [
                { label: 'Total Activities', value: metrics.hubspot_activities },
                { label: 'Engagement Score', value: metrics.engagement_score }
            ]
        }
    };
    
    const data = kpiData[kpiType];
    if (!data) return;
    
    modalTitle.textContent = data.label;
    modalBody.innerHTML = data.details.map(detail => `
        <div class="modal__stat">
            <span class="modal__stat-label">${detail.label}</span>
            <span class="modal__stat-value">${detail.value}</span>
        </div>
    `).join('');
    
    modal.style.display = 'flex';
}

function showToast(message, type = 'info') {
    // Simple toast notification (you can enhance this)
    console.log(`[${type.toUpperCase()}] ${message}`);
}

