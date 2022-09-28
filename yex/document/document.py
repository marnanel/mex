r"`Document` holds a document while it's being processed."

import datetime
import yex
import yex.decorator
import yex.box
import re
from yex.document.callframe import Callframe
from yex.document.group import Group, GroupOnlyForModes, ASSIGNMENT_LOG_RECORD
import logging

logger = logging.getLogger('yex.general')

KEYWORD_WITH_INDEX = re.compile(r'^([^;]+?);?(-?[0-9]+)$')

FORMAT_VERSION = 1

def REGISTER_NAME(n):
    """
    Temporary: removes leading backslashes to turn control names into
    register names. When issue 6 is resolved, this won't be needed.
    """
    if n.startswith('\\'):
        return n[1:]
    else:
        return n

class Document:
    r"""A document, while it's being processed.

    All macro definitions, fonts, and so on are kept here.

    Mostly, you interact with a Document as if it was a dict, by getting
    and setting the values of its elements (known as "subscripting").
    This makes it clearer and easier when we have to reset values
    at the end of a TeX group.

    The names of all elements are strings. The values depend on the element.
    Some possible names:

        - The name of any predefined control.
            For example, ``doc['\if']``. Don't include the backslash prefix.
        - The name of any user-defined macro.
        - The name of any register.
            For example, ``doc['\count23']`` or ``doc['\box12']``.
        - The prefix of any register, such as ``doc['\count']``
            You must supply `tokens`, so we can find the rest of it.
        - Some internal special values:
            - ``doc['_font']``, for the current font.
            - ``doc['_mode']``, for the current mode.
        - A few controls can themselves be subscripted.
            Writing ``doc['\font3']`` is equivalent to writing
            ``doc['\font'][3]``.

            The second subscript must be an integer,
            and can be negative. You can also separate the field name
            from the field subscript with a semicolon. So
            ``doc['font;3']``, ``doc['font3']``, and ``doc['font'][3]``
            are equivalant. ``doc['cmr10;3']`` couldn't be written
            without the semicolon.

    Attributes:
        created_at (`datetime.datetime`): when the Document was
            constructed. This provides initial values for
            TeX's time-based parameters, such as ``\year``.
        controls (:obj:`ControlsTable`): all the controls defined,
            both built-in and user-defined. Registers
            are stored in the ``registers`` attribute, not here.
            This may change ([#6](https://gitlab.com/marnanel/yex/-/issues/6)).
        registers (:obj:`RegisterTable`): the doc of all the
            registers, such as ``\count12``.
        groups (list of :obj:`Group`): the nested groups
            of the TeX source being processed, which are
            created either by ``{``/``}`` or by
            ``\begingroup``/``\endgroup``.
        fonts (dict of :obj:`Font`): fonts currently loaded.
            They need not have identifiers in the controls
            table, but they're not accessible from TeX code
            unless they do.
        font (:obj:`Font`): the currently selected font.
        mode (:obj:`Mode`): the currently selected mode.
        output (:obj:`Output`): the output driver. For example,
            the PDF driver or the SVG driver.
        contents (list of :obj:`Box`): the rendered contents
            waiting to go to the output driver.
        next_assignment_is_global (bool): if True, the next
            use of `__setitem__` will apply until further notice.
            Otherwise, it applies until the end of the
            current group.
        parshape (list of :obj:`Dimen`): you probably don't
            need to look at this. It's a list of constraints on lengths
            of lines in the current paragraph, set by ``\parshape``
            but kept here so it persists.
        ifdepth (`_Ifdepth_List`): essentially a list of booleans,
            representing whether particular conditional clauses are
            executing. For example, after ``\iftrue`` the top member
            will be True, after ``\iffalse`` it will be False, and
            ``\else`` will (generally) negate the top member.
    """


    def __init__(self):

        self.created_at = datetime.datetime.now()

        self.controls = yex.control.ControlsTable(doc=self)
        self.controls |= yex.control.handlers()

        self.fonts = {}

        self.registers = yex.register.handlers(doc=self)

        self.groups = []

        self.next_assignment_is_global = False
        self.parshape = None

        self.ifdepth = _Ifdepth_List([True])
        self.call_stack = []

        self.font = None
        self.mode = None

        self.mode_stack = []
        self.contents = []
        self.output = None

        self.controls |= {
                '_inputs': yex.io.StreamsTable(doc=self,
                our_type=yex.io.InputStream),
                '_outputs': yex.io.StreamsTable(doc=self,
                our_type=yex.io.OutputStream),
                }

    def open(self, what,
            **kwargs):

        r"""Opens a string, a list of characters, or a file for reading.

            Constructs a :obj:`Tokeniser` on `what`,
            and an :obj:`Expander` on that `Tokeniser`.
            Returns the `Expander`.

            Args:
                what (`str`, `list`, or file-like): where we're getting the
                    symbols from.
                **kwargs: Arguments to pass to the `Expander`.

            Returns:
                An :obj:`Expander`.
            """
        t = yex.parse.Tokeniser(
                doc = self,
                source = what,
                )
        e = yex.parse.Expander(
                t,
                **kwargs,
                )
        return e

    def read(self, what,
            **kwargs):
        r"""Reads a string, or a file, and adds it to this Document.

            Args:
                thing (`str`, or file-like): something to read characters from.
                **kwargs: Arguments to pass to the `Expander` which we'll
                    use to parse the input.

            Returns:
                `None`
        """

        logger.debug("%s: reading from %s", self, what)
        logger.debug("%s: reading with params %s", self, kwargs)

        e = self.open(what, **kwargs)

        logger.debug("%s: reading through %s", self, e)

        for item in e:
            logger.debug("  -- resulting in: %s", item)

            if item is None:
                break

            self.mode.handle(
                    item=item,
                    tokens=e,
                    )

        logger.debug("%s: done", self)

    def __iadd__(self, thing):
        r"""Short for `read(thing)`. See `read` for more information.

            Args:
                thing (`str`, or file-like): something to read characters from.

            Returns:
                self (`Document`)
        """
        self.read(thing)

        return self

    def __setitem__(self, field, value,
            from_restore = False):
        r"""Assigns a value to an element of this doc.

            Args:
                field (`str`): the name of the element to change.
                    See the class description for a list of field names.
                value (any): the value to give the element.
                    Acceptable types and values depend on the field name.
                from_restore (`bool`): if True, we're in the process of
                    restoring settings at the end of a group; otherwise,
                    we're not, and we store a record of this assignment
                    until we are. You probably don't need to use this.

            Raises:
                `KeyError`: if the field doesn't name an element
                `TypeError`: if the value has the wrong type for the field
                `ValueError`: if there's something wrong with the value
                and many other possibilities, depending on which element it is

            Returns:
                `None`
            """

        if from_restore:
            logger.debug(
                    "{restoring %s=%s}",
                    field, repr(value))
            logger.debug(
                    ASSIGNMENT_LOG_RECORD,
                    'R', field, repr(value))
        elif self.next_assignment_is_global:
            logger.debug(
                    ASSIGNMENT_LOG_RECORD,
                    'G', field, repr(value))
        else:
            logger.debug(
                    ASSIGNMENT_LOG_RECORD,
                    '', field, repr(value))

            if self.groups:
                # XXX This is rather inefficient, because
                # we parse the fieldname twice
                previous = self.get(field, default=None)
                self.groups[-1].remember_restore(field,
                        previous)

        m = re.match(KEYWORD_WITH_INDEX, field)

        if m is None:

            # Must be a control, rather than a register.
            self.controls[field] = value

        else:
            keyword, index = m.groups()

            if REGISTER_NAME(keyword) in self.registers:
                self.registers[REGISTER_NAME(keyword)][int(index)] = value
            elif keyword in self.controls:
                self.controls[keyword][int(index)] = value
            else:
                # Check for missing leading backslashes.
                # This should only be a problem in legacy code,
                # so we can take this check out again in a few weeks.
                # (March 2022)
                if field[0]!='\\':
                    try:
                        self.__setitem__('\\'+field, value)
                        raise ValueError(
                                f"lookup of {field} failed, when "
                                rf"\{field} would have worked; "
                                "this is almost certainly a mistake"
                                )
                    except KeyError:
                        pass

                raise KeyError(field)

        self.next_assignment_is_global = False

    def get(self, field,
            tokens=None,
            param_control=False,
            **kwargs,
            ):
        r"""
        Retrieves the value of an element of this doc.

        Args:
            field (`str`): the name of the element to find.
                See the class description for a list of field names.
            tokens (`Expander`): in some cases, `field` may only be a
                prefix of a proper element name. For example, the count
                register numbered 23 is named "count23", but this name
                is three tokens if you write it in TeX: ``\count``, ``2``,
                and ``3``. The lookup will only fetch ``\count``, which
                isn't in itself the name of an element. So, in such cases
                we fetch the next tokens to find the full name.
            default (any): what to return if there is no such element.
                If this is not specified, we raise `KeyError`.
            param_control (bool): if True, requests for parameter controls
                return the control object itself, as with any other control.
                If False, which is the default, they return the value
                stored in the control object; this is probably what
                you wanted.

        Returns:
            the value you asked for

        Raises:
            `KeyError`: if there is no element with the name you requested,
                and `default` was not specified.
            `ParseError`: if we attempted to complete the field name with
                `tokens`, but failed.
        """

        for k in kwargs.keys():
            if k not in ['default']:
                raise TypeError(f'{k} is an invalid keyword for get()')

        # If it's the name of a registers table (such as "count"),
        # and we have access to the tokeniser, read in the integer
        # which completes the name.
        #
        # Note that you can't subscript controls this way.
        # This is because you shouldn't access these from TeX code.
        if REGISTER_NAME(field) in self.registers and tokens is not None:
            index = yex.value.Number.from_tokens(tokens).value
            result = self.registers[REGISTER_NAME(field)][index]
            logger.debug(r"  -- %s%d==%s",
                    field, index, result)
            return result

        # If it's in the controls table, that's easy.
        if field in self.controls:
            result = self.controls.get(
                    field,
                    param_control = param_control,
                    )
            logger.debug(r"  -- %s==%s (param_control==%s)",
                    field, result, param_control)
            return result

        # Or maybe it's already a variable name plus an integer.
        m = re.match(KEYWORD_WITH_INDEX, field)

        if m is not None:
            keyword, index = m.groups()

            try:
                result = self.registers[REGISTER_NAME(keyword)][int(index)]
                logger.debug(r"  -- %s==%s",
                        field, result)
                return result
            except TypeError:
                pass
            except KeyError:
                pass

            try:
                result = self.controls[keyword][int(index)]
                logger.debug(r"  -- %s==%s",
                        field, result)
                return result
            except KeyError:
                pass

        # Check for missing leading backslashes.
        # This should only be a problem in legacy code,
        # so we can take this check out again in a few weeks.
        # (March 2022)
        if field[0]!='\\':
            try:
                self.__getitem__('\\'+field)
                raise ValueError(
                        f"lookup of {field} failed, when "
                        rf"\{field} would have worked; "
                        "this is almost certainly a mistake"
                        )
            except KeyError:
                pass

        if 'default' in kwargs:
            return kwargs['default']
        else:
            raise KeyError(field)

    def __getitem__(self, field):
        return self.get(field)

    @property
    def mode_list(self):
        """
        The working list of `self.mode`. Identical to `self.mode.list`.

        This exists so that `doc['mode_list']` works.
        You can also set this property.
        """
        return self.mode.list

    @mode_list.setter
    def mode_list(self,v): self.mode.list = v

    @property
    def created(self):
        """
        Timestamp of this doc's creation. Same as `created_at.timestamp()`.

        This exists so that `doc['created']` works.
        You can't set this property, unless you're Doctor Who,
        Marty McFly, or Bill and Ted.
        """
        return self.created_at.timestamp()

    def begin_group(self,
            flavour=None,
            **kwargs,
            ):
        r"""
        Opens a new group.

        Called by ``{`` and ``\begingroup``.

        Args:
            flavour (`str` or `None`): if `None`, create ordinary group;
                if `"no-mode"` create group which won't restore a mode
                (this is for `\begingroup`; not yet implemented);
                if `"only-mode"` create a group which will only restore a mode.
                Otherwise, raise `ValueError`.

            Other arguments are passed to the constructor of Group
            (or of a subclass of Group).

        Raises:
            `ValueError`: if flavour is other than the options given above.

        Returns:
            `Group`. This is mainly useful to pass to `end_group()` to make
            sure the groups are balanced.
        """

        if flavour is None:
            new_group = Group(
                    doc = self,
                    **kwargs,
                    )
        elif flavour=='only-mode':
            try:
                delegate = self.groups[-1]
            except IndexError:
                delegate = None

            new_group = GroupOnlyForModes(
                    doc = self,
                    delegate = delegate,
                    **kwargs,
                    )
        else:
            raise ValueError(flavour)

        self.groups.append(new_group)
        logger.debug("%s: Started group: %s",
                '  '*len(self.groups),
                self.groups)

        return new_group

    def end_group(self,
            group=None,
            tokens=None,
            ):
        r"""
        Closes a group.

        Discards all settings made since the most recent `begin_group()`,
        except:
            - global settings
            - `'_mode'`, if flavour is `'no-mode'`
            - anything but `'mode'`, if flavour is `'only-mode'`.

        Called by ``}`` and ``\endgroup``.

        Args:
            group (`Group` or `None`): the group we should be closing.
                This only functions as a check; we can only close the
                top group in the stack. If this is None, which is the
                default, we just close the top group without doing a check.
                If for some reason we have to close multiple groups,
                this check is not carried out on ephemeral groups.

            tokens (`Expander` or `None`): the token stream we're reading.
                This is only needed if the group we're ending has produced
                a list which now has to be handled.

                This argument *can* be `None`, if you're sure that won't
                happen; if it does, and the handler needs a token stream,
                you'll get an error from the handler.

        Raises:
            `YexError`: if there are no groups remaining.

        Returns:
            `None`
        """
        if not self.groups:
            raise yex.exception.YexError("More groups ended than began!")

        while True:
            logger.debug("%s]] Ended group: %s",
                    '  '*len(self.groups),
                    self.groups)
            ended = self.groups.pop()

            if group is not None and not ended.ephemeral:
                if ended is not group:
                    raise ValueError(
                            f"expected to close group {group}, "
                            f"but found group {ended}."
                            )
                group = None

            ended.run_restores()

            if ended.ephemeral and self.groups:
                logger.debug("  -- the group was ephemeral, so loop")
            else:
                break

    def showlists(self):
        r"""
        Prints details of the list in the current `Mode`, and of all
        the containers it contains, and all the containers *they* contain,
        and so on.

        Implements the `\showlists` debugging command:
        see p88 of the TeXbook.

        Currently disabled.

        Args:
            none

        Returns:
            `None`
        """
        raise NotYetImplemented()

    def __len__(self):
        # this used to do something ridiculous. Catch anyone calling it.
        # Take it out when we know there's nobody. July 2022.
        raise NotImplementedError()

    def remember_restore(self, f, v):
        r"""
        Stores a record of an assignment, so it can be undone at the end
        of the current group. Doesn't actually make the assignment.
        You probably don't want to use this.

        Other than changes to internal flags, this just calls through
        to `remember_restore` in the topmost :obj:`Group`.

        Args:
            f: field name
            v: field value

        Returns:
            `None`
        """
        if not self.groups:
            return
        if self.next_assignment_is_global:
            self.next_assignment_is_global = False
            return
        self.groups[-1].remember_restore(f,v)

    def shipout(self, box):
        """
        Sends a box, or multiple boxes, to the output queue.

        Anything passed to this method will be stored, rather than
        rendered immediately. It will be rendered when the `save` method
        is called.

        Args:
            box (`Box`, or list of `Box`): a box or boxes to be rendered.

        Returns:
            `None`
        """
        if isinstance(box, list):
            self.contents.extend(box)
        else:
            self.contents.append(box)

    def end_all_groups(self,
            tokens = None,
            ):
        """
        Closes all open groups.

        Args:
            tokens (`Expander` or `None`): the token stream we're reading.
                This is only needed if one of the groups we're ending
                has produced a list which now has to be handled.

        Returns:
            `None`.
        """
        logger.debug("%s: ending all groups: %s", self,
                self.groups)
        while self.groups:
            self.end_group(
                    tokens=tokens,
                    )
        logger.debug("%s:   -- done ending all groups",
                self)

    def save(self):
        """
        Renders the document to the output driver specified
        by `doc['_output']`.

        Ends all open groups before it attempts to render.

        Raises:
            OSError: if something goes wrong during writing

        Returns:
            `None`
        """

        logger.debug("%s: saving document to %s", self,
                self.output)
        self.end_all_groups()
        self.mode.exercise_page_builder()

        if not self.contents:
            logger.debug("%s:   -- but there was no output", self)
            print("note: there was no output")
            return

        if not self.output:
            print("note: there was no output driver")
            return

        self.output.render()
        logger.debug("%s:   -- done!", self)

    def __getstate__(self,
            full=True,
            raw=False,
            ):

        result = {
                '_full': full,
                '_format': FORMAT_VERSION,
                }

        if full:
            # we don't need anything to compare against
            blank = None
        else:
            # get ourselves a fresh version of this class, so that
            # we know what's changed
            blank = self.__class__()

        # Controls

        def matches(a, b):

            def to_instance(n):
                if hasattr(n, '__subclasses__'):
                    return n(doc=self)
                else:
                    return n

            a = to_instance(a)
            b = to_instance(b)

            return a==b

        for k, v in self.controls.items():

            if not full and k not in [
                    # fields which always appear even if full==False
                    '_created',
                    ]:

                # let's see whether we should duck out of this one

                if k in blank.controls and not matches(k, blank.controls[k]):
                    continue

            logger.debug("  -- added %s==%s", k, v)
            result[k] = v

        # Registers

        for name, table in self.registers.items():

            try:
                table.contents
            except AttributeError:
                continue

            for f,v in table.items():
                result[f] = v

        def _maybe_getstate(v):
            if raw:
                return v
            elif hasattr(v, '__subclasses__') and \
                    issubclass(v, yex.control.C_Control):
                        return {'control': v.__name__}
            elif hasattr(v, '__getstate__'):
                return v.__getstate__()
            else:
                return v

        result = dict([(f,_maybe_getstate(v)) for f,v in result.items()])
        return result

    def __setstate__(self, state):
        if state['_format']!=FORMAT_VERSION:
            raise ValueError("Format version was unknown")

        self.__init__()

        state = dict(state) # take a copy

        for cruft in [
                '_format', '_full', '_created', '_inputlineno',
                ]:
            if cruft in state:
                del state[cruft]

        for field, value in sorted(state.items()):
            logger.debug("doc.__setstate__: %s=%s", field, value)
            self[field] = value

        logger.debug("doc.__setstate__: done!")

    def __repr__(self):
        return '[doc;boxes=%d]' % (len(self.contents))

    def items(self, full=False):
        if full:
            # we don't need anything to compare against
            blank = None
        else:
            # get ourselves a fresh version of this class, so that
            # we know what's changed
            blank = self.__class__()

        return DocumentIterator(
                doc = self,
                full = full,
                blank = blank,
                )

class DocumentIterator:
    def __init__(self,
        doc,
        full,
        blank,
        ):

        self.doc = doc
        self.full = full
        self.blank = blank

    def __iter__(self):
        yield ('_format', FORMAT_VERSION)
        yield ('_full',   self.full)

        # Controls

        for k, v in self.doc.controls.items():

            if k.startswith('_') and not k.startswith('__'):
                continue

            if self.full:
                yield (k, v)
            elif k not in self.blank.controls:
                yield (k, v)
            elif v.__class__!=self.blank.controls[k].__class__:
                yield (k, v)

        # Registers

        for name, table in self.doc.registers.items():

            try:
                table.contents
            except AttributeError:
                continue

            yield from table.items()

        # Other stuff

        for easy_underscored_field in INTERNAL_FIELDS:
            value = self.doc[easy_underscored_field]

            if self.full or value:
                yield (easy_underscored_field, value)

    def __repr__(self):
        return f'[{self.__class__.__name__};d={self.doc}]'

class _Ifdepth_List(list):
    """
    Just like an ordinary list, except that its representation
    is suited for printing a list of booleans compactly.
    """
    def __repr__(self):
        def _repr(v):
            if v==True:
                return 'T'
            elif v==False:
                return 'f'
            else:
                return repr(v)
        result = ''.join([_repr(v) for v in self])
        return result