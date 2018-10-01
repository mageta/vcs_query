#!/usr/bin/env python3
# -*- coding: utf8 -*-

# TODO
# documentation

# http://www.ietf.org/rfc/rfc2426.txt
import vobject, sys, os
import functools
import argparse
import pickle

import logging
vobject_logger = logging.getLogger("vobject.base")
logger = logging.getLogger(__name__)

def main(argv):
    optparser = argparse.ArgumentParser(prog=argv[0],
                                        description="Query VCard Files for "
                                                    "EMail Addresses")
    optparser.add_argument("pattern", metavar="PATTERN",
                           nargs='?', default=None,
                           help="only those lines that contain PATTERN will be"
                                "displayed")
    optparser.add_argument("-d", "--vcard-dir",
                           required=True,
                           help="specify directory with vcards")
    optparser.add_argument("-s", "--starting-matches",
                           required=False, action="store_true",
                           help="display lines which start with PATTERN first")
    optparser.add_argument("-a", "--all-addresses",
                           required=False, action="store_true",
                           help="display all addresses stored for a contact")
    args = optparser.parse_args(argv[1:])

    if not os.path.isdir(args.vcard_dir):
        sys.exit("please specify a directory with vcards")

    pattern = args.pattern
    if pattern:
        pattern = pattern.strip().lower()

    print("vcs_query.py, see http://github.com/marvinthepa/vcs_query")

    cache = VcardCache(args.vcard_dir)
    entries = cache.get_entries()
    entries.sort(key=(lambda x: str(x).lower()))
    if args.starting_matches and pattern:
        sortfunc = get_sortfunc(pattern)
        keyfunc = functools.cmp_to_key(sortfunc)
        entries.sort(key=keyfunc)

    for vcard in entries:
        if vcard:
            if args.all_addresses:
                contact_data = str(vcard)
            else:
                contact_data = vcard[0]

            if not pattern or pattern in contact_data.lower():
                print(contact_data)

def get_sortfunc(pattern):
    def sortfunc(a,b):
        if str(a).lower().startswith(pattern):
            if str(b).lower().startswith(pattern):
                return 0
            else:
                return -1
        else:
            if str(b).lower().startswith(pattern):
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
            with open(self.pickle_path, "rb") as f:
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
                if path not in self.vcard_files or self.vcard_files[path].needs_update():
                    self.vcard_files[path] = VcardFile(path)
        self.vcards = []
        for vcard_file in self.vcard_files.values():
            self.vcards.extend(vcard_file.vcards)

    def _serialize(self):
        try:
            if not os.path.isdir(self.cache_dir):
                os.mkdir(self.cache_dir)
            with open(self.pickle_path, "wb") as f:
                pickle.dump((self.last_vcard_dir_timestamp, self.vcard_files), f)
        except IOError:
            print("cannot write to cache file {!s}".format(self.pickle_path))

    def get_entries(self):
        return self.vcards

class Vcard(object):
    def __init__(self, component):
        self.name = ""
        self.mails = []
        if "fn" in component.contents:
            self.name = component.fn.value
        if "email" in component.contents:
            self.mails = [mail.value for mail in component.contents["email"]]

        self.description = "" # TODO?

    def __getitem__(self, i):
        mail = self.mails[i]
        return "{!s}\t{!s}\t{!s}".format(mail, self.name, self.description)

    def __len__(self):
        return len(self.mails)

    def __str__(self):
        return "\n".join(self)

class VcardFile(object):
    def __init__(self, path):
        self.path = path
        self.timestamp = get_timestamp(path)
        self._read_components(path)

    def _read_components(self, path):
        vobject_logger.setLevel(logging.FATAL)
        # FIXME: can we at least guess what charset the file has?
        with open(path, encoding="utf-8") as f:
            components = vobject.readComponents(f, ignoreUnreadable=True)
            self.vcards = []
            for component in components:
                if component.name.lower() == "vcard":
                    self.vcards.append( Vcard(component) )
                # hack to parse full emails for contained vcards:
                elif "vcard" in component.contents:
                    self.vcards.append( Vcard(component.vcard) )
                else:
                    logger.warning("no vcard in component: %s from file %s",
                                   component.name, path)

        vobject_logger.setLevel(logging.ERROR)

    def needs_update(self):
        return get_timestamp(self.path) > self.timestamp

    def __str__(self):
        return "\n".join(self.vcards)

def get_timestamp(path):
    return os.stat(path).st_mtime

if __name__ == "__main__":
    main(sys.argv)
