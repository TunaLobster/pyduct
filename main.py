import re


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
        line = str.lower(line)
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

    fittings = ducts['fittings']
    make_connections(fittings)
    setup_flowrates(fittings)
    setup_fan_distances(fittings)

    print('\n\nAfter setup_flowrates and setup_fan_distances: \n')
    print_summary(ducts)


if __name__ == '__main__':
    main()
