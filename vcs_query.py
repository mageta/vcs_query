#!/usr/bin/env python3
# -*- coding: utf8 -*-

# This file is part of vcs_query - https://github.com/mageta/vcs_query
# SPDX-License-Identifier: MIT
# See file LICENSE for more information.

# TODO: modules documentation

import collections
import argparse
import hashlib
import logging
import pickle
import sys
import os
import re

# http://www.ietf.org/rfc/rfc2426.txt
import vobject

VOBJECT_LOGGER = logging.getLogger("vobject.base")
LOGGER = logging.getLogger(__name__)

Version = collections.namedtuple("Version", ["major", "minor", "patch"])
VERSION = Version(
    major=0,
    minor=3,
    patch=1,
)

def main(argv):
    optparser = argparse.ArgumentParser(prog=argv[0],
                                        description="Query VCard Files for "
                                                    "EMail Addresses")
    optparser.add_argument("pattern", metavar="PATTERN",
                           nargs='?', default=None,
                           help="only those lines that contain PATTERN will be"
                                "displayed")
    optparser.add_argument("--version",
                           action="version",
                           version="%(prog)s version "
                                   "{v.major:d}.{v.minor:d}.{v.patch:d}".format(
                                       v=VERSION))
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

    print("vcs_query.py, see https://github.com/mageta/vcs_query")

    # Load all contacts from the given VCard-Directories; duplicates are
    # automatically handled by using a set
    contacts_uniq = set()
    for vcdir in args.vcard_dir:
        try:
            for vcard in VcardCache(vcdir).vcards:
                if vcard:
                    if args.all_addresses:
                        contacts_uniq.update(vcard)
                    else:
                        contacts_uniq.add(vcard[0])
        except OSError as error:
            LOGGER.error("Error while reading VCard Dir: %s: %s", vcdir, error)

    # sort the found contacts according to the given command-line options
    if not args.sort_names:
        contacts = sorted(contacts_uniq,
                          key=(lambda x: (x.mail.lower(), x.name.lower(),
                                          x.description.lower())))
    else:
        contacts = sorted(contacts_uniq,
                          key=(lambda x: (x.name.lower(), x.mail.lower(),
                                          x.description.lower())))

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

        self.last_vcard_dir_timestamp = 0
        self.vcard_files = {}

        self._state = self._load()
        self._update()
        self._serialize()

    _cache_version = 1

    @property
    def _default_state(self):
        return (VcardCache._cache_version, 0, {})

    @property
    def _state(self):
        return (VcardCache._cache_version,
                self.last_vcard_dir_timestamp, self.vcard_files)

    @_state.setter
    def _state(self, value):
        self.last_vcard_dir_timestamp = value[1]
        self.vcard_files = value[2]

    def _load(self):
        try:
            with open(self.pickle_path, "rb") as cache:
                obj = pickle.load(cache)

                # prune invalid or outdated cache-files
                if not isinstance(obj, tuple) or len(obj) < 3:
                    raise RuntimeError("Invalid type")
                elif obj[0] != VcardCache._cache_version:
                    raise RuntimeError("Invalid Version ({})".format(obj[0]))

                return obj
        except (OSError, RuntimeError, AttributeError, EOFError, ImportError,
                IndexError, pickle.UnpicklingError) as error:
            if not isinstance(error, OSError) or error.errno != 2:
                LOGGER.warning("Cache file (%s) could not be read: %s",
                               self.pickle_path, error)
            return self._default_state

    def _update(self):
        vcard_dir_timestamp = get_timestamp(self.vcard_dir)
        if vcard_dir_timestamp > self.last_vcard_dir_timestamp:
            self.last_vcard_dir_timestamp = vcard_dir_timestamp

            paths = set()
            # let erros in os.scandir() bubble up.. the whole thing failed
            with os.scandir(self.vcard_dir) as directory:
                for node in directory:
                    try:
                        path = os.path.abspath(node.path)
                        if node.is_file():
                            paths.add(path)
                    except OSError as err:
                        LOGGER.error("Error reading VCard: %s: %s", node, err)

            # prune VCards that don't exist anymore
            for path in self.vcard_files.keys():
                if path not in paths:
                    del self.vcard_files[path]

            # add or update VCards
            for path in paths:
                vcard = self.vcard_files.get(path)
                if not vcard or vcard.needs_update():
                    try:
                        vcard = VcardFile(path)
                        self.vcard_files[path] = vcard
                    except OSError as err:
                        LOGGER.error("Error reading VCard: %s: %s", path, err)
                        try:
                            del self.vcard_files[path]
                        except KeyError:
                            pass

    def _serialize(self):
        try:
            if not os.path.isdir(self.cache_dir):
                os.mkdir(self.cache_dir)
            with open(self.pickle_path, "wb") as cache:
                pickle.dump(self._state, cache)
        except OSError:
            LOGGER.warning("Cannot write to cache file: %s", self.pickle_path)

    @property
    def vcards(self):
        for vcard_file in self.vcard_files.values():
            for vcard in vcard_file.vcards:
                yield vcard

class Vcard(object):
    Contact = collections.namedtuple("Contact", ["mail", "name", "description"])

    def __init__(self, component):
        self.name = ""
        if "fn" in component.contents:
            self.name = component.fn.value

        self.mails = []
        if "email" in component.contents:
            self.mails = [mail.value for mail in component.contents["email"]]

        self.description = ""
        if "note" in component.contents:
            self.description = "; ".join([
                line for line in component.note.value.splitlines() if line
            ])

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
        self.vcards = []
        self._read_components(path)

    def _read_components(self, path):
        VOBJECT_LOGGER.setLevel(logging.FATAL)

        # FIXME: can we at least guess what charset the file has?
        # let errors from file-IO bubble up, this whole VCard is failed
        with open(path, encoding="utf-8") as vcfile:
            components = vobject.readComponents(vcfile, ignoreUnreadable=True)
            for component in components:
                if component.name.lower() == "vcard":
                    self.vcards.append(Vcard(component))
                # hack to parse full emails for contained vcards:
                elif "vcard" in component.contents:
                    self.vcards.append(Vcard(component.vcard))
                else:
                    LOGGER.warning("No VCard in component: '%s' from file '%s'",
                                   component.name, path)

        VOBJECT_LOGGER.setLevel(logging.ERROR)

    def needs_update(self):
        return get_timestamp(self.path) > self.timestamp

def get_timestamp(path):
    return os.stat(path).st_mtime

if __name__ == "__main__":
    main(sys.argv)
