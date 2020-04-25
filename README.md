# Adding module loading functionality to Pyodide

This repository adds module loading functionality to Pyodide's console.html (based on the built artifacts of Pyodide).

The main files modified are
- [console.html](https://github.com/mauricelam/pyodide-built/blob/gh-pages/console.html) (The javascript code is modified to utilize the module loader and load
  packages from various URLs)
- [module_loader.py](https://github.com/mauricelam/pyodide-built/blob/gh-pages/module_loader.py) (The custom loader, added to sys.meta_path to load repositories and
  zip files if they are not already loaded by the built-in loader.)

Usage:
```
await pyodide.loadZipPackage('https://cors-anywhere.herokuapp.com/https://github.com/sfneal/PyPDF3/archive/master.zip/PyPDF3-master')
await pyodide.addUrlPackages({
  "requests": "https://raw.githubusercontent.com/psf/requests/master/requests",
  "urllib3": "https://raw.githubusercontent.com/urllib3/urllib3/master/src/urllib3",
  "chardet": "https://raw.githubusercontent.com/chardet/chardet/master/chardet",
  "certifi": "https://raw.githubusercontent.com/certifi/python-certifi/master/certifi",
  "idna": "https://raw.githubusercontent.com/kjd/idna/master/idna",
  "argcomplete": "https://raw.githubusercontent.com/kislyuk/argcomplete/master/argcomplete",
});
```
