import pytest
import numpy as np
from seminar1_adapted_code import ColorTranslator, RunLengthEncoder, JPEGFileManager

def test_rgb_to_yuv():
    translator = ColorTranslator()
    # Black
    y, u, v = translator.rgb_to_yuv(0, 0, 0)
    assert (y, u, v) == (0, 0, 0)
    
    # White (Approximate)
    y, u, v = translator.rgb_to_yuv(1, 1, 1)
    assert y == pytest.approx(1.0)
    assert u == pytest.approx(0.0, abs=1e-2)

def test_rle_encoding():
    encoder = RunLengthEncoder()
    data = [10, 10, 10, 2, 2, 5]
    expected = [(3, 10), (2, 2), (1, 5)]
    assert encoder.encode(data) == expected

def test_rle_empty():
    encoder = RunLengthEncoder()
    assert encoder.encode([]) == []

def test_serpentine_too_small(tmp_path):
    # Create a dummy file smaller than 64 bytes
    p = tmp_path / "small.bin"
    p.write_bytes(b'\x00' * 10)
    
    manager = JPEGFileManager()
    assert manager.serpentine(str(p)) is None