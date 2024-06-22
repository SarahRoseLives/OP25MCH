import zeep
import base64
import sqlite3
import os

class GetSystems:
    def __init__(self, username, password, version="latest", style="rpc"):
        self.auth_info = {
            "appKey": base64.b64decode('Mjg4MDExNjM=').decode(),
            "username": username,
            "password": password,
            "version": version,
            "style": style
        }
        self.wsdl_url = "http://api.radioreference.com/soap2/?wsdl&v=latest&s=rpc"
        self.client = zeep.Client(wsdl=self.wsdl_url)

    def get_zipcode_info(self, zip_code):
        try:
            response = self.client.service.getZipcodeInfo(zipcode=int(zip_code), authInfo=self.auth_info)
            return response
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def get_county_info(self, county_id):
        try:
            response = self.client.service.getCountyInfo(ctid=county_id, authInfo=self.auth_info)
            return response
        except Exception as e:
            print(f"An error occurred while fetching county information: {e}")
            return None




    def create_system_database(self, system_id):
        try:
            response = self.client.service.getTrsSites(sid=system_id, authInfo=self.auth_info)

            if response:
                # Create directory if it doesn't exist
                db_directory = os.path.join('resources', 'systems')
                os.makedirs(db_directory, exist_ok=True)

                # Create or connect to the SQLite database named after the system_id
                db_path = os.path.join(db_directory, f"{system_id}.db")
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Create table if it doesn't exist
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS sites (
                    site_id INTEGER PRIMARY KEY,
                    latitude REAL,
                    longitude REAL,
                    site_county TEXT
                )
                ''')

                # Insert data into the table
                for site in response:
                    cursor.execute('''
                    INSERT INTO sites (site_id, latitude, longitude, site_county)
                    VALUES (?, ?, ?, ?)
                    ''', (
                        site['siteId'],
                        float(site['lat']),  # Convert to float
                        float(site['lon']),  # Convert to float
                        site['siteDescr']
                    ))

                # Commit the changes and close the connection
                conn.commit()
                conn.close()

                print(f"Data has been stored in {db_path}")
            else:
                print("No sites found for this trunked system.")

        except sqlite3.Error as sqle:
            print(f"SQLite error: {sqle}")
        except Exception as e:
            print(f"An error occurred while fetching and storing trunked system sites: {e}")

    def get_systems_in_county(self, zip_code):
        zipcode_info = self.get_zipcode_info(zip_code)
        if zipcode_info and 'ctid' in zipcode_info:
            county_id = zipcode_info['ctid']
            county_info = self.get_county_info(county_id)
            if county_info and 'trsList' in county_info:
                return county_info['trsList']
            else:
                print("No trunked systems found in this county.")
                return []
        else:
            print("Failed to retrieve zip code information or county ID.")
            return []


# Example usage:
if __name__ == "__main__":
    username = ""
    password = ""

    client = GetSystems(username, password)

    zip_code = "44047"
    systems = client.get_systems_in_county(zip_code)
    for system in systems:
        print(f"System ID: {system['sid']}, Name: {system['sName']}")

        # Fetch and store sites for each system
        client.create_system_database(system['sid'])
