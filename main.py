import menu.bootloader
import sys
import traceback
import utils
import components.image

if __name__ == "__main__":
  try:
    main_menu = menu.bootloader.Bootloader()
    main_menu.init()
  except KeyboardInterrupt:
    main_menu.destroy_curses()
  except:
    main_menu.destroy_curses()
    traceback.print_exc(file=sys.stdout)
    sys.exit(1)
