import numpy as np
from scipy.ndimage import convolve
from PIL import Image
import io

# Konvertiert RGB (von PIL) zu Graustufen (ersetzt cv2.cvtColor)
def manual_cvtColor_RGB2GRAY(image_np):
    R = image_np[:, :, 0]
    G = image_np[:, :, 1]
    B = image_np[:, :, 2]
    # Standard-Luminanz-Formel
    gray_image = 0.2989 * R + 0.5870 * G + 0.1140 * B
    return gray_image.astype(np.float32)

# Hauptfunktion zur Kantenerkennung (ersetzt die frühere Funktion)
def prewitt_edge_detection(image_bytes: bytes):
    """
    Führt Prewitt-Kantenerkennung auf den übergebenen Bild-Bytes durch.
    Gibt die Kanten als PIL Image (Graustufen) zurück.
    """
    # 1. Bild von Bytes laden
    image_rgb = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_np = np.array(image_rgb)
    
    # 2. Graustufenkonvertierung
    gray_image = manual_cvtColor_RGB2GRAY(image_np)
    
    # 3. Prewitt-Kernel
    kernel_x = np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], dtype=np.float32)
    kernel_y = np.array([[-1, -1, -1], [0, 0, 0], [1, 1, 1]], dtype=np.float32)
    
    # 4. Faltung mit SciPy
    horizontal_edges = convolve(gray_image, kernel_x)
    vertical_edges = convolve(gray_image, kernel_y)
    
    # 5. Gradientenbetrag
    gradient_magnitude = np.sqrt(horizontal_edges**2 + vertical_edges**2)
    
    # 6. Schwellwertbildung und Normalisierung
    threshold = 50
    edges_np = np.where(gradient_magnitude > threshold, 255, 0)
    
    # 7. Als PIL Image (Graustufen) zurückgeben
    edges_image = Image.fromarray(edges_np.astype(np.uint8), mode='L')
    return edges_image