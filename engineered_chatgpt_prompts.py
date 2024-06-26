"""
This is a simple PyQt5 GUI application that allows to create elaborated
chatgtp prompts. Using a specified goal, the input text is processed
by the chatgpt model to generate the output text.
"""

import argparse
import asyncio
import os
import sys

import openai
from dotenv import load_dotenv, find_dotenv
from PyQt5.QtWidgets import (QApplication,  # pylint: disable=no-name-in-module
                             QWidget,
                             QVBoxLayout,
                             QHBoxLayout,
                             QLabel,
                             QFileDialog,
                             QTextEdit,
                             QPushButton)

_ = load_dotenv(find_dotenv())  # read local .env file
# default_openai_model = "gpt-4o"
default_openai_model = "gpt-3.5-turbo"
# default_openai_model = "text-embedding-3-small"
# default_openai_model = "text-embedding-3-large"
# default_openai_model = "gpt-4-1106-vision-preview"

openai.api_key = os.getenv('OPENAI_API_KEY')
openai.organization = os.getenv('OPENAI_ORGANIZATION')
openai.project = os.getenv('OPENAI_PROJECT')

print("OpenAI version:", openai.__version__)
last_response = ""  # pylint: disable=invalid-name,redefined-outer-name


async def get_completion(prompt,
                         model=default_openai_model):
    """
    method to query openai API
    """
    messages = [{"role": "user", "content": prompt}]
    chat = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0,
        # stream=True,
        # this is the randomness degree of the model's output
    )
    global last_response  # pylint: disable=global-statement
    last_response = chat.choices[0].message[
        "content"]  # pylint: disable=invalid-name,redefined-outer-name
    sys.stdout.write(f"\r{last_response}>")
    sys.stdout.flush()
    return last_response


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Launch engineered chatgtp prompts tool '
                    'on graphical or command line mode.\n\n'
                    'Example processing a directory in batch mode:\n'
                    '  python engineered_chatgtp_prompts.py'
                    ' --directory="/path/to/directory"'
                    ' --goal="/path/to/goal"'
                    '\n\n'
                    'Example processing a file in batch mode:\n'
                    '  python engineered_chatgtp_prompts.py'
                    ' --file="/path/to/file"'
                    ' --goal="${PWD}/goals/general/summarize.txt"'
                    '\n\n'
                    'Example Launching it on graphical mode:\n'
                    '  python engineered_chatgtp_prompts.py ',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-d', "--dir", required=False,
                        dest='dir',
                        default=None, type=str,
                        help="full path to directory to process")
    parser.add_argument('-f', "--file", required=False,
                        dest='file',
                        default=None, type=str,
                        help="full path to file to process")
    parser.add_argument('-g', "--goal", required=False,
                        dest='goal',
                        default=None, type=str,
                        help="relative file path to goal file in"
                             " ./goals directory")
    parser.add_argument('-t', "--filter", required=False,
                        dest='ffilter',
                        default="", type=str,
                        help="relative file path to filter file in"
                             " ./utils/file_filters directory")
    args_namespace = parser.parse_args()
    if hasattr(args_namespace, 'help'):
        parser.print_help()
        exit(0)
    return args_namespace


def check_arguments(_args: argparse.Namespace):
    """
    verify that provided arguments are correct
    :param _args:
        input arguments parser
    :return:
         void
    """
    if _args.dir is not None and _args.file is not None:
        raise Exception("Directory and file arguments are exclusive")
    if _args.dir is not None or _args.file is not None:
        if _args.goal is None:
            raise Exception("Goal argument is required when "
                            "directory or file is provided")
        else:
            goal_file = full_path_goal(_args.goal)
            if not os.path.exists(goal_file):
                raise Exception(f"Goal file does not exist: {goal_file}")
            if len(_args.ffilter) != 0:
                filter_file = full_path_filter(_args.ffilter)
                print(f"Filter file: {filter_file}")
                if not os.path.exists(filter_file):
                    raise Exception(f"Filter file does not exist: {filter_file}")
    if _args.dir is not None:
        if not os.path.exists(_args.dir):
            raise Exception(f"Directory does not exist: {_args.dir}")
    if _args.file is not None:
        if not os.path.exists(_args.file):
            raise Exception(f"File does not exist: {_args.file}")


def full_path_goal(input: str):
    return f"goals/{input}"


def full_path_filter(input: str):
    return f"utils/file_filters/{input}"


def process_file(file: str, goal: str):
    """
    process a file with a goal
    :param file:
        file to process
    :param goal:
        goal to process
    :return:
        void
    """
    with open(file, 'r', encoding='utf-8') as f:
        gf = open(full_path_goal(goal), 'r', encoding='utf-8')
        goal_text = gf.read()
        gf.close()
        file_text = f.read()
        print(f"sending to openai file: {file} with goal:\n{goal_text}")
        full_prompt = (f"with the following goal "
                       f"(delimited by triple backticks): ```{goal_text}```"
                       f"process the following text with specified goal"
                       f"(delimited by triple backticks): ```{file_text}```")
        asyncio.run(get_completion(full_prompt))
        print(last_response)


def process_directory(dir: str, goal: str, ffilter: str = ""):
    """
    process a directory with a goal
    :param directory:
        directory to process
    :param goal:
        goal to process
    :return:
        void
    """
    import subprocess
    import time
    import tempfile
    # ffilter = "has_timestamp.sh"
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
        timestamp = str(int(time.time()))
        temp_file_name = temp_file.name
        temp_file.close()
        print(f"Executing: ./utils/serialize_dir.sh"
              f" {dir} {temp_file_name} {ffilter}")
        subprocess.run(
            ['bash', 'utils/serialize_dir.sh', dir, temp_file_name, ffilter])
        process_file(temp_file_name, goal)
        os.remove(temp_file_name)


class EngineeredChatgptPrompts(
    QWidget):  # pylint: disable=too-many-instance-attributes
    """
    class to hold widgets and process method of main application
    """

    def __init__(self):
        super().__init__()

        # Create widgets
        self.goal_label = QLabel('Enter Goal:')
        self.goal_text = QTextEdit()
        self.clear_goal_button = QPushButton('Clear')
        self.load_goal_button = QPushButton('Load')
        self.save_goal_button = QPushButton('Save')
        self.input_text_label = QLabel('Enter input text:')
        self.input_text = QTextEdit()
        self.clear_input_button = QPushButton('Clear input')
        self.process_button = QPushButton('Process')
        self.result_label = QLabel('Processed Text:')
        self.output_text = QTextEdit()

        height = 400
        output_text_height = 200
        width = 800
        self.goal_text.setFixedSize(width, 70)
        self.input_text.setFixedSize(width, height)
        self.output_text.setFixedSize(width, output_text_height)
        # Enable word wrap for both text input and result label
        self.goal_text.setLineWrapMode(QTextEdit.WidgetWidth)
        self.input_text.setLineWrapMode(QTextEdit.WidgetWidth)
        self.output_text.setLineWrapMode(QTextEdit.WidgetWidth)
        self.output_text.setReadOnly(True)

        # set horizontal layouts (for buttons)
        self.goal_buttons_layout = QHBoxLayout()
        self.goal_buttons_layout.addWidget(self.clear_goal_button)
        self.goal_buttons_layout.addWidget(self.load_goal_button)
        self.goal_buttons_layout.addWidget(self.save_goal_button)
        self.process_buttons_layout = QHBoxLayout()
        self.process_buttons_layout.addWidget(self.clear_input_button)
        self.process_buttons_layout.addWidget(self.process_button)

        # Set up main main_layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.goal_label)
        main_layout.addWidget(self.goal_text)
        main_layout.addLayout(self.goal_buttons_layout)
        main_layout.addWidget(self.input_text_label)
        main_layout.addWidget(self.input_text)
        main_layout.addLayout(self.process_buttons_layout)
        main_layout.addWidget(self.result_label)
        main_layout.addWidget(self.output_text)

        # Set the main_layout for the main window
        self.setLayout(main_layout)

        # Connect the button click event to the process_text method
        self.load_goal_button.clicked.connect(self.load_goal)
        self.save_goal_button.clicked.connect(self.save_goal)
        self.clear_goal_button.clicked.connect(self.clear_goal)
        self.process_button.clicked.connect(self.process_text)
        self.clear_input_button.clicked.connect(self.clear_input)

        # Set up the main window
        self.setWindowTitle('engineered chatgpt prompts')
        self.show()

    def process_text(self):
        """ send engineered prompt to openai API and set result on output """
        input_text = self.input_text.toPlainText()
        goal = self.goal_text.toPlainText()
        # Perform processing on the input text (replace with your own logic)
        if len(goal) < 2:
            goal = "summarize in 2 sentence"
        full_prompt = (f"with the following goal "
                       f"(delimited by triple backticks): ```{goal}```"
                       f"process the following text with specified goal"
                       f"(delimited by triple backticks): ```{input_text}```")
        asyncio.run(get_completion(full_prompt))
        global last_response  # pylint: disable=global-statement
        self.output_text.setPlainText(last_response)

    def load_goal(self):
        """ open a dialog inspecting text files on file system """
        filename = QFileDialog.getOpenFileName(self,
                                               'Open File',
                                               '.',
                                               'Text Files (*.txt)')
        if filename[0]:
            with open(filename[0], 'r', encoding='utf-8') as f:
                file_text = f.read()
                self.goal_text.setText(file_text)

    def save_goal(self):
        """ save goal text into system file """
        filename = QFileDialog.getSaveFileName(self,
                                               'Save File',
                                               '.',
                                               'Text Files (*.txt)')
        if filename[0]:
            file = filename[0]
            if not filename[0].endswith('.txt'):
                file += '.txt'
            with open(file, 'w', encoding='utf-8') as f:
                my_text = self.goal_text.toPlainText()
                f.write(my_text)

    def clear_goal(self):
        """ clean goal text box """
        self.goal_text.setText('')

    def clear_input(self):
        """ clean input text box """
        self.input_text.setText('')


if __name__ == '__main__':
    args = parse_arguments()
    check_arguments(args)
    if args.dir is not None:
        print(f"Processing directory: {args.dir}\nwith goal: {args.goal}")
        process_directory(args.dir, args.goal, args.ffilter)
    elif args.file is not None:
        process_file(args.file, args.goal)
        print(f"Processing file: {args.file}\nwith goal: {args.goal}")
    else:
        app = QApplication([])
        window = EngineeredChatgptPrompts()
        app.exec_()
