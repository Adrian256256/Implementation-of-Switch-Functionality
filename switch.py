#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name

def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    # Check for VLAN tag (0x8100 in network byte order is b'\x81\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id

def create_vlan_tag(vlan_id):
    # 0x8100 for the Ethertype for 802.1Q
    # vlan_id & 0x0FFF ensures that only the last 12 bits are used
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)

def send_bdpu_every_sec():
    global own_bridge_id, root_bridge_id, interfaces, vlan_table, root_path_cost
    while True:
        # TODO Send BDPU every second if necessary
        if own_bridge_id == root_bridge_id:
            for i in interfaces:
                # send BPDU
                if vlan_table[get_interface_name(i)] == 'T':
                    dst_mac = 0x0180C2000000
                    mac_cast = struct.pack('!6s', dst_mac.to_bytes(6, byteorder='big'))
                    src_mac = get_switch_mac()
                    llc_length = struct.pack('!H', 0)
                    byte1 = 0x42
                    byte2 = 0x42
                    byte3 = 0x03
                    llc_heather = struct.pack('!3s', byte1.to_bytes(1, byteorder='big') + byte2.to_bytes(1, byteorder='big') + byte3.to_bytes(1, byteorder='big'))
                    bpdu_header = struct.pack('!I', 0)
                    root_bridge_id_packed = struct.pack('!q', root_bridge_id) # 22
                    root_path_cost_packed = struct.pack('!I', root_path_cost) # 30
                    own_bridge_id_packed = struct.pack('!q', own_bridge_id) # 34
                    
                    
                    data = mac_cast + src_mac + llc_length + llc_heather + bpdu_header + root_bridge_id_packed + root_path_cost_packed + own_bridge_id_packed
                    send_to_link(i, len(data), data)
        time.sleep(1)



def main():
    global own_bridge_id, root_bridge_id, interfaces, vlan_table, root_path_cost
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]

    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    print('# Starting switch with id {}'.format(switch_id), flush=True)
    print('[INFO] Switch MAC', ':'.join(f'{b:02x}' for b in get_switch_mac()))

    # Printing interface names
    for i in interfaces:
        print(get_interface_name(i))

    # create a dictionary to store the MAC address table (switching table)
    mac_table = {}

    # create a dictionary to store the VLAN table
    vlan_table = {}

    # read the file
    with open(f'configs/switch{switch_id}.cfg') as f:
        lines = f.readlines()
        # set switch priority, from the first line
        own_priority_value = lines[0].strip()
        # for every line in the file, except the first one
        for line in lines[1:]:
            #take out the \n
            line = line.strip()
            vlan_table[line.split()[0]] = line.split()[1]

    # stp preparation
    stp_table = {}
    own_bridge_id = int(own_priority_value)
    root_bridge_id = int(own_priority_value)
    root_path_cost = 0

    if own_bridge_id == root_bridge_id:
        # set all ports to DESIGNATED_PORT
        for i in interfaces:
            stp_table[i] = 'DESIGNATED_PORT'

    root_port = None

    # Create and start a new thread that deals with sending BDPU
    t = threading.Thread(target=send_bdpu_every_sec)
    t.start()


    while True:
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # 'Hello'
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # ' World'
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()

        if data[0:6] == b'\x01\x80\xc2\x00\x00\x00':
            # STP BPDU
            root_bridge_id_received = int.from_bytes(data[21:29], byteorder='big')
            sender_path_cost = int.from_bytes(data[29:33], byteorder='big')
            sender_bridge_id = int.from_bytes(data[33:41], byteorder='big')
            
            root = False
            if own_bridge_id == root_bridge_id:
                root = True

            if root_bridge_id_received < root_bridge_id:
                root_bridge_id = root_bridge_id_received
                root_path_cost = sender_path_cost + 10
                root_port = interface

                # if we were the root, change all ports to BLOCKING, except the root port
                # except hosts
                if root == True:
                    for i in stp_table:
                        if i != root_port and vlan_table[get_interface_name(i)] == 'T':
                            stp_table[i] = 'BLOCKING'
                
                if stp_table[root_port] == 'BLOCKING':
                    # if the root port is BLOCKING, change it to DESIGNATED_PORT
                    stp_table[root_port] = 'DESIGNATED_PORT'

                # update and foward the BPDU
                for i in interfaces:
                    if i != interface and vlan_table[get_interface_name(i)] == 'T':
                        dst_mac = 0x0180C2000000
                        mac_cast = struct.pack('!6s', dst_mac.to_bytes(6, byteorder='big'))
                        src_mac = get_switch_mac()
                        llc_length = struct.pack('!H', 0)
                        byte1 = 0x42
                        byte2 = 0x42
                        byte3 = 0x03
                        llc_heather = struct.pack('!3s', byte1.to_bytes(1, byteorder='big') + byte2.to_bytes(1, byteorder='big') + byte3.to_bytes(1, byteorder='big'))
                        bpdu_header = struct.pack('!I', 0)
                        root_bridge_id_packed = struct.pack('!q', root_bridge_id) # 22
                        root_path_cost_packed = struct.pack('!I', root_path_cost) # 30
                        own_bridge_id_packed = struct.pack('!q', own_bridge_id) # 34
                        
                        data = mac_cast + src_mac + llc_length + llc_heather + bpdu_header + root_bridge_id_packed + root_path_cost_packed + own_bridge_id_packed
                        send_to_link(i, len(data), data)
            
            elif root_bridge_id_received == root_bridge_id:
                if interface == root_port and sender_path_cost + 10 < root_path_cost:
                    root_path_cost = sender_path_cost + 10
                
                elif interface != root_port:
                    if sender_path_cost > root_path_cost:
                        if stp_table[interface] == 'BLOCKING':
                            stp_table[interface] = 'DESIGNATED_PORT'

            elif sender_bridge_id == own_bridge_id:
                # if the sender is us, we have a loop
                # change the port to BLOCKING
                stp_table[interface] = 'BLOCKING'
            else:
                continue

            if own_bridge_id == root_bridge_id:
                # set all ports to DESIGNATED_PORT
                for i in interfaces:
                    stp_table[i] = 'DESIGNATED_PORT'
            continue
            
        
        

        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)

        # Print the MAC src and MAC dst in human readable format
        dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac = ':'.join(f'{b:02x}' for b in src_mac)

        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(10) + data[12:]

        print(f'Destination MAC: {dest_mac}')
        print(f'Source MAC: {src_mac}')
        print(f'EtherType: {ethertype}')

        print('Received frame of size {} on interface {}'.format(length, interface), flush=True)

        # add the source MAC address to the MAC address table
        if src_mac not in mac_table:
            mac_table[src_mac] = interface

        # unicast
        if dest_mac in mac_table:
            # destination MAC is in the MAC address table
            # send to the interface where the destination MAC is found
            # check if the src interface is trunk(swich) or access(host)

            source_name = get_interface_name(interface)
            dest_name = get_interface_name(mac_table[dest_mac])

            #caut in vlan table
            if vlan_table[source_name] == 'T' and vlan_table[dest_name] == 'T':
                # trunk to trunk
                send_to_link(mac_table[dest_mac], length, data)
            if vlan_table[source_name] == 'T' and vlan_table[dest_name] != 'T':
                # trunk to access
                # check if the source vlan is the same as the dest vlan
                if vlan_id == int(vlan_table[dest_name]):
                    send_to_link(mac_table[dest_mac], length - 4, data[0:12] + data[16:])
            if vlan_table[source_name] != 'T' and vlan_table[dest_name] == 'T':
                # access to trunk
                # add vlan tag
                send_to_link(mac_table[dest_mac], length + 4, data[0:12] + create_vlan_tag(int(vlan_table[source_name])) + data[12:])
            if vlan_table[source_name] != 'T' and vlan_table[dest_name] != 'T':
                # access to access
                # check if the source vlan is the same as the dest vlan
                if int(vlan_table[source_name]) == int(vlan_table[dest_name]):
                    send_to_link(mac_table[dest_mac], length, data)

        else:
            # destination MAC is not in the MAC address table
            # broadcast to all ports except the one where the frame was received
            for i in interfaces:
                if i != interface and stp_table[i] == 'DESIGNATED_PORT':
                    source_name = get_interface_name(interface)
                    dest_name = get_interface_name(i)
                    if vlan_table[source_name] == 'T' and vlan_table[dest_name] == 'T':
                        # trunk to trunk
                        send_to_link(i, length, data)
                    if vlan_table[source_name] == 'T' and vlan_table[dest_name] != 'T':
                        # trunk to access
                        # check if the source vlan is the same as the dest vlan
                        if vlan_id == int(vlan_table[dest_name]):
                            send_to_link(i, length - 4, data[0:12] + data[16:])
                    if vlan_table[source_name] != 'T' and vlan_table[dest_name] == 'T':
                        # access to trunk
                        # add vlan tag
                        send_to_link(i, length + 4, data[0:12] + create_vlan_tag(int(vlan_table[source_name])) + data[12:])
                    if vlan_table[source_name] != 'T' and vlan_table[dest_name] != 'T':
                        # access to access
                        # check if the source vlan is the same as the dest vlan
                        if int(vlan_table[source_name]) == int(vlan_table[dest_name]):
                            send_to_link(i, length, data)
                    

if __name__ == '__main__':
    main()
