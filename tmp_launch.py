from jarvis.ui.app import run
import threading
import time

def main():
    run()

if __name__ == "__main__":
    t = threading.Thread(target=main, daemon=True)
    t.start()
    time.sleep(2)
    print("launched")
