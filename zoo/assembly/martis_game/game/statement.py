import re
import numpy as np

from my_types import Opcode, Index, Increment, Label

class Statement:
    INDENT_COUNT = 4
    INDENT = " " * INDENT_COUNT

    def __init__(self, line: str):
        self.line = line.strip()
        self.opcode_mnemonic = Opcode()
        self.destination_index = Index()
        self.source_index1 = Index()
        self.source_index2 = Index()
        self.increment = Increment()
        self.label = None
        self.immediate_value = 0.000
        self.cursor_position = 0
        self.parse_from_file()

    def parse_from_file(self):
        # Regex patterns to match different operations
        self.patterns = {
            'scalar_assign': re.compile(r's(\d+)\s*=\s*(-?\d+(\.\d+)?)'),
            'dot_product': re.compile(r's(\d+)\s*=\s*dot\(v(\d+),\s*v(\d+)\)'),
            'subtraction': re.compile(r's(\d+)\s*=\s*s(\d+)\s*-\s*s(\d+)'),
            'multiplication': re.compile(r's(\d+)\s*=\s*s(\d+)\s*\*\s*s(\d+)'),
            'vector_scalar_mult': re.compile(r'v(\d+)\s*=\s*v(\d+)\s*\*\s*s(\d+)'),
            'vector_add': re.compile(r'v(\d+)\s*=\s*v(\d+)\s*\+\s*v(\d+)'),
            'section_label': re.compile(r'(Setup|Predict|Learn)'),
        }
        self.opcode_mnemonic_map = {
            "scalar_assign": "let",
            "dot_product": "dot",
            "subtraction": "sub",
            "multiplication": "mul",
            "vector_scalar_mult": "muv",
            "vector_add": "add",
            "section_label": "label",
        }
        

        # Attempt to match each pattern and parse tokens
        for key, pattern in self.patterns.items():
            match = pattern.search(self.line)
            if match:
                self.operation = key
                try:
                    self.tokens = [int(x) if x.isdigit() else float(x) for x in match.groups()]
                except:
                    # label
                    self.tokens = [match.group(1)]
                if self.operation == "section_label":
                    self.label = self.tokens[0]
                    if self.label not in Label.LABELS:
                        raise ValueError(f"Invalid label '{self.label}'")
                elif self.operation == "scalar_assign":
                    self.opcode_mnemonic.set("let")
                    self.destination_index.set(self.tokens[0])
                    self.immediate_value = self.tokens[1]
                else:
                    self.opcode_mnemonic.set(self.opcode_mnemonic_map[self.operation])
                    self.destination_index.set(self.tokens[0])
                    self.source_index1.set(self.tokens[1])
                    self.source_index2.set(self.tokens[2])
                self.tokens = None # force exception if referenced subsequently
                break
        else:
            raise ValueError(f"Invalid statement: >>{self.line}<<")

    def serialize_for_file(self):
        # Serialize tokens back into a string using the operation format
        if self.operation == 'scalar_assign':
            return f'{self.INDENT}s{self.destination_index} = {self.roundtrip_floating_point():.3f}'
        elif self.operation == 'dot_product':
            return f'{self.INDENT}s{self.destination_index} = dot(v{self.source_index1}, v{self.source_index2})'
        elif self.operation in ['subtraction', 'multiplication']:
            op = '-' if self.operation == 'subtraction' else '*'
            return f'{self.INDENT}s{self.destination_index} = s{self.source_index1} {op} s{self.source_index2}'
        elif self.operation == 'vector_scalar_mult':
            return f'{self.INDENT}v{self.destination_index} = v{self.source_index1} * s{self.source_index2}'
        elif self.operation == 'vector_add':
            return f'{self.INDENT}v{self.destination_index} = v{self.source_index1} + v{self.source_index2}'
        elif self.operation == 'section_label':
            return f'def {self.label}():'
        return self.line

    def serialize_for_display(self):
        if self.label is not None:
            return f'label {self.label}:'
        elif str(self.opcode_mnemonic) == 'let':
            return f'let {self.destination_index} {self.immediate_value:.3f}'
        else:
            return f'{self.opcode_mnemonic.current()} {self.destination_index} {self.source_index1} {self.source_index2}'

    def decode_floating_point(self, encoded: int) -> float:
        # Very special cases
        if encoded == 0:
            return 0.0
        elif encoded == 1:
            return 0.001

        sign_bit = encoded >> 7
        biased_exponent = (encoded >> 3) & 0b1111
        exponent = biased_exponent - 10  # Reversing the bias

        scaled_mantissa = encoded & 0b111
        mantissa = (scaled_mantissa / 8.0) + 1  # Reverting scale

        number = (mantissa * (2 ** exponent)) * (-1 if sign_bit else 1)
        return number

    def encode_floating_point(self, number: float = None, debug: bool = False) -> int:
        """
        Encode a floating point value in eight (8) bits, in an encoding that is similar to IEEE 754 floating point encoding.
        """
        if number is None:
            number = self.immediate_value
        # Very special cases
        if number == 0:
            return 0
        elif number == 0.001:
            return 1

        sign_bit = 1 if number < 0 else 0
        abs_number = abs(number)

        # if not 0.001 < abs(number) <= 10:
        #     raise ValueError(f"Number out of range: {number}.")
        abs_number = max(0.001, min(10, abs_number))

        # XXX Handle corner cases our encoding fails at
        # For these intervals we would get ~50% error, because the encoding fails
        if 0.48 < abs_number < 0.52 or 1.93 < abs_number < 2.23 or 7.75 < abs_number < 8:
            candidate1 = abs_number * 0.95
            candidate2 = abs_number * 1.04
            abs_number = candidate1 if abs(candidate1 - abs_number) < abs(candidate2 - abs_number) else candidate2

        exponent = int(np.floor(np.log2(abs_number)))
        exponent_bias = 10  # Adjusting bias to support the range
        biased_exponent = exponent + exponent_bias
        biased_exponent = min(0b1111, biased_exponent) # clip to 4 bits

        mantissa = (abs_number / (2 ** exponent)) - 1
        scaled_mantissa = round(mantissa * 8)  # Scale for 3-bit mantissa
        scaled_mantissa = min(0b111, scaled_mantissa)  # clip to 3 bits (this is a no-op, unless we have a bug somewhere)

        if debug:
            print(f"sign_bit: {sign_bit}, biased_exponent: {biased_exponent}, scaled_mantissa: {scaled_mantissa}")
            print(f"sign_bit: {bin(sign_bit)}, biased_exponent: {bin(biased_exponent)}, scaled_mantissa: {bin(scaled_mantissa)}")
        encoded = (sign_bit << 7) | (biased_exponent << 3) | scaled_mantissa
        return encoded

    def roundtrip_floating_point(self, number: float = None, **kwargs):
        """
        Round-trip a floating point number through the encoding and decoding functions.
        """
        if "error" in kwargs:
            only_error = kwargs["error"]
        else:
            only_error = False

        if number is None:
            number = self.immediate_value
        encoded = self.encode_floating_point(number)
        decoded = self.decode_floating_point(encoded)
        if only_error:
            if number == 0:
                # Division by zero
                return 0
            else:
                return (abs(decoded) - abs(number)) / abs(number)
        else:
            return decoded

    def serialize_one_hot(self, cursor=False):
        """Encode the full statement as a one-hot vector. The encoding uses 62 bits + 2 bits of padding. The encoding is as follows:
        
        bits | description
        -----|------------
         6   | opcode / label
         3   | label type (Setup, Predict, Learn)
         1   | cursor
        10   | destination index
         1   | cursor
        10   | source index 1
         1   | cursor
        10   | source index 2
         1   | cursor
         8   | immediate value (for opcode 'let')
        10   | increment (for opcode 'let')
         2   | padding (unused)
        """
        WORD = 64 # bits
        def one_hot(width: int, value: int) -> list[int]:
            return [1 if i == value else 0 for i in range(width)]

        if self.label is not None:
            enc = ([1] if cursor else [0]) + \
                one_hot(6, 5) + (
                [0, 0, 1] if self.label == "Setup" else
                [0, 1, 0] if self.label == "Predict" else
                [1, 0, 0] if self.label == "Learn" else
                [0, 0, 0] # Invalid
            ) + [0] * (WORD - (1 + 6 + 3))
        elif self.opcode_mnemonic.current() == 'let':
            # encode the constant as an array of eight bits
            constant = self.encode_floating_point()
            try:
                constant = [int(x) for x in bin(constant)[2:].zfill(8)]
            except:
                raise ValueError(f"Invalid constant {constant} for opcode 'let': bin(constant): {bin(constant)}, self.immediate_value: {self.immediate_value}, statement: {self.serialize_for_file()}")
            enc = ([1] if cursor and self.cursor_position == 0 else [0]) \
                 + one_hot(6, 0) \
                 + [0] * 3 \
                 + ([1] if cursor and self.cursor_position == 1 else [0]) \
                 + one_hot(10, self.destination_index.current()) \
                 + [0] * 11 \
                 + [0] * 11 \
                 + ([1] if cursor and self.cursor_position == 2 else [0]) \
                 + constant \
                 + one_hot(len(Increment.VALUES), Increment.VALUES.index(self.increment.current())) \
                 + [0] * (WORD - (1 + 6 + 3 + (1+10)*3 + (1 + 8 + 10)))
        else:
            enc = ([1] if cursor and self.cursor_position == 0 else [0]) \
                 + one_hot(6, Opcode.MNEMONICS.index(self.opcode_mnemonic.current())) \
                 + [0] * 3 \
                 + ([1] if cursor and self.cursor_position == 1 else [0]) \
                 + one_hot(10, self.destination_index.current()) \
                 + ([1] if cursor and self.cursor_position == 2 else [0]) \
                 + one_hot(10, self.source_index1.current()) \
                 + ([1] if cursor and self.cursor_position == 3 else [0]) \
                 + one_hot(10, self.source_index2.current()) \
                 + [0] * (WORD - (1 + 6 + 3 + (1+10)*3))
        
        return enc

    def get_cursor_display_column(self):
        """Return the display column corresponding to the current cursor position. Because our mnemonic is always 3 characters long, and our exceptions (label and let) can only take a cursor position 0 and [0, 1] respectively, we can do this uniformly for every operation."""
        # label Label:
        # ^----------- cursor position
        # mne 1 2 3
        # ^---^-^-^--- cursor positions
        # let 0.000
        # ^---^------- cursor positions
        return 0 if self.cursor_position == 0 else len("mne")-1 + len(" 1") * self.cursor_position

    def increment_token(self):
        # Increment the value of the current token, with wrapping if needed
        if self.label is not None:
            return
        elif self.cursor_position == 0:
            next(self.opcode_mnemonic)
        elif self.cursor_position == 1:
            next(self.destination_index)
        else:
            if self.opcode_mnemonic.current() == 'let':
                if self.cursor_position == 2:
                    new_value = self.immediate_value + self.increment.current()
                    new_sign = 1 if new_value >= 0 else -1
                    abs_new_value = abs(new_value)
                    if new_value == 0:
                        pass
                    elif abs_new_value < 0.001:
                        abs_new_value = 0.001
                    elif abs_new_value > 10:
                        abs_new_value = 10
                    # For certain values, the encoding error is very large for some values, certainly larger than the smaller increment, which is why we don't use self.roundtrip_floating_point() here
                    self.immediate_value = new_sign * abs_new_value
                else:
                    raise RuntimeError(f"Invalid cursor position {self.cursor_position} for opcode 'let'")
            else:
                if self.cursor_position == 2:
                    next(self.source_index1)
                elif self.cursor_position == 3:
                    next(self.source_index2)
                else:
                    raise RuntimeError(f"Invalid cursor position {self.cursor_position} for opcode '{self.opcode_mnemonic.current()}'")
        self.redraw()
    
    def redraw(self):
        pass

    def decrement_token(self):
        raise NotImplementedError("Decrementing tokens is not supported")

    def move_cursor_right(self):
        # Move the cursor to the right, wrapping around
        if self.label is not None or \
                (self.opcode_mnemonic.current() == 'let' and self.cursor_position == 2) or \
                self.cursor_position == 3:
            # Move to the next statement
            raise NextStatementException(self)
        else:
            self.cursor_position += 1
        self.redraw()

    def move_cursor_left(self):
        raise NotImplementedError("Moving the cursor left is not supported")
    
    def change_increment(self):
        next(self.increment)
    
    def reset_token(self):
        # Not implemented
        pass


class NextStatementException(Exception):
    def __init__(self, statement: Statement):
        self.statement = statement
        super().__init__(f"Statement is finished: {statement.serialize_for_file()}")