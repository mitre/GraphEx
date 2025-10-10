from graphex import Number, Boolean, String, Node, NodeType, InputSocket, ListInputSocket, OutputSocket, constants
import typing
import math

class AddNumbers(Node):
    name: str = "Add Numbers"
    description: str = "Add up all input numbers and output the sum."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#numbers"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    input_numbers = ListInputSocket(datatype=Number, name="Numbers", description="The numbers to add up.")

    output = OutputSocket(datatype=Number, name="Result", description="The sum of the input numbers.")

    def run(self):
        self.disable_output_socket("Result")
        sum: float = 0.0
        for num in self.input_numbers:
            sum += num
        if sum.is_integer():
            self.output = int(sum)
        else:
            self.output = sum


class SubtractNumbers(Node):
    name: str = "Subtract Numbers"
    description: str = "Subtract all subtrahend numbers from the minuend numbers and output the difference."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#numbers"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    input_minuend = InputSocket(datatype=Number, name="Minuend", description="The number to subtract values from.")
    input_subtrahends = ListInputSocket(datatype=Number, name="Subtrahends", description="The numbers to subtract from the minuend.")

    output = OutputSocket(datatype=Number, name="Result", description="The difference between the numbers.")

    def run(self):
        self.disable_output_socket("Result")
        minuend: float = float(self.input_minuend)
        for num in self.input_subtrahends:
            minuend -= num
        if minuend.is_integer():
            self.output = int(minuend)
        else:
            self.output = minuend


class MultiplyNumbers(Node):
    name: str = "Multiply Numbers"
    description: str = "Multiply all input numbers and output the result"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#numbers"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    input_numbers = ListInputSocket(datatype=Number, name="Numbers", description="The numbers to multiply together.")

    output = OutputSocket(datatype=Number, name="Result", description="The result of the input numbers multiplied together.")

    def run(self):
        self.disable_output_socket("Result")
        result: float = 1.0
        for num in self.input_numbers:
            result *= num
        if result.is_integer():
            self.output = int(result)
        else:
            self.output = result


class DivideNumbers(Node):
    name: str = "Divide Numbers"
    description: str = "Divide two numbers and output the result. If you divide by zero the result is a NaN (Not a Number) value (type is Number)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#numbers"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    dividend_top = InputSocket(datatype=Number, name="Dividend", description="The number to divide.")
    divisor_bottom = InputSocket(datatype=Number, name="Divisor", description="The number by which to divide the dividend with.", input_field=2)

    output = OutputSocket(datatype=Number, name="Result", description="The result of division.")

    def run(self):
        try:
            result: float = float(self.dividend_top) / self.divisor_bottom
        except ZeroDivisionError:
            self.log_warning(f"Division by zero occured for node 'Divide Numbers'. Dividend: {self.dividend_top} Divisor: {self.divisor_bottom}")
            result = math.nan
        if result.is_integer():
            self.output = int(result)
        else:
            self.output = result


class ExponentNumber(Node):
    name: str = "Raise Number to Power"
    description: str = "Raise a number to the provided power."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#numbers"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    input_number = InputSocket(datatype=Number, name="Base Number", description="The number to exponentialize.")
    power = InputSocket(datatype=Number, name="Exponent", description="The number to apply as the exponent.", input_field=2)

    output = OutputSocket(datatype=Number, name="Result", description="The number after exponentializing.")

    def run(self):
        self.output = self.input_number**self.power


class RootNumber(Node):
    name: str = "Root of Number"
    description: str = "Computes the 'root' of the number. Default operation is 'square root' (2)"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.sqrt", "https://docs.python.org/3/library/math.html#math.pow"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    input_number = InputSocket(datatype=Number, name="Number", description="The number to take the root of.")
    root = InputSocket(
        datatype=Number, name="Root Value", description="The root to apply to the input number ('2' for square root, '3' for cube root, etc.)", input_field=2
    )

    output = OutputSocket(datatype=Number, name="Result", description="The result after taking the root of the number")

    def run(self):
        if not self.root:
            self.output = math.sqrt(self.input_number)
        else:
            self.output = math.pow(self.input_number, (1 / int(self.root)))


class LogOfNumber(Node):
    name: str = "Log of Number"
    description: str = "Calculate the log of a number and output the result (default base 10)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.log"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    input_number = InputSocket(datatype=Number, name="Number", description="The number to take the log of.")
    base = InputSocket(datatype=Number, name="Base", description="The base of the log.", input_field=10)

    output = OutputSocket(datatype=Number, name="Result", description="The log of the number")

    def run(self):
        base: float = self.base if self.base else 10
        self.output = math.log(self.input_number, base)


class NaturalLogOfNumber(Node):
    name: str = "Natural Log (ln) of Number"
    description: str = "Calculate the natural log of a number (base 'e') and output the result."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.log"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    input_number = InputSocket(datatype=Number, name="Number", description="The number to take the natural log of (ln with base e).")

    output = OutputSocket(datatype=Number, name="Result", description="The natural log of the number")

    def run(self):
        self.output = math.log(self.input_number)


class SinOfNumber(Node):
    name: str = "Sin of Number"
    description: str = "Calculate the sin (sine) of a number and output it in radians."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.sin"]
    categories: typing.List[str] = ["Math", "Trigonometry"]
    color: str = constants.COLOR_MATH

    input_number = InputSocket(datatype=Number, name="Number", description="The number to take the sin of.")

    output = OutputSocket(datatype=Number, name="Result", description="The sin of the input number")

    def run(self):
        self.output = math.sin(self.input_number)


class CosOfNumber(Node):
    name: str = "Cos of Number"
    description: str = "Calculate the cos (cosine) of a number and output it in radians."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.cos"]
    categories: typing.List[str] = ["Math", "Trigonometry"]
    color: str = constants.COLOR_MATH

    input_number = InputSocket(datatype=Number, name="Number", description="The number to take the cos of.")

    output = OutputSocket(datatype=Number, name="Result", description="The cos of the input number")

    def run(self):
        self.output = math.cos(self.input_number)


class TanOfNumber(Node):
    name: str = "Tan of Number"
    description: str = "Calculate the tan (tanget) of a number and output it in radians."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.tan"]
    categories: typing.List[str] = ["Math", "Trigonometry"]
    color: str = constants.COLOR_MATH

    input_number = InputSocket(datatype=Number, name="Number", description="The number to take the tan of.")

    output = OutputSocket(datatype=Number, name="Result", description="The tan of the input number")

    def run(self):
        self.output = math.tan(self.input_number)


class Pi(Node):
    node_type = NodeType.GENERATOR
    name: str = "Math Constant: Pi (π)"
    description: str = "The number 'pi' (e.g. 3.141...) with 15 decimal places."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.pi"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    output = OutputSocket(datatype=Number, name="Pi", description="The number Pi with 15 decimal places (e.g. 3.141...)")

    def run(self):
        self.output = math.pi


class ConstantE(Node):
    node_type = NodeType.GENERATOR
    name: str = "Math Constant: e"
    description: str = "Creates the number 'e' (e.g. 2.71...) with 15 decimal places."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.e"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    output = OutputSocket(datatype=Number, name="e", description="The number 'e' (e.g. 2.71...) with 15 decimal places.")

    def run(self):
        self.output = math.e


class InfiniteNumber(Node):
    node_type = NodeType.GENERATOR
    name: str = "Infinity Value"
    description: str = "Creates a value that represents 'infinity'"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.inf"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    output = OutputSocket(datatype=Number, name="Infinity", description="A value that represents 'infinity'")

    def run(self):
        self.output = math.inf


class NotANumber(Node):
    node_type = NodeType.GENERATOR
    name: str = "NaN Value"
    description: str = "Creates a value that represents 'Not a Number' (NaN)"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.nan"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    output = OutputSocket(datatype=Number, name="Nan Value", description="A value that represents NaN")

    def run(self):
        self.output = math.nan


class RoundNumber(Node):
    name: str = "Round Number"
    description: str = "Rounds a number to the provided decimal place."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#round"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    input_value = InputSocket(datatype=Number, name="Number", description="The number to round.")
    rounding_digits = InputSocket(datatype=Number, name="Digits", description="The number of digits to round to.")

    output_value = OutputSocket(datatype=Number, name="Result", description="The rounded number")

    def run(self):
        self.output_value = round(self.input_value, int(self.rounding_digits))


class Factorial(Node):
    name: str = "Factorial"
    description: str = "Calculate the factorial of a number."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.factorial"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    input_value = InputSocket(datatype=Number, name="n", description="The number to apply factorial to.")

    output_value = OutputSocket(datatype=Number, name="Result", description="The product of the factorial.")

    def run(self):
        self.output_value = math.factorial(int(self.input_value))


class Ceiling(Node):
    name: str = "Ceiling of Number"
    description: str = "Calculate the ceiling of a number."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.ceil"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    input_value = InputSocket(datatype=Number, name="Number", description="The number to apply ceiling to.")

    output_value = OutputSocket(datatype=Number, name="Result", description="The ceiling of the number.")

    def run(self):
        self.output_value = math.ceil(self.input_value)


class Floor(Node):
    name: str = "Floor of Number"
    description: str = "Calculate the floor of a number."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.floor"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    input_value = InputSocket(datatype=Number, name="Number", description="The number to apply floor to.")

    output_value = OutputSocket(datatype=Number, name="Result", description="The floor of the number.")

    def run(self):
        self.output_value = math.floor(self.input_value)


class Degrees(Node):
    name: str = "Degree of Number"
    description: str = "Convert a number from radians to degrees."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.degrees"]
    categories: typing.List[str] = ["Math", "Trigonometry"]
    color: str = constants.COLOR_MATH

    input_value = InputSocket(datatype=Number, name="Radians", description="The number in radians.")

    output_value = OutputSocket(datatype=Number, name="Degrees", description="The number in degrees.")

    def run(self):
        self.output_value = math.degrees(self.input_value)


class Radians(Node):
    name: str = "Radians of Number"
    description: str = "Convert a number from degrees to radians."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.radians"]
    categories: typing.List[str] = ["Math", "Trigonometry"]
    color: str = constants.COLOR_MATH

    input_value = InputSocket(datatype=Number, name="Degrees", description="The number in degrees.")

    output_value = OutputSocket(datatype=Number, name="Radians", description="The number in radians.")

    def run(self):
        self.output_value = math.radians(self.input_value)


class NumberIsInf(Node):
    name: str = "Number is Infinite"
    description: str = "Check if a number is infinite (positive or negative)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.isinf"]
    categories: typing.List[str] = ["Math", "Conditionals"]
    color: str = constants.COLOR_MATH

    input_value = InputSocket(datatype=Number, name="Number", description="The number to check.")

    output_value = OutputSocket(datatype=Boolean, name="Result", description="Whether or not the number is infinite")

    def run(self):
        self.output_value = math.isinf(self.input_value)


class NumberIsFinite(Node):
    name: str = "Number is Finite"
    description: str = "Check if a number is finite (not infinite)"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.isfinite"]
    categories: typing.List[str] = ["Math", "Conditionals"]
    color: str = constants.COLOR_MATH

    input_value = InputSocket(datatype=Number, name="Number", description="The number to check.")

    output_value = OutputSocket(datatype=Boolean, name="Result", description="Whether or not the number is finite")

    def run(self):
        self.output_value = math.isfinite(self.input_value)


class ArcSinOfNumber(Node):
    name: str = "Arcsin of Number"
    description: str = "Calculate the arcsin of a number and output it in radians."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.asin"]
    categories: typing.List[str] = ["Math", "Trigonometry"]
    color: str = constants.COLOR_MATH

    input_number = InputSocket(datatype=Number, name="Number", description="The number to take the arcsin of.")

    output = OutputSocket(datatype=Number, name="Result", description="The arcsin of the input number")

    def run(self):
        self.output = math.asin(self.input_number)


class ArcCosOfNumber(Node):
    name: str = "Arccos of Number"
    description: str = "Calculate the arccos of a number and output it in radians."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.acos"]
    categories: typing.List[str] = ["Math", "Trigonometry"]
    color: str = constants.COLOR_MATH

    input_number = InputSocket(datatype=Number, name="Number", description="The number to take the arccos of.")

    output = OutputSocket(datatype=Number, name="Result", description="The arccos of the input number")

    def run(self):
        self.output = math.acos(self.input_number)


class ArcTanOfNumber(Node):
    name: str = "Arctan of Number"
    description: str = "Calculate the arctan of a number and output it in radians."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.atan"]
    categories: typing.List[str] = ["Math", "Trigonometry"]
    color: str = constants.COLOR_MATH

    input_number = InputSocket(datatype=Number, name="Number", description="The number to take the arctan of.")

    output = OutputSocket(datatype=Number, name="Result", description="The arctan of the input number")

    def run(self):
        self.output = math.atan(self.input_number)


class HyberbolicSinOfNumber(Node):
    name: str = "Sinh of Number"
    description: str = "Calculate the hyberbolic sine of a number and output it in radians."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.sinh"]
    categories: typing.List[str] = ["Math", "Trigonometry"]
    color: str = constants.COLOR_MATH

    input_number = InputSocket(datatype=Number, name="Number", description="The number to take the sinh of.")

    output = OutputSocket(datatype=Number, name="Result", description="The sinh of the input number")

    def run(self):
        self.output = math.sinh(self.input_number)


class HyberbolicCosOfNumber(Node):
    name: str = "Cosh of Number"
    description: str = "Calculate the hyberbolic cosine of a number and output it in radians."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.cosh"]
    categories: typing.List[str] = ["Math", "Trigonometry"]
    color: str = constants.COLOR_MATH

    input_number = InputSocket(datatype=Number, name="Number", description="The number to take the cosh of.")

    output = OutputSocket(datatype=Number, name="Result", description="The cosh of the input number")

    def run(self):
        self.output = math.cosh(self.input_number)


class HyberbolicTanOfNumber(Node):
    name: str = "Tanh of Number"
    description: str = "Calculate the hyberbolic tangent of a number and output it in radians."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.tanh"]
    categories: typing.List[str] = ["Math", "Trigonometry"]
    color: str = constants.COLOR_MATH

    input_number = InputSocket(datatype=Number, name="Number", description="The number to take the tanh of.")

    output = OutputSocket(datatype=Number, name="Result", description="The tanh of the input number")

    def run(self):
        self.output = math.tanh(self.input_number)


class NumberIsNan(Node):
    name: str = "Number is NaN value"
    description: str = "Check if a number is 'not a number' (Nan)"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.isnan"]
    categories: typing.List[str] = ["Math", "Conditionals"]
    color: str = constants.COLOR_MATH

    input_value = InputSocket(datatype=Number, name="Number", description="The number to check.")

    output_value = OutputSocket(datatype=Boolean, name="Result", description="Whether or not the number is Nan")

    def run(self):
        self.output_value = math.isnan(self.input_value)


class NumberCombination(Node):
    name: str = "Combination"
    description: str = (
        "Calculate the combination of n and k: n! / (k! * (n-k)!) when k <= n else 0. The number of ways to choose 'k items from n items' without order."
    )
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.comb"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    n = InputSocket(datatype=Number, name="n", description="The n value in the combination formula.")
    k = InputSocket(datatype=Number, name="k", description="The k value in the combination formula.")

    output_value = OutputSocket(datatype=Number, name="Result", description="The output of the combination function.")

    def run(self):
        self.output_value = math.comb(int(self.n), int(self.k))


class NumberPermutation(Node):
    name: str = "Permutation"
    description: str = "Calculate the permutation of n and k: n! / (n-k)! when k <= n else 0. The number of ways to choose 'k items from n items' with order."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/math.html#math.perm"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    n = InputSocket(datatype=Number, name="n", description="The n value in the permutation formula.")
    k = InputSocket(datatype=Number, name="k", description="The k value in the permutation formula.")

    output_value = OutputSocket(datatype=Number, name="Result", description="The output of the permutation function.")

    def run(self):
        self.output_value = math.perm(int(self.n), int(self.k))


class NumberGreaterThan(Node):
    name: str = "Greater Than"
    description: str = "Returns true if Greater Number > Lesser Number"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#value-comparisons"]
    categories: typing.List[str] = ["Math", "Conditionals"]
    color: str = constants.COLOR_MATH

    greater_value = InputSocket(datatype=Number, name="Greater Number", description="The number to assert is greater.")
    lesser_value = InputSocket(datatype=Number, name="Lesser Number", description="The number to assert is lesser.")

    output_value = OutputSocket(datatype=Boolean, name="Result", description="The result of the conditional operation.")

    def run(self):
        self.output_value = self.greater_value > self.lesser_value


class NumberGreaterThanEqual(Node):
    name: str = "Greater Than or Equal To"
    description: str = "Returns true if Greater Number >= Lesser Number"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#value-comparisons"]
    categories: typing.List[str] = ["Math", "Conditionals"]
    color: str = constants.COLOR_MATH

    greater_value = InputSocket(datatype=Number, name="Greater Number", description="The number to assert is greater.")
    lesser_value = InputSocket(datatype=Number, name="Lesser Number", description="The number to assert is lesser.")

    output_value = OutputSocket(datatype=Boolean, name="Result", description="The result of the conditional operation.")

    def run(self):
        self.output_value = self.greater_value >= self.lesser_value


class NumberLessThan(Node):
    name: str = "Less Than"
    description: str = "Returns true if lesser number < greater number"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#value-comparisons"]
    categories: typing.List[str] = ["Math", "Conditionals"]
    color: str = constants.COLOR_MATH

    lesser_value = InputSocket(datatype=Number, name="Lesser Number", description="The number to assert is lesser.")
    greater_value = InputSocket(datatype=Number, name="Greater Number", description="The number to assert is greater.")

    output_value = OutputSocket(datatype=Boolean, name="Result", description="The result of the conditional operation.")

    def run(self):
        self.output_value = self.lesser_value < self.greater_value


class NumberLessThanEqual(Node):
    name: str = "Less Than or Equal to"
    description: str = "Returns true if lesser number <= greater number"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#value-comparisons"]
    categories: typing.List[str] = ["Math", "Conditionals"]
    color: str = constants.COLOR_MATH

    lesser_value = InputSocket(datatype=Number, name="Lesser Number", description="The number to assert is lesser.")
    greater_value = InputSocket(datatype=Number, name="Greater Number", description="The number to assert is greater.")

    output_value = OutputSocket(datatype=Boolean, name="Result", description="The result of the conditional operation.")

    def run(self):
        self.output_value = self.lesser_value <= self.greater_value


class NumberEqual(Node):
    name: str = "Equal (Number)"
    description: str = "Returns true if Number 1 == Number 2"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#value-comparisons"]
    categories: typing.List[str] = ["Math", "Conditionals"]
    color: str = constants.COLOR_MATH

    value_1 = InputSocket(datatype=Number, name="Number 1", description="The first number to compare.")
    value_2 = InputSocket(datatype=Number, name="Number 2", description="The second number to compare.")

    output_value = OutputSocket(datatype=Boolean, name="Result", description="The result of the conditional operation.")

    def run(self):
        self.output_value = self.value_1 == self.value_2


class NumberNotEqual(Node):
    name: str = "Not Equal (Number)"
    description: str = "Returns true if Number 1 != Number 2"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#value-comparisons"]
    categories: typing.List[str] = ["Math", "Conditionals"]
    color: str = constants.COLOR_MATH

    value_1 = InputSocket(datatype=Number, name="Number 1", description="The first number to compare.")
    value_2 = InputSocket(datatype=Number, name="Number 2", description="The second number to compare.")

    output_value = OutputSocket(datatype=Boolean, name="Result", description="The result of the conditional operation.")

    def run(self):
        self.output_value = self.value_1 != self.value_2


class AbsoluteNumber(Node):
    name: str = "Absolute Value of Number"
    description: str = "Returns the positive (absolute) value of a number."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#abs"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    input_num = InputSocket(datatype=Number, name="Number", description="The number to take the absolute value of.")

    result = OutputSocket(datatype=Number, name="Absolute Value", description="The positive value of the number.")

    def run(self):
        self.result = abs(self.input_num)


class DivModNumber(Node):
    name: str = "DivMod Number"
    description: str = "Outputs the quotient and remainder after division."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#divmod"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    dividend_top = InputSocket(datatype=Number, name="Dividend", description="The number to divide.")
    divisor_bottom = InputSocket(datatype=Number, name="Divisor", description="The number by which to divide the dividend with.", input_field=2)

    output_q = OutputSocket(datatype=Number, name="Quotient", description="The result of division.")
    output_r = OutputSocket(datatype=Number, name="Remainder", description="The remander from division.")

    def run(self):
        try:
            t = divmod(self.dividend_top, self.divisor_bottom)
        except ZeroDivisionError:
            self.log_warning(f"Division by zero occured for node 'DivMod Number'. Dividend: {self.dividend_top} Divisor: {self.divisor_bottom}")
            self.output_q = math.nan
            self.output_r = math.nan
            return
        self.output_q = t[0]
        self.output_r = t[1]


class ModuloNumber(Node):
    name: str = "Modulo"
    description: str = "Outputs the modulo (remainder) after division."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#numbers"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    dividend_top = InputSocket(datatype=Number, name="Dividend", description="The number to divide.")
    divisor_bottom = InputSocket(datatype=Number, name="Divisor", description="The number by which to divide the dividend with.", input_field=2)

    output = OutputSocket(datatype=Number, name="Remainder", description="The remander from division.")

    def run(self):
        try:
            self.output = self.dividend_top % self.divisor_bottom
        except ZeroDivisionError:
            self.log_warning(f"Division by zero occured for node 'Modulo'. Dividend: {self.dividend_top} Divisor: {self.divisor_bottom}")
            self.output = math.nan


class MaxNumber(Node):
    name: str = "Max Number"
    description: str = "Outputs the Maximum number provided from all input values."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#max"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    input_numbers = ListInputSocket(datatype=Number, name="Numbers", description="The numbers to search for a max from.")

    result = OutputSocket(datatype=Number, name="Max Number", description="The largest number provided")

    def run(self):
        self.disable_output_socket("Max Number")
        if len(self.input_numbers):
            self.result = max(self.input_numbers)


class MinNumber(Node):
    name: str = "Min Number"
    description: str = "Outputs the Minimum number provided from all input values."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#min"]
    categories: typing.List[str] = ["Math"]
    color: str = constants.COLOR_MATH

    input_numbers = ListInputSocket(datatype=Number, name="Numbers", description="The numbers to search for a min from.")

    result = OutputSocket(datatype=Number, name="Min Number", description="The smallest number provided")

    def run(self):
        self.disable_output_socket("Min Number")
        if len(self.input_numbers):
            self.result = min(self.input_numbers)


class IntegerToOctalString(Node):
    name: str = "Number to Octal String"
    description: str = "Truncates a number into an integer and then outputs the octal string representation of that number."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#oct"]
    categories: typing.List[str] = ["Math", "Other Bases"]
    color: str = constants.COLOR_MATH

    input_integer = InputSocket(datatype=Number, name="Integer", description="The integer to get an octal representation of.")

    output_octal = OutputSocket(datatype=String, name="Octal String", description="The octal number represented as a string.")

    def run(self):
        self.output_octal = oct(int(self.input_integer))


class OctalStringToInteger(Node):
    name: str = "Octal String to Number"
    description: str = "Converts a previously stored octal string back into a normal number."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#oct"]
    categories: typing.List[str] = ["Math", "Other Bases"]
    color: str = constants.COLOR_MATH

    input_octal = InputSocket(datatype=String, name="Octal String", description="The octal number represented as a string.")

    output_integer = OutputSocket(datatype=Number, name="Integer", description="The integer to get an octal representation of.")

    def run(self):
        try:
            self.output_integer = int(self.input_octal, 0)
        except Exception as e:
            self.log_error(f"Exception converting from Octal String to Integer: {str(e)} ... Ensure string is an octal number (e.g. 0o7)")
            self.output_integer = math.nan


class IntegerToHexString(Node):
    name: str = "Number to Hexadecimal String"
    description: str = "Truncates a number into an integer and then outputs the hexidecimal string representation of that number."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#hex"]
    categories: typing.List[str] = ["Math", "Other Bases"]
    color: str = constants.COLOR_MATH

    input_integer = InputSocket(datatype=Number, name="Integer", description="The integer to get a hexidecimal representation of.")

    output_octal = OutputSocket(datatype=String, name="Hex String", description="The hex number represented as a string.")

    def run(self):
        self.output_octal = hex(int(self.input_integer))


class HexidecimalStringToInteger(Node):
    name: str = "Hexidecimal String to Number"
    description: str = "Converts a previously stored Hexidecimal string back into a normal number."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#hex"]
    categories: typing.List[str] = ["Math", "Other Bases"]
    color: str = constants.COLOR_MATH

    input_hex = InputSocket(datatype=String, name="Hexidecimal String", description="The Hexidecimal number represented as a string.")

    output_integer = OutputSocket(datatype=Number, name="Integer", description="The integer to get an Hexidecimal representation of.")

    def run(self):
        try:
            self.output_integer = int(self.input_hex, 0)
        except Exception as e:
            self.log_error(f"Exception converting from Hexidecimal String to Integer: {str(e)} ... Ensure string is a hexidecimal number (e.g. 0x1e)")
            self.output_integer = math.nan


class IntegerToBinaryString(Node):
    name: str = "Number to Binary String"
    description: str = "Truncates a number into an integer and then outputs the binary string representation of that number."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#bin"]
    categories: typing.List[str] = ["Math", "Other Bases"]
    color: str = constants.COLOR_MATH

    input_integer = InputSocket(datatype=Number, name="Integer", description="The integer to get an binary representation of.")

    output_binary = OutputSocket(datatype=String, name="Binary String", description="The binary number represented as a string.")

    def run(self):
        self.output_binary = bin(int(self.input_integer))


class BinaryStringToInteger(Node):
    name: str = "Binary String to Number"
    description: str = "Converts a previously stored binary string back into a normal number."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#bin"]
    categories: typing.List[str] = ["Math", "Other Bases"]
    color: str = constants.COLOR_MATH

    input_binary = InputSocket(datatype=String, name="Binary String", description="The binary number represented as a string.")

    output_integer = OutputSocket(datatype=Number, name="Integer", description="The integer to get an binary representation of.")

    def run(self):
        try:
            self.output_integer = int(self.input_binary, 0)
        except Exception as e:
            self.log_error(f"Exception converting from Binary String to Integer: {str(e)} ... Ensure string is an binary number (e.g. 0b1)")
            self.output_integer = math.nan


class BitwiseAnd(Node):
    name: str = "Bitwise And"
    description: str = "Assigns the bit 1 anywhere that both bits were 1. Else assigns the bit 0. Truncates floating point values into integers."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#unary-arithmetic-and-bitwise-operations"]
    categories: typing.List[str] = ["Math", "Bitwise"]
    color: str = constants.COLOR_MATH

    input_1 = InputSocket(datatype=Number, name="Integer 1", description="The first number to compare.")
    input_2 = InputSocket(datatype=Number, name="Integer 2", description="The second number to compare.")

    output = OutputSocket(datatype=Number, name="Result", description="The result of the Bitwise operation.")

    def run(self):
        self.output = int(self.input_1) & int(self.input_2)


class BitwiseOr(Node):
    name: str = "Bitwise Or"
    description: str = "Assigns the bit 1 anywhere that either bits were 1. Else assigns the bit 0. Truncates floating point values into integers."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#unary-arithmetic-and-bitwise-operations"]
    categories: typing.List[str] = ["Math", "Bitwise"]
    color: str = constants.COLOR_MATH

    input_1 = InputSocket(datatype=Number, name="Integer 1", description="The first number to compare.")
    input_2 = InputSocket(datatype=Number, name="Integer 2", description="The second number to compare.")

    output = OutputSocket(datatype=Number, name="Result", description="The result of the Bitwise operation.")

    def run(self):
        self.output = int(self.input_1) | int(self.input_2)


class BitwiseNot(Node):
    name: str = "Bitwise Not / Invert"
    description: str = "Flips all bits that are 0 to 1 and all bits that are 1 to 0. This operation also affects the bit that determines positive/negative. Truncates floating point values into integers."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#unary-arithmetic-and-bitwise-operations"]
    categories: typing.List[str] = ["Math", "Bitwise"]
    color: str = constants.COLOR_MATH

    input_1 = InputSocket(datatype=Number, name="Integer", description="The number to flip the bits on.")

    output = OutputSocket(datatype=Number, name="Result", description="The result of the Bitwise operation.")

    def run(self):
        self.output = ~int(self.input_1)


class BitwiseXor(Node):
    name: str = "Bitwise Exclusive Or (xor)"
    description: str = "Assigns the bit 1 anywhere that the values of the bits are different (e.g. Int_1 has 0, Int_2 has 1). Else assigns the bit 0. Truncates floating point values into integers."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#unary-arithmetic-and-bitwise-operations"]
    categories: typing.List[str] = ["Math", "Bitwise"]
    color: str = constants.COLOR_MATH

    input_1 = InputSocket(datatype=Number, name="Integer 1", description="The first number to compare.")
    input_2 = InputSocket(datatype=Number, name="Integer 2", description="The second number to compare.")

    output = OutputSocket(datatype=Number, name="Result", description="The result of the Bitwise operation.")

    def run(self):
        self.output = int(self.input_1) ^ int(self.input_2)


class BitwiseLeftShift(Node):
    name: str = "Bitwise (<<) Left Shift"
    description: str = "Shifts an integer 'x' to the left by 'n' bits (x << n). Truncates floating point values into integers."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#unary-arithmetic-and-bitwise-operations"]
    categories: typing.List[str] = ["Math", "Bitwise"]
    color: str = constants.COLOR_MATH

    input_1 = InputSocket(datatype=Number, name="Integer (x)", description="The number to shift.")
    n_bits = InputSocket(datatype=Number, name="Number of Bits (n)", description="The number of bits to shift by.")

    output = OutputSocket(datatype=Number, name="Result", description="The result of the Bitwise operation.")

    def run(self):
        self.output = int(self.input_1) << int(self.n_bits)


class BitwiseRightShift(Node):
    name: str = "Bitwise (>>) Right Shift"
    description: str = "Shifts an integer 'x' to the right by 'n' bits (x >> n). Truncates floating point values into integers."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#unary-arithmetic-and-bitwise-operations"]
    categories: typing.List[str] = ["Math", "Bitwise"]
    color: str = constants.COLOR_MATH

    input_1 = InputSocket(datatype=Number, name="Integer (x)", description="The number to shift.")
    n_bits = InputSocket(datatype=Number, name="Number of Bits (n)", description="The number of bits to shift by.")

    output = OutputSocket(datatype=Number, name="Result", description="The result of the Bitwise operation.")

    def run(self):
        self.output = int(self.input_1) >> int(self.n_bits)


class NumberBitLength(Node):
    name: str = "Number Length in Bits"
    description: str = "Outputs how many binary bits are needed to represent this number in binary (base 2)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#int.bit_length"]
    categories: typing.List[str] = ["Math", "Bitwise"]
    color: str = constants.COLOR_MATH

    input_1 = InputSocket(datatype=Number, name="Integer", description="The number to count the bits on.")

    output = OutputSocket(datatype=Number, name="Result", description="The number of bits in the number.")

    def run(self):
        self.output = int(self.input_1).bit_length()


class NumberBitCount(Node):
    name: str = "(Number) Bit (Population) Count"
    description: str = "Outputs the number of ones in binary representation of the absolute value of the integer."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#int.bit_count"]
    categories: typing.List[str] = ["Math", "Bitwise"]
    color: str = constants.COLOR_MATH

    input_1 = InputSocket(datatype=Number, name="Integer", description="The number to count the bits on.")

    output = OutputSocket(datatype=Number, name="Result", description="The number of populated bits in the number.")

    def run(self):
        # this function doesn't exist until python 3.10 (manually implemented here)
        self.output = bin(int(self.input_1)).count("1")
