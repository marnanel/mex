import string
import yex.exception
import yex.parse
import logging
import copy
from yex.value.value import Value

commands_logger = logging.getLogger('yex.commands')

class Tokenlist(Value):
    def __init__(self,
            t = None):

        super().__init__()

        if t is None:
            self.value = []
        elif isinstance(t, list):

            not_tokens = [x for x in t
                    if not isinstance(x, yex.parse.Token)]

            if not_tokens:
                raise yex.exception.YexError(
                        "Expected a list of Tokens, but it contained "
                        f"{not_tokens}"
                        )

            self.value = t
        elif isinstance(t,
                (Tokenlist, yex.parse.Tokenstream)):
            self.set_from_tokens(
                    self.prep_tokeniser(t),
                    )
        else:
            self.value = [
                    yex.parse.Token(c)
                    for c in str(t)
                    ]

        self._iterator = self._read()

    def set_from_tokens(self, tokens):

        t = tokens.next(deep=True)

        if t.category!=t.BEGINNING_GROUP:
            raise yex.exception.ParseError(
                    "expected a token list "
                    f"but found {t}"
                    )

        tokens.push(t)

        self.value = list(
                tokens.single_shot(
                    expand = False,
                    ))

        commands_logger.debug("%s: set value from tokens = %s",
                self,
                self.value)

    def __iter__(self):

        read = self._read

        class Tokenlist_iterator:
            def __init__(self):
                self.iterator = read()

            def __next__(self):
                return self.iterator.__next__()

        return Tokenlist_iterator()

    def __next__(self):
        return self._iterator.__next__()

    def _read(self):
        for token in self.value:
            commands_logger.debug("%s: yield member %s",
                    self, token)
            yield token
        commands_logger.debug("%s: all done",
                self)

    def __eq__(self, other):
        if isinstance(other,
                (Tokenlist, yex.parse.Tokenstream)):

            return self.value==other.value
        elif isinstance(other, list):

            return self.value == other

        elif isinstance(other, str):
            return self.value==[
                    yex.parse.Token(ch=c)
                    for c in other]
        else:
            raise TypeError(
                    f"{self} can't be compared "
                    f"with {other}, which is {other.__class__}"
                    )

    def __repr__(self):
        return f'[token list %x: %d: %s]' % (
                id(self)%0xFFFF,
                len(self.value),
                str(self),
                )

    def __str__(self):
        return ''.join([x.ch for x in self.value])

    def __len__(self):
        return len(self.value)

    def __bool__(self):
        return len(self.value)!=0

    def __getitem__(self, index):
        return self.value[index]

    def __setitem__(self, index, v):
        self.value[index] = v

    def __deepcopy__(self, memo):
        contents = [
                copy.deepcopy(v)
                for v in self.value
                ]
        result = Tokenlist(contents)
        return result