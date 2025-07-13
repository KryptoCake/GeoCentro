import os
import shutil

def run_task():
    """
    This task organizes the Downloads folder by moving image files
    to the Pictures folder.
    """
    downloads_path = os.path.expanduser('~/Downloads')
    pictures_path = os.path.expanduser('~/Pictures')
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']

    print("    - Organizing Downloads folder...")

    if not os.path.exists(pictures_path):
        print(f"    - Creating Pictures directory at: {pictures_path}")
        os.makedirs(pictures_path)

    try:
        for filename in os.listdir(downloads_path):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                src_path = os.path.join(downloads_path, filename)
                dest_path = os.path.join(pictures_path, filename)
                
                # Avoid overwriting files
                if not os.path.exists(dest_path):
                    print(f"    - Moving '{filename}' to Pictures.")
                    shutil.move(src_path, dest_path)
                else:
                    print(f"    - Skipped '{filename}', it already exists in Pictures.")
        print("    - Finished organizing Downloads.")
    except Exception as e:
        print(f"    [!] Error while organizing Downloads: {e}")
