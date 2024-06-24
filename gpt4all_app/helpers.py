# Class for defining command line styles
class bcolors:
    DEFAULT = '\033[0;39m'
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# Function to convert column int to column letter
def column_int_to_letter(column_int):
    
    start_index = 1 # can start with either 0 or 1
    letter = ''
    
    while column_int > 25 + start_index:
        letter += chr(65 + int((column_int - start_index)/26) - 1)
        column_int = column_int - (int((column_int - start_index) / 26)) * 26

    letter += chr(65 - start_index + (int(column_int)))

    return letter