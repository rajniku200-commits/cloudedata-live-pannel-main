import pathlib

BASE_DIR = pathlib.Path.cwd().resolve()


def _resolve_path(path):
    if not path:
        raise ValueError('Path is required')
    target = (BASE_DIR / path).resolve()
    if not str(target).startswith(str(BASE_DIR)):
        raise ValueError('Invalid path')
    return target


def list_files(path='.'):
    target = _resolve_path(path)
    if not target.exists() or not target.is_dir():
        raise FileNotFoundError('Directory not found')
    return [item.name for item in target.iterdir()]


def read_file(path):
    target = _resolve_path(path)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError('File not found')
    with target.open('r', encoding='utf-8') as file:
        return file.read()


def create_file(path, content=''):
    target = _resolve_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        with target.open('wb') as file:
            file.write(content)
    else:
        with target.open('w', encoding='utf-8') as file:
            file.write(content)
    return 'File created'


def updated_file(path, content=''):
    target = _resolve_path(path)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError('File not found')
    with target.open('w', encoding='utf-8') as file:
        file.write(content)
    return 'File updated'


def deleted_file(path):
    target = _resolve_path(path)
    if not target.exists():
        raise FileNotFoundError('Path not found')
    if target.is_dir():
        for item in target.iterdir():
            if item.is_dir():
                deleted_file(str(item.relative_to(BASE_DIR)))
            else:
                item.unlink()
        target.rmdir()
        return 'Directory deleted'
    target.unlink()
    return 'File deleted'
