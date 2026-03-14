import sqlite3
c = sqlite3.connect('database.db').cursor()
c.execute('SELECT path FROM images LIMIT 5')
print(c.fetchall())