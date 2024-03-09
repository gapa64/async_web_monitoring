""" ddp - data printer """

import sys
import re
from colored import fore, back, style


SCHEME_COLORS_DEFAULT = dict(
    bool = fore.LIGHT_BLUE,
    none = fore.LIGHT_BLUE,
    int = fore.LIGHT_YELLOW,
    float = fore.LIGHT_YELLOW,
    str = fore.LIGHT_GREEN,
    bytes = fore.LIGHT_MAGENTA,
    object = fore.LIGHT_RED,
    any = fore.LIGHT_GRAY,
    key = fore.LIGHT_CYAN,
    ref = fore.RED,
    punct = fore.WHITE,
)


class SchemeColors:
    ''' Схема цветов '''
    def __init__(self, **kw):
        x = dict(**SCHEME_COLORS_DEFAULT)
        for k in kw:
            x[k]    # тест на профпригодность
            x[k] = kw[k]
        for k in x:
            setattr(self, k, x[k])


SCHEME_PYTHON = dict(
    kword=False,
    oword=True,
    kw="=",
    kv=": ",
    object_open="%n(",
    object_close=")",
    dict_open="{",
    dict_close="}",
    list_open="[",
    list_close="]",
    tuple_open="(",
    tuple_close=")",
    str="'%s'",
    bytes="b'%s'",
    scalar="%n('%s')",
    none="None",
    true="True",
    false="False",
)

SCHEME_PERL = dict(
    kword=True,
    oword=True,
    kw=" => ",
    kv=" => ",
    object_open="bless {",
    object_close="}, %n",
    dict_open="{",
    dict_close="}",
    list_open="[",
    list_close="]",
    tuple_open="[",
    tuple_close="]",
    str='"%s"',
    bytes='do { use bytes; "%s" }',
    scalar='%n ("%s")',
    none="undef",
    true="1",
    false="0",
)

SCHEME_NODE = dict(
    kword=True,
    oword=True,
    kw=": ",
    kv=": ",
    object_open="new %n(",
    object_close=")",
    dict_open="{",
    dict_close="}",
    list_open="[",
    list_close="]",
    tuple_open="[",
    tuple_close="]",
    str='"%s"',
    bytes=lambda s: "".join(['Buffer.from([', ", ".join(["0x%X" % ch for ch in s]) ,'])']),
    scalar="new %n('%s')",
    none="null",
    true="true",
    false="false",
)

SCHEME_SEP = dict(
    python=SCHEME_PYTHON,
    perl=SCHEME_PERL,
    node=SCHEME_NODE,
)

class SchemeSeparators:
    ''' Схема разделителей '''
    def __init__(self, **kw):
        x = dict(**SCHEME_PYTHON)
        for k in kw:
            x[k]    # тест на профпригодность
            x[k] = kw[k]
        for k in x:
            setattr(self, k, x[k])

IS_WORD = re.compile(r'^[A-Z_a-z]\w*$')
def is_word(s):
    if not isinstance(s, str):
        return False
    return IS_WORD.search(s)


class DDP:
    def __init__(self, color, sep, filters):
        self.ref = {}   # memaddr => pathaddr
        self._idents = []
        self.s = []
        self.path = [] # pathaddr
        self.color = SchemeColors(**color) if isinstance(color, dict) else (color if isinstance(color, SchemeColors) else SchemeColors())
        self.is_color = bool(color)
        self.indexes = True
        self.sep = SchemeSeparators(**sep) if isinstance(sep, dict) else (sep if isinstance(sep, SchemeSeparators) else SchemeSeparators(**SCHEME_SEP[sep]))
        self.filters = filters
        
    
    def echo(self, x, c):
        if self.is_color:
            self.s.append(c)
        self.s.append(x)
        return self
    
        
    def ident(self, n):
        ''' Кеширует отступы '''
        i = self._idents
        
        if n == len(i):
            i.append(' ' * (n*2))
        return i[n]


    def el_dict(self, k, v):
        ''' Распечатывает элемент словаря {x: y} '''
        if self.sep.kword and is_word(k):
            self.echo(k, self.color.key)
        else:
            self.np(k)
        self.echo(self.sep.kv, self.color.punct)
        self.np(v)
        return self


    def el_object(self, k, v):
        ''' Распечатывает элемент объекта A(x=y) '''
        if self.sep.oword and is_word(k):
            self.echo(k, self.color.key)
        else:
            self.np(k)
        self.echo(self.sep.kw, self.color.punct)
        self.np(v)
        return self


    def el_list(self, k, v):
        ''' Распечатывает элемент объекта '''
        if self.indexes:
            self.echo('[%d] ' % k, self.color.punct)
        self.np(v)
        return self

    def struct(self, fill, iterator, sk1, sk2, elem_fn, before=None, before_color=None):
        ''' Структура '''
        space = self.ident(len(self.path))
        self.path.append(None)
        spaces = self.ident(len(self.path))
        self.echo(sk1, self.color.punct)
        if before is not None:
            self.echo(before, before_color)
        if fill:
            self.echo("\n", style.RESET)
            for e in iterator:
                self.echo(spaces, '')
                k, v = e
                self.path[-1] = str(k)
                elem_fn(k, v)
                self.echo(",\n", self.color.punct)
            self.echo(space, '')
        self.echo(sk2, self.color.punct)
        self.path.pop()
        return self


    def object_name(self, p):
        """ Возвращает класс объекта """
        return (p.__class__.__name__+
                (' '+p.__name__ if hasattr(p, '__name__') else '')+
                (' of '+p.__self__.__class__.__name__ if hasattr(p, '__self__') else ''))


    def echo_ref(self, p):
        """ Распечатывает ссылку """
        self.echo("<%s at %s>" % (type(p), '.'.join(self.ref[id(p)]) or '<root>'), self.color.ref)
        return self


    def np(self, p):
        """ Распечатывает данные в список """

        is_struct = isinstance(p, (dict, list, tuple)) or isinstance(p, object) and hasattr(p, '__dict__')

        if is_struct and id(p) in self.ref:
            self.echo_ref(p)
            return

        if type(p) in self.filters:
            fn = self.filters[type(p)]
            return fn(p, self)

        if is_struct:
            self.ref[id(p)] = self.path[:]
        
            if isinstance(p, object) and hasattr(p, '__dict__'):
                name = self.object_name(p)
                if self.is_color:
                    name = "%s%s%s" % (self.color.object, name, self.color.punct)
                sk1 = self.sep.object_open.replace("%n", name)
                sk2 = self.sep.object_close.replace("%n", name)

                before = None
                before_color = None
                for maybe_type in [int, bool, float, str, bytes, type(None)]:
                    if isinstance(p, maybe_type):
                        before = repr(p)
                        before_color = getattr(self.color, 'none' if maybe_type == type(None) else maybe_type.__name__)
                        break

                self.struct(
                    before=before,
                    before_color=before_color,
                    fill=bool(p.__dict__),
                    iterator=p.__dict__.items(),
                    sk1=sk1,
                    sk2=sk2,
                    elem_fn=self.el_object,
                )

            if isinstance(p, dict):
                self.struct(
                    fill=bool(p),
                    iterator=p.items(),
                    sk1=self.sep.dict_open,     # {
                    sk2=self.sep.dict_close,    # }
                    elem_fn=self.el_dict,
                )
            elif isinstance(p, list):
                self.struct(
                    fill=bool(p),
                    iterator=enumerate(p),
                    sk1=self.sep.list_open,     # [
                    sk2=self.sep.list_close,    # ]
                    elem_fn=self.el_list,
                )
            elif isinstance(p, tuple):
                self.struct(
                    fill=bool(p),
                    iterator=enumerate(p),
                    sk1=self.sep.tuple_open,     # (
                    sk2=self.sep.tuple_close,    # )
                    elem_fn=self.el_list,
                )
                
        elif isinstance(p, str):
            self.echo(self.sep.str.replace("%s", repr(p)[1:-1]), self.color.str)
        elif isinstance(p, bool):
            self.echo((self.sep.true if p else self.sep.false), self.color.bool)
        elif isinstance(p, int):
            self.echo(repr(p), self.color.int)
        elif isinstance(p, float):
            self.echo(repr(p), self.color.float)
        elif isinstance(p, bytes):
            s = self.sep.bytes(p) if callable(self.sep.bytes) else self.sep.bytes.replace("%s", repr(p)[2:-1])
            self.echo(s, self.color.bytes)
        elif p is None:
            self.echo(self.sep.none, self.color.none)
        else: # Например, datetime.datetime ⌘:
            name = self.object_name(p)
            if self.is_color:
                name = "%s%s%s" % (self.color.object, name, self.color.punct)
            x = self.sep.scalar.replace("%n", name).replace("%s", str(p))
            self.echo(x, self.color.any)
        return self



def np(p, color=False, indexes=True, sep="python", end='\n', filters={}):
    x = DDP(color, sep, filters)
    x.indexes = indexes
    x.np(p)
    x.echo(end, style.RESET)
    return "".join(x.s)



class DDPFile(DDP):
    def __init__(self, file, color, sep, filters):
        super().__init__(color, sep, filters)
        self.file=file


    def echo(self, x, c):
        if self.is_color:
            self.file.write(c)
        self.file.write(x)
        return self



def p(data, file=sys.stdout, color=True, indexes=True, sep="python", end='\n', filters={}):
    x = DDPFile(file, color, sep, filters)
    x.indexes = indexes
    x.np(data)
    x.echo(end, style.RESET)
