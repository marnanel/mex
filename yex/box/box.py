import yex.value
from yex.box.gismo import *
import yex.parse
import logging
import wrapt
import yex

logger = logging.getLogger('yex.general')

class Box(C_Box):

    """
    A Box is a rectangle on the page. It's not necessarily visible.

    All Boxes have a width, a height, and a depth.
    Their x-dimension is their width.
    Their y-dimension is their height plus their depth.
    Any of these may be negative.

    They are measured from a point on the page called their
    "reference point", which is not stored in the Box instance
    itself. From this point, height is measured upwards,
    depth downwards, and width to the right.
    """

    def __init__(self, height=None, width=None, depth=None,
            contents=None,
            ):

        not_a_tokenstream(height)

        self.height = require_dimen(height)
        self.width = require_dimen(width)
        self.depth = require_dimen(depth)

        if contents is None:
            self._contents = []
        else:
            self._contents = contents

        # in the general case, these are two names for the same thing
        self.contents = self._contents

    def set_from_tokens(self, index, tokens):
        index = self._check_index(index)

        tokens.eat_optional_equals()

        for e in tokens.single_shot():
            box = e

        if isinstance(box, yex.box.Box):
            self.__setitem__(index, box)
        else:
            raise yex.exception.ParseError(
                    "not a box: {box}",
                    )

    def __eq__(self, other):
        return self._compare(other, depth = 0)

    def _compare(self, other, depth=0):
        debug_indent = '  '*depth
        logger.debug("%sComparing %s and %s...",
                debug_indent,
                self, other)

        if not isinstance(other, self.__class__):
            logger.debug("%s  -- types differ, %s %s so False",
                    debug_indent, other.__class__, self.__class__)
            return False

        if len(self)!=len(other):
            logger.debug("%s  -- lengths differ, so False",
                    debug_indent)
            return False

        # we compare their contents, not their _contents, so that
        # we don't compare line breaks

        for ours, theirs in zip(self._contents, other.contents):
            logger.debug("%s  -- comparing %s and %s",
                    debug_indent,
                    ours, theirs)
            if not ours._compare(theirs,
                    depth = depth+1,
                    ):
                logger.debug("%s  -- they differ, so False",
                    debug_indent,
                    )
                return False

        logger.debug("%s  -- all good, so True!",
                    debug_indent,
                    )
        return True

    def __repr__(self):
        result = r'[\%s:%04x]' % (
                self.__class__.__name__.lower(),
                id(self) % 0xffff,
                )
        return result

    def _repr(self):
        result = ''
        for i in self._contents:
            result += ':' + repr(i)

        return result

    def __len__(self):
        # length does not include line breaks
        return len(self.contents)

    def showbox(self):
        r"""
        Returns a list of lines to be displayed by \showbox.

        We keep this separate from the repr() routine on purpose.
        The formatting and the information to display are
        too different to merge them.
        """
        result = [self._showbox_one_line()]

        for c in self.contents:
            result.extend(['.'+x for x in c.showbox()])

        return result

    def _showbox_one_line(self):
        return '\\'+self.__class__.__name__.lower()

    def is_void(self):
        return self._contents==[]

    def __getitem__(self, n):
        if isinstance(n, slice):
            result = _SlicedBox(
                    wrapped=self,
                    the_slice=n,
                    )
        elif isinstance(n, int):
            result = self._contents[n]
        else:
            raise TypeError(n)

        return result

class _SlicedBox(wrapt.ObjectProxy):
    """
    A slice of a box.

    This is a proxy object.
    """

    badness = 0 # don't use the "badness" attribute of the wrapper

    def __init__(self, wrapped, the_slice):
        super(_SlicedBox, self).__init__(wrapped)
        self._self_slice = the_slice
        self.badness = 0

    @property
    def contents(self):
        result = self.__wrapped__.contents[self._self_slice]
        return result

    def fit_to(self, size,
            badness_param = None,
            ):
        logger.debug("%s: fit_to() is using the slice",
                self)

        self.badness = self._inner_fit_to(
                size = size,
                contents = self.contents,
                badness_param = badness_param,
                )

    def __repr__(self):
        return repr(self.__wrapped__)[:-1]+f';{self._self_slice}]'

    def __str__(self):
        return str(self.__wrapped__)[:-1]+f';{self._self_slice}]'

class Rule(Box):
    """
    A Rule is a box which appears black on the page.
    """
    def __str__(self):
        return fr'[\rule; {self.width}x({self.height}+{self.depth})]'

class HVBox(Box):
    """
    A HVBox is a Box which contains some number of Gismos, in some order.

    This is an abstract class; its descendants HBox and VBox are
    the ones you want to actually use.
    """

    def __init__(self, contents=None,
            to=None, spread=None,
            ):
        # Not calling super().__init__() so
        # it doesn't overwrite height/width

        not_a_tokenstream(contents)
        if contents is None:
            self._contents = []
        else:
            self._contents = contents

        self.to = require_dimen(to)
        self.spread = require_dimen(spread)
        self.shifted_by = yex.value.Dimen(0)

        self.badness = 0 # positively angelic 😇

    def length_in_dominant_direction(self):

        lengths = [
            self.dominant_accessor(n)
            for n in
            self.contents
            ]

        result = sum(lengths, start=yex.value.Dimen())

        logger.debug(
                '%s: lengths in dominant direction (sum=%s): %s',
                self, result, lengths)

        return result

    def length_in_non_dominant_direction(self, c_accessor,
            shifting_polarity):

        lengths = [
            c_accessor(n) + n.shifted_by*shifting_polarity
            for n in
            self.contents
            ]

        result = max(lengths, default=yex.value.Dimen())

        logger.debug(
                '%s: lengths in non-dominant direction (max=%s): %s',
                self, result, lengths)

        return result

    def fit_to(self, size,
            badness_param = None,
            ):
        """
        Fits this box to the given length. The length of all glue will
        be adjusted accordingly.

        Args:
            size (Dimen): the width, for horizontal boxes, or height,
                for vertical boxes, to fit this box to.

            badness_param: if not None, a C_NumberParameter to update
                with the new badness score.
        """
        self.badness = self._inner_fit_to(
                size = size,
                contents = self._contents,
                badness_param = badness_param,
                )

    def _inner_fit_to(self, size, contents, badness_param):

        size = require_dimen(size)

        logger.debug(
                '%s: fitting our length to %s',
                self, size)

        length_boxes = [
            self.dominant_accessor(n)
            for n in
            contents
            if not isinstance(n, Leader)
            ]

        sum_length_boxes = sum(length_boxes,
            start=yex.value.Dimen())

        logger.debug(
                '%s: -- contents, other than leaders, sum to %s and are: %s',
                self, sum_length_boxes, length_boxes)

        leaders = [
                n for n in contents
                if isinstance(n, Leader)
                ]

        for leader in leaders:
            leader.glue.length = leader.glue.space

        length_glue = [
                leader.glue.length
                for leader in leaders
                ]

        sum_length_glue = sum(length_glue,
            start=yex.value.Dimen())

        logger.debug(
                '%s: -- leaders sum to %s and are: %s',
                self, sum_length_glue, leaders)

        natural_width = sum_length_boxes + sum_length_glue

        sum_glue_final_total = yex.value.Dimen()

        if natural_width == size:
            logger.debug(
                '%s: -- natural width==%s, which is equal to the new size',
                self, natural_width)
            factor = 0

        elif natural_width < size:
            difference = size - natural_width
            logger.debug(
                '%s: -- natural width==%s, so it must get longer by %s',
                self, natural_width, difference)

            max_stretch_infinity = max([g.stretch.infinity for g in leaders])
            stretchability = float(sum([g.stretch for g in leaders
                if g.stretch.infinity==max_stretch_infinity]))

            factor = float(difference)/stretchability
            if max_stretch_infinity==0:
                logger.debug(
                        '%s:   -- each unit of stretchability '
                        'should change by %0.04g',
                    self, factor)

            for leader in leaders:
                g = leader.glue
                logger.debug(
                    '%s:   -- considering %s',
                    self, g)

                if g.stretch.infinity<max_stretch_infinity:
                    g.length = g.space
                    logger.debug(
                            '%s:     -- it can\'t stretch further: %g',
                        self, g.length)
                    continue

                if max_stretch_infinity==0:
                    # Values in g.stretch are actual lengths
                    g.length = g.space + g.stretch*factor
                else:
                    # Values in g.stretch are proportions
                    g.length = g.space + (
                            difference * (float(g.stretch)/stretchability))

                logger.debug(
                        '%s:     -- new width: %g',
                    self, g.length)

                leader.glue = g

                sum_glue_final_total += g

        else: # natural_width > size

            difference = natural_width - size

            logger.debug(
                '%s: natural width==%s, so it must get shorter by %s',
                self, natural_width, difference)

            max_shrink_infinity = max([g.shrink.infinity for g in leaders])
            shrinkability = float(sum([g.shrink for g in leaders
                if g.shrink.infinity==max_shrink_infinity],
                start=yex.value.Dimen()))

            factor = float(difference)/shrinkability
            if max_shrink_infinity==0:
                logger.debug(
                        '%s:   -- each unit of shrinkability '
                        'should change by %0.04g',
                    self, factor)

            final = None
            rounding_error = 0.0

            for leader in leaders:
                g = leader.glue

                logger.debug(
                    '%s:   -- considering %s',
                    self, g)

                if g.shrink.infinity<max_shrink_infinity:
                    g.length = g.space
                    logger.debug(
                            '%s:     -- it can\'t shrink further: %g',
                        self, g.length)
                    continue

                rounding_error_delta = (
                        g.space.value - g.shrink.value*factor)%1

                g.length = g.space - g.shrink * factor

                if g.length.value < g.space.value-g.shrink.value:
                    g.length.value = g.space.value-g.shrink.value
                else:
                    rounding_error += rounding_error_delta
                    logger.debug(
                            '%s:     -- rounding error += %g, to %g',
                        self, rounding_error_delta, rounding_error)

                logger.debug(
                        '%s:     -- new width: %g',
                    self, g.length)

                leader.glue = g
                sum_glue_final_total += g
                final = g

            if final is not None and rounding_error!=0.0:
                logger.debug(
                        '%s:     -- adjusting %s for rounding error of %.6gsp',
                    self, final, rounding_error)
                final.length -= yex.value.Dimen(rounding_error, 'sp')

        # The badness algorithm begins on p97 of the TeXbook

        sum_length_final_total = sum_glue_final_total + sum_length_boxes

        if (sum_length_final_total > size):
            badness = 1000000
            logger.debug(
                '%s: -- box is overfull (%s>%s), so badness == %s',
                self, sum_length_final_total, size, badness)

        else:

            badness = int(round(factor**3 * 100))
            logger.debug(
                '%s: -- badness is (%s**3 * 100) == %d',
                self, factor, badness)

            BADNESS_LIMIT = 10000

            if badness > BADNESS_LIMIT:
                badness = BADNESS_LIMIT
                logger.debug(
                    '%s:   -- clamped to %d',
                    self, badness)

        if badness_param is not None:
            badness_param.value = badness

        logger.debug(
            '%s: -- done!',
            self)

        return badness

    def append(self, thing):
        self._contents.append(thing)

    def extend(self, things):
        for thing in things:
            self.append(thing)

    def _showbox_one_line(self):
        result = r'\%s(%0.06g+%0.06g)x%0.06g' % (
                self.__class__.__name__.lower(),
                self.height,
                self.depth,
                self.width,
                )

        if self.shifted_by.value:
            result += ', shifted %0.06g' % (
                    self.shifted_by,
                    )

        return result

    def _repr(self):
        result = ''

        if int(self.spread)!=0:
            result += f':spread={self.spread}'

        if int(self.to)!=0:
            result += f':to={self.to}'

        result += super()._repr()
        return result

class Breakpoint:
    """
    A point at which the words in an HBox could wrap to the next line.

    Chapter 14 of the TeXbook explains the algorithm.

    Attributes:
        penalty (int): the cost of breaking at this breakpoint.
    """

    def __init__(self, penalty=0):
        self.penalty = penalty

    def __repr__(self):
        return f'[bp:{self.penalty}]'

class HBox(HVBox):
    """
    A box whose contents are arranged horizontally.

    Text in HBoxes can be wordwrapped at points called Breakpoints.
    HBoxes insert Breakpoints as they go along, but their "contents"
    property always returns a copy with the Breakpoints removed.
    This saves astonishing any code which expects to find in a box
    exactly what it just put in there.

    If you want to see the Breakpoints, look in the "with_breakpoints"
    property. It returns a proxy of this object where the Breakpoints
    are visible.
    """

    dominant_accessor = lambda self, c: c.width

    def _offset_fn(self, c):
        return c.width

    @property
    def width(self):
        return self.length_in_dominant_direction()

    @property
    def height(self):
        result = self.length_in_non_dominant_direction(
                c_accessor = lambda c: c.height,
                shifting_polarity = -1,
                )
        return result

    @property
    def depth(self):
        return self.length_in_non_dominant_direction(
                c_accessor = lambda c: c.depth,
                shifting_polarity = 1,
                )

    def append(self, thing,
            hyphenpenalty = 50,
            exhyphenpenalty = 50):

        def is_glue(thing):
            return isinstance(thing, Leader) and \
                    isinstance(thing.glue, yex.value.Glue)

        try:
            previous = self._contents[-1]
        except IndexError:
            previous = None

        if is_glue(thing):
            if previous is not None and not previous.discardable:
                # FIXME and it's not part of a maths formula
                super().append(Breakpoint())
                logger.debug(
                        '%s: added breakpoint before glue: %s',
                        self, self._contents)
            elif isinstance(previous, Kern):
                self._contents.pop()
                super().append(Breakpoint())
                super().append(previous)

                logger.debug(
                        '%s: added breakpoint before previous kern: %s',
                        self, self._contents)
            elif isinstance(previous,
                    MathSwitch) and previous.which==False:
                self._contents.pop()
                super().append(Breakpoint())
                super().append(previous)

                logger.debug(
                        '%s: added breakpoint before previous math-off: %s',
                        self, self._contents)

        elif isinstance(thing, Penalty):
            super().append(Breakpoint(thing.demerits))
            logger.debug(
                    '%s: added penalty breakpoint: %s',
                    self, self._contents)

        elif isinstance(thing, DiscretionaryBreak):

            try:
                if previous.ch!='':
                    demerits = exhyphenpenalty
                else:
                    demerits = hyphenpenalty
            except AtttributeError:
                demerits = exhyphenpenalty

            super().append(Breakpoint(demerits))
            logger.debug(
                    '%s: added breakpoint before discretionary break: %s',
                    self, self._contents)

        super().append(thing)

    @property
    def contents(self):
        return [item for item in self._contents
                if isinstance(item, Gismo)]

    @property
    def with_breakpoints(self):
        """
        Returns a proxy of this box which makes Breakpoints visible.
        """
        return _HBoxWithBreakpoints(self)

class _HBoxWithBreakpoints(wrapt.ObjectProxy):
    """
    An HBox where the breakpoints are visible.

    HBoxes always keep track of their breakpoints, but by default they
    hide them in _contents. This proxy makes them visible.
    """

    @property
    def contents(self):
        result = self.__wrapped__._contents
        return result

    def __repr__(self):
        return repr(self.__wrapped__)[:-1]+f';breaks]'

class VBox(HVBox):

    dominant_accessor = lambda self, c: c.height+c.depth

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.contents = self._contents

    def _offset_fn(self, c):
        return yex.value.Dimen(), c.height+c.depth

    @property
    def width(self):
        return self.length_in_non_dominant_direction(
                c_accessor = lambda c: c.width,
                shifting_polarity = 1,
                )

    @property
    def height(self):
        return self.length_in_dominant_direction() - self.depth

    @property
    def depth(self):
        try:
            bottom = self.contents[-1]
        except IndexError:
            return yex.value.Dimen()

        return bottom.depth

class VtopBox(VBox):
    pass

class CharBox(Box):
    """
    A Box containing single character from a font.

    Attributes:
        ch (str): the character
        font: the font
        from_ligature (str): the ligature that produced this character,
            or None if there wasn't one. Usually this is None.
            It's only used for diagnostics.
    """
    def __init__(self, font, ch):

        metric = font[ch].metrics
        super().__init__(
                height = yex.value.Dimen(metric.height, 'pt'),
                width = yex.value.Dimen(metric.width, 'pt'),
                depth = yex.value.Dimen(metric.depth, 'pt'),
                )

        self.font = font
        self.ch = ch
        self.from_ligature = None

    def __repr__(self):
        if self.from_ligature is not None:
            return f'[{self.ch} from {self.from_ligature}]'
        else:
            return f'[{self.ch}]'

    def showbox(self):
        if self.from_ligature is not None:
            return [r'%s %s (ligature %s)' % (
                self.font, self.ch,
                self.from_ligature,
                )]
        else:
            return [r'%s %s' % (self.font, self.ch)]

class WordBox(HBox):
    """
    A sequence of characters from a yex.font.Font.

    Not something in TeX. This exists because the TeXbook says
    about character tokens in horizontal mode (p282):

    "If two or more commands of this type occur in succession,
    TEX processes them all as a unit, converting to ligatures
    and/or inserting kerns as directed by the font information."
    """

    def __init__(self, font):
        super().__init__()
        self.font = font

    def append(self, ch):
        if not isinstance(ch, str):
            raise TypeError(
                    f'WordBoxes can only hold characters '
                    f'(and not {ch}, which is {type(ch)})')
        elif len(ch)!=1:
            raise TypeError(
                    f'You can only add one character at a time to '
                    f'a WordBox (and not "{ch}")')

        new_char = CharBox(
                ch = ch,
                font = self.font,
                )

        font_metrics = self.font.metrics

        previous = None
        try:
            previous = self._contents[-1].ch
        except IndexError as e:
            pass
        except AttributeError as e:
            pass

        if previous is not None:
            pair = previous + ch

            kern_size = font_metrics.kerns.get(pair, None)

            if kern_size is not None:
                new_kern = Kern(width=-kern_size)
                logger.debug("%s: adding kern: %s",
                        self, new_kern)

                self._contents.append(new_kern)

            else:

                ligature = font_metrics.ligatures.get(pair, None)

                if ligature is not None:
                    logger.debug('%s:  -- add ligature for "%s"',
                            self, pair)

                    self._contents[-1].from_ligature = (
                        self._contents[-1].from_ligature or
                            self.contents[-1].ch) + ch

                    self._contents[-1].ch = ligature
                    return

        logger.debug("%s: adding %s after %s",
                self, ch, previous)
        self._contents.append(new_char)

    @property
    def ch(self):
        return ''.join([yex.util.only_ascii(c.ch) for c in self._contents
                if isinstance(c, CharBox)])

    def __repr__(self):
        return f'[wordbox:{self.ch}]'

    def showbox(self):
        r"""
        Returns a list of lines to be displayed by \showbox.

        WordBox doesn't appear in the output because it's not
        something that TeX displays.
        """
        return sum(
                [x.showbox() for x in self._contents],
                [])