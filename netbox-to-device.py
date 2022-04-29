#! /usr/bin/env python3
# 
#	fetch a device's config from url and merge it to a device using napalm
#	falz 2020-06
#	https://github.com/falz/netbox-device-scripts
# 
# dependencies:
#	pip install argparse json getpass napalm pynetbox
#
# changelog:
#	2020-06-18	converted merge_test.py to netbox-to-device.py, adding:
#			ability to fetch config from netbox_router_config.cgi
#			ability to talk to netbox api to get some info about device, such as its priamry ip
#
#	2020-07-29	compare napalm model with netbox model, abort if they dont match
#			print out additional data about the netbox and napalm devices before the diff
#
#	2020-12-05	add optional -r/--replace option. uses netbox config_replace instead of config_merge
#			add optional -c/--config option. read config from text file instead of config generator
#
#	2021-01-27	move config to config.py
#
#	2021-07-23	colourize diff
#
#	2022-04-29	put on github https://github.com/falz/netbox-device-scripts

import argparse
import getpass
from napalm.base import get_network_driver
import os
import pynetbox
import re
import requests
import sys
import config as config
from colorama import Fore, Style

## see config.py for config

def parse_cli_args(config):
	parser = argparse.ArgumentParser()
	parser.add_argument('-d', '--device',   required=True,  help='Source Netbox Device id to fetch config from. Use numeric ID.')
	parser.add_argument('-i', '--ip',	required=False,  help='IP address or hostname to push config to. Use to override whatever Netbox returns as primary IP')
	parser.add_argument('-u', '--username', required=False, help='Username. Used for both Netbox API call and device login. Defaults to shell username.')
	parser.add_argument('-c', '--config',	required=False,  help='Config file to push to device, overrides pulling from Netbox Config Generator')
	parser.add_argument('-r', '--replace',	required=False, action='store_true', help='Config REPLACE instead of config MERGE (default). Danger, for Testing!')

	args = vars(parser.parse_args())

	if args['device'].isnumeric() == False:
		print("Device \"" + args['device'] + "\" is not numeric. -i should be the device ID from netbox")
		print()
		sys.exit(1)

	username = args['username']
	if username is None:
		username = getpass.getuser()
		args['username'] = username

	print("")
	args['password'] = getpass.getpass("Password for user \"" + username + "\" to log in to device and netbox: ")
	return(args)


def get_device(args):
	device = args['device']
	nb = pynetbox.api(config.netbox_url, config.netbox_api_token)
	# add error checking
	nb_device = nb.dcim.devices.get(device)
	return(True, nb_device)


def get_config_from_generator(config, args):
	username =	args['username']
	password =	args['password']
	url = 		config.generator_url + args['device']
	print('Fetching ' + url)
	print()

	try:   
		config_from_generator = requests.get(url, auth=(username, password), timeout=config.request_timeout)
	except requests.exceptions.RequestException as errormessage:
		print(errormessage)
		sys.exit(1)
	#check http status code as 200
	if config_from_generator.status_code != 200:
		print("")
		print("SEV0 received HTTP status code " + str(config_from_generator.status_code))
		print("Recheck password and double check if URL works: " + url)
		print("")
		sys.exit(1)
	return(config_from_generator.text)


# IOS banners have issues with ^C and they must be Ascii character 3 instead. search/replace for that here.
def sanitize_config(dirty_config_str):
	clean_config_str = re.sub(r'\^C', '\x03', dirty_config_str)
	return(clean_config_str)

def get_device_ip(args, nb_device):
	# see if passed from -i cli
	ip = args['ip']
	if ip is None:
		# try to get primary IP from netbox 	
		if nb_device.primary_ip:
			# split off /32 or /128 from primary_ip. leaving this long form for human legibility
			ip_str = str(nb_device.primary_ip)
			ip_spl = ip_str.split("/")
			ip = ip_spl[0]
		else:
			print("Cannot determine device ip. Either use '-i' flag to specify or set primary IP on netbox device")
			sys.exit(1)
	return(ip)

def get_config_file(file):
	if os.path.exists(file):
		file = open(file, 'r')
		filestr = file.read()
	else:
		print(file, "doesn't exist!")
		sys.exit(1)

	return(filestr)

def color_diff(diff):
	difflist = diff.splitlines()
	colorized_str = ''
	for line in difflist:
		if line.startswith('+'):
			colorized_str = colorized_str + Fore.GREEN + line + "\n"
		elif line.startswith('-'):
			colorized_str = colorized_str + Fore.RED + line + "\n"
		elif line.startswith('^'):
			colorized_str = colorized_str + Fore.BLUE + line + "\n"
		else:
			colorized_str = colorized_str + line + "\n"

	return(colorized_str + Style.RESET_ALL)


args = parse_cli_args(config)

sanity, nb_device = get_device(args)
if sanity == False:
	print(message) 
	sys.exit(1)
else:
	# if -c is set, read from that file
	if args['config'] is not None:
		candidate_config = get_config_file(args['config'])
	# otherwise, get from config generator
	else: 
		# perhaps do some sanity check on this to see if looks like a device config in some way
		candidate_config = get_config_from_generator(config, args)

ip = get_device_ip(args, nb_device)

platform = (str(nb_device.platform).lower())

driver = get_network_driver(platform)

if platform == "ios":
	optional_args = {
		'global_delay_factor' : 2,
	}
else:
	optional_args = {}

live_device = driver(
	hostname	= ip,
	username	= args['username'],
	password	= args['password'],
	optional_args	= optional_args
)
live_device.open()

config_str = sanitize_config(candidate_config)

if live_device.is_alive()['is_alive']:
	facts = live_device.get_facts()

	# check if netbox type matches napalm model

	if str(facts['model']) == str(nb_device.device_type):
		print("Netbox device we're retrieving config from: ")
		if args['ip']: 
			connectingto = args['ip']
		else:
			connectingto = nb_device.name
		print("	 ", connectingto, "  (", nb_device.name, ")", sep="")
		print("	", nb_device.device_type)
		print("	", "Status: ", nb_device.status)
		print("")
		print("Device we're connected to is: ")
		print("	", facts['hostname'])
		print("	", facts['model'])
		print("	", facts['serial_number'])
		print("")

		if args['replace'] == True:
			print("Generating diff using REPLACE method..")
			print("")
			live_device.load_replace_candidate(config=config_str)
		else:
			print("Generating diff using MERGE method..")
			print("")
			live_device.load_merge_candidate(config=config_str)

		diffs = live_device.compare_config()

		if diffs == "":
			print("No configuration changes required")
		else:
			color_diff = color_diff(diffs)
			print(color_diff)

			yesno = input('\nApply changes to ' + ip + '? [y/N] ').lower()
			if (yesno == 'y') or (yesno == 'yes'):
				print("Applying changes..")
				live_device.commit_config()
			else:
				print("Discarding changes..")
				live_device.discard_config()
			print("")
			print("Complete")
			print("")
	else: 
		print("Abort! Netbox device type:", nb_device.device_type,  "does not match model we're connecting to:", facts['model'])
		print("")

live_device.close()
