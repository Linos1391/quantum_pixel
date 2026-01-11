# cSpell:ignore reconstructor, fromarray
"""
Reconstruct the alter layers.
"""

import numpy as np
from PIL import Image

class Reconstructor:
    """
    The reconstructor. (STILL IN DEVELOPMENT AND NOT YET READY FOR DEPLOYMENT.) #TODO
    """
    def __init__(self):
        self.layers: list[Image.Image] = []

    def add_layer(self, img: str | Image.Image | np.ndarray) -> None:
        """
        add layer to compile.


        Args:
            img (str | Image.Image | np.ndarray): the layer to add, can be path or pure image.
        """
        if isinstance(img, str): # is a path.
            img = Image.open(img)
        if isinstance(img, Image.Image): # is a pure image.
            img = np.array(img.convert("RGB"))

        if self.layers and img.shape != self.layers[0].shape:
            raise ValueError("all layers must have the same shape")
        self.layers.append(img)

    def reconstruct(self) -> Image.Image:
        """
        Reconstruct the layers into one image.
        ```
        reconstructor = Reconstructor()
        reconstructor.reconstruct([layer1, layer2, ...])
        ```

        Args:
            layers (list): list of layers to reconstruct.
        """

        assert self.layers, "no layers to reconstruct"

        # Ensure identical shapes
        first_shape = self.layers[0].shape
        if any(layer.shape != first_shape for layer in self.layers):
            raise ValueError("all layers must have the same shape")

        # new[0][0][0] = layer1[0][0][0] + layer2[0][0][0] + ...
        summed = np.sum(np.stack(self.layers, axis=0), axis=0)
        summed = np.clip(summed, 0, 255).astype(np.uint8)
        return Image.fromarray(summed)

if __name__ == "__main__":
    reconstructor = Reconstructor()
    reconstructor.add_layer("layer_0.png")
    reconstructor.add_layer("layer_1.png")
    reconstructor.reconstruct().show()
