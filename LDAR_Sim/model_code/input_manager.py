# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        LDAR-Sim input manager
# Purpose:     Interface for managing, validating, and otherwise dealing with parameters
#
# Copyright (C) 2018-2020  Thomas Fox, Mozhou Gao, Thomas Barchyn, Chris Hugenholtz
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
import copy
import os
import yaml
import json
import glob
import sys

def check_types (default, test, omit_keys = [], fatal = False):
    """Helper function to recursively check the type of parameter dictionaries

    :param default: default element to test
    :param test: test element to test
    :omit_keys: a list of dictionary keys to omit from further recursive testing
    :param fatal: boolean to control whether sys.exit() is called upon a error
    """
    if type(default) is type(test):
        # proceed to test for dict or list types to recursively examine
        if isinstance(test, dict):
            for i in test:
                if not i in omit_keys:
                    if not i in default:
                        print('Key ' + i + ' present in test parameters, but not in default parameters')
                        if fatal:
                            sys.exit()

                    else:
                        check_types(default[i], test[i], fatal)

        elif isinstance(test, list):
            if len(test) > 0:
                for i in range(len(test)):
                    check_types(default[0], test[i], fatal)

    else:
        print('Parameter type mismatch')
        print('Default parameter: ' + str(default) + ' is ' + type(default))
        print('Test parameter: ' + str(test) + ' is ' + type(test))
        if fatal:
            sys.exit()

class input_manager:
    def __init__ (self, global_parameter_filename = '..//inputs_template//global_parameters.txt',
                  program_parameter_filenames = None):
        """ Constructor loads the input parameters in a format that is compliant with the internals of LDAR-Sim. These
        parameters are subsequently modified by one or more input parameters.

        First, this creates a default 'program' that contains all possible 'program' parameters. No input program can
        contain parameters that do not exist in this default program.

        Then, this creates a library of 'methods' that have unique parameter sets. For example, the aircraft method
        can have different parameters than the truck method. But the P_aircraft and P_truck programs must have the
        same parameters (with the exception of the methods, which can have non-unique parameters). When constructing a
        new program, the methods must have appropriate tags to look up the default parameters for the methods involved.

        The format of the default parameters is .txt, or .py, that gets read, and executed directly as
        python code. This is to ensure reverse compatibility with the existing set of parameters and also to ensure
        that the type are explicitly set with python code, where type setting is easier to understand and less subject
        to possible issues with json or yaml parsers inferring incorrect types.

        :param global_parameter_filename: filename for global parameters. Defaults to
            '..//inputs_template//global_parameters.txt'
        :param program_parameter_filenames: a list of default parameter files that represent the number of possible
            programs. If missing, the '..//inputs_template//' directory is searched for files with a pattern of
            'P_*.txt', which is the default naming convention in present use. NOTE: programs must be defined in
            these default files as a dictionary where the object defined is IDENTICAL to the name of the file without
            an exception. For example:

            P_aircraft = {
                # P_Aircraft parameters go here
            }

            Must be inside a file called P_aircraft.txt, or P_aircraft.py. There are no possible exceptions to this
            rule presently.

        This sets three class variables to represent default parameters:
        self.global_parameters = all global parameters as a dictionary
        self.program_parameters = all program parameters as a dictionary
        self.method_parameters = a dictionary where the names refer to all possible methods
        """

        # Check if program parameter filenames were supplied, else try to read them in
        if program_parameter_filenames is None:
            program_parameter_filenames = glob.glob('..//inputs_template//P_*.txt')

        # Read in default parameters
        # 1) read in global parameters, this sets a local variable called 'parameters'
        with open(global_parameter_filename, 'r') as f:
            exec(f.read())

        # 2) read in the program definitions, which contain method definitions
        for parameter_filename in program_parameter_filenames:
            with open(parameter_filename, 'r') as f:
                program_definition, _ = os.path.splitext(os.path.basename(parameter_filename))
                exec(f.read())
                if not program_definition in locals():
                    print(program_definition + ' is not defined in ' + parameter_filename)

                parameters['programs'].append(eval(program_definition))

        # 3) separate programs from methods and construct a default program with all possible parameters. This
        #    accumulates a list of method definitions from the programs to conflate to a unique list of method
        #    definitions.
        self.program_parameters = {'methods': []}
        temp_methods = []
        for program in parameters['programs']:
            temp_methods.append(program.pop['methods'])
            self.program_parameters.update(program)

        # 4) accumulate the method parameters so there is a dictionary of possible method types, each with all
        #    known parameters, in a default and completely defined format
        self.method_parameters = {}
        for method_samples in temp_methods:
            self.method_parameters.update(method_samples)

        # 5) set default global parameters, programs and methods are dealt with separately
        parameters['programs'] = []
        self.global_parameters = parameters
        return

    def read_and_validate_parameters (self, parameter_filenames):
        """Method to read and validate parameters
        :param parameter_filenames: a list of paths to parameter files
        :return returns fully validated parameters dictionary for simulation in LDAR-Sim
        """
        unvalidated_parameters = self.read_parameter_files(parameter_filenames)
        validated_parameters = self.parse_parameters(unvalidated_parameters)
        return(validated_parameters)

    def parse_parameters (self, new_parameters_list):
        """Method to parse and validate new parameters, perform type checking, and organize for simulation.

        This first goes through the new parameters, sorts out the programs and orphaned methods (methods that are
        not directly integrated to a program).

        Programs are then addressed, consecutively adding them in, calling in any orphaned methods. Orphaned methods
        can be used in multiple programs if desired.

        :param new_parameters_list: a list of new parameter dictionaries
        :return returns the validated parameters
        """
        # First, validate and install the global parameters, saving the programs and orphaned methods for the next step
        programs = []
        orphan_methods = []
        for new_parameters in new_parameters_list:
            # Address unsupplied
            if not 'parameter_level' in new_parameters:
                new_parameters['parameter_level'] = 'global'
                print('Warning: parameter_level should be supplied to parameter files, LDAR-Sim interprets parameter'
                      'files as global if unspecified')

            if new_parameters['parameter_level'] == 'global':
                programs.append(new_parameters.pop('programs'))
                check_types(self.global_parameters, new_parameters, omit_keys = ['programs', 'methods'])
                self.global_parameters.update(new_parameters)
            elif new_parameters['parameter_level'] == 'program':
                check_types(self.program_parameters, new_parameters, omit_keys = ['methods'])
                programs.append(new_parameters)
            elif new_parameters['parameter_level'] == 'method':
                orphan_methods.append(new_parameters)

        # Second, install the programs, checking for specified children methods
        for program in programs:
            # Find any orphaned children
            if 'children_names' in program:
                for children in program['children_names']:
                    child_found = False
                    for orphan in orphan_methods:
                        if 'name' in orphan and orphan['name'] == children:
                            program['methods'].update(copy.deepcopy(orphan))
                            child_found = True

                    if not child_found:
                        print('Warning, the following child method was specified by not supplied ' + children)

            # Next, perform type checking on the methods to ensure the supplied methods are compliant
            for method in program['methods']:
                method_type
                check_types(self.method_parameters[method_name], program['methods'][method_name])

        # Third, append the parameters to the global parameters and return
        self.global_parameters['programs'] = programs
        return(self.global_parameters)

    def read_parameter_files (self, parameter_filenames):
        """Method to read a collection of parameter files
        :param parameter_filenames: a list of paths to parameter files
        :return returns a list of parameter dictionaries
        """
        new_parameters_list = []
        for parameter_filename in parameter_filenames:
            new_parameters_list.append(self.read_parameter_file(parameter_filename))

        return(new_parameters_list)

    def read_parameter_file (self, filename):
        """Method to read a single parameter file from a filename. This method can be extended to address different
        file formats or mappings.

        :param filename: the path to the parameter file
        :return: dictionary of parameters read from the parameter file
        """
        parameter_set_name, extension = os.path.splitext(os.path.basename(filename))
        new_parameters = {}
        with open(filename, 'r') as f:
            print('Reading ' + filename)
            if extension == '.txt':
                exec(f.read())
                new_parameters.update(eval(parameter_set_name))
            elif extension == '.json':
                new_parameters = json.loads(f.read())
            elif extension == '.yaml' or extension == '.yml':
                new_parameters = yaml.load(f.read(), Loader = yaml.FullLoader)
            else:
                sys.exit('Invalid parameter file format: ' + filename)

        return(new_parameters)
