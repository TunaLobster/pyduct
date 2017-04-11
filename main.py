# ----------------------------
# code from Dela


def new_duct_network():
    ducts = dict(title=None, fanpressure=None, air_density=None, roughness=None, rounding=None, fittings=[])
    return ducts


def new_fitting():
    fitting = dict(ID=None, type=None, IDup=None, branchUP=None, IDdownMain=None, IDBranch=None, flow=None,
                   flowMain=None, flowBranch=None, size=None, sizeMain=None, sizeBranch=None,
                   pdrop=None, pdropMain=None, pdropBranch=None, length=None, fandist=None)
    return fitting


def read_input_file(filename):
    file = open(filename, 'r')
    data = file.readlines()
    file.close()
    return data


def process_keyworkds(data):
    pass


def find_fitting(ID, fittings):
    for fitting in fittings:
        if fitting['ID'] == ID:
            return fitting


def make_connections(fittings):
    pass


def setup_fan_distances(fittings):
    pass


def setup_flowrates(fittings):
    pass


def print_fitting(f):
    print(' ', f['ID'], ' ', end='')
    print(f['type'], ' ', end='')
    if f['IDup'] is not None:
        print(' connects to: ', f['IDup'], end='')
    if f['BranchUP'] is not None:
        print('-', f['BranchUp'])
    else:
        print('\n', end='')

    if f['length'] is not None:
        print(' length: ', f['IDdownMain'])
    if f['IDdownMain'] is not None:
        print(' IDdownMain: ', f['IDdownMain'])
    if f['flow'] is not None:
        print(' flow: ', f['flow'])
    if f['fandist'] is not None:
        print(' fandist: ', f['fandist'])


def print_summary(ducts):
    print('title: ', ducts['title'])
    print('fan_pressure: ', ducts['fan_pressure'])
    print('air_density: ', ducts)
    # This is exhausting.
    print('roughness: ', ducts['roughness'])
    print('rounding: ', ducts['rounding'])
    fittings = ducts['fittings']
    for f in fittings:
        print_fitting(f)


def main():
    file_data = read_input_file('Duct Design Sample Input')
    ducts = process_keyworkds(file_data)
    print('After process_keywords', end='\n\n')
    print_summary(ducts)

    fittings = ducts['fittings']
    make_connections(fittings)
    setup_flowrates(fittings)
    setup_fan_distances(fittings)

    print('\n\nAfter setup_fan_distances \n')
    print_summary(ducts)


# end code from Dela
# ---------------------------


if __name__ == '__main__':
    main()
