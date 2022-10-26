"""
Miscellaneous controls.

These should find a home somewhere else. But for now, they live here.
"""
import logging
from yex.control.control import *
from yex.decorator import control
import yex

logger = logging.getLogger('yex.general')

class The(C_Unexpandable):
    r"""
    Takes an argument, one of many kinds (see the TeXbook p212ff)
    and returns a representation of that argument.

    For example, \the\count100 returns a series of character
    tokens representing the contents of count100.
    """

    def __call__(self, tokens):
        subject = tokens.next(
                level='reading',
                on_eof='raise',
                )

        if isinstance(subject, yex.parse.Token):
            handler = tokens.doc.get(subject.identifier,
                    default=None,
                    tokens=tokens)

            if handler is None:
                raise yex.exception.TheUnknownError(
                        subject = subject,
                        )
        else:
            handler = subject

        try:
            method = handler.get_the
        except AttributeError:
            raise yex.exception.TheNotFoundError(
                    subject = subject,
                    )

        representation = method(tokens)
        logger.debug(r'\the for %s is %s',
                subject, representation)

        tokens.push(representation,
                clean_char_tokens=True,
                is_result=True,
                )

class Show(C_Unexpandable): pass
class Showthe(C_Unexpandable): pass

class Let(C_Unexpandable):
    """
    TODO
    """ # TODO


    def __call__(self, tokens):

        lhs = self.get_lhs(tokens)
        rhs = self.get_rhs(tokens)

        logger.debug("%s: will set %s=%s",
                self, lhs, rhs)

        self.redefine(tokens, lhs, rhs)

    def get_lhs(self, tokens):

        result = tokens.next(
                level='deep',
                on_eof='raise',
                )

        if not isinstance(result, (yex.parse.Control, yex.parse.Active)):
            raise yex.exception.LetInvalidLhsError(
                    name = self.__class__.__name__,
                    subject = result,
                    )

        tokens.eat_optional_char('=')

        return result

    def get_rhs(self, tokens):

        result = tokens.next(
                level='deep',
                on_eof='raise',
                )

        return result

    def redefine(self, tokens, lhs, rhs):
        if isinstance(rhs, yex.parse.Control):
            self.redefine_to_control(lhs, rhs, tokens)
        else:
            self.redefine_to_ordinary_token(lhs, rhs, tokens)

    def redefine_to_control(self, lhs, rhs, tokens):

        rhs_referent = tokens.doc.get(rhs.identifier,
                        default=None,
                        tokens=tokens)

        logger.debug(r"%s: %s = %s, which is %s",
                self, lhs, rhs, rhs_referent)

        tokens.doc[lhs.identifier] = rhs_referent

    def redefine_to_ordinary_token(self, lhs, rhs, tokens):

        class Redefined_by_let(C_Expandable):

            def __call__(self, tokens):
                tokens.push(rhs, is_result=True)

            def __repr__(self):
                return f"[{rhs}]"

            @property
            def value(self):
                return rhs

        logger.debug(r"%s: %s = %s",
                self, lhs, rhs)

        tokens.doc[lhs.identifier] = Redefined_by_let()

class Futurelet(Let):

    def __call__(self, tokens):

        lhs = self.get_lhs(tokens)
        rhs1 = self.get_rhs(tokens)
        rhs2 = self.get_rhs(tokens)

        logger.debug("%s: will set %s=%s, "
                "then run %s, but push %s immediately before its result.",
                self, lhs, rhs2, rhs1, rhs2)

        self.redefine(tokens, lhs, rhs2)

        tokens.push(rhs1)

        inside = tokens.another(
                on_push = yex.parse.Afterwards(
                    item = rhs2,
                    ),
                level = 'executing',
                )

        first = inside.next()
        tokens.push(first)

##############################

class Meaning(C_Unexpandable): pass

##############################

@yex.decorator.control()
def Relax():
    """
    Does nothing.

    See the TeXbook, p275.
    """
    def __call__(self, tokens):
        pass

##############################

class Indent(C_Unexpandable):

    vertical = True
    horizontal = True
    math = True

    def __call__(self, tokens):

        if tokens.doc.mode.is_vertical:
            self._in_vertical_mode(tokens)
        else:
            self._in_horizontal_and_math_modes(tokens)

    def _in_vertical_mode(self, tokens):

        doc = tokens.doc
        mode = doc['_mode']

        # see the TeXbook, p278
        if not mode.list:
            logger.debug("indent: not adding parskip glue because "
                    "list is empty")
        elif isinstance(mode, yex.mode.Internal_Vertical):
            logger.debug("indent: not adding parskip glue because "
                    "this is internal vertical mode")
        else:
            mode.append(
                    yex.box.Leader(
                        glue=tokens.doc[r'\parskip']
                        ))
            logger.debug("indent: added parskip glue: %s",
                    tokens.doc[r'\parskip'])

        logger.debug("indent: switching to horizontal mode")

        doc.begin_group(flavour='only-mode',
                ephemeral = True)

        doc['_mode'] = 'horizontal'

        for item in reversed(doc[r'\everypar']):
            tokens.push(item)

        self._maybe_add_indent(doc)

        doc.mode.exercise_page_builder()

    def _in_horizontal_and_math_modes(self, tokens):
        # see the TeXbook, p282
        doc = tokens.doc

        self._maybe_add_indent(doc)
        doc[r'\spacefactor'] = 1000

        # TODO: math mode is slightly more complicated than this

    def _maybe_add_indent(self, doc):
        logger.debug("indent: adding indent of width %s",
                doc[r'\parindent'])
        doc.mode.append(
                yex.box.Box(width=doc[r'\parindent'])
                )

class Noindent(Indent):

    def _maybe_add_indent(self, doc):
        pass # no, not here

##############################

class C_Begin_or_end_group(C_Expandable):
    pass

class Begingroup(C_Begin_or_end_group): pass
class Endgroup(C_Begin_or_end_group): pass

##############################

@yex.decorator.control(
        expandable = True,
        push_result = False,
        )
def Noexpand(tokens):
    """
    The argument is not expanded.
    """

    t = tokens.next(level='deep')
    logger.debug(r'\noexpand: not expanding %s', t)
    return t

@yex.decorator.control(
        expandable = True,
        even_if_not_expanding = True,
        )
def Expandafter(tokens):
    r"""
    Process the argument, then give the result to the previous control.

    For example, in

        \def\spong{spong}
        \uppercase{\spong}

    firstly \uppercase runs on "\spong", which gives "\spong" (since it's a
    control, not a series of letters). Then \spong is run, so we end up
    with "spong".

    But in

        \def\spong{spong}
        \uppercase\expandafter{\spong}

    \expandafter runs "\spong" and gets "spong", then passes it to
    \uppercase. So we end up with "SPONG".
    """

    # We need to know what the token is immediately after \expandafter,
    # so that we can reproduce it. We can't just instantiate a new
    # BeginningGroup token, because we'd need to know what character
    # it represented. That's usually "{", but it need not be.
    #
    # We use this token to persuade the Expander of the previous symbol
    # to re-parse our argument as a single.

    opening = tokens.next(
            level = 'deep',
            on_eof = 'raise',
            )

    tokens.doc.pushback.adjust_group_depth(
        c = opening,
        why = "(don't count it twice)",
        reverse = True,
        )

    # Right, let's read our argument.

    argument = [token for token in tokens.another(
        level = 'executing',
        bounded ='single',
        on_eof = 'exhaust',
        )]

    logger.debug(r'\expandafter: begin re-processing: %s',
            argument)

    class Expandafter_Teardown(yex.parse.Internal):
        def __call__(self, *args, **kwargs):
            logger.debug(r'\expandafter: done re-processing: %s',
                    argument)

    # We need to push an actual BeginningGroup, so that any
    # Expander(bounded='single') which might have preceded this \expandafter
    # knows that we're dealing with a bounded series of tokens.
    #
    # We give the BeginningGroup, and its corresponding EndGroup, a ch of ''
    # because they don't represent real symbols in the original source,
    # and besides we don't know what characters (if any) might represent
    # BeginningGroup or EndGroup at present.

    tokens.push(Expandafter_Teardown())
    tokens.push(yex.parse.EndGroup(ch=''))
    tokens.push(argument)
    tokens.push(yex.parse.BeginningGroup(ch=''))
    tokens.push(opening)

    tokens.doc.pushback.group_depth += 1

##############################

@yex.decorator.control()
def Showlists(doc):
    doc.showlists()

##############################

@yex.decorator.control(even_if_not_expanding=True)
def String(tokens):

    result = []

    location = tokens.location

    def add(ch, with_escapechar=False):
        if with_escapechar:
            escapechar = tokens.doc[r'\escapechar']
            if escapechar>=0 and escapechar<=255:
                add(chr(escapechar))

        for c in ch:
            result.append(
                    yex.parse.get_token(
                        ch = c,
                        category = None, # i.e. Other or Space
                        location = location,
                        )
                    )

    t = tokens.next(level='deep')

    logger.debug(
            r'\string: token was %s of class %s',
            t, t.__class__.__name__)

    if isinstance(t, yex.parse.Control):
        add(t.name, with_escapechar=True)
    elif hasattr(t, 'identifier'):
        add(t.identifier[1:], with_escapechar=True)
    elif hasattr(t, 'ch'):
        add(t.ch)
    else:
        add(str(t))

    return result

##############################

def _uppercase_or_lowercase(tokens, prefix):

    result = []

    for token in tokens.another(
            bounded='single',
            on_eof='exhaust',
            level='reading'):

        replacement_code = None

        if not isinstance(token, yex.parse.Token):
            logger.debug("  -- %s is not a token but a %s",
                    token, type(token))

        elif isinstance(token, yex.parse.Control):
            logger.debug("  -- %s is a control token",
                    token)

        elif isinstance(token, (
            yex.parse.Letter,
            yex.parse.Other,
            )):

            replacement_code = tokens.doc[r'\%s%d' % (
                prefix,
                ord(token.ch))].value

        if replacement_code:
            replacement = yex.parse.get_token(
                    ch = chr(int(replacement_code)),
                    category = token.category,
                    )
        else:
            replacement = token

        logger.debug("  -- s: %s -> %s",
                token, replacement)
        result.append(replacement)

    return result

@yex.decorator.control()
def Uppercase(tokens):
    return _uppercase_or_lowercase(tokens=tokens, prefix='uccode')

@yex.decorator.control()
def Lowercase(tokens):
    return _uppercase_or_lowercase(tokens=tokens, prefix='lccode')

##############################

@yex.decorator.control()
def Csname(tokens):
    r"""
    Creates new control tokens.

    \csname must be followed by a series of tokens of any of the basic
    categories. Expandable controls will be expanded; unexpandable controls
    aren't allowed. The series must end with \endcsname.

    This series will become the name of a new control token, which will
    initially point at \relax. See p40 of the TeXbook for more details.

    You can use this to create control tokens with weird names-- even
    the empty string. Note that if you create a token with a name
    beginning with an underscore, that underscore will
    be doubled in doc[name] so that it doesn't conflict with yex's internal
    settings.
    """

    logger.debug(r'\csname: reading name of new control')

    location = tokens.location

    name = ''
    try:
        while True:
            item = tokens.next(level='executing', on_eof='raise')

            if isinstance(item, yex.parse.Token) and item.is_from_tex:
                name += item.ch
            else:
                raise yex.exception.YexError(
                        r'\csname can only be followed by standard characters, '
                        fr'and not {item}, which is a {item.__class__}'
                    )
    except yex.exception.EndcsnameError:
        pass

    if name.startswith('_'):
        name = f'_{name}'

    logger.debug(r'\csname: new control will be called %s', name)

    result = yex.parse.Control(
            name = name,
            doc = tokens.doc,
            location = location,
            )

    logger.debug(r'\csname: new control is %s', result)

    if name not in tokens.doc.controls:
        tokens.doc.controls[name] = Relax()
        logger.debug(r'\csname: added to controls table')

    return result

@yex.decorator.control()
def Endcsname():
    r"""
    Ends a \csname sequence.

    This is special-cased by \csname, and in any other context it
    raises an exception.
    """
    raise yex.exception.EndcsnameError()

##############################

class Parshape(C_Expandable):

    def __call__(self, tokens):

        count = yex.value.Number.from_tokens(tokens).value

        if count==0:
            tokens.doc.parshape = None
            return
        elif count<0:
            raise yex.exception.YexError(
                    rf"\parshape count must be >=0, not {count}"
                    )

        tokens.doc.parshape = []

        for i in range(count):
            length = yex.value.Dimen.from_tokens(tokens)
            indent = yex.value.Dimen.from_tokens(tokens)
            tokens.doc.parshape.append(
                    (length, indent),
                    )
            logger.debug("%s: %s/%s = (%s,%s)",
                    self, i+1, count, length, indent)

    def get_the(self, tokens):
        if tokens.doc.parshape is None:
            result = 0
        else:
            result = len(tokens.doc.parshape)

        return str(result)

##############################

@yex.decorator.control(
    vertical = False,
    horizontal = True,
    math = False,
    )
def S_0020(): # Space
    """
    Add an unbreakable space.
    """
    return yex.parse.token.Other(ch=chr(32))

@yex.decorator.control(
    vertical = False,
    horizontal = None,
    math = False,
    )
def Par():
    """
    Add a paragraph break.
    """
    return yex.parse.token.Paragraph()

##############################

class Noboundary(C_Unexpandable):
    vertical = False
    horizontal = True
    math = False

class Unhbox(C_Unexpandable):
    vertical = False
    horizontal = True
    math = True

class Unhcopy(C_Unexpandable):
    vertical = False
    horizontal = True
    math = True

class Valign(C_Unexpandable):
    vertical = False
    horizontal = True
    math = False

class Accent(C_Unexpandable):
    vertical = False
    horizontal = True
    math = False

@yex.decorator.control(
    vertical = False,
    horizontal = True,
    math = False,
    )
def Discretionary(tokens):
    "Adds a discretionary break."

    symbols = {}

    for name in ['prebreak', 'postbreak', 'nobreak']:
        symbols[name] = list(tokens.another(
            level='reading',
            on_eof='exhaust',
            bounded='balanced',
            ))

    return yex.box.DiscretionaryBreak(**symbols)

class S_002d(C_Unexpandable): # Hyphen
    vertical = False
    horizontal = True
    math = True

class Afterassignment(C_Unexpandable): pass
class Aftergroup(C_Unexpandable): pass

@yex.decorator.control()
def Penalty(tokens):
    demerits = yex.value.Number.from_tokens(
            tokens.not_expanding()).value

    penalty = yex.box.Penalty(
            demerits = demerits,
            )

    return penalty

class Insert(C_Unexpandable): pass
class Vadjust(C_Unexpandable): pass

@yex.decorator.control()
def Char(tokens):
    codepoint = yex.value.Number.from_tokens(
            tokens.not_expanding()).value

    if codepoint in range(32, 127):
        logger.debug(r"\char produces ascii %s (%s)",
            codepoint, chr(codepoint))
    else:
        logger.debug(r"\char produces ascii %s",
            codepoint)

    return chr(codepoint)

class Unvbox(C_Unexpandable):
    horizontal = 'vertical'
    vertical = True

class Unvcopy(C_Unexpandable):
    horizontal = 'vertical'
    vertical = True

class Halign(C_Unexpandable):
    horizontal = 'vertical'
    vertical = True

class Noalign(C_Unexpandable):
    pass

class End(C_Unexpandable):
    horizontal = 'vertical'
    vertical = True

@yex.decorator.control(
    horizontal = True,
    vertical = True,
    math = True,
)
def Shipout(tokens):
    r"""
    Sends a box to the output.
    """

    found = tokens.next(level='querying')
    try:
        boxes = found.value
    except AttributeError:
        boxes = [found]

    for box in boxes:
        logger.debug(r'\shipout: shipping %s',
                box)

        if not isinstance(box, yex.box.Gismo):
            raise yex.exception.YexError(
                    f"needed a box or similar here (and not {box}, "
                    f"which is a {box.__class__.__name__})"
                    )

        tokens.doc.shipout(box)

class Ignorespaces(C_Unexpandable): pass

##############################

class Special(C_Unexpandable):
    r"""
    An instruction to the output driver.

    This creates a yex.box.Whatsit which stores the instruction until
    it's shipped out. Bear in mind that it may never be shipped out.

    The argument is expanded when it's read. It consists of a keyword,
    followed optionally by a space and arguments to the keyword.
    The keyword isn't examined until the instruction is run.

    For the syntax of \special, see p276 of the TeXbook. For the syntax
    of its argument, see p225.
    """

    def __call__(self, tokens):

        inside = tokens.another(
                level='executing',
                bounded='single',
                on_eof="exhaust",
                )

        name = self._get_name(inside)
        args = self._get_args(inside)

        def return_special():
            return (name, args)

        result = yex.box.Whatsit(
                on_box_render = return_special,
                )

        logger.debug(r"special: created %s",
                result)

        tokens.push(result)

    def _get_name(self, tokens):
        result = ''

        for t in tokens:
            if isinstance(t, yex.parse.Space):
                break

            result += t.ch

        logger.debug(r"\special: name is %s", result)
        return result

    def _get_args(self, tokens):
        result = []

        for t in tokens:
            result.append(t)

        logger.debug(r"\special: args are %s", result)
        return result
