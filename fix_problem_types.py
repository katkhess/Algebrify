import sqlite3

db_path = r"c:/Users/hess2/Code/Final project/algebrify/data/algebrify.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS problem_types")
cur.execute("""
CREATE TABLE IF NOT EXISTS problem_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT
)
""")

problem_types = [
    ('factoring', 'factoring', 'Factor polynomials and solve equations by factoring'),
    ('quadratics', 'quadratic_equations', 'Solve and analyze quadratic equations'),
    ('statistics', 'descriptive_statistics', 'Summarize and interpret data sets'),
    ('statistics', 'inferential_statistics', 'Make predictions and inferences from data'),
    ('radicals', 'radical_functions', 'Simplify, graph, and solve radical expressions'),
    ('exponentials', 'exponential_logarithmic', 'Explore and solve exponential and logarithmic functions'),
    ('polynomials', 'modeling_polynomials', 'Model real-world problems using polynomial functions'),
    ('matrices', 'linear_algebra', 'Perform operations and solve problems using matrices'),
    ('rationals', 'rational_functions', 'Simplify and analyze rational expressions and equations'),
    ('trigonometry', 'unit_circles', 'Understand trigonometric ratios and the unit circle')
]

cur.executemany(
    "INSERT OR IGNORE INTO problem_types (unit, type, description) VALUES (?, ?, ?)",
    problem_types
)

conn.commit()

# Print current contents
print("\nCurrent contents of problem_types table:")
cur.execute("SELECT * FROM problem_types")
for row in cur.fetchall():
    print(row)

conn.close()
print("\nproblem_types table created and seeded.")
