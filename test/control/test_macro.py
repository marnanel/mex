import io
import pytest
from mex.state import State
from mex.parse import Tokeniser, Expander
from .. import run_code
import mex.font
import mex.put

def test_expand_simple():
    string = "This is a test"
    assert run_code(string,
            find = 'chars',
            ) == string

def test_expand_simple_def():
    assert run_code(
            setup = r'\def\wombat{Wombat}',
            call = r'\wombat',
            find = "chars",
            ) =="Wombat"

def test_expand_simple_with_nested_braces():
    string = "\\def\\wombat{Wom{b}at}\\wombat"
    assert run_code(
            string,
            find = "chars",
            ) =="Wom{b}at"

def test_expand_active_character():
    assert run_code(
            r"\catcode`X=13\def X{your}This is X life",
            find = "chars",
            ) =="This is your life"

def test_expand_with_single():
    assert run_code(r"This is a test",
            single=False,
            find = "chars") =="This is a test"

    assert run_code(r"This is a test",
            single=True,
            find = "chars") =="T"

    assert run_code(r"{This is} a test",
            single=False,
            find = "chars") =="{This is} a test"

    assert run_code(r"{This is} a test",
            single=True,
            find = "chars") =="This is"

    assert run_code(r"{Thi{s} is} a test",
            single=False,
            find = "chars") =="{Thi{s} is} a test"

    assert run_code(r"{Thi{s} is} a test",
            single=True,
            find = "chars") =="Thi{s} is"

def test_expand_with_expand_and_single():
    assert run_code(r"{\def\wombat{x}\wombat} a test",
            single=True, expand=True,
            find = "ch") ==r"x"
    assert run_code(r"{\def\wombat{x}\wombat} a test",
            single=True, expand=False,
            find = "ch") ==r"\def\wombatx"

def test_expand_with_run_code():
    assert run_code(r"\def\wombat{x}\wombat",
            run_code=True,
            find = "chars") =="x"

    assert run_code(r"\def\wombat{x}\wombat",
            run_code=False,
            find = "chars") ==r"\def\wombat{x}\wombat"

    with run_codeer_on_string(r"\def\wombat{x}\wombat\wombat\wombat",
            run_code=True) as e:

        t1 = e.next()
        assert str(t1,
                find = "chars") =='x'

        e.run_code=False
        t2 = e.next()
        assert str(t2,
                find = "chars") ==r'\wombat'

        e.run_code=True
        t3 = e.next()
        assert str(t3,
                find = "chars") =='x'

def test_expand_with_run_code():
    s = State()

    with io.StringIO(r"abc") as f:
        t = Tokeniser(
                state = s,
                source = f,
                )

        e1 = Expander(t)

        t1 = e1.next()
        assert t1.ch=='a'

        e2 = Expander(t)
        t2 = e2.next()
        assert t2.ch=='b'

        t3 = e1.next()
        assert t3.ch=='c'

def test_expand_ex_20_2():
    string = r"\def\a{\b}" +\
            r"\def\b{A\def\a{B\def\a{C\def\a{\b}}}}" +\
            r"\def\puzzle{\a\a\a\a\a}" +\
            r"\puzzle"
    assert run_code(string,
            find = "chars") =="ABCAB"

def test_expand_params_p200():
    # I've replaced \\ldots with ... because it's not
    # pre-defined here, and _ with - because it's run
    # in vertical mode.
    string = r"\def\row#1{(#1-1,...,#1-n)}\row x"
    assert run_code(string,
            find = "chars") ==r"(x-1,...,x-n)"

def test_expand_params_p201():
    # I've replaced \\ldots with ... because it's not
    # pre-defined here, and _ with - because it's run
    # in vertical mode.
    string = r"\def\row#1#2{(#1-1,...,#1-#2)}\row xn"
    assert run_code(string,
            find = "chars") ==r"(x-1,...,x-n)"

def test_expand_params_p203():
    assert run_code(
            setup=(
                r"\def\cs AB#1#2C$#3\$ {#3{ab#1}#1 c##\x #2}"
                ),
            call=(
                r"\cs AB {\Look}C${And\$ }{look}\$ 5"
                ),
            find='ch',
            mode='dummy',
            )==r"{And\$ }{look}{ab\Look}\Look c#\x5"

def test_expand_params_p325():
    string = (
            r"\def\a#1{\def\b##1{##1#1}}"
            r"\a!"
            r"\b x"
            )
    assert run_code(string,
            find='chars',
            )=="x!"

def test_expand_params_final_hash_p204():
    # The output "\hboxto" is an artefact of run_code;
    # it just concats all the string representations.
    assert run_code(
            setup=(
                r"\def\a#1#{\hbox to #1}"
                ),
            call=(
                r"\a3pt{x}"
                ),
            find='ch',
            mode='dummy',
            )==r"\hboxto 3pt{x}"

def test_expand_params_out_of_order():
    with pytest.raises(mex.exception.ParseError):
        string = r"\def\cs#2#1{foo}"
        run_code(string,
                find='chars',
                )

def test_expand_params_basic_shortargument():
    string = "\\def\\hello#1{a#1b}\\hello 1"
    assert run_code(string,
            find = "chars") =="a1b"

def test_expand_params_basic_longargument():
    string = "\\def\\hello#1{a#1b}\\hello {world}"
    assert run_code(string,
            find = "chars") =="aworldb"

def test_expand_params_with_delimiters():
    string = (
            r"\def\cs#1wombat#2spong{#2#1}"
            r"\cs wombawombatsposponspong"
            )
    assert run_code(string,
            find = "chars") =="sposponwomba"

def test_expand_params_with_prefix():
    string = (
            r"\def\cs wombat#1{#1e}"
            r"\cs wombat{spong}wombat"
            )
    assert run_code(string,
            find = "chars") =="spongewombat"

    string = (
            r"\def\cs wombat#1wombat{#1e}"
            r"\cs wombatswombatspong"
            )
    assert run_code(string,
            find = "chars") =="sespong"

    string = (
            r"\def\cs wombat#1wombat{#1e}"
            r"\cs wombatspongwombat"
            )
    assert run_code(string,
            find = "chars") =="sponge"

    with pytest.raises(mex.exception.MacroError):
        string = (
                r"\def\cs wombat#1wombat{#1e}"
                r"\cs womspong"
                )
        run_code(string)

def test_expand_params_non_numeric():
    for forbidden in [
            '!',
            'A',
            r'\q',
            ]:
        with pytest.raises(mex.exception.ParseError):
            string = (
                    r"\def\wombat#"
                    f"{forbidden}"
                    r"{hello}"
                    )
            run_code(string,
                    find='chars',
                    )

def test_expand_long_def():
    s = State()

    run_code(r"\long\def\ab#1{a#1b}",
            find='chars',
            state=s)
    run_code(r"\def\cd#1{c#1d}",
            find='chars',
            state=s)

    assert s['ab'].is_long == True
    assert run_code(r"\ab z",
            state=s,
            find='ch',
            )=="azb"
    assert run_code(r"\ab \par",
            state=s,
            find='ch',
            )==r"a\parb"

    assert s['cd'].is_long == False
    assert run_code(r"\cd z",
            state=s,
            find='ch',
            )=="czd"
    with pytest.raises(mex.exception.ParseError):
        run_code(r"\cd \par",
                state=s,
                find='ch',
                )

def test_expand_outer():

    # Per the TeXbook, p.205, \outer macros may not appear
    # in several places. We don't test all of them yet
    # (marked with a *), but we will. (TODO.) They are:
    #
    #  - In a macro argument
    #  - Param text of definition *
    #  - Replacement text of definition
    #  - Preamble to alignment *
    #  - Conditional text which is being skipped over *

    SETUP = (
            r"\outer\def\wombat{W}"
            r"\def\notwombat{W}"
            r"\def\spong#1{Spong}"
            )

    s = State()
    run_code(SETUP, s=s)

    assert s['wombat'].is_outer == True
    assert s['notwombat'].is_outer == False

    for (forbidden, context) in [
            (
                r'\spong{%s}',
                'macro argument',
                ),
            (
                r'\def\fred#1%s#2{fred}',
                'param text',
                ),
            (
                r'\def\fred#1{fred#1}\fred %s',
                'replacement text',
                ),
            ]:

        try:
            reason = f"outer macro called in {context}"
            run_code(
                    setup = SETUP,
                    call = forbidden % (r'\wombat',),
                    find = 'chars',
                    # not reusing s
                    )
            assert False, reason + " succeeded"
        except mex.exception.MexError:
            assert True, reason + " failed"

        try:
            reason = f'non-outer called in {context}'
            run_code(
                    setup = SETUP,
                    call = forbidden % (r'\notwombat',),
                    find = 'chars',
                    )
            assert True, reason + " succeeded"
        except mex.exception.MexError:
            assert False, reason + " failed"

def test_expand_edef_p214():

    assert run_code(
            setup=(
                r'\def\double#1{#1#1}'
                r'\edef\a{\double{xy}}'
                ),
            call=(
                r"\a"
                ),
            )=='xy'*2
    assert run_code(
            setup=(
                r'\def\double#1{#1#1}'
                r'\edef\a{\double{xy}}'
            r'\edef\a{\double\a}\a'
                ),
            call=(
                r"\a"
                ),
            )=='xy'*4

def test_expand_long_long_long_def_flag():
    s = State()
    string = "\\long\\long\\long\\def\\wombat{Wombat}\\wombat"
    assert run_code(string,
            find='chars',
            state=s,
            )=="Wombat"
    assert s['wombat'].is_long == True

# XXX TODO Integration testing of edef is best done when
# XXX macro parameters are working.

def _test_expand_global_def(form_of_def, state=None):

    if state is None:
        state = State()

    result = run_code(
            r"\def\wombat{Wombat}"
            r"\wombat",
            find='chars',
            state=state,
            )
    assert result=="Wombat"

    state.begin_group()

    result = run_code(
            r"\wombat"
            r"\def\wombat{Spong}"
            r"\wombat",
            find='chars',
            state=state,
            )
    assert result=="WombatSpong"

    state.end_group()

    result = run_code(
            "\\wombat",
            state=state)
    assert result=="Wombat"

    state.begin_group()

    result = run_code(
            r"\wombat" +\
            form_of_def + r"\wombat{Spong}"
            r"\wombat",
            find='chars',
            state=state)
    assert result=="WombatSpong"

    state.end_group()

    result = run_code(
            r"\wombat",
            find='chars',
            state=state)
    assert result=="Spong"

def test_expand_global_def():
    _test_expand_global_def(r"\global\def")

def test_expand_gdef():
    _test_expand_global_def(r"\gdef")

def test_catcode():
    # We set the catcode of ";" to 14, which makes it
    # a comment symbol.
    string = r";what\catcode`;=14 ;what"
    assert run_code(string,
            find = "chars") ==";what"

def test_chardef():
    string = r"\chardef\banana=98wom\banana at"
    assert run_code(string,
            find = "chars") =="wombat"
    string = r"\chardef\dollar=36wom\dollar at"
    assert run_code(string,
            find = "chars") =="wom$at"


def test_mathchardef():
    string = r'\mathchardef\sum="1350'
    mex.put.put(string)
    # XXX This does nothing useful yet,
    # XXX but we have the test here to make sure it parses

def run_code_the(string, s=None, *args, **kwargs):

    if s is None:
        s = State()

    result = ''

    with run_codeer_on_string(string,
            *args, **kwargs) as e:

        for c in e:
            if c.ch==32: 
                assert c.category==10 
            else: 
                assert c.category==12 

            result += c.ch

    return result

def test_the_count():
    string = r'\count20=177\the\count20'
    assert run_code_the(string,
            find = "chars") == '177'

def test_the_dimen():
    string = r'\dimen20=20pt\the\dimen20'
    assert run_code_the(string,
            find = "chars") == '20pt'

def test_let_p206_1():
    string = r'\let\a=\def \a\b{hello}\b'
    assert run_code(string,
            find = "chars") == 'hello'

def test_let_p206_2():
    string = r'\def\b{x}\def\c{y}'+\
            r'\b\c'+\
            r'\let\a=\b \let\b=\c \let\c=\a'+\
            r'\b\c'
    assert run_code(string,
            find = "chars") == 'xyyx'

def test_let_lhs_is_not_control():
    string = (
            r'\let5=5'
            )

    with pytest.raises(mex.exception.MexError):
        run_code(string,
                find='chars',
                )

def _test_font_control(
        string,
        s = None,
        ):

    if s is None:
        s = State()

    return s['_currentfont'].value

def test_countdef():
    string = r'\count28=17 '+\
            r'\countdef\chapno=28 '+\
            r'\the\chapno'+\
            r'\chapno=18'+\
            r'\the\count28'
    assert run_code(string,
            find = "chars") == '1718'

def test_dimendef():
    string = r'\dimen28=17pt'+\
            r'\dimendef\chapno=28 '+\
            r'\the\chapno'+\
            r'\chapno=18pt'+\
            r'\the\dimen28'
    assert run_code(string,
            find = "chars") == '17pt18pt'

def test_skipdef():
    string = r'\skip28=17pt plus 1pt minus 2pt'+\
            r'\skipdef\chapno=28 '+\
            r'\the\chapno'+\
            r'\chapno=18pt plus 3pt minus 4pt'+\
            r'\the\skip28'
    assert run_code(string,
            find = "chars") == '17pt plus 1pt minus 2pt18pt plus 3pt minus 4pt'

def test_muskipdef():
    string = r'\muskip28=17pt plus 1pt minus 2pt'+\
            r'\muskipdef\chapno=28 '+\
            r'\the\chapno'+\
            r'\chapno=18pt plus 3pt minus 4pt'+\
            r'\the\muskip28'
    assert run_code(string,
            find = "chars") == '17pt plus 1pt minus 2pt18pt plus 3pt minus 4pt'

def test_toksdef():
    string = (
            r'\toks28={Yes, we have no bananas}'
            r'\toksdef\bananas=28 '
            r'\the\bananas'
            r'\bananas={delicious and yellow}'
            r'\the\toks28'
            )
    assert run_code(string,
            find = "chars") == (
                    'Yes, we have no bananas'
                    'delicious and yellow'
                    )

# Arithmetic

def test_advance_count():
    assert run_code(
            r'\count10=100'+\
                    r'\advance\count10 by 5 '+\
                    r'\the\count10',
                    find = "chars") == '105'

def test_advance_dimen():
    assert run_code(
            r'\dimen10=10pt'+\
                    r'\advance\dimen10 by 5pt'+\
                    r'\the\dimen10',
                    find = "chars") == '15pt'

def test_multiply():
    assert run_code(
            (r'\count10=100'
                r'\multiply\count10 by 5 '
                r'\the\count10'),
            find = "chars") == '500'

def test_divide():
    assert run_code(
            (r'\count10=100'
                r'\divide\count10 by 5 '
                r'\the\count10'),
            find='chars',
            ) == '20'

# Conditionals

def test_conditional_basics():
    assert run_code(r"a\iftrue b\fi z",
            find = "chars") =='abz'
    assert run_code(r"a\iffalse b\fi z",
            find = "chars") =='az'
    assert run_code(r"a\iftrue b\else c\fi z",
            find = "chars") =='abz'
    assert run_code(r"a\iffalse b\else c\fi z",
            find = "chars") =='acz'

def test_conditional_nesting():
    for outer, inner, expected in [
            ('true', 'true', 'abcez'),
            ('true', 'false', 'abdez'),
            ('false', 'true', 'afgiz'),
            ('false', 'false', 'afhiz'),
            ]:
        assert run_code((
            rf"a\if{outer} "
            rf"b\if{inner} c\else d\fi e"
            r"\else "
            rf"f\if{inner} g\else h\fi i"
            r"\fi z"),
            find='chars',
            )==expected

def test_conditional_ifcase():

    s = State()

    run_code(r"\countdef\who=0", s=s)

    for expected in ['fred', 'wilma', 'barney',
            'betty', 'betty', 'betty']:

        assert run_code((
                r"\ifcase\who fred"
                    r"\or wilma"
                    r"\or barney"
                    r"\else betty"
                    r"\fi\advance\who by 1"),
                    find='chars',
                    state=s,
                    )==expected

def test_conditional_ifnum_irs():
    # Based on the example on p207 of the TeXbook.

    s = State()

    run_code(r"\countdef\balance=77", s=s)

    for balance, expected in [
            (-100, 'under'),
            (0, 'fully'),
            (100, 'over'),
            ]:

        s['count77'] = balance

        assert run_code(
                r'\ifnum\balance=0 fully'
                r'\else\ifnum\balance>0 over'
                r'\else under'
                r'\fi'
                r'\fi',
                find='chars',
                state=s,
                )==expected

def test_conditional_ifdim():

    for length, expected in [
            ('5mm', 'shorter'),
            ('50mm', 'same'),
            ('100mm', 'longer'),
            ]:

        assert run_code(
                r"\dimen1="+length+(r"\dimen2=50mm"
                    r"\ifdim\dimen1=\dimen2 same\fi"
                    r"\ifdim\dimen1<\dimen2 shorter\fi"
                    r"\ifdim\dimen1>\dimen2 longer\fi"),
                find='chars',
                )==expected

def test_conditional_ifodd():

    state = State()

    state['count50'] = 50
    state['count51'] = 51

    for test in [
            r'\ifodd0 N\else Y\fi',
            r'\ifodd1 Y\else N\fi',
            r'\ifodd2 N\else Y\fi',
            r'\ifodd\count50 N\else Y\fi',
            r'\ifodd\count51 Y\else N\fi',
            ]:
        assert run_code(test,
                find='chars',
                state=state)=="Y"

def test_conditional_of_modes():

    string = (
        r"\ifvmode V\fi"
        r"\ifhmode H\fi"
        r"\ifmmode M\fi"
        r"\ifinner I\fi"
        )

    state = State()

    for mode, expected in [
            ('vertical', 'V'),
            ('internal_vertical', 'VI'),
            ('horizontal', 'H'),
            ('restricted_horizontal', 'HI'),
            ('math', 'MI'),
            ('display_math', 'M'),
            ]:
        state['_mode'] = mode
        assert run_code(string,
                find='chars',
                state=state)==expected

def _ifcat(q, state):
    return run_code(
            r"\ifcat " + q +
            r"T\else F\fi",
            find='chars',
            state=state,
            ).strip()

def test_conditional_ifcat():
    s = State()

    assert _ifcat('11', s)=='T'
    assert _ifcat('12', s)=='T'
    assert _ifcat('AA', s)=='T'
    assert _ifcat('AB', s)=='T'
    assert _ifcat('1A', s)=='F'
    assert _ifcat('A1', s)=='F'

def test_conditional_ifcat_p209():
    s = State()

    # Example from p209 of the TeXbook
    run_code(r"\catcode`[=13 \catcode`]=13 \def[{*}",
            find='chars',
            s=s)

    assert _ifcat(r"\norun_code[\norun_code]", s)=="T"
    assert _ifcat(r"[*", s)=="T"
    assert _ifcat(r"\norun_code[*", s)=="F"

def _ifproper(q, state):
    return run_code(
            r"\if " + q +
            r" T\else F\fi",
            find='chars',
            state=state)

def test_conditional_ifproper():
    s = State()

    assert _ifproper('11', s)=='T'
    assert _ifproper('12', s)=='F'
    assert _ifproper('AA', s)=='T'
    assert _ifproper('AB', s)=='F'
    assert _ifproper('1A', s)=='F'
    assert _ifproper('A1', s)=='F'

def test_conditional_ifproper_p209():
    s = State()

    # Example from p209 of the TeXbook
    run_code((
        r"\def\a{*}"
        r"\let\b=*"
        r"\def\c{/}"),
        find='chars',
        state=s,
        )

    assert _ifproper(r"*\a", s)=="T"
    assert _ifproper(r"\a\b", s)=="T"
    assert _ifproper(r"\a\c", s)=="F"

##########################

def test_inputlineno():
    string = (
            r"\the\inputlineno"
            '\n'
            r"\the\inputlineno"
            '\n'
            '\n'
            r"\the\inputlineno"
            r"\the\inputlineno"
            )

    assert run_code(string,
            find='chars',
            )==r"1 2 \par44"

##########################

def test_message(capsys):
    run_code(r"\message{what}",
            find='chars')
    roe = capsys.readouterr()
    assert roe.out == "what"
    assert roe.err == ""

def test_errmessage(capsys):
    run_code(r"\errmessage{what}",
            find='chars')
    roe = capsys.readouterr()
    assert roe.out == ""
    assert roe.err == "what"

def test_special():
    found = {'x': None}
    def handle_string(self, name, s):
        found['x'] = s

    mex.control.Special.handle_string = handle_string
    run_code(r"\special{what}",
            find='chars')

    assert found['x'] == "what"

def test_register_table_name_in_message(capsys):
    # Based on ch@ck in plain.tex.
    # This doesn't parse unless the \errmessage
    # handler is run, but told not to do anything,
    # even when an if statement would ordinarily stop it.
    #
    # This is because the parser run_codes all code
    # when it's not executing. That's usually the
    # right answer, but not for \message{} and friends.

    run_code(
            r"\def\check#1#2{\ifnum\count11<#1"
            r"\else\errmessage{No room for a new #2}\fi}"
            r"\check1\dimen",
            find='chars',
            )
    roe = capsys.readouterr()
    assert roe.err == roe.out == ''

def test_expansion_with_fewer_params():
    string = (
            r"\def\friendly #1#2#3{#1 #2 my #3 friend}"
            r"\def\greet #1{#1 {Hello} {there}}"
            r"\greet\friendly {beautiful} !"
            )

    assert run_code(string,
            find='chars',
            ) == r"Hello there my beautiful friend !"

def test_expansion_with_control_at_start_of_params():
    assert run_code(
                r"\def\Look{vada}"
                r"\def\cs A\Look B#1C{wombat #1}"
                r"\cs A\Look B9C",
                find='chars',
            )==r"wombat 9"

def test_string():
    assert run_code(
            r"\string\def",
            find='chars',
            )==r"\def"

def test_def_wlog():
    assert run_code(
            # from plain.tex
            r"\def\wlog{\immediate\write\mene}",
            find='chars',
            )==''
