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
    
    // Send button click
    sendButton.addEventListener('click', sendMessage);
    
    // Enter key in input
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
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

