// State
let currentSessionId = null;
let isStreaming = false;

const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const sessionListEl = document.getElementById('sessionList');
const newChatBtn = document.getElementById('newChatBtn');

// Auto-resize textarea
inputEl.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 150) + 'px';
});

// Enter to send, Shift+Enter for newline
inputEl.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

newChatBtn.addEventListener('click', createSession);

// Create a new chat session
async function createSession() {
    const resp = await fetch('/api/sessions', { method: 'POST' });
    const data = await resp.json();
    currentSessionId = data.id;
    messagesEl.innerHTML = '';
    renderSessionItem(data);
    setActiveSession(data.id);
    inputEl.focus();
}

// Render a session item in sidebar
function renderSessionItem(session) {
    const div = document.createElement('div');
    div.className = 'session-item';
    div.dataset.id = session.id;
    div.onclick = () => loadSession(session.id);
    div.innerHTML = `
        <span class="session-title">${escapeHtml(session.title)}</span>
        <button class="session-delete" onclick="event.stopPropagation(); deleteSession(${session.id})">&times;</button>
    `;
    sessionListEl.prepend(div);
}

function setActiveSession(id) {
    document.querySelectorAll('.session-item').forEach(el => {
        el.classList.toggle('active', parseInt(el.dataset.id) === id);
    });
}

// Load a session and display its messages
async function loadSession(id) {
    currentSessionId = id;
    setActiveSession(id);
    const resp = await fetch(`/api/sessions/${id}/messages`);
    const messages = await resp.json();
    messagesEl.innerHTML = '';
    messages.forEach(msg => appendMessage(msg.role, msg.content));
    scrollToBottom();
}

// Delete a session
async function deleteSession(id) {
    if (!confirm('确定删除这个对话吗？')) return;
    await fetch(`/api/sessions/${id}`, { method: 'DELETE' });
    const el = document.querySelector(`.session-item[data-id="${id}"]`);
    if (el) el.remove();
    if (currentSessionId === id) {
        currentSessionId = null;
        messagesEl.innerHTML = '<div class="empty-state">选择或创建一个对话开始聊天</div>';
    }
}

// Send a message
async function sendMessage() {
    const content = inputEl.value.trim();
    if (!content || isStreaming) return;

    if (!currentSessionId) {
        await createSession();
    }

    inputEl.value = '';
    inputEl.style.height = 'auto';
    appendMessage('user', content);
    scrollToBottom();

    // Show typing indicator
    const assistantEl = appendMessage('assistant', '');
    const contentEl = assistantEl.querySelector('.message-content');
    contentEl.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    scrollToBottom();

    isStreaming = true;
    sendBtn.disabled = true;

    try {
        const resp = await fetch(`/api/chat/${currentSessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content }),
        });

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';
        contentEl.textContent = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const text = decoder.decode(value);
            const lines = text.split('\n');

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const data = JSON.parse(line.slice(6));
                if (data.error) {
                    contentEl.textContent = 'Error: ' + data.error;
                    break;
                }
                if (data.done) break;
                fullText += data.content;
                contentEl.innerHTML = formatMarkdown(fullText);
                scrollToBottom();
            }
        }

        // Update session title in sidebar
        updateSessionTitle(currentSessionId, content);

    } catch (err) {
        contentEl.textContent = '网络错误，请重试';
    } finally {
        isStreaming = false;
        sendBtn.disabled = false;
        inputEl.focus();
    }
}

// Append a message to the chat area
function appendMessage(role, content) {
    const div = document.createElement('div');
    div.className = `message ${role}`;
    const avatarText = role === 'user' ? 'U' : 'AI';
    div.innerHTML = `
        <div class="message-avatar">${avatarText}</div>
        <div class="message-content">${role === 'user' ? escapeHtml(content) : content}</div>
    `;
    messagesEl.appendChild(div);
    return div;
}

function updateSessionTitle(sessionId, firstMessage) {
    const title = firstMessage.length > 20 ? firstMessage.slice(0, 20) + '...' : firstMessage;
    const el = document.querySelector(`.session-item[data-id="${sessionId}"] .session-title`);
    if (el && el.textContent === '新对话') {
        el.textContent = title;
    }
}

function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Simple markdown-like formatting
function formatMarkdown(text) {
    let html = escapeHtml(text);

    // Code blocks
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // Line breaks
    html = html.replace(/\n/g, '<br>');

    return html;
}

// Show empty state on load
if (!currentSessionId) {
    messagesEl.innerHTML = '<div class="empty-state">选择或创建一个对话开始聊天</div>';
}
