#!/usr/bin/env python
# -*- coding: utf8 -*-

# TODO
# documentation

# http://www.ietf.org/rfc/rfc2426.txt
import vobject, sys, os, re
from getopt import gnu_getopt

try:
    import cPickle as pickle
except:
    import pickle

import logging
logger = logging.getLogger("vobject.base")
import locale
language, output_encoding = locale.getdefaultlocale()

def main(argv):
    vcard_dir = None
    opts, args = gnu_getopt(argv, "d:", ["vcard-dir="])
    for opt, val in opts:
        if opt == "-d" or opt == "--vcard-dir":
            vcard_dir = val

    if len(args) < 1:
        pattern = re.compile(".*", re.I)
    else:
        pattern = re.compile(args[0].strip())

    if vcard_dir is None:
        sys.exit("please specify a directory with vcards")

    if not os.path.isdir(vcard_dir):
        sys.exit("please specify a directory with vcards")

    print "first line is ignored"

    cache = VcardCache(vcard_dir)
    entries = cache.get_entries()
    entries.sort(key=str)

    for vcard in entries:
        if len(vcard.mail) > 0:
            repr = str(vcard)
            if pattern.search(repr):
                print repr

class VcardCache(object):
    def __init__(self, vcard_dir):
        self.cache_dir = os.path.expanduser("~/.cache/")
        self.pickle_path = os.path.join(self.cache_dir, "vcard_query")
        self.vcard_dir = vcard_dir
        self.last_vcard_dir_timestamp, self.vcard_files = self._load()
        self._update()
        self._serialize()

    def _load(self):
        if os.path.isfile(self.pickle_path):
            with open(self.pickle_path, "r") as f:
                return pickle.load(f)
        else:
            return 0, {}

    def _update(self):
        if get_timestamp(self.vcard_dir) > self.last_vcard_dir_timestamp:
            paths = os.listdir(self.vcard_dir)
            paths = [ os.path.join(self.vcard_dir, p) for p in paths ]
            for path in paths:
                if not self.vcard_files.has_key(path) or self.vcard_files[path].needs_update():
                    self.vcard_files[path] = VcardFile(path)
        self.vcards = []
        for vcard_file in self.vcard_files.values():
            self.vcards.extend(vcard_file.vcards)

    def _serialize(self):
        try:
            if not os.path.isdir(self.cache_dir):
                os.mkdir(self.cache_dir)
            with open(self.pickle_path, "w") as f:
                pickle.dump((self.last_vcard_dir_timestamp, self.vcard_files), f)
        except IOError:
            print "cannot write to cache file " + cache

    def get_entries(self):
        return self.vcards

class Vcard(object):
    def __init__(self, component):
        data = component.contents["vcard"][0]
        self.name = ""
        self.mail = ""
        if data.contents.has_key("fn"):
            self.name = data.contents["fn"][0].value
        if data.contents.has_key("email"):
            self.mail = data.contents["email"][0].value.lower()

        self.description = "" # TODO?

    def __str__(self):
        return self.mail.encode(output_encoding) +\
                "\t" + self.name.encode(output_encoding)\
                + "\t" + self.description

class VcardFile(object):
    def __init__(self, path):
        self.path = path
        self.timestamp = get_timestamp(path)
        self._read_components(path)

    def _read_components(self, path):
        logger.setLevel(logging.FATAL)
        with open(path) as f:
            components = vobject.readComponents(f, ignoreUnreadable=True)
            self.vcards = [ Vcard(component) for component in components ]
        logger.setLevel(logging.ERROR)

    def needs_update(self):
        return get_timestamp(self.path) > self.timestamp

    def __str__(self):
        result = "\n".join(self.vcards)

def get_timestamp(path):
    return os.stat(path).st_mtime 

if __name__ == "__main__":
    main(sys.argv[1:])
