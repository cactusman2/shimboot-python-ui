import pathlib
import subprocess
import curses
import time
from threading import Event

#define a few useful paths
base_path = pathlib.Path(__file__).resolve().parent
mock_data_path = base_path / "mock_data"
config_path = base_path / "config"
image_path = base_path / "images"
mock_debug_file = base_path / "mock_data" / "debug.txt"

on_shim = pathlib.Path("/bin/bootstrap.sh").exists()
output_file = pathlib.Path("/tmp/bootloader_result")
stateful_mount = pathlib.Path("/mnt/state")

def horizontal_line(width):
  return "├" + "─" * (width - 2) + "┤"

def erase(window, y, x, h, w):
  for yOff in range(h-1):
    for xOff in range(w):
      window.addstr(y+yOff, x+xOff, " ")

def swap(y, x, window, h, w):
  # swaps CHGAT attributes
  for xOff in range(w):
    for yOff in range(h):
      attrs = window.inch(y+yOff, x+xOff)
      isreverse = bool(attrs & curses.A_REVERSE)
      window.chgat(y+yOff, x+xOff, curses.A_NORMAL if isreverse else curses.A_REVERSE)

def safe_write(y, x, window, text, wrap = False, width = None):
  # whenever you write outside the screen, the curses throws an error, this prevents the error from happening
  # auto wraps and truncates aswell, which is pretty handy :)
  size = window.getmaxyx()

  while (len(text) > 0):
    current_cutoff = min(width if width != None else (size[1]-x), len(text)) # how many characters were visualizing
    render = text[0:current_cutoff]
    text = text[current_cutoff:len(text)]
    solutions_available = (wrap and y+1 < size[0]) or (len(text) <= 0)

    if (not solutions_available):
        render = render[0:len(render)-3]+"..."
    window.addstr(y, x, render)
    if (solutions_available):
        y += 1
    else:
        break

def is_int(string):
  try:
    int(string)
    return True
  except ValueError:
    return False

def run_command(cmd):
  if type(cmd) is str:
    cmd = cmd.split()
  output_bytes = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
  return output_bytes.decode()

mock_debug_file.write_text("")
def doprint(msg):
  mock_debug_file.write_text(mock_debug_file.read_text()+"\n"+str(msg))
