import zeep
import base64
import sqlite3
import os
import csv

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


    def get_trs_sites(self, system_id):
        try:
            response = self.client.service.getTrsSites(sid=system_id, authInfo=self.auth_info)
            return response
        except Exception as e:
            print(f"An error occurred while fetching trunked system sites: {e}")
            return None

    def get_trs_talkgroups(self, system_id):
        try:
            result = self.client.service.getTrsTalkgroups(system_id, 0, 0, 0, self.auth_info)
            talkgroups_info = []
            for row in result:
                if row.enc == 0:
                    talkgroups_info.append([row.tgDec, row.tgAlpha])
                else:
                    pass
            return talkgroups_info
        except Exception as e:
            print(f"An error occurred while fetching trunked system talkgroups: {e}")
            return None

    def create_system_folder(self, system_id):
        if not os.path.exists('systems'):
            os.makedirs('systems')
        system_folder = os.path.join('systems', str(system_id))
        if not os.path.exists(system_folder):
            os.makedirs(system_folder)
        return system_folder

    def create_talkgroups_tsv_file(self, system_id, talkgroups):
        system_folder = self.create_system_folder(system_id)
        file_path = os.path.join(system_folder, f"{system_id}_talkgroups.tsv")
        with open(file_path, 'w', newline='') as tsvfile:
            writer = csv.writer(tsvfile, delimiter='\t')
            for talkgroup in talkgroups:
                writer.writerow(talkgroup)

    def create_site_tsv_file(self, system_id, site):
        system_folder = self.create_system_folder(system_id)
        site_id = site['siteId']
        file_path = os.path.join(system_folder, f"{system_id}_{site_id}_trunk.tsv")
        control_channels = sorted(
            [freq['freq'] for freq in site['siteFreqs'] if freq['use'] is not None],
            key=lambda freq: (1 if any(f['use'] == 'a' and f['freq'] == freq for f in site['siteFreqs']) else 2)
        )
        control_channels_str = ','.join(map(str, control_channels))
        with open(file_path, 'w', newline='') as tsvfile:
            writer = csv.writer(tsvfile, delimiter='\t', quoting=csv.QUOTE_ALL)
            writer.writerow([
                "Sysname", "Control Channel List", "Offset", "NAC", "Modulation", "TGID Tags File", "Whitelist",
                "Blacklist", "Center Frequency"
            ])
            writer.writerow([
                f"{system_id}", f"{control_channels_str}", "0", "0", "cqpsk", f"systems/{system_id}/{system_id}_talkgroups.tsv", "", "", ""
            ])

    def create_and_populate_db(self, system_id, sites_info, talkgroups_info):
        system_folder = self.create_system_folder(system_id)
        db_path = os.path.join(system_folder, f"{system_id}.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create tables if they don't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sites (
            site_id INTEGER PRIMARY KEY,
            latitude REAL,
            longitude REAL,
            site_county TEXT
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS talkgroups (
            tg_dec INTEGER PRIMARY KEY,
            tg_alpha TEXT
        )
        ''')

        # Insert site data
        for site in sites_info:
            cursor.execute('''
            INSERT OR IGNORE INTO sites (site_id, latitude, longitude, site_county)
            VALUES (?, ?, ?, ?)
            ''', (
                site['siteId'],
                float(site['lat']),  # Convert to float
                float(site['lon']),  # Convert to float
                site['siteDescr']
            ))

        # Insert talkgroup data
        for talkgroup in talkgroups_info:
            cursor.execute('''
            INSERT OR IGNORE INTO talkgroups (tg_dec, tg_alpha)
            VALUES (?, ?)
            ''', (
                talkgroup[0],
                talkgroup[1]
            ))

        # Commit the changes and close the connection
        conn.commit()
        conn.close()



    def create_system_tsv_files(self, system_id):
        # Fetch and save site data
        sites_info = self.get_trs_sites(system_id)
        if sites_info:
            for site in sites_info:
                self.create_site_tsv_file(system_id, site)
                print(f"Created TSV file for site {site['siteId']}")
        else:
            print("No sites found for this trunked system.")

        # Fetch and save talkgroup data
        talkgroups_info = self.get_trs_talkgroups(system_id)
        if talkgroups_info:
            self.create_talkgroups_tsv_file(system_id, talkgroups_info)
            print(f"Created TSV file for talkgroups of system {system_id}.")
        else:
            print("No talkgroup data found for this trunked system.")

        # Create and populate the database
        if sites_info or talkgroups_info:
            self.create_and_populate_db(system_id, sites_info if sites_info else [],
                                   talkgroups_info if talkgroups_info else [])
            print(f"Data has been stored in {os.path.join('systems', str(system_id), f'{system_id}.db')}")
        else:
            print("No data available to store in the database.")



# Example usage:
if __name__ == "__main__":
    username = ""
    password = ""

    client = GetSystems(username, password)

    client.create_system_tsv_files('6643')

#    zip_code = "44047"
#    systems = client.get_systems_in_county(zip_code)
#    for system in systems:
#        print(f"System ID: {system['sid']}, Name: {system['sName']}")#
#
#        # Fetch and store sites for each system
#        client.create_system_database(system['sid'])
