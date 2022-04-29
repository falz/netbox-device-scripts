#! /usr/bin/env python3
#
#	https://github.com/falz/netbox-device-scripts
#
#	config file for netbox device scripts. 

##########################################
#### common stuff

netbox_url =		"https://netbox.example.org/"
netbox_api_token =	"CREATEME"
request_timeout = 	10

##########################################
#### netbox-to-device stuff

generator_url =       "https://netbox.example.org/cgi-bin/netbox_router_config.cgi?device="


##########################################
#### device-to-netbox stuff

device_role =		"cpe"		# default device role (-r)
device_status = 	"active"	# default device status (no current flag)
os = 			"ios"		# default os / napalm driver (-o)
ip_status =		"active"	# default ip statis (no current flag)

# interfaces you don't want to import.  case insensitive + multiline flags given
bad_if_regex =	['^vlan1$', '^bme.*', '^cbp.*',
		'^esi.*', '^.local.*',
		'^dsc.*', '^demux.*',
		'em\d\.*', 'fti.*',
		'gr', 'gre',
		'ipip', 'jsrv.*', 'lsi', 'mtun', 
		'pfe.*', 'pfh.*', '^pim.*', 'pip.*', 'pp\d/*.*'
		'rbeb', 'sxe', 'tap', 'vme', 'vtep',
		'.*\.16385$', '.*\.3276\d$', '.*\.3277\d$'
]

# IP's to ignore and not import
bad_ip = [ 'fe80::/10', 'fd00::/8',
	'10.0.0.0/8',
	'172.16.0.0/12',
	'192.168.0.0/16', 
	'127.0.0.0/8',
	'128.0.0.0/16',
	'169.254.0.0/16'
]


interface_roles =		{}
interface_roles['loopback'] =	"^(lo0.0|loopback0)$"

# Map interface types before falling back on "other" - see /api/dcim/_choices/
interface_map =			{}
interface_map['ios'] = {
	'vlan' : 	'virtual',
	'bdi' :		'virtual',
	'port-channel':	'lag'
}

interface_map['junos'] = {
	'ge-' : '1000base-x-sfp',
	'xe-' : '10gbase-x-sfpp',
	'et-' : '100gbase-x-qsfp28',
	'irb' : 'virtual',
	'vlan' : 'virtual',
	'ae' : 'lag'
}



##########################################
#### netbox-device-type-change stuff

# create a new type by mapping interface names to roles (wan1/2, lan1/2, mgmt, loop)

types = {}
types['ASR-920-4SZ-A'] = {}
types['ASR-920-4SZ-A']['console-ports']		= { 'Console - Serial' : 'usb-a', 'Console - USB' : 'usb-a' }
types['ASR-920-4SZ-A']['power-ports']		= { 'PS-0' : 'iec-60320-c16', 'PS-1' : 'iec-60320-c16' }
types['ASR-920-4SZ-A']['interfaces'] = {}
types['ASR-920-4SZ-A']['interfaces']['Loopback0']			= { 'role' : 'loop', 'type' : 'virtual' }
types['ASR-920-4SZ-A']['interfaces']['TenGigabitEthernet0/0/3']	= { 'role' : 'wan1', 'type' : '10gbase-x-sfpp' }
types['ASR-920-4SZ-A']['interfaces']['TenGigabitEthernet0/0/5']	= { 'role' : 'wan2', 'type' : '10gbase-x-sfpp' }
types['ASR-920-4SZ-A']['interfaces']['TenGigabitEthernet0/0/2']	= { 'role' : 'lan1', 'type' : '10gbase-x-sfpp' }
types['ASR-920-4SZ-A']['interfaces']['TenGigabitEthernet0/0/4']	= { 'role' : 'lan2', 'type' : '10gbase-x-sfpp' }
types['ASR-920-4SZ-A']['interfaces']['GigabitEthernet0']		= { 'role' : 'mgmt', 'type' : '1000base-t'}

types['ASR-920-12CZ-A'] = {}
types['ASR-920-12CZ-A']['console-ports']	= { 'Console - Serial' : 'usb-a', 'Console - USB' : 'usb-a' }
types['ASR-920-12CZ-A']['power-ports']		= { 'PS-0' : 'iec-60320-c16', 'PS-1' : 'iec-60320-c16' }
types['ASR-920-12CZ-A']['interfaces'] = {}
types['ASR-920-12CZ-A']['interfaces']['Loopback0']			= { 'role' : 'loop', 'type' : 'virtual' }
types['ASR-920-12CZ-A']['interfaces']['TenGigabitEthernet0/0/13']	= { 'role' : 'wan1', 'type' : '10gbase-x-sfpp' }
types['ASR-920-12CZ-A']['interfaces']['TenGigabitEthernet0/0/12']	= { 'role' : 'lan1', 'type' : '10gbase-x-sfpp' }
types['ASR-920-12CZ-A']['interfaces']['GigabitEthernet0']		= { 'role' : 'mgmt', 'type' : '1000base-t'}

types['ME-3400EG-2CS-A'] = {}
types['ME-3400EG-2CS-A']['console-ports']	= { 'rj-45' : 'Console - Serial' }
types['ME-3400EG-2CS-A']['power-ports']		= { 'PS-0' : 'iec-60320-c14' }
types['ME-3400EG-2CS-A']['interfaces'] = {}
types['ME-3400EG-2CS-A']['interfaces']['Loopback0']		= { 'role' : 'loop', 'type' : 'virtual' }
types['ME-3400EG-2CS-A']['interfaces']['GigabitEthernet0/2']	= { 'role' : 'wan1', 'type' : '1000base-x-sfp' }
types['ME-3400EG-2CS-A']['interfaces']['GigabitEthernet0/3']	= { 'role' : 'wan2', 'type' : '1000base-x-sfp' }
types['ME-3400EG-2CS-A']['interfaces']['GigabitEthernet0/1']	= { 'role' : 'lan1', 'type' : '1000base-x-sfp' }
types['ME-3400EG-2CS-A']['interfaces']['GigabitEthernet0/4']	= { 'role' : 'lan2', 'type' : '1000base-x-sfp' }
types['ME-3400EG-2CS-A']['interfaces']['FastEthernet0']	= { 'role' : 'mgmt', 'type' : '100base-tx' }


