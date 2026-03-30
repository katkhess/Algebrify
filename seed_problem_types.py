import sqlite3

db_path = "c:/Users/hess2/Code/Final project/algebrify/data/algebrify.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

problem_types = [
    ("Algebra 2 - Factoring",),
]

cur.executemany("INSERT OR IGNORE INTO problem_types (name) VALUES (?)", problem_types)
conn.commit()
conn.close()
