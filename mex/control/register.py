import logging
from mex.control.word import *
import mex.parse
import mex.exception

macros_logger = logging.getLogger('mex.macros')
commands_logger = logging.getLogger('mex.commands')

# TODO this is in need of some refactoring.

class C_Defined_by_chardef(C_Unexpandable):

    in_vertical = 'horizontal'

    def __init__(self, char, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.char = char

    def __call__(self, name, tokens):
        tokens.push(
                mex.parse.Token(
                    ch = self.char,
                ))

    def __repr__(self):
        return "[chardef: %d]" % (ord(self.char),)

    def __int__(self):
        return ord(self.char)

    @property
    def value(self):
        return self.char

class Chardef(C_Expandable):

    def __call__(self, name, tokens):

        newname = tokens.next(expand=False)

        if newname.category != newname.CONTROL:
            raise mex.exception.ParseError(
                    f"{name} must be followed by a control, not {token}")

        # XXX do we really want to allow them to redefine
        # XXX *any* control?

        tokens.eat_optional_equals()

        self.redefine_symbol(
                symbol = newname,
                tokens = tokens,
                )

    def redefine_symbol(self, symbol, tokens):

        char = chr(mex.value.Number(tokens).value)

        tokens.state[symbol.name] = C_Defined_by_chardef(
                char = char)

class Mathchardef(Chardef):

    def redefine_symbol(self, symbol, tokens):
        mathchar = chr(mex.value.Number(tokens).value)

        # TODO there's nothing useful to do with this
        # until we implement math mode!

class _Registerdef(C_Expandable):

    def __call__(self, name, tokens):

        newname = tokens.next(expand=False)

        if newname.category != newname.CONTROL:
            raise mex.exception.ParseError(
                    f"{name} must be followed by a control, not {newname}")

        tokens.eat_optional_equals()

        index = self.block + str(mex.value.Number(tokens).value)

        existing = tokens.state.get(
                field = index,
                )
        commands_logger.debug(r"%s sets \%s to %s",
                name,
                newname.name,
                existing)

        tokens.state[newname.name] = existing

class Countdef(_Registerdef):
    block = 'count'

class Dimendef(_Registerdef):
    block = 'dimen'

class Skipdef(_Registerdef):
    block = 'skip'

class Muskipdef(_Registerdef):
    block = 'muskip'

class Toksdef(_Registerdef):
    block = 'toks'

# there is no Boxdef-- see the TeXbook, p121
