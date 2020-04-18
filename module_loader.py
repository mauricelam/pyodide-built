import importlib
import importlib.abc
import sys
import io
from js import loader
import json


sys.remote_path = ['pymodules.json']


class InternetPathFinder(importlib.abc.MetaPathFinder):

    def __init__(self):
        self.loaded_listings = set()
        self.package_listings = {}

    def add_packages(**kwargs):
        listings = dict(kwargs)
        listings.update(self.package_listings)
        self.package_listings = listings

    def _load_package_list(self):
        for url in sys.remote_path:
            if url not in self.loaded_listings:
                try:
                    listing = json.loads(_load_url(url))
                    listing.update(self.package_listings)
                    self.package_listings = listing
                except JsException as e:
                    print(f'Cannot load listings {url}', e, file=sys.stderr)
                self.loaded_listings.add(url)

    def _load_spec(self, fullname, pkg_url, *, path=None):
        # Import the source mimicking Python's path resolution
        # https://www.python.org/dev/peps/pep-0420/#specification
        if pkg_url != '__namespace__':
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
        print('finding spec', fullname, path, target)
        if path is None:
            if fullname not in self.package_listings:
                # Refresh the list with any new items added to
                # sys.remote_path
                self._load_package_list()
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
            return str(err_obj)


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


finder = InternetPathFinder()
sys.meta_path.append(finder)
