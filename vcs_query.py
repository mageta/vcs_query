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
        print >> sys.stderr, "please specify a directory with vcards"
        sys.exit(1)

    if not os.path.isdir(vcard_dir):
        print >> sys.stderr, "please specify a directory with vcards"
        sys.exit(1)

    print "first line is ignored"

    cache = VcardCache(vcard_dir)
    entries = cache.vcards.values()
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
        self.last_vcard_dir_timestamp, self.vcards = self._load()
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
                if not self.vcards.has_key(path) or self.vcards[path].needs_update():
                    self.vcards[path] = Vcard(path)

    def _serialize(self):
        try:
            if not os.path.isdir(self.cache_dir):
                os.mkdir(self.cache_dir)
            with open(self.pickle_path, "w") as f:
                pickle.dump((self.last_vcard_dir_timestamp, self.vcards), f)
        except IOError:
            print "cannot write to cache file " + cache


class Vcard(object):
    def __init__(self, path):
        self.path = path
        self.timestamp = get_timestamp(path)
        with open(path) as f:
            vcs_string = f.read()

        component = self._read_component(vcs_string)
        data = component.contents["vcard"][0]

        self.name = ""
        self.mail = ""
        if data.contents.has_key("fn"):
            self.name = data.contents["fn"][0].value
        if data.contents.has_key("email"):
            self.mail = data.contents["email"][0].value.lower()

        self.description = "" # TODO?

    def _read_component(self, vcs_string):
        # vobject cannot parse lines containing a space and issues a warning
        # zimbra produces these lines
        # watch https://bugzilla.zimbra.com/show_bug.cgi?id=43702
        logger.setLevel(logging.FATAL)
        component = vobject.readOne(vcs_string, ignoreUnreadable=True)
        logger.setLevel(logging.ERROR)
        return component

    def needs_update(self):
        return get_timestamp(self.path) > self.timestamp

    def __str__(self):
        return self.mail.encode(output_encoding) +\
                "\t" + self.name.encode(output_encoding)\
                + "\t" + self.description

def get_timestamp(path):
    return os.stat(path).st_mtime 

if __name__ == "__main__":
    main(sys.argv[1:])
