import os
import shutil
from utils.logger import setup_logger

logger = setup_logger("FileService")

class FileService:
    @staticmethod
    def ensure_directory(path):
        if not os.path.exists(path):
            try:
                os.makedirs(path)
                logger.info(f"Created directory: {path}")
            except OSError as e:
                logger.error(f"Failed to create directory {path}: {e}")

    @staticmethod
    def save_image(image, folder, filename, quality=95):
        """
        Save PIL Image to disk.
        Returns absolute path of the saved file or None on failure.
        """
        try:
            FileService.ensure_directory(folder)
            filepath = os.path.join(folder, filename)
            image.save(filepath, quality=quality)
            logger.debug(f"Saved image to {filepath} (Q={quality})")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save image {filename}: {e}")
            return None

    @staticmethod
    def move_file(src_path, dest_folder):
        """
        Moves file from src to dest_folder.
        """
        try:
            FileService.ensure_directory(dest_folder)
            filename = os.path.basename(src_path)
            dest_path = os.path.join(dest_folder, filename)
            shutil.move(src_path, dest_path)
            logger.info(f"Moved {src_path} -> {dest_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to move file {src_path} to {dest_folder}: {e}")
            return False

    @staticmethod
    def copy_file(src_path, dest_folder):
        """
        Copies file from src to dest_folder.
        """
        try:
            FileService.ensure_directory(dest_folder)
            filename = os.path.basename(src_path)
            dest_path = os.path.join(dest_folder, filename)
            shutil.copy(src_path, dest_path)
            logger.info(f"Copied {src_path} -> {dest_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to copy file {src_path} to {dest_folder}: {e}")
            return False

    @staticmethod
    def delete_file(path):
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.debug(f"Deleted {path}")
        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
