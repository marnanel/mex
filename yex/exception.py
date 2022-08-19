def t(n):
    r"""
    Returns the str() of an object plus a description of its type.

    For use in descriptions of error messages.

    Args:
        n: any object

    Returns:
        If n is exactly the string "EOF", returns "end of file".
        Otherwise, returns f"{n} (which is a {type(n)})".
    """
    if n=='EOF':
        return 'end of file'
    else:
        return f'{n} (which is a {n.__class__.__name__})'

class YexError(Exception):

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args)

        self.kwargs = kwargs

        if not hasattr(self, 'form'):
            return

        try:
            g = self.form.replace("'", "\\'").replace('\\', '\\\\')

            self.message = eval(f"f'{g}'", globals(), kwargs)
        except Exception as e:
            self.message = (
                    f"Error in error: {e}; "
                    f"form is: {self.form}; "
                    f"details are: {kwargs}"
                    )

    def __getitem__(self, k):
        return self.kwargs[k]

    def __str__(self):
        return self.message

class ParseError(YexError):
    pass

class MacroError(YexError):
    pass

class RunawayExpansionError(ParseError):
    pass

##############################

class YexControlError(YexError):
    pass

class EndcsnameError(YexControlError):
    form = r"You used an \endcsname without a preceding \csname."

# I would just like to say that "\the" was a daft name for a major control

class TheUnknownError(YexControlError):
    form = r"\the cannot define {subject} because it doesn't exist."

class TheNotFoundError(YexControlError):
    form = r"\the found no answer for {subject}."

class LetInvalidLhsError(YexControlError):
    form = (
            r"\{name} must be followed by Control or Active, "
            r"and not {t(subject)}."
            )

##############################

class YexParseError(YexError):
    pass

class UnknownUnitError(YexParseError):
    form = '{unit_class} does not know the unit {unit}.'

class RegisterNegationError(YexParseError):
    form = "There is no unary negation of registers."

class NoUnitError(YexParseError):
    form = 'Dimens need a unit, but I found {t(problem)}.'

class ExpectedNumberError(YexParseError):
    form = 'Expected a number, but I found {t(problem)}.'

class LiteralControlTooLongError(YexParseError):
    form = (
            'Literal control sequences must have names of one character: '
            'yours was {name}.'
            )

##############################

class YexValueError(YexError):
    pass

class CantAddError(YexValueError):
    form = "Can't add {t(them)} to {us}."

class CantSubtractError(YexValueError):
    form = "Can't subtract {t(them)} from {us}."

class CantMultiplyError(YexValueError):
    form = "You can only multiply {us} by numeric values, not {t(them)}."

class CantDivideError(YexValueError):
    form = "You can only divide {us} by numeric values, not {t(them)}."

class DifferentUnitClassError(YexValueError):
    form = "{us} and {t(them)} are measuring different kinds of things."

class DifferentInfinityError(YexValueError):
    form = "{us} and {t(them)} are infinitely different."

class ForbiddenInfinityError(YexValueError):
    form = "You can only use finite units here, not fil/fill/filll."
