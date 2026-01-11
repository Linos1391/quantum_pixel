# cspell:ignore setdiff, fromarray
"""
Generating layers from an image file.
"""

import logging
from random import shuffle, randint

import numpy as np
from PIL import Image

class Generator:
    """
    The generator.
    """
    def __init__(self, input_path: str):
        try: # convert to RGB to remove the only way AI can learn to solve.
            self.img_data = np.array(Image.open(input_path).convert("RGB"))
        except Exception as e:
            logging.error("Error opening image: %s", e)
            raise e
        self._allowance: int = -1
        self._remain_allowance: int = -1

    def receive_current_progress(self):
        """
        Receive the current progress, this print out the percentage of completion.
        """
        return int(100*(1-self._remain_allowance/self._allowance))

    def _generate(self, image_data: np.ndarray, remove_interacted_data: bool):
        assert self._allowance > 0, "Allowance not set."

        layer: np.ndarray = np.zeros_like(self.img_data)

        # [[i, j] for i in range(img_data.shape[0]) for j in range(img_data.shape[1])]
        available_location = np.stack(np.meshgrid(np.arange(self.img_data.shape[0]),
            np.arange(self.img_data.shape[1])), axis=-1).reshape(-1, 2).tolist()
        shuffle(available_location)

        # do the shit.
        self._remain_allowance = self._allowance

        while self._remain_allowance > 0:
            try:
                location = tuple(available_location.pop())
            except IndexError:
                break
            for current_value in range(3): # RGBA channels
                value = min(randint(0, image_data[location][current_value]), self._remain_allowance)
                if remove_interacted_data:
                    image_data[location][current_value] -= value
                layer[location][current_value] = value
                self._remain_allowance -= value
        return Image.fromarray(layer.astype(np.uint8), "RGB")

    def preview(self, intensity: float) -> Image.Image:
        """
        Generate the preview layer.
        ```
        generator = Generator("Path/to/image.png")
        generator.preview(0.5).show()
        ```


        Args:
            intensity (float): the amount of pixel being taken (0-1). The smaller it is, the \
                faster to process, the harder to visualize. (AI may have the stroke, and so \
                human's eyes)

            
        Returns:
            Image.Image: the preview layer.
        """
        assert 0 < intensity < 1, "Invalid intensity"

        self._allowance = int(int(np.sum(self.img_data) * intensity))
        return self._generate(self.img_data, False)

    def separate(self, number_layer: int, ignore_recommend: bool = False) -> list[Image.Image]:
        """
        Generate layers. (STILL IN DEVELOPMENT AND NOT YET READY FOR DEPLOYMENT.) #TODO
        ```
        generator = Generator("Path/to/image.png")
        for img in generator.separate(2):
            img.show()
        ```

        
        Args:
            number_layer (int): number of layers to generate. (recommend 1-100)
            ignore_recommend (bool): whether to bypass the recommendation check, meaning \
                the `number_layer` can exceed 100. (this may cause algorithm errors and \
                "un-unique" randomness)

            
        Returns:
            list[Image.Image]: List of generated layers.
        """

        assert number_layer > 1, "Should be greater than 1."
        assert number_layer < self.img_data.shape[0] * self.img_data.shape[1], f"Too many layers \
            for this image (smaller than {self.img_data.shape[0] * self.img_data.shape[1]})."
        if not ignore_recommend:
            assert number_layer < 100, "Numbers of layer are too many. Set `ignore_recommend` \
                to True to bypass this check."

        # set the allowance. (yes)
        self._allowance = int(np.sum(self.img_data) / number_layer)

        # generating layers.
        result = []
        remaining: np.ndarray = self.img_data.copy()
        for _ in range(number_layer - 1):
            result.append(self._generate(remaining, True))
        result.append(Image.fromarray(remaining.astype(np.uint8), "RGB"))
        return result

    def clone(self, number_clone: int) -> list[Image.Image]:
        """
        Used after separated. (STILL IN DEVELOPMENT AND NOT YET READY FOR DEPLOYMENT.) #TODO
        
        Generate clones from image. Since it use the same technique, it is almost impossible to \
        identify the real one with computer. The only way to get is manually by hand. (This will \
        be considered with algorithm updates in future in which I have no idea where to start lol)
        ```
        for img in generator.clone(2):
            img.show()
        ```


        Args:
            number_clone (int): number of clones to generate.


        Returns:
            list[Image.Image]: List of generated clones.
        """

        assert self._allowance != -1, "Separate layers first before clone actually."

        # generating clones.
        result = []
        for _ in range(number_clone):
            result.append(self._generate(self.img_data, False))
        return result

if __name__ == "__main__":
    generator = Generator("material.png")

    # for i, img in enumerate(generator.separate(2)):
    #     img.save(f"layer_{i}.png", optimize=True)



    # generator.preview(0.5).save("preview.png", optimize=True)
