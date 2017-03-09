#!/usr/bin/python3
PURPLE = '\033[95m'
CYAN = '\033[96m'
DARKCYAN = '\033[36m'
BLUE = '\033[94m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
END = '\033[0m'


def coloredPrint(msg, colorCode):
    try:
        print(colorCode + BOLD + msg + END)
    except:
        print("\n[-] Error printing with color {}\n".format(colorCode) + msg)