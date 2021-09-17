# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        LDAR-Sim gui
# Purpose:     Simple tkinter GUI for LDAR Sim
#
# Copyright (C) 2018-2021  Intelligent Methane Monitoring and Management System (IM3S) Group
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the MIT License as published
# by the Free Software Foundation, version 3.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# MIT License for more details.

# You should have received a copy of the MIT License
# along with this program.  If not, see <https://opensource.org/licenses/MIT>.
#
# ------------------------------------------------------------------------------

import os
import tkinter
import tkinter.filedialog as tkFileDialog
import subprocess

def create_input_file_listing():
    '''
    Function to create an input file listing for display in the program
    '''
    global input_files
    return ('\n'.join(input_files))

def choose_input_file():
    '''
    Function to choose an input file and add to the input stack
    '''
    global input_files
    parameter_file = tkFileDialog.askopenfilename(
                            initialdir = os.path.abspath('..//sample_simulations'), parent = root,
                            title = "Select input file",
                            filetypes = [('LDAR SIM parameter files', '.yaml')])
    if not os.path.exists(parameter_file):
        print('ERROR: ' + parameter_file + ' does not exist')
    else:
        for i in range(len(input_files)):
            if input_files[i] == '':
                input_files[i] = parameter_file
                break

    inputlist.config(text = create_input_file_listing())

def delete_last_input_file():
    '''
    Function to remove the last input file from the stack
    '''
    global input_files
    for i in range(len(input_files) - 1, -1, -1):
        if input_files[i] != '':
            input_files[i] = ''
            break

    inputlist.config(text = create_input_file_listing())

def run_model():
    '''
    Function to run the model
    '''
    global input_files
    callstring = ['.//ldar_sim_main.exe']
    for i in input_files:
        if i != '':
            callstring.append(i)
    print('ldar sim core call:')
    print(str(callstring))
    try:
        _ = subprocess.call(callstring)

    except Exception:
        print('ERROR with model call')

    print('SIMULATION CALL COMPLETED (check for errors)')
    return

if __name__ == '__main__':
    # set up default input files
    input_files = [os.path.abspath('..//sample_simulations//P_OGI_dev.yaml')] + [''] * 9
    button_width = 100

    # set up GUI
    root = tkinter.Tk()
    root.title('LDAR Sim')
    root.focus_force()

    # set up and pack GUI elements
    entry = tkinter.Button(root, width = button_width, text = 'Add parameter file ...',
                            command = choose_input_file)
    entry.pack()
    delete_last_entry = tkinter.Button(root, width = button_width,
                                       text = 'Delete last parameter file',
                                       command = delete_last_input_file)
    delete_last_entry.pack()
    inputlist = tkinter.Label(root, text = create_input_file_listing())
    inputlist.pack()
    run_button = tkinter.Button(root, width = button_width, text = 'Run model!',
                                command = run_model)
    run_button.pack()
    root.mainloop()


