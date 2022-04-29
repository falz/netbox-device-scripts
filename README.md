# netbox-device-scripts
## Overview
Scripts to import devices in to netbox, as well as changing device types while mapping interfaces properly. Tested on Cisco IOS devices (ME3400, ASR920) as well as various Juniper MX anx QFX. Should work with any other devices that have NAPALM drivers.

## Scripts
* device-to-netbox.py : Import a productoin device using NAPALM driver
* netbox-to-device.py : Push a config from netbox to a device. Requires something to create this config (not in this repo)
* netbox-device-type-change.py : Converts device types, 
* config.py : configuration file for API key, device type mapping, etc.

## Requirements
```
pip install argparse json getpass napalm pynetbox
```

## Usage
### device-to-netbox.py
```
Argument        Required  Default   Notes
-d / --device	yes	none	hostname of device to get config from
-m / --model	yes	none	netbox device type (model) to import in to
-s / --site	yes	none	netbox site name (AbbotsfordSD). Gets location from here?
-t / --tenant	yes	none	netbox tenant name (AbbotsfordSD). Not to be confused with site, although many will be the same.
-o / os	        no	ios	OS of device. Uses NAPALM driver names
-r / role 	no	cpe	Netbox device role
-p / --password	no	        send password from cli. ask for one if flag not given.
-u / --username	no	        shell username	Username that logs in to router. Default to shell session's username
```

Example import
```
./device-to-netbox.py -d hostname -s sitename -t tenantname -m ME-3400EG-2CS-A -o ios -r cpe
 
Password for user "falz" to log in to "hostname":
Connection summary:
 
    user:   falz
    device: hostname
    model:  ME-3400EG-2CS-A
    os: ios
    role:   cpe
    site:   sitename
    tenant: tenantname
 
Netbox sanity checks: Done
 
Connecting to hostname: Done
 
Getting info: Facts Interfaces IPs BGP Done
 
Creating netbox device: Done - https://netbox.example.org/dcim/devices/353/
 
Adding interfaces: Done
 
Skipping interfaces: Vlan1 Done
 
Updating interfaces: FastEthernet0 GigabitEthernet0/1 GigabitEthernet0/2 GigabitEthernet0/3 GigabitEthernet0/4 Loopback0 Done
 
Adding IP addresses: 10.56.48.145/28 192.189.129.166/30 192.189.129.18/32 (updated) (primary) Done
 
Device added successfully.

```

### netbox-to-device.py


### netbox-device-type-change.py
Changes a netbox device from one model to another. We used this do 'upgrade' devices in the field and stage their new config. Requires extensive interface mapping in config.py in the `types` dictionary. 

This will also clear the device serial number and adjust status to Planned, and add any missing interfaces that are in the target device type.

This was very specific to our scenario and one has to map loopback, wan1/2, lan1/2 interfaces, which are all pretty layer3 heavy. YMMV.

Currently supports ME-3400EG-2CS-A, ASR-920-4SZ-A, ASR-920-12CZ-A. 

Arguments
```
-d : numeric netbox device to convert (integer)
-t : type to convert to. Requires this device type to exist (string)
```

Exmaple conversion
```
./netbox-device-type-change.py -t ASR-920-4SZ-A -d 372
 
Fetching netbox device 372 ..
Working on hostname (https://netbox.wiscnet.net/dcim/devices/372) Type: ASR-920-4SZ-A
 
Mapping interfaces..
Role: wan2 Old Name: GigabitEthernet0/1 -> New Name: TenGigabitEthernet0/0/5 New Type: 10gbase-x-sfpp Status: OK
Role: wan1 Old Name: GigabitEthernet0/2 -> New Name: TenGigabitEthernet0/0/3 New Type: 10gbase-x-sfpp Status: OK
Role: lan1 Old Name: GigabitEthernet0/3 -> New Name: TenGigabitEthernet0/0/2 New Type: 10gbase-x-sfpp Status: OK
Role: lan2 Old Name: GigabitEthernet0/4 -> New Name: TenGigabitEthernet0/0/4 New Type: 10gbase-x-sfpp Status: OK
Role: mgmt Old Name: FastEthernet0 -> New Name: GigabitEthernet0 New Type: 1000base-t Status: OK
Role: loop Old Name: Loopback0 -> New Name: Loopback0 New Type: virtual Status: OK
Done
 
Changing Serial Number from 'FOC1234ABCD' to ''
Changing Status from Active to Planned
Changing Type from ME-3400EG-2CS-A to ASR-920-4SZ-A
Done
 
Creating missing interfaces:
GigabitEthernet0/0/0 1000base-t
GigabitEthernet0/0/1 1000base-t
Done
```
