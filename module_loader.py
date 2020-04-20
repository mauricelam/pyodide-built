import importlib
import importlib.abc
import sys
import io
import tempfile
import zipfile
import os
from js import loader, pyodide, Promise, Object, fetch
from micropip import _get_url_async


def load_zip_packages(urls):
    return Promise.all([load_zip_package(url) for url in urls])


def load_zip_package(url, zip_prefix=None):
    """Loads a given zip package as a python module.

    Similar to zipimport, you can contain a path within the archive to only
    import from that subdirectory. For example,
    https://github.com/iodide-project/pyodide/archive/master.zip/packages will
    only import from the packages subdirectory inside the zip file.
    """
    zip_file_url, path_inside_zip = url.split('.zip', 1)
    zip_url = zip_file_url + '.zip'

    def handle_zip_result(bytestream):
        # zipimport (for Python < 3.8) doesn't support archive comments
        # so we copy all the files into a new archive
        fd, zip_path = tempfile.mkstemp(
            prefix=zip_prefix,
            suffix='.zip')
        with zipfile.ZipFile(bytestream, 'r') as zin:
            with zipfile.ZipFile(open(fd, 'wb'), 'w') as zout:
                sys.path.append(zip_path + path_inside_zip)
                for zipinfo in zin.infolist():
                    zout.writestr(zipinfo, zin.read(zipinfo.filename))
        return None
    return _get_url_async(zip_url, handle_zip_result)


def add_url_packages(package_dict):
    iterable = package_dict.items() if hasattr(package_dict, 'items') \
               else Object.entries(package_dict)
    for name, url in iterable:
        add_url_package(name, url)
    return Promise.resolve(None)


def add_url_package(name, url):
    """Adds a URL-based package.

    After calling this function, importing `name` will try to load the package
    from `url`, using rules similar to how Python loads from the filesystem.
    For example, if the URL is http://www.example.python.org/zipimport, it will
    first try to load http://www.example.python.org/zipimport/__init__.py. If
    it doesn't exist, then it will try to load
    http://www.example.python.org/zipimport.py. Implicit namespace packages are
    not supported because we cannot tell existence of "directories" from a web
    URL.
    """
    _module_loader.add_package(name, url)
    # Future-proof return value to support asynchronous fetching
    return Promise.resolve(None)


pyodide.loadZipPackage = load_zip_package
pyodide.loadZipPackages = load_zip_packages
pyodide.addUrlPackage = add_url_package
pyodide.addUrlPackages = add_url_packages


class InternetPathFinder(importlib.abc.MetaPathFinder):

    def __init__(self):
        self.package_listings = {}

    def add_package(self, name, url):
        if name in self.package_listings:
            return
        self.package_listings[name] = url

    def _load_spec(self, fullname, pkg_url, *, path=None):
        # Import the source mimicking Python's path resolution
        # https://www.python.org/dev/peps/pep-0420/#specification
        if pkg_url:  # Falsy values are used to create namespace packages
            try:
                file_url = pkg_url + '/__init__.py'
                spec = importlib.machinery.ModuleSpec(
                    fullname,
                    InternetSourceFileLoader(file_url, pkg_url),
                    is_package=True,
                    origin=file_url)
                spec.submodule_search_locations = [pkg_url]
                return spec
            except JsException:
                try:
                    file_url = pkg_url + '.py'
                    spec = importlib.machinery.ModuleSpec(
                        fullname,
                        InternetSourceFileLoader(file_url, path),
                        is_package=False,
                        origin=file_url)
                    return spec
                except JsException as e:
                    print(f'Unable to load module "{fullname}"', e,
                          file=sys.stderr)
        if fullname in self.package_listings:
            # If the package name is in the package listings, assume
            # this is a namespace package, since the listing is essentially
            # asserting that the package exists. We don't implicitly assume the
            # existence or check for "directories" since the concept doesn't
            # map well to web URLs.
            spec = importlib.machinery.ModuleSpec(
                fullname,
                None,
                is_package=True)
            spec.submodule_search_locations = [pkg_url]
            return spec
        else:
            return None

    def find_spec(self, fullname, path, target=None):
        # print('finding spec', fullname, path, target)
        if path is None:
            if fullname in self.package_listings:
                pkg_url = self.package_listings[fullname]
                return self._load_spec(fullname, pkg_url)
        elif path:
            path = path[0]
            filename = fullname.split('.')[-1]
            return self._load_spec(
                fullname,
                f'{path}/{filename}',
                path=path)
        return None


class JsException(Exception):

    def __init__(self, *, xhr=None, err_obj=None):
        super().__init__()
        self.xhr = xhr
        self.err_obj = err_obj

    def __str__(self):
        if self.xhr:
            return f'HTTP error {self.xhr.status}'
        else:
            return str(self.err_obj)


def _load_url(url):
    xhr, err = loader.open_url(url)
    if err is not None or xhr.status != 200:
        raise JsException(xhr=xhr, err_obj=err)
    return xhr.response


class InternetSourceFileLoader(
        importlib.abc.SourceLoader,
        importlib.abc.ResourceReader):

    def __init__(self, url, resource_url_prefix):
        self.url = url
        self.source_code = _load_url(url)
        self.resource_url_prefix = resource_url_prefix

    def get_data(self, path):
        return self.source_code.encode('utf-8')

    def get_filename(self, fullname):
        return self.url

    def get_resource_reader(self, spec):
        return self

    def open_resource(self, resource):
        # Note: Since this fetches the resources synchronously as text, it will
        # not work for binary files, since the browser scrubs all invalid
        # unicode characters.
        try:
            response = _load_url(f'{self.resource_url_prefix}/{resource}')
            return io.BytesIO(response.encode('utf-8'))
        except JsException as e:
            raise FileNotFoundError(str(e))

    def resource_path(self, resource):
        raise FileNotFoundError('Paths are not available for internet modules')

    def is_resource(self, name):
        try:
            self.open_resource(name)
            return True
        except FileNotFoundError:
            raise

    def contents(self):
        # Return empty sequence since we can't list contents for URLs
        return ()


_module_loader = InternetPathFinder()
sys.meta_path.append(_module_loader)
