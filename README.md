# Implementation of Switch Functionality

This project completes the skeleton code provided to implement the core functionalities of a network switch, including MAC address learning, VLAN handling, and Spanning Tree Protocol (STP).

## Data Structures

- **mac_table**: A dictionary storing pairs of (MAC address, interface). Initially empty, it learns the source MAC and port of incoming packets, allowing the switch to forward packets efficiently to the correct port.

- **vlan_table**: Reads the switch configuration file and stores pairs of (port_name, VLAN type or ID). Ports can be:
  - **Trunk (T)**: Tagged VLAN ports.
  - **Access**: Ports assigned to a specific VLAN ID for connected stations.

- **stp_table**: Dictionary storing the state of ports (open/listening/designated or blocked). It supports the Spanning Tree Protocol implementation.

## Functionality

- The program initializes dictionaries and variables, reads the switch configuration, and sets up STP.
- A separate thread runs concurrently to send BPDU packets every second if needed, following the provided pseudocode.
- The main loop keeps the switch active, processing incoming packets continuously:
  - If the packet is a BPDU, STP logic is executed per the specification.
  - For regular packets, the switch updates `mac_table` with the source MAC and incoming port.
  - It checks the destination MAC port; if unknown, packets are flooded on all designated ports.
  - VLAN tagging or removal is handled depending on whether ports are trunk or access, based on `vlan_table`.
  - Access ports only receive packets from their VLAN.

The implementation uses Python's `struct.pack` and `int.from_bytes` for converting between human-readable and machine-readable packet formats.

This design ensures accurate MAC address learning, proper VLAN segregation, and loop prevention via STP.
