import re
import sys
import warnings

import numpy as np
from scipy.optimize import fsolve

# suppress sqrt warning. it's going to happen. Don't really care if it does.
warnings.filterwarnings('ignore', 'invalid value encountered in sqrt')


def new_duct_network():
    ducts = dict(title=None, fan_pressure=None, air_density=None, roughness=None, rounding=None, fittings=[])
    return ducts


def new_fitting():
    fitting = dict(ID=None, type=None, IDup=None, BranchUP=None, IDdownMain=None, IDdownBranch=None, flow=None,
                   flowMain=None, flowBranch=None, size=None, sizeMain=None, sizeBranch=None,
                   pdrop=None, pdropMain=None, pdropBranch=None, length=None, fandist=None, diffuser_psum=None)
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


def get_little_f(dia, velocity, roughness):
    def func(vals):
        f = vals
        Re = 8.5 * (dia / 12) * velocity  # eqn (21)

        # eqn (19) 2013 version corrected for units
        left_side = 1 / np.sqrt(f)
        right_right = (-1) * 2 * np.log10((roughness / (3.7 * (dia / 12))) + (2.51 / (Re * np.sqrt(f))))
        return (right_right - left_side)

    guess = 10
    finished = False
    while not finished:
        f = fsolve(func, guess, full_output=True)
        if int(f[2]) == 1:  # check solution flag
            finished = True
        else:
            guess = guess / 2.0  # update guess
    return f[0][0]


def largest_path(fittings):  # Finds the diffuser with the longest path to the fan
    fitting_compare = find_fitting(1, fittings)  # Sets the initial fitting that will be compared
    for fitting in fittings:
        if fitting['type'] == 'diffuser':
            if fitting['fandist'] > fitting_compare['fandist']:  # compare fan distances
                fitting_compare = fitting  # sets new comparison
    return fitting_compare


def duct_pressure_drop(dia, flow, length, density, roughness):  # dia [inches], length [ft]
    area = (np.pi * (dia / 12) ** 2) / 4  # [ft^2]
    velocity = flow / area  # [ft/min=fpm]
    f = get_little_f(dia, velocity, roughness)
    pdrop = ((12 * f * length) / (dia / 12)) * density * (velocity / 1097) ** 2
    return pdrop


# Nick and Charlie
def pressure_drop_sum(ID, fittings):  # calculates total pressure loss of ANY RUN
    # find the fitting dictionary attached to the ID in quesiton
    fitting = find_fitting(int(ID), fittings)
    route = [int(fitting['ID'])]
    main_pattern = re.compile(r'\d+\b-main\b')
    branch_pattern = re.compile(r'\d+\b-branch\b')

    # find route IDs
    while fitting['type'] != 'air_handling_unit':  # while not at the air handler
        if main_pattern.match(fitting['IDup']):  # matching main if IDup is tee
            index_of_hyphen = fitting['IDup'].find('-')
            ID = int(fitting['IDup'][:index_of_hyphen])
            route.append(ID)
            fitting = find_fitting(ID, fittings)
        elif branch_pattern.match(fitting['IDup']):  # matching branch if IDup is tee
            index_of_hyphen = fitting['IDup'].find('-')
            ID = int(fitting['IDup'][:index_of_hyphen])
            route.append(ID)
            fitting = find_fitting(ID, fittings)
        else:
            ID = int(fitting['IDup'])
            route.append(ID)
            fitting = find_fitting(ID, fittings)

    pdrop_sum = 0
    for i in range(len(route)):
        fitting = find_fitting(int(route[i]), fittings)
        if fitting['type'] == 'duct' or fitting['type'] == 'elbow':
            pdrop_sum += fitting['pdrop']
        elif fitting['type'] == 'tee':
            # next downstream fitting ID
            next_fitting_ID = route[i - 1]
            if next_fitting_ID == fitting['IDdownMain']:
                pdrop_sum += find_fitting(int(next_fitting_ID), fittings)['pdropMain']
            elif next_fitting_ID == fitting['IDdownBranch']:
                pdrop_sum += find_fitting(int(next_fitting_ID), fittings)['pdropBranch']
    return pdrop_sum


def fitting_loss_sum(fittings):  # calculates total pressure loss of tees and elbows only, of LONGEST RUN
    farthest_fitting = largest_path(fittings)
    fitting = farthest_fitting
    longest_route = [int(fitting['ID'])]
    main_pattern = re.compile(r'\d+\b-main\b')
    branch_pattern = re.compile(r'\d+\b-branch\b')

    # find longest route using farthest diffusers
    while fitting['type'] != 'air_handling_unit':  # while not at the air handler
        if main_pattern.match(fitting['IDup']):  # matching main if IDup is tee
            index_of_hyphen = fitting['IDup'].find('-')
            ID = int(fitting['IDup'][:index_of_hyphen])
            longest_route.append(ID)
            fitting = find_fitting(ID, fittings)
        elif branch_pattern.match(fitting['IDup']):  # matching branch if IDup is tee
            index_of_hyphen = fitting['IDup'].find('-')
            ID = int(fitting['IDup'][:index_of_hyphen])
            longest_route.append(ID)
            fitting = find_fitting(ID, fittings)
        else:
            ID = int(fitting['IDup'])
            longest_route.append(ID)
            fitting = find_fitting(ID, fittings)

    pdrop_fitloss_sum = 0
    for i in range(len(longest_route)):
        fitting = find_fitting(int(longest_route[i]), fittings)
        if fitting['type'] == 'elbow':
            pdrop_fitloss_sum += fitting['pdrop']
        elif fitting['type'] == 'tee':
            # next downstream fitting ID
            next_fitting_ID = longest_route[i - 1]
            if next_fitting_ID == fitting['IDdownMain']:
                pdrop_fitloss_sum += find_fitting(int(next_fitting_ID), fittings)['pdropMain']
            elif next_fitting_ID == fitting['IDdownBranch']:
                pdrop_fitloss_sum += find_fitting(int(next_fitting_ID), fittings)['pdropBranch']
    return pdrop_fitloss_sum


def get_duct_size(deltap, flow, length, density, roughness):
    def func(vals):
        dia = vals
        return deltap - duct_pressure_drop(dia, flow, length, density, roughness)

    finished = False
    guess = .01
    while not finished:
        # print(guess)
        f = fsolve(func, guess, full_output=True)
        if int(f[2]) == 1:
            finished = True
        else:
            guess = guess * 2.0
    diameter = f[0][0]
    return diameter


def findBetween(x, xlist):
    # iterate over xlist to find where x fits in
    for position in range(0, len(xlist) - 1):
        # check if the current iteration in xlist is good
        if (xlist[position] <= x <= xlist[position + 1]) or (xlist[position] >= x >= xlist[position + 1]):
            return position


def interp1D(x, xlist, ylist):
    # find between value
    position = findBetween(x, xlist)

    # gather needed numbers from xlist and ylist
    x1 = xlist[position]
    x3 = xlist[position + 1]
    y1 = ylist[position]
    y3 = ylist[position + 1]

    # interpolate value of y
    y = (((x - x1) * (y3 - y1)) / (x3 - x1)) + y1
    return y


def interp2D(x, y, xlist, ylist, zmatrix):
    # find the correct column to use
    yposition = findBetween(y, ylist)

    # extract and interpolate each column
    x1 = interp1D(x, xlist, zmatrix[:, yposition])
    x2 = interp1D(x, xlist, zmatrix[:, yposition + 1])

    # interpolate between columns
    z = interp1D(y, ylist[yposition:yposition + 2], [x1, x2])
    return z


def tee_pressure_drop(dia, density, flow, outlet_flow, outlet_dia, branch):
    '''

    :param dia:
    :param density:
    :param flow:
    :param outlet_flow:
    :param outlet_dia:
    :param branch: Boolean
    :return:
    '''
    Q = np.array([.1, .2, .3, .4, .5, .6, .7, .8, .9])  # top most row Q_(branch/main)/Q_common
    A = np.array([.1, .2, .3, .4, .5, .6, .7, .8, .9])  # right most column A_(branch/main)/A_common

    # Table from 2009 ASHRAE Handbook 21.50 for SD5-10 Tee, Concial Branch Tapered into Body, Diverging
    # c_branch values
    sd5cb = np.array([[0.65, 0.24, 0.15, 0.11, 0.09, 0.07, 0.06, 0.05, 0.05],
                      [2.98, 0.65, 0.33, 0.24, 0.18, 0.15, 0.13, 0.11, 0.10],
                      [7.36, 1.56, 0.65, 0.39, 0.29, 0.24, 0.20, 0.17, 0.15],
                      [13.78, 2.98, 1.20, 0.65, 0.43, 0.33, 0.27, 0.24, 0.21],
                      [22.24, 4.92, 1.98, 1.04, 0.65, 0.47, 0.36, 0.30, 0.26],
                      [32.73, 7.36, 2.98, 1.56, 0.96, 0.65, 0.49, 0.39, 0.33],
                      [45.26, 10.32, 4.21, 2.21, 1.34, 0.90, 0.65, 0.51, 0.42],
                      [59.82, 13.78, 5.67, 2.98, 1.80, 1.20, 0.86, 0.65, 0.52],
                      [76.41, 17.75, 7.36, 3.88, 2.35, 1.56, 1.11, 0.83, 0.65]])
    # c_main values
    sd5cm = np.array([[0.13, 0.16, 0.57, 0.74, 0.74, 0.70, 0.65, 0.60, 0.56],
                      [0.20, 0.13, 0.15, 0.16, 0.28, 0.57, 0.69, 0.74, 0.75],
                      [0.90, 0.13, 0.13, 0.14, 0.15, 0.16, 0.20, 0.42, 0.57],
                      [2.88, 0.20, 0.14, 0.13, 0.14, 0.15, 0.15, 0.16, 0.34],
                      [6.25, 0.37, 0.17, 0.14, 0.13, 0.14, 0.14, 0.15, 0.15],
                      [11.88, 0.90, 0.20, 0.13, 0.14, 0.13, 0.14, 0.14, 0.15],
                      [18.62, 1.71, 0.33, 0.18, 0.16, 0.14, 0.13, 0.15, 0.14],
                      [26.88, 2.88, 0.50, 0.20, 0.15, 0.14, 0.13, 0.13, 0.14],
                      [36.45, 4.46, 0.90, 0.30, 0.19, 0.16, 0.15, 0.14, 0.13]])
    area = (np.pi * (dia / 12) ** 2) / 4
    velocity = flow / area
    p_v = density * (velocity / 1097) ** 2
    A_common = (np.pi * (dia / 12) ** 2) / 4
    A_outlet = (np.pi * (outlet_dia / 12) ** 2) / 4
    area_ratio = A_outlet / A_common
    flow_ratio = outlet_flow / flow

    # protect from extrapolating on the table
    if area_ratio > .9:
        area_ratio = .9
    elif area_ratio < .1:
        area_ratio = .1
    if flow_ratio > .9:
        flow_ratio = .9
    elif flow_ratio < .1:
        flow_ratio = .1
    if branch:
        c_branch = interp2D(area_ratio, flow_ratio, A, Q, sd5cb)
        pdrop = c_branch * p_v
    else:
        c_main = interp2D(area_ratio, flow_ratio, A, Q, sd5cm)
        pdrop = c_main * p_v
    return pdrop


def elbow_pressure_drop(dia, flow, density):
    # Table from ASHRAE 2009 chapter 21 for pleated 90 degree elbow
    D = np.array([4, 6, 8, 10, 12, 14, 16])
    Co = np.array([0.57, 0.43, 0.34, 0.28, 0.26, 0.25, 0.25])

    # protect from extrapolating on the table
    if dia >= 16:
        c_o = 0.25
    elif dia <= 4:
        c_o = 0.57
    else:
        c_o = interp1D(dia, D, Co)

    area = (np.pi * (dia / 12) ** 2) / 4
    velocity = flow / area
    p_v = density * (velocity / 1097) ** 2
    pdrop = c_o * p_v
    return pdrop


# Nick Nelsen 5/4/17
def sizing_iterate_nick(ducts):
    # assign for easier use later
    density = ducts['air_density']
    roughness = ducts['roughness']
    fan_pressure = ducts['fan_pressure']
    fittings = ducts['fittings']
    maxlength = largest_path(fittings)['fandist']

    # take care of nonetype errors the cheesy way
    for fitting in fittings:
        if fitting['pdrop'] is None:
            fitting['pdrop'] = 0.0
        if fitting['pdropMain'] is None:
            fitting['pdropMain'] = 0.0
        if fitting['pdropBranch'] is None:
            fitting['pdropBranch'] = 0.0

    psum = fitting_loss_sum(fittings)
    dpdl = (fan_pressure - psum) / maxlength
    dpdl_old = 0
    count = 0
    # main loop to size ducts first, then elbows, and finally tees
    while abs(dpdl - dpdl_old) >= 1e-10:
        for fitting in fittings:  # solving ducts
            if fitting['type'] == 'duct':
                length = fitting['length']
                deltap = dpdl * length
                flow = fitting['flow']
                diameter = get_duct_size(deltap, flow, length, density, roughness)
                fitting['size'] = diameter
                # p_duct = duct_pressure_drop(diameter, flow, length, density, roughness)
                p_duct = deltap
                # print(p_duct, p_duct2)
                fitting['pdrop'] = p_duct

        for fitting in fittings:  # solving elbows
            if fitting['type'] == 'elbow':
                down_fitting = find_fitting(int(fitting['IDdownMain']), fittings)
                if down_fitting['type'] == 'duct':
                    e_diameter = down_fitting['size']
                    p_elbow = elbow_pressure_drop(e_diameter, fitting['flow'], density)
                    fitting['size'] = e_diameter
                    fitting['pdrop'] = p_elbow

                # if up_fitting is a tee
                elif fitting['IDup'].find('-') != -1:
                    index_of_hyphen = fitting['IDup'].find('-')
                    tee_ID = int(fitting['IDup'][:index_of_hyphen])
                    up_fitting = find_fitting(tee_ID, fittings)
                    e_diameter = up_fitting['size']
                    p_elbow = elbow_pressure_drop(e_diameter, fitting['flow'], density)
                    fitting['size'] = e_diameter
                    fitting['pdrop'] = p_elbow
                # if up_fitting has no hyphen
                else:
                    up_fitting = find_fitting(int(fitting['IDup']), fittings)
                    # if up_fitting['size'] is not None:
                    e_diameter = up_fitting['size']
                    p_elbow = elbow_pressure_drop(e_diameter, fitting['flow'], density)
                    fitting['size'] = e_diameter
                    fitting['pdrop'] = p_elbow

        for fitting in fittings:  # solving tees
            if fitting['type'] == 'tee':
                up_fitting = find_fitting(int(fitting['IDup']), fittings)
                tee_inlet_diameter = up_fitting['size']
                p_tee_main = tee_pressure_drop(tee_inlet_diameter, density, fitting['flow'],
                                               find_fitting(fitting['IDdownMain'], fittings)['flow'],
                                               find_fitting(fitting['IDdownMain'], fittings)['size'], False)
                p_tee_branch = tee_pressure_drop(tee_inlet_diameter, density, fitting['flow'],
                                                 find_fitting(fitting['IDdownBranch'], fittings)['flow'],
                                                 find_fitting(fitting['IDdownBranch'], fittings)['size'], True)
                fitting['size'] = tee_inlet_diameter
                fitting['sizeMain'] = find_fitting(fitting['IDdownMain'], fittings)['size']
                fitting['sizeBranch'] = find_fitting(fitting['IDdownBranch'], fittings)['size']
                fitting['pdropMain'] = p_tee_main
                fitting['pdropBranch'] = p_tee_branch

        psum = fitting_loss_sum(fittings)
        dpdl_old = dpdl
        dpdl = (fan_pressure - psum) / maxlength

    for fitting in fittings:
        if fitting['type'] == 'diffuser':
            fitting['diffuser_psum'] = pressure_drop_sum(int(fitting['ID']), fittings)

    # rounding stuff
    if ducts['rounding'] is not None:
        if ducts['rounding'] == 'nearest':
            for fitting in fittings:
                if fitting['type'] != 'air_handling_unit' and fitting['type'] != 'diffuser':
                    fitting['size'] = round(fitting['size'])
                    if fitting['type'] == 'tee':
                        fitting['sizeMain'] = round(fitting['sizeMain'])
                        fitting['sizeBranch'] = round(fitting['sizeBranch'])
        elif ducts['rounding'] == 'up':
            for fitting in fittings:
                if fitting['type'] != 'air_handling_unit' and fitting['type'] != 'diffuser':
                    fitting['size'] = np.ceil(fitting['size'])
                    if fitting['type'] == 'tee':
                        fitting['sizeMain'] = np.ceil(fitting['sizeMain'])
                        fitting['sizeBranch'] = np.ceil(fitting['sizeBranch'])
        elif ducts['rounding'] == 'down':
            for fitting in fittings:
                if fitting['type'] != 'air_handling_unit' and fitting['type'] != 'diffuser':
                    fitting['size'] = np.floor(fitting['size'])
                    if fitting['type'] == 'tee':
                        fitting['sizeMain'] = np.floor(fitting['sizeMain'])
                        fitting['sizeBranch'] = np.floor(fitting['sizeBranch'])

        # recalculate pdrop everything after rounding
        for fitting in fittings:
            if fitting['type'] == 'duct':
                fitting['pdrop'] = duct_pressure_drop(fitting['size'], fitting['flow'], fitting['length'], density,
                                                      roughness)
            elif fitting['type'] == 'tee':
                fitting['flowMain'] = find_fitting(int(fitting['IDdownMain']), fittings)['flow']
                fitting['pdropMain'] = tee_pressure_drop(fitting['size'], density, fitting['flow'], fitting['flowMain'],
                                                         fitting['sizeMain'], False)
                fitting['flowBranch'] = find_fitting(int(fitting['IDdownBranch']), fittings)['flow']
                fitting['pdropBranch'] = tee_pressure_drop(fitting['size'], density, fitting['flow'],
                                                           fitting['flowBranch'], fitting['sizeBranch'], True)
            elif fitting['type'] == 'elbow':
                fitting['pdrop'] = elbow_pressure_drop(fitting['size'], fitting['flow'], density)

    # finally apply sizes to diffuers
    for fitting in fittings:
        if fitting['type'] == 'diffuser':
            fitting['size'] = find_fitting(int(fitting['IDup']), fittings)['size']

    return


def print_results(fittings):
    # file=open("pyductresults.txt","w")
    print('ID'.rjust(4), 'Fitting'.rjust(20), 'Velocity (fpm)'.rjust(15), 'Q (cfm)'.rjust(15), 'DeltaP (in. wg)'.rjust(16),
          'Diameter (in)'.rjust(17), 'Diffuser pressure (in. wg)'.rjust(25))
    print('-'*120)
    orig_stdout = sys.stdout
    file = open("pyductresult.txt", "w+")
    sys.stdout = file
    print('ID'.rjust(4), 'Fitting'.rjust(20), 'Velocity (fpm)'.rjust(15), 'Q (cfm)'.rjust(15), 'DeltaP (in. wg)'.rjust(16),
          'Diameter (in)'.rjust(17), 'Diffuser pressure (in. wg)'.rjust(25))
    print('-'*120)
    sys.stdout = orig_stdout
    for fitting in fittings:
        if fitting['type'] != 'air_handling_unit':
            # TODO: @sziske needs to fix this
            # velocity = 5
            velocity = fitting['flow'] / (np.pi * (fitting['size'] / 12) * (fitting['size'] / 12))
        else:
            velocity = 0.0
            fitting['size'] = 0.0
        if fitting['pdrop'] is None:
            fitting['pdrop'] = 0.0
        if fitting['size'] is None:
            fitting['size'] = 0.0
        if fitting['diffuser_psum'] is None:
            print(repr(fitting['ID']).rjust(4), fitting['type'].rjust(20), ("%.3f" % velocity).rjust(15),
                  ("%.1f" % fitting['flow']).rjust(15), ("%.3f" % fitting['pdrop']).rjust(16),
                  ("%.3f" % fitting['size']).rjust(17))
            orig_stdout = sys.stdout
            sys.stdout = file
            print(repr(fitting['ID']).rjust(4), fitting['type'].rjust(20), ("%.3f" % velocity).rjust(15),
                  ("%.1f" % fitting['flow']).rjust(15), ("%.3f" % fitting['pdrop']).rjust(16),
                  ("%.3f" % fitting['size']).rjust(17))
            sys.stdout = orig_stdout
        else:
            print(repr(fitting['ID']).rjust(4), fitting['type'].rjust(20), ("%.3f" % velocity).rjust(15),
                  ("%.1f" % fitting['flow']).rjust(15), ("%.3f" % fitting['pdrop']).rjust(16),
                  ("%.3f" % fitting['size']).rjust(17), ("%.3f" % fitting['diffuser_psum']).rjust(25))
            orig_stdout = sys.stdout
            sys.stdout = file
            print(repr(fitting['ID']).rjust(4), fitting['type'].rjust(20), ("%.3f" % velocity).rjust(15),
                  ("%.1f" % fitting['flow']).rjust(15), ("%.3f" % fitting['pdrop']).rjust(16),
                ("%.3f" % fitting['size']).rjust(17), ("%.3f" % fitting['diffuser_psum']).rjust(25))
            sys.stdout = orig_stdout

    file.close()


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
    if f['size'] is not None:
        print('    size: ', f['size'])
    if f['pdrop'] is not None:
        print('    pdrop: ', f['pdrop'])
    if f['pdropMain'] is not None:
        print('    pdropMain: ', f['pdropMain'])
    if f['pdropBranch'] is not None:
        print('    pdropBranch: ', f['pdropBranch'])
    if f['diffuser_psum'] is not None:
        print('    diffuser_psum: ', f['diffuser_psum'])


def print_summary(ducts):
    print('title: ', ducts['title'])
    print('fan_pressure: ', ducts['fan_pressure'])
    print('air_density: ', ducts['air_density'])
    print('roughness: ', ducts['roughness'])
    print('rounding: ', ducts['rounding'])
    fittings = ducts['fittings']
    for f in fittings:
        print_fitting(f)


def calculate(filename):
    file_data = read_input_file(filename)
    ducts = process_keywords(file_data)
    fittings = ducts['fittings']
    make_connections(fittings)
    setup_flowrates(fittings)
    setup_fan_distances(fittings)
    sizing_iterate_nick(ducts)
    print_results(fittings)


if __name__ == '__main__':
    # filename = 'Duct Design Sample Input.txt'
    # calculate(filename)
    print('Please run from main.py')
