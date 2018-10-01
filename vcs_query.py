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
vobject_logger = logging.getLogger("vobject.base")
logger = logging.getLogger(__name__)
import locale
language, output_encoding = locale.getdefaultlocale()

def main(argv):
    """
    usage: $0 [<options>] [<substr>]
    only those lines that contain <substr> will be displayed
    options:
    -d --vcard-dir=         specify directory with vcards
    -s --starting-matches   display lines which start with <substr> first
    """
    vcard_dir = None
    starting_matches = False
    opts, args = gnu_getopt(argv, "d:s", ["vcard-dir=","starting-matches"])
    for opt, val in opts:
        if opt == "-d" or opt == "--vcard-dir":
            vcard_dir = val
        if opt == "-s" or opt == "--starting-matches":
            starting_matches = True

    if vcard_dir is None:
        sys.exit("please specify a directory with vcards")

    if not os.path.isdir(vcard_dir):
        sys.exit("please specify a directory with vcards")

    pattern = None
    if len(args) > 0:
        pattern = args[0].strip().lower() #re.compile(args[0].strip(), re.I)

    print "vcs_query.py, see http://github.com/marvinthepa/vcs_query"

    cache = VcardCache(vcard_dir)
    entries = cache.get_entries()
    entries.sort(key=str)
    if starting_matches and pattern:
        sortfunc = get_sortfunc(pattern)
        entries.sort(cmp=sortfunc, key=str)

    for vcard in entries:
        if len(vcard.mail) > 0:
            repr = str(vcard)
            if not pattern or pattern in repr.lower(): #.search(repr):
                print repr

def get_sortfunc(pattern):
    def sortfunc(a,b):
        if a.lower().startswith(pattern):
            if b.lower().startswith(pattern):
                return 0
            else:
                return -1
        else:
            if b.lower().startswith(pattern):
                return 1
            else:
                return 0

    return sortfunc

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
            paths = [ p for p in paths if os.path.isfile(p) ]
            for key in self.vcard_files.keys():
                if key not in paths:
                    del self.vcard_files[key]
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
        self.name = ""
        self.mail = ""
        if component.contents.has_key("fn"):
            self.name = component.fn.value
        if component.contents.has_key("email"):
            self.mail = component.email.value

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
        vobject_logger.setLevel(logging.FATAL)
        with open(path) as f:
            components = vobject.readComponents(f, ignoreUnreadable=True)
            self.vcards = []
            for component in components:
                if component.name.lower() == u'vcard':
                    self.vcards.append( Vcard(component) )
                # hack to parse full emails for contained vcards:
                elif component.contents.has_key("vcard"):
                    self.vcards.append( Vcard(component.vcard) )
                else:
                    logger.warning("no vcard in component: "
                            + component.name.encode(output_encoding)
                            + "from file " + path )

        vobject_logger.setLevel(logging.ERROR)

    def needs_update(self):
        return get_timestamp(self.path) > self.timestamp

    def __str__(self):
        result = "\n".join(self.vcards)

def get_timestamp(path):
    return os.stat(path).st_mtime

if __name__ == "__main__":
    main(sys.argv[1:])
