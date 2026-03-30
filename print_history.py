import sqlite3
from pprint import pprint
p = r"C:/Users/hess2/Code/Final project/algebrify/data/algebrify.db"
conn = sqlite3.connect(p)
cur = conn.cursor()
rows = list(cur.execute("SELECT id, user_id, unit, question, user_answer, correct_answer, result, timestamp FROM history ORDER BY id DESC LIMIT 10"))
print('Found', len(rows), 'rows')
for r in rows:
    pprint(r)
conn.close()
