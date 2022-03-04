import io
import mex.parse
import mex.state
import mex.value
import logging

general_logger = logging.getLogger('mex.general')

def expand(string, state=None,
        *args, **kwargs):

    if 's' in kwargs:
        # Workaround for old tests; should fix at some point
        state = kwargs['s']
        del kwargs['s']

    if state is None:
        state = mex.state.State()

    with io.StringIO(string) as f:
        t = mex.parse.Tokeniser(
                state = state,
                source = f,
                )

        e = mex.parse.Expander(t,
                *args, **kwargs)

        result = ''.join([t.ch for t in e])

    return result

def call_macro(
        setup,
        call,
        state = None,
        as_list = False,
        ):

    if state is None:
        state = mex.state.State()

    expand(setup, s=state)

    result = []

    with io.StringIO(call) as f:
        t = mex.parse.Tokeniser(
                state = state,
                source = f,
                )

        for token in t:

            if token is None:
                break

            general_logger.debug("call_macro saw: %s",
                    token)

            if token.category!=token.CONTROL:
                general_logger.debug("  -- which isn't a control; saved to result")

                result.append(token)
                continue

            name = token.name

            try:
                handler = state[name]
            except KeyError:
                # FIXME when State.__contains__ is implemented,
                # we should use it here.
                general_logger.debug("  -- which isn't known; saved to result")
                result.append(token)
                continue

            general_logger.debug("  -- calling it")
            received = handler(
                    name = name,
                    tokens = t,
                    )
            if received is None:
                general_logger.debug(r"call_macro: \%s gave us None",
                        name,
                        )
            else:
                result.extend(received)

                general_logger.debug(r"call_macro: \%s gave us %s; saved to result",
                        name,
                        received,
                        )

    if not as_list:
            result = ''.join([
                x.ch for x in result
                ])

    general_logger.debug("call_macro result: %s",
            result)

    return result

def tokenise_and_get(string, cls, state = None):
    """
    Creates a State and a Tokeniser, and initialises the
    class "cls" with that Tokeniser.

    The string should represent the new value followed
    by the letter "q" (so we can test how well literals are
    delimited by the following characters).

    If you pass in "state", uses that State instead of
    constructing a new one.

    Returns the result.
    """

    if state is None:
        state = mex.state.State()

    with io.StringIO(string) as f:
        t = mex.parse.Tokeniser(state, f)

        result = cls(t)

        for q in t:
            break

        if q is None:
            raise ValueError("Wanted trailing 'q' for "
                    f'"{string}" but found nothing')

        if not (q.category==q.LETTER and q.ch=='q'):
            raise ValueError(f"Wanted trailing 'q' for "
                    f'"{string}" but found {q}')

        return result

def get_number(string,
        state = None,
        raw = False,
        ):
    """
    See tokenise_and_get().
    """

    result = tokenise_and_get(string,
            cls=mex.value.Number,
            state=state,
            )

    if raw:
        return result

    return result.value

def get_dimen(string,
        state = None,
        raw = False,
        ):
    """
    See tokenise_and_get().
    """

    result = tokenise_and_get(string,
            cls=mex.value.Dimen,
            state=state,
            )

    if raw:
        return result

    return result.value

def get_glue(string,
        state = None,
        raw = False):
    """
    See tokenise_and_get().

    If raw is True, returns the Glue object;
    otherwise returns a tuple:
       (space, stretch, shrink, stretch_infinity,
       shrink_infinity).
    """

    result = tokenise_and_get(string,
            cls=mex.value.Glue,
            state=state)

    if raw:
        return result

    return (
            result.space.value,
            result.stretch.value,
            result.shrink.value,
            result.stretch.infinity,
            result.shrink.infinity,
            )

def get_muglue(string,
        state = None,
        raw = False):
    """
    See tokenise_and_get().

    If raw is True, returns the Muglue object;
    otherwise returns a tuple:
       (space, stretch, shrink, stretch_infinity,
       shrink_infinity).
    """

    result = tokenise_and_get(string,
            cls=mex.value.Muglue,
            state=state)

    if raw:
        return result

    return (
            result.space.value,
            result.stretch.value,
            result.shrink.value,
            result.stretch.infinity,
            result.shrink.infinity,
            )

__all__ = [
        'expand',
        'get_number',
        'get_dimen',
        'get_glue',
        'get_muglue',
        ]
