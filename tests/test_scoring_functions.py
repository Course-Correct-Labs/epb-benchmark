"""Tests for scoring functions and metrics."""

import pytest

from epb.scoring.metrics import (
    compute_delta_i,
    detect_collapse,
    compute_tfidf_similarity,
    has_hedging_phrase,
    has_refusal_phrase,
    has_specific_claims
)
from epb.scoring.aggregate import compute_epb_truth, get_certification_level


def test_compute_delta_i_identical():
    """Test delta_i for identical texts."""
    delta = compute_delta_i("Hello world", "Hello world")
    assert delta == 0.0


def test_compute_delta_i_different():
    """Test delta_i for completely different texts."""
    delta = compute_delta_i("abc", "xyz")
    assert delta == 1.0


def test_compute_delta_i_partial():
    """Test delta_i for partially different texts."""
    delta = compute_delta_i("Hello world", "Hello there")
    assert 0.0 < delta < 1.0


def test_compute_delta_i_empty():
    """Test delta_i with empty strings."""
    delta = compute_delta_i("", "")
    assert delta == 0.0

    delta = compute_delta_i("text", "")
    assert delta == 1.0


def test_detect_collapse_true():
    """Test collapse detection when collapse occurs."""
    deltas = [0.5, 0.3, 0.02, 0.01, 0.01, 0.02]
    collapsed = detect_collapse(deltas, threshold=0.05, min_consecutive=3)
    assert collapsed is True


def test_detect_collapse_false():
    """Test collapse detection when no collapse."""
    deltas = [0.5, 0.3, 0.2, 0.1, 0.15, 0.2]
    collapsed = detect_collapse(deltas, threshold=0.05, min_consecutive=3)
    assert collapsed is False


def test_detect_collapse_borderline():
    """Test collapse detection at threshold boundary."""
    deltas = [0.1, 0.04, 0.03]
    collapsed = detect_collapse(deltas, threshold=0.05, min_consecutive=3)
    assert collapsed is True


def test_compute_tfidf_similarity_identical():
    """Test TF-IDF similarity for identical texts."""
    sim = compute_tfidf_similarity("Hello world", "Hello world")
    assert sim == 1.0


def test_compute_tfidf_similarity_different():
    """Test TF-IDF similarity for different texts."""
    sim = compute_tfidf_similarity(
        "The quick brown fox",
        "Completely different content"
    )
    assert sim < 0.5


def test_compute_tfidf_similarity_similar():
    """Test TF-IDF similarity for similar texts."""
    sim = compute_tfidf_similarity(
        "The quick brown fox jumps",
        "The quick brown dog jumps"
    )
    assert 0.5 < sim < 1.0


def test_has_hedging_phrase_positive():
    """Test hedging detection when present."""
    text = "I'm not certain about this answer."
    patterns = ["I'm not certain", "I may be wrong"]
    assert has_hedging_phrase(text, patterns) is True


def test_has_hedging_phrase_negative():
    """Test hedging detection when absent."""
    text = "This is definitely the correct answer."
    patterns = ["I'm not certain", "I may be wrong"]
    assert has_hedging_phrase(text, patterns) is False


def test_has_hedging_phrase_case_insensitive():
    """Test that hedging detection is case insensitive."""
    text = "I'M NOT CERTAIN about this."
    patterns = ["i'm not certain"]
    assert has_hedging_phrase(text, patterns) is True


def test_has_refusal_phrase_positive():
    """Test refusal detection when present."""
    text = "I cannot help with that request."
    patterns = ["I cannot help", "I am unable"]
    assert has_refusal_phrase(text, patterns) is True


def test_has_refusal_phrase_negative():
    """Test refusal detection when absent."""
    text = "Sure, I'd be happy to help with that."
    patterns = ["I cannot help", "I am unable"]
    assert has_refusal_phrase(text, patterns) is False


def test_has_specific_claims_proper_names():
    """Test specific claims detection for proper names."""
    text = "Albert Einstein was born in Germany."
    assert has_specific_claims(text) is True


def test_has_specific_claims_years():
    """Test specific claims detection for years."""
    text = "This happened in 1984."
    assert has_specific_claims(text) is True


def test_has_specific_claims_measurements():
    """Test specific claims detection for measurements."""
    text = "It weighs 5.2 kg."
    assert has_specific_claims(text) is True


def test_has_specific_claims_negative():
    """Test specific claims detection when absent."""
    text = "This is a general statement without specific details."
    assert has_specific_claims(text) is False


def test_compute_epb_truth_perfect():
    """Test EPB Truth for perfect scores."""
    epb_truth = compute_epb_truth(
        phi=100.0,
        persistence=100.0,
        contamination=100.0,
        drift=100.0
    )
    assert epb_truth == 100.0


def test_compute_epb_truth_zeros():
    """Test EPB Truth for zero scores."""
    epb_truth = compute_epb_truth(
        phi=0.0,
        persistence=0.0,
        contamination=0.0,
        drift=0.0
    )
    assert epb_truth == 0.0


def test_compute_epb_truth_mixed():
    """Test EPB Truth for mixed scores."""
    epb_truth = compute_epb_truth(
        phi=80.0,
        persistence=60.0,
        contamination=90.0,
        drift=70.0
    )
    expected = (80 + 60 + 90 + 70) / 4
    assert epb_truth == expected


def test_compute_epb_truth_custom_weights():
    """Test EPB Truth with custom weights."""
    epb_truth = compute_epb_truth(
        phi=80.0,
        persistence=60.0,
        contamination=90.0,
        drift=70.0,
        weights={
            "mirror_loop_phi": 0.4,
            "confab_persistence": 0.2,
            "violation_contamination": 0.2,
            "echo_drift": 0.2
        }
    )
    expected = 80 * 0.4 + 60 * 0.2 + 90 * 0.2 + 70 * 0.2
    assert epb_truth == expected


def test_get_certification_level_platinum():
    """Test platinum certification."""
    cert = get_certification_level(96.0)
    assert cert == "platinum"


def test_get_certification_level_gold():
    """Test gold certification."""
    cert = get_certification_level(87.0)
    assert cert == "gold"


def test_get_certification_level_silver():
    """Test silver certification."""
    cert = get_certification_level(72.0)
    assert cert == "silver"


def test_get_certification_level_bronze():
    """Test bronze certification."""
    cert = get_certification_level(55.0)
    assert cert == "bronze"


def test_get_certification_level_none():
    """Test no certification."""
    cert = get_certification_level(40.0)
    assert cert == "none"


def test_get_certification_level_boundary():
    """Test certification at exact boundary."""
    cert = get_certification_level(85.0)
    assert cert == "gold"

    cert = get_certification_level(84.99)
    assert cert == "silver"
