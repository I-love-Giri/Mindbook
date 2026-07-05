from pathlib import Path

def save_text(filename: str , content: str):

    Path(filename).write_text(content,encoding="utf-8")


'''

pathlib is a built-in Python module for working with files and directories in an object-oriented way.

Path: Represents a file or folder path or creates a Path object that refers to the file notes.txt.

-------

write_text() is a method of the Path object.

It:

opens the file
writes the text
closes the file automatically

If the file doesn't exist, Python creates it.

If the file already exists, its previous contents are replaced.

------

UTF-8 is a character encoding that supports text from virtually all languages and symbols.

For example:

save_txt(
    "greeting.txt",
    "Hello, नमस्ते こんにちは"
)

Using UTF-8 ensures these characters are written correctly.

---------

Call:
save_txt("notes.txt", "Python is awesome")

            │
            ▼
Path("notes.txt")
            │
            ▼
write_text("Python is awesome")
            │
            ▼
Creates (or overwrites) notes.txt
            │
            ▼
notes.txt now contains:

Python is awesome


'''