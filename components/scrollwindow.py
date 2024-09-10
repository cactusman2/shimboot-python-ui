import utils
import curses

# a component is what we'll use to render an entry
class scroll_component:
  h = 1
  scroll_owner = None
  selected = False
  def __init__(self, text=""):
    self.text = text

  def can_plot_y(self, y):
    return self.scroll_owner.in_view_y(y)

  def plot(self, f, y, *args):
    if self.can_plot_y(y):
      f(y, *args)
  
  def refresh(self): # dunno if u care about performance, but i was thinking of caching the values since last render, and then whenever the component wants to individually rerender it uses those values. HOWEVER its just simpler this way and much more convienent
    self.scroll_owner.refresh()

  def unselect(self):
    pass

  def select(self):
    pass

  def recieve_key(self, key):
    pass
  
  def render(self, y, x, h, w, selected):
    self.plot(utils.safe_write, y, x, self.scroll_owner.draw_target, self.text, False, int(w/2))
    self.plot(self.scroll_owner.draw_target.chgat, y, x, w, curses.A_REVERSE if selected else curses.A_NORMAL)

# i figured out u can't make a subpad of a subpad! ):
class scroll_window:
  selected = None # scroll component
  def __init__(self, curse_window):
    self.entries = []
    self.draw_target = curse_window
    size = curse_window.getmaxyx()
    self.scroll_y = 0

  def get_height():
    h = 0    
    for i in self.entries:
      h += i.h
    return h

  # x is the one in place, y is the contender
  # returns whether or not they should continue
  def sorting_comparison(x, y):
    return y.layout > x.layout

  def iterative_next_index(contender): # probably i frogor
    # returns where a value should be inserted at in order to keep the list sorted
    for i, target in enumerate(self.entries):
      if not self.sorting_comparison(target, contender):
        return i-1
    return len(entries)-1

  def full_sort():
    # repeat this the length of what we have to sort -1 len every time
    for cutoff in range(len(self.entries)):
      for i in range(cutoff, len(self.entries)):
        next_index = self.iterative_next_index(i)
        self.entries.remove(i)
        self.entries.insert(i, next_index)

  def clear(self):
    self.selected = None
    self.entries.clear()

  def add(self, v):
    self.entries.append(v)
    v.scroll_owner = self
    if self.selected == None:
      self.selected = v

  def next(self):
    ind = self.entries.index(self.selected)
    if ind != -1 and ind+1 < len(self.entries):
      self.select(self.entries[ind+1])

  def back(self):
    ind = self.entries.index(self.selected)
    if ind != -1 and ind-1 >= 0:
      self.select(self.entries[ind-1])

  def get_entry_y(self, find_entry):
    y = 0
    for i, entry in enumerate(self.entries):
      if entry == find_entry:
        return y, i
      else:
        y += entry.h 
    return -1, -1

  def in_view_x(self, x):
    tl = self.draw_target.getbegyx()
    size = self.draw_target.getmaxyx()
    return x > tl[1] and x < tl[1]+size[1]

  def in_view_y(self, y):
    tl = self.draw_target.getbegyx()
    size = self.draw_target.getmaxyx()
    return y >= 0 and y < size[0]
  
  def refresh(self):
    cursor = 0
    tl = self.draw_target.getbegyx()
    size = self.draw_target.getmaxyx()
    utils.erase(self.draw_target, 0, 0, size[0], size[1])
    for i,entry in enumerate(self.entries):
      entry.render((cursor-self.scroll_y), 0, size[0], size[1], self.selected == entry)
      cursor += entry.h
    self.draw_target.refresh()
  
  def select(self, entry):
    if self.selected == entry:
      pass
    
    if self.selected:
      self.selected.selected = False
      self.selected.unselect()
    y, index = self.get_entry_y(entry)
    self.selected = entry
    entry.selected = True
    entry.select()
    screenPos = y-self.scroll_y
    size = self.draw_target.getmaxyx()
    if screenPos <= 0 or screenPos >= size[0] or screenPos+entry.h <= 0 or screenPos+entry.h >= size[0]:
        if y > self.scroll_y:
            self.scroll_y = y-size[0]+entry.h
        else:
            self.scroll_y = y
    self.refresh()
