"""Helper functions for generating problems, checking answers, and hints.
"""

import random
import math
from typing import Tuple, Union, List


def _parse_expr_to_float(s: str) -> float:
    """Parse a simple numeric expression into a float.
    Supports integers, decimals, simple fractions (a/b), sqrt(·) forms.
    """
    if s is None:
        raise ValueError("empty expression")
    expr = str(s).strip().lower()
    if not expr:
        raise ValueError("empty expression")
    expr = expr.replace('√', 'sqrt')
    expr = expr.replace(' ', '')

    # fraction
    if '/' in expr:
        num_str, den_str = expr.split('/', 1)
        num = _parse_expr_to_float(num_str)
        den = _parse_expr_to_float(den_str)
        if den == 0:
            raise ValueError("division by zero")
        return num / den

    # sqrt
    if expr.startswith('sqrt'):
        inside = expr[4:]
        if inside.startswith('(') and inside.endswith(')'):
            inside = inside[1:-1]
        if not inside:
            raise ValueError("invalid sqrt form")
        return math.sqrt(float(inside))

    return float(expr)


def check_answer(user_answer: str, correct_answer: Union[float, int, List[float], str]) -> bool:
    """Check user's answer against correct_answer. Accepts small tolerance for floats.
    correct_answer may be a list (multiple roots).
    """
    ABS_TOL = 5e-3
    REL_TOL = 1e-3
    try:
        # list/roots comparison
        if isinstance(correct_answer, (list, tuple)):
            if isinstance(user_answer, (int, float)):
                user_answer = str(user_answer)
            user_roots = [_parse_expr_to_float(x.strip()) for x in str(user_answer).split(',') if x.strip() != ""]
            correct_roots = [float(x) for x in correct_answer]
            user_roots.sort()
            correct_roots.sort()
            if len(user_roots) != len(correct_roots):
                return False
            for u, c in zip(user_roots, correct_roots):
                if not math.isclose(u, c, rel_tol=REL_TOL, abs_tol=ABS_TOL):
                    return False
            return True

        # scalar comparison
        ua = _parse_expr_to_float(str(user_answer))
        ca = _parse_expr_to_float(str(correct_answer))
        return math.isclose(ua, ca, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    except Exception:
        return False


def analyze_incorrect_answer(user_answer, correct_answer, problem_type=None, question=None) -> str:
    """Return a short, non-spoiling guidance string for incorrect answers."""
    try:
        ua = str(user_answer).strip()
        ca = correct_answer

        # Multi-root case
        if isinstance(ca, (list, tuple)):
            # count submitted roots
            user_roots = []
            try:
                user_roots = [x.strip() for x in ua.split(',') if x.strip() != ""]
            except Exception:
                if ua:
                    user_roots = [ua]
            if len(user_roots) == 0:
                return "It looks like you didn't submit any roots. Try factoring the quadratic and list each root separated by commas."
            if len(user_roots) == 1 and len(ca) > 1:
                return "You found one root. Quadratics usually have two roots — try finding a second number whose product equals the constant term."
            return "Check your factoring: look for two numbers whose product equals the constant term and whose sum equals the coefficient of x (watch signs)."

        # Scalar comparison attempts
        try:
            ua_val = _parse_expr_to_float(ua)
            ca_val = _parse_expr_to_float(str(ca))
            if math.isclose(ua_val, ca_val, rel_tol=1e-2, abs_tol=1e-2):
                return "Your answer is close numerically — check rounding/precision or whether an exact form (√ or fraction) is expected."
            if ('sqrt' in str(ca).lower() or '√' in str(ca)) and ('.' in ua or ua.replace('-', '').isdigit()):
                return "Try expressing the answer exactly (e.g., using √ or fractions) rather than a decimal, unless decimals are explicitly allowed."
        except Exception:
            pass

        # Problem-type specific nudges
        if problem_type == 'factoring':
            return "Try writing the quadratic as (x - r1)(x - r2). Find two numbers with product equal to the constant term and sum equal to the x coefficient."
        if problem_type == 'quadratic_equations':
            return "Use the quadratic formula or try factoring. Compute Δ = b² - 4ac to check the number of real roots."
        if problem_type == 'descriptive_statistics':
            return "Check your calculations: compute the mean by summing observations and dividing by n; the median is the middle value after sorting."
        if problem_type == 'inferential_statistics':
            return "Double-check whether you're asked for a sample statistic or a confidence interval; consider whether you should use z- or t-based methods."
        if problem_type == 'radical_functions':
            return "Simplify radicals by factoring perfect squares from under the root and rationalizing denominators when needed."
        if problem_type == 'exponential_logarithmic':
            return "Try rewriting expressions using laws of exponents/logarithms (e.g., log rules or convert to same base)."
        if problem_type == 'modeling_polynomials':
            return "Set up the model carefully: identify the dependent variable and plug in the given values before simplifying."
        if problem_type == 'linear_algebra':
            return "For matrix problems, check your multiplication order and use row/column operations carefully; confirm dimensions line up."
        if problem_type == 'rational_functions':
            return "Look for common factors to cancel and check domain exclusions; simplify numerator/denominator separately first."
        if problem_type == 'unit_circles':
            return "Use special-angle exact values (30°, 45°, 60°) or convert degrees to radians for calculations."

        return "Check your arithmetic and simplification steps. Break the problem into smaller steps (expand, simplify, then solve)."
    except Exception:
        return "Review your steps carefully — small arithmetic slips are common. Try simplifying step-by-step."

# url= (your repo path if you want to keep a permalink)
def personalize_review(review_text: str, user_answer, correct_answer, problem_type=None, question=None) -> str:
    """
    Personalize the provided review_text by prepending a short note
    based on analyze_incorrect_answer analysis. Keeps review helpful and non-spoiling.
    """
    try:
        note = analyze_incorrect_answer(user_answer, correct_answer, problem_type=problem_type, question=question)
        # If analyze_incorrect_answer returns a generic hint, don't repeat; only include if it's specific enough.
        generic_checks = [
            "Check your arithmetic",
            "Review your steps",
            "Check your calculations",
            "Check your factoring",
            "Use the quadratic formula"
        ]
        include_note = True
        for g in generic_checks:
            if isinstance(note, str) and g.lower() in note.lower():
                include_note = False
                break

        if include_note and note:
            personalized = f"Note about your attempt: {note}\n\n{review_text}"
        else:
            personalized = review_text
        return personalized
    except Exception:
        return review_text
    
# --- Problem generators ----------------------------------------------------- #

def generate_problem_by_type(problem_type: str) -> Tuple[str, Union[float, int, List[float]], str, str, str]:
    """Dispatch to specific generators. Returns (q, solution, hint1, hint2, hint3)."""
    if problem_type == 'factoring':
        return generate_factoring_problem()
    if problem_type == 'quadratic_equations':
        return generate_quadratic_problem()
    if problem_type == 'descriptive_statistics':
        return generate_descriptive_statistics_problem()
    if problem_type == 'inferential_statistics':
        return generate_inferential_statistics_problem()
    if problem_type == 'radical_functions':
        return generate_radical_problem()
    if problem_type == 'exponential_logarithmic':
        return generate_exponential_problem()
    if problem_type == 'modeling_polynomials':
        return generate_modeling_polynomials_problem()
    if problem_type == 'linear_algebra':
        return generate_linear_algebra_problem()
    if problem_type == 'rational_functions':
        return generate_rational_problem()
    if problem_type == 'unit_circles':
        return generate_trig_problem()

    # Fallback
    return ("No generator for this problem type yet.", None,
            "No hint available.", "", "")


# ----------------- Generators ------------------------------------------------- #

def generate_factoring_problem():
    """Return (question, [roots], hint1, hint2, hint3). Simple integer roots."""
    r1 = random.randint(-6, 6)
    r2 = random.randint(-6, 6)
    if r1 == 0 and r2 == 0:
        r2 = 1
    b = -(r1 + r2)
    c = r1 * r2
    # build polynomial string
    terms = ["x^2"]
    if b != 0:
        terms.append(f"{' - ' if b < 0 else ' + '}{abs(b)}x")
    if c != 0:
        terms.append(f"{' - ' if c < 0 else ' + '}{abs(c)}")
    question = "Factor and solve for x: " + "".join(terms) + " = 0"
    solution = sorted([r1, r2])
    hint1 = "Nudge: Try writing the quadratic as (x - r1)(x - r2)."
    hint2 = "Scaffold: Find two numbers whose product is the constant term and whose sum equals the coefficient of x."
    hint3 = f"Review: The roots are r1={r1}, r2={r2}. So (x - ({r1}))(x - ({r2})) = 0 → x = {r1} or x = {r2}."
    return question, solution, hint1, hint2, hint3


def generate_quadratic_problem():
    """Return (question, [roots], hint1, hint2, hint3). Use quadratic formula with real roots."""
    a = random.randint(1, 4)
    b = random.randint(-10, 10)
    c = random.randint(-10, 10)
    disc = b * b - 4 * a * c
    if disc < 0:
        return generate_quadratic_problem()
    r1 = (-b + math.sqrt(disc)) / (2 * a)
    r2 = (-b - math.sqrt(disc)) / (2 * a)
    question = f"Solve for x: {a}x² + ({b})x + ({c}) = 0"
    solution = sorted([round(r1, 3), round(r2, 3)])
    hint1 = "Nudge: Use the quadratic formula x = (-b ± √(b² - 4ac)) / (2a)."
    hint2 = "Scaffold: Compute the discriminant Δ = b² - 4ac first, then evaluate (-b ± √Δ)/(2a)."
    hint3 = f"Review: Δ = {disc}. Roots: x = (-{b} ± √{disc}) / {2*a} → approx {solution[0]}, {solution[1]}."
    return question, solution, hint1, hint2, hint3


def generate_descriptive_statistics_problem():
    """Create a small dataset and ask for mean or median or mode."""
    n = random.choice([5, 6, 7])
    data = [random.randint(1, 20) for _ in range(n)]
    what = random.choice(['mean', 'median', 'mode'])
    if what == 'mean':
        q = f"Compute the mean of the data set: {data}"
        solution = round(sum(data) / len(data), 2)
        hint1 = "Nudge: Add all the values and divide by how many there are."
        hint2 = f"Scaffold: Sum = {sum(data)}; divide by {len(data)}."
        hint3 = f"Review: mean = {sum(data)}/{len(data)} = {solution}."
    elif what == 'median':
        q = f"Compute the median of the data set: {data}"
        s = sorted(data)
        mid = len(s) // 2
        if len(s) % 2 == 1:
            solution = s[mid]
        else:
            solution = round((s[mid - 1] + s[mid]) / 2, 2)
        hint1 = "Nudge: Sort the list and find the middle value."
        hint2 = f"Scaffold: Sorted = {s}."
        hint3 = f"Review: median of {s} is {solution}."
    else:  # mode
        q = f"Find the mode (most frequent value) of the data set: {data}"
        freq = {}
        for x in data:
            freq[x] = freq.get(x, 0) + 1
        maxf = max(freq.values())
        modes = sorted([k for k, v in freq.items() if v == maxf])
        solution = modes if len(modes) > 1 else modes[0]
        hint1 = "Nudge: Look for the value(s) that appear most often."
        hint2 = f"Scaffold: value counts = {freq}"
        hint3 = f"Review: mode(s) = {solution}."
    return q, solution, hint1, hint2, hint3


def generate_inferential_statistics_problem():
    """Generate a simple confidence-interval or sample-mean question (basic)."""
    # small sample from known population approx
    n = random.choice([10, 12, 15])
    pop_mean = random.randint(50, 100)
    # generate a sample around the population mean
    sample = [pop_mean + random.randint(-10, 10) for _ in range(n)]
    what = random.choice(['sample_mean', '95ci_mean'])
    if what == 'sample_mean':
        q = f"A sample of {n} observations is {sample}. Compute the sample mean."
        solution = round(sum(sample) / n, 2)
        hint1 = "Nudge: Sum the sample values and divide by n."
        hint2 = f"Scaffold: Sum = {sum(sample)} divide by {n}."
        hint3 = f"Review: sample mean = {solution}."
    else:
        sample_mean = sum(sample) / n
        # use sample sd approximation
        ssd = sum((x - sample_mean) ** 2 for x in sample) / (n - 1)
        s = math.sqrt(ssd)
        se = s / math.sqrt(n)
        # 95% z-approx (teaching scope)
        margin = round(1.96 * se, 2)
        lower = round(sample_mean - margin, 2)
        upper = round(sample_mean + margin, 2)
        q = f"A sample of {n} observations is {sample}. Give an approximate 95% CI for the population mean."
        solution = (lower, upper)
        hint1 = "Nudge: Compute the sample mean and the standard error (s/√n)."
        hint2 = f"Scaffold: sample mean = {round(sample_mean,2)}, s ≈ {round(s,2)}, SE ≈ {round(se,2)}."
        hint3 = f"Review: 95% CI ≈ {round(sample_mean,2)} ± 1.96×{round(se,2)} → ({lower}, {upper})."
    return q, solution, hint1, hint2, hint3


def generate_radical_problem():
    """Simplify a radical expression, e.g., sqrt(50) or sqrt(18)/3 etc."""
    # pick a radicand with a perfect square factor
    base_factors = [2, 3, 5]
    square = random.choice([4, 9])
    outside = random.randint(1, 6)
    radicand = square * outside
    question = f"Simplify √{radicand}."
    # simplify: sqrt(square*outside) = sqrt(square)*sqrt(outside) = sqrt(square)*sqrt(outside)
    outside_coef = int(math.sqrt(square))
    if outside == 1:
        solution = f"{outside_coef}"
        hint1 = "Nudge: Look for perfect-square factors inside the radical."
        hint2 = f"Scaffold: √{radicand} = √{square}×√{outside} = {outside_coef}√{outside}."
        hint3 = f"Review: √{radicand} = {outside_coef}√{outside}."
    else:
        solution = f"{outside_coef}√{outside}"
        hint1 = "Nudge: Factor out the largest perfect square."
        hint2 = f"Scaffold: √{radicand} = √{square}·√{outside} = {outside_coef}√{outside}."
        hint3 = f"Review: √{radicand} simplifies to {solution}."
    return question, solution, hint1, hint2, hint3


def generate_exponential_problem():
    """Compute base^exponent or solve small exponential/log equation."""
    if random.random() < 0.6:
        base = random.randint(2, 6)
        exp = random.randint(1, 4)
        question = f"What is {base}^{exp}?"
        solution = base ** exp
        hint1 = "Nudge: Multiply the base by itself exponent times."
        hint2 = f"Scaffold: {base}^{exp} = " + " × ".join([str(base)] * exp) + f" = {solution}."
        hint3 = f"Review: {base}^{exp} = {solution}."
    else:
        # simple log solving: solve for x in 2^x = 8
        a = random.choice([2, 3])
        b = random.choice([2, 3])
        power = random.randint(1, 3)
        val = a ** power
        question = f"Solve for x: {a}^x = {val}"
        solution = power
        hint1 = "Nudge: Write both sides as the same base when possible."
        hint2 = f"Scaffold: {val} = {a}^{power}, so x = {power}."
        hint3 = f"Review: Express both sides with base {a}: {a}^x = {a}^{power} → x = {power}."
    return question, solution, hint1, hint2, hint3


def generate_modeling_polynomials_problem():
    """Simple modeling: evaluate polynomial at a value or find coeff from data point."""
    # either evaluate or fit a simple linear/quadratic through points
    if random.random() < 0.6:
        a = random.randint(1, 5)
        b = random.randint(-5, 5)
        c = random.randint(-5, 5)
        x = random.randint(-3, 3)
        question = f"Evaluate the polynomial f(x) = {a}x^2 + {b}x + {c} at x = {x}."
        sol = a * x * x + b * x + c
        solution = sol
        hint1 = "Nudge: Substitute x into the polynomial and compute."
        hint2 = f"Scaffold: {a}*{x}^2 + {b}*{x} + {c} = {solution}."
        hint3 = f"Review: f({x}) = {solution}."
    else:
        # find linear coefficient given point (simple)
        m = random.randint(-5, 5)
        b = random.randint(-5, 5)
        x = random.randint(0, 5)
        y = m * x + b
        question = f"A linear model is y = mx + b. If m = {m} and b = {b}, what is y when x = {x}?"
        solution = y
        hint1 = "Nudge: Multiply slope by x and add b."
        hint2 = f"Scaffold: y = {m}*{x} + {b} = {y}."
        hint3 = f"Review: y = {y}."
    return question, solution, hint1, hint2, hint3


def generate_linear_algebra_problem():
    """Very small matrix operation: multiply 2x2 by 2x1 or add matrices."""
    if random.random() < 0.6:
        # matrix-vector multiplication
        A = [[random.randint(-3, 3) for _ in range(2)] for _ in range(2)]
        v = [random.randint(-3, 3) for _ in range(2)]
        # compute product
        res0 = A[0][0] * v[0] + A[0][1] * v[1]
        res1 = A[1][0] * v[0] + A[1][1] * v[1]
        question = f"Compute the matrix-vector product: {A} × {v}."
        solution = [res0, res1]
        hint1 = "Nudge: Multiply each row of the matrix by the vector and sum the products."
        hint2 = f"Scaffold: row1: {A[0][0]}*{v[0]} + {A[0][1]}*{v[1]} = {res0}; row2: {res1}."
        hint3 = f"Review: result = {solution}."
    else:
        # simple 2x2 matrix addition
        A = [[random.randint(-3, 3) for _ in range(2)] for _ in range(2)]
        B = [[random.randint(-3, 3) for _ in range(2)] for _ in range(2)]
        S = [[A[i][j] + B[i][j] for j in range(2)] for i in range(2)]
        question = f"Compute A + B where A = {A} and B = {B}."
        solution = S
        hint1 = "Nudge: Add corresponding entries."
        hint2 = f"Scaffold: S[0,0] = {A[0][0]}+{B[0][0]} = {S[0][0]} and so on."
        hint3 = f"Review: A + B = {S}."
    return question, solution, hint1, hint2, hint3


def generate_rational_problem():
    """Simplify simple rational expression like (k*m)/m -> k or reduce fraction."""
    m = random.randint(1, 10)
    k = random.randint(1, 10)
    question = f"Simplify the rational expression: {k * m}/{m}"
    solution = k
    hint1 = "Nudge: Look for common factors in numerator and denominator."
    hint2 = f"Scaffold: ({k}*{m})/{m} = {k}*( {m}/{m} ) = {k}."
    hint3 = f"Review: the expression simplifies to {k}."
    return question, solution, hint1, hint2, hint3


def generate_trig_problem():
    """Special-angle trig evaluation (unit circle)."""
    values = {
        'sin': {0: 0.0, 30: 0.5, 45: math.sqrt(2) / 2, 60: math.sqrt(3) / 2},
        'cos': {0: 1.0, 30: math.sqrt(3) / 2, 45: math.sqrt(2) / 2, 60: 0.5},
        'tan': {0: 0.0, 30: 1 / math.sqrt(3), 45: 1.0, 60: math.sqrt(3)},
    }
    func = random.choice(list(values.keys()))
    angle = random.choice(list(values[func].keys()))
    question = f"What is {func}({angle}°)?"
    solution = round(float(values[func][angle]), 3)
    hint1 = "Nudge: Use the unit circle special-angle values."
    hint2 = "Scaffold: 30°→1/2 or √3/2, 45°→√2/2, 60°→√3/2. For tan, use sin/cos."
    hint3 = f"Review: {func}({angle}°) = {values[func][angle]} ≈ {solution}."
    return question, solution, hint1, hint2, hint3