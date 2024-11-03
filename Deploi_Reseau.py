import json
from openstack import connection
from os import environ as env

def get_subnet_id(conn, subnet_name):
    subnets = conn.network.subnets()
    for subnet in subnets:
        if subnet.name == subnet_name:
            return subnet.id
    raise Exception(f"Subnet with name {subnet_name} not found.")

def deploy_network_topology(json_file):
    with open(json_file, 'r') as file:
        topology_data = json.load(file)

    # Connect to OpenStack
    conn = connection.Connection(
        region_name='RegionINSA',
        auth={
            'auth_url': 'https://os-api-ext.insa-toulouse.fr:5000/v3',
            'project_id': 'e20dbf88faeb4ef1a9fcd99f2c1a3808',
            'username': 'benchekroun',
            'password': env['OS_PASSWORD'],
            'user_domain_id': 'ef8de9847762471f9f8cea12458550d2',
        },
        compute_api_version='2',
        identity_interface='public'
    )

    for network in topology_data['network_topology']['networks']:
        print(f"Deploying {network['name']}")

        # Create network
        network_data = {
            "name": network['name'],
            "admin_state_up": True,
        }
        created_network = conn.network.create_network(**network_data)

        for subnet in network['components']:
            if subnet['type'] == 'subnet':
                # Create subnet for network
                subnet_data = {
                    "name": subnet['name'],
                    "cidr": subnet['ip_range'],
                    "ip_version": subnet['ip_version'],
                    "network_id": created_network.id,
                }
                created_subnet = conn.network.create_subnet(**subnet_data)

                for component in subnet['components']:
                    if component['type'] == 'vm':
                        # Create VM in subnet
                        vm_data = {
                            "name": component['name'],
                            "imageRef": "5cfa5fb0-3a64-49ef-a321-8e97e741b52d",
                            "flavorRef": "b27bf9a7-8882-4a52-80fa-e8293acbcf0b",
                            "networks": [{"uuid": created_subnet.network_id}]
                        }
                        created_vm = conn.compute.create_server(**vm_data)

                    elif component['type'] == 'router':
                        # Create router with or without external gateway
                        router_data = {
                            "name": component['name'],
                            "external_gateway_info": {
                                "network_id": "577d76a8-31b0-4e12-a8da-93748f1b3459",
                            } if 'external_gateway' in component and component['external_gateway'] else {}
                        }
                        created_router = conn.network.create_router(**router_data)

                        # Add interfaces for each subnet linked to router
                        for interface in component['interfaces']:
                            subnet_name = interface['subnet_name']
                            subnet_id = get_subnet_id(conn, subnet_name)
                            print(f"Adding interface to router. Subnet ID: {subnet_id}")
                            try:
                                conn.network.add_interface_to_router(created_router, subnet_id=subnet_id)
                                print("Interface added successfully.")
                            except Exception as e:
                                print(f"Error adding interface to router: {e}")
                                
        print(f"{network['name']} deployed successfully")

    conn.close()

if __name__ == "__main__":
    json_file_path = "topology.json"
    deploy_network_topology(json_file_path)