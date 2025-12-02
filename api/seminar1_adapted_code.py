import numpy as np
from scipy.fftpack import dct, idct
import pywt


class ColorTranslator:
    def __init__(self):
        self.rgb_to_yuv_matrix = np.array([
                [ 0.299,  0.587,  0.114],
                [-0.147, -0.289,  0.436],
                [ 0.615, -0.515, -0.100]
            ])
        self.yuv_to_rgb_matrix = np.linalg.inv(self.rgb_to_yuv_matrix)

    def rgb_to_yuv(self, r, g, b):
        rgb_vector = np.array([r, g, b])
        yuv_vector = np.dot(self.rgb_to_yuv_matrix, rgb_vector)
        y, u, v = yuv_vector
        return (y, u, v)
   
    def yuv_to_rgb(self, y, u, v):
        yuv_vector = np.array([y, u, v])
        rgb_vector = np.dot(self.yuv_to_rgb_matrix, yuv_vector)
        r, g, b = np.clip(rgb_vector, 0.0, 1.0)
        return (r, g, b)

class JPEGFileManager:
    def serpentine(self, file_path):
        print(f"Reading file: {file_path}")
        try:
            with open(file_path, 'rb') as f:
                bytes_data = f.read(64)
        except FileNotFoundError:
            return None
           
        if len(bytes_data) < 64:
            return None

        block = np.frombuffer(bytes_data, dtype=np.uint8).reshape(8, 8)
        
        serpentine_output = []
        rows, cols = 8, 8
       
        for i in range(rows + cols - 1):
            if i % 2 == 1:
                x = 0 if i < cols else i - cols + 1
                y = i if i < cols else cols - 1
                while x < rows and y >= 0:
                    serpentine_output.append(int(block[x][y]))
                    x += 1
                    y -= 1
            else:
                x = i if i < rows else rows - 1
                y = 0 if i < rows else i - rows + 1
                while x >= 0 and y < cols:
                    serpentine_output.append(int(block[x][y]))
                    x -= 1
                    y += 1
        return serpentine_output

class RunLengthEncoder:
    def encode(self, data):
        if not data or len(data) == 0:
            return []
        
        encoded_data = []
        current_value = data[0]
        count = 1
       
        for i in range(1, len(data)):
            if data[i] == current_value:
                count += 1
            else:
                encoded_data.append((count, current_value))
                current_value = data[i]
                count = 1
        encoded_data.append((count, current_value))
        return encoded_data

class DCTConverter:
    def convert(self, block):
        return dct(dct(block.T, norm='ortho').T, norm='ortho')

    def decode(self, dct_block):
        return idct(idct(dct_block.T, norm='ortho').T, norm='ortho')