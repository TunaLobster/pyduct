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
    # print(data)
    return data


def process_keywords(data):
    ducts = new_duct_network()
    # print('data: ', data)
    for line in data:
        # print('line: ', line)
        if line.find('#') != -1:
            continue
        else:
            item = [x.strip() for x in line.split(',')]
            # print('item: ', item)
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
                fitting['ID'] = float(item[1])
                fitting['type'] = item[2]
                try:  # checking for air handeling units and other malformed lines
                    # if fitting['type'] == '':
                    fitting['IDup'] = item[3]
                except Exception:
                    pass
                if item[2] == 'Duct':  # check for ducts. Ducts should have length feet
                    fitting['length'] = float(item[4])
                elif item[2] == 'Diffuser':  # check for diffusers. Diffusers should have flowrate in CFM
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
    main_pattern = re.compile(r'\d+\b-main\b')
    branch_pattern = re.compile(r'\d+\b-branch\b')
    # print(fittings)
    # print(find_fitting(4, fittings))

    for fitting in fittings:
        # print(type(fitting['ID']))
        # print(type(fitting['IDup']))
        if fitting['IDup'] is None:
            continue
        elif main_pattern.match(fitting['IDup']):  # main line from Tee
            # print('matched main')
            # Find index of hyphen when present
            index_of_hyphen = fitting['IDup'].find('-')
            tee_ID = int(fitting['IDup'][:index_of_hyphen])
            tee_fitting = find_fitting(tee_ID, fittings)
            tee_fitting['IDdownMain'] = fitting['ID']
        elif branch_pattern.match(fitting['IDup']):  # branch from Tee
            # print('matched branch')
            index_of_hyphen = fitting['IDup'].find('-')
            tee_ID = int(fitting['IDup'][:index_of_hyphen])
            tee_fitting = find_fitting(tee_ID, fittings)
            tee_fitting['IDdownBranch'] = fitting['ID']
            # print(tee_ID)
        else:
            fittingUp = find_fitting(float(fitting['IDup']), fittings)
            fittingUp['IDdownMain'] = fitting['ID']


def setup_fan_distances(fittings):
    # fan_distance = 0
    for fitting in fittings:
        fitting['fandist'] = 0
        if fitting['type'] == 'Air_Handling_Unit':
            # print('AHU')
            fitting['fandist'] = 0
        else:
            # if current is duct take current fandist and add length
            # apply new fandist to IDdownMain fitting
            if fitting['type'] == 'Duct':
                fan_distance = fitting['fandist'] + fitting['length']
                # print(type(fitting['IDdownMain']))
                fittingDown = find_fitting(fitting['IDdownMain'], fittings)
                fittingDown['fandist'] = fan_distance

            # if on a tee also put new fandist on branch
            elif fitting['type'] == 'Tee':
                fan_distance = fitting['fandist']
                fittingDownMain = find_fitting(fitting['IDdownMain'], fittings)
                fittingDownMain['fandist'] = fan_distance

                fittingDownBranch = find_fitting(fitting['IDdownBranch'], fittings)
                fittingDownBranch['fandist'] = fan_distance

                # fitting['fandist'] =
            elif fitting['IDup'].find('-') != -1:  # IDup is a tee
                index_of_hyphen = fitting['IDup'].find('-')
                tee_ID = int(fitting['IDup'][:index_of_hyphen])
                fittingUp = find_fitting(tee_ID, fittings)
                fitting['fandist'] = fittingUp['fandist']

                fittingDown = find_fitting(fitting['IDdownMain'], fittings)
                fittingDown['fandist'] = fan_distance
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
    # This is exhausting.
    print('roughness: ', ducts['roughness'])
    print('rounding: ', ducts['rounding'])
    fittings = ducts['fittings']
    for f in fittings:
        print_fitting(f)


def main():
    file_data = read_input_file('Duct Design Sample Input.txt')
    # print(file_data)
    ducts = process_keywords(file_data)
    # print(ducts)
    # print('After process_keywords', end='\n\n')
    # print_summary(ducts)

    fittings = ducts['fittings']
    # print('Making connections', end='\n\n')
    make_connections(fittings)
    # print('Finding flowrates and fan distances', end='\n\n')
    setup_flowrates(fittings)
    setup_fan_distances(fittings)

    print('\n\nAfter setup_fan_distances \n')
    print_summary(ducts)


if __name__ == '__main__':
    main()
