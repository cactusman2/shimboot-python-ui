import curses
import curses.panel
import time
import traceback
import os
import sys
import components.image
from components.scrollwindow import scroll_window, scroll_component

import disks
import utils
import settings
import menu.options

options = ["edit", "rescue"]

class partition_component(scroll_component):
  h=5
  expandable = True
  def __init__(self, partName="", partType="", layout=""):
    super().__init__(None, layout)
    self.partType = partType
    self.partName = partName
    self.expanded = False
    self.cursor_position = -1

  def unselect(self):
    self.cursor_position = -1

  def select(self):
    self.cursor_position = -1

  def recieve_key(self, key):
    if self.expandable:
      if key == curses.KEY_RIGHT:
        if self.cursor_position-1 >= -1:
          self.cursor_position -= 1
          self.refresh()
      elif key == curses.KEY_LEFT:
        if self.cursor_position+1 < len(options):
          self.cursor_position += 1
          self.refresh()

  def get_text(self):
    return self.partName

  def get_icon_info(self):
    return components.image.get_sys_icon(self.partType, "min")

  def render(self, y, x, h, w, selected):
    self.plot(utils.safe_write, y+2, x, self.scroll_owner.draw_target, self.get_text())
    expanded = self.cursor_position >= 0
    if selected and not expanded and self.expandable:
      for i in range(int((self.h/2)+1)):
        self.plot(utils.safe_write, y+int(self.h/4)+i, x+w-1, self.scroll_owner.draw_target, "<")
    for i in range(self.h):
      self.plot(self.scroll_owner.draw_target.chgat, y+i, x, w, curses.A_REVERSE if selected else curses.A_NORMAL)
    if not expanded: # i hate this
      icon_info = self.get_icon_info()
      components.image.draw_image(self.scroll_owner.draw_target, y, w-icon_info[0]-1, icon_info, self.can_plot_y, selected)
    if expanded:
      utils.doprint(self.cursor_position)
      to_display = options[self.cursor_position]
      if self.cursor_position+1 < len(options):
        to_display = "< "+to_display
      if self.cursor_position-1 >= -1:
        to_display = to_display+" >"
      width = len(to_display)
      x_corner = x+int(w/2)-int(width/2)
      self.plot(utils.safe_write, y, x_corner, self.scroll_owner.draw_target, to_display)

class shell_option(partition_component):
  expandable = False
  layout = "Z"
  def __init__(self):
    super().__init__(None, None)
    self.layout = "Z"

  def get_text(self):
    return "enter shell"

  def get_icon_info(self):
    return components.image.get_sys_icon("shell", "min")

class Bootloader:
  def init(self):
    self.setup_curses()
    self.setup_windows()
    self.update_partitions()
    self.pick_os()
    self.destroy_curses()

  def update_partitions(self):
    entries_from_partitions = disks.get_all_partitions()
    self.entries_scroller.clear()    
    
    for entry in entries_from_partitions:
      layout = None
      if entry["schema_name"] == "chrome_os":
        # if were chromeos, treat similar chromeos layouts with alphabhetical ordering by the label
        layout = "1"+entry["label"]
      else:
        # this is a shimboot, instead order them by order of when they were plugged in
        layout = "2"+entry["device"]
      new_component = partition_component(entry["device"]+" on "+entry["name"], entry["distro"], layout)
      self.entries_scroller.add(new_component, bulk=True)
    self.entries_scroller.add(shell_option(), bulk=True) # shell: i here
    self.entries_scroller.full_sort()
    self.entries_scroller.refresh()

  def pick_os(self):
    selected_item = 0

    while True:
      key = self.entries_window.getch()
      
      if key == curses.KEY_DOWN: 
        self.entries_scroller.next()
      elif key == curses.KEY_UP:
        self.entries_scroller.back()
      elif key == curses.KEY_LEFT:
        if self.entries_scroller.selected:
          self.entries_scroller.selected.recieve_key(key)
      elif key == curses.KEY_RIGHT:
        if self.entries_scroller.selected:
          self.entries_scroller.selected.recieve_key(key)
      elif key == curses.KEY_ENTER or key == 10 or key == 13:
        pass
        #self.boot_entry(selected_item)
      elif key == 115: #s
        self.enter_shell()
      elif key == 101: #e
        self.edit_entry(selected_item)
  
  def edit_entry(self, selected_item):
    partition = self.all_partitions[selected_item]
    schema_name = partition["schema_name"]
    schema = settings.schemas[schema_name]

    self.options_panel.show()
    options_menu = menu.options.OptionsMenu(self.options_window, schema, {})
    new_options = options_menu.edit_options()
    self.options_panel.hide()
    curses.panel.update_panels()
    
  def enter_shell(self):
    self.destroy_curses()
    print("Entering a shell")
    utils.output_file.write_text('enable_debug_console "$TTY1"')
    os._exit(0)
  
  def boot_entry(self, selected_item):
    self.destroy_curses()
    partition = self.all_partitions[selected_item]
    
    if partition["type"] == "ChromeOS rootfs":
      self.boot_chrome_os(partition)
    else:
      self.boot_regular(partition)
    
    os._exit(0)
  
  def boot_regular(self, partition):
    print(f"Booting {partition['name']} on {partition['device']}")
    output_cmd = f"boot_target {partition['device']}"
    utils.output_file.write_text(output_cmd)
  
  def boot_chrome_os(self, partition):
    print(f"Booting Chrome OS {partition['name']} on {partition['device']}")
    output_cmd = f"boot_chromeos {partition['device']}"
    utils.output_file.write_text(output_cmd)
  
  def setup_windows(self):
    self.title_window = curses.newwin(3, self.cols, 0, 0)
    self.centered_text(self.title_window, 1, "Shimboot OS Selector")
    self.title_window.refresh()

    self.entries_window = curses.newwin(self.rows-7, self.cols-8, 3, 4)
    self.entries_window.keypad(True)
    self.entries_window.border()
    self.entries_scroll_container = self.entries_window.derwin(self.rows-9, self.cols-10, 1, 1)
    self.entries_scroller = scroll_window(self.entries_scroll_container)

    self.footer_window = curses.newwin(2, self.cols-10, self.rows - 3, 5)
    utils.safe_write(0,0, self.footer_window,"Use the arrow keys to select an entry. Press [enter] to boot the selected item. Use [e] to edit an entry, [s] to enter a shell, and [esc] to shut down the system.", True)
    self.footer_window.refresh()

    rows, cols = self.entries_window.getmaxyx()
    options_width = cols / 2
    x1 = int(cols / 2 - options_width / 2)
    x2 = int(cols / 2 + options_width / 2)
    win_cols = x2 - x1
    win_rows = int(rows / 1.5)
    self.options_window = curses.newwin(win_rows, win_cols, 7, x1)
    self.options_window.keypad(True)
    self.options_window.border()

    self.setup_panels()
  
  def setup_panels(self):
    self.title_panel = curses.panel.new_panel(self.title_window)
    self.entries_panel = curses.panel.new_panel(self.entries_window)
    self.footer_panel = curses.panel.new_panel(self.footer_window)
    self.options_panel = curses.panel.new_panel(self.options_window)
    self.options_panel.hide()
  
  def setup_curses(self):
    self.screen = curses.initscr()
    
    curses.start_color()
    curses.use_default_colors()
    # epic color pallete (copy paste spam :) )
    curses.init_pair(0, curses.COLOR_WHITE, -1)
    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.init_pair(2, curses.COLOR_BLUE, -1)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    curses.init_pair(4, curses.COLOR_YELLOW, -1)
    curses.init_pair(5, curses.COLOR_CYAN, -1)
    curses.init_pair(6, curses.COLOR_MAGENTA, -1)
    curses.init_pair(7, curses.COLOR_WHITE, -1)
    curses.init_pair(8, curses.COLOR_WHITE, curses.COLOR_WHITE)
    curses.init_pair(9, curses.COLOR_RED, curses.COLOR_WHITE)
    curses.init_pair(10, curses.COLOR_BLUE, curses.COLOR_WHITE)
    curses.init_pair(11, curses.COLOR_GREEN, curses.COLOR_WHITE)
    curses.init_pair(12, curses.COLOR_YELLOW, curses.COLOR_WHITE)
    curses.init_pair(13, curses.COLOR_CYAN, curses.COLOR_WHITE)
    curses.init_pair(14, curses.COLOR_MAGENTA, curses.COLOR_WHITE)
    curses.init_pair(15, curses.COLOR_BLACK, curses.COLOR_WHITE)
    
    self.rows, self.cols = self.screen.getmaxyx()
    self.screen.nodelay(1)
    curses.curs_set(0)
    curses.noecho()
    curses.cbreak()
  
  def destroy_curses(self):
    curses.curs_set(1)
    curses.nocbreak()
    curses.echo()
    curses.endwin()
    print("\x1b[2J\x1b[H", end="")
  
  def centered_text(self, window, y, text):
    cols = self.screen.getmaxyx()[1]
    x = int(cols/2 - len(text)/2)
    window.addstr(y, x, text)
