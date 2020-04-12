import struct

import six
from builtins import range
from past.builtins import map

from .. import helpers
from ..constants import LITTLE_ENDIAN
from ..fuzzable import Fuzzable


def binary_string_to_int(binary):
    """
    Convert a binary string to a decimal number.

    @type  binary: str
    @param binary: Binary string

    @rtype:  int
    @return: Converted bit string
    """

    return int(binary, 2)


def int_to_binary_string(number, bit_width):
    """
    Convert a number to a binary string.

    @type  number:    int
    @param number:    (Optional, def=self._value) Number to convert
    @type  bit_width: int
    @param bit_width: (Optional, def=self.width) Width of bit string

    @rtype:  str
    @return: Bit string
    """
    return "".join(map(lambda x: str((number >> x) & 1), range(bit_width - 1, -1, -1)))


class BitField(Fuzzable):
    def __init__(
        self,
        width,
        max_num=None,
        endian=LITTLE_ENDIAN,
        output_format="binary",
        signed=False,
        full_range=False,
    ):
        """
        The bit field primitive represents a number of variable length and is used to define all other integer types.

        @type  width:         int
        @param width:         Width of bit fields
        @type  max_num:       int
        @param max_num:       Maximum number to iterate up to
        @type  endian:        chr
        @param endian:        (Optional, def=LITTLE_ENDIAN) Endianess of the bit field (LITTLE_ENDIAN: <, BIG_ENDIAN: >)
        @type  output_format: str
        @param output_format: (Optional, def=binary) Output format, "binary" or "ascii"
        @type  signed:        bool
        @param signed:        (Optional, def=False) Make size signed vs. unsigned (applicable only with format="ascii")
        @type  full_range:    bool
        @param full_range:    (Optional, def=False) If enabled the field mutates through *all* possible values.
        """

        assert isinstance(width, six.integer_types), "width must be an integer!"

        self.width = width
        self.max_num = max_num
        self.endian = endian
        self.format = output_format
        self.signed = signed
        self.full_range = full_range

        if not self.max_num:
            self.max_num = binary_string_to_int("1" + "0" * width)

        assert isinstance(self.max_num, six.integer_types), "max_num must be an integer!"

    def _iterate_fuzz_lib(self):
        if self.full_range:
            for i in range(0, self.max_num):
                yield i
        else:
            # try only "smart" values.
            interesting_boundaries = [
                0,
                self.max_num // 2,
                self.max_num // 3,
                self.max_num // 4,
                self.max_num // 8,
                self.max_num // 16,
                self.max_num // 32,
                self.max_num,
            ]
            for boundary in interesting_boundaries:
                for v in self._yield_integer_boundaries(boundary):
                    yield v
        # TODO Add a way to inject a list of fuzz values
        # elif isinstance(default_value, (list, tuple)):
        # for val in iter(default_value):
        #    yield val

        # TODO: Add injectable arbitrary bit fields

    def _yield_integer_boundaries(self, integer):
        """
        Add the supplied integer and border cases to the integer fuzz heuristics library.

        @type  integer: int
        @param integer: int to append to fuzz heuristics
        """
        for i in range(-10, 10):
            case = integer + i
            if 0 <= case < self.max_num:
                # some day: if case not in self._user_provided_values
                yield case

    def encode(self, value, mutation_context):
        temp = self._render_int(
            value, output_format=self.format, bit_width=self.width, endian=self.endian, signed=self.signed
        )
        return helpers.str_to_bytes(temp)

    def mutations(self):
        for val in self._iterate_fuzz_lib():
            yield val

    @staticmethod
    def _render_int(value, output_format, bit_width, endian, signed):
        """
        Convert value to a bit or byte string.

        Args:
            value (int): Value to convert to a byte string.
            output_format (str): "binary" or "ascii"
            bit_width (int): Width of output in bits.
            endian: BIG_ENDIAN or LITTLE_ENDIAN
            signed (bool):

        Returns:
            str: value converted to a byte string
        """
        if output_format == "binary":
            bit_stream = ""
            rendered = b""

            # pad the bit stream to the next byte boundary.
            if bit_width % 8 == 0:
                bit_stream += int_to_binary_string(value, bit_width)
            else:
                bit_stream = "0" * (8 - (bit_width % 8))
                bit_stream += int_to_binary_string(value, bit_width)

            # convert the bit stream from a string of bits into raw bytes.
            for i in range(len(bit_stream) // 8):
                chunk_min = 8 * i
                chunk_max = chunk_min + 8
                chunk = bit_stream[chunk_min:chunk_max]
                rendered += struct.pack("B", binary_string_to_int(chunk))

            # if necessary, convert the endianness of the raw bytes.
            if endian == LITTLE_ENDIAN:
                # reverse the bytes
                rendered = rendered[::-1]

            _rendered = rendered
        else:
            # Otherwise we have ascii/something else
            # if the sign flag is raised and we are dealing with a signed integer (first bit is 1).
            if signed and int_to_binary_string(value, bit_width)[0] == "1":
                max_num = binary_string_to_int("1" + "0" * (bit_width - 1))
                # chop off the sign bit.
                val = value & binary_string_to_int("1" * (bit_width - 1))

                # account for the fact that the negative scale works backwards.
                val = max_num - val - 1

                # toss in the negative sign.
                _rendered = "%d" % ~val

            # unsigned integer or positive signed integer.
            else:
                _rendered = "%d" % value
        return _rendered

    def __bool__(self):
        """
        Make sure instances evaluate to True even if __len__ is zero.

        :return: True
        """
        return True
