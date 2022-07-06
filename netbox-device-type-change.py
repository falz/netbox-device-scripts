#! /usr/bin/env python3
# 
#	change a netbox device type while intelligently mapping things such as interfaces
# 
#	falz 2020-08
#	https://github.com/falz/netbox-device-scripts
# 
# dependencies:
#	pip install argparse json getpass napalm pynetbox
#
# changelog:
#	2020-08-04	initial release
#	2020-08-11	fixed some incorrect me3400 interface mapping
#	2021-01-27	move config to config.py
#	2021-04-20	convert from netbox 2.8.0 to 2.11.0. Only change is device status no longer is an id, so change "2" to "planned".
#	2022-04-29	posted to github
#	2022-07-02	remove deprecated slugs
#
# todo:
#	instead of 1:1 mapping of interfaces, should we sense its type based on circuit ID and correctly assign it?
#	finalize missing console and power ports

import argparse
import pynetbox
import sys
import config as config


## see config.py for config

##########################################
## functions
def parse_cli_args(config):
	parser = argparse.ArgumentParser()
	parser.add_argument('-d', '--device',   required=True,  help='Netbox Device id - Numeric.')
	parser.add_argument('-t', '--type',	required=True,  help='Netbox Device Type to convert to. Perhaps ME-3400EG-2CS-A or ASR-920-4SZ-A')

	args = vars(parser.parse_args())

	if args['device'].isnumeric() == False:
		print("Device \"" + args['device'] + "\" is not numeric. -i should be the device ID from netbox")
		print()
		sys.exit(1)

	return(args)

def get_device(config, args):
	device = args['device']
	type = args['type'].lower()

	nb = pynetbox.api(config.netbox_url, config.netbox_api_token)
	# todo add error checking
	nb_device = nb.dcim.devices.get(device)

	print("Working on", nb_device, "(" + config.netbox_url +"dcim/devices/" + device + ") Type: ", end="")

	# check if this type is valid in netbox
	try:
		nb_device_type = nb.dcim.device_types.get(model__ie=type)
		#print(nb_device_type)
	except pynetbox.RequestError as e:
		print(e.error)
		sys.exit(1)

	nb_device_types = nb.dcim.device_types.filter(model__ie=type)

	#cant do simple 'if a in b' because one is string and other is object
	if str(type) in [str(device_type).lower() for device_type in nb_device_types]:
		print (type)
	else:
		print("")
		print("INVALID:", type, "Aborting.")
		sys.exit(1)

	return(nb, nb_device, nb_device_types)


# misc other stuff - clear serial number, change status
def fix_other(nb_device, nb_device_types, args):
	print("")
	print("Changing Serial Number from '" + nb_device.serial +"' to ''")
	print("Changing Status from", nb_device.status, "to Planned")

	update_dict=dict(
		serial="",
		status="planned",
	)

	for device_type in nb_device_types:
		if str(device_type) == args['type']:
			print("Changing Type from", nb_device.device_type, "to", args['type'])
			update_dict['device_type'] = device_type.id

	#print(update_dict)
	nb_device.update(update_dict)

	print("Done")
	return(True)


# map lan and wan interfaces. perhaps add missing here as well
def map_interfaces(config, nb_device, args):
	target_type	= args['type'].lower()
	current_type	= str(nb_device.device_type).lower()

	if current_type not in config.types:
		print("ERROR: device type", current_type, "not defined in config.py")
		print()
		sys.exit(1)

	print("")
	print("Mapping interfaces..")

	# get interfaces from netbox device
	current_interfaces	= nb.dcim.interfaces.filter(device_id=nb_device.id)

	for current_interface in current_interfaces:
		current_interface_str=str(current_interface)
		if current_interface_str in config.types[current_type]['interfaces']:
			current_interface_role = config.types[current_type]['interfaces'][current_interface_str]['role']
			current_interface_type = config.types[current_type]['interfaces'][current_interface_str]['type']
			print("Role:", current_interface_role, "Old Name:", current_interface, end='')

			for new_interface in config.types[target_type]['interfaces']:
				new_interface_str=str(new_interface)
				if current_interface_role in config.types[target_type]['interfaces'][new_interface_str]['role']:
					new_interface_role = config.types[target_type]['interfaces'][new_interface]['role']
					new_interface_type = config.types[target_type]['interfaces'][new_interface]['type']
					print(" -> New Name:", new_interface, "New Type:", new_interface_type, end='')

					netbox_interface	= nb.dcim.interfaces.get(device_id=nb_device.id, name=current_interface)
					#print(netbox_interface)

					# finally actually make the change
					update_dict = {}
					update_dict = dict(
						name	= new_interface,
						type	= new_interface_type,
					)
					#print(update_dict)
					try:
						netbox_interface.update(update_dict)
						print(" Status: OK")
					except pynetbox.lib.query.RequestError as e:
						print(e.error)
	print("Done")
	return(True)


def add_missing_interfaces(config, nb_device, nb_device_types, args):
	# use api/dcim/interface-templates/?devicetype_id=1 (well, get that id from device types)
	# loop throught them and add missing 

	# get the devicetype_id for the desired device
	for device_type in nb_device_types:
		if str(device_type) == args['type']:
			devicetype_id = device_type.id
			netbox_interfaces		= nb.dcim.interfaces.filter(device_id=nb_device.id)
			netbox_template_interfaces	= nb.dcim.interface_templates.filter(devicetype_id=device_type.id)
			print("")
			print("Creating missing interfaces:")

			for template_interface in netbox_template_interfaces:
				#comparison only works on strings
				if str(template_interface) not in [str(netbox_interface) for netbox_interface in netbox_interfaces]:
					print(template_interface, template_interface.type.value)
					create_dict = dict(
						device =	nb_device.id,
						name =		str(template_interface),
						type =		template_interface.type.value,
						enabled =	False,
					)
					#print(create_dict)
					try:
						result = nb.dcim.interfaces.create(create_dict)
					except pynetbox.RequestError as e:
						print(e.error)
			print("Done")
	return(True)


# attempt to find the template based on desired device type, then add missing console and power ports
def fix_ports_from_template(config, nb_device, args):
	return(True)


##########################################
## main
args = parse_cli_args(config)

print("Fetching netbox device", args['device'], "..")
nb, nb_device, nb_device_types = get_device(config, args)

# do this before other as the device has to be old type still
map_interfaces = map_interfaces(config, nb_device, args)
#print(interfaces)

other=fix_other(nb_device, nb_device_types, args)
#print(other)

# do this after the device type is changed
missing_interfaces = add_missing_interfaces(config, nb_device, nb_device_types, args)
