import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QRubberBand
from PyQt5.QtCore import Qt, QRect, QPoint, QSize
from PIL import ImageGrab
import pywinctl as pwc
import psutil
import keyboard
import win32gui
import win32con
import win32clipboard
import sys
from io import BytesIO

# Snipping Tool Class from the first script
class SnippingTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Snipping Tool')
        self.setWindowOpacity(0.5)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.showFullScreen()
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self)
        self.origin = QPoint()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.origin = event.pos()
            self.rubber_band.setGeometry(QRect(self.origin, QSize()))
            self.rubber_band.show()

    def mouseMoveEvent(self, event):
        if not self.origin.isNull():
            self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.capture()

    def send_to_clipboard(self, image):
        output = BytesIO()
        image.convert('RGB').save(output, 'BMP')
        data = output.getvalue()[14:]
        output.close()

        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

    def capture(self):
        rect = self.rubber_band.geometry()
        self.close()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        img = ImageGrab.grab(bbox=(x, y, x+w, y+h))
        from mss import mss
        with mss() as sct:
            sct.shot(output="monitor-1.png")
        # save to clipboard
        self.send_to_clipboard(img)

# Global dictionary to store window positions and sizes
window_positions = {}

def set_window_on_top(hwnd):
    # Check if the window is minimized
    if win32gui.IsIconic(hwnd):
        # Restore the window to normal or maximized state
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)

def set_window_not_on_top(hwnd):
    win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)

def cycle_right(event = None):
    global current_overlay_index
    current_overlay_index += 1
    cycle_windows_and_set_top()

def cycle_left(event = None):
    global current_overlay_index
    current_overlay_index -= 1
    cycle_windows_and_set_top()

def get_all_app_windows():
    windows = pwc.getAllWindows()
    windows = [window for window in windows if hasattr(window, "title")
               and window._parent == 0
               and window.title != ""
               and window.title != "Program Manager"
               and window.title != "Microsoft Text Input Application"
               and window.title != "LGControlCenterRTManager"]
    return windows

def cycle_windows_and_set_top():
    global current_overlay_index
    windows = get_all_app_windows()

    if len(windows) == 0:
        print("No valid windows found.")
        return

    windows.sort(key=lambda x: x._hWnd)
    
    next_window_index = current_overlay_index % len(windows)
    next_window = windows[next_window_index]

    try:
        next_window.activate()
    except Exception as e:
        if e.__class__.__name__ == 'PyGetWindowException':
             pass
        else:
             raise e

    hwnd = next_window._hWnd
    print("Switching to", next_window.title)
    set_window_on_top(hwnd)


def minimize_all_windows(event=None):
    global window_positions  # Access the global dictionary
    windows = get_all_app_windows()
    for window in windows:
        if "Respondus LockDown Browser" != window.title:
            hwnd = window._hWnd
            is_maximized = window.isMaximized  # Check if the window is maximized
            # Save the window's current position, size, and maximized state before minimizing
            rect = win32gui.GetWindowRect(hwnd)
            window_positions[hwnd] = (rect, is_maximized)  # Store position, size, and state
            window.minimize()
    # focus on LockDownBrowser
    for window in windows:
        if "Respondus LockDown Browser" == window.title:
            window.activate()
            hwnd = window._hWnd
            set_window_on_top(hwnd)
    print("Minimizing all windows...")


def unminimize_all_windows(event=None):
    cycle_windows_and_set_top()
    cycle_windows_and_set_top()
    
def cleanup_and_exit(event=None):
    windows = get_all_app_windows()
    hwnds = [window._hWnd for window in windows]
    for hwnd in hwnds:
            set_window_not_on_top(hwnd)
    print("Exiting...")
    sys.exit()  # Use sys.exit() to exit the program

def close_respondus(event=None):
    # Close LockDownBrowser.exe
    # while LockDownBrowser.exe is running, kill it
    while "LockDownBrowser.exe" in (proc.info['name'] for proc in psutil.process_iter(['name'])):
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == "LockDownBrowser.exe":
                proc.kill()
                print("LockDownBrowser.exe killed")
                show_taskbar()
                break

def show_taskbar(event=None):
    # Show the taskbar
    hwnd = win32gui.FindWindow("Shell_traywnd", None)
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

def hide_taskbar(event=None):
    # Hide the taskbar
    hwnd = win32gui.FindWindow("Shell_traywnd", None)
    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)

def show_snipping_tool(event=None):
    app = QApplication(sys.argv)  # Ensure this only runs once
    snipping_tool = SnippingTool()
    app.exec_()

current_overlay_index = 0 

# Modify keyboard listener setup to include Ctrl + Shift + S for the Snipping Tool
keyboard.add_hotkey("ctrl+shift+s", show_snipping_tool)
# Keyboard listener
keyboard.add_hotkey("ctrl+right", cycle_right)
keyboard.add_hotkey("ctrl+left", cycle_left)
keyboard.add_hotkey("ctrl+down", minimize_all_windows)
keyboard.add_hotkey("ctrl+up", unminimize_all_windows)
keyboard.on_press_key("esc", cleanup_and_exit)
# key del to close respondus
keyboard.on_press_key("delete", close_respondus)
keyboard.on_press_key("f8", hide_taskbar)
keyboard.on_press_key("f10", show_taskbar)

keyboard.wait()
