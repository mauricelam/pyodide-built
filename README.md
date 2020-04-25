# Adding module loading functionality to Pyodide

This repository adds module loading functionality to Pyodide's console.html (based on the built artifacts of Pyodide).

The main files modified are
- [console.html](https://github.com/mauricelam/pyodide-built/blob/gh-pages/console.html) (The javascript code is modified to utilize the module loader and load
  packages from various URLs)
- [module_loader.py](https://github.com/mauricelam/pyodide-built/blob/gh-pages/module_loader.py) (The custom loader, added to sys.meta_path to load repositories and
  zip files if they are not already loaded by the built-in loader.)
