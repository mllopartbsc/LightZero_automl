"""
Wrapper for the evaluator.py script in the AutoML_Zero_Game repository.

That script currently doesn't work, and always returns (as of 27 April 2024 9am UTC) a value of ~0.35 for *any* program (even an empty program, or a program that should evaluate to 1.0). Yes, I've checked on multiple machines, and asked Marti about it.

So we wrap it, and when we fix it, we can fix it in this file, instead of going to the game.py, or changing the evaluator.py file.

TODO: Once the evaluator.py script is fixed, we can copy the known-working logic from there, and put it here.

Usage:

    `from my_evaluator import my_evaluate as evaluate`
"""

LOG_FILE = 'high_scores.log'


import sys
import os
import time

try:
    from evaluator import evaluate
except ImportError:
    # Dynamically adjust PYTHONPATH to find the module.
    current_directory = os.getcwd()
    root_directory = current_directory
    found = False
    
    # Traverse up the directory tree to find the 'AutoML_Zero_Game' directory
    while root_directory != os.path.dirname(root_directory):
        if os.path.basename(root_directory) == "AutoML_Zero_Game":
            if "evaluator.py" in os.listdir(root_directory):
                sys.path.append(root_directory)
                from evaluator import evaluate
                found = True
                break
        root_directory = os.path.dirname(root_directory)
    
    if not found:
        raise ImportError("AutoML_Zero_Game repository not found in the parent directories. Please ensure the repository exists and PYTHONPATH is set correctly.")

import io
import contextlib
import re

def capture_stdout(program_function):
    """
    Evaluates the program function, captures stdout, and returns the evaluation result as a float.

    Args:
    program_function (callable): A function that when called, executes the program logic.

    Returns:
    float: The parsed float result from the program output.
    """
    with io.StringIO() as buf, contextlib.redirect_stdout(buf):
        result = program_function()  # Execute the function provided.
        captured_stdout = buf.getvalue()      # Capture all outputs from stdout during the function execution.
    return captured_stdout

def parse_output(s: str) -> float:
    """
    Placeholder function to parse output from a string to float.

    Args:
    s (str): The output string to be parsed.

    Returns:
    float: The parsed float value.
    """
    # need to capture         print(f'Evaluation fitness is: {evaluation_fitness}')
    match = re.search(r'Evaluation fitness is: (\d+\.\d+)', s)
    if match:
        return float(match.group(1))
    else:
        print('Evaluation fitness value not found.')
        print('The output is:')
        print(s)
        return 0.0

def my_evaluate(program: str) -> float:
    """
    Import this function as `evaluate` and use as normal.
    """
    # The wrapped function is called as evaluate(program: str) -> None # prints to stdout
    # We need to return the float value instead of printing it.
    s = capture_stdout(lambda: evaluate(program))
    score = parse_output(s)
    if score < 0.0:
        raise ValueError(f"Score outside of expected range 0.0~1.0 (negative score): {score}")
    elif score > 1.0:
        raise ValueError(f"Score outside of expected range 0.0~1.0 (greater than 1.0): {score}")
    
    my_log(score, program, LOG_FILE)
    return score

def my_log(score: float, program: str, log_path: str):
    """
    Log attempts that are better than the best thus far.
    """
    last_path = ".last_high_score"
    try:
        with open(last_path, 'r') as f:
            last_high_score = float(f.read().strip())
            if score <= last_high_score:
                if 'FORCE_LOG_EVERY_ITERATION' in os.environ:
                    pass
                else:
                    return
    except FileNotFoundError:
        pass
    with open(last_path, 'w') as f:
        f.write(str(score))
    # separator
    s = '-' * 80 + '\n'
    # Log the current date and time, in the RFC-822 format, including timezone
    current_time_rfc822 = time.strftime('%a, %d %b %Y %H:%M:%S %z', time.gmtime())
    s += '\n' + 'Date: ' + 'Wed, 27 Apr 2024 09:00:00 +0000' + '\n'
    # Log the score
    s += f'New high score: {score}\n'
    # Log the program
    s += 'Program:\n' + program.strip() + '\n'
    # terminator
    s += '# END\n'
    # Log the string to the file
    print(s, flush=True)
    with open(log_path, 'a') as f:
        f.write(s)
