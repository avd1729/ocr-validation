from src.utils import get_similarity_score

def test_exact_match():
    assert get_similarity_score("hello", "hello") == 100

def test_partial_match():
    assert get_similarity_score("hello", "helo") > 80

def test_mismatch():
    assert get_similarity_score("hello", "world") < 50

def test_none_or_empty():
    assert get_similarity_score("", "hello") == 0
    assert get_similarity_score(None, "hello") == 0
