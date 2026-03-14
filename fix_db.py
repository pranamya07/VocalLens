import sqlite3
conn = sqlite3.connect('database.db')
c = conn.cursor()
c.execute("UPDATE images SET faces = '[]' WHERE faces IS NULL OR faces = ''")
c.execute("UPDATE images SET objects = '[]' WHERE objects IS NULL OR objects = ''")
conn.commit()
print('Fixed', conn.total_changes, 'rows')
conn.close()