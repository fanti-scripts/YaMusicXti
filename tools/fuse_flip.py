import os
import shutil
import sys
import time

SENTINEL = b'dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX'
FUSE_INDEX = 4  # EnableEmbeddedAsarIntegrityValidation
ENABLED = 0x31
DISABLED = 0x30


def copy_retry(src, dst, attempts=60, delay=0.25):
    last = None
    for _ in range(attempts):
        try:
            shutil.copy2(src, dst)
            return
        except PermissionError as e:
            last = e
            time.sleep(delay)
    raise last


def write_byte_retry(path, offset, value, attempts=60, delay=0.25):
    last = None
    for _ in range(attempts):
        try:
            with open(path, "r+b") as f:
                f.seek(offset)
                f.write(bytes([value]))
                f.flush()
                os.fsync(f.fileno())
            return
        except PermissionError as e:
            last = e
            time.sleep(delay)
    raise last


def fuse_offset(data):
    i = data.find(SENTINEL)
    if i < 0:
        return None
    return i + len(SENTINEL) + 2 + FUSE_INDEX


def restore_from_backup(path):
    backup = path + ".orig"
    if not os.path.exists(backup):
        return False
    try:
        copy_retry(backup, path)
    except PermissionError:
        # Файл всё ещё удерживается. Пробуем отодвинуть его и положить оригинал.
        locked = path + ".locked"
        try:
            if os.path.exists(locked):
                os.remove(locked)
            os.replace(path, locked)
            try:
                copy_retry(backup, path)
            except Exception:
                # Возвращаем всё как было, чтобы не оставить без exe.
                try:
                    os.replace(locked, path)
                except Exception:
                    pass
                raise
            try:
                os.remove(locked)
            except OSError:
                pass
        except Exception:
            raise
    print("restored exe from", backup)
    return True


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    action = sys.argv[2] if len(sys.argv) > 2 else "disable"
    if not path:
        sys.exit("usage: fuse_flip.py <exe> [disable|restore]")

    if action == "restore":
        data = None
        try:
            with open(path, "rb") as f:
                data = bytearray(f.read())
        except (OSError, IOError):
            data = None

        if data is not None:
            off = fuse_offset(data)
            if off is not None:
                if data[off] == ENABLED:
                    print("integrity fuse already enabled")
                    return
                if data[off] == DISABLED:
                    try:
                        write_byte_retry(path, off, ENABLED)
                        print("restored exe fuse byte")
                        return
                    except PermissionError:
                        pass

        if not restore_from_backup(path):
            if data is not None and fuse_offset(data) is not None and data[fuse_offset(data)] == ENABLED:
                print("integrity fuse already enabled")
                return
            sys.exit("no exe backup: " + path + ".orig")
        return

    with open(path, "rb") as f:
        data = bytearray(f.read())
    off = fuse_offset(data)
    if off is None:
        sys.exit("fuse sentinel not found")

    if data[off] == DISABLED:
        print("integrity fuse already disabled")
        return

    backup = path + ".orig"
    copy_retry(path, backup)
    print("backup:", backup)
    write_byte_retry(path, off, DISABLED)
    print("integrity fuse disabled")


if __name__ == "__main__":
    main()
