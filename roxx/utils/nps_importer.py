import xml.etree.ElementTree as ET
import logging
from typing import List, Dict, Any
import os

logger = logging.getLogger("roxx.utils.nps_importer")

class NPSImporter:
    """
    Parses Microsoft NPS configuration XML files.
    Usually exported via: netsh nps export filename="nps_config.xml" exportPrivateKeys=yes
    """
    
    @staticmethod
    def parse_xml(xml_content: str) -> Dict[str, Any]:
        """
        Parses the NPS XML and returns a structured dictionary of clients and policies.
        """
        try:
            root = ET.fromstring(xml_content)
            results = {
                "clients": [],
                "remote_radius_servers": [],
                "connection_request_policies": [],
                "network_policies": []
            }
            
            # Note: NPS XML structure is deeply nested and often uses "Ms-NP-..." or "Ms-RS-..." tags
            # This is a simplified parser targeting common elements.
            
            # Find RADIUS Clients
            for client in root.findall(".//RadiusClient"):
                name = client.find("Name")
                address = client.find("Address")
                shared_secret = client.find("SharedSecret")
                
                results["clients"].append({
                    "name": name.text if name is not None else "Unknown",
                    "address": address.text if address is not None else "0.0.0.0",
                    "shared_secret": shared_secret.text if shared_secret is not None else ""
                })
                
            # Find Remote RADIUS Servers (Backends)
            for group in root.findall(".//RemoteRadiusServerGroup"):
                group_name = group.find("Name")
                for server in group.findall(".//RemoteRadiusServer"):
                    address = server.find("Address")
                    results["remote_radius_servers"].append({
                        "group": group_name.text if group_name is not None else "Default",
                        "address": address.text if address is not None else ""
                    })

            logger.info(f"NPS Import: Found {len(results['clients'])} clients and {len(results['remote_radius_servers'])} remote servers.")
            return results
            
        except Exception as e:
            logger.error(f"Failed to parse NPS XML: {e}")
            raise ValueError(f"Invalid NPS XML format: {str(e)}")

    @staticmethod
    def convert_to_roxx_clients(nps_results: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Converts parsed NPS clients to RoXX internal client format.
        """
        roxx_clients = []
        for client in nps_results["clients"]:
            roxx_clients.append({
                "shortname": client["name"].lower().replace(" ", "_"),
                "ipaddr": client["address"],
                "secret": client["shared_secret"]
            })
        return roxx_clients
