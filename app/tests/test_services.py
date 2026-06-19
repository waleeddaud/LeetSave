from services.github import compute_code_hash, solution_filename, difficulty_folder


def test_compute_code_hash_stable():
    h1 = compute_code_hash("print(1)", "python", "two-sum")
    h2 = compute_code_hash("print(1)", "python", "two-sum")
    h3 = compute_code_hash("print(2)", "python", "two-sum")
    assert h1 == h2
    assert h1 != h3


def test_solution_filename_mapping():
    assert solution_filename("python3") == "solution.py"
    assert solution_filename("cpp") == "solution.cpp"
    assert solution_filename("kotlin") == "solution.txt"


def test_difficulty_folder():
    assert difficulty_folder("Easy") == "easy"
    assert difficulty_folder(None) == "unknown"
