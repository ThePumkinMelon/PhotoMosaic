# a simple program to photo mosaic images
# made in: 2020

from PIL import Image
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import os
import sys
import time

USAGE = f'USAGE: {sys.argv[0]} [TargetImage] [TilesFolder] [TileSize]'

# splits an image in to sectors
class TiledImage:
    def __init__(self, orignal_img, tile_px_size):
        self.sectors = self.split(orignal_img, tile_px_size)

    def split(self, image, tile_px_size):
        sectors = []

        width, height = image.size[0], image.size[1]
        x, y = width / tile_px_size, height / tile_px_size
        w, h = int(width/x), int(height/y)

        for i in range(int(x)):
            for j in range(int(y)):
                sectors.append(image.crop((i*w, j*h, (i+1)*w, (j+1)*h)))
        return sectors


class TileProcessor:
    def __init__(self, tiles_path, tile_px_size):
        self.tiles_path = tiles_path
        self.tile_px_size = tile_px_size

    # opens and resizes image for tile
    def processTile(self, img_path, tile_px_size):
        try:
            img = Image.open(img_path)
            w, h = img.size[0], img.size[1]
            min_dim = min(w, h)
            w_crop, h_crop = (w - min_dim) / 2, (h - min_dim) / 2

            img = img.crop((w_crop, h_crop, w - w_crop, h - h_crop))

            img = img.resize((tile_px_size, tile_px_size))

            return(img.convert('RGB'))
        except:
            return(None)

    # opens, resizes and returns images for tiles
    def getTileImages(self):
        tiles_path = self.tiles_path

        imgs = []

        for root, _, files in os.walk(tiles_path):
            for file in files:
                file_path = os.path.join(root, file)
                img = self.processTile(file_path, self.tile_px_size)
                imgs.append(img)
        return imgs

# for finding a tile for a image sector
class TileFitter:
    def __init__(self, tiles_data):
        self.tiles_data = tiles_data

    def get_diff(self, img_data, tile_data, pixle_index):
        return ((img_data[pixle_index][0] - tile_data[pixle_index][0])**2 + (img_data[pixle_index][1] - tile_data[pixle_index][1])**2 + (img_data[pixle_index][2] - tile_data[pixle_index][2])**2)

    def get_tile_diff(self, img_data, tile_data, bail_value):
        diff = 0

        for i in range(len(img_data)):
            #diff += (abs(img_data[i][0] - tile_data[i][0]) + abs(img_data[i][1] - tile_data[i][1]) + abs(img_data[i][2] - tile_data[i][2]))
            #diff += ((img_data[i][0] - tile_data[i][0])**2 + (img_data[i][1] - tile_data[i][1])**2 + (img_data[i][2] - tile_data[i][2])**2)
            diff += self.get_diff(img_data, tile_data, i)

            if diff > bail_value:
                return diff

        return diff

    def find_best_matching_tile(self, img):
        best_tile_index = 0
        min_diff = sys.maxsize
        tile_index = 0
        img_data = img.getdata()

        for tile_data in self.tiles_data:
            diff = self.get_tile_diff(img_data, tile_data, min_diff)

            if diff < min_diff:
                best_tile_index = tile_index
                min_diff = diff
            tile_index += 1

        return best_tile_index


def build_mosaic(target_img_path, tiles_path, tile_px_size):
    start_time = time.perf_counter()

    base_img = Image.open(target_img_path)
    target_img = TiledImage(base_img, tile_px_size)
    tile_imgs = TileProcessor(tiles_path, tile_px_size).getTileImages()

    tiles_data = []
    for img in tile_imgs:
        tiles_data.append(list(img.getdata()))

    tilefitter = TileFitter(tiles_data)

    mosaic_tiles_indexs = []
    with ProcessPoolExecutor() as executor:
        mosaic_tiles_indexs = executor.map(
            tilefitter.find_best_matching_tile, target_img.sectors)

    mosaic_tiles_data = []
    for index in mosaic_tiles_indexs:
        mosaic_tiles_data.append(tiles_data[index])

    mosaic = Image.new('RGB', base_img.size)

    index = 0
    for x in range(int(base_img.size[0] / tile_px_size)):
        for y in range(int(base_img.size[1] / tile_px_size)):
            tile = Image.new('RGB', (tile_px_size, tile_px_size))
            tile.putdata(mosaic_tiles_data[index])
            mosaic.paste(tile, (x * tile_px_size, y * tile_px_size,
                                (x + 1) * tile_px_size, (y + 1) * tile_px_size))
            index += 1

    mosaic.save('mosaic.png')

    end_time = time.perf_counter()
    print(f'Done! It took {end_time - start_time} seconds')

if __name__ == "__main__":
    args = sys.argv[1:]

    if len(args) != 3:
        raise SystemExit(USAGE)
    
    build_mosaic(str(args[0]), str(args[1]), int(args[2]))

    