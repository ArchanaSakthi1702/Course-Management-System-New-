import os

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
MEDIA_UPLOAD_DIR = os.path.join(UPLOADS_DIR, "media")
THUMBNAIL_UPLOAD_DIR = os.path.join(UPLOADS_DIR, "thumbnails")
ASSIGNMENT_SUBMISSION_DIR = os.path.join(UPLOADS_DIR, "assignment_submissions")


def get_media_fs_path(file_url: str) -> str:
    """
    Converts media file_url -> absolute filesystem path
    Example:
    /uploads/media/abc.mp4
    -> F:/course_management_system/uploads/media/abc.mp4
    """
    return os.path.join(MEDIA_UPLOAD_DIR, os.path.basename(file_url))


def get_thumbnail_fs_path(thumbnail_url: str) -> str:
    """
    Converts thumbnail URL -> absolute filesystem path
    Example:
    /uploads/thumbnails/xyz.png
    -> F:/course_management_system/uploads/thumbnails/xyz.png
    """
    return os.path.join(THUMBNAIL_UPLOAD_DIR, os.path.basename(thumbnail_url))


def delete_assignment_file_safely(file_url: str):
    if not file_url:
        return

    filename = os.path.basename(file_url)
    file_path = os.path.join(ASSIGNMENT_SUBMISSION_DIR, filename)

    if os.path.exists(file_path):
        os.remove(file_path)