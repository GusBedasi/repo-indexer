import os
#import json
import sqlite3
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, Tk

IGNORE_DIRS = {".git", "node_modules", "__pycache__", "dist", "build", "webpack", "chunks"}
NON_CODE_EXTENSIONS = {"md", "txt", "json", "yml", "yaml", "xml", "csv", "log"}

def extract_extension(filename):
    extension = os.path.splitext(filename)[1][1:].lower() 
    if extension == "":
        return "unknown"
    return extension

def extract_language(extension):
    if extension in NON_CODE_EXTENSIONS:
        return "text"
    return extension

def extract_last_modified(entry_stats):
    return datetime.strftime(datetime.fromtimestamp(entry_stats.st_mtime), "%Y-%m-%d %H:%M:%S")

def line_counter(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception as e:
        print(f"Error counting lines in {file_path}: {e}")
        return 0

def extract(entry):
    entry_stats = entry.stat()
    last_modified = extract_last_modified(entry_stats)
    extension = extract_extension(entry.name)
    line_count = line_counter(entry.path)

    return{
        "path": Path(entry.path).as_posix(),
        "filename": entry.name,
        "language": extract_language(extension),
        "size": entry_stats.st_size,
        "last_modified": last_modified,
        "line_count": line_count,
        "depth": len(Path(entry.path).parts),
        "extension": extension
    }

def extract_tokenized_path(path, root):
    return Path(path).relative_to(root).as_posix().replace("/", " ").replace(".", " ").replace("_", " ").replace("-", " ")

def walk(root):
    with os.scandir(root) as it:
        for entry in it:
            if entry.is_dir(follow_symlinks=False):
                if entry.name in IGNORE_DIRS:
                    continue
                yield from walk(entry.path)
            elif entry.is_file(follow_symlinks=False):
                yield entry

def init_db(repository_name="repository_data.db"):
    conn = sqlite3.connect(repository_name)

    ## Drop existing tables if they exist to start fresh
    conn.execute("DROP TABLE IF EXISTS file_fts")
    conn.execute("DROP TABLE IF EXISTS files")

    ## Create main table for file metadata
    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT,
            filename TEXT,
            language TEXT,
            line_count INTEGER,
            extension TEXT,
            size INTEGER,
            depth INTEGER,
            modified TEXT
        )
    """)

    ## Create FTS5 virtual table for tokenized paths
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS file_fts USING fts5(
            tokenized_path
        )
    """)
    return conn

if __name__ == "__main__":
    Tk().withdraw()
    repo_path = filedialog.askdirectory(title="Select the root directory of your repository")
    conn = init_db(os.path.basename(repo_path) + "_data.db")

    if not repo_path:
        print("No directory selected.")
        exit()

    for entry in walk(repo_path):
        data = extract(entry)
        #data = json.loads(entry)
        cursor = conn.execute("""
            INSERT INTO files (path, filename, language, line_count, extension, size, depth, modified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["path"],
            data["filename"],
            data["language"],
            data["line_count"],
            data["extension"],
            data["size"],
            data["depth"],
            data["last_modified"]
        ))

        file_id = cursor.lastrowid
        tokenized_path = extract_tokenized_path(data["path"], repo_path)
                          
        conn.execute("""
            INSERT INTO file_fts (rowid, tokenized_path)
            VALUES (?, ?)
        """, (
            file_id,
            tokenized_path
        ))
    conn.commit()
    conn.close()