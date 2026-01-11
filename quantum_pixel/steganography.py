# cspell:ignore stegano, computer-lizing
"""
Do what is needed to be done.
"""

from io import BytesIO
from base64 import b85encode, b85decode

from PIL import Image
import stegano

class Steganography:
    """Encode and decode. [This will be upgraded to prevent computer-lizing]"""
    @classmethod
    def encode(cls, preview: Image.Image, data: Image.Image, path: str) -> bool:
        """
        Encoder.

        Args:
            preview (Image.Image): Preview image.
            data (Image.Image): The real image that got hidden.
            path (str): The path the encoded image is saved into.

        Returns:
            bool: operate successfully.
        """
        try:
            buffered = BytesIO()
            data.save(buffered, format="webp")
            encoded_data = b85encode(buffered.getvalue()).decode()
            stegano.lsb.hide(preview, encoded_data).save(path)
            return True
        except (ValueError, TypeError):
            return False

    @classmethod
    def decode(cls, decoded_image: Image.Image, path: str) -> bool:
        """
        Decoder.

        Args:
            decoded_image (Image.Image): Decoded image.
            path (str): The path then hidden image is saved into.
        
        Returns:
            bool: operate successfully.
        """
        try:
            Image.open(BytesIO(b85decode(stegano.lsb.reveal(decoded_image)))).save(path)
            return True
        except (ValueError, TypeError):
            return False

if __name__ == "__main__":
    Steganography.encode(Image.open("preview.png"), Image.open("material.png"), "steganography.png")
