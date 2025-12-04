import dataclasses
import os
from typing import Annotated
import typer
import subprocess
import json
from pathlib import Path, PurePosixPath
import hashlib


OTA_HASHES_FILE = Path("_ota_hashes.json")


class Device:
    @classmethod
    def exec_cmd(cls, cmd: list[str]) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["mpremote"] + cmd,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result

    @classmethod
    def tree_directory(cls, device_dir: PurePosixPath):
        result = cls.exec_cmd(["tree", f"{device_dir}"])
        if result.returncode != 0:
            if "is not a directory" in result.stderr:
                return False
            else:
                typer.echo(
                    f"Failed to display directory tree for '{device_dir}' on device:\n"
                    f"{result.stderr}\n"
                    "Aborting!"
                )
                raise typer.Exit(code=1)
        return True

    @classmethod
    def create_directory(cls, device_dir: PurePosixPath):
        result = cls.exec_cmd(["mkdir", f"{device_dir}"])
        if result.returncode != 0:
            if "File exists" in result.stderr:
                return False
            else:
                typer.echo(
                    f"Failed to create directory '{device_dir}' on device:\n"
                    f"{result.stderr}\n"
                    "Aborting!"
                )
                raise typer.Exit(code=1)
        return True

    @classmethod
    def push_directory(cls, local_dir: Path, device_dir: PurePosixPath):
        result = cls.exec_cmd(["cp", "-rv", f"{local_dir}/.", f":{device_dir}"])
        if result.returncode != 0:
            typer.echo(
                f"Failed to push directory '{device_dir}' to device:\n"
                f"{result.stderr}\n"
                "Aborting!"
            )
            raise typer.Exit(code=1)

    @classmethod
    def push_file(cls, local_file: Path, device_file: PurePosixPath):
        result = cls.exec_cmd(["cp", f"{local_file}", f":{device_file}"])
        if result.returncode != 0:
            typer.echo(
                f"Failed to push file '{device_file}' to device:\n"
                f"{result.stderr}\n"
                "Aborting!"
            )
            raise typer.Exit(code=1)

    @classmethod
    def pull_file(cls, device_file: PurePosixPath, local_file: Path):
        result = cls.exec_cmd(["cp", f":{device_file}", f"{local_file}"])
        if result.returncode != 0:
            if "No such file or directory" in result.stderr:
                return False
            typer.echo(
                f"Failed to pull file '{device_file}' from device:\n"
                f"{result.stderr}\n"
                "Aborting!"
            )
            raise typer.Exit(code=1)
        return True

    @classmethod
    def delete_directory(cls, device_dir: PurePosixPath):
        result = cls.exec_cmd(["rm", "-rv", f"{device_dir}"])
        if result.returncode != 0:
            if "No such file or directory" in result.stderr:
                return False
            typer.echo(
                f"Failed to delete directory '{device_dir}' on device:\n"
                f"{result.stderr}\n"
                "Aborting!"
            )
            raise typer.Exit(code=1)
        return True

    @classmethod
    def delete_file(cls, device_file: PurePosixPath):
        result = cls.exec_cmd(["rm", f"{device_file}"])
        if result.returncode != 0:
            if "No such file or directory" in result.stderr:
                return False
            typer.echo(
                f"Failed to delete file '{device_file}' from device:\n"
                f"{result.stderr}\n"
                "Aborting!"
            )
            raise typer.Exit(code=1)
        return True

    @classmethod
    def hard_reset(cls):
        result = cls.exec_cmd(["reset"])
        if result.returncode != 0:
            typer.echo(f"Failed to hard reset the device:\n{result.stderr}\nAborting!")
            raise typer.Exit(code=1)
        typer.echo("Sent hard reset command to the device")

    @classmethod
    def repl(cls, reset: bool = False):
        if reset:
            cls.hard_reset()
        cls.exec_cmd(["repl"])


app = typer.Typer(no_args_is_help=True)


@app.command()
def tree(remote_dir: str):
    """Displays OTA code directory tree on the device."""
    device_dir = PurePosixPath(remote_dir)
    if not Device.tree_directory(device_dir):
        typer.echo(f"Directory '{device_dir}' not found on device.")


@app.command()
def delete(remote_dir: str):
    """Deletes OTA code directory on the device."""
    device_dir = PurePosixPath(remote_dir)
    typer.confirm(
        f"Are you sure you want to delete '{device_dir}' directory on the device?",
        abort=True,
    )
    delete_cache(remote_dir)
    if Device.delete_directory(device_dir):
        typer.echo()
        typer.echo(f"Directory '{device_dir}' deleted from device!")
    else:
        typer.echo(f"Directory '{device_dir}' not found on device.")


@app.command()
def upload(
    local_dir: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=False,
            dir_okay=True,
        ),
    ],
    remote_dir: Annotated[str | None, typer.Argument()] = None,
):
    """Copies local OTA code directory to the device."""
    remote_dir = remote_dir or local_dir.as_posix()
    device_dir = PurePosixPath(remote_dir)
    typer.confirm(
        f"Do you really want to copy local directory '{local_dir}' "
        f"to '{device_dir}' on device?\n"
        f"This may overwrite existing files on the device.",
        abort=True,
    )
    delete_cache(remote_dir)
    Device.create_directory(device_dir)
    Device.push_directory(local_dir, device_dir)
    typer.echo()
    typer.echo(f"Local directory '{local_dir}' copied to '{device_dir}' on device!")


@dataclasses.dataclass
class FilesMeta:
    files: dict[str, str]
    dirs: list[str]


def delete_local_cache(local_dir: Path):
    try:
        os.remove(local_dir / OTA_HASHES_FILE)
    except FileNotFoundError:
        pass


@app.command()
def sync(
    local_dir: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=False,
            dir_okay=True,
        ),
    ],
    remote_dir: Annotated[str | None, typer.Argument()] = None,
):
    """Syncs OTA code directory on the device with local code directory."""
    remote_dir = remote_dir or local_dir.as_posix()
    device_dir = PurePosixPath(remote_dir)

    device_meta = FilesMeta(files={}, dirs=[])

    if Device.pull_file(device_dir / OTA_HASHES_FILE, local_dir / OTA_HASHES_FILE):
        with open(local_dir / OTA_HASHES_FILE, "r") as f:
            device_meta_json = json.load(f)
            device_meta = FilesMeta(**device_meta_json)
        typer.echo("File hashes pulled from device.")
        delete_local_cache(local_dir)
    else:
        typer.confirm(
            f"Failed to pull file hashes from device.\n"
            f"Assuming that the '{device_dir}' directory on the device is empty.\n"
            f"Do you want to continue?",
            abort=True,
        )

    local_meta = FilesMeta(files={}, dirs=[])

    for root, dirs, files in Path.walk(local_dir):
        relative_root = Path(root).relative_to(local_dir)

        for d in dirs:
            posix_path = PurePosixPath((relative_root / d).as_posix())

            local_meta.dirs.append(f"{posix_path}")

        for f in files:
            posix_path = PurePosixPath((relative_root / f).as_posix())

            with open(root / f, "rb") as f:
                digest = hashlib.file_digest(f, "sha256")
            hash_str = digest.hexdigest()

            local_meta.files[f"{posix_path}"] = hash_str

    typer.echo("Computed hashes for local files.")
    typer.echo()

    if device_meta.dirs == local_meta.dirs and device_meta.files == local_meta.files:
        typer.echo("No changes detected. Device directory up to date!")
        delete_local_cache(local_dir)
        return

    created_dirs = [p for p in local_meta.dirs if p not in device_meta.dirs]
    deleted_dirs = [p for p in device_meta.dirs if p not in local_meta.dirs]

    updated_files = [
        p
        for p in local_meta.files
        if p in device_meta.files and local_meta.files[p] != device_meta.files[p]
    ]
    created_files = [p for p in local_meta.files if p not in device_meta.files]
    deleted_files = [p for p in device_meta.files if p not in local_meta.files]

    typer.echo("Diff: ")
    if created_dirs:
        typer.echo(f"  created {len(created_dirs)} directories")
    if deleted_dirs:
        typer.echo(f"  deleted {len(deleted_dirs)} directories")
    if created_files:
        typer.echo(f"  created {len(created_files)} files")
    if updated_files:
        typer.echo(f"  updated {len(updated_files)} files")
    if deleted_files:
        typer.echo(f"  deleted {len(deleted_files)} files")

    typer.echo()
    Device.create_directory(device_dir)

    warnings = False

    for f in deleted_files:
        if not Device.delete_file(device_dir / f):
            typer.echo(f"Warning: file '{device_dir / f}' not found on device.")
            warnings = True

    for d in deleted_dirs[::-1]:
        if not Device.delete_directory(device_dir / d):
            typer.echo(f"Warning: directory '{device_dir / d}' not found on device.")
            warnings = True

    for d in created_dirs:
        if not Device.create_directory(device_dir / d):
            typer.echo(
                f"Warning: directory '{device_dir / d}' already exists on device."
            )
            warnings = True

    for f in created_files:
        Device.push_file(local_dir / f, device_dir / f)

    for f in updated_files:
        Device.push_file(local_dir / f, device_dir / f)

    with open(local_dir / OTA_HASHES_FILE, "w") as f:
        device_meta_json = dataclasses.asdict(local_meta)
        json.dump(device_meta_json, f, indent=4)
    Device.push_file(local_dir / OTA_HASHES_FILE, device_dir / OTA_HASHES_FILE)

    delete_local_cache(local_dir)

    typer.echo()
    if warnings:
        typer.echo("Sync completed with warnings! You might want to clean and re-sync.")
    else:
        typer.echo("Sync completed!")


@app.command()
def delete_cache(remote_dir: str):
    """Deletes OTA cache on the device."""
    device_dir = PurePosixPath(remote_dir)
    if Device.delete_file(device_dir / OTA_HASHES_FILE):
        typer.echo(f"OTA cache deleted from folder '{device_dir}' on device.")
    else:
        typer.echo(f"No OTA cache found in folder '{device_dir}' on device.")


@app.command()
def reset():
    """Hard-resets the machine."""
    Device.hard_reset()


@app.command()
def repl(reset: Annotated[bool, typer.Option("--reset")] = False):
    """Opens REPL on the device. Optionally, hard-resets the machine first."""
    Device.repl(reset=reset)


if __name__ == "__main__":
    app()
