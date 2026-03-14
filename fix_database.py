import sqlite3
import json

print("🔧 Fixing database JSON columns...")

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Check current state
c.execute("PRAGMA table_info(images)")
columns = c.fetchall()
print("\n📊 Current table structure:")
for col in columns:
    print(f"   {col[1]}: {col[2]}")

# Fix empty strings in faces column
c.execute("SELECT id, faces FROM images WHERE faces = '' OR faces IS NULL")
empty_faces = c.fetchall()
print(f"\n🔍 Found {len(empty_faces)} rows with empty/invalid faces")

for row in empty_faces:
    c.execute("UPDATE images SET faces = ? WHERE id = ?", ('[]', row[0]))

# Fix empty strings in objects column
c.execute("SELECT id, objects FROM images WHERE objects = '' OR objects IS NULL")
empty_objects = c.fetchall()
print(f"🔍 Found {len(empty_objects)} rows with empty/invalid objects")

for row in empty_objects:
    c.execute("UPDATE images SET objects = ? WHERE id = ?", ('[]', row[0]))

# Fix empty strings in scene column
c.execute("SELECT id, scene FROM images WHERE scene = '' OR scene IS NULL")
empty_scene = c.fetchall()
print(f"🔍 Found {len(empty_scene)} rows with empty/invalid scene")

for row in empty_scene:
    c.execute("UPDATE images SET scene = ? WHERE id = ?", ('unknown', row[0]))

conn.commit()

# Verify fix
c.execute("SELECT id, faces, objects, scene FROM images LIMIT 5")
print("\n✅ Fixed rows (sample):")
for row in c.fetchall():
    print(f"   ID {row[0]}: faces={row[1]}, objects={row[2]}, scene={row[3]}")

conn.close()
print("\n🎉 Database fixed! Run your app again.")