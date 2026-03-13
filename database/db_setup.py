# database/db_setup.py
"""
Database setup and utility functions - NO HARDCODED NAMES
Everything starts empty and learns from user
"""

import sqlite3
import os
import json
from datetime import datetime

def init_database(db_path='database.db'):
    """Initialize database with all tables - NO SAMPLE DATA"""
    
    # Remove existing database if you want fresh start
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"🗑️ Removed existing database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # People table - starts EMPTY
    c.execute('''
        CREATE TABLE people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            relation TEXT,
            name TEXT,
            first_seen TEXT,
            last_seen TEXT,
            photo_count INTEGER DEFAULT 0,
            face_encoding TEXT,
            metadata TEXT
        )
    ''')
    
    # Events table - starts EMPTY
    c.execute('''
        CREATE TABLE events (
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
    
    # Images table - will be filled as user uploads
    c.execute('''
        CREATE TABLE images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            path TEXT,
            tags TEXT,
            date TEXT,
            location TEXT,
            faces TEXT,
            objects TEXT,
            scene TEXT,
            quality REAL,
            embedding BLOB,
            analyzed INTEGER DEFAULT 0
        )
    ''')
    
    # Photo-People relationship
    c.execute('''
        CREATE TABLE photo_people (
            photo_id INTEGER,
            person_id INTEGER,
            face_id TEXT,
            confidence REAL,
            FOREIGN KEY(photo_id) REFERENCES images(id),
            FOREIGN KEY(person_id) REFERENCES people(id)
        )
    ''')
    
    # Photo-Events relationship
    c.execute('''
        CREATE TABLE photo_events (
            photo_id INTEGER,
            event_id INTEGER,
            confidence REAL,
            FOREIGN KEY(photo_id) REFERENCES images(id),
            FOREIGN KEY(event_id) REFERENCES events(id)
        )
    ''')
    
    # User preferences
    c.execute('''
        CREATE TABLE user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            value TEXT,
            updated_at TEXT
        )
    ''')
    
    # Conversation memory
    c.execute('''
        CREATE TABLE conversation_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            response TEXT,
            context TEXT,
            timestamp TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"✅ Empty database created at {db_path}")
    print("   No hardcoded data - system will learn from user interactions")
    return db_path

def add_sample_photos_only(db_path='database.db'):
    """
    Add ONLY sample photos (no person data)
    Person data will be learned when user identifies them
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Sample images - with face DETECTIONS but no person IDs
    # Faces are detected but NOT identified - they will be learned
    images = [
        # beach1.jpg - no faces detected
        ('beach1.jpg', '/static/samples/beach1.jpg', 
         'beach, ocean, sunset, vacation', 
         '2024-01-15', 'Goa',
         '[]',  # No faces
         '[{"label": "sky/water"}, {"label": "sand"}]', 
         'beach', 0.85, None, 1),
        
        # beach2.jpg - 2 faces detected (unknown persons)
        ('beach2.jpg', '/static/samples/beach2.jpg', 
         'beach, friends, party, sunset, group_photo', 
         '2024-01-16', 'Goa',
         '[{"face_id": "beach2_face1", "bbox": [100,50,80,80], "confidence": 0.9, "person_id": null, "relation": null}, {"face_id": "beach2_face2", "bbox": [200,60,75,75], "confidence": 0.85, "person_id": null, "relation": null}]',
         '[{"label": "sky/water"}, {"label": "people"}]', 
         'beach', 0.78, None, 1),
        
        # wedding1.jpg - 2 faces detected (unknown persons)
        ('wedding1.jpg', '/static/samples/wedding1.jpg', 
         'wedding, ceremony, family, group_photo, happy', 
         '2024-02-10', 'Mumbai',
         '[{"face_id": "wedding1_face1", "bbox": [150,40,100,100], "confidence": 0.95, "person_id": null, "relation": null}, {"face_id": "wedding1_face2", "bbox": [300,50,90,90], "confidence": 0.92, "person_id": null, "relation": null}]',
         '[{"label": "people"}, {"label": "flowers"}]', 
         'indoor', 0.88, None, 1),
        
        # wedding2.jpg - 1 face detected (unknown person)
        ('wedding2.jpg', '/static/samples/wedding2.jpg', 
         'wedding, bride, cake, celebration', 
         '2024-02-10', 'Mumbai',
         '[{"face_id": "wedding2_face1", "bbox": [200,30,120,120], "confidence": 0.9, "person_id": null, "relation": null}]',
         '[{"label": "cake"}, {"label": "people"}]', 
         'indoor', 0.82, None, 1),
        
        # birthday1.jpg - 2 faces detected (unknown persons)
        ('birthday1.jpg', '/static/samples/birthday1.jpg', 
         'birthday, cake, party, celebration', 
         '2024-03-05', 'Delhi',
         '[{"face_id": "birthday1_face1", "bbox": [180,60,85,85], "confidence": 0.88, "person_id": null, "relation": null}, {"face_id": "birthday1_face2", "bbox": [280,70,80,80], "confidence": 0.86, "person_id": null, "relation": null}]',
         '[{"label": "cake"}, {"label": "people"}]', 
         'indoor', 0.75, None, 1),
        
        # birthday2.jpg - 1 face detected (unknown person)
        ('birthday2.jpg', '/static/samples/birthday2.jpg', 
         'birthday, family, cake, happy', 
         '2024-03-05', 'Delhi',
         '[{"face_id": "birthday2_face1", "bbox": [120,50,95,95], "confidence": 0.9, "person_id": null, "relation": null}]',
         '[{"label": "cake"}, {"label": "balloons"}]', 
         'indoor', 0.8, None, 1),
    ]
    
    for img in images:
        try:
            c.execute('''
                INSERT INTO images 
                (filename, path, tags, date, location, faces, objects, scene, quality, embedding, analyzed)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ''', img)
        except Exception as e:
            print(f"⚠️ Error inserting image {img[0]}: {e}")
    
    # IMPORTANT: NO photo_people entries - they will be added when user identifies people
    
    conn.commit()
    conn.close()
    
    print("✅ Sample photos added with face DETECTIONS but no person IDs")
    print("   System will ask user to identify people when needed")

if __name__ == "__main__":
    db_path = init_database()
    add_sample_photos_only(db_path)
    
    # Verify the database
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM images")
    img_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM people")
    people_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM photo_people")
    links_count = c.fetchone()[0]
    conn.close()
    
    print(f"\n📊 Database Status:")
    print(f"   - Images: {img_count} (with face detections)")
    print(f"   - Known people: {people_count} (learned from user)")
    print(f"   - Person-photo links: {links_count}")
    print("\n🎉 Database ready! System will learn from user interactions.")
   