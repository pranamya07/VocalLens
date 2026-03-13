# agents/memory_agent.py
"""
Memory Agent - Remembers people, events, and learns from interactions
NO HARDCODED NAMES - Everything learned dynamically
"""

import sqlite3
import json
import numpy as np
from datetime import datetime

class MemoryAgent:
    """
    Intelligent memory system that learns and improves over time
    Starts empty - learns everything from user interactions
    """
    
    def __init__(self, db_path='database.db'):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
        
    def create_tables(self):
        """Initialize all memory tables - all empty initially"""
        c = self.conn.cursor()
        
        # People table - starts EMPTY, filled when user identifies people
        c.execute('''
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                relation TEXT,  -- 'sister', 'brother', 'mother', etc.
                name TEXT,       -- Optional: user can provide name later
                first_seen TEXT,
                last_seen TEXT,
                photo_count INTEGER DEFAULT 0,
                face_encoding TEXT,  -- Will store face features
                metadata TEXT
            )
        ''')
        
        # Events table - starts EMPTY, filled as events are detected
        c.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                date TEXT,
                location TEXT,
                description TEXT,
                photo_count INTEGER DEFAULT 0,
                first_photo_date TEXT,
                last_photo_date TEXT
            )
        ''')
        
        # Images table (enhanced)
        c.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                path TEXT,
                tags TEXT,
                date TEXT,
                location TEXT,
                faces TEXT,        -- JSON array of detected faces with face_ids
                objects TEXT,
                scene TEXT,
                quality REAL,
                embedding BLOB,
                analyzed INTEGER DEFAULT 0
            )
        ''')
        
        # Photo-People relationship - links photos to identified people
        c.execute('''
            CREATE TABLE IF NOT EXISTS photo_people (
                photo_id INTEGER,
                person_id INTEGER,
                face_id TEXT,      -- Which face in the photo (from faces array)
                confidence REAL,
                FOREIGN KEY(photo_id) REFERENCES images(id),
                FOREIGN KEY(person_id) REFERENCES people(id)
            )
        ''')
        
        # Photo-Events relationship
        c.execute('''
            CREATE TABLE IF NOT EXISTS photo_events (
                photo_id INTEGER,
                event_id INTEGER,
                confidence REAL,
                FOREIGN KEY(photo_id) REFERENCES images(id),
                FOREIGN KEY(event_id) REFERENCES events(id)
            )
        ''')
        
        # User preferences/learning
        c.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                updated_at TEXT
            )
        ''')
        
        # Conversation memory - remembers past interactions
        c.execute('''
            CREATE TABLE IF NOT EXISTS conversation_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                response TEXT,
                context TEXT,
                timestamp TEXT
            )
        ''')
        
        self.conn.commit()
        print("✅ Memory tables created (all empty, ready to learn)")
    
    def add_image(self, filename, path, analysis):
        """
        Add analyzed image to memory
        """
        c = self.conn.cursor()
        
        c.execute('''
            INSERT INTO images 
            (filename, path, tags, date, location, faces, objects, scene, quality, analyzed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            filename,
            path,
            ', '.join(analysis.get('tags', [])),
            analysis.get('timestamp', ''),
            analysis.get('location', ''),
            json.dumps(analysis.get('faces', [])),
            json.dumps(analysis.get('objects', [])),
            analysis.get('scene', {}).get('type', ''),
            analysis.get('quality', {}).get('overall', 0.5)
        ))
        
        photo_id = c.lastrowid
        self.conn.commit()
        return photo_id
    
    def identify_person_in_photo(self, photo_id, face_id, person_relation):
        """
        Mark that a specific face in a photo belongs to a person
        This is how the system LEARNS
        """
        c = self.conn.cursor()
        
        # Get or create person
        c.execute('SELECT id FROM people WHERE relation = ?', (person_relation,))
        result = c.fetchone()
        
        if result:
            person_id = result[0]
        else:
            # New person - add to memory
            c.execute('''
                INSERT INTO people (relation, first_seen, last_seen, photo_count)
                VALUES (?, datetime('now'), datetime('now'), 0)
            ''', (person_relation,))
            person_id = c.lastrowid
            print(f"✅ Learned new person: {person_relation}")
        
        # Update the faces JSON in the image
        c.execute('SELECT faces FROM images WHERE id = ?', (photo_id,))
        row = c.fetchone()
        if row and row[0]:
            faces = json.loads(row[0])
            for face in faces:
                if face.get('face_id') == face_id:
                    face['person_id'] = person_id
                    face['relation'] = person_relation
                    break
            
            c.execute('UPDATE images SET faces = ? WHERE id = ?', 
                     (json.dumps(faces), photo_id))
        
        # Link photo to person
        c.execute('''
            INSERT INTO photo_people (photo_id, person_id, face_id, confidence)
            VALUES (?, ?, ?, 1.0)
        ''', (photo_id, person_id, face_id))
        
        # Update photo count for person
        c.execute('''
            UPDATE people SET 
                photo_count = (
                    SELECT COUNT(*) FROM photo_people WHERE person_id = ?
                ),
                last_seen = datetime('now')
            WHERE id = ?
        ''', (person_id, person_id))
        
        self.conn.commit()
        return person_id
    
    def find_photos_with_person(self, person_relation):
        """
        Find all photos containing a specific person
        """
        c = self.conn.cursor()
        c.execute('''
            SELECT i.* FROM images i
            JOIN photo_people pp ON i.id = pp.photo_id
            JOIN people p ON pp.person_id = p.id
            WHERE p.relation = ?
        ''', (person_relation,))
        
        return c.fetchall()
    
    def get_all_known_people(self):
        """
        Get list of all people the system knows (from user teaching)
        """
        c = self.conn.cursor()
        c.execute('SELECT relation, photo_count, first_seen FROM people ORDER BY photo_count DESC')
        return [{'relation': row[0], 'photo_count': row[1], 'first_seen': row[2]} 
                for row in c.fetchall()]
    
    def get_unidentified_faces(self, limit=20):
        """
        Get photos with faces that haven't been identified yet
        Used when we need to ask user to identify someone
        """
        c = self.conn.cursor()
        c.execute('''
            SELECT id, filename, faces FROM images 
            WHERE faces != '[]' 
            AND faces IS NOT NULL
            AND id NOT IN (
                SELECT DISTINCT photo_id FROM photo_people
            )
            LIMIT ?
        ''', (limit,))
        
        return c.fetchall()
    
    def learn_from_interaction(self, query, response, context):
        """
        Store conversation memory for future reference
        """
        c = self.conn.cursor()
        c.execute('''
            INSERT INTO conversation_memory (query, response, context, timestamp)
            VALUES (?, ?, ?, datetime('now'))
        ''', (query, json.dumps(response), json.dumps(context)))
        self.conn.commit()
    
    def get_relevant_context(self, current_query):
        """
        Retrieve relevant past interactions
        """
        c = self.conn.cursor()
        c.execute('''
            SELECT query, response FROM conversation_memory
            WHERE query LIKE ? OR query LIKE ?
            ORDER BY timestamp DESC
            LIMIT 5
        ''', (f'%{current_query}%', f'%{current_query.split()[0] if current_query.split() else ""}%'))
        
        return c.fetchall()
    
    def get_statistics(self):
        """
        Get memory statistics - all should be 0 initially
        """
        c = self.conn.cursor()
        
        stats = {}
        
        c.execute('SELECT COUNT(*) FROM images')
        stats['total_photos'] = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM people')
        stats['known_people'] = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM photo_people')
        stats['identified_faces'] = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM conversation_memory')
        stats['conversations'] = c.fetchone()[0]
        
        # Get list of known people
        stats['people_list'] = self.get_all_known_people()
        
        return stats