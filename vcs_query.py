#!/usr/bin/env python3
# -*- coding: utf8 -*-

# TODO
# documentation

# http://www.ietf.org/rfc/rfc2426.txt
import vobject, sys, os
import collections
import argparse
import hashlib
import pickle
import re

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
                           required=True, action='append',
                           help="specify directory containing VCards (can be "
                                "given multiple times)")
    optparser.add_argument("-a", "--all-addresses",
                           required=False, action="store_true",
                           help="display all addresses stored for a contact")
    optparser.add_argument("-n", "--sort-names",
                           required=False, action="store_true",
                           help="sort the result according to the contact name "
                                "(the default is to sort according to mail-"
                                "address first)")
    optparser.add_argument("-r", "--regex",
                           required=False, action="store_true",
                           help="interpret PATTERN as regular expression "
                                "(syntax: https://docs.python.org/3/library/"
                                "re.html#regular-expression-syntax)")
    args = optparser.parse_args(argv[1:])

    for vcdir in args.vcard_dir:
        if not os.path.isdir(vcdir):
            optparser.error("'{}' is not a directory".format(vcdir))

    try:
        pattern = Pattern(args.pattern, args.regex)
    except re.error as error:
        optparser.error("Given PATTERN is not a valid regular "
                        "expression: {!s}".format(error))

    print("vcs_query.py, see http://github.com/marvinthepa/vcs_query")

    # Load all contacts from the given VCard-Directories; duplicates are
    # automatically handled by using a set
    contacts_uniq = set()
    for vcdir in args.vcard_dir:
        cache = VcardCache(vcdir)
        vcards = cache.get_entries()

        for vcard in vcards:
            if vcard:
                if args.all_addresses:
                    contacts_uniq.update(vcard)
                else:
                    contacts_uniq.add(vcard[0])

    # Convert set into list, so we can do the sorting
    if not args.sort_names:
        contacts = list(sorted(contacts_uniq,
                               key=(lambda x: (x.mail.lower(), x.name.lower(),
                                               x.description.lower()))))
    else:
        contacts = list(sorted(contacts_uniq,
                               key=(lambda x: (x.name.lower(), x.mail.lower(),
                                               x.description.lower()))))

    for contact in contacts:
        contact_formatted = "{}\t{}\t{}".format(contact.mail, contact.name,
                                                contact.description)

        if pattern.search(contact_formatted):
            print(contact_formatted)

class Pattern(object):
    def __init__(self, pattern, is_regex):
        self.match_all = False if pattern else True
        self.is_regex = is_regex

        if not self.match_all:
            if self.is_regex:
                self.pattern = re.compile(pattern, re.IGNORECASE)
            else:
                self.pattern = pattern.lower()

    def search(self, string):
        if self.match_all:
            return True

        if self.is_regex and self.pattern.search(string):
            return True
        elif not self.is_regex and self.pattern in string.lower():
            return True

        return False

class VcardCache(object):
    def __init__(self, vcard_dir):
        self.cache_dir = os.path.expanduser("~/.cache/")
        self.vcard_dir = os.path.normcase(os.path.normpath(vcard_dir))

        dhsh = hashlib.sha256()
        dhsh.update(self.vcard_dir.encode())
        self.pickle_path = os.path.join(self.cache_dir,
                                        "{}.vcs_query".format(dhsh.hexdigest()))

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
    Contact = collections.namedtuple("Contact", ["mail", "name", "description"])

    def __init__(self, component):
        self.name = ""
        self.mails = []
        if "fn" in component.contents:
            self.name = component.fn.value
        if "email" in component.contents:
            self.mails = [mail.value for mail in component.contents["email"]]

        self.description = "" # TODO?

    def _get_mail_contact(self, mail):
        return Vcard.Contact(str(mail), str(self.name), str(self.description))

    def __getitem__(self, i):
        return self._get_mail_contact(self.mails[i])

    def __iter__(self):
        for mail in self.mails:
            yield self._get_mail_contact(mail)

    def __len__(self):
        return len(self.mails)

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

def get_timestamp(path):
    return os.stat(path).st_mtime

if __name__ == "__main__":
    main(sys.argv)
