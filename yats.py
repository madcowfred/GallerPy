# Copyright (c) 2001 Brett Haydon email:bbhaydon@bigpond.com
# Permission to use, copy, modify, and distribute this software and
# its documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appear in all copies and
# that both that copyright notice and this permission notice appear in
# supporting documentation.
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
# SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS, IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
# SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER
# RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF
# CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

# COPYRIGHT (C) 1996-9  ROBIN FRIEDRICH  email:Robin.Friedrich@pdq.net
# Permission to use, copy, modify, and distribute this software and
# its documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appear in all copies and
# that both that copyright notice and this permission notice appear in
# supporting documentation.
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
# SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS, IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
# SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER
# RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF
# CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.


__author__ = "Brett Haydon (bbhaydon@bigpond.com)"
__version__ = "$Revision$"[11:-2]

PRINTECHO = 1
MissingTag="Missing Matching End Tag"
import string, re, os, types

class StringTemplate:
    """Generate documents based on a template and a substitution mapping.

    Must use Python 1.5 or newer. Uses re and the get method on dictionaries.

    Usage:
       T = TemplateDocument('Xfile')
       T.substitutions = {'month': ObjectY, 'town': 'Scarborough'}
       T.write('Maine.html')

    A dictionary, or object that behaves like a dictionary, is assigned to the
    *substitutions* attribute which has symbols as keys to objects. Upon every
    occurance of these symbols surrounded by braces {} in the source template,
    the corresponding value is converted to a string and substituted in the output.
    
    For example, source text which looks like:
     I lost my heart at {town} Fair.
    becomes:
     I lost my heart at Scarborough Fair.

    Symbols in braces which do not correspond to a key in the dictionary are removed.

    An optional third argument to the class is a list or two strings to be
    used as the delimiters instead of { } braces. They must be of the same
    length; for example ['##+', '##'] is invalid.
    
    Conditional substitution is denoted by a begin and end HTML comment tag with
    matching symbols as above. eg. <!--{tag}--> block <!--{tag-->.
    A Conditional substitution remains in place unless you extract it

    Usage:
        T.extract('tag')    

    A row, or rows of data is as conditional substitution, but the substution value is itself
    a dictionary object and a tuple of dictionaries respectively.
    
    """
    def __init__(self, template, substitutions=None,**kw):
        self.delimiters = ['{', '}']
        self.__dict__.update(kw)
        if len(self.delimiters) != 2:
            raise ValueError("delimiter argument must be a pair of strings")
        self.delimiter_width = len(self.delimiters[0])
        delimiters = map(re.escape, self.delimiters)
        self.subpatstr = delimiters[0] + "[\w_]+" + delimiters[1]
        self.subpat = re.compile(self.subpatstr)
        self.substitutions = substitutions or {}
        self.set_template(template)
        
    def set_template(self, template):
        self.source = template
    
    def keys(self):
        return self.substitutions.keys()

    def __setitem__(self, name, value):
        self.substitutions[name] = value
        
    def __getitem__(self, name):
        return self.substitutions[name]
      
    def __str__(self):
        return self._sub(self.source).replace('<!---->', '')

    def _sub(self, source, subs=None):
        """Perform source text substitutions.

        *source* string containing template source text
        *subs* mapping of symbols to replacement values
        """
        substitutions = subs or self.substitutions
        dw = self.delimiter_width
        i = 0
        output = []
        groups = {}
        matched = self.subpat.search(source[i:])
        while matched:
            a, b = matched.span()
            token = source[i+a+dw:i+b-dw]
            substitute = substitutions.get(token, '')
            subtype = type(substitute)
            if subtype in [types.ListType, types.TupleType, types.InstanceType, types.DictType]:
                newsearch = '<!--{%s}-->'% token
                groupsubpat = re.compile(newsearch)
                groupmatch = groupsubpat.search(source[i+b+3:])
                if groupmatch:
                    output.append(source[i:i+a-4])
                    b = b + 3
                    startendtoken,endendtoken = groupmatch.span()
                    groups[token] = StringTemplate(source[i+b:i+b+startendtoken])
                    source = source[:i+a-4] + source[i+b+endendtoken:]
                    newsubs = substitutions.copy()
                    if subtype in (types.ListType, types.TupleType):
                         for row in substitute:
                            newsubs = substitutions.copy()
                            newsubs.update(row)
                            groups[token].substitutions = newsubs
                            output.append(str(groups[token]))
                    elif subtype == types.DictType:
                        newsubs = substitutions.copy()
                        newsubs.update(substitute)
                        groups[token].substitutions = newsubs
                        output.append(str(groups[token]))
                    else:
                        substitute.substitutions = newsubs
                        output.append(str(substitute))
                    b = a - 4
                else:
                    raise MissingTag
            else:
                output.append(source[i:i+a])
                output.append(str(substitute))
            i = i + b
            matched = self.subpat.search(source[i:])
        else:
            output.append(source[i:])
        return string.join(output, '')
    def extract(self, token):
        """Extract section marked with beginning and end <!--{token}-->.
        
        Updates the substitution dictionary with the text from the region.
        """
        self.R = re.compile(r"<!--{%(token)s}-->(?P<text>.*?)<!--{%(token)s}-->"% vars(), re.S)
        source = self.source
        a = 0
        newtemplate = []
        d1, d2 = self.delimiters
        while 1:
            m = self.R.search(source, a)
            if m:
                start, end = m.span()
                newtemplate.append(source[a:start])
                a = end
                newtemplate.append(d1+token+d2)
            else:
                newtemplate.append(source[a:])
                break
        self.source = string.join(newtemplate, '')

    def write(self, filename=None):
        """Emit the Document HTML to a file or standard output.
        
        Will not overwrite file is it exists and is textually the same.
        In Unix you can use environment variables in filenames.
        Will print to stdout if no argument given.
        """
        if filename:
            filename = mpath(filename)
            if os.path.exists(filename):
                s = str(self)
                if compare_s2f(s, filename):
                    f = open(filename, 'w')
                    f.write(str(self))
                    f.close()
                    if PRINTECHO: print 'wrote: "'+filename+'"'
                else:
                    if PRINTECHO: print 'file unchanged: "'+filename+'"'
            else:
                f = open(filename, 'w')
                f.write(str(self))
                f.close()
                if PRINTECHO: print 'wrote: "'+filename+'"'
        else:
            import sys
            sys.stdout.write(str(self))

class TemplateDocument(StringTemplate):
    
    def set_template(self, template):
        f = open(mpath(template))
        self.source = f.read()
        f.close()

def mpath(path):
    """Converts a POSIX path to an equivalent Macintosh path.

    Works for ./x ../x /x and bare pathnames.
    Won't work for '../../style/paths'.

    Also will expand environment variables and Cshell tilde
    notation if running on a POSIX platform.
    """
    import os
    if os.name == 'mac' : #I'm on a Mac
        if path[:3] == '../': #parent
            mp = '::'
            path = path[3:]
        elif path[:2] == './': #relative
            mp = ':'
            path = path[2:]
        elif path[0] == '/': #absolute
            mp = ''
            path = path[1:]
        else: # bare relative
            mp = ''
        pl = string.split(path, '/')
        mp = mp + string.join(pl, ':')
        return mp
    elif os.name == 'posix': # Expand Unix variables
        if path[0] == '~' :
            path = os.path.expanduser( path )
        if '$' in path:
            path = os.path.expandvars( path )
        return path
    else: # needs to take care of dos & nt someday
        return path

def compare_s2f(s, f2):
    """Helper to compare a string to a file, return 0 if they are equal."""

    BUFSIZE = 8192
    i = 0
    fp2 = open(f2)
    try:
        while 1:
            try:
                b1 = s[i: i + BUFSIZE]
                i = i + BUFSIZE
            except IndexError:
                b1 = ''
            b2 = fp2.read(BUFSIZE)
            if not b1 and not b2: return 0
            c = cmp(b1, b2)
            if c: return c
    finally:
        fp2.close()