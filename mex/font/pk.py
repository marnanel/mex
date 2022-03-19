# https://tug.org/TUGboat/Articles/tb06-3/tb13pk.pdf
# http://www.davidsalomon.name/DC4advertis/PKfonts.pdf

import struct

PK_XXX1 = 240
PK_XXX2 = 241
PK_XXX3 = 242
PK_XXX4 = 243
PK_YYY = 244
PK_POST = 245
PK_NO_OP = 246
PK_PRE = 247

PK_ID = 89

POINTS_PER_INCH = 72.27

class _Source:
    def __init__(self, f):
        self.f = f
        self.part_nibble = None

    def one_byte_int(self):
        self.part_nibble = None
        b = self.f.read(1)
        result = struct.unpack(
                '>'+'B',
                b,
                )[0]
        return result

    def two_byte_int(self):
        self.part_nibble = None
        b = self.f.read(2)
        result = struct.unpack(
                '>'+'H',
                b,
                )[0]
        return result

    def three_byte_int(self):
        self.part_nibble = None
        b = self.f.read(3)
        result = struct.unpack(
                '>'+'BH',
                b,
                )
        result = (b[0]<<16) | b[1]
        return result

    def four_byte_int(self):
        self.part_nibble = None
        b = self.f.read(4)
        result = struct.unpack(
                '>'+'L',
                b,
                )[0]
        return result

    def four_byte_float(self):
        self.part_nibble = None
        result = float(self.four_byte_int()) / 2**16
        return result

    def one_nibble_int(self):
        if self.part_nibble is not None:
            result = self.part_nibble
            self.part_nibble = None
        else:
            b = self.one_byte_int()
            result = b >> 4
            self.part_nibble = b & 0xF

        return result

    def read(self, length):
        result = self.f.read(length)
        return result

class Char:

    def __init__(self, source,
            firstbyte = None):
        self.source = source

        self._load(source, firstbyte)

    def _load(self, s, firstbyte=None):

        if firstbyte is not None:
            flags = firstbyte
        else:
            flags = s.one_byte_int()

        black = bool(flags & 0x8)
        dyn_f = flags >> 4
        if dyn_f==14:
            raise ValueError("bitmap")

        preamble_format = flags & 0x7

        if preamble_format<4:
            # Short format

            packet_length = s.one_byte_int()
            self.charcode = s.one_byte_int()
            tfm_width = s.read(3)
            self.dx = 0
            self.dy = s.one_byte_int()
            self.width = s.one_byte_int()
            self.height = s.one_byte_int()
            self.h_offset = s.one_byte_int() # XXX signed
            self.v_offset = s.one_byte_int()

        elif preamble_format<8:
            # Extended short format

            packet_length = s.one_byte_int()
            self.charcode = s.two_byte_int()
            tfm_width = s.read(3)
            self.dx = 0
            self.dy = s.two_byte_int()
            self.width = s.two_byte_int()
            self.height = s.two_byte_int()
            self.h_offset = s.two_byte_int() # XXX signed
            self.v_offset = s.two_byte_int()

        else:
            raise ValueError("long format")

        def no_repeat_repeats(n):
            if n[0]!=0:
                raise ValueError("file contains repeat repeats!")
            return n[1]

        def pk_packed_num():
            """
            returns a tuple: (repeat_count, run_count)
            """
            a = s.one_nibble_int()

            if a==0:
                # large run count

                width = 1
                while True:
                    j = s.one_nibble_int()
                    if j==0:
                        width += 1
                    else:
                        break

                for i in range(width):
                    j <<= 4
                    j |= s.one_nibble_int()

                result = (0,
                        (j-15)+(13-dyn_f)*16+dyn_f,
                        'A',
                        )

            elif a<=dyn_f:
                result = (0, a, 'B')
            elif a==14:
                x1 = pk_packed_num() # s.one_nibble_int()
                x2 = pk_packed_num()
                result = (
                        no_repeat_repeats(x1),
                        no_repeat_repeats(x2),
                        '4'+x1[2]+x2[2],
                        )
            elif a==15:
                x2 = pk_packed_num()

                result = (
                        1,
                        no_repeat_repeats(x2),
                        '5'+x2[2],
                        )
            else:
                r = s.one_nibble_int()
                result = (
                        0,
                        ((a-dyn_f-1) << 4) +\
                        r + dyn_f + 1,
                        'X',
                        )

            return result

        x = y = 0
        line_repeat_count = 0
        self.glyph = []
        line = ''

        while y<self.height:
            repeat_count, run_count, v = pk_packed_num()

            if run_count>1000000:
                raise ValueError("ludicrously huge run count")

            if repeat_count!=0:
                if line_repeat_count!=0:
                    raise ValueError(
                            "repeat count specified twice on the same line")
                line_repeat_count = repeat_count

            for i in range(run_count):
                if black:
                    line += 'X'
                else:
                    line += '.'

                if len(line)>=self.width:
                    self.glyph.extend([line] * (line_repeat_count+1))
                    y += line_repeat_count+1

                    line_repeat_count = 0
                    line = ''

            black = not black

        if y>self.height:
            raise ValueError(
                    "repeat count was too high "
                    f"({y}, needed {self.height})")

    def dump(self):
        print("Charcode:", self.charcode)
        for i, line in enumerate(self.glyph):
            print(" %02d   %s" % (
                    i, line))

class Glyphs:
    def __init__(self, f):
        self.f = f
        self._load()

    def _load(self):
        def _not_a_pk():
            raise ValueError(
                    f"{self.f.name} is not a pk file"
                    )

        pk = _Source(self.f)

        magic = pk.one_byte_int()

        if magic!=PK_PRE:
            _not_a_pk()

        version = pk.one_byte_int()

        if version!=PK_ID:
            _not_a_pk()

        comment_length = pk.one_byte_int()
        self.comment = pk.read(comment_length).decode(
                'ascii',
                )

        self.design_size = pk.four_byte_float()

        checksum = pk.four_byte_int()
        self.pixels_per_point = (
                int(pk.four_byte_float()*POINTS_PER_INCH),
                int(pk.four_byte_float()*POINTS_PER_INCH),
                )

        self.chars = {}

        while True:
            command = pk.one_byte_int()

            if command==PK_XXX1:
                length = pk.one_byte_int()
                contents = pk.read(length)
            elif command==PK_XXX2:
                length = pk.two_byte_int()
                contents = pk.read(length)
            elif command==PK_XXX3:
                length = pk.three_byte_int()
                contents = pk.read(length)
            elif command==PK_XXX4:
                length = pk.four_byte_int()
                contents = pk.read(length)
            elif command==PK_YYY:
                contents = pk.four_byte_int()
            elif command==PK_NO_OP:
                pass
            elif command==PK_POST:
                return
            elif command & 0xF0 == 0xF0:
                raise ValueError("Unexpected command byte")
            else:
                ch = Char(pk, firstbyte=command)
                self.chars[ch.charcode] = ch

    def dump(self):
        for code, ch in sorted(self.chars.items()):
            ch.dump()

def xi_test():
    """
    From Rokicki, 1985, p120
    """

    import io

    xi = (
            b'\x88'
            b'\x1A'
            b'\x04'
            b'\x09\xC7\x1C'
            b'\x19'
            b'\x14'
            b'\x1D'
            b'\xFE'
            b'\x1C'
            b'\xD9\xE2\x97'
            b'\x2B\x1E\x22'
            b'\x93\x24\xE3'
            b'\x97\x4E\x22'
            b'\x93\x2C\x5E'
            b'\x22\x97\xD9'
            )

    with io.BytesIO(xi) as f:
        with _Source(f) as s:
            ch = Char(s)

            found = ch.glyph

            expected = [
                    'XXXXXXXXXXXXXXXXXXXX',
                    'XXXXXXXXXXXXXXXXXXXX',
                    'XXXXXXXXXXXXXXXXXXXX',
                    'XXXXXXXXXXXXXXXXXXXX',
                    'XX................XX',
                    'XX................XX',
                    'XX................XX',
                    '....................',
                    '....................',
                    '..XX............XX..',
                    '..XX............XX..',
                    '..XX............XX..',
                    '..XXXXXXXXXXXXXXXX..',
                    '..XXXXXXXXXXXXXXXX..',
                    '..XXXXXXXXXXXXXXXX..',
                    '..XXXXXXXXXXXXXXXX..',
                    '..XX............XX..',
                    '..XX............XX..',
                    '..XX............XX..',
                    '....................',
                    '....................',
                    '....................',
                    'XX................XX',
                    'XX................XX',
                    'XX................XX',
                    'XXXXXXXXXXXXXXXXXXXX',
                    'XXXXXXXXXXXXXXXXXXXX',
                    'XXXXXXXXXXXXXXXXXXXX',
                    'XXXXXXXXXXXXXXXXXXXX',
                    ]

            print('ok?', found==expected)

if __name__=='__main__':
    f = open('other/cmr10.pk', 'rb')
    font = Font(f)
    font.dump()
