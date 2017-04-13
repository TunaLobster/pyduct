import re
from copy import deepcopy


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
				except:
					continue
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
			tee_ID = float(fitting['IDup'][:index_of_hyphen])
			tee_fitting = find_fitting(tee_ID, fittings)
			tee_fitting['IDdownMain'] = fitting['ID']
		elif branch_pattern.match(fitting['IDup']):  # branch from Tee
			# print('matched branch')
			index_of_hyphen = fitting['IDup'].find('-')
			tee_ID = int(fitting['IDup'][:index_of_hyphen])
			tee_fitting = find_fitting(tee_ID, fittings)
			tee_fitting['IDdownBranch'] = fitting['ID']
			# print(tee_ID)
			pass


def setup_fan_distances(fittings):
	pass


def setup_flowrates(fittings):
	main_pattern = re.compile(r'\d+\b-main\b')
	branch_pattern = re.compile(r'\d+\b-branch\b')
	run_fit = deepcopy(fittings)
	for fitting in run_fit:
		flow = 0.0
		if fitting['flow'] is not None:
			if fitting['IDup'] is None:
				return
			elif main_pattern.match(fitting['IDup']):  # main line from Tee
				# print('matched main')
				index_of_hyphen = fitting['IDup'].find('-')
				tee_ID = fitting['IDup'][:index_of_hyphen]
			# print(tee_ID)
			elif branch_pattern.match(fitting['IDup']):  # branch from Tee
				# print('matched branch')
				index_of_hyphen = fitting['IDup'].find('-')
				tee_ID = fitting['IDup'][:index_of_hyphen]
			# print(tee_ID)
			else:
				tee_ID = fitting['IDup']
			fittingUp = find_fitting(float(tee_ID), fittings)
			flow += fitting['flow']
			fittingUp['flow'] = flow
			print(len(run_fit))
			run_fit.remove(fitting)
			#print(len(run_fit))
			#setup_flowrates(run_fit)


def print_fitting(f):
	print(' ', f['ID'], ' ', end='')
	print(f['type'], ' ', end='')
	if f['IDup'] is not None:
		print(' connects to: ', f['IDup'], end='')
	if f['BranchUP'] is not None:
		print('-', f['branchUp'])
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
