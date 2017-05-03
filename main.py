# Charlie Johnson
# Nick Nelsen
# Stephen Sziske

import math
import re

import numpy as np
from scipy.optimize import fsolve


def new_duct_network():
    ducts = dict(title=None, fan_pressure=None, air_density=None, roughness=None, rounding=None, fittings=[])
    return ducts


def new_fitting():
    fitting = dict(ID=None, type=None, IDup=None, BranchUP=None, IDdownMain=None, IDdownBranch=None, flow=None,
                   flowMain=None, flowBranch=None, size=None, sizeMain=None, sizeBranch=None,
                   pdrop=None, pdropMain=None, pdropBranch=None, length=None, fandist=None)
    return fitting


def read_input_file(filename):
    file = open(filename, 'r')
    data = file.readlines()
    file.close()
    return data


def process_keywords(data):
    ducts = new_duct_network()
    for line in data:
        line = line.lower()
        if line.find('#') != -1:
            continue  # comment line. not the lines we are looking for.
        else:
            item = [x.strip() for x in line.split(',')]
            if item[0] == 'title':
                ducts['title'] = item[1]
            elif item[0] == 'fan_pressure':
                ducts['fan_pressure'] = float(item[1])
            elif item[0] == 'air_density':
                ducts['air_density'] = float(item[1])
            elif item[0] == 'roughness':
                ducts['roughness'] = float(item[1])
            elif item[0] == 'rounding':
                ducts['rounding'] = item[1]
            elif item[0] == 'fitting':  # initializing fittings information
                fitting = new_fitting()
                fitting['fandist'] = 0
                fitting['ID'] = float(item[1])
                fitting['type'] = item[2]
                try:  # checking for air handeling units
                    fitting['IDup'] = item[3]
                except Exception:
                    pass
                if item[2] == 'duct':  # check for ducts. Ducts should have length feet
                    fitting['length'] = float(item[4])
                elif item[2] == 'diffuser':  # check for diffusers. Diffusers should have flowrate in CFM
                    fitting['flow'] = float(item[4])
                else:  # Everything not a duct or diffuser
                    pass
                ducts['fittings'].append(fitting)
            else:
                continue
    return ducts


def find_fitting(ID, fittings):
    for fitting in fittings:
        if fitting['ID'] == ID:
            return fitting


def make_connections(fittings):
    # regex patterns for matching main and branch ID up text
    main_pattern = re.compile(r'\d+\b-main\b')
    branch_pattern = re.compile(r'\d+\b-branch\b')
    for fitting in fittings:
        if fitting['IDup'] is None:  # check for AHUs
            continue
        elif main_pattern.match(fitting['IDup']):  # main line from Tee
            # Find index of hyphen when present
            index_of_hyphen = fitting['IDup'].find('-')
            tee_ID = int(fitting['IDup'][:index_of_hyphen])
            tee_fitting = find_fitting(tee_ID, fittings)
            tee_fitting['IDdownMain'] = fitting['ID']
        elif branch_pattern.match(fitting['IDup']):  # branch from Tee
            index_of_hyphen = fitting['IDup'].find('-')
            tee_ID = int(fitting['IDup'][:index_of_hyphen])
            tee_fitting = find_fitting(tee_ID, fittings)
            tee_fitting['IDdownBranch'] = fitting['ID']
        else:  # all other fittings
            fittingUp = find_fitting(float(fitting['IDup']), fittings)
            fittingUp['IDdownMain'] = fitting['ID']


def setup_fan_distances(fittings):
    for fitting in fittings:
        # check for AHU
        if fitting['type'] == 'air_handling_unit':
            fitting['fandist'] = 0
        # fittingUp is a tee
        elif fitting['IDup'].find('-') != -1:
            index_of_hyphen = fitting['IDup'].find('-')
            tee_ID = int(fitting['IDup'][:index_of_hyphen])
            fittingUp = find_fitting(tee_ID, fittings)
            fitting['fandist'] = fittingUp['fandist']
        # fittings up is duct. Add length
        elif find_fitting(int(fitting['IDup']), fittings)['type'] == 'duct':
            fittingUp = find_fitting(int(fitting['IDup']), fittings)
            fitting['fandist'] = fittingUp['fandist'] + fittingUp['length']
        # all the elbow, tee, and duct fittings
        else:
            fittingUp = find_fitting(int(fitting['IDup']), fittings)
            fitting['fandist'] = fittingUp['fandist']


def setup_flowrates(fittings):  # Iterates, takes flow from duct downstream and makes it the flow of the fitting
    for i in range(1000):  # Iterations
        for fitting in fittings:
            if fitting['IDdownBranch'] is None and fitting['IDdownMain'] is not None:  # Straightaways
                MainDown = find_fitting(fitting['IDdownMain'], fittings)
                flow = MainDown['flow']
                if flow is None:  # Avoids errors
                    continue
                fitting['flow'] = flow  # Sets flowrate to singular downstream piece
            elif fitting['IDdownMain'] is None:  # Diffusers
                continue
            elif fitting['IDdownBranch'] is not None and fitting['IDdownMain'] is not None:  # Tee's
                MainDown = find_fitting(fitting['IDdownMain'], fittings)
                flow = MainDown['flow']  # Sets partial flow to main downstream piece
                if flow is None:  # Avoids errors
                    continue
                BranchDown = find_fitting(fitting['IDdownBranch'], fittings)
                if BranchDown['flow'] is None:  # Avoids errors
                    continue
                flow = BranchDown['flow'] + flow  # Adds branch flow to mainflow
                fitting['flow'] = flow  # Sets flow for fitting
            else:
                print("There was an error in the flow rate.")  # Error message, just in case


"""
TODO:

def get little f(dia, c, roughness)
    .
    .
    .
    f = fsolve()

def duct pressure drop(dia, flow, length, ...):
    v = ...
    f = gtlittle f (dia, c, roughness)
    .
    .
    .
    return pdrop

def get duct size(deltap,...)
    .
    .
    .
    dia = fsolve()

use chart with flow, deltap, and size to go to equation 18 to find f
"""


def get_little_f(dia, velocity, roughness):
    def func(vals):
        f = vals
        Re = 8.5 * (dia / 12) * velocity
        left_side = 1 / np.sqrt(f)
        right_right = (-1) * 2 * np.log((roughness / (3.7 * (dia / 12))) + (2.51 / (Re * np.sqrt(f))))
        return right_right - left_side

    # # need to figure out what c is
    # """
    # C_o for cd3-5 Elbow, Pleated, 90 degree
    #     dia - 4     6       8        10     12      14      16
    #     C_o - 0.57  0.43    0.34    0.28    0.26    0.25    0.25
    # """
    # f = fsolve(func, .001, full_output=True)
    finished = False
    guess = 1000000
    while not finished:
        f = fsolve(func, guess, full_output=True)
        if int(f[2]) == 1:
            finished = True
        else:
            guess = guess / 2.0
    return f[0][0]


print('test point')
print(get_little_f(24, 2000, .0003))  # should be about 0.2
"""
sd5cb = np.array([[0.65, 0.24, 0.15, 0.11, 0.09, 0.07, 0.06, 0.05, 0.05],
                [2.98, 0.65, 0.33, 0.24, 0.18, 0.15, 0.13, 0.11, 0.10],
                [7.36, 1.56, 0.65, 0.39, 0.29, 0.24, 0.20, 0.17, 0.15],
                [13.78, 2.98, 1.20, 0.65, 0.43, 0.33, 0.27, 0.24, 0.21],
                [22.24, 4.92, 1.98, 1.04, 0.65, 0.47, 0.36, 0.30, 0.26],
                [32.73, 7.36, 2.98, 1.56, 0.96, 0.65, 0.49, 0.39, 0.33],
                [45.26, 10.32, 4.21, 2.21, 1.34, 0.90, 0.65, 0.51, 0.42],
                [59.82, 13.78, 5.67, 2.98, 1.80, 1.20, 0.86, 0.65, 0.52],
                [76.41, 17.75, 7.36, 3.88, 2.35, 1.56, 1.11, 0.83, 0.65]])

sd5cs = np.array([0.13, 0.16, 0.57, 0.74, 0.74, 0.70, 0.65, 0.60, 0.56],         
                 [0.20, 0.13, 0.15, 0.16, 0.28, 0.57, 0.69, 0.74, 0.75],
                 [0.90, 0.13, 0.13, 0.14, 0.15, 0.16, 0.20, 0.42, 0.57],
                 [2.88, 0.20, 0.14, 0.13, 0.14, 0.15, 0.15, 0.16, 0.34],
                 [6.25, 0.37, 0.17, 0.14, 0.13, 0.14,  0.14, 0.15, 0.15],
                 [11.88, 0.90, 0.20, 0.13, 0.14, 0.13, 0.14, 0.14, 0.15],
                 [18.62, 1.71, 0.33, 0.18, 0.16, 0.14, 0.13, 0.15, 0.14],
                 [26.88, 2.88, 0.50, 0.20, 0.15, 0.14, 0.13, 0.13, 0.14],
                 [36.45, 4.46, 0.90, 0.30, 0.19, 0.16, 0.15, 0.14, 0.13]])

Q = np.array([.1, .2, .3, .4, .5, .6, .7, .8, .9])
A = np.array([.1, .2, .3, .4, .5, .6, .7, .8, .9])

D = np.array([4,6,8,10,12,14,16])
Co = np.array([0.57, 0.43, 0.34, 0.28, 0.26, 0.25, 0.25])
"""


def duct_pressure_drop(dia, flow, length, density, roughness):
    area = (np.pi * dia ** 2) / 4
    velocity = flow / area
    f = get_little_f(dia, velocity, roughness)
    pdrop = ((12 * f * length) / dia) * density * (velocity / 1097)
    return pdrop


def get_duct_size(deltap, flow, length, density, roughness, v):
    def func(vals):
        dia = vals
        return deltap - duct_pressure_drop(dia, flow, length, density, roughness)

    finished = False
    guess = 16
    while not finished:
        f = fsolve(func, guess, full_output=True)
        if int(f[2]) == 1:
            finished = True
        else:
            guess = guess / 2.0
    diameter = math.ceil(f[0][0])
    if diameter % 2 != 0:
        diameter += 1
    return diameter


def print_fitting(f):
    print(' ', int(f['ID']), ' ', end='')
    print(f['type'], ' ', end='')
    if f['IDup'] is not None:
        print('connects to: ', f['IDup'], end='')
    if f['BranchUP'] is not None:
        print('-', f['branchUp'])
    else:
        print('\n', end='')
    if f['length'] is not None:
        print('    length: ', f['length'])
    if f['IDdownMain'] is not None:
        print('    IDdownMain: ', int(f['IDdownMain']))
    if f['IDdownBranch'] is not None:
        print('    IDdownBranch', int(f['IDdownBranch']))
    if f['flow'] is not None:
        print('    flow: ', f['flow'])
    if f['fandist'] is not None:
        print('    fandist: ', f['fandist'])


def print_summary(ducts):
    print('title: ', ducts['title'])
    print('fan_pressure: ', ducts['fan_pressure'])
    print('air_density: ', ducts['air_density'])
    print('roughness: ', ducts['roughness'])
    print('rounding: ', ducts['rounding'])
    fittings = ducts['fittings']
    for f in fittings:
        print_fitting(f)


def main():
    file_data = read_input_file('Duct Design Sample Input.txt')
    ducts = process_keywords(file_data)
    print('After process_keywords:', end='\n\n')
    print_summary(ducts)

    # Project Progress check
    fittings = ducts['fittings']
    make_connections(fittings)
    setup_flowrates(fittings)
    setup_fan_distances(fittings)

    # Progress check 2
    for fitting in fittings:
        if fitting['type'] == 'duct':
            fitting['size'] = get_duct_size(float(ducts['fan_pressure']), fitting['flow'], fitting['length'], ducts['air_density'], ducts['roughness'], 1800)

    print('\n\nAfter setup_flowrates and setup_fan_distances: \n')
    print_summary(ducts)


if __name__ == '__main__':
    main()
