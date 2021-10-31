from collections import deque
from typing import Iterable, List
import math
import re
import numpy as np
from discord.ext import commands


constants = {
    'pi': math.pi,
    'π': math.pi,
    'e': math.e,
    '∞': math.inf
}

operators = {
    '+': {'precedence': 1, 'associativity': 'left', 'function': lambda x, y: x + y, 'arguments': 2},
    '-': {'precedence': 1, 'associativity': 'left', 'function': lambda x, y: x - y, 'arguments': 2},
    '*': {'precedence': 2, 'associativity': 'left', 'function': lambda x, y: x * y, 'arguments': 2},
    'x': {'precedence': 2, 'associativity': 'left', 'function': lambda x, y: x * y, 'arguments': 2},
    '/': {'precedence': 2, 'associativity': 'left', 'function': lambda x, y: x / y, 'arguments': 2},
    '÷': {'precedence': 2, 'associativity': 'left', 'function': lambda x, y: x / y, 'arguments': 2},
    '^': {'precedence': 3, 'associativity': 'right', 'function': lambda x, y: x ** y, 'arguments': 2},
    '√': {'precedence': 3, 'associativity': 'right', 'function': math.sqrt, 'arguments': 1},
    '!': {'precedence': 0, 'associativity': 'right', 'function': math.factorial, 'arguments': 1}
    # factorial is to be immediately moved to output stack, precedence does not matter
}


radians = False
functions = {
    'sqrt': {'function': math.sqrt, 'arguments': 1},
    'log': {'function': math.log, 'arguments': 2},
    # accept 2 params x and n, num x and base n, where it becomes log n(x)
    'log10': {'function': math.log10, 'arguments': 1},  # log10
    'ln': {'function': lambda x: math.log(x, math.e), 'arguments': 1},  # natural log

    # trigonometry functions
    'sin': {'function': lambda x: math.sin(x if radians else math.radians(x)), 'arguments': 1},
    'sinh': {'function': lambda x: math.sinh(x if radians else math.radians(x)), 'arguments': 1},
    'asin': {'function': lambda x: math.asin(x if radians else math.radians(x)), 'arguments': 1},
    'arcsin': {'function': lambda x: math.asin(x if radians else math.radians(x)), 'arguments': 1},
    'asinh': {'function': lambda x: math.asinh(x if radians else math.radians(x)), 'arguments': 1},
    'cos': {'function': lambda x: math.cos(x if radians else math.radians(x)), 'arguments': 1},
    'cosh': {'function': lambda x: math.cosh(x if radians else math.radians(x)), 'arguments': 1},
    'acos': {'function': lambda x: math.acos(x if radians else math.radians(x)), 'arguments': 1},
    'arccos': {'function': lambda x: math.acos(x if radians else math.radians(x)), 'arguments': 1},
    'acosh': {'function': lambda x: math.acosh(x if radians else math.radians(x)), 'arguments': 1},
    'tan': {'function': lambda x: math.tan(x if radians else math.radians(x)), 'arguments': 1},
    'tanh': {'function': lambda x: math.tanh(x if radians else math.radians(x)), 'arguments': 1},
    'atan': {'function': lambda x: math.atan(x if radians else math.radians(x)), 'arguments': 1},
    'arctan': {'function': lambda x: math.atan(x if radians else math.radians(x)), 'arguments': 1},
    'atanh': {'function': lambda x: math.atanh(x if radians else math.radians(x)), 'arguments': 1},

    'ceil': {'function': math.ceil, 'arguments': 1},
    'floor': {'function': math.floor, 'arguments': 1}
}


# Shunting Yard Algorithm
def rpn_parser(expression: str) -> deque:
    output_stack = deque()
    operator_stack = deque()
    last: str = ''
    for literal, op in re.findall(r'(-?\d+\.?\d*)|([a-zA-Z]+|[+\-*x/÷()^√!]|[⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+)', expression):  # splitting equation regex
        match literal, op:
            case _, '':  # matches number
                if literal.startswith('-'):  # handling negative numbers
                    if re.match(r'(\d+)(?:\.\d+)?', last):  # if the last token is a number
                        # while (op_stack is not empty) AND
                        # 1 <- "subtraction sign precedence" is the smaller or same precedence than the top value
                        #       of op_stack
                        while len(operator_stack) != 0:
                            if 1 <= operators[operator_stack[-1]]['precedence']:
                                output_stack.append(
                                    operator_stack.pop())  # pop and append the top value to output_stack
                            else:
                                break
                        # separating the negative symbol from literal
                        operator_stack.append('-')
                        literal = literal.strip('-')  # removing the negative sign as it isn't a negative number
                try:
                    output_stack.append(int(literal))
                except ValueError:
                    output_stack.append(float(literal))
            case '', _:  # matches operators
                match op:
                    case literal if op in constants.keys():  # constants
                        output_stack.append(constants[literal])
                    case func if op in functions.keys():  # matches functions
                        operator_stack.append(func)  # moved to output stack
                    case ('+' | '-' | '*' | 'x' | '/' | '÷' | '^' | '√'):  # matches most common operators
                        # while (op_stack is not empty) AND
                        # (op is lower precedence than the top value of op_stack) OR
                        # (op is same precedence than the top value of op_stack AND op is left associative)
                        try:
                            while len(operator_stack) != 0:
                                if operators[op]['precedence'] < operators[operator_stack[-1]]['precedence'] or \
                                        (operators[op]['precedence'] == operators[operator_stack[-1]]['precedence'] and
                                         operators[op]['associativity'] == 'left'):
                                    output_stack.append(
                                        operator_stack.pop())  # pop and append the top value to output_stack
                                else:
                                    break
                        except KeyError:  # probably just '(' or ')'
                            pass
                        operator_stack.append(op)  # append 'op' to stack
                    case sup if re.match('[⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+', op):  # superscript characters
                        operator_stack.append('^')
                        num = ''
                        for number in sup:
                            match number:
                                case '⁻':
                                    num += '-'
                                case '⁰':
                                    num += '0'
                                case '¹':
                                    num += '1'
                                case '²':
                                    num += '2'
                                case '³':
                                    num += '3'
                                case '⁴':
                                    num += '4'
                                case '⁵':
                                    num += '5'
                                case '⁶':
                                    num += '6'
                                case '⁷':
                                    num += '7'
                                case '⁸':
                                    num += '8'
                                case '⁹':
                                    num += '9'
                        try:
                            output_stack.append(int(num))
                        except ValueError:
                            output_stack.append(float(num))
                    case '!':  # special case where factorial doesn't care about precedence
                        output_stack.append(op)
                    case '(':
                        if re.match(r'(-?\d+\.?\d*)', last):  # append an additional '*' for cases like '2(4)'
                            operator_stack.append('*')
                        operator_stack.append(op)  # append '(' to stack
                    case ')':
                        # while the 'top value from the op_stack' isn't '('
                        while operator_stack[-1] != '(':
                            output_stack.append(operator_stack.pop())  # pop and append the top value to output_stack
                        operator_stack.pop()  # pop the top '(' and discard it
                        if len(operator_stack) != 0 and operator_stack[-1] in functions.keys():  # if the top value of op_stack is a function, pop it into output_stack
                            output_stack.append(operator_stack.pop())
                    case _:
                        raise SyntaxError('unknown operator')
            case _:  # error
                raise SyntaxError('unknown operator')
        if op not in ('(', ')'):
            last = literal or op
    for _ in range(len(operator_stack)):  # for the remaining tokens in the op_stack
        output_stack.append(operator_stack.pop())  # pop everything to output_stack
    return output_stack


def rpn_eval(stack: Iterable) -> int | float:
    number_stack = deque()
    for token in stack:
        match token:
            case (int() | float()):  # put number into stack for later evaluation
                number_stack.append(token)
            case str() as op:  # do evaluation
                values = [number_stack.pop() for _ in
                          range((operators | functions)[op]['arguments'])]  # pop the amount of arguments needed for the function
                number_stack.append(
                    (operators | functions)[op]['function'](*reversed(values)))  # reversing as its popped top to bottom
            case _:
                raise SyntaxError('unknown operator')
    return number_stack[0]


def linear_system_parser(equations: str) -> np.ndarray:
    pass


class NoSolution(ValueError):
    pass


def gaussian_elimination(matrix: np.ndarray) -> List[np.float64]:
    """
    Compute a matrix of a linear system to return the value of each terms with gaussian elimination

    Args:
        matrix <numpy.ndarray>: a matrix of a linear system

    Returns:
        a size of List[numpy.float64] equal to the number of rows corresponding to each terms from x1 to xn

    Raises:
        NoSolution: no solution can be returned, usually its because the determinant is 0
    """
    # [x1, y1, z1, ..., n1]
    # [x2, y2, z2, ..., n2]
    # [x3, y3, z3, ..., n3]
    # [..  ..  ..  ..., ..]
    # [xn, yn, zn, ..., nn]
    for n_row in range(0, len(matrix)):  # up to down
        # Rn / Rn[n] -> Rn
        # Rn+1 - Rn * Rn[n] -> Rn+1
        if matrix[n_row][n_row] == 0:  # if n_row th term coefficient is 0
            # search other rows to swap row with
            for n_other_row in range(n_row+1, len(matrix)):
                if matrix[n_other_row][n_row] != 0:
                    matrix[[n_row, n_other_row]] = matrix[[n_other_row, n_row]]  # swap row
                    break
            else:
                continue
        matrix[n_row] /= matrix[n_row][n_row]  # turn the current row n_row th term coefficient into 1
        for n_other_row in range(n_row+1, len(matrix)):  # every row down except for the current one
            matrix[n_other_row] -= matrix[n_row] * matrix[n_other_row][n_row]  # scale up the n_row value use it to subtract the rows below
    # Echelon form
    # [x1, y1, z1, ..., n1]
    # [0 , y2, z2, ..., n2]
    # [0 , 0 , z3, ..., n3]
    # [..  ..  ..  ..., ..]
    # [       0       , nn]
    det = math.prod(matrix[n][n] for n in range(0, len(matrix)))
    if det == 0:
        raise NoSolution('Determinant is 0')
    for n_row in range(1, len(matrix)):  # down to up
        # R-(n+1) - R-n * R-(n+1)[-n]
        for n_other_row in range(1+n_row, len(matrix)+1):  # every row up except for the current one
            # remove all the other terms, is like the one above but in reverse
            matrix[-n_other_row] -= matrix[-n_row] * matrix[-n_other_row][-(n_row+1)]
    return matrix[...,len(matrix[0])-1]


class Math(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def math(self, ctx, *, msg):
        """All things math"""

        if not ctx.invoked_subcommand:
            await ctx.invoke(self.evaluate, expression=msg)

    @math.command(aliases=['eval'])
    async def evaluate(self, ctx, *, expression):
        """
        Do math, shows answer only for now

        Currently only supporting
        - addition
        - subtraction
        - multiplication
        - division
        - exponentiation
        - parenthesis
        """

        stack = rpn_parser(expression)
        result = rpn_eval(stack)
        await ctx.reply(str(round(result, 12)))

    @math.command()
    async def toggle_radians(self, ctx):
        global radians
        radians = False if radians else True
        await ctx.reply(f'Radians mode toggled {"on" if radians else "off"}')


def setup(bot):
    bot.add_cog(Math(bot))


if __name__ == '__main__':
    ...
    print(rpn_eval(rpn_parser(input())))
