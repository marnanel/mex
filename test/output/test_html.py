import tempfile
from bs4 import BeautifulSoup
from test import *
import os
import pytest
import yex
import glob
import logging

logger = logging.getLogger('yex.general')

@pytest.fixture
def html_driver():

    directory_to_remove = None

    def get_driver(
            code = None,
            ):

        doc = yex.Document()

        if code is not None:
            run_code(code,
                    doc=doc,
                    mode=None,
                    )
            # FIXME these shouldn't be necessary; run_code() should
            # check for these conditions and handle them itself
            # (with a switch for if you don't want it to)
            doc.end_all_groups()
            doc.mode.exercise_page_builder()

        directory_to_remove = output_dir = tempfile.mkdtemp(prefix='yex-test')
        filename = os.path.join(
                output_dir,
                'wombat.html')

        result = yex.output.html.Html(doc, filename)

        return result

    yield get_driver

    if directory_to_remove is None:
        logger.debug("Nothing to clean up.")
        return

    logger.debug("Cleaning up directory: %s", directory_to_remove)

    for n in glob.glob(os.path.join(directory_to_remove, '*')):
        try:
            logger.debug("  -- %s", n)
        except Exception as e:
            logger.debug("    -- failed, %s", e)

    try:
        logger.debug("  -- %s", directory_to_remove)
        os.removedir(directory_to_remove)
    except Exception as e:
        logger.debug("    -- failed, %s", e)

    logger.debug("Cleanup finished.")

def test_output_html_init(html_driver):
    h = html_driver()

    # h.result is BeautifulSoup

    assert h.result.find('title').string=='Yex output'

def test_output_html_can_handle():
    assert yex.output.html.Html.can_handle('html')
    assert yex.output.html.Html.can_handle('htm')
    assert not yex.output.html.Html.can_handle('pdf')

def test_output_html_render(html_driver):

    STRING = "Where have all the flowers gone?"

    h = html_driver(STRING)

    h.render()

    with open(h.filename, 'r') as f:
        results = BeautifulSoup(f, features='lxml')

    main = results.find('main')

    assert [s for s in main.strings if s.strip()!='']==[
            'Where', 'have', 'all', 'the', '(0d)owers', 'gone?',
            ]

def make_example_vbox(
        para_indent,
        first_line_spacing,
        second_line_spacing,
        split_at,
        ):

    font = yex.font.Default()

    result = yex.box.VBox()
    hbox = yex.box.HBox()
    result.append(hbox)

    space_width = first_line_spacing

    for i, word in enumerate(
            'My face is my fortune, sir; nobody asked you to'.split()):

        if i==0:
            # start of first line
            hbox.append(yex.box.Leader(glue=yex.value.Glue(para_indent)))
        elif hbox.is_void():
            pass # start of subsequent line; do nothing
        else:
            glue = yex.value.Glue(space_width)
            leader = yex.box.Leader(glue=glue)
            hbox.append(leader)

        wordbox = yex.box.WordBox(font)
        for letter in word:
            wordbox.append(letter)

        hbox.append(wordbox)

        if i==split_at:
            hbox = yex.box.HBox()
            result.append(hbox)
            space_width = second_line_spacing

    return result

def test_output_html_internals_realistic(html_driver):

    h = html_driver()

    vbox = make_example_vbox(
        para_indent = 5,
        first_line_spacing = 3,
        second_line_spacing = 7,
        split_at = 4,
    )

    words = h._generate_written_words(vbox)

    assert str(words)==('['
            '[ 5 [wordbox;My] 3], '
            '[ [wordbox;face] 3], '
            '[ [wordbox;is] 3], '
            '[ [wordbox;my] 3], '
            '[ [wordbox;fortune,] br], '
            '[ [wordbox;sir;] 7], '
            '[ [wordbox;nobody] 7], '
            '[ [wordbox;asked] 7], '
            '[ [wordbox;you] 7], '
            '[ [wordbox;to] br]'
            ']'
            )

    vbox = make_example_vbox(
        para_indent = 3,
        first_line_spacing = 4,
        second_line_spacing = 5,
        split_at = 2,
    )

    words = h._generate_written_words(vbox,
            merge_with = words,
            )

    assert str(words)==('['
            '[ 5,3 [wordbox;My] 3,4], '
            '[ [wordbox;face] 3,4], '
            '[ [wordbox;is] 3,br], '
            '[ [wordbox;my] 3,5], '
            '[ [wordbox;fortune,] br,5], '
            '[ [wordbox;sir;] 7,5], '
            '[ [wordbox;nobody] 7,5], '
            '[ [wordbox;asked] 7,5], '
            '[ [wordbox;you] 7,5], '
            '[ [wordbox;to] br,br]'
            ']'
            )

    assert [x.contains_breaks for x in words] == [
            False, False, True, False, True, False, False, False, False, True,
            ], f'words={words}'

    assert [x.has_lhs for x in words] == [
            True,
            False, False, False, False, False, False, False, False, False,
            ], f'words={words}'

    width_boxes = h._generate_width_boxes(words)
    assert str(width_boxes)==(
            '[[5,3 My face is 3,4], [my fortune, 3,5], '
            '[sir; nobody asked you to 7,5]]'
            )

    words[-2].rhs = [
            yex.value.Dimen(1),
            yex.value.Dimen(2),
            ]

    words[-1].rhs = words[-2].rhs

    width_boxes = h._generate_width_boxes(words)
    assert str(width_boxes)==(
            '[[5,3 My face is 3,4], [my fortune, 3,5], '
            '[sir; nobody asked 7,5], [you to 1,2]]'
            )

    # Edge case where the "br"s are (correctly) visible
    # in the repr for the width boxes.
    # They will be replaced as appropriate in the final HTML.
    words[3].rhs[1] = None

    width_boxes = h._generate_width_boxes(words)
    assert str(width_boxes)==(
            '[[5,3 My face is 3,4], [my 3,br], [fortune, br,5], '
            '[sir; nobody asked 7,5], [you to 1,2]]'
            )

def test_output_html_width_box_classes(html_driver):

    h = html_driver()

    words = h._generate_written_words(
            make_example_vbox(
                para_indent = 0,
                first_line_spacing = 1,
                second_line_spacing = 2,
                split_at = 4,
            ),
            )

    words = h._generate_written_words(
            make_example_vbox(
                para_indent = 0,
                first_line_spacing = 3,
                second_line_spacing = 4,
                split_at = 2,
            ),
            merge_with = words,
            )

    def analyse(words):
        width_boxes = h._generate_width_boxes(words)
        return [
                (
                    str(wb),
                    wb.css_class,
                    )
                for wb in width_boxes
                ]

    widths_1 = analyse(words)

    assert [w[0] for w in widths_1] == [
                   '[My face is 1,3]',
                   '[my fortune, 1,4]',
                   '[sir; nobody asked you to 2,4]',
                   ], 'each box is different'

    assert len(set(
        [w[1] for w in widths_1]))==3, (
                'each box gets a different CSS class name'
                )

    words[7].rhs[0]=yex.value.Dimen(9)

    widths_2 = analyse(words)

    assert [w[0] for w in widths_2] == [
                   '[My face is 1,3]',
                   '[my fortune, 1,4]',
                   '[sir; nobody 2,4]',
                   '[asked 9,4]',
                   '[you to 2,4]',
                   ], 'it returns to the previous values after interpolation'

    assert [
            (
                w2[0],
                dict(widths_1).get(w2[0]) == dict(widths_2).get(w2[0]),
                w2[1] not in [w1[1] for w1 in widths_1],
                )
            for w2 in widths_2
            ]==[
                    # repr                 same?      new class?
                    ('[My face is 1,3]',   True,      False, ),
                    ('[my fortune, 1,4]',  True,      False, ),
                    ('[sir; nobody 2,4]',  False,     False, ),
                    ('[asked 9,4]',        False,     True,  ),
                    ('[you to 2,4]',       False,     False, ),

                    ], (
                            'it reuses the earlier CSS class names'
                            )