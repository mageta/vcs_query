vcs_query
=========

eMail query-command to use vCards in mutt and Vim.

What does it do?
----------------

This scripts parses all vCards in the directory given with `-d`
and prints them either in a format that is usable as `$query_command` in mutt,
or in a format usable for a completion-function (`completefunc`) in vim.

The first non-option argument is interpreted as a pattern to filter the
resulting lines.

As parsing can take some time, the results are cached in
`~/.cache/*.vcs_query` (the first part is a hash of the path to the directory
you used as argument for `-d`; this way each directory gets its own cache).

### Table of Content

1. [Requirements](#requirements)
1. [Installation](#installation)
1. [CLI synopsis](#cli-synopsis)
1. [Mutt](#mutt)
    1. [Configuration](#mutt-configuration)
    1. [Output Format](#mutt-output-format)
1. [Vim](#vim)
    1. [Configuration](#vim-configuration)
    1. [Output Format](#vim-output-format)
1. [Limitations](#limitations)
1. [Credits](#credits)

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
and add that directory to your `$PATH` environment variable (you probably want
to use your shell's rc-file, like `~/.bashrc` for bash, look into your shell's
manual for more information on that); this way you don't need to be root in
order to install the script.

CLI synopsis
------------

```
usage: vcs_query.py [-h] [--version] -d VCARD_DIR [-a] [-n] [-r]
                    [-m {mutt,vim}]
                    [PATTERN]

Query vCard Files for EMail Addresses

positional arguments:
  PATTERN               only those lines that contain PATTERN will bedisplayed

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -d VCARD_DIR, --vcard-dir VCARD_DIR
                        specify directory containing vCards (can be given
                        multiple times)
  -a, --all-addresses   display all addresses stored for a contact
  -n, --sort-names      sort the result according to the contact name (the
                        default is to sort according to mail-address first)
  -r, --regex           interpret PATTERN as regular expression (syntax:
                        https://docs.python.org/3/library/re.html#regular-
                        expression-syntax)
  -m {mutt,vim}, --mode {mutt,vim}
                        select output-mode (default: mutt)
```

Mutt
----

<span id="mutt-configuration"></span>
### Configuration

To use `vcs_query.py`, instead of the aliases defined in your `.muttrc`, put
something like this in your `.muttrc`:

```
set query_command="vcs_query.py -d ~/.local/share/contacts -a -n %s"
```

For more options, or what these options mean, run `vcs_query.py --help`, or
look above into the [synopsis](#cli-synopsis).

Here is the corresponding documentation of the mutt-project:
[documentation](http://www.mutt.org/doc/manual/#query), [configuration
reference](http://www.mutt.org/doc/manual/#query-command). More tools like this
one can be found in the mutt wiki:
[here](https://gitlab.com/muttmua/mutt/wikis/QueryCommand).

<span id="mutt-output-format"></span>
### Output Format

With `vcs_query.py --mode mutt` (or simply not specifying any mode, as this is
the default) the output will be formatted like this:

```
vcs_query.py, see https://github.com/mageta/vcs_query
<eMail-Adr #1>\t<Name #1>\t<Description #1>
<eMail-Adr #2>\t<Name #2>\t<Description #2>
....
<eMail-Adr #N>\t<Name #N>\t<Description #N>
```

The mapping between the vCard specification ([RFC
6350](https://tools.ietf.org/html/rfc6350)) and the output fields is as
follows:

| Output-Field | vCard Type |
|--------------|------------|
| eMail-Adr    | EMAIL      |
| Name         | FN         |
| Description  | NOTE       |

Each line in the output will always only contain a single eMail-Address (this
is a requirement by mutt). If multiple eMails are stored in a single vCard, the
option `-a`/`--all-addresses` ([synopsis](#cli-synopsis)) can be used to print
a line for each stored eMail (Name and Description will be the same in each of
those lines).

Because mutt requires exactly one line per contact, we mangle the NOTE type
of the vCard so that the Description field will not contain any line breaks.

Vim
---

<span id="vim-configuration"></span>
### Configuration

The configuration for Vim is slightly more involved, as there is no predefined
interface for completing eMail-Addresses. But it is straight-forward to write a
completion-function and use that as user-defined completion for files that have
the filetype `mail`, `patch`, and whatever other filetype you'd enter
eMail-Addresses regularly.

If you don't care for any more details, here is a chunk of code that does
exactly this. If you paste that into your `vimrc`, and adapt the `g:vcs_dir`
variable (near to the top, be aware that the `\` is necessary for
line-continuation), it should just work. Use the keybinding for [User defined
completion](http://vimhelp.appspot.com/insert.txt.html#ins-completion) (per
default Ctrl-X Ctrl-U) to trigger the completion.

```vim
" mail address completion {{{
    let g:vcs_query = "vcs_query.py"
    let g:vcf_options = "-a -n"
    let g:vcs_dir = [ "~/Documents/Contacts/Work",
                    \ "~/Documents/Contacts/Personal"]

    fun! CompleteMail(findstart, base)
        if a:findstart
            " guess the start of the address
            let line = getline('.')
            let pos = col('.') - 1  " character to look at
            let start = -3          " start of the search-term
                                    " return -3 if we never find it
            let delimiter = '[,:]'
            while pos >= 0
                " Stop when encountering a delimiter
                if line[pos] =~ delimiter
                    break
                endif

                " For everything that is not a whitespace-
                " character remeber the postion as possible
                " start of the search-term
                if line[pos] !~ '\s'
                    let start = pos
                endif

                " Count everything that is not a delimiter
                let pos -= 1
            endwhile
            return start
        else
            " Don't return all addresses, this is probably too much
            if len(a:base) <= 0
                return []
            endif

            let res = systemlist(
                \ g:vcs_query
                \ . " -d " . join(g:vcs_dir, " -d ")
                \ . " " . g:vcf_options
                \ . " -m vim "
                \ . shellescape(a:base))
            return res[1:]
        endif
    endfun

    if has("autocmd")
        autocmd Filetype mail,gitsendemail,patch,gitcommit
            \ setlocal completefunc=CompleteMail
    endif
" }}}
```

What this does is, it creates a function `CompleteMail()` that is called via
the hook for [User defined
completion](http://vimhelp.appspot.com/insert.txt.html#compl-function):
[completefunc](http://vimhelp.appspot.com/insert.txt.html#complete-functions).
But only for buffers that have the
[Filetype](http://vimhelp.appspot.com/filetype.txt.html) set to either `mail`,
`gitsendemail`, `patch`, or `gitcommit` (the list is near the bottom of the
code).

**This might conflict with other plugins you use.** Its hard to tell, without
knowing all plugins you use, and how they are implemented. So, you'll have to
figure this out yourself.

The function `CompleteMail()` itself will try to figure out where the
eMail-Address you want to type starts, then pass that to `vcs_query.py`
to figure out the rest, and finally return a (possibly empty) list of
found addresses back to vim.

Figuring out the start of the address is not exact in every possible case.
It'll try to jump spaces to make it possible to narrow down the search, this
makes it somewhat error-prone if used in normal sentences, or other spots,
where there is no clear delimiter for when to stop the "scoping". It is
oriented to work with the usual spots in files, where you'd write
eMail-Addresses: address-lines, such as `To:`, `Cc:`, `Signed-off-by:`. It will
search backwards from the cursor-position and stop at `:`, `,`, or line-start;
this is then passed to `vcs_query.py` as `PATTERN`.

<span id="vim-output-format"></span>
### Output Format

With `vcs_query.py --mode vim` the output will be formatted like this:

```
vcs_query.py, see https://github.com/mageta/vcs_query
<Name #1> \<<eMail-Adr #1>\>
<Name #2> \<<eMail-Adr #2>\>
....
<Name #N> \<<eMail-Adr #N>\>
```

The mapping between the vCard specification is the same as for
[mutt](#mutt-output-format), as is the fact that it will only print one
eMail-Address per contact, unless you pass `-a`/`--all-addresses` as option
([synopsis](#cli-synopsis)).

The names will be encoded according to [RFC
2047](https://tools.ietf.org/html/rfc2047.html), if they contain any characters
that are not printable as US-ASCII. **NOTE:** this is not true while matching
your input on the found vCards, only when the matching contacts are printed;
this is so the PATTERN doesn't need to be encoded in the same way as in RFC
2047 (ideally you'll never notice the fact that this is done this way).

Limitations
-----------

Some know limitation either on the script, or on the provided data:

* The vCards *MUST* be encoded in UTF-8. This is a limitation introduced by
  the latest vCard RFC: <https://tools.ietf.org/html/rfc6350#section-3.1>; and
  quite frankly, it makes the implementation easier.

Credits
-------

* Martin Sander (aka. marvinthepa): idea, design, and initial implementation
* Benjamin Block (aka. mageta): Python 3 conversion, cleanups, some more options
