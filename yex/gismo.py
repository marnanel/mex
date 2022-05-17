import yex.value
import logging

logger = logging.getLogger('yex.general')

class Gismo:

    shifted_by = yex.value.Dimen()

    def __init__(self, height=None, depth=None, width=None):
        not_a_tokenstream(height)

        self.height = require_dimen(height)
        self.depth = require_dimen(depth)
        self.width = require_dimen(width)
        self.contents = []

    def showbox(self):
        r"""
        Returns a list of strings which should be displayed by \showbox
        for this gismo.
        """
        return ['\\'+self.__class__.__name__.lower()]

    def is_void(self):
        return False

    def __repr__(self):
        return '['+self.__class__.__name__.lower()+']'

class DiscretionaryBreak(Gismo):

    discardable = False

    def __init__(self,
            prebreak,
            postbreak,
            nobreak,
            ):
        super().__init__()
        self.prebreak = prebreak
        self.postbreak = postbreak
        self.nobreak = nobreak

    def __repr__(self):
        return (
                f'[discretionary break: pre={self.prebreak} '
                f'post={self.postbreak} / no={self.nobreak}]'
                )

class Whatsit(Gismo):

    discardable = False
    height = depth = width = 0

    def __init__(self,
            on_box_render,
            ):
        self.on_box_render = on_box_render

    def __call__(self):
        logger.debug("%s: we're being rendered, so run %s",
                self, self.on_box_render)
        self.on_box_render()
        logger.debug("%s: call to %s finished",
                self, self.on_box_render)

class VerticalMaterial(Gismo):

    discardable = False

    def __repr__(self):
        return f'[Vertical material]'

class C_Box(Gismo):
    """
    Superclass of all Boxes.
    """
    discardable = False

class Leader(Gismo):
    """
    Leaders, although at present this only wraps Glue.
    """

    discardable = True

    def __init__(self,
            *args,
            glue=None,
            vertical=False,
            **kwargs,
            ):
        """
        Constructor.

        Args:
            glue (`Glue`): glue for the new Leader to wrap.
               If this is None, we construct a new Glue using **kwargs
               and wrap that, instead.

            vertical (`bool`): True if this Leader is vertical,
                False if it's horizontal.
        """

        if glue is not None:
            self.glue = glue
        else:
            self.glue = yex.value.Glue(**kwargs)

        self.vertical = vertical

        for name in [
                'space', 'stretch', 'shrink',
                ]:
            setattr(self, name, getattr(self.glue, name))

    @property
    def contents(self):
        return []

    @property
    def width(self):
        if self.vertical:
            return yex.value.Dimen(0)
        else:
            return self.glue.length

    @property
    def height(self):
        if self.vertical:
            return self.glue.length
        else:
            return yex.value.Dimen(0)

    @property
    def depth(self):
        return yex.value.Dimen(0)

    def __repr__(self):
        return repr(self.glue)

class Kern(Gismo):

    discardable = True

    def __init__(self, width):
        super().__init__(
                width = width,
                )

    def __repr__(self):
        return f'[kern: {self.width}]'

    def showbox(self):
        return [r'\kern %.5g' % (
            float(self.width),)]

class Penalty(Gismo):

    discardable = True

    def __init__(self, demerits):
        super().__init__()
        self.demerits = demerits

    def __repr__(self):
        return f'[penalty: {self.demerits}]'

class MathSwitch(Gismo):

    discardable = True

    def __init__(self, which):
        super().__init__()
        self.which = which

    def __repr__(self):
        if self.which:
            return '[math on]'
        else:
            return '[math off]'

def require_dimen(d):
    """
    Casts d to a Dimen and returns it.

    People send us all sorts of weird numeric types, and
    we need to make sure they're Dimens before we start
    doing any maths with them.
    """
    if isinstance(d, yex.value.Dimen):
        return d
    elif d is None:
        return yex.value.Dimen()
    elif str(d)=='inherit':
        return str(d)
    elif isinstance(d, (int, float)):
        return yex.value.Dimen(d, 'pt')
    else:
        return yex.value.Dimen(d)

def not_a_tokenstream(nat):
    r"""
    If nat is a Tokenstream, does nothing.
    Otherwise, raises YexError.

    Many classes can be initialised with a Tokenstream as
    their first argument. This doesn't work for boxes:
    they must be constructed using a control.
    For example,

        2pt

    is a valid Dimen, but

        {hello}

    is not a valid Box; you must write something like

        \hbox{hello}

    to construct one. So we have this helper function
    which checks the first argument of box constructors,
    in case anyone tries it (which they sometimes do).
    """
    if isinstance(nat, yex.parse.Tokenstream):
        raise yex.exception.YexError(
                "internal error: boxes can't be constructed "
                "from Tokenstreams"
                )
