from __future__ import annotations
from abc import ABCMeta, abstractmethod
from typing import Any, Union

# create a context where variables stored with set are kept
context: dict[str,int] = {}

# add a "verbose" flag to print all parse exceptions while debugging
verbose = False

# define base classes for Language exceptions for ParsingExceptions
class CalcException(Exception): pass
class CalcParseException(CalcException): pass
class CalcEvalException(CalcException): pass

# define a base class for Commands
class Command(metaclass=ABCMeta):
    @abstractmethod
    def __init__(self): pass
    @abstractmethod
    def eval(self) -> Union[int,None]: pass
    @staticmethod
    def parse(s: str) -> Command:
        """Factory method for creating Command subclasses from lines of code"""
        tokens: list[str] = s.strip().split()
        try:
            # first try to pase this command as a statement
            return Statement.parse(tokens)
        except CalcParseException as e:
            if verbose: print(e)
        
        try:
            # if it is not a statement it must be an expression
            return Expression.parse(tokens)
        except CalcParseException as e:
            if verbose: print(e)
            
        raise CalcParseException(f"Unrecognized Command: {s}")
            
# define a base class for Expressions
class Expression(Command, metaclass=ABCMeta):
    @abstractmethod
    def __init__(self): pass
    @abstractmethod
    def eval(self) -> int: pass
    @classmethod
    def parse(cls, tokens: list[str]) -> Expression:
        """Factory method for creating Expression subclasses from tokens"""
        subclasses: list[type[Expression]] = cls.__subclasses__()
        for subclass in subclasses:
            try:
                return subclass.parse(tokens)
            except CalcParseException as e:
                if verbose: print(e)
        raise CalcParseException(f"Unrecognized Expression: {' '.join(tokens)}")
    @staticmethod
    def match_parens(tokens: list[str]) -> int:
        """Searches tokens beginning with ( and returns index of matching )"""
        # ensure tokens is such that a matching ) might exist
        if len(tokens) < 2: raise CalcParseException("Expression too short")
        if tokens[0] != '(': raise CalcParseException("No opening ( found")
        # track the depth of nested ()
        depth: int = 0
        for i,token in enumerate(tokens):
            # when a ( is found, increase the depth
            if token == '(': depth += 1
            # when a ) is found, decrease the depth
            elif token == ')': depth -= 1
            # if after a token the depth reaches 0, return that index
            if depth == 0: return i
        # if the depth never again reached 0 then parens do not match
        raise CalcParseException("No closing ) found")

# define a base class for Statements
class Statement(Command, metaclass=ABCMeta):
    @abstractmethod
    def __init__(self): pass
    @abstractmethod
    def eval(self) -> None: pass
    @staticmethod
    def parse(tokens: list[str]) -> Statement:
        """Factory method for creating Statement subclasses from tokens"""
        # Only valid statement is set
        return Set.parse(tokens)

# define a class to represent the "set" statement
class Set(Statement):
    def __init__(self, name: Name, value: Expression): # Set command has access to either side of the =
        self.name = name
        self.value = value
    def eval(self) -> None: # Set the expression in context dic to the right name
        context[self.name.name] = self.value.eval()
    def __eq__(self, other: Any): # Set statements being equal; same parse tree
        return (isinstance(other, Set) and 
                self.name == other.name and self.value == other.value)
    @staticmethod
    def parse(tokens: list[str]) -> Set:
        """Factory method for creating Set commands from tokens"""
        # Make sure there are enough tokens
        if len(tokens) < 4:
            raise CalcParseException("Statement is too short for Set")
        # 1 Make sure first token is set
        if tokens[0] != 'set':
            raise CalcParseException("Set statements must begin with 'set'")
        # 2 Make sure next token is a valid name
        try:
            name: Name = Name.parse([tokens[1]])
        except CalcParseException as e:
            raise CalcParseException("No name found for Set statement")
        # 3 Make sure the next token is an '='
        if tokens[2] != '=':
            raise CalcParseException("Set statement requires '='")
        # 4 Ensure remaining tokens represent an expression
        try:
            # Taking tokens from 3 on as an expression
            value: Expression = Expression.parse(tokens[3:])    
        except CalcParseException:
            raise CalcParseException("No valuse found for Set statement")
        # If this point is reached, this is a valid Set command
        return Set(name, value)

# define an expression for the addition operation
class Add(Expression):
    def __init__(self, first: Expression, second: Expression):
        self.first = first
        self.second = second
    def eval(self) -> int: # Add the integer values together
        return self.first.eval() + self.second.eval()
    def __eq__(self, other) -> bool:
        return (isinstance(other, Add) and
                self.first == other.first and self.second == other.second)
    @staticmethod
    def parse(tokens: list[str]) -> Add:
        """Factory method for creating Add expressions from tokens"""
        s = ' '.join(tokens)
        if len(tokens) < 7:
            raise CalcParseException(f"Not enough tokens for Add in {s}")
        if tokens[0] != '+' or tokens[1] != '(':
            raise CalcParseException(f"Add must begin with '+ (' in {s}")
        # Make sure the next token(s) represent an expression
        try:
            cut = Expression.match_parens(tokens[1:]) + 1
            first: Expression = Expression.parse(tokens[2:cut])
        except CalcParseException as e:
            raise CalcParseException(f"Unable to find first addend in {s}")
        # Make sure that there are enough tokens left after first expression
        tokens = tokens[cut + 1:]
        if len(tokens) < 3:
            raise CalcParseException(f"Not enough tokens for Add in {s}")
        # Make sure that remaining tokens begin and end with ()
        if tokens[0] != '(' or tokens[-1] != ')':
            raise CalcParseException(f"Addneds must be wrapped in (): {s}")
        # Make sure that the stuff in the middle is a valid expression
        try:
            second: Expression = Expression.parse(tokens[1:-1])
        except CalcParseException as e:
            raise CalcParseException(f"Unable to find the second addend in {s}")
        # POINT REACHED MEANS VALID ADD EXPRESSION
        return Add(first, second)

# define an expression for the subtraction operation
class Subtract(Expression):
    def __init__(self, first: Expression, second: Expression):
        self.first = first
        self.second = second
    def eval(self) -> int: # Subtract the integer values together
        return self.first.eval() - self.second.eval()
    def __eq__(self, other) -> bool:
        return (isinstance(other, Subtract) and
                self.first == other.first and self.second == other.second)
    @staticmethod
    def parse(tokens: list[str]) -> Subtract:
        """Factory method for creating Subtract expressions from tokens"""
        s = ' '.join(tokens)
        if len(tokens) < 7:
            raise CalcParseException(f"Not enough tokens for Subtract in {s}")
        if tokens[0] != '-' or tokens[1] != '(':
            raise CalcParseException(f"Add must begin with '- (' in {s}")
        # Make sure the next token(s) represent an expression
        try:
            cut = Expression.match_parens(tokens[1:]) + 1
            first: Expression = Expression.parse(tokens[2:cut])
        except CalcParseException as e:
            raise CalcParseException(f"Unable to find first minuend in {s}")
        # Make sure that there are enough tokens left after first expression
        tokens = tokens[cut + 1:]
        if len(tokens) < 3:
            raise CalcParseException(f"Not enough tokens for Subtract in {s}")
        # Make sure that remaining tokens begin and end with ()
        if tokens[0] != '(' or tokens[-1] != ')':
            raise CalcParseException(f"Subtrahends must be wrapped in (): {s}")
        # Make sure that the stuff in the middle is a valid expression
        try:
            second: Expression = Expression.parse(tokens[1:-1])
        except CalcParseException as e:
            raise CalcParseException(f"Unable to find the second subtrahend in {s}")
        # POINT REACHED MEANS VALID SUBTRACT EXPRESSION
        return Subtract(first, second)

# define an expression for an integer constant
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
            raise CalcParseException(f"Wrong number of tokens ({len(tokens)}) for number")
        # Ensure that the tokens are numbers
        if not tokens[0].isdigit():
            raise CalcParseException("Numbers can contain only digits")
        return Number(int(tokens[0]))

# define an expression for a variable name
class Name(Expression):
    def __init__(self, name: str):
        self.name = name # Sets the name value
    def eval(self) -> int:
        if self.name in context: # If there is a variable under that name return it
            return context[self.name] 
        else: # If there is no variable under that name then error
            raise CalcEvalException(f"{self.name} is undefined")
    def __eq__(self, other: Any) -> bool: # Reference Equality
        return (isinstance(other, Name) and other.name == self.name)
    @staticmethod
    def parse(tokens: list[str]) -> Name:
        """Factory method for creating Name expressions from tokens"""
        if len(tokens) != 1:
            raise CalcParseException("Wrong number of tokens for Name")
        if not tokens[0].isalpha():
            raise CalcParseException("Names can contain letters")
        return Name(tokens[0])
        