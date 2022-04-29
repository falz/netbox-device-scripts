#! /usr/bin/env python3
#
# falz 2020-03
#	https://github.com/falz/netbox-device-scripts
#
# import a production router to netbox. Uses model # to match netbox template. 
# Should work with varying degrees of success on any model that has a NAPALM driver (ios, junos, etc)
#
# dependencies:
#	pip install argparse json getpass napalm pynetbox
# 
# changelog:
#	2020-03-05	initial creation
#	2020-03-08	add IP addresses and interface ignoring lists
#	2020-03-10	set IP addresses as primary. change defaults for roles to active instead of planned
#	2020-03-10	set interface types and fall back on 'other' if not defined
#	2020-03-12	suppress paramiko juniper warnings, change try/except for pynetbox to only be pynetbox 
#			statements. added dumb message if it fails.
#	2020-03-13	add -r (role) and more user friendly output
#	2020-03-17	if it finds an IP address that already exists, it will associate it with this device. 
#			also converted the role to loopback regexp to a config option for easier tweaking
#	2021-01-27	move config to config.py
#	2021-04-20	update from netbox 2.8 to 2.11. adjust up_dict to not use 'interface' and instead use 'assigned_object_*'
#	2022-04-29	published on github at https://github.com/falz/netbox-device-scripts/
#
# issues / todo:
#
#	needs more error handling. a lot of the 'try:' statements fail silently. should be enough normal output to know what area failed (ie adding facts: bgp..)
#	searches for sites and tenants are based on lowercased slugs for those items. if your slugs have uppercase characters, currently will not work. tbd if we want to make this script more flexible or not.
#
#

import argparse
import datetime
import getpass
from ipaddress import ip_address, ip_network
import json
import napalm
import pynetbox
import re
import sys
import config as config

## see config.py for config

#these are here to suppress crypto errors from paramiko <2.5.0 related to Juniper devices. Remove once Paramiko 2.5.0+ is available.
#	https://github.com/paramiko/paramiko/issues/1369
import warnings
warnings.filterwarnings(action='ignore',module='.*paramiko.*')


# see config.py for config options

# functions

def parse_cli_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('-d', '--device',	required=True,  help='Device hostname to fetch config from')
	parser.add_argument('-m', '--model',	required=True,  help='Netbox device model name to create (example ASR-920-4SZ-A)')
	parser.add_argument('-o', '--os',	required=False, help='OS of device to fetch. Defaults to "ios" if not specified. (see NAPALM driver names)')
	parser.add_argument('-r', '--role',	required=False, help='Netbox device role. Defaults to "cpe" if not specified (See ' + config.netbox_url + 'dcim/device-roles/)')
	parser.add_argument('-s', '--site',	required=True,  help='Netbox site name to use (Example AbbotsfordSD)')
	parser.add_argument('-t', '--tenant',	required=True,  help='Netbox tenant name to use (Example AbbotsfordSD)')
	parser.add_argument('-u', '--username',	required=False, help='Username. Used for both Netbox API call and device login. Defaults to shell username.')

	args = vars(parser.parse_args()) 

	os = args['os']
	if os is None:
		os = "ios"
		args['os'] = os

	role = args['role']
	if role is None:
		args['role'] = config.device_role

	username = args['username']
	if username is None:
		username = getpass.getuser()
		args['username'] = username

	print("")
	args['password'] = getpass.getpass("Password for user \"" + username + "\" to log in to \"" + args['device'] + "\": ")
	return(args)



def check_netbox_sanity(args, nb):
	# sanity checks, return results from checks for use later
	sanitydata = {}

	device = 	args['device']
	site =		args['site'].lower()

	try:
		existingdevices = nb.dcim.devices.get(name=device, site=site)
	except pynetbox.lib.query.RequestError as e:
		print(e.error)

	if existingdevices is not None:
		message="Device " +  device + " already exists at site " + site + ": " + config.netbox_url + "dcim/devices/" + str(existingdevices.id) + "/"
		return(False, message, sanitydata)


	model = args['model']
	try:
		models = nb.dcim.device_types.get(model=model)
	except pynetbox.lib.query.RequestError as e:
		print(e.error)

	if models is None:
		message="Model " + model + " doesn't exist!"
		return(False, message, sanitydata)
	else:
		sanitydata['model'] = models


	site = args['site']
	sites = nb.dcim.sites.get(slug=site.lower())
	if sites is None:
		message = "Site " + site + " doesn't exist!"
		return(False, message, sanitydata)
	else:
		sanitydata['site'] = sites


	tenant = args['tenant']
	try:
		tenants = nb.tenancy.tenants.get(slug=tenant.lower())
	except pynetbox.lib.query.RequestError as e:
		print(e.error)

	if tenants is None:
		message = "Tenant " + tenant + " doesn't exist!"
		return(False, message, sanitydata)
	else:
		sanitydata['tenant'] = tenants


	message="Netbox sanity checks: Done"

	return(True, message, sanitydata)


def get_device_info(args):
	# todo - add more error handling (check if napalm installed, if the driver passed is legit

	print("")
	print("Connecting to " + args['device'] + ":", end='')
	try:
		driver = napalm.get_network_driver(args['os'])
		napalmdevice = driver(args['device'], args['username'], args['password'])
		napalmdevice.open()
	except:
		print(" ERROR: Can't connect to", args['device'], "for some reason! Check hostname, password, OS")
		return(False)
	print(" Done")


	device_dict = {}
	print("")
	print("Getting info:", end='')

	try:
		print(" Facts", end='')
		facts = napalmdevice.get_facts()
		device_dict['facts'] = facts
	except:
		return(False, device_dict)


	try:
		print(" Interfaces", end='')
		interfaces = napalmdevice.get_interfaces()

		# use lists for easy comparison
		interfaces_list = list(interfaces.keys())
		bad_if_list = config.bad_if_regex

		pattern = re.compile("|".join(bad_if_list), flags=re.IGNORECASE | re.MULTILINE)
		good_interface_list = [ i for i in interfaces_list if not pattern.match(i) ]
		bad_interface_list =  [ i for i in interfaces_list if pattern.match(i) ]

		good_interfaces = {}
		for interface_key, interface_val in interfaces.items():
			if interface_key in good_interface_list:
				good_interfaces[interface_key] = interface_val


		bad_interfaces = {}
		for interface_key, interface_val in interfaces.items():
			if interface_key in bad_interface_list:
				bad_interfaces[interface_key] = interface_val


		device_dict['good_interfaces'] = good_interfaces
		device_dict['bad_interfaces'] = bad_interfaces

	except:
		return(False, device_dict)

	try:
		print(" IPs", end='')
		ips = napalmdevice.get_interfaces_ip()
		device_dict['ips'] = ips

	except:
		return(False, device_dict)


	try:
		print(" BGP", end='')
		bgp = napalmdevice.get_bgp_neighbors()
		device_dict['bgp'] = bgp
	except:
		device_dict['bgp'] = {}

	print (" Done")

	return (True, device_dict)

def create_netbox_device(config, nb, args, device_dict, sanitydata):

	print("")
	print("Creating netbox device: ", end='')
	try:
		role = nb.dcim.device_roles.get(slug=args['role'])
		platform = nb.dcim.platforms.get(slug=args['os'])
	except pynetbox.lib.query.RequestError as e:
		print(e.error)

	now =		datetime.datetime.now()
	timestamp =	now.strftime("%Y-%m-%d %H:%M:%S")

	create_dict = {}
	create_dict =dict(
		name =		args['device'],
		device_type =	sanitydata['model'].id,
		device_role =	role.id,
		platform =	platform.id,
		serial =	device_dict['facts']['serial_number'],
		tenant =	sanitydata['tenant'].id,
		site =		sanitydata['site'].id,
		status =	config.device_status,
		comments =	"Created " + timestamp + " via import script by " + args['username'],
	)

	try:
		result = nb.dcim.devices.create(create_dict)
	except pynetbox.lib.query.RequestError as e:
		print(e.error)

	print("Done - " + config.netbox_url + "dcim/devices/" + str(result.id) + "/")

	return(result)

# use this for nonstandard nontemplate interfaces such as vlan
def add_interfaces(config, nb, args, device_dict, device_result):

	# get existing interfaces from netbox, keep one orig and another a list of strings for easier comparison
	try:
		netbox_interfaces=nb.dcim.interfaces.filter(device_id=device_result.id)
	except pynetbox.lib.query.RequestError as e:
		print(e.error)

	# uses lists to more easily compare
	netbox_interfaces_list = [str(i) for i in netbox_interfaces]
	device_interfaces = list(device_dict['good_interfaces'].keys())

	# compare the two to create a new list of interfaces to add
	missing_interfaces = list(set(device_interfaces) - set(netbox_interfaces_list))
	#print(missing_interfaces)

	print("")
	print("Adding interfaces:", end='')
	for interface in missing_interfaces:
		interface_type = "other"
		# map interface types. This almost certainly could get condensed.
		for platform_key, platform_val in config.interface_map.items():
			if platform_key == args['os']:
				for interface_match, netbox_type in platform_val.items():
					if re.match(interface_match, interface, re.IGNORECASE):
						interface_type = netbox_type
						#print(interface_type)
						# probably a better way to break out of this
						continue


		try:
			nb.dcim.interfaces.create(
				device =	device_result.id,
				name =		interface,
				type =		interface_type,
			)
			print(" " + interface, end='')

		except pynetbox.lib.query.RequestError as e:
			print(e.error)

	print(" Done")

	# print out skipped interfaces because why not
	print("")
	print("Skipping interfaces:", end='')
	for bad_interface in device_dict['bad_interfaces']:
		print (" " + bad_interface, end='')

	print(" Done")

	return(missing_interfaces)


# add IP's to interfaces that we hope already exist
def update_interfaces(config, nb, args, device_dict, device_result):

	device_interfaces={}
	device_interfaces=device_dict['good_interfaces']

	print("")
	print("Updating interfaces:", end='')

	for interface_key, interface_val in device_interfaces.items():
		try:
			netbox_interface=nb.dcim.interfaces.get(device_id=device_result.id,name=interface_key)
		except pynetbox.lib.query.RequestError as e:
			print(e.error)

		update_dict = {}
		update_dict = dict(
			enabled 	= interface_val['is_enabled'],
			description	= interface_val['description'],
		)
		try:
			netbox_interface.update(update_dict)
			print(" " + interface_key,  end='')

		except pynetbox.lib.query.RequestError as e:
			print(e.error)

	print(" Done")

	return()

def bad_ip_check(config, ip_check):
	for bad_net in config.bad_ip:
		if ip_address(ip_check) in ip_network(bad_net):
			return(True)
	return(False)


def add_ips(config, nb, args, device_dict, device_result, sanitydata):
	# dealing with something like:
	#(
	#   "Vlan3000",
	#   {
	#      "ipv4":{
	#         "140.189.80.186":{
	#            "prefix_length":30
	#         }
	#      }
	#   }
	#)

	# we need the tenant id to add
	netbox_tenant = sanitydata['tenant']

	print("")
	print("Adding IP addresses:", end='')
	for interface_key, interface_val in device_dict['ips'].items():
		for family_key, family_value in interface_val.items():
			for ip_key, ip_val in family_value.items():
				# if we concat stuff together, do it hear to keep the section below cleaner + for re-usibility
				address = ip_key + "/" + str(ip_val['prefix_length'])
				description = device_result.name + " " + interface_key

				# check if this is in bad_ip list
				if not bad_ip_check(config, ip_key):

					print(" " + address, end='')

					# get interface associated with this IP
					try:
						netbox_interface=nb.dcim.interfaces.get(device_id=device_result.id, name=interface_key)
					except pynetbox.lib.query.RequestError as e:
						print(e.error)


					ip_dict = {}
					ip_dict = dict(
						# api change in 2.9.0 - https://github.com/netbox-community/netbox/releases/tag/v2.9.0
						#interface =		netbox_interface.id,
						assigned_object_id =	netbox_interface.id,
						assigned_object_type =	"dcim.interface",
						address =		address,
						status =		config.ip_status,
						tenant =		netbox_tenant.id,
						description =		description,
					)

					interface_role = ""
					# todo: support more interface_roles and loop through them, even if it's only one item
					if re.search(config.interface_roles['loopback'], interface_key, re.IGNORECASE):
						interface_role = "loopback"
						ip_dict['role'] = interface_role


					#Check if IP already exists, if so update it. if not, add it.
					try:
						netbox_ip = nb.ipam.ip_addresses.get(q=address)
					except pynetbox.lib.query.RequestError as e:
						print(e.error)

					if netbox_ip:
						print(" (updated)", end='')
						try:
							netbox_ip.update(ip_dict)
						except pynetbox.lib.query.RequestError as e:
							print(e.error)

					else:
						try:
							netbox_ip = nb.ipam.ip_addresses.create(ip_dict)
						except pynetbox.lib.query.RequestError as e:
							print(e.error)



					# do this after the ip is created
					if interface_role == "loopback":
						try:
							device_role = nb.dcim.device_roles.get(slug=args['role'])
						except pynetbox.lib.query.RequestError as e:
							print(e.error)

						update_dict = {}
						update_dict = dict(
							device_type =	sanitydata['model'].id,
							device_role =	device_role,
							site =		sanitydata['site'].id,
						)
						if family_key == "ipv4":
							update_dict['primary_ip4'] =	netbox_ip.id

						if family_key == "ipv6":
							update_dict['primary_ip6'] =	netbox_ip.id

						update_device(nb, device_result, update_dict)
						print(" (primary)", end='')

	print(" Done")
	return(True)


def update_device(nb, device_result, update_dict):
	try:
		device = nb.dcim.devices.get(device_result.id)
		device.update(update_dict)
	except pynetbox.lib.query.RequestError as e:
		print(e.error)
	return()


def update_ip(nb, device_result, update_dict):
	#todo if we want this functionalty (update an ip if we find a duplicate)
	return()


def update_prefix(nb, device_result, update_dict):
	# placeholder, perhaps take this opportunity to fix site/tenant on prefixes, which are the direct parent of IPs discovered?
	# it's not easy to find direct parent prefix, if we do this we'd have to iterate through all parents and find the ones with the most specific?
	# also this makes sense for members conenctions, but probably not hubs
	return()


def prettyprint(dict):
	print(json.dumps(dict, indent=4, sort_keys=True, separators=(',', ': ')))
	return()

def pretty_summary(args):
	print("Connection summary:")
	print("")
	print("\tuser:\t" + args['username'])
	print("\tdevice:\t" + args['device'])
	print("\tmodel:\t" + args['model'])
	print("\tos:\t" + args['os'])
	print("\trole:\t" + args['role'])
	print("\tsite:\t" + args['site'])
	print("\ttenant:\t" + args['tenant'])
	print("")
	return()

# main stuff. probs move this to a __main__ function?

args = parse_cli_args()

pretty_summary(args)



#connect to netbox api
nb = pynetbox.api(config.netbox_url, config.netbox_api_token)

#do some super basic checks with netbox API based on CLI args before even logging in to a device
sanity, message, sanitydata = check_netbox_sanity(args, nb)
if sanity == False:
	print(message)
	sys.exit(1)
else: 
	print(message)
	devicestatus, device_dict = get_device_info(args)

	if devicestatus == True:
		#prettyprint(device_dict['facts'])
		device_result = create_netbox_device(config, nb, args, device_dict, sanitydata)
		#print(device_result)

		# add interfaces
		add_interfaces_result = add_interfaces(config, nb, args, device_dict, device_result)
		#print(add_interfaces_result)

		# update interfaces
		update_interfaces_result = update_interfaces(config, nb, args, device_dict, device_result)
		#print(update_interfaces_result)

		# add ip addresses to interfaces
		ips_result = add_ips(config, nb, args, device_dict, device_result, sanitydata)
		#print(ips_result)

		print("")
		print("Device added successfully.")
		print("")

