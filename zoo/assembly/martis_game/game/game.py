import curses
import sys
import os
import signal

from statement import Statement, NextStatementException
from my_evaluator import my_evaluate as evaluate

DEFAULT_STATEMENT = "let s0 = 0.000" # This is what gets inserted as a new statement; chaning this will change the shape of the search space
MAX_MOVES = 500 # Force a game end after this many moves, to prevent infinitely looped paths through the search space
MAX_LINES = 20 # The game is lost immediately once no combination of valid moves can result in a program that is within the line limit, i.e. when the number of lines behind the cursor has reached MAX_LINES + 1
MAX_LINE_PENALTY = 0.3 # Penalty per additional line is MAX_LINE_PENALTY / MAX_LINES. This is to motivate concise programs. Should be set low enough to allow exploring the search space.

class GameOverException(Exception):
    pass

class GameOverProgramTooLongException(GameOverException):
    pass

class GameCompleteException(Exception):
    pass

class Game:
    VALID_INPUTS = ['l', 'h', 'k', 'j', ' ']
    NUM_ACTIONS = len(VALID_INPUTS)
    EMPTY_PROGRAM = """def Setup():\ndef Predict():\ndef Learn():"""

    def __init__(self, program: str = EMPTY_PROGRAM):
        self.program = program
        self.lines = []
        self.current_line = 0
        for line in program.split('\n'):
            # Strip comments
            if '#' in line:
                line = line[:line.index('#')]
            # Skip empty lines
            line = line.strip()
            if len(line) == 0:
                continue
            self.lines.append(Statement(line))
        if not self.is_valid_program():
            print(str(self))
            raise ValueError("invalid program")

    def is_valid_program(self):
        """The Statement class parsing takes care of invalid statements, so all that's left to do is to ensure we contain all three labels, in the correct order, and that we start with the first label."""
        if not self.lines[0].label == "Setup":
            print("first line must be a Setup label")
            return False
        labels = [x.label for x in filter(lambda x: x.label, self.lines)]
        if len(list(labels))!= 3:
            print("program must contain exactly three labels")
            return False
        if not labels[1] == "Predict":
            print("second label must be a Predict label")
            return False
        if not labels[2] == "Learn":
            print("third label must be a Learn label")
            return False
        return True

    def init_curses(self, stdscr: curses.window):
        """Initialize ncurses"""
        curses.curs_set(0)
        stdscr.keypad(0)
        curses.noecho()
        curses.cbreak()
        # Set blinking block cursor
        curses.curs_set(2)


    def clean_up_curses(self, stdscr: curses.window):
        """Clean up ncurses"""
        curses.nocbreak()
        stdscr.keypad(0)
        curses.echo()
        curses.endwin()

    def main(self, stdscr: curses.window):
        self.init_curses(stdscr)
        while True:
            if self.current_line > MAX_LINES:
                raise GameOverProgramTooLongException()
            stdscr.clear()
            for i, statement in enumerate(self.lines):
                stdscr.addstr(i, 0, statement.serialize_for_display())
            if str(self.lines[self.current_line].opcode_mnemonic) == "let" and \
                    self.lines[self.current_line].cursor_position == 2:
                stdscr.addstr(f"\n\nIncrement: {self.lines[self.current_line].increment}")
                stdscr.addstr(f"\nError: {self.lines[self.current_line].roundtrip_floating_point(None, error=True)*100:.2f}%")
                stdscr.addstr(f"\nActual: {self.lines[self.current_line].roundtrip_floating_point():.3f}")
            stdscr.move(self.current_line, self.lines[self.current_line].get_cursor_display_column())
            # Handle input
            ch = stdscr.getch()
            try:
                self._step(ch)
            except GameCompleteException:
                break

        self.clean_up_curses(stdscr)
                
        # Write back to file
        with open(sys.argv[1], 'w') as f:
            f.writelines([statement.serialize_for_file() + '\n' for statement in self.lines])
        print(f"Wrote {sys.argv[1]}", file=sys.stderr)

    def step(self, action: int): # obs, rew, terminated, truncated, info
        observation, reward, terminated, truncated, info = None, 0, False, False, {}
        ch = ord(self.VALID_INPUTS[action])
        try:
            self._step(ch)
            observation = self.state()
        except GameCompleteException:
            terminated = True
            score = self.score()
            per_line_penalty = MAX_LINE_PENALTY / (MAX_LINES - 3)
            penalty = (len(self.lines) - 3) * per_line_penalty
            penalty *= score # Normalize the penalty to the score; this way the score is the primary reward signal; we want the penalty to be a tie-breaker and a nudge towards shorter programs, while allowing longer and better programs
            reward = score - penalty
        except GameOverException:
            terminated = True
            truncated = True
            per_line_penalty = MAX_LINE_PENALTY / (MAX_LINES - 3)
            reward = - (len(self.lines) - 3) * per_line_penalty # Penalize for each added program line (i.e. each line that is not a section label)
        observation = self.state()
        return observation, reward, terminated, truncated, info
    
    def _step(self, ch: int):
        if ch == ord('l'): #curses.KEY_RIGHT:
            try:
                self.lines[self.current_line].move_cursor_right()
            except NextStatementException as e:
                if self.current_line == len(self.lines) - 1:
                    # Submit the program
                    raise GameCompleteException()
                self.current_line += 1
        elif ch == ord('h'): #curses.KEY_LEFT:
            if self.lines[self.current_line].label is None:
                del self.lines[self.current_line]
                self.current_line -= 1 # We won't ever underflow, as a valid program always contains a label as the 0th line
        elif ch == ord('k'): #curses.KEY_UP:
            if self.lines[self.current_line].label is None:
                self.lines[self.current_line].increment_token()
        elif ch == ord('j'): #curses.KEY_DOWN:
            if str(self.lines[self.current_line].opcode_mnemonic) == "let" and \
                self.lines[self.current_line].cursor_position == 2:
                self.lines[self.current_line].change_increment()
        elif ch == ord(' '): # Spacebar
            # Add a line after this one, and move the cursor to it
            self.lines.insert(self.current_line + 1, Statement(DEFAULT_STATEMENT))
        if self.current_line > MAX_LINES:
            raise GameOverProgramTooLongException()
    
    def _program(self) -> str:
        return "".join([statement.serialize_for_file() + "\n" for statement in self.lines])

    def __str__(self):
        s = self._program()
        s += "\n"
        s += f"Current line: {self.current_line}\n"
        s += f"Cursor: {self.lines[self.current_line].cursor_position}\n"
        return s

    def state(self) -> list[int]:
        state = [statement.serialize_one_hot(cursor=(i==self.current_line)) for i, statement in enumerate(self.lines)]
        # Truncate to MAX_LINES
        # Note: when this is not a no-op, we're Game Over anyway
        state = state[:MAX_LINES]
        # Pad to MAX_LINES
        word = len(state[0])
        pad_length = MAX_LINES - len(state)
        state += [[0] * word] * pad_length
        # Flatten
        state = [item for sublist in state for item in sublist]
        return state

    def reset(self):
        self.__init__(self.EMPTY_PROGRAM)

    action_space_size: int = len(VALID_INPUTS)

    def score(self) -> float:
        return evaluate(self._program())
        

if __name__ == "__main__":
    with open(sys.argv[1], 'r') as f:
        program = f.read()
    game = Game(program)
    curses.wrapper(game.main)
