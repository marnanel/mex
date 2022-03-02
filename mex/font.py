import struct
import os
from collections import namedtuple
import logging
import mex.filename
import mex.value

commands_logger = logging.getLogger('mex.commands')

class Font:
    def __init__(self,
            tokens = None,
            filename = None,
            scale = None,
            name = None,
            ):

        if tokens is None:
            self.filename = filename
            self.scale = scale

            if isinstance(self.filename, str):
                self.filename = mex.filename.Filename(
                        self.filename,
                        filetype='font',
                        )
        else:
            if name is not None:
                raise ValueError("you can't specify both a name "
                        "and a tokeniser")
            self._set_from_tokens(tokens)

        if name is None and self.filename is not None:
            self.name = os.path.splitext(
                    os.path.basename(self.filename.value))[0]
        else:
            self.name = name

        self._metrics = None
        self.has_been_used = False

    @property
    def metrics(self):
        if self._metrics is None:
            self.filename.resolve()
            commands_logger.debug("loading font metrics from %s",
                self.filename)
            self._metrics = Metrics(self.filename.path)

        return self._metrics

    def _set_from_tokens(self, tokens):
        self.filename = mex.filename.Filename(
                name = tokens,
                filetype = 'font',
                )

        commands_logger.debug(r"font is: %s",
                self.filename.value)

        tokens.eat_optional_spaces()
        if tokens.optional_string("at"):
            tokens.eat_optional_spaces()
            self.scale = mex.value.Dimen(tokens)
            commands_logger.debug(r"  -- scale is: %s",
                    self.scale)
        elif tokens.optional_string("scaled"):
            tokens.eat_optional_spaces()
            self.scale = mex.value.Number(tokens)
            commands_logger.debug(r"  -- scale is: %s",
                    self.scale)
        else:
            self.scale = None
            commands_logger.debug(r"  -- scale is not specified")

    def __repr__(self):
        result = self.name
        if self.scale is not None:
            result += f' at {self.scale}pt'

        return result

    def __getitem__(self, n):

        if not isinstance(n, int):
            raise TypeError()
        if n<=0:
            raise ValueError()

        if n in self.metrics.dimens:
            result = self.metrics.dimens[n]
        else:
            result = mex.value.Dimen()

        commands_logger.debug(
                r"%s: lookup dimen %s, == %s",
                self, n, result)

        return result

    def __setitem__(self, n, v):
        if not isinstance(n, int):
            raise TypeError()
        if n<=0:
            raise ValueError()
        if not isinstance(v, mex.value.Dimen):
            raise TypeError()

        if n not in self.metrics.dimens and self.has_been_used:
            raise mex.exception.MexError(
                    "You can only add new dimens to a font "
                    "before you use it.")

        commands_logger.debug(
                r"%s: set dimen %s, = %s",
                self, n, v)
        self.metrics.dimens[n] = v

class Nullfont(Font):
    """
    A font that does nothing much.

    An instance of this font always appears in the controls table
    under the name "nullfont".
    """

    def __init__(self):
        super().__init__(
                name = 'nullfont',
                )

        class NullfontMetrics:
            def __init__(self):
                self.dimens = {}

        self._metrics = NullfontMetrics()

class CharacterMetric(namedtuple(
    "CharacterMetric",
    "codepoint width_idx height_idx depth_idx "
    "char_ic_idx tag_code remainder "
    "parent",
    )):

    @property
    def tag(self):
        return [
                "vanilla", "kerned", "chain", "extensible",
                ][self.tag_code]

    @property
    def width(self):
        return self.parent.width_table[self.width_idx]

    @property
    def height(self):
        return self.parent.height_table[self.height_idx]

    @property
    def depth(self):
        return self.parent.depth_table[self.depth_idx]

    def __repr__(self):
        return ('%(codepoint)3d '+\
               'w%(width)4.2f '+\
               'h%(height)4.2f '+\
               'd%(depth)4.2f '+\
               'c%(char_ic_idx)-3d '+\
               '%(tag)s') % {
                       'codepoint': self.codepoint,
                       'width': self.width,
                       'height': self.height,
                       'depth': self.depth,
                       'char_ic_idx': self.char_ic_idx,
                       'tag': self.tag,
                       }

class Metrics:

    # Font metrics, from TFM files. See
    # https://tug.org/TUGboat/Articles/tb02-1/tb02fuchstfm.pdf
    # for details of the format.

    def __init__(self, filename):
        with open(filename, 'rb') as f:

            # load the actual header

            headers= f.read(12*2)

            self.file_length, self.header_table_length, \
                    self.first_char, self.last_char, \
                    self.width_table_length, \
                    self.height_table_length, \
                    self.depth_table_length, \
                    self.italic_correction_table_length, \
                    self.lig_kern_program_length, \
                    self.kern_table_length, \
                    self.extensible_char_table_length, \
                    self.param_count = \
                    struct.unpack(
                        '>'+'H'*12,
                        headers,
                        )

            charcount = self.last_char-self.first_char+1

            if self.file_length != \
                    (6+self.header_table_length+\
                    charcount+ \
                    self.width_table_length+ \
                    self.height_table_length+ \
                    self.depth_table_length+ \
                    self.italic_correction_table_length+ \
                    self.lig_kern_program_length+ \
                    self.kern_table_length+ \
                    self.extensible_char_table_length+ \
                    self.param_count):

                        raise ValueError(f"{filename} does not appear "
                                "to be a .tfm file.")

            # load the table that TeX calls the header.
            # For some reason it's always 18*4 bytes long,
            # not necessarily the length of header_table_length.

            header_table = f.read(18*4)

            self.checksum, \
                    self.design_size, \
                    self.character_coding_scheme, \
                    self.font_identifier, \
                    self.random_word = \
                    struct.unpack(
                            '>II40p20pI',
                            header_table,
                            )

            finfo = struct.unpack(
                    f'>{charcount}I',
                    f.read(charcount*4),
                    )

            self.char_table = dict([       
                (charcode,
                CharacterMetric(
                    charcode,
                    (value & 0xFF000000) >> 24,
                    (value & 0x00F00000) >> 20,
                    (value & 0x000F0000) >> 16,
                    (value & 0x0000FD00) >> 10,
                    (value & 0x00000300) >> 8,
                    (value & 0x0000000F),
                    parent = self,
                        ))
                for charcode, value in
                enumerate(
                    finfo,
                    start = self.first_char,
                    )
                ])

            def unfix(n):
                # Turns a signed 4-byte integer into a real number.
                # See p14 of the referenced document for details.
                result = (float(n)/(2**20))*10
                return result

            def get_table(length):
                return [unfix(n) for n in
                        struct.unpack(
                        f'>{length}I',
                        f.read(length*4)
                        )]
            self.width_table = get_table(self.width_table_length)
            self.height_table = get_table(self.height_table_length)
            self.depth_table = get_table(self.depth_table_length)
            self.italic_correction_table = \
                    get_table(self.italic_correction_table_length)

            # TODO: parse lig/kern program
            self.lig_kern_program = get_table(self.lig_kern_program_length)
            # TODO: parse kern table
            self.kern_table = get_table(self.kern_table_length)

            # Dimens are specified on p429 of the TeXbook.
            # We're using a dict rather than an array
            # because the identifiers are effectively keys.
            # People might want to delete them and so on,
            # but it would make no sense, say, to shift them all
            # down by one.
            self.dimens = dict([
                    (i+1, mex.value.Dimen(unfix(n), 'pt'))
                    for i, n
                    in enumerate(struct.unpack('>7I', f.read(7*4)))
                    ])

    def print_char_table(self):
        for f,v in self.char_table.items():
            if f>31 and f<127:
                char = chr(f)
            else:
                char = ' '

            print('%4d %s %s' % (f, char, v))

if __name__=='__main__':
    m = Metrics(
            filename = 'other/cmr10.tfm'
            )
