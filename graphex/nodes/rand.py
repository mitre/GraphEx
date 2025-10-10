from graphex import Number, String, Node, InputSocket, OutputSocket, constants
import typing
import random
 

class RandomInt(Node):
    name: str = "Random Integer"
    description: str = (
        "Outputs a random integer from the provided range (a <= R <= b; where R represents the Random number). The 'randomness' is based on the seed."
    )
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/random.html#random.randint"]
    categories: typing.List[str] = ["Miscellaneous", "Random"]
    color = constants.COLOR_RANDOM

    lowest_possible_a = InputSocket(datatype=Number, name="Lowest Possible Int (a)", description="The lowest possible random value.")
    highest_possible_b = InputSocket(datatype=Number, name="Highest Possible Int (b)", description="The highest possible random value.", input_field=10)
    seed = InputSocket(datatype=String, name="Seed", description="A value to 'seed' the random number on (if empty, the system time will be used).")

    result = OutputSocket(datatype=Number, name="Random Integer", description="A random integer in the specified range.")

    def run(self):
        s = self.seed if self.seed.strip() else None
        random.seed(s)
        self.result = random.randint(int(self.lowest_possible_a), int(self.highest_possible_b))


class RandomFloat(Node):
    name: str = "Random Float (Uniform)"
    description: str = "Outputs a random float (number with decimal points) from the provided range (a <= R <= b; where R represents the Random number). The 'randomness' is based on the seed."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/random.html#random.uniform"]
    categories: typing.List[str] = ["Miscellaneous", "Random"]
    color = constants.COLOR_RANDOM

    lowest_possible_a = InputSocket(datatype=Number, name="Lowest Possible Float (a)", description="The lowest possible random value.")
    highest_possible_b = InputSocket(datatype=Number, name="Highest Possible Float (b)", description="The highest possible random value.", input_field=1)
    seed = InputSocket(datatype=String, name="Seed", description="A value to 'seed' the random number on (if empty, the system time will be used).")

    result = OutputSocket(datatype=Number, name="Random Float", description="A random float in the specified range.")

    def run(self):
        s = self.seed if self.seed.strip() else None
        random.seed(s)
        self.result = random.uniform(self.lowest_possible_a, self.highest_possible_b)
