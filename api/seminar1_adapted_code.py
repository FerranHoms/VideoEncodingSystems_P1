import numpy as np
from scipy.fftpack import dct, idct

class ColorTranslator:
    def __init__(self):
        # Pre-calculated matrix for speed
        self.rgb_to_yuv_matrix = np.array([
            [ 0.299,  0.587,  0.114],
            [-0.147, -0.289,  0.436],
            [ 0.615, -0.515, -0.100]
        ])

    def rgb_to_yuv(self, r, g, b):
        return tuple(np.dot(self.rgb_to_yuv_matrix, [r, g, b]))

class JPEGFileManager:
    def serpentine(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                data = f.read(64)
        except FileNotFoundError:
            return None

        if len(data) < 64:
            return None

        block = np.frombuffer(data, dtype=np.uint8).reshape(8, 8)
        
        # Optimized Pythonic Zigzag
        lines = [[] for _ in range(15)] # 8+8-1 diagonals
        for y in range(8):
            for x in range(8):
                lines[y + x].append(block[y][x])
        
        result = []
        for i, line in enumerate(lines):
            result.extend(line if i % 2 != 0 else line[::-1])
            
        return result

class RunLengthEncoder:
    def encode(self, data):
        if not data: return []
        
        # NumPy optimization for RLE (Grouping)
        arr = np.array(data)
        n = len(arr)
        if n == 0: return []
        
        y = arr[1:] != arr[:-1] # find where values change
        i = np.append(np.where(y), n - 1) # indices of changes
        z = np.diff(np.append(-1, i)) # counts
        
        # Return as list of tuples per original format
        values = arr[i]
        return list(zip(z.tolist(), values.tolist()))