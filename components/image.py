import curses
import json
import pathlib
import utils

colors = {
  "w": 0, # w is allowed to blend into the background when selected, this is to maintain consistency while a bit stupid
  "r": 1,
  "b": 2,
  "g": 3,
  "y": 4,
  "c": 5,
  "m": 6,
  "d": 7, # d for DEFAULT, default flips color when white and acts as a default text character
}

white_colors = {
  "w": 8,
  "r": 9,
  "b": 10,
  "g": 11,
  "y": 12,
  "c": 13,
  "m": 14,
  "d": 15,
}

def unpack_image_raw(packedImage):
  data = [0]
  for i in range(len(packedImage)):
    string = packedImage[i]
    color_collection_mode = False
    color = "w"
    widthCount = 0
    line = []
    data.append(line)
    for l in range(len(string)):
      s = string[l]
      if color_collection_mode:
        if s == "]":
          color_collection_mode = False
        else:
          color += s
      else:
        if s == "[":
          color = ""
          color_collection_mode = True
        else:
          # add character based on color
          line.append([s, color or "w"])
          widthCount += 1
    data[0] = max(data[0], widthCount)
  return data
# ends up looking like [2, [["a", curses.RED], ["b", curses.WHITE]], ["new line lol", curses.RED]]

read_icons_json = None
unpacked_icons = {}

def get_sys_icon(operating_system, icon_name):
  global read_icons_json
  global unpacked_icons
  if read_icons_json == None:
    icons_path = utils.config_path / "icons.json"
    icons_text = (icons_path).read_text()
    read_icons_json = json.loads(icons_text)
  identifier = operating_system + "/" + icon_name
  cached_icon = unpacked_icons.get(identifier, None)
  if (cached_icon == None):
    cached_icon = unpack_image_raw(read_icons_json[operating_system][icon_name])
    unpacked_icons[identifier] = cached_icon
  return cached_icon

# from top to bottom
def draw_image(window, y, x, imageData, canRenderFunc, white_bkg=False):
  for i in range(1, len(imageData)):
    line = imageData[i]
    yCursor = y+(i-1)
    if canRenderFunc(yCursor):
      for letter in range(len(line)):
        xCursor = x+letter
        render = line[letter]
        pallete = white_colors if white_bkg else colors
        window.addstr(yCursor, xCursor, render[0], curses.color_pair(pallete.get(render[1], 0)))
