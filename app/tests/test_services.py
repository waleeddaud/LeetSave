from services.github import (
    compute_code_hash,
    difficulty_folder,
    github_token_kind,
    solution_filename,
    validate_github_token_for_repo_sync,
)


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


def test_github_token_kind():
    assert github_token_kind("ghu_abc") == "github_app_user"
    assert github_token_kind("gho_abc") == "oauth_app"
    assert github_token_kind("deadbeef") == "classic_oauth"


def test_validate_github_token_for_repo_sync():
    assert validate_github_token_for_repo_sync("ghu_x", set(), "Yq8R") is not None
    assert validate_github_token_for_repo_sync("gho_x", {"public_repo"}, "Yq8R") is None
    assert validate_github_token_for_repo_sync("gho_x", set(), "Yq8R") is not None
