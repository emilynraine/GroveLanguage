from grove_lang import *
import builtins
import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

def main():
    # loop until the command :done is found
    while True:
        s: str = input('')
        # s: str = input('Grove>>')
        if (s.strip() == 'exit') or (s.strip() == 'quit'): break
        try:
            cmd = Command.parse(s).eval()
            if cmd is not None: print(cmd)
        except GroveParseError as e:
            print(f"Error Parsing {s}")
            print(e)
        except GroveEvalError as e:
            print(f"error Evaluating {s}")
            print(e)

if __name__ == "__main__": main()
    