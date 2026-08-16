import subprocess
import zipfile
from pathlib import Path

import py7zr
import rarfile
from ftfy import fix_text


def fix_filename(path: Path) -> Path:
    fixed_name = fix_text(path.name)

    if fixed_name != path.name:
        new_path = path.with_name(fixed_name)
        path.rename(new_path)
        return new_path

    return path


def extract_archive(archive_path: Path, extension: str, extract_dir: Path) -> list[Path]:
    if extension.lower() == "zip":

        print(f"[extract] extracting ZIP: {archive_path} -> {extract_dir}")

        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(archive_path, "r") as archive:
            print(f"[extract] ZIP contains {len(archive.namelist())} files")
            archive.extractall(extract_dir)

        files = [
            p for p in extract_dir.rglob("*")
            if p.is_file()
        ]

        print(f"[extract] extracted {len(files)} files")

    elif extension == "rar":
        with rarfile.RarFile(archive_path) as archive:
            try:
                archive.extractall(extract_dir)
            except rarfile.RarCannotExec:
                subprocess.run(
                        ["unar", "-output-directory", str(extract_dir), str(archive_path)],
                        check=True,
                        capture_output=True,
                        text=True,
                    )

    elif extension == "7z":
        try:
            with py7zr.SevenZipFile(archive_path, mode="r") as archive:
                archive.extractall(path=extract_dir)
        except py7zr.exceptions.Bad7zFile:
            subprocess.run(
                ["7z", "x", str(archive_path), f"-o{extract_dir}"],
                check=True,
                capture_output=True,
                text=True,
            )

    extracted_files = sorted(path for path in extract_dir.rglob("*") if path.is_file())

    return [fix_filename(path) for path in extracted_files if path.is_file()]
