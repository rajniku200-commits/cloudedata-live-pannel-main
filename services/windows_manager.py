import os
import string
import shutil

def get_drives():
    drives = []
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            drives.append(drive)
    return drives

def browse_path(path):
    items = []
    for item in os.listdir(path):
        full_path = os.path.join(path, item)
        items.append({"name": item, "is_folder": os.path.isdir(full_path)})
    return items

def create_folder(path):
    os.makedirs(path, exist_ok=True)
    return {"message": "Folder created successfully"}

def delete_path(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)
    return {"message": "Item deleted successfully"}

def rename_file(old_path, new_path):
    os.rename(old_path, new_path)
    return {"message": "Item renamed successfully"}

def move_file(source, destination):
    shutil.move(source, destination)
    return {"message": "Item moved successfully"}

def copy_file(source, destination):
    if os.path.isdir(source):
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)
    return {"message": "Item copied successfully"}

