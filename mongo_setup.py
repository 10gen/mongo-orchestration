import os
import subprocess
import platform
from urllib import request

DEFAULT_VERSION = "latest"
DEFAULT_URL = ""


class MongoDBInstaller:
    """Generic installer for MongoDB Community Edition"""

    def __init__(self, version=DEFAULT_VERSION, url=DEFAULT_URL):
        self._version = version
        self._url = url
        self._install = get_best_installer()

    def install(self):
        print("Attempting to install binary; ")
        self._install(self._version, self._url)


def brew_install(*args, version=DEFAULT_VERSION, **kwargs):
    """For brew supported devices, install MongoDB

    :param version: _description_, defaults to DEFAULT_VERSION
    :type version: _type_, optional
    """
    tap = "brew tap mongodb/brew"
    update = "brew update"
    install = f"brew install -q mongodb-community@{version}"
    for step in [tap, update, install]:
        subprocess.call(step.split(" "))


def is_intel():
    return platform.processor() == "i386"


brew_install.viable = lambda: subprocess.call(["which", "brew"]) == 0


def tar_install(*args, version=DEFAULT_VERSION, target="", **kwargs):
    """Download and install a tarball.
    Mimics instructions from
    https://www.mongodb.com/docs/v7.0/tutorial/install-mongodb-on-os-x-tarball/

    TODO: Make this compatible with any unix system

    :param version: _description_, defaults to DEFAULT_VERSION
    :type version: _type_, optional
    :param target: _description_, defaults to ""
    :type target: str, optional
    """
    chipset = "x86_64" if is_intel() else "arm64"
    filename = f"mongodb-macos-{chipset}-{version}"
    url = f"https://fastdl.mongodb.org/osx/{filename}"
    with request.urlopen(url) as src, open(f"{target or filename}.tgz", "wb+") as dst:
        dst.write(src.read())

    extract_command = f"tar -zxvf {target}.tgz"
    subprocess.call(extract_command.split(" "))

    path_install_command = f"sudo cp {filename}/bin/* usr/local/bin"
    subprocess.call(path_install_command.split(" "))


def get_best_installer():
    installers = [
        brew_install,
        tar_install,
    ]
    for installer in installers:
        if installer.viable():
            return installer


def download_mongo_binary(
    version=DEFAULT_VERSION,
    download_base=DEFAULT_URL,
    to_dir=os.curdir,
    delay=15,
    downloader_factory=get_best_installer,
):
    """Download setuptools from a specified location and return its filename

    `version` should be a valid setuptools version number that is available
    as an egg for download under the `download_base` URL (which should end
    with a '/'). `to_dir` is the directory where the egg will be downloaded.
    `delay` is the number of seconds to pause before an actual download
    attempt.

    ``downloader_factory`` should be a function taking no arguments and
    returning a function for downloading a URL to a target.
    """
    # making sure we use the absolute path
    to_dir = os.path.abspath(to_dir)
    tgz_name = "setuptools-%s.tar.gz" % version
    url = download_base + tgz_name
    saveto = os.path.join(to_dir, tgz_name)
    if not os.path.exists(saveto):  # Avoid repeated downloads
        log.warn("Downloading %s", url)
        downloader = downloader_factory()
        downloader(url, saveto)
    return os.path.realpath(saveto)
