// static/js/script.js
/**
 * VOCAL LENS - MAIN APPLICATION SCRIPT
 * Handles UI, API calls, and integrates with voice layer
 */

// ==================== STATE MANAGEMENT ====================
const AppState = {
    currentQuery: null,
    conversationHistory: [],
    pendingQuestions: [],
    selectedPhotos: new Set(),
    userPreferences: {},
    darkMode: false,
    currentContext: null
};

// ==================== DOM ELEMENTS ====================
const elements = {
    micBtn: document.getElementById('micBtn'),
    searchInput: document.getElementById('searchInput'),
    searchBtn: document.getElementById('searchBtn'),
    themeToggle: document.getElementById('themeToggle'),
    resultDiv: document.getElementById('result'),
    loadingDiv: document.getElementById('loading'),
    aiChatBox: document.getElementById('aiChatBox'),
    aiReasoning: document.getElementById('aiReasoning'),
    interactiveArea: document.getElementById('interactiveArea')
};

// ==================== VOICE INTEGRATION ====================
let voiceIntegration;
let voiceProcessor;

// ==================== AI INTERACTION CLASS ====================
class AIInteraction {
    // Add message from AI to chat box
    static addAIMessage(message, type = 'info') {
        const chatBox = elements.aiChatBox;
        if (!chatBox) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `ai-message ${type}`;
        messageDiv.innerHTML = `
            <span class="ai-icon">🤖</span>
            <p>${message}</p>
        `;
        
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }
    
    // Show AI's reasoning process
    static showReasoning(steps) {
        const reasoningDiv = elements.aiReasoning;
        if (!reasoningDiv || !steps || steps.length === 0) return;
        
        reasoningDiv.classList.remove('hidden');
        reasoningDiv.innerHTML = '<h3>🧠 AI Thinking:</h3>';
        
        steps.forEach((step, index) => {
            reasoningDiv.innerHTML += `
                <div class="reasoning-step">
                    <span class="step-number">${index + 1}</span>
                    <span class="step-text">${step}</span>
                </div>
            `;
        });
    }
    
    // Show photo selection grid for identification
    static showIdentificationGrid(photos, question) {
        const area = elements.interactiveArea;
        if (!area) return;
        
        this.addAIMessage(question, 'question');
        
        let html = '<div class="identification-grid">';
        photos.forEach(photo => {
            html += `
                <div class="selectable-photo" onclick="AISelection.togglePhoto('${photo.id}')" id="photo-${photo.id}">
                    <img src="${photo.url || '/static/samples/placeholder.jpg'}" alt="Selectable photo">
                    <span class="checkmark">✓</span>
                </div>
            `;
        });
        html += `
            <div style="grid-column: 1/-1; text-align: center; margin-top: 20px;">
                <button onclick="AISelection.submitSelection()" class="btn btn-primary">
                    Confirm Selection
                </button>
            </div>
        </div>`;
        
        area.innerHTML = html;
        AppState.selectedPhotos.clear();
    }
    
    // Show confirmation after learning
    static showLearningConfirmation(person, count) {
        this.addAIMessage(
            `✅ I've learned to recognize your ${person}! Found ${count} photos with ${person}.`,
            'success'
        );
        
        // Offer next actions
        elements.interactiveArea.innerHTML = `
            <div style="display: flex; gap: 10px; justify-content: center; margin-top: 20px;">
                <button onclick="createAlbum()" class="btn btn-success">
                    ✨ Create Album Now
                </button>
                <button onclick="findMorePhotos()" class="btn btn-info">
                    🔍 Find More Photos
                </button>
            </div>
        `;
    }
    
    // Clear AI chat
    static clearChat() {
        if (elements.aiChatBox) {
            elements.aiChatBox.innerHTML = '';
        }
    }
    
    // Clear reasoning
    static clearReasoning() {
        if (elements.aiReasoning) {
            elements.aiReasoning.classList.add('hidden');
            elements.aiReasoning.innerHTML = '<h3>🧠 AI Thinking:</h3>';
        }
    }
    
    // Clear interactive area
    static clearInteractive() {
        if (elements.interactiveArea) {
            elements.interactiveArea.innerHTML = '';
        }
    }
}

// ==================== AI SELECTION HANDLER ====================
class AISelection {
    static togglePhoto(photoId) {
        const photoElement = document.getElementById(`photo-${photoId}`);
        if (!photoElement) return;
        
        if (AppState.selectedPhotos.has(photoId)) {
            AppState.selectedPhotos.delete(photoId);
            photoElement.classList.remove('selected');
        } else {
            AppState.selectedPhotos.add(photoId);
            photoElement.classList.add('selected');
        }
    }
    
    static async submitSelection() {
        const selectedIds = Array.from(AppState.selectedPhotos);
        
        if (selectedIds.length === 0) {
            AIInteraction.addAIMessage('Please select at least one photo.', 'error');
            return;
        }
        
        // Send selection to backend
        try {
            const response = await fetch('/learn/identify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    photoIds: selectedIds,
                    context: AppState.currentContext
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                AIInteraction.showLearningConfirmation(
                    data.person,
                    data.photoCount
                );
                
                // Clear selection area
                elements.interactiveArea.innerHTML = '';
                AppState.selectedPhotos.clear();
                
                // If album creation was requested, create it
                if (data.createAlbum) {
                    createAlbum();
                }
                
                // Speak confirmation
                if (voiceIntegration) {
                    voiceIntegration.speak(`I've learned to recognize your ${data.person}. Found ${data.photoCount} photos.`);
                }
            }
        } catch (error) {
            console.error('Error submitting selection:', error);
            AIInteraction.addAIMessage('Error saving your selection. Please try again.', 'error');
        }
    }
}

// ==================== SEARCH FUNCTION ====================
async function searchImages(query) {
    const searchText = query || elements.searchInput.value;
    if (!searchText) return;
    
    // Show loading
    elements.loadingDiv.classList.remove('hidden');
    elements.resultDiv.innerHTML = '';
    
    // Clear previous AI messages but keep reasoning
    AIInteraction.clearChat();
    AIInteraction.clearInteractive();
    
    // Add user message
    AIInteraction.addAIMessage(`You: "${searchText}"`, 'info');
    
    try {
        const response = await fetch('/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                query: searchText,
                context: AppState.conversationHistory
            })
        });
        
        const data = await response.json();
        
        // Show AI's reasoning if provided
        if (data.reasoning) {
            AIInteraction.showReasoning(data.reasoning);
        }
        
        // Handle AI questions (needs user input)
        if (data.needsInput) {
            if (data.type === 'identify_person') {
                AIInteraction.showIdentificationGrid(
                    data.candidatePhotos,
                    data.question
                );
                AppState.currentContext = data.context;
            } else {
                AIInteraction.addAIMessage(data.question, 'question');
            }
            
            // Speak the question
            if (voiceIntegration) {
                voiceIntegration.speak(data.question);
            }
            return;
        }
        
        // Handle results
        if (data.results) {
            displayResults(data.results);
            
            // Voice feedback
            const voiceResponse = data.voice_response || 
                `Found ${data.results.count} photos. ${data.results.title}`;
            
            if (voiceIntegration) {
                voiceIntegration.speak(voiceResponse);
            }
            
            // If AI learned something
            if (data.learned) {
                AIInteraction.showLearningConfirmation(
                    data.learned.person,
                    data.learned.count
                );
            }
        }
        
        // Save to conversation history
        AppState.conversationHistory.push({
            query: searchText,
            response: data
        });
        
    } catch (error) {
        console.error('Error:', error);
        AIInteraction.addAIMessage('Error searching photos. Please try again.', 'error');
        elements.resultDiv.innerHTML = '<p class="error">Error searching photos</p>';
    } finally {
        elements.loadingDiv.classList.add('hidden');
    }
}

// ==================== DISPLAY RESULTS ====================
function displayResults(data) {
    let html = `<h2>${data.title} (${data.count} photos)</h2>`;
    
    if (data.images && data.images.length > 0) {
        html += '<div class="album-grid">';
        data.images.forEach(img => {
            html += `
                <div class="album-card" onclick="viewPhoto('${img.id}')">
                    <img src="${img.url || '/static/samples/placeholder.jpg'}" 
                         alt="${img.tags || 'Photo'}">
                    <div class="album-content">
                        <div class="album-title">${img.title || 'Photo'}</div>
                        <div class="album-meta">
                            ${img.date || ''} ${img.location ? '• ' + img.location : ''}
                        </div>
                        <div class="album-tags">
                            ${(img.tags || []).map(tag => 
                                `<span class="tag">${tag}</span>`
                            ).join('')}
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
    } else {
        html += '<p>No photos found. Try a different search.</p>';
    }
    
    elements.resultDiv.innerHTML = html;
}

// ==================== DARK MODE ====================
function toggleTheme() {
    document.body.classList.toggle('dark-mode');
    AppState.darkMode = !AppState.darkMode;
    elements.themeToggle.textContent = AppState.darkMode ? '☀️ Light Mode' : '🌓 Dark Mode';
}

// ==================== VIEW PHOTO ====================
function viewPhoto(photoId) {
    console.log('View photo:', photoId);
    // Could implement lightbox or full view
}

// ==================== CREATE ALBUM ====================
async function createAlbum() {
    if (!AppState.currentContext) return;
    
    try {
        const response = await fetch('/create-album', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(AppState.currentContext)
        });
        
        const data = await response.json();
        
        if (data.success) {
            AIInteraction.addAIMessage(
                `✅ Created album "${data.albumTitle}" with ${data.photoCount} photos!`,
                'success'
            );
            
            if (voiceIntegration) {
                voiceIntegration.speak(`Created album ${data.albumTitle} with ${data.photoCount} photos.`);
            }
            
            if (data.album) {
                displayResults(data.album);
            }
        }
    } catch (error) {
        console.error('Error creating album:', error);
        AIInteraction.addAIMessage('Error creating album.', 'error');
    }
}

// ==================== FIND MORE PHOTOS ====================
async function findMorePhotos() {
    if (!AppState.currentContext) return;
    
    try {
        const response = await fetch('/find-similar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(AppState.currentContext)
        });
        
        const data = await response.json();
        
        if (data.photos && data.photos.length > 0) {
            AIInteraction.addAIMessage(
                `Found ${data.photos.length} more photos!`,
                'success'
            );
            
            if (voiceIntegration) {
                voiceIntegration.speak(`Found ${data.photos.length} more photos.`);
            }
        }
    } catch (error) {
        console.error('Error finding more photos:', error);
    }
}

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', () => {
    // Initialize voice integration
    voiceIntegration = new VoiceIntegration();
    voiceProcessor = new VoiceCommandProcessor();
    
    // Set up voice callbacks
    voiceIntegration.onListeningStarted = () => {
        elements.micBtn.classList.add('listening');
        AIInteraction.addAIMessage('🎤 Listening... Speak your command', 'info');
    };
    
    voiceIntegration.onListeningEnded = () => {
        elements.micBtn.classList.remove('listening');
    };
    
    voiceIntegration.onVoiceResult = (result) => {
        const processed = voiceProcessor.processVoiceInput(result.transcript);
        
        AIInteraction.addAIMessage(
            `I heard: "${result.transcript}" (confidence: ${Math.round(result.confidence * 100)}%)`,
            'success'
        );
        
        elements.searchInput.value = processed.query;
        searchImages(processed.query);
    };
    
    voiceIntegration.onVoiceError = (error) => {
        elements.micBtn.classList.remove('listening');
        
        let message = 'Voice recognition error. ';
        switch(error) {
            case 'not-allowed':
                message += 'Please allow microphone access in your browser.';
                break;
            case 'no-speech':
                message += 'No speech detected. Please try again.';
                break;
            case 'audio-capture':
                message += 'No microphone found. Please check your microphone.';
                break;
            case 'network':
                message += 'Network error. Please check your connection.';
                break;
            case 'not-supported':
                message += 'Voice recognition is not supported in this browser. Try Chrome or Edge.';
                elements.micBtn.classList.add('disabled');
                elements.micBtn.disabled = true;
                break;
            default:
                message += 'Please try again or type your query.';
        }
        AIInteraction.addAIMessage(message, 'error');
    };
    
    voiceIntegration.onNoMatch = () => {
        elements.micBtn.classList.remove('listening');
        AIInteraction.addAIMessage("I didn't catch that. Please try again.", 'question');
    };
    
    voiceIntegration.onSpeechStarted = () => {
        console.log('Speaking started');
    };
    
    voiceIntegration.onSpeechEnded = () => {
        console.log('Speaking ended');
    };
    
    voiceIntegration.onSpeechError = (error) => {
        console.error('Speech error:', error);
    };

    elements.micBtn.addEventListener('click', () => {
    voiceIntegration.startListening();
});
    
    // Event listeners
    elements.searchBtn.addEventListener('click', () => searchImages());
    elements.themeToggle.addEventListener('click', toggleTheme);
    
    elements.searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchImages();
    });
    
    // Welcome message
    setTimeout(() => {
        AIInteraction.addAIMessage(
            "👋 Hi! I'm Vocal Lens. I can understand natural language and learn from you. " +
            "Try asking: 'Show me my sister's wedding photos' or 'Find pictures from Goa trip'",
            'info'
        );
        
        // Voice welcome
        if (voiceIntegration && voiceIntegration.voiceSupported) {
            voiceIntegration.speak(
                "Hello! I'm Vocal Lens. I can understand natural language and learn from you. " +
                "Try asking: show me my sister's wedding photos",
                { rate: 0.85 }
            );
        }
    }, 1000);
});

// Export functions for HTML onclick handlers
window.searchImages = searchImages;
window.toggleTheme = toggleTheme;
window.AISelection = AISelection;
window.createAlbum = createAlbum;
window.findMorePhotos = findMorePhotos;
window.viewPhoto = viewPhoto;