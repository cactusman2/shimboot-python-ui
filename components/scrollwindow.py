import utils
import curses

# a component is what we'll use to render an entry
class scroll_component:
  h = 1
  scroll_owner = None
  selected = False
  layout = 0
  def __init__(self, text="", layout=""):
    self.layout = layout
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

prefs = {}

it = 0
for i in range(97, 123):
  it += 1
  prefs[chr(i)] = it

for i in range(65, 90):
  it += 1
  prefs[chr(i)] = it

for i in range(48, 57):
  it += 1
  prefs[chr(i)] = it

# x is the one in place, y is the contender
# returns whether or not they should continue
def string_sorting_comparison(x, y):
  for char_iter in range(min(len(x), len(y))):
    comp1 = x[char_iter]
    comp2 = y[char_iter]
    if comp1 != comp2:
      return prefs.get(comp2, ord(comp2)) > prefs.get(comp1, ord(comp1))
  return True

# i figured out u can't make a subpad of a subpad! ):
class scroll_window:
  selected = None # scroll component
  sorting_comparison = string_sorting_comparison
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

  def iterative_next_index(self, contender): # probably i frogor
    # returns where a value should be inserted at in order to keep the list sorted
    for i, target in enumerate(self.entries):
      if not self.sorting_comparison(target, contender):
        return i-1
    return len(self.entries)-1

  def sorting_comparison(self, x, y):
    return string_sorting_comparison(x.layout, y.layout)

  def full_sort(self):
    for cutoff in range(len(self.entries)-1):
      smallest_val = None
      for i in range(cutoff, len(self.entries)):
        v = self.entries[i]
        if smallest_val != v and smallest_val == None or not self.sorting_comparison(smallest_val, v):
          smallest_val = v
          # we then need to check that all values are corresponding to the smallest val by looping again
          hit = False            
          for i in range(cutoff, len(self.entries)):
            c = self.entries[i]
            if not self.sorting_comparison(smallest_val, c):
              hit = True
              smallest_val = c
              break
          if not hit: # all are in agreeance this is the current smallest value
            break
      self.entries.remove(smallest_val)
      self.entries.insert(cutoff, smallest_val)

  def clear(self):
    self.selected = None
    self.entries.clear()

  def add(self, v, bulk=False): # auto_sort will put the element in place automatically
    if bulk:
      # keep the entry for later sorting
      # if u dont sort after using bulk the sort will be messed up ):
      # this is only beneficial if your adding new_len^2(ish?) items otherwise an iteration for every item added might aswell be justified in terms of micro optimization
      self.entries.append(v)
    else:
      # all adds are assumed to be iterative, please use bulk for optimization (like 1/100000th lol)
      # this only works if the list is already sorted.
      ind = self.iterative_next_index(v)
      self.entries.insert(ind, v)
    v.scroll_owner = self
    if self.selected == None:
      self.selected = v

  def next(self):
    try:
      ind = self.entries.index(self.selected)
    except:
      ind = 0
    if ind+1 < len(self.entries):
      self.select(self.entries[ind+1])

  def back(self):
    try:
      ind = self.entries.index(self.selected)
    except:
      ind = 0
    if ind-1 >= 0:
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
