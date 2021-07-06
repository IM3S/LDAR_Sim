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
import time

from input_mapper_v1 import input_mapper_v1


def check_types(default, test, omit_keys = None, fatal = False):
    """Helper function to recursively check the type of parameter dictionaries

    :param default: default element to test
    :param test: test element to test
    :param omit_keys: a list of dictionary keys to omit from further recursive testing
    :param fatal: boolean to control whether sys.exit() is called upon a error
    """
    # Infer 'None' to an empty list
    if omit_keys is None:
        omit_keys = []

    if type(default) is type(test):
        # Proceed to test for dict or list types to recursively examine
        if isinstance(test, dict):
            for i in test:
                if i not in omit_keys:
                    if i not in default:
                        print('Key ' + i + ' present in test parameters, but not in default parameters')
                        if fatal:
                            sys.exit()

                    else:
                        check_types(default[i], test[i], omit_keys = omit_keys, fatal = fatal)

        elif isinstance(test, list):
            if len(test) > 0:
                for i in range(len(test)):
                    check_types(default[0], test[i], omit_keys = omit_keys, fatal = fatal)

    else:
        print('Parameter type mismatch')
        print('Default parameter: ' + str(default) + ' is ' + str(type(default)))
        print('Test parameter: ' + str(test) + ' is ' + str(type(test)))
        if fatal:
            sys.exit()


class InputManager:
    def __init__(self, global_parameter_filename = '..//inputs_template//global_parameters.txt',
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
        to possible issues with json or yaml parsers inferring types.

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
        self.global_parameters = all global parameters as a dictionary.
        self.program_parameters = all known program parameters as a dictionary.
        self.method_parameters = a dictionary where the names are a lookup by type. This contains all known method types
            with a full listing of possible parameters, this is possible to lookup via type. For example
            self.method_parameters['OGI'] will return a full listing of all OGI parameters that is subsequently used
            for type validation and provide the base of default parameters to build upon.
        """
        # Check if program parameter filenames were supplied, else try to read them in
        if program_parameter_filenames is None:
            program_parameter_filenames = glob.glob('..//inputs_template//P_*.txt')

        # Assemble the default parameters
        # 1) read in global parameters, this sets a local variable called 'parameters'
        with open(global_parameter_filename, 'r') as f:
            exec(f.read(), globals())

        # 2) read in the program definitions, which contain method definitions
        for parameter_filename in program_parameter_filenames:
            with open(parameter_filename, 'r') as f:
                program_definition, _ = os.path.splitext(os.path.basename(parameter_filename))
                exec(f.read())
                if program_definition not in locals():
                    print(program_definition + ' is not defined in ' + parameter_filename)

                global_parameters['programs'].append(eval(program_definition))

        # 3) separate programs from methods and construct a default program with all possible parameters. This
        #    accumulates a list of method definitions from the programs to conflate to a unique list of method
        #    definitions.
        self.program_parameters = {'methods': []}
        temp_methods = []
        for program in global_parameters['programs']:
            if len(program['methods']) > 0:
                temp_methods.append(program.pop('methods'))

            self.program_parameters.update(program)

        # 4) accumulate the method samples so there is a dictionary of possible method types, each with all
        #    known parameters, in a default and completely defined format.
        self.method_parameters = {}
        for method_samples in temp_methods:
            for i in method_samples:
                # Address an issue where 'type' is not specified, allow reverse compatibility by using the name
                if 'type' not in method_samples[i]:
                    method_samples[i]['type'] = i

                self.method_parameters.update({method_samples[i]['type']: method_samples[i]})

        # 5) set default global parameters, programs and methods are dealt with separately
        global_parameters['programs'] = []
        self.global_parameters = global_parameters

        # 6) construct simulation parameters, which will be updated and returned
        self.simulation_parameters = copy.deepcopy(self.global_parameters)
        return

    def read_and_validate_parameters(self, parameter_filenames):
        """Method to read and validate parameters
        :param parameter_filenames: a list of paths to parameter files
        :return returns fully validated parameters dictionary for simulation in LDAR-Sim
        """
        raw_parameters = self.read_parameter_files(parameter_filenames)
        self.parse_parameters(raw_parameters)

        # Coerce all paths to absolute paths prior to release, add extra guards for other parts of the code
        # that concatenate strings to construct file paths, and expect trailing slashes
        self.simulation_parameters['wd'] = os.path.abspath(self.simulation_parameters['wd']) + '//'
        self.simulation_parameters['output_directory'] = os.path.abspath(self.simulation_parameters['output_directory']) + '//'
        return(copy.deepcopy(self.simulation_parameters))

    def write_parameters(self, filename):
        """Method to write simulation parameters to the file system

        :param filename: filename to write the parameters to
        """
        with open(filename, 'w') as f:
            f.write(yaml.dump(self.simulation_parameters))

    def read_parameter_files(self, parameter_filenames):
        """Method to read a collection of parameter files and perform any mapping prior to validation.

        :param parameter_filenames: a list of paths to parameter files
        :return returns a list of parameter dictionaries
        """
        # Read in the parameter files
        new_parameters_list = []
        for parameter_filename in parameter_filenames:
            new_parameters_list.append(self.read_parameter_file(parameter_filename))

        # Perform any mapping, optionally accumulating mined global parameters
        global_parameters = {}
        for i in range(len(new_parameters_list)):
            new_parameters_list[i], mined_global_parameters = self.map_parameters(new_parameters_list[i])
            global_parameters.update(mined_global_parameters)

        # Append the mined global parameters for installation
        if len(global_parameters) > 0:
            global_parameters['parameter_level'] = 'global'
            new_parameters_list.append(global_parameters)

        return(new_parameters_list)

    def read_parameter_file(self, filename):
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

    def map_parameters(self, parameters):
        """Function to map parameters from older versions to the present version, all mappings are externally specified
        in the relavent function.

        :param parameters = the input parameter dictionary
        :return returns the compliant parameters dictionary, and optionally mined global parameters
        """
        if 'version' not in parameters:
            print('Warning: interpreting parameters as version 1.0 because version key was missing')
            parameters['version'] = '1.0'

        mined_global_parameters = {}
        if parameters['version'] == '1.0':
            parameters, mined_global_parameters = input_mapper_v1(parameters)

        return(parameters, mined_global_parameters)

    def parse_parameters(self, new_parameters_list):
        """Method to parse and validate new parameters, perform type checking, and organize for simulation.

        This first goes through the new parameters, sorts out the programs and orphaned methods (methods that are
        not directly integrated to a program).

        Programs are then addressed, consecutively adding them in, calling in any orphaned methods. Orphaned methods
        can be used in multiple programs if desired.

        :param new_parameters_list: a list of new parameter dictionaries

        The self.simulation_variables variable is set
        """
        # First, validate and install the global parameters, saving the programs and orphaned methods for the next step
        programs = []
        orphan_methods = {}
        for new_parameters in new_parameters_list:
            # Address unsupplied parameter level
            if 'parameter_level' not in new_parameters:
                new_parameters['parameter_level'] = 'global'
                print('Warning: parameter_level should be supplied to parameter files, LDAR-Sim interprets parameter'
                      'files as global if unspecified')

            if new_parameters['parameter_level'] == 'global':
                if len(new_parameters['programs']) > 0:
                    programs = programs + new_parameters.pop('programs')

                check_types(self.global_parameters, new_parameters, omit_keys = ['programs', 'methods'])
                self.simulation_parameters.update(new_parameters)

            elif new_parameters['parameter_level'] == 'program':
                check_types(self.program_parameters, new_parameters, omit_keys = ['methods'])

                # Copy all default program parameters to build upon by calling update, then append
                new_program = copy.deepcopy(self.program_parameters)
                new_program.update(new_parameters)
                programs.append(new_program)

            elif new_parameters['parameter_level'] == 'method':
                # Search for the methods in this definition, which will be defined as dictionaries
                for i in new_parameters:
                    if isinstance(new_parameters[i], dict):
                        orphan_methods.update({i: new_parameters[i]})

            else:
                sys.exit('supplied parameter_level is not possible to parse')

        # Second, install the programs, checking for specified children methods
        for program in programs:
            # Find any orphaned methods that can be installed in this program
            if 'method_names' in program:
                for method_name in program['method_names']:
                    method_found = False
                    for i in orphan_methods:
                        if method_name == i:
                            program['methods'].update({i: copy.deepcopy(orphan_methods[i])})
                            method_found = True

                    if not method_found:
                        print('Warning, the following method was specified by not supplied ' + method_name)

            # Next, perform type checking and updating from default types, even for methods pre-specified
            for i in program['methods']:
                method_type = program['methods'][i]['type']
                check_types(self.method_parameters[method_type], program['methods'][i])
                new_method = copy.deepcopy(self.method_parameters[method_type])

                # update from the default version, and re-assign
                new_method.update(program['methods'][i])
                program['methods'][i] = new_method

        # Third, append the parameters to the global parameters
        self.simulation_parameters['programs'] = programs
