import sqlite3, json
conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()
cur.execute('SELECT id, name, fee_percentage, fee_payer FROM pos_paymentmethod')
rows = cur.fetchall()
print(json.dumps(rows, ensure_ascii=False))
conn.close()