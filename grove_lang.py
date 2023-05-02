from __future__ import annotations
## Parse tree nodes for the Grove language
import re
import sys
import importlib
import builtins
from abc import ABCMeta, abstractmethod
from typing import Any, Union

# The exception classes from the notes.
class GroveError(Exception): pass
class GroveParseError(GroveError): pass
class GroveEvalError(GroveError): pass

context: dict[str,object] = {}

# Command Base Class (superclass of expressions and statements)
class Command(object):
    pass

# Expression Base Class (superclass of Num, Name, StringLiteral, etc.)
class Expression(Command):
    pass

# Statement Base Class (superclass of Assign, Terminate, and Import)
class Statement(Command):
    pass

# -----------------------------------------------------------------------------
# Implement each of the following parse tree nodes for the Grove language
# -----------------------------------------------------------------------------

class Number(Expression):
    def __init__(self, num: int):
        self.num = num # Sets the number value
    def eval(self) -> int:
        return self.num # Returns what number it is
    def __eq__(self, other: Any) -> bool: # Reference Equality
        return (isinstance(other, Number) and other.num == self.num) # Returns if two ints are the same
    @staticmethod
    def parse(tokens: list[str]) -> Number:
        """Factory method for creating Number expressions from tokens"""
        # Ensure that there are enough tokens for a number
        if len(tokens) != 1:
            raise GroveParseError(f"Wrong number of tokens ({len(tokens)}) for number")
        # Ensure that the tokens are numbers
        if not tokens[0].isdigit():
            raise GroveParseError("Numbers can contain only digits")
        return Number(int(tokens[0]))

class StringLiteral(Expression):
    def __init__(self, string: str):
        self.string = string # Sets the string value
    def eval(self) -> int:
        return self.string # Return the string that is present
    def __eq__(self, other: Any) -> bool: # Reference Equality
        return (isinstance(other, StringLiteral) and other.string == self.string)
    @staticmethod
    def parse(tokens: list[str]) -> StringLiteral:
        """Factory method for creating string expressions from tokens"""
        if len(tokens) != 1:
            raise GroveParseError("Wrong number of tokens for string")
        
        return StringLiteral(tokens[0])

class Object(Expression):
    def __init__(self, targetObject: object):
        self.object = targetObject
    def eval(self) -> object:
        return self.object; 
    def __eq__(self, o) -> bool:
        return self.object.__eq__(o) 
    @staticmethod
    def parse(tokens: list[str]) -> Object:
        """Factory method for creating object expression from tokens"""
        s = ' '.join(tokens)
        
        if len(tokens) != 1:
            raise GroveParseError(f"Wrong amount of tokens for parsing object: '{s}'")
        for string in globals(): #https://stackoverflow.com/questions/1176136/convert-string-to-python-class-object
            if type(getattr(sys.modules[__name__], string)) == object:
                return Object(getattr(sys.modules[__name__], string))
            # if is an object that can be called, then create object
                # Object(Object())
            # if callable(getattr(element, function)
        # builtins.__dict__
        # gloabls()
        raise GroveParseError(f"Couldn't find the object '{s}' in modules")
    
class Call(Expression):
    def __init__(self, ref, method, *args):
        self.ref = ref
        self.method = method
        self.args = args
    
    def eval(self) -> Any:
        try:
            return getattr(context[self.ref], self.method)(*self.args)
        except Exception as e:
            className = str(type(context[self.ref])).split("'")[1]
            raise GroveEvalError(f"Incorrect number of parameters for {className}.{self.method}(), ({len(self.args)} given)")

    # TODO: Implement node for "call" expression
    @staticmethod
    def parse(tokens: list[str]) -> Call:
        """Factory method for creating call expressions from tokens"""
        if len(tokens) < 6: # check for correct number of tokens
            raise GroveParseError(f"Wrong number of tokens ({len(tokens)}) for Call")
        if tokens[0] != "call": # make sure we start with call keyword
            raise GroveParseError(f"Expected 'call' but found {tokens[0]}")
        if tokens[1] != "(": # make sure expression after call starts and ends with parentheses
            raise GroveParseError(f"Expected '(' but found {tokens[1]}")
        if tokens[-1] != ")":
            raise GroveParseError(f"Expected ')' but found {tokens[-1]}")
        if tokens[2] not in context.keys(): # make sure the object being called on is defined already
            raise GroveParseError(f"Object '{tokens[2]}' not defined in context")
        if tokens[3] not in dir(context[tokens[2]]): # make sure the object has the attribute trying to be called
            raise GroveParseError(f"'{tokens[3]}' not defined for objects of type {type(context[tokens[2]])}")
        if not callable(getattr(context[tokens[2]], tokens[3])): # makes sure the attribute is callable
            raise GroveParseError(f"Attribute '{tokens[3]}' is not callable for objects of type {type(context[tokens[2]])}")
        ref = tokens[2]
        method = tokens[3]
        args = (arg for arg in tokens[4:-2])
        return Call(ref, method, *args)
        
class Addition(Expression):
    def __init__(self, first: Expression, second: Expression):
        self.first = first
        self.second = second
    def eval(self) -> int: # Add the integer values together
        self.first.eval() + self.second.eval()
    def __eq__(self, other) -> bool:
        return (isinstance(other, Addition) and
                self.first == other.first and self.second == other.second)
    @staticmethod
    def parse(tokens: list[str]) -> Addition:
        """Factory method for creating Addition expressions from tokens"""
        s = ' '.join(tokens)
        if len(tokens) < 7:
            raise GroveParseError(f"Not enough tokens for Addition in {s}")
        if tokens[0] != '+' or tokens[1] != '(':
            raise GroveParseError(f"Addition must begin with '+ (' in {s}")
        # Make sure the next token(s) represent an expression
        try:
            cut = Expression.match_parens(tokens[1:]) + 1
            first: Expression = Expression.parse(tokens[2:cut])
        except GroveParseError as e:
            raise GroveParseError(f"Unable to find first Additionend in {s}")
        # Make sure that there are enough tokens left after first expression
        tokens = tokens[cut + 1:]
        if len(tokens) < 3:
            raise GroveParseError(f"Not enough tokens for Addition in {s}")
        # Make sure that remaining tokens begin and end with ()
        if tokens[0] != '(' or tokens[-1] != ')':
            raise GroveParseError(f"Additionneds must be wrapped in (): {s}")
        # Make sure that the stuff in the middle is a valid expression
        try:
            second: Expression = Expression.parse(tokens[1:-1])
        except GroveParseError as e:
            raise GroveParseError(f"Unable to find the second Additionend in {s}")
        # POINT REACHED MEANS VALID Addition EXPRESSION
        return Addition(first, second)

class Name(Expression):
    def __init__(self, name: str):
        self.name = name # Sets the name value
    def eval(self) -> int:
        if self.name in context: # If there is a variable under that name return it
            return context[self.name] 
        else: # If there is no variable under that name then error
            raise GroveEvalError(f"{self.name} is undefined")
    def __eq__(self, other: Any) -> bool: # Reference Equality
        return (isinstance(other, Name) and other.name == self.name)
    @staticmethod
    def parse(tokens: list[str]) -> Name:
        """Factory method for creating Name expressions from tokens"""
        if len(tokens) != 1:
            raise GroveParseError("Wrong number of tokens for Name")
        if not tokens[0][0].isalpha():
            raise GroveParseError("Name must start with alpha")
        if [i.isalpha() or i == "_" for i in tokens[0]].count(False) == 0:
            raise GroveParseError("Names can contain letters")
        return Name(tokens[0])

class Assignment(Statement):
    def __init__(self, name: Name, value: Expression): # Assignment command has access to either side of the =
        self.name = name
        self.value = value
    def eval(self) -> None: # Assignment the expression in context dic to the right name
        context[self.name.name] = self.value.eval()
    def __eq__(self, other: Any): # Assignment statements being equal; same parse tree
        return (isinstance(other, Assignment) and 
                self.name == other.name and self.value == other.value)
    @staticmethod
    def parse(tokens: list[str]) -> Assignment:
        """Factory method for creating Assignment commands from tokens"""
        # Make sure there are enough tokens
        if len(tokens) < 4:
            raise GroveParseError("Statement is too short for Assignment")
        # 1 Make sure first token is Assignment
        if tokens[0] != 'set':
            raise GroveParseError("Assignment statements must begin with 'Assignment'")
        # 2 Make sure next token is a valid name
        try:
            name: Name = Name.parse([tokens[1]])
        except GroveParseError as e:
            raise GroveParseError("No name found for Assignment statement")
        # 3 Make sure the next token is an '='
        if tokens[2] != '=':
            raise GroveParseError("Assignment statement requires '='")
        # 4 Ensure remaining tokens represent an expression
        try:
            # Taking tokens from 3 on as an expression
            value: Expression = Expression.parse(tokens[3:])    
        except GroveParseError:
            raise GroveParseError("No valuse found for Assignment statement")
        # If this point is reached, this is a valid Assignment command
        return Assignment(name, value)

class Import(Expression):
    # TODO: Implement node for "import" statements
    pass

class Terminate(Expression):
	# Implement node for "quit" and "exit" statements
    def eval(self) -> None: 
        sys.exit()
    @staticmethod
    def parse(tokens: list[str]):
        # make sure there is only 1 token
        if len(tokens) > 1:
            raise GroveParseError("Statement is too long for Terminate")
         # Make sure token is either 'exit' or 'quit'
        if tokens[0] != 'quit' and tokens[0] != 'exit':
            raise GroveParseError("Terminate statement must be either 'quit' or 'exit'")
        return Terminate(tokens[0])
