from grove_lang import *
import builtins
import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

def main():
    print("Welcome to the Grove Interpreter!")
    print("Enter your commands or 'exit' or 'quit' to exit")
    # loop until the command :done is found
    while True:
        s: str = input('> ')
        if (s.strip() == 'exit') or (s.strip() == 'quit'): break
        try:
            x = Command.parse(s).eval()
            if x is not None: print(x)
        except GroveParseError as e:
            print(f"Error Parsing {s}")
            print(e)
        except GroveEvalError as e:
            print(f"error Evaluating {s}")
            print(e)
    print("Goodbye and thank you for using Grove!")

if __name__ == "__main__": main()
    