#
# Funcparserlib -- A parser library based on parser combinators
# by Andrey Vlasovskikh et al
#

__all__ = ['Slurp','Tokenizer','Spec','Token','LexerError','LineNumber']
import re,io,os,os.path

# ----------------

class NotStream(Exception):
    pass

class Slurp:
    """
    A file/string/bytes slurping class for use by the lexer.
    """
    chunk=4096
    def __init__(self,source,binary=False):
        self._pos=0
        self.pos=0
        self.buffer='' if not binary else b''
        self.binary=binary
        if isinstance(source,str):
            if binary==False:
                self.buffer=source
            else:
                self.buffer=source.encode()
        elif isinstance(source,bytes):
            if binary==True:
                self.buffer=source
            else:
                self.buffer=source.decode('utf8')
        elif isinstance(source,io.IOBase):
            self.stream=source
    def _append(self,chunk):
        if not any(map(lambda x: issubclass(chunk.__class__,x),[str,bytes])):
            raise Exception('Unknown chunk {}'.format(chunk))
        if self.binary:
            if isinstance(chunk,bytes):
                app=chunk
            else:
                app=chunk.encode()
        else:
            if isinstance(chunk,str):
                app=chunk
            else:
                app=chunk.decode('utf8')
        self.buffer=self.buffer[self._pos:]+app
        self._pos=0
    def _buffer(self):
        if hasattr(self,'stream') and isinstance(self.stream,io.IOBase):
            tmp=self.stream.read(self.chunk)
            if len(tmp)==0:
                raise EOFError('stream exhausted')
            self._append(tmp)
        else:
            raise NotStream('Not a buffered Slurp')
    def next(self,n=None):
        if not n:
            n=self.chunk
        def _inc(x):
            ret=(self.buffer[self._pos:self._pos+x],self.pos)
            self.pos+=x
            self._pos+=x
            return ret
        if self._pos+n < len(self.buffer):
            return _inc(n)
        else:
            try:
                while self._pos+n > len(self.buffer):
                    self._buffer()
                return _inc(n)
            except EOFError:
                next_chunk=len(self.buffer)-self._pos
                if next_chunk > 0:
                    return _inc(next_chunk)
                else:
                    raise
            except NotStream:
                next_chunk=len(self.buffer)-self._pos
                if next_chunk > 0:
                    return _inc(next_chunk)
                else:
                    raise EOFError('The Slurp was exhausted')
    def __next__(self):
        return self.next(1)
    @property
    def filename(self):
        if hasattr(self,'stream'):
            return os.path.normpath(os.path.join(os.getcwd(),self.stream.name))
        else:
            return ''

# ----------------

class LineNumber:
    """
    A line number tracker for the lexer
    """
    sep=re.compile(r'\r?\n')
    sepb=re.compile(b'\r?\n')
    def __init__(self):
        self.lines=[]
        self.pos=0
    def track(self,string):
        start=self.pos
        if isinstance(string,str):
            seps=self.sep.finditer(string)
        elif isinstance(string,bytes):
            seps=self.sepb.finditer(string)
        else:
            raise Exception('only string/bytes supported {}'.format(string))
        ret=[]
        for x in seps:
            e=x.end()
            self.lines.append(self.pos+e)
            ret.append(e)
        self.pos+=len(string)
        return (len(self.lines),start,ret)
    def find_last(self,pos):
        ln=len(self.lines)
        if pos<0:
            raise Exception('invalid pos {}'.format(pos))
        elif pos >= self.pos:
            return (ln,None)
        c=ln
        val=lambda x: 0 if x==0 else self.lines[x-1]
        while c>=0:
            if pos >= val(c):
                return (c,self.lines[c] if c < ln else None)
            c-=1
        return (0,None)
    def find(self,pos):
        if pos<0:
            raise Exception('invalid pos {}'.format(pos))
        elif pos>self.lines[-1]:
            return (len(self.lines),None)
        lo,hi=0,len(self.lines)
        val=lambda x: self.lines[x]
        mid=lambda lo,hi: lo+(hi-lo)//2
        cm=mid(lo,hi)
        while lo<hi:
            if pos >= val(cm):
                lo=cm+1
            else:
                hi=cm
            cm=mid(lo,hi)
        alt=True if lo>=len(self.lines) else False
        return (lo,val(lo) if not alt else None)

# ----------------

class Token:
    __slots__ = ['type', 'value', 'pos','case','start','lineno']
    def __init__(self,type,value,start=None,case=True,lineno=None):
        self.type=type
        self.value=value
        self.case=case
        self.start=start
        self.lineno=lineno
    def val(self):
        if self.case or not isinstance(self.value,str):
            return self.value
        else:
            return self.value.lower()
    def __eq__(self, other):
        if not isinstance(other, Token):
            return False
        pre=self.type==other.type
        none=self.value is None or other.value is None
        eq=self.val()==obj.val()
        return pre and (none or eq)
    def __hash__(self):
        return hash(self.type) ^ hash(self.value) ^ hash(self.start)
    def __repr__(self):
        return 'Token(%r,%r)' % (self.type, self.value)
    def ebnf(self):
        return ("'%s'" % (self.value,)
                if self.value is not None
                else '? %s ?' % (self.type,))
    @property
    def name(self):
        return self.value
    @property
    def end(self):
        return self.start+len(self.value)
    @property
    def linespan(self):
        s=self.lineno.find(self.start)
        if self.end < s[1]:
            e=(self.end,s[1])
        else:
            e=self.lineno.find(self.end-1)
        return ((s[0],self.start-s[1]),
                (e[0],self.end-e[1]+1))

# ----------------

class Spec(object):
    def __init__(self,type,regexp,flags=0,case=True,multiline=False):
        self.type=type
        self._regexp=regexp
        self._flags=flags
        self.case=case
        if not case:
            self._flags|=re.I
        if multiline:
            self._flags|=re.MULTILINE
    @property
    def re(self):
        if hasattr(self,'_re'):
            return self._re
        else:
            self._re=re.compile(self._regexp,self._flags)
            return self._re
    def __repr__(self):
        return 'Spec(%r, %r, %r)' % (self.type, self._regexp, self._flags)

# ----------------

class LexerError(Exception):
    def __init__(self, msg, filename, line, column):
        self.msg=msg
        self.filename=filename
        self.line=line
        self.column=column
    def __repr__(self):
        return '#<LexerError {}:{}:{} ({})>'.format(
            self.filename,
            self.line,
            self.column,
            self.msg)
    def __str__(self):
        return self.msg

# ----------------

class Tokenizer:
    def __init__(self,specs,binary=False):
        self.specs=specs
        self.binary=binary
    def run(self,slurp,chunk=4096):
        ln=LineNumber()
        gpos=0
        pos=0
        buf=b'' if self.binary else ''
        def _buffer(buf,pos):
            tmp,_=slurp.next(chunk)
            ln.track(tmp)
            buf=buf[pos:]+tmp
            pos=0
            return (buf,0)
        cont,rem,buffer_flag=True,True,False
        while cont or rem:
            cont=False
            if rem and (buffer_flag or len(buf)-pos < chunk//2):
                buffer_flag=False
                try:
                    buf,pos=_buffer(buf,pos)
                except EOFError:
                    rem=False
            if len(buf)-pos <= 0:
                continue
            longest_match=None
            for spec in self.specs:
                m=spec.re.match(buf,pos)
                if m:
                    value=m.group()
                    cont=True
                    if rem and m.end() == len(buf):
                        # if we matched to the end, buffer
                        buffer_flag=True
                        break
                    if not longest_match or longest_match[0] < m.end():
                        longest_match=(
                            m.end(),
                            spec.type,
                            value,
                            m.start(),
                            spec.case,
                            )
            else:
                if longest_match:
                    end,spec_type,value,start,case=longest_match
                    gpos+=end-pos
                    pos=end
                    yield Token(spec_type,value,start,case,ln)
                elif rem:
                    buffer_flag=True
                else:
                    line,linestart=ln.find_last(gpos)
                    raise LexerError('No regex match in lexer @<{}>'.format(buf[pos:min(pos+10,len(buf))]),
                                     slurp.filename,
                                     line,
                                     gpos-linestart if linestart else None)
        
# ----------------

# This is an example of a token spec. See also [this article][1] for a
# discussion of searching for multiline comments using regexps (including `*?`).
#
#   [1]: http://ostermiller.org/findcomment.html
_example_token_specs = [
    Spec('comment', r'\(\*(.|[\r\n])*?\*\)',multiline=True),
    Spec('comment', r'\{(.|[\r\n])*?\}',multiline=True),
    Spec('comment', r'//.*'),
    Spec('nl',      r'[\r\n]+'),
    Spec('space',   r'[ \t\r\n]+'),
    Spec('name',    r'[A-Za-z_][A-Za-z_0-9]*'),
    Spec('real',    r'[0-9]+\.[0-9]*([Ee][+\-]?[0-9]+)*'),
    Spec('int',     r'[0-9]+'),
    Spec('int',     r'\$[0-9A-Fa-f]+'),
    Spec('op',      r'(\.\.)|(<>)|(<=)|(>=)|(:=)|[;,=\(\):\[\]\.+\-<>\*/@\^]'),
    Spec('string',  r"'([^']|(''))*'"),
    Spec('char',    r'#[0-9]+'),
    Spec('char',    r'#\$[0-9A-Fa-f]+'),
]
#tokenize=Tokenizer(_example_token_specs)

