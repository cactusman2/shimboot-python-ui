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

# these are shared among all components, are able to have seperate render functions
class expanded_option():
  icon = ("unknown", "unknown")
  option_name = "unknown"
  quick_key = 0

  def get_w(self, selected):
    if selected:
      return 11+len(self.option_name)+1
    else:
      return 11
  
  def render(self, y, x, h, w, selected, partition_component=None):
    icon_info = components.image.get_sys_icon(*self.icon)
    if selected:
      partition_component.plot(utils.safe_write, y+2, x+1, partition_component.scroll_owner.draw_target, self.option_name)
    for i in range(h):
      partition_component.plot(partition_component.scroll_owner.draw_target.chgat, y+i, x, w, curses.A_REVERSE if selected else curses.A_NORMAL)
    components.image.draw_image(partition_component.scroll_owner.draw_target, y, x+w-1-icon_info[0], icon_info, partition_component.can_plot_y, selected)

  def run(self, partition_component):
    # this runs the component
    pass

class edit_option(expanded_option):
  icon = ("settings", "min")
  option_name = "config"
  quick_key = 101
  def run(self, partition_component):
    pass

class rescue_option(expanded_option):
  option_name = "rescue"
  icon = ("rescue", "min")
  quick_key = 114
  def run(self, partition_component):
    pass

options = [edit_option, rescue_option]

class partition_component(scroll_component):
  h=5
  expandable = True
  def __init__(self, partName="", partType=""):
    super().__init__()
    self.partType = partType
    self.partName = partName
    self.expanded = False
    self.cursor_position = 0

  def unselect(self):
    self.expanded = False

  def select(self):
    self.cursor_position = 0
    self.expanded = False  

  def recieve_key(self, key):
    if self.expandable:
      if key == curses.KEY_RIGHT:
        if self.expanded:
          if self.cursor_position-1 >= 0:
            self.cursor_position -= 1
            self.refresh()
        else:
          self.cursor_position = 0
          self.expanded = True
          self.refresh()
      elif key == curses.KEY_LEFT:
        if self.expanded:
          if self.cursor_position+1 < len(options):
            self.cursor_position += 1
            self.refresh()
          else:
            self.expanded = False
            self.refresh()

  def get_text(self):
    return self.partName

  def get_icon_info(self):
    return components.image.get_sys_icon(self.partType, "min")

  def render(self, y, x, h, w, selected):
    self.plot(utils.safe_write, y+2, x, self.scroll_owner.draw_target, self.get_text())
    if self.expandable and not self.expanded:   
      for i in range(int((self.h/2)+1)):
        self.plot(utils.safe_write, y+int(self.h/4)+i, x+w-1, self.scroll_owner.draw_target, ">")
    for i in range(self.h):
      self.plot(self.scroll_owner.draw_target.chgat, y+i, x, w, curses.A_REVERSE if not self.expanded and selected else curses.A_NORMAL)
    if not self.expanded: # i hate this
      icon_info = self.get_icon_info()
      components.image.draw_image(self.scroll_owner.draw_target, y, w-icon_info[0]-1, icon_info, self.can_plot_y, selected)
    # draw the expanded options on top
    if self.expanded:
      x_cursor = w
      for i, option in enumerate(options):
        is_selected = i == self.cursor_position
        width = option.get_w(option, selected=is_selected)
        x_cursor -= width
        # Extend to show the option text
        option.render(option, y, x_cursor, 5, width, is_selected, partition_component=self)
      for i in range(int((self.h/2)+1)):
        self.plot(utils.safe_write, y+int(self.h/4)+i, x_cursor-1, self.scroll_owner.draw_target, "<")

class shell_option(partition_component):
  expandable = False
  def __init__(self):
    super().__init__()

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
      utils.doprint(str(entry))
      new_component = partition_component(entry["device"]+" on "+entry["name"], entry["distro"])
      self.entries_scroller.add(new_component)
    self.entries_scroller.add(shell_option())
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
    #if curses.can_change_color(): # use pure white if we can, for some reason curses color white is grey (this only applies to certain terminals, enable this for perfect mock support)
    #  curses.init_color(curses.COLOR_WHITE, 1000, 1000, 1000)
    
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
  
  # each entry is 5 pixels big (so we can center the text! and the icon)
  def show_disks(self, selected_item):
    pass
    #entrySize = 5
    #width = self.entries_window.getmaxyx()[1]
    #for i, partition in enumerate(self.all_partitions):
    #  positionY = i*entrySize
    #  partition_text = f"{partition['name']} on {partition['device']}"
    #  utils.safe_write(self.entries_window, positionY+int(entrySize/2), 2, partition_text, False, int((width-2)/2))
    #  utils.chgat_multiline(self.entries_window, positionY+1, 1, width-2, entrySize, curses.A_REVERSE if i == selected_item else curses.A_NORMAL)
    #  i += 1
    #self.entries_window.refresh()
