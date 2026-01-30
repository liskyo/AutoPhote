import threading
import time
import queue
from concurrent.futures import ThreadPoolExecutor
from config import CAMERA_COUNT, LOCAL_TEMP_BUFFER, USE_REAL_CAMERA, CAMERA_IPS
from hardware.mock_camera import MockCamera
from hardware.hik_camera import HikCamera
from services.file_service import FileService
from utils.logger import setup_logger
from utils.image_utils import overlay_timestamp

logger = setup_logger("CaptureService")

class CaptureManager:
    def __init__(self, upload_queue, update_cam_status_callback=None, update_cam_image_callback=None):
        self.cameras = []
        self.upload_queue = upload_queue
        self.executor = ThreadPoolExecutor(max_workers=CAMERA_COUNT)
        self.update_cam_status_callback = update_cam_status_callback 
        self.update_cam_image_callback = update_cam_image_callback # callback(cam_idx, pil_image)
        self.pending_captures = {} # {index: pil_image}
        # Status codes: 0=Disconnected, 1=Connected, 2=Capturing, 3=Done/Success, 4=Error, 5=Reviewing

    def initialize_cameras(self):
        logger.info(f"Initializing {CAMERA_COUNT} cameras... (Real Hardware: {USE_REAL_CAMERA})")
        for i in range(CAMERA_COUNT):
            if USE_REAL_CAMERA:
                ip = CAMERA_IPS.get(i+1, "0.0.0.0")
                cam = HikCamera(camera_id=i+1, ip_address=ip)
            else:
                cam = MockCamera(camera_id=i+1)
            
            if cam.connect():
                self.cameras.append(cam)
                if self.update_cam_status_callback:
                    self.update_cam_status_callback(i, 1) # Connected
            else:
                logger.error(f"Failed to connect to Camera {i+1}")
                if self.update_cam_status_callback:
                    self.update_cam_status_callback(i, 0) # Error
        logger.info("All cameras initialized.")

    def trigger_batch_capture(self, save_now=True):
        """
        Trigger all cameras.
        If save_now is False, images are stored in pending_captures for review.
        """
        logger.info(f"Trigger received! Batch capture (Save={save_now}).")
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        self.pending_captures.clear()
        
        futures = []
        for i, cam in enumerate(self.cameras):
            if self.update_cam_status_callback:
                self.update_cam_status_callback(i, 2) # Capturing
            futures.append(self.executor.submit(self._capture_task, cam, i, timestamp_str, save_now))

    def _capture_task(self, camera, index, batch_id, save_now):
        try:
            img = camera.grab_image()
            logger.debug(f"Cam {index+1} Grab success. Type: {type(img)}")
            
            # --- OVERLAY TIMESTAMP ---
            try:
                img = overlay_timestamp(img, camera_id=index+1)
                logger.debug(f"Cam {index+1} Overlay success.")
            except Exception as e_overlay:
                logger.error(f"Cam {index+1} Overlay failed: {e_overlay}")
                # Continue without overlay if it fails
                pass

            # Update UI immediately for preview
            if self.update_cam_image_callback:
                self.update_cam_image_callback(index, img)

            if not save_now:
                # Store for review
                self.pending_captures[index] = img
                if self.update_cam_status_callback:
                    self.update_cam_status_callback(index, 5) # Reviewing
                return

            # Save immediately
            self._save_and_queue(index, img, batch_id)
                    
        except Exception as e:
            logger.error(f"Error capturing from Cam {index+1}: {e}")
            if self.update_cam_status_callback:
                self.update_cam_status_callback(index, 4) # Exception

    def confirm_save(self):
        """
        Save all pending captures to disk and queue for upload.
        """
        logger.info("Confirming save for pending captures...")
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        
        # We can run this in parallel too, but simple loop is fine for saving
        for index, img in self.pending_captures.items():
            try:
                self._save_and_queue(index, img, timestamp_str)
            except Exception as e:
                logger.error(f"Error saving pending Cam {index+1}: {e}")
                self.update_cam_status_callback(index, 4)

        self.pending_captures.clear()

    def discard_capture(self):
        """
        Discard pending captures and reset status to Ready.
        """
        logger.info("Discarding pending captures.")
        self.pending_captures.clear()
        for i in range(len(self.cameras)):
             if self.update_cam_status_callback:
                self.update_cam_status_callback(i, 1) # Reset to Ready

    def _save_and_queue(self, index, img, batch_id):
        from config import JPEG_QUALITY
        filename = f"CAM{index+1}_{batch_id}.jpg"
        saved_path = FileService.save_image(img, LOCAL_TEMP_BUFFER, filename, quality=JPEG_QUALITY)
        
        if saved_path:
            self.upload_queue.put(saved_path)
            logger.debug(f"Cam {index+1} captured & queued.")
            if self.update_cam_status_callback:
                self.update_cam_status_callback(index, 3) # Success
        else:
            if self.update_cam_status_callback:
                self.update_cam_status_callback(index, 4) # Save Error

    def shutdown(self):
        for cam in self.cameras:
            cam.disconnect()
        self.executor.shutdown(wait=True)
