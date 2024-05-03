class WraparoundIterator:
    def __init__(self, data):
        if len(data) == 0:
            raise ValueError("empty data -- data must have at least one member")
        self.data = data
        self.index = 0

    def __next__(self):
        if not self.data:
            raise StopIteration
        self.index = (self.index + 1) % len(self.data)
        item = self.data[self.index]
        return item

    def __iter__(self):
        return self
    
    def __str__(self):
        return str(self.current())

    def current(self):
        if not self.data:
            raise StopIteration
        return self.data[self.index]
    
    def set(self, value):
        if value not in self.data:
            raise ValueError(f"value >>{value}<< not in data {self.data}")
        while self.current() != value:
            next(self)


def test1():
    """Example of using the WraparoundIterator with the current method"""
    data = [1, 2, 3]
    iterator = WraparoundIterator(data)
    print(iterator.current())  # Prints the current item without moving to the next
    print(next(iterator))  # Moves to the first item and prints it
    print(iterator.current())  # Prints the current item without moving to the next

MAX_INDEX = 9 # single-digit only

class Opcode(WraparoundIterator):
    MNEMONICS = ["let", "add", "dot", "sub", "mul", "muv"]
    def __init__(self):
        super().__init__(self.MNEMONICS)

class Index(WraparoundIterator):
    def __init__(self):
        super().__init__([i for i in range(MAX_INDEX + 1)])

class Increment(WraparoundIterator):
    VALUES = [-10.000, -1.000, -0.100, -0.010, -0.001,
                0.001,  0.010,  0.100,  1.000, 10.000]
    def __init__(self):
        super().__init__(self.VALUES)

class Label():
    LABELS = ["Setup", "Predict", "Learn"] 

def test2():
    """Example of using the Opcode, Index, and Increment classes"""
    opcode = Opcode()
    index = Index()
    increment = Increment()

    print(opcode.current())  # Prints the current opcode
    print(next(opcode))  # Moves to the next opcode and prints it
    print(opcode.current())  # Prints the current opcode
    print(index.current())  # Prints the current index
    print(next(index))  # Moves to the next index and prints it
    print(index.current())  # Prints the current index
    print(increment.current())  # Prints the current increment
    print(next(increment))  # Moves to the next increment and prints it
    print(increment.current())  # Prints the current increment
    print(next(increment))  # Moves to the next increment and prints it

    # Resetting the iterators to the initial state
    opcode = Opcode()
    index = Index()
    increment = Increment()

    for i in range(20):
        print(i, "opcode:", next(opcode), "index:", next(index), "increment:", next(increment))


if __name__ == "__main__":
    test1()
    test2()