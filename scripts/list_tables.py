import sqlite3, json
conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
rows = cur.fetchall()
print(json.dumps(rows, ensure_ascii=False, indent=2))
conn.close()