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

