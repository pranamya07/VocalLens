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
    def __init__(self):
        self.nlu = NLUAgent()
        self.vision = VisionAgent()
        self.memory = MemoryAgent()
        self.conn = sqlite3.connect('database.db', check_same_thread=False)
        self.conversation_memory = {}

    def process_query(self, query, user_context=None):
        understanding = self.nlu.process(query, user_context)
        if understanding['missing_info']:
            return self._handle_missing_info(understanding)
        if understanding['intent'] == 'create_album':
            return self._create_album(understanding)
        elif understanding['intent'] == 'slideshow':
            return self._create_slideshow(understanding)
        else:
            return self._search_photos(understanding)

    def _handle_missing_info(self, understanding):
        response = {
            'needsInput': True,
            'reasoning': understanding['reasoning'],
            'missing_info': understanding['missing_info']
        }
        person_to_identify = next(
            (info for info in understanding['missing_info']
             if info['type'] == 'identify_person'), None
        )
        if person_to_identify:
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
        c = self.conn.cursor()
        c.execute('''
            SELECT id, filename, path, faces FROM images
            WHERE faces != '[]' AND faces IS NOT NULL AND faces != ''
            LIMIT 20
        ''')
        results = c.fetchall()
        candidates = []
        for row in results:
            try:
                faces = json.loads(row[3]) if row[3] else []
            except Exception:
                faces = []
            if faces and not any(face.get('person_id') for face in faces):
                candidates.append({
                    'id': row[0],
                    'url': row[2] if row[2] else f"/static/samples/{row[1]}",
                    'preview': True
                })
        return candidates[:10]

    def _safe_json(self, val):
        if not val:
            return []
        try:
            return json.loads(val)
        except Exception:
            return []

    def _search_photos(self, understanding):
        c = self.conn.cursor()

        query = understanding.get('original_query', '').lower()
        params = []
        conditions = []

        stopwords = {'show', 'me', 'find', 'get', 'photos', 'pictures', 'images',
                     'from', 'in', 'of', 'the', 'a', 'an', 'my', 'all', 'some', 'with'}
        keywords = [w for w in query.split() if w not in stopwords and len(w) > 2]

        for keyword in keywords:
            conditions.append(
                "(tags LIKE ? OR location LIKE ? OR filename LIKE ? OR path LIKE ?)"
            )
            params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])

        for event in understanding['entities'].get('events', []):
            conditions.append("tags LIKE ?")
            params.append(f'%{event["type"]}%')

        for location in understanding['entities'].get('locations', []):
            conditions.append("(location LIKE ? OR tags LIKE ?)")
            params.extend([f'%{location["name"]}%', f'%{location["name"]}%'])

        for date in understanding['entities'].get('dates', []):
            conditions.append("(date LIKE ? OR tags LIKE ? OR path LIKE ?)")
            params.extend([f'%{date["value"]}%', f'%{date["value"]}%', f'%{date["value"]}%'])

        if conditions:
            sql = "SELECT * FROM images WHERE " + " OR ".join(conditions)
        else:
            sql = "SELECT * FROM images"

        c.execute(sql, params)
        results = c.fetchall()

        images = []
        for row in results:
            images.append({
                'id': row[0],
                'filename': row[1],
                'tags': row[3].split(', ') if row[3] else [],
                'date': row[4],
                'location': row[5],
                'faces': self._safe_json(row[6]),
                'url': '/' + row[2] if row[2] else f"/static/samples/{row[1]}"
            })

        title = ' '.join(keywords).title() if keywords else 'Photos'
        voice_response = f"Found {len(images)} photos for {title}"

        return {
            'results': {'title': title, 'count': len(images), 'images': images},
            'reasoning': understanding['reasoning'],
            'voice_response': voice_response,
            'learned': None
        }

    def _create_album(self, understanding):
        search_results = self._search_photos(understanding)
        search_results['results']['title'] = "Album: " + search_results['results']['title']
        search_results['voice_response'] = "Creating album. " + search_results['voice_response']
        return search_results

    def _create_slideshow(self, understanding):
        search_results = self._search_photos(understanding)
        search_results['results']['title'] = "Slideshow: " + search_results['results']['title']
        search_results['voice_response'] = "Creating slideshow. " + search_results['voice_response']
        return search_results

    def learn_from_identification(self, photo_ids, person_relation):
        c = self.conn.cursor()
        c.execute('''
            INSERT OR IGNORE INTO people (relation, first_seen, last_seen, photo_count)
            VALUES (?, datetime('now'), datetime('now'), 0)
        ''', (person_relation,))
        c.execute('SELECT id FROM people WHERE relation = ?', (person_relation,))
        result = c.fetchone()
        if not result:
            return {'success': False, 'error': 'Could not create person record'}
        person_id = result[0]
        for photo_id in photo_ids:
            c.execute('SELECT faces FROM images WHERE id = ?', (photo_id,))
            row = c.fetchone()
            if row and row[0]:
                faces = self._safe_json(row[0])
                if faces:
                    faces[0]['person_id'] = person_id
                    faces[0]['relation'] = person_relation
                    c.execute('UPDATE images SET faces = ? WHERE id = ?',
                              (json.dumps(faces), photo_id))
            c.execute('''
                INSERT INTO photo_people (photo_id, person_id, confidence)
                VALUES (?, ?, 1.0)
            ''', (photo_id, person_id))
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
            'createAlbum': True
        }

if __name__ == "__main__":
    orch = OrchestratorAgent()
    result = orch.process_query("show me birthday photos in Mumbai")
    print(result)