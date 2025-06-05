# Here you define the commands that will be added to your add-in.
from .createWaveDrive import entry as createWaveDrive

commands = [
    createWaveDrive
]


def start():
    for command in commands:
        command.start()


def stop():
    for command in commands:
        command.stop()
