vcs_query
=========

query-command to use vcards in mutt

What does it do?
----------------

This scripts parses all VCards in the directory given with `-d`
and prints them in a format that is usable as `$query-command` in mutt.

The first non-option argument is interpreted as a pattern to filter the
resulting lines.

As parsing can take some time, the results are cached in
`~/.cache/*.vcs_query` (the first part is a hash of the path to the directory
you used as argument for `-d`; this way each directory gets its own cache).

Requirements
------------

To use `vcs_query.py` you will need at least:

1. **Python 3** (tested with Python 3.6.6)
    * linux-distributions usually package this with names like `python3`

2. Python **vobject** library (tested with vobject 0.9.4.1)
    * linux-distributions usually packages this with names like
      `python-vobject`, or `python3-vobject` (you'll have to make sure they
      package it in a form so that the Python 3 interpreter can use it)
    * alternatively you can use `pip` to install this (again, make sure you
      use the pip version that corresponds to Python 3), e.g.:
      `pip3 install --user vobject`

Installation
------------

Simply put `vcs_query.py` into an arbitrary directory listed in your `$PATH`
environment variable. You don't need to put it into any of the default system
directories like `/bin`, or `/usr/bin`; as a user you can put it into `~/bin`,
and add that directory to your `$PATH` (you probably want to use your shell's
rc-file, like `~/.bashrc` for bash, look into your shell's manual for more
information on that); this way you don't need to be root in order to install
the script.

Mutt Configuration
------------------

To use `vcs_query.py`, instead of the aliases defined in your `.muttrc`, put
this in your `.muttrc`:

```
set query_command="vcs_query.py -d ~/.local/share/contacts -a -n %s"
```

Here is the corresponding documentation of the mutt-project:
[documentation](http://www.mutt.org/doc/manual/#query), [configuration
reference](http://www.mutt.org/doc/manual/#query-command).

vcs_query.py CLI synopsis
-------------------------

```
usage: vcs_query.py [-h] [--version] -d VCARD_DIR [-a] [-n] [-r] [PATTERN]

Query VCard Files for EMail Addresses

positional arguments:
  PATTERN               only those lines that contain PATTERN will bedisplayed

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -d VCARD_DIR, --vcard-dir VCARD_DIR
                        specify directory containing VCards (can be given
                        multiple times)
  -a, --all-addresses   display all addresses stored for a contact
  -n, --sort-names      sort the result according to the contact name (the
                        default is to sort according to mail-address first)
  -r, --regex           interpret PATTERN as regular expression (syntax:
                        https://docs.python.org/3/library/re.html#regular-
                        expression-syntax)
```

Credits
-------

* Martin Sander (aka. marvinthepa): idea, design, and initial implementation
* Benjamin Block (aka. mageta): Python 3 conversion, cleanups, some more options
