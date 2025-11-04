import sqlite3, json
conn = sqlite3.connect('milhomem_vendas/db.sqlite3')
cur = conn.cursor()
cur.execute('SELECT id, name, fee_percentage, fee_payer FROM outflows_paymentmethod')
rows = cur.fetchall()
print(json.dumps(rows, ensure_ascii=False, indent=2))
conn.close()