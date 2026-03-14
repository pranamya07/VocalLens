// static/js/script.js

const AppState = {
    currentQuery: null,
    conversationHistory: [],
    selectedPhotos: new Set(),
    currentContext: null,
    darkMode: false
};

const elements = {
    landingPage: document.getElementById('landingPage'),
    resultsPage: document.getElementById('resultsPage'),
    micBtn: document.getElementById('micBtn'),
    micBtnResults: document.getElementById('micBtnResults'),
    searchInput: document.getElementById('searchInput'),
    searchInputResults: document.getElementById('searchInputResults'),
    searchBtn: document.getElementById('searchBtn'),
    themeToggle: document.getElementById('themeToggle'),
    resultDiv: document.getElementById('result'),
    loadingDiv: document.getElementById('loading'),
    aiChatBox: document.getElementById('aiChatBox'),
    aiReasoning: document.getElementById('aiReasoning'),
    interactiveArea: document.getElementById('interactiveArea'),
    photosLabel: document.getElementById('photosLabel')
};

let voiceIntegration;
let voiceProcessor;
let activeMicBtn = null;

// ===================== LIGHTBOX =====================
function openLightbox(url) {
    const existing = document.getElementById('lightbox');
    if (existing) existing.remove();

    const lb = document.createElement('div');
    lb.id = 'lightbox';
    lb.style.cssText = `
        position: fixed; inset: 0; z-index: 9999;
        background: rgba(0,0,0,0.92);
        display: flex; align-items: center; justify-content: center;
        cursor: zoom-out;
    `;
    lb.innerHTML = `
        <img src="${encodeURI(url)}" style="
            max-width: 92vw; max-height: 92vh;
            border-radius: 12px;
            box-shadow: 0 8px 60px rgba(0,0,0,0.8);
            object-fit: contain;
        ">
        <button onclick="document.getElementById('lightbox').remove()" style="
            position: absolute; top: 20px; right: 28px;
            background: none; border: none;
            color: white; font-size: 36px;
            cursor: pointer; line-height: 1;
        ">✕</button>
    `;
    lb.addEventListener('click', (e) => {
        if (e.target === lb) lb.remove();
    });
    document.body.appendChild(lb);
}

// ===================== PAGE NAVIGATION =====================
function goToResults() {
    elements.landingPage.classList.add('hidden');
    elements.resultsPage.classList.remove('hidden');
}

function goBack() {
    elements.resultsPage.classList.add('hidden');
    elements.landingPage.classList.remove('hidden');
    elements.searchInput.value = '';
}

function useHint(el) {
    const text = el.textContent.replace(/['"]/g, '');
    elements.searchInput.value = text;
    elements.searchInput.focus();
}

// ===================== CHAT SYSTEM =====================
class Chat {
    static add(message, type = 'ai', subtype = 'info') {
        const box = elements.aiChatBox;
        if (!box) return;

        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${type === 'user' ? 'user' : subtype}`;

        const avatar = document.createElement('div');
        avatar.className = 'bubble-avatar';
        avatar.textContent = type === 'user' ? 'U' : 'AI';

        const content = document.createElement('div');
        content.className = 'bubble-content';
        content.textContent = message;

        bubble.appendChild(avatar);
        bubble.appendChild(content);
        box.appendChild(bubble);
        box.scrollTop = box.scrollHeight;
    }

    static addUser(message) { this.add(message, 'user'); }
    static addAI(message, subtype = 'info') { this.add(message, 'ai', subtype); }

    static showReasoning(steps) {
        const div = elements.aiReasoning;
        if (!div || !steps?.length) return;

        div.classList.remove('hidden');
        div.innerHTML = `
            <div class="reasoning-title">
                <div class="reasoning-dot"></div>
                Thinking
            </div>
        `;
        steps.forEach((step, i) => {
            div.innerHTML += `
                <div class="reasoning-step">
                    <span class="step-num">${i + 1}.</span>
                    <span>${step}</span>
                </div>
            `;
        });
    }

    static hideReasoning() {
        elements.aiReasoning.classList.add('hidden');
        elements.aiReasoning.innerHTML = '';
    }

    static clear() {
        elements.aiChatBox.innerHTML = '';
        this.hideReasoning();
        elements.interactiveArea.innerHTML = '';
    }

    static showIdentificationGrid(photos, question) {
        Chat.addAI(question, 'question');

        let html = '<div class="identification-grid">';
        photos.forEach(photo => {
            html += `
                <div class="selectable-photo" onclick="Selection.toggle('${photo.id}')" id="photo-${photo.id}">
                    <img src="${photo.url || '/static/samples/placeholder.jpg'}" alt="Photo">
                    <span class="checkmark">✓</span>
                </div>
            `;
        });
        html += `</div>
            <button class="confirm-btn" onclick="Selection.submit()">Confirm Selection</button>`;
        elements.interactiveArea.innerHTML = html;
        AppState.selectedPhotos.clear();
    }

    static showLearningConfirmation(person, count) {
        Chat.addAI(`Learned: this is your ${person}. Found ${count} photos with them.`, 'success');
        elements.interactiveArea.innerHTML = `
            <div class="next-actions">
                <button class="action-btn" onclick="createAlbum()">Create album now</button>
                <button class="action-btn" onclick="findMorePhotos()">Find more photos</button>
            </div>
        `;
    }
}

// ===================== SELECTION =====================
class Selection {
    static toggle(photoId) {
        const el = document.getElementById(`photo-${photoId}`);
        if (!el) return;
        if (AppState.selectedPhotos.has(photoId)) {
            AppState.selectedPhotos.delete(photoId);
            el.classList.remove('selected');
        } else {
            AppState.selectedPhotos.add(photoId);
            el.classList.add('selected');
        }
    }

    static async submit() {
        const ids = Array.from(AppState.selectedPhotos);
        if (!ids.length) { Chat.addAI('Please select at least one photo.', 'error'); return; }

        try {
            const res = await fetch('/learn/identify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ photoIds: ids, context: AppState.currentContext })
            });
            const data = await res.json();
            if (data.success) {
                Chat.showLearningConfirmation(data.person, data.photoCount);
                elements.interactiveArea.innerHTML = '';
                AppState.selectedPhotos.clear();
                if (data.createAlbum) createAlbum();
                if (voiceIntegration) voiceIntegration.speak(`Learned to recognize your ${data.person}.`);
            }
        } catch(err) {
            Chat.addAI('Error saving selection. Try again.', 'error');
        }
    }
}

// ===================== SEARCH =====================
async function searchImages(query) {
    const text = query || elements.searchInput.value;
    if (!text?.trim()) return;

    goToResults();
    elements.searchInputResults.value = text;

    elements.loadingDiv.classList.remove('hidden');
    elements.resultDiv.innerHTML = '';
    Chat.clear();
    Chat.addUser(text);

    try {
        const res = await fetch('/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: text, context: AppState.conversationHistory })
        });
        const data = await res.json();

        if (data.reasoning) Chat.showReasoning(data.reasoning);

        if (data.needsInput) {
            if (data.type === 'identify_person') {
                Chat.showIdentificationGrid(data.candidatePhotos, data.question);
                AppState.currentContext = data.context;
            } else {
                Chat.addAI(data.question, 'question');
            }
            if (voiceIntegration) voiceIntegration.speak(data.question);
            return;
        }

        if (data.results) {
            displayResults(data.results);
            const msg = data.voice_response || `Found ${data.results.count} photos.`;
            Chat.addAI(msg, 'success');
            if (voiceIntegration) voiceIntegration.speak(msg);
            if (data.learned) Chat.showLearningConfirmation(data.learned.person, data.learned.count);
        }

        AppState.conversationHistory.push({ query: text, response: data });

    } catch(err) {
        console.error('Search error:', err);
        Chat.addAI('Error searching photos. Please try again.', 'error');
    } finally {
        elements.loadingDiv.classList.add('hidden');
    }
}

function searchFromResults() {
    const text = elements.searchInputResults.value;
    if (!text?.trim()) return;
    elements.searchInput.value = text;
    searchImages(text);
}

// ===================== DISPLAY RESULTS =====================
function displayResults(data) {
    if (elements.photosLabel) {
        elements.photosLabel.textContent = data.title || 'Photo Results';
    }

    if (!data.images?.length) {
        elements.resultDiv.innerHTML = '<p class="no-results">No photos found. Try a different search.</p>';
        return;
    }

    let html = `<p class="results-title">${data.count} photos</p><div class="album-grid">`;
    data.images.forEach(img => {
        const url = img.url || '/static/samples/placeholder.jpg';
        html += `
            <div class="album-card" onclick="openLightbox('${url}')">
                <img src="${encodeURI(url)}" alt="Photo" loading="lazy">
                <div class="album-content">
                    <div class="album-meta">${img.date || ''} ${img.location ? '· ' + img.location : ''}</div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    elements.resultDiv.innerHTML = html;
}

// ===================== MISC ACTIONS =====================
function viewPhoto(id) { console.log('View photo:', id); }

async function createAlbum() {
    if (!AppState.currentContext) return;
    try {
        const res = await fetch('/create-album', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(AppState.currentContext)
        });
        const data = await res.json();
        if (data.success) {
            Chat.addAI(`Created album "${data.albumTitle}" with ${data.photoCount} photos!`, 'success');
            if (voiceIntegration) voiceIntegration.speak(`Created album ${data.albumTitle}.`);
            if (data.album) displayResults(data.album);
        }
    } catch(err) { Chat.addAI('Error creating album.', 'error'); }
}

async function findMorePhotos() {
    if (!AppState.currentContext) return;
    try {
        const res = await fetch('/find-similar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(AppState.currentContext)
        });
        const data = await res.json();
        if (data.photos?.length) {
            Chat.addAI(`Found ${data.photos.length} more photos!`, 'success');
            if (voiceIntegration) voiceIntegration.speak(`Found ${data.photos.length} more photos.`);
        }
    } catch(err) { console.error('Error finding photos'); }
}

// ===================== THEME =====================
function toggleTheme() {
    AppState.darkMode = !AppState.darkMode;
    applyTheme();
}

function applyTheme() {
    document.body.classList.toggle('dark-mode', AppState.darkMode);
    document.body.classList.toggle('light-mode', !AppState.darkMode);
    localStorage.setItem('vocallens-theme', AppState.darkMode ? 'dark' : 'light');
}

function loadTheme() {
    const saved = localStorage.getItem('vocallens-theme');
    AppState.darkMode = saved === 'dark';
    applyTheme();
}

// ===================== VOICE SETUP =====================
function setupVoice(micBtn, onResult) {
    if (!voiceIntegration) return;
    activeMicBtn = micBtn;

    micBtn.addEventListener('click', () => voiceIntegration.startListening());

    voiceIntegration.onListeningStarted = () => {
        micBtn.classList.add('listening');
    };
    voiceIntegration.onListeningEnded = () => {
        micBtn.classList.remove('listening');
    };
    voiceIntegration.onVoiceResult = (result) => {
        const processed = voiceProcessor.processVoiceInput(result.transcript);
        onResult(processed.query);
    };
    voiceIntegration.onVoiceError = (error) => {
        micBtn.classList.remove('listening');
        const msgs = {
            'not-allowed': 'Allow microphone access and try again.',
            'no-speech': 'No speech detected. Try again.',
            'audio-capture': 'No microphone found.',
            'network': 'Network error.',
            'not-supported': 'Voice not supported. Try Chrome.'
        };
        const msg = msgs[error] || 'Voice error. Please try again.';
        if (elements.aiChatBox) Chat.addAI(msg, 'error');
        if (error === 'not-supported') { micBtn.disabled = true; micBtn.classList.add('disabled'); }
    };
    voiceIntegration.onNoMatch = () => {
        micBtn.classList.remove('listening');
        if (elements.aiChatBox) Chat.addAI("Didn't catch that. Try again.", 'question');
    };
}

// ===================== INIT =====================
document.addEventListener('DOMContentLoaded', () => {
    loadTheme();
    voiceIntegration = new VoiceIntegration();
    voiceProcessor = new VoiceCommandProcessor();

    setupVoice(elements.micBtn, (query) => {
        elements.searchInput.value = query;
        searchImages(query);
    });

    elements.micBtnResults.addEventListener('click', () => {
        activeMicBtn = elements.micBtnResults;
        voiceIntegration.onListeningStarted = () => elements.micBtnResults.classList.add('listening');
        voiceIntegration.onListeningEnded = () => elements.micBtnResults.classList.remove('listening');
        voiceIntegration.onVoiceResult = (result) => {
            const processed = voiceProcessor.processVoiceInput(result.transcript);
            elements.searchInputResults.value = processed.query;
            searchImages(processed.query);
        };
        voiceIntegration.startListening();
    });

    elements.searchBtn.addEventListener('click', () => searchImages());
    elements.themeToggle.addEventListener('click', toggleTheme);
    elements.searchInput.addEventListener('keypress', e => { if (e.key === 'Enter') searchImages(); });
    elements.searchInputResults.addEventListener('keypress', e => { if (e.key === 'Enter') searchFromResults(); });
});

// Expose globals
window.searchImages = searchImages;
window.searchFromResults = searchFromResults;
window.goBack = goBack;
window.useHint = useHint;
window.toggleTheme = toggleTheme;
window.Selection = Selection;
window.createAlbum = createAlbum;
window.findMorePhotos = findMorePhotos;
window.viewPhoto = viewPhoto;
window.openLightbox = openLightbox;