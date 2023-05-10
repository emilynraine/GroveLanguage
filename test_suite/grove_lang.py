from __future__ import annotations
## Parse tree nodes for the Grove language
import re
import sys
import importlib
import builtins
from abc import ABCMeta, abstractmethod
from typing import Any, Union

# add a "verbose" flag to print all parse exceptions while debugging
verbose = False

# The exception classes from the notes.
class GroveError(Exception): pass
class GroveParseError(GroveError): pass
class GroveEvalError(GroveError): pass

# context: dict[str,object] = {} #Make this globals()
globals()

# Command Base Class (superclass of expressions and statements)
class Command(object):
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
        except GroveParseError as e:
            if verbose: print(e)
        
        try:
            # if it is not a statement it must be an expression
            return Expression.parse(tokens)
        except GroveParseError as e:
            if verbose: print(e)
            
        raise GroveParseError(f"Unrecognized Command: {s}")

# Expression Base Class (superclass of Num, Name, StringLiteral, etc.)
class Expression(Command):
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
            except GroveParseError as e:
                if verbose: print(e)
        raise GroveParseError(f"Unrecognized Expression: {' '.join(tokens)}")
    @staticmethod
    def match_parens(tokens: list[str]) -> int:
        """Searches tokens beginning with ( and returns index of matching )"""
        # ensure tokens is such that a matching ) might exist
        if len(tokens) < 2: raise GroveParseError("Expression too short")
        if tokens[0] != '(': raise GroveParseError("No opening ( found")
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
        raise GroveParseError("No closing ) found")

# Statement Base Class (superclass of Assign, Terminate, and Import)
class Statement(Command):
    @abstractmethod
    def __init__(self): pass
    @abstractmethod
    def eval(self) -> None: pass
    @staticmethod
    def parse(tokens: list[str]) -> Statement:
        """Factory method for creating Statement subclasses from tokens"""
        # Only valid statement is Assignment, Terminate, or Import
        try:
            # try to parse as assignment
            return Assignment.parse(tokens)
        except GroveParseError as e:
            if verbose: print(e)
        try:
            # try to parse as terminate
            return Terminate.parse(tokens)
        except GroveParseError as e:
            if verbose: print(e)
            
        try:
            # try to parse as import
            return Import.parse(tokens)
        except GroveParseError as e:
            if verbose: print(e)
                
        raise GroveParseError(f"Unrecognized Command on tokens: {tokens}")

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
        if tokens[0][0] != '"' or tokens[0][len(tokens) - 1] != '"':
            raise GroveParseError("Needs quotes on the sides")
        
        return StringLiteral(tokens[0][1:(len(tokens)-2)])

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
        
        if len(tokens) != 2:
            raise GroveParseError(f"Wrong amount of tokens for parsing object: '{s}'")
        if tokens[0] != "new":
            raise GroveParseError(f"Did not find 'new' instead found {tokens[0]}")
        
        # Look for burried Object "aka. something seperated by a ."
        pieces = tokens[1].split(".")
        if pieces[0] in globals():
            if len(pieces) == 1:
                return Object(globals()[pieces[0]])
            else:
                if type(globals()[pieces[0]]) == dict:
                    if pieces[1] in globals()[pieces[0]]:
                        return Object(globals()[pieces[0]][pieces[1]]()) # The orgional way that worked for test 5
                else:
                    index = dir(globals()[pieces[0]]).index(pieces[1]) # attempting to handle the import
                    return Object(dir(globals()[pieces[0]])[index])
                
        raise GroveParseError(f"Couldn't find the object '{s}' in modules")
    
class Call(Expression):
    def __init__(self, ref: Name, method: Name, args: list[Expression]):
        self.ref = ref
        self.method = method
        self.args = args

    def eval(self) -> Any:
        try:
            self.ref.eval()
        except:
            raise GroveEvalError(f"{self.ref.name} not defined in scope.")
        if self.method not in dir(self.ref.eval()):
            raise GroveEvalError(f"{self.method} not defined for {self.ref.name}")
        if not callable(getattr(self.ref.eval(), self.method)):
            raise GroveEvalError(f"{self.method} not callable on {self.ref.name}")
        try:
            return getattr(self.ref.eval(), self.method)(*[arg.eval() for arg in self.args])
        except:
            raise GroveParseError(f"incorrect number of parameters for {self.method} ({len(self.args)} given)")
        

    @staticmethod
    def parse(tokens: list[str]) -> Call:
        """Factory method for creating call expressions from tokens"""
        if len(tokens) < 5: # check for correct number of tokens
            raise GroveParseError(f"Wrong number of tokens ({len(tokens)}) for Call")
        if tokens[0] != "call": # make sure we start with call keyword
            raise GroveParseError(f"Expected 'call' but found {tokens[0]}")
        if tokens[1] != "(": # make sure expression after call starts and ends with parentheses
            raise GroveParseError(f"Expected '(' but found {tokens[1]}")
        if tokens[-1] != ")":
            raise GroveParseError(f"Expected ')' but found {tokens[-1]}")
        ref: Name = Name.parse(tokens[2:3])
        method: str = tokens[3]
        paramTokens = tokens[4:-1]
        print(paramTokens)
        args: list[Expression] = []
        #while paramTokens:
        for i in range(len(paramTokens) + 1):
            try:
                args.append(Expression.parse(paramTokens[0:i]))
                paramTokens = paramTokens[i:] # may cause problems for i if there is multiple occurances
            except:
                pass
        return Call(ref, method, args)
        
class Addition(Expression):
    def __init__(self, first: Expression, second: Expression):
        self.first = first
        self.second = second
    def eval(self) -> int: # Add the integer values together
        return self.first.eval() + self.second.eval()
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
        if self.name in globals(): # If there is a variable under that name return it
            return globals()[self.name] 
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
        if not tokens[0].replace("_", "").isalnum():
            raise GroveParseError("Names can contain letters")
        if tokens[0] == "call":
            raise GroveParseError(f"call is a protected word and not a valid name for your variable")
        return Name(tokens[0])

class Assignment(Statement):
    def __init__(self, name: Name, value: Expression): # Assignment command has access to either side of the =
        self.name = name
        self.value = value
    def eval(self) -> None: # Assignment the expression in globals dic to the right name
        globals()[self.name.name] = self.value.eval()
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
    # Implement node for "import" statements
    def __init__(self, mod):
        self.mod = mod
    def eval(self):
        #theoretically this should be adding the module to the globals dictionary
        globals()[self.mod] = importlib.import_module(self.mod)
        # self.mod.__name__ = importlib.import_module(self.mod)
    @staticmethod 
    def parse(tokens: list[str]):
        if len(tokens) != 2:
            raise GroveParseError("Statement is wrong length for Import")
        #check if first word is import
        if tokens[0] != "import":
            raise GroveParseError("First token did not equal 'import'")
        # try:
        #     mod:Expression = tokens[1]
        # except:
        #     raise GroveParseError("No value found for module in import statement")
        
        return Import(tokens[1])


class Terminate(Expression):
	# Implement node for "quit" and "exit" statements
    def __init__(self, term:Expression) -> None:
        self.term = term
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
        try:
            term:Expression = tokens[0]
        except:
            raise GroveParseError("No values found in terminate statement")
        return Terminate(term)
