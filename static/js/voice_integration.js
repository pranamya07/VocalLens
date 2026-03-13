// static/js/voice-integration.js
/**
 * COMPLETE VOICE INTEGRATION LAYER
 * Handles all voice-related functionality
 */

class VoiceIntegration {
    constructor() {
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.isListening = false;
        this.voiceSupported = false;
        this.availableVoices = [];
        this.currentUtterance = null;
        
        // Callbacks
        this.onListeningStarted = null;
        this.onListeningEnded = null;
        this.onVoiceResult = null;
        this.onVoiceError = null;
        this.onNoMatch = null;
        this.onSpeechStarted = null;
        this.onSpeechEnded = null;
        this.onSpeechError = null;
        
        this.initVoice();
    }
    
    initVoice() {
        // Check for speech recognition support
        if ('webkitSpeechRecognition' in window) {
            this.recognition = new webkitSpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = 'en-US';
            this.recognition.maxAlternatives = 3;
            
            this.voiceSupported = true;
            console.log('✅ Voice recognition supported (webkit)');
        } else if ('SpeechRecognition' in window) {
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = 'en-US';
            this.recognition.maxAlternatives = 3;
            
            this.voiceSupported = true;
            console.log('✅ Voice recognition supported');
        } else {
            console.warn('❌ Voice recognition not supported in this browser');
            this.voiceSupported = false;
        }
        
        // Load available voices for synthesis
        if (this.synthesis) {
            // Voices might not be loaded immediately
            if (this.synthesis.getVoices().length) {
                this.availableVoices = this.synthesis.getVoices();
            } else {
                this.synthesis.addEventListener('voiceschanged', () => {
                    this.availableVoices = this.synthesis.getVoices();
                });
            }
        }
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        if (!this.recognition) return;
        
        this.recognition.onstart = () => {
            this.isListening = true;
            if (this.onListeningStarted) this.onListeningStarted();
        };
        
        this.recognition.onend = () => {
            this.isListening = false;
            if (this.onListeningEnded) this.onListeningEnded();
        };
        
        this.recognition.onresult = (event) => {
            const results = [];
            for (let i = 0; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                const confidence = event.results[i][0].confidence;
                results.push({ transcript, confidence });
            }
            
            // Get the best result
            const bestResult = results[0];
            if (this.onVoiceResult) this.onVoiceResult(bestResult);
        };
        
        this.recognition.onerror = (event) => {
            console.error('Voice recognition error:', event.error);
            this.isListening = false;
            if (this.onVoiceError) this.onVoiceError(event.error);
        };
        
        this.recognition.onnomatch = () => {
            if (this.onNoMatch) this.onNoMatch();
        };
    }
    
    // Start listening
    startListening() {
        if (!this.recognition) {
            if (this.onVoiceError) this.onVoiceError('not_supported');
            return;
        }
        
        try {
            this.recognition.start();
        } catch (error) {
            console.error('Failed to start recognition:', error);
            if (this.onVoiceError) this.onVoiceError('start_failed');
        }
    }
    
    // Stop listening
    stopListening() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
        }
    }
    
    // Speak text
    speak(text, options = {}) {
        if (!this.synthesis) {
            console.warn('Speech synthesis not supported');
            return;
        }
        
        // Cancel any ongoing speech
        this.stopSpeaking();
        
        const utterance = new SpeechSynthesisUtterance(text);
        
        // Configure voice
        if (options.voice) {
            const selectedVoice = this.availableVoices.find(v => v.name === options.voice);
            if (selectedVoice) utterance.voice = selectedVoice;
        } else {
            // Try to find a nice Indian English voice
            const indianVoice = this.availableVoices.find(v => 
                v.lang.includes('en-IN') || v.name.includes('Google UK')
            );
            if (indianVoice) utterance.voice = indianVoice;
        }
        
        // Set properties
        utterance.rate = options.rate || 0.9;  // Slightly slower for clarity
        utterance.pitch = options.pitch || 1.0;
        utterance.volume = options.volume || 1.0;
        utterance.lang = options.lang || 'en-US';
        
        // Event handlers
        utterance.onstart = () => {
            this.currentUtterance = utterance;
            if (this.onSpeechStarted) this.onSpeechStarted();
        };
        
        utterance.onend = () => {
            this.currentUtterance = null;
            if (this.onSpeechEnded) this.onSpeechEnded();
        };
        
        utterance.onerror = (event) => {
            console.error('Speech synthesis error:', event);
            this.currentUtterance = null;
            if (this.onSpeechError) this.onSpeechError(event);
        };
        
        // Speak
        this.synthesis.speak(utterance);
    }
    
    // Stop speaking
    stopSpeaking() {
        if (this.synthesis && this.currentUtterance) {
            this.synthesis.cancel();
            this.currentUtterance = null;
        }
    }
    
    // Pause speaking
    pauseSpeaking() {
        if (this.synthesis && this.synthesis.speaking) {
            this.synthesis.pause();
        }
    }
    
    // Resume speaking
    resumeSpeaking() {
        if (this.synthesis && this.synthesis.paused) {
            this.synthesis.resume();
        }
    }
    
    // Get available voices
    getVoices() {
        return this.availableVoices;
    }
    
    // Check if currently speaking
    isSpeaking() {
        return this.synthesis ? this.synthesis.speaking : false;
    }
    
    // Check if currently listening
    isCurrentlyListening() {
        return this.isListening;
    }
    
    // Set language
    setLanguage(lang) {
        if (this.recognition) {
            this.recognition.lang = lang;
        }
    }
    
    // Get supported languages
    getSupportedLanguages() {
        return [
            { code: 'en-US', name: 'English (US)' },
            { code: 'en-GB', name: 'English (UK)' },
            { code: 'en-IN', name: 'English (India)' },
            { code: 'hi-IN', name: 'Hindi (India)' },
            { code: 'ta-IN', name: 'Tamil (India)' },
            { code: 'te-IN', name: 'Telugu (India)' },
            { code: 'kn-IN', name: 'Kannada (India)' },
            { code: 'ml-IN', name: 'Malayalam (India)' },
            { code: 'bn-IN', name: 'Bengali (India)' },
            { code: 'mr-IN', name: 'Marathi (India)' },
            { code: 'gu-IN', name: 'Gujarati (India)' }
        ];
    }
}

// Voice Command Processor - understands voice-specific patterns
class VoiceCommandProcessor {
    constructor() {
        this.commandPatterns = {
            'search': [
                /show me (.*)/i,
                /find (.*)/i,
                /search for (.*)/i,
                /display (.*)/i,
                /get (.*)/i,
                /i want to see (.*)/i,
                /show (.*)/i,
                /look for (.*)/i
            ],
            'create_album': [
                /make an album of (.*)/i,
                /create album (.*)/i,
                /generate album (.*)/i,
                /create a (.*) album/i,
                /make a (.*) album/i,
                /album of (.*)/i
            ],
            'slideshow': [
                /play slideshow of (.*)/i,
                /show slideshow (.*)/i,
                /make a slideshow (.*)/i,
                /start slideshow (.*)/i,
                /slideshow of (.*)/i,
                /play (.*) as slideshow/i
            ],
            'identify': [
                /who is this/i,
                /identify (.*)/i,
                /who are they/i,
                /name this person/i,
                /who is in this photo/i
            ],
            'help': [
                /help/i,
                /what can you do/i,
                /how to use/i,
                /what commands/i
            ]
        };
    }
    
    processVoiceInput(transcript) {
        const result = {
            original: transcript,
            intent: 'unknown',
            query: transcript,
            confidence: 0.5
        };
        
        // Check each intent pattern
        for (const [intent, patterns] of Object.entries(this.commandPatterns)) {
            for (const pattern of patterns) {
                const match = transcript.match(pattern);
                if (match) {
                    result.intent = intent;
                    result.query = match[1] || transcript;
                    result.confidence = 0.9;
                    result.matchedPattern = pattern;
                    break;
                }
            }
            if (result.intent !== 'unknown') break;
        }
        
        return result;
    }
    
    // Generate voice-friendly response
    generateVoiceResponse(aiResponse) {
        if (!aiResponse) {
            return "I'm having trouble understanding. Please try again.";
        }
        
        if (aiResponse.needsInput) {
            return aiResponse.question || "I need more information to help you.";
        }
        
        if (aiResponse.results) {
            const count = aiResponse.results.count;
            if (count === 0) {
                return "I couldn't find any photos matching your request. Try being more specific.";
            } else if (count === 1) {
                return `I found 1 photo. ${aiResponse.results.title || ''}`;
            } else {
                return `I found ${count} photos. ${aiResponse.results.title || ''}`;
            }
        }
        
        if (aiResponse.learned) {
            return `Great! I've learned to recognize your ${aiResponse.learned.person}. Found ${aiResponse.learned.count} photos.`;
        }
        
        if (aiResponse.error) {
            return "Sorry, I encountered an error. Please try again.";
        }
        
        return "I'm processing your request. Please wait a moment.";
    }
}

// Export for use in other scripts
window.VoiceIntegration = VoiceIntegration;
window.VoiceCommandProcessor = VoiceCommandProcessor;