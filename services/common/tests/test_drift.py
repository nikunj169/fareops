import numpy as np

from fareops_common.drift import build_profile, psi


def test_psi_low_for_same_distribution():
    rng = np.random.default_rng(0)
    reference = rng.normal(5, 1, 5000)
    profile = build_profile(reference.reshape(-1, 1), ["trip_distance"], ["trip_distance"])
    prof = profile["trip_distance"]
    same = rng.normal(5, 1, 5000)
    assert psi(prof["expected"], same, prof["edges"]) < 0.05


def test_psi_high_for_shifted_distribution():
    rng = np.random.default_rng(0)
    reference = rng.normal(5, 1, 5000)
    profile = build_profile(reference.reshape(-1, 1), ["trip_distance"], ["trip_distance"])
    prof = profile["trip_distance"]
    shifted = rng.normal(15, 1, 5000)
    assert psi(prof["expected"], shifted, prof["edges"]) > 0.2


def test_psi_binary_feature_all_ones_vs_all_zeros_profile():
    zeros = np.zeros(5000)
    profile = build_profile(zeros.reshape(-1, 1), ["is_airport_pickup"], ["is_airport_pickup"])
    prof = profile["is_airport_pickup"]
    ones = np.ones(5000)
    assert psi(prof["expected"], ones, prof["edges"]) > 1.0
