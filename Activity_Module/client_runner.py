import sys
import time
import io
import warnings
import requests
import mss
import os
from datetime import datetime
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import pywinctl as pwc

# Suppress pywinctl warnings for unreadable titles
warnings.filterwarnings("ignore", category=UserWarning)

POLL_INTERVAL = 2.0

class ClientRunner:
    def __init__(self, endpoint_url: str):
        self.endpoint_url = endpoint_url.rstrip("/") + "/analyze/remote"
        self.sct = mss.mss()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self._is_sending = False
        print(f"🚀 NeuroLens Client Started [Poll: {POLL_INTERVAL}s]")
        print("-" * 40)
        
    def _get_active_window_title(self) -> str:
        try:
            active_win = pwc.getActiveWindow()
            return active_win.title if active_win and active_win.title else ""
        except Exception:
            return ""

    def _capture_screen(self) -> Image.Image:
        monitor = self.sct.monitors[1]
        sct_img = self.sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        return img

    def _send_payload(self, img: Image.Image, title: str):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        buf.seek(0)

        try:
            files = {"file": ("screenshot.jpg", buf, "image/jpeg")}
            data = {"window_title": title}
            resp = requests.post(self.endpoint_url, files=files, data=data, timeout=10)
            
            if resp.status_code == 200:
                res = resp.json()
                label = res.get("content", {}).get("activity", "Unknown")
                conf = res.get("content", {}).get("confidence", 0.0)
                ts = datetime.now().strftime("%H:%M:%S")
                # Exact Requested Format: [HH:MM:SS]  Category - Specific Activity
                print(f"[{ts}]  {label}")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]  SERVER ERROR ({resp.status_code})")


        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] CONNECTION LOST...")
        finally:
            self._is_sending = False

    def capture_and_send_async(self):
        if self._is_sending:
            return

        title = self._get_active_window_title()
        img = self._capture_screen()
        
        self._is_sending = True
        self.executor.submit(self._send_payload, img, title)

    def run(self):
        try:
            while True:
                start = time.time()
                self.capture_and_send_async()
                elapsed = time.time() - start
                
                sleep_time = max(0.1, POLL_INTERVAL - elapsed)
                time.sleep(sleep_time)
        except KeyboardInterrupt:
            print("\n🛑 Stopped NeuroLens Client")
            self.executor.shutdown(wait=False)
            sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client_runner.py <SERVER_URL>")
        sys.exit(1)
        
    url = sys.argv[1]
    runner = ClientRunner(url)
    runner.run()
