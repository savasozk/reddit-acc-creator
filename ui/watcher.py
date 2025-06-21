import time
import threading
import streamlit as st
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, file_path, callback):
        self.file_path = file_path
        self.callback = callback

    def on_modified(self, event):
        if event.src_path == self.file_path:
            self.callback()

def start_watching(file_path: str, callback):
    """Starts watching a file for changes in a background thread."""
    event_handler = FileChangeHandler(file_path, callback)
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()
    return observer 