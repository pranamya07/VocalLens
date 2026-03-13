# main.py
"""
Vocal Lens - Main Flask Application
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import sqlite3
import json
import os
from datetime import datetime
from agents.orchestrator import OrchestratorAgent
from agents.vision_agent import VisionAgent
from agents.memory_agent import MemoryAgent

app = Flask(__name__)
orchestrator = OrchestratorAgent()
vision = VisionAgent()
memory = MemoryAgent()

def init_db():
    """Initialize database with sample data if it doesn't exist"""
    if not os.path.exists('database.db'):
        from database.db_setup import init_database, add_sample_photos_only
        init_database()
        add_sample_photos_only()
    else:
        print("✅ Database already exists")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/search', methods=['POST'])
def search():
    """Main search endpoint - handles ANY query intelligently"""
    data = request.json
    query = data.get('query', '')
    context = data.get('context', [])
    
    # Process query through orchestrator
    result = orchestrator.process_query(query, {'history': context})
    
    return jsonify(result)

@app.route('/voice/process', methods=['POST'])
def process_voice():
    """Process voice input with special handling"""
    data = request.json
    transcript = data.get('transcript', '')
    confidence = data.get('confidence', 0)
    
    # Log voice interaction
    print(f"🎤 Voice input: '{transcript}' (confidence: {confidence})")
    
    # Process through orchestrator (same as text search)
    result = orchestrator.process_query(transcript, {'source': 'voice'})
    
    # Add voice-specific response if not already present
    if result.get('results') and not result.get('voice_response'):
        count = result['results']['count']
        if count == 0:
            result['voice_response'] = f"I couldn't find any photos matching '{transcript}'. Try being more specific."
        elif count == 1:
            result['voice_response'] = f"I found 1 photo. {result['results']['title']}"
        else:
            result['voice_response'] = f"I found {count} photos. {result['results']['title']}"
    
    return jsonify(result)

@app.route('/learn/identify', methods=['POST'])
def learn_identify():
    """Endpoint for learning person identities from user selection"""
    data = request.json
    photo_ids = data.get('photoIds', [])
    context = data.get('context', {})
    
    if not photo_ids or not context:
        return jsonify({'success': False, 'error': 'Missing data'})
    
    # Learn from user selection
    result = orchestrator.learn_from_identification(photo_ids, context.get('person'))
    
    return jsonify(result)

@app.route('/create-album', methods=['POST'])
def create_album():
    """Create album from context"""
    data = request.json
    
    # This would use the orchestrator to create an album
    # For now, return success
    return jsonify({
        'success': True, 
        'albumTitle': 'Your Album', 
        'photoCount': 5
    })

@app.route('/find-similar', methods=['POST'])
def find_similar():
    """Find similar photos"""
    data = request.json
    
    # This would use vision + memory to find similar photos
    # For now, return empty list
    return jsonify({'success': True, 'photos': []})

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get memory statistics"""
    stats = memory.get_statistics()
    return jsonify(stats)

if __name__ == '__main__':
    # Initialize database if it doesn't exist
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)