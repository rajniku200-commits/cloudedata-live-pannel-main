import time
import threading

try:
    import cv2
    import mss
    import numpy as np
except ImportError as error:
    cv2 = None
    mss = None
    np = None
    IMPORT_ERROR = error
else:
    IMPORT_ERROR = None


class ScreenAgent:

    def __init__(self, socket_client, agent_id):
        self.socket = socket_client
        self.agent_id = agent_id
        self.streaming = False
        self.fps = 15
        self.quality = 60
        self.width = 1280
        self.height = 720


    def start(self, settings=None):
      
        if self.streaming:
            return
        settings = settings or {}
        self.fps = max(1, min(30, int(settings.get('fps', self.fps))))
        self.quality = max(25, min(90, int(settings.get('quality', self.quality))))
        self.width = max(320, min(1920, int(settings.get('width', self.width))))
        self.height = max(240, min(1080, int(settings.get('height', self.height))))

        self.streaming = True

        thread = threading.Thread(
            target=self.capture_loop,
            daemon=True
        )

        thread.start()

        print("[SCREEN] Streaming started")


    def stop(self):
        
        self.streaming = False
        print("[SCREEN] Streaming stopped")


    def capture_loop(self):
        if IMPORT_ERROR:
            self.socket.emit(
                'screen_error',
                {'agent_id': self.agent_id, 'error': str(IMPORT_ERROR)},
                namespace='/agent',
            )
            self.streaming = False
            return

        with mss.mss() as sct:

            monitor = sct.monitors[1]

            while self.streaming:

                start_time = time.time()


                # Screen Capture
                image = sct.grab(monitor)

                frame = np.array(image)

                frame = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGRA2BGR
                )


                # Resize for performance
                frame = cv2.resize(
                    frame,
                    (
                        self.width,
                        self.height
                    )
                )


               
                success, buffer = cv2.imencode(
                    ".jpg",
                    frame,
                    [
                        cv2.IMWRITE_JPEG_QUALITY,
                        self.quality
                    ]
                )


                if success:

                    self.socket.emit(
                        "screen_frame",
                        {
                            "agent_id": self.agent_id,
                            "frame": buffer.tobytes()
                        },
                        namespace='/agent',
                    )


               
                elapsed = time.time() - start_time

                delay = max(
                    0,
                    (1 / self.fps) - elapsed
                )

                time.sleep(delay)
