# agents/orchestrator.py
"""
Orchestrator Agent - Coordinates all agents and manages the intelligent workflow
"""

import sqlite3
import json
from agents.nlu_agent import NLUAgent
from agents.vision_agent import VisionAgent
from agents.memory_agent import MemoryAgent

class OrchestratorAgent:
    """
    Main orchestrator that coordinates all agents
    Implements intelligent decision making and learning
    """
    
    def __init__(self):
        self.nlu = NLUAgent()
        self.vision = VisionAgent()
        self.memory = MemoryAgent()
        self.conn = sqlite3.connect('database.db', check_same_thread=False)
        self.conversation_memory = {}  # Remember context across queries
        
    def process_query(self, query, user_context=None):
        """
        Main entry point - process ANY query intelligently
        """
        # Step 1: Understand the query with context
        understanding = self.nlu.process(query, user_context)
        
        # Step 2: Check if we need more information
        if understanding['missing_info']:
            return self._handle_missing_info(understanding)
        
        # Step 3: Execute the plan
        if understanding['intent'] == 'create_album':
            return self._create_album(understanding)
        elif understanding['intent'] == 'slideshow':
            return self._create_slideshow(understanding)
        else:
            return self._search_photos(understanding)
    
    def _handle_missing_info(self, understanding):
        """
        Handle cases where we need more information from user
        """
        response = {
            'needsInput': True,
            'reasoning': understanding['reasoning'],
            'missing_info': understanding['missing_info']
        }
        
        # Handle person identification
        person_to_identify = next(
            (info for info in understanding['missing_info'] 
             if info['type'] == 'identify_person'), 
            None
        )
        
        if person_to_identify:
            # Find candidate photos that might contain this person
            candidates = self._find_person_candidates(person_to_identify['person'])
            
            response.update({
                'type': 'identify_person',
                'question': person_to_identify['question'],
                'candidatePhotos': candidates,
                'context': {
                    'person': person_to_identify['person'],
                    'original_query': understanding['original_query']
                }
            })
        
        return response
    
    def _find_person_candidates(self, person_relation):
        """
        Find photos that might contain the person to identify
        """
        c = self.conn.cursor()
        
        # Find photos with faces but not yet identified
        c.execute('''
            SELECT id, filename, faces FROM images 
            WHERE faces != '[]' 
            AND faces IS NOT NULL
            LIMIT 20
        ''')
        
        results = c.fetchall()
        
        candidates = []
        for row in results:
            # Check if this photo already has identified people
            faces = json.loads(row[2]) if row[2] else []
            # Only include if no person identified yet (simplified)
            if faces and not any(face.get('person_id') for face in faces):
                candidates.append({
                    'id': row[0],
                    'url': f"/static/samples/{row[1]}" if row[1] else '/static/samples/placeholder.jpg',
                    'preview': True
                })
        
        return candidates[:10]  # Limit to 10 candidates
    
    def _search_photos(self, understanding):
        """
        Search photos based on understanding
        """
        c = self.conn.cursor()
        
        # Build dynamic SQL query
        sql = "SELECT * FROM images WHERE 1=1"
        params = []
        
        # Add event filters
        for event in understanding['entities'].get('events', []):
            sql += " AND tags LIKE ?"
            params.append(f'%{event["type"]}%')
        
        # Add location filters
        for location in understanding['entities'].get('locations', []):
            sql += " AND location LIKE ?"
            params.append(f'%{location["name"]}%')
        
        # Add date filters
        for date in understanding['entities'].get('dates', []):
            sql += " AND (date LIKE ? OR tags LIKE ?)"
            params.append(f'%{date["value"]}%')
            params.append(f'%{date["value"]}%')
        
        # Execute search
        c.execute(sql, params)
        results = c.fetchall()
        
        # Format results
        images = []
        for row in results:
            images.append({
                'id': row[0],
                'filename': row[1],
                'tags': row[2].split(', ') if row[2] else [],
                'date': row[3],
                'location': row[4],
                'faces': json.loads(row[5]) if row[5] else [],
                'url': f"/static/samples/{row[1]}" if row[1] else '/static/samples/placeholder.jpg'
            })
        
        # Generate title
        title_parts = []
        if understanding['entities'].get('events'):
            title_parts.append(understanding['entities']['events'][0]['type'].capitalize())
        if understanding['entities'].get('locations'):
            title_parts.append(f"in {understanding['entities']['locations'][0]['name'].capitalize()}")
        if understanding['entities'].get('dates'):
            title_parts.append(f"({understanding['entities']['dates'][0]['value']})")
        
        title = " ".join(title_parts) if title_parts else "Photos"
        
        # Generate voice-friendly response
        voice_response = f"Found {len(images)} photos"
        if title_parts:
            voice_response += f" for {title}"
        
        return {
            'results': {
                'title': title,
                'count': len(images),
                'images': images
            },
            'reasoning': understanding['reasoning'],
            'voice_response': voice_response,
            'learned': None
        }
    
    def _create_album(self, understanding):
        """
        Create an album from search results
        """
        search_results = self._search_photos(understanding)
        
        # Add album-specific logic
        search_results['results']['title'] = "Album: " + search_results['results']['title']
        search_results['voice_response'] = "Creating album. " + search_results['voice_response']
        
        return search_results
    
    def _create_slideshow(self, understanding):
        """
        Create a slideshow
        """
        search_results = self._search_photos(understanding)
        
        # Add slideshow-specific logic
        search_results['results']['title'] = "Slideshow: " + search_results['results']['title']
        search_results['voice_response'] = "Creating slideshow. " + search_results['voice_response']
        
        return search_results
    
    def learn_from_identification(self, photo_ids, person_relation):
        """
        Learn person identity from user selections
        """
        c = self.conn.cursor()
        
        # Create or get person
        c.execute('''
            INSERT OR IGNORE INTO people (relation, first_seen, last_seen, photo_count)
            VALUES (?, datetime('now'), datetime('now'), 0)
        ''', (person_relation,))
        
        c.execute('SELECT id FROM people WHERE relation = ?', (person_relation,))
        result = c.fetchone()
        if not result:
            return {'success': False, 'error': 'Could not create person record'}
        
        person_id = result[0]
        
        # Update selected photos
        for photo_id in photo_ids:
            # Get current faces
            c.execute('SELECT faces FROM images WHERE id = ?', (photo_id,))
            row = c.fetchone()
            if row and row[0]:
                faces = json.loads(row[0])
                # Mark the first face as identified (simplified)
                if faces and len(faces) > 0:
                    faces[0]['person_id'] = person_id
                    faces[0]['relation'] = person_relation
                    
                    c.execute('UPDATE images SET faces = ? WHERE id = ?', 
                             (json.dumps(faces), photo_id))
            
            # Link photo to person
            c.execute('''
                INSERT INTO photo_people (photo_id, person_id, confidence)
                VALUES (?, ?, 1.0)
            ''', (photo_id, person_id))
        
        # Update photo count
        c.execute('''
            UPDATE people 
            SET photo_count = (
                SELECT COUNT(*) FROM photo_people WHERE person_id = ?
            ), last_seen = datetime('now')
            WHERE id = ?
        ''', (person_id, person_id))
        
        self.conn.commit()
        
        return {
            'success': True,
            'person': person_relation,
            'photoCount': len(photo_ids),
            'createAlbum': True  # Suggest creating album after identification
        }
if __name__ == "__main__":
    orch = OrchestratorAgent()
    result = orch.process_query("show me birthday photos in Mumbai")
    print(result)