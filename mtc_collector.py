# Observing MTConnect standard
# MTConnect must have a single Device for this collector.

import time
import datetime
import sys
import requests
import pymysql.cursors
from xml.etree import ElementTree as ET


# Probe parsing class
class ProbeParsing(object):

    def __init__(self, root):
        self.MTCONNECT_STR = root.tag.split("}")[0]+"}" # MTConnectDevices
        self.schema = self.MTCONNECT_STR.split(":")[-1][:-1]
        header = root.find("./"+self.MTCONNECT_STR+"Header")
        self.instnaceId = int(header.attrib["instanceId"])
        self.version = header.attrib["version"]
        self.creationTime = header.attrib["creationTime"]

        device = root.find(".//"+self.MTCONNECT_STR+"Device")
        self.id = device.attrib["id"]
        self.name = device.attrib["name"]
        self.uuid = device.attrib["uuid"]


# Header parsing class
class HeaderParsing(object):

    def __init__(self, root):
        self.MTCONNECT_STR = root.tag.split("}")[0]+"}" # MTConnectStreams
        header = root.find("./"+self.MTCONNECT_STR+"Header")
        self.nextSeq = header.attrib["nextSequence"]
        self.lastSeq = header.attrib["lastSequence"]
        self.instnaceId = int(header.attrib["instanceId"])
        self.version = header.attrib["version"]


# keep MySQL connector alive
def connect_mysql(host, user, password, db, port):
    # while True:
    try:
        connection = pymysql.connect(host=host, user=user, password=password, db=db, port=port)
        return connection # returning connection object when make connection
    except Exception as e: # when network error happen in the site device
        print("Could not get Mysql connection ...")
        print("Exception error:", e)
        return None # returning None when failing connection


def query_return(elem, category, uuid):
    id = elem.get("dataItemId") # dataItemId
    timestamp = elem.get("timestamp")[0:10]+" "+elem.get("timestamp")[11:26] 
    timestamp = timestamp.replace("T", " ").replace("Z","") # converting Zulu date time format to MySQL TIMESTAMP but, still UTC
    value = elem.text
    tagname = elem.tag[40:]

    if category == "condition": # for condition category
        # condition type, native code, qualifier, native serverity identification
        cond_type = elem.get("type")
        nativeCode = elem.get("nativeCode")
        if nativeCode is None or nativeCode == " ":
            cond_native_code = ""
        else: cond_native_code = nativeCode
        qualifier = elem.get("qualifier")
        if qualifier is None or qualifier == " ":
            cond_qualifier = ""
        else: cond_qualifier = qualifier
        nativeSeverity = elem.get("nativeSeverity")
        if nativeSeverity is None or nativeSeverity == " ":
            cond_native_severity = ""
        else: cond_native_severity = nativeSeverity

        # Data check
        if value == "AVAILABLE" or value == "UNAVAILABLE":
            query = "INSERT IGNORE INTO %s (dataItemId, uuid, tag, timestamp, type, avail, nativeCode, nativeSeverity, qualifier) \
                VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');" \
                % ("mtc_condition", id, uuid, tagname, timestamp, cond_type, value, cond_native_code, cond_qualifier, qualifier)
        else:
            query = "INSERT IGNORE INTO %s (dataItemId, uuid, tag, timestamp, type, value, nativeCode, nativeSeverity, qualifier) \
                VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');" \
                % ("mtc_condition", id, uuid, tagname, timestamp, cond_type, value, cond_native_code, cond_native_severity, qualifier)

    else: # event and sample

        if category == "sample": # in case of Sample
            table = "mtc_sample"
        else: table = "mtc_event" # in case of Event

        if value == "AVAILABLE" or value == "UNAVAILABLE":
            query = "INSERT IGNORE INTO %s (dataItemId, uuid, tag, timestamp, avail) VALUES ('%s', '%s', '%s', '%s', '%s');" \
                % (table, id, uuid, tagname, timestamp, value)
        else:
            query = "INSERT IGNORE INTO %s (dataItemId, uuid, tag, timestamp, value) VALUES ('%s', '%s', '%s', '%s', '%s');" \
                % (table, id, uuid, tagname, timestamp, value)

    return query

#time.sleep(10)

## MTConnect standard Component list
COMPONENT_LIST = ['Device', 
                  'Axes', 
                  'Linear',
                  'Rotary',
                  'Controller', 
                  'Path',
                  'Systems', 
                  'Door', 
                  'Actuator',
                  'Sensor', 
                  'Stock', 
                  'Interfaces', 
                  'Hydraulic',
                  'Pneumatic',
                  'Coolant',
                  'Lubrication',
                  'Electric']


def main():
    ### Probing started (target tables: 'device', 'dataitem')
    root = ET.fromstring(requests.get(probe_req).content)

    Probe = ProbeParsing(root) # Probe obj

    print("MTConnect string:",Probe.MTCONNECT_STR) # MTConnect elem. string including MTConnect schema version
    print("MTConnect version:",Probe.version) # MTConnect agent version
    print("MTConnect schema:",Probe.schema) # MTConnect schema version
    print("instanceId:",Probe.instnaceId) # Agent instanceId
    print("Device name:",Probe.name) # Device name (optional)
    print("Device id:",Probe.id) # Device id (requirement)
    print("Device uuid:",Probe.uuid) # Device uuid (requirement)
    print("Header timestamp:", Probe.creationTime) # Header timestamp

    creationTime = Probe.creationTime.replace("T", " ").replace("Z","")
    print(creationTime)
    uuid = Probe.uuid
    instanceId = Probe.instnaceId

    # database.device update/insert below
    connection = connect_mysql(host=HOST, user=USER, password=PASSWORD, db=DB, port=PORT)

    # try to write mtc_device table
    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT IGNORE INTO mtc_device (uuid, id, name, version, mtconnect_schema)\
                        VALUES ('%s', '%s', '%s', '%s', '%s');" %(Probe.uuid, Probe.id, Probe.name, Probe.version, Probe.schema,))
        connection.commit()
    except Exception as e: # if exist, pass
        print(e)
        pass
    finally:
        connection.close()

    # database.dataitem update/insert below
    component_name = "Device" + "_" + Probe.name

    for elem in root.iter():
        tag = elem.tag.replace(Probe.MTCONNECT_STR, '')
        if tag != "DataItem" and tag in COMPONENT_LIST:
            component = tag
            component_name = component+"_"+elem.attrib["name"]
        elem.attrib["component"] = component_name # add component attribute
        elem.attrib["uuid"] = uuid # add uuid attribute
        
        if tag == "DataItem":
            placeholders = ', '.join(['%s'] * len(elem.attrib))
            columns = ', '.join(elem.attrib.keys())
            query = "INSERT IGNORE INTO %s ( %s ) VALUES ( %s );" % ('mtc_dataitem', columns, placeholders)

            connection = connect_mysql(host=HOST, user=USER, password=PASSWORD, db=DB, port=PORT)
            try:
                with connection.cursor() as cursor:
                    cursor.execute(query, list(elem.attrib.values()))
                connection.commit()
            except Exception as e:
                print(e)
                connection.rollback()
                pass
            finally:
                connection.close()
        else:
            pass


    # Comparing current MTConnect agent instance and DB 
    current_root = ET.fromstring(requests.get(current_req).content)
    MTCONNECT_STR = current_root.tag.split("}")[0]+"}" # MTConnect stream text
    header = current_root.find("./"+MTCONNECT_STR+"Header")
    current_firstSeq = header.attrib["firstSequence"]
    current_nextSeq = header.attrib["nextSequence"]
    current_lastSeq = header.attrib["lastSequence"]

    print("current first sequence=", current_firstSeq)
    # print("current next sequence=", current_nextSeq)
    print("current last sequence=", current_lastSeq)


    connection = connect_mysql(host=HOST, user=USER, password=PASSWORD, db=DB, port=PORT)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT instanceId, latest_sequence FROM mtc_instance WHERE uuid='%s' ORDER BY instanceId DESC LIMIT 1;" %(uuid,))
            current_instance = cursor.fetchone()
            print(current_instance)
        
            if current_instance == None:
                updated_req = sample_req+"?count=50"
                print("CASE1", updated_req)
                cursor.execute("INSERT IGNORE INTO mtc_instance (uuid, instanceId) VALUES ('%s', '%s');" %(uuid,instanceId,))
                
            elif int(current_instance[0]) != int(instanceId):
                updated_req = sample_req+"?count=50"
                print("CASE2", updated_req)
                cursor.execute("SET time_zone='+00:00';")
                cursor.execute("INSERT IGNORE INTO mtc_instance (uuid, instanceId) VALUES ('%s', '%s');" %(uuid,instanceId,))
                
            elif int(current_instance[0]) == int(instanceId) and int(current_firstSeq) <= int(current_instance[1]) <= int(current_lastSeq) :
                start_sequence = current_instance[1]
                updated_req = sample_req+"?from="+str(int(start_sequence+1))+"&count=50"
                print("CASE3", updated_req)
            else:
                updated_req = sample_req+"?count=50"
                print("CASE4", updated_req)
        
        connection.commit()

    except Exception as e:
        print(e)
        connection.rollback()

    finally:
        connection.close()


    print(updated_req)

    max_retries = 10000 # maximum 10000 times of connection retry
    delay = 10 # 10 seconds of delday for connection retry

    while True: # infinite loop
        t_start = time.time() # measure loop time
        root = ET.fromstring(requests.get(updated_req).content) # XML root and parsing

        ## Handling MTConnect agent attribute error by ahead/behind sequence from the buffer
        try:
            MTCONNECT_STR = root.tag.split("}")[0]+"}" # MTConnectStreams
            header = root.find("./"+MTCONNECT_STR+"Header")
            # print(header.attrib)
            firstSeq = header.attrib["firstSequence"]
            nextSeq = header.attrib["nextSequence"]
            lastSeq = header.attrib["lastSequence"]
            print("firstSeq={}, nextSeq={}, lastSeq={}, uuid={}, instanceId={}".format(firstSeq, nextSeq, lastSeq, uuid, instanceId))
        except AttributeError as ae:
            print(ae)
            root = ET.fromstring(requests.get(sample_req+"?count=50"))
            header = root.find("./"+MTCONNECT_STR+"Header")
            # print(header.attrib)
            firstSeq = header.attrib["firstSequence"]
            nextSeq = header.attrib["nextSequence"]
            lastSeq = header.attrib["lastSequence"]
            print(datetime.datetime.now(), ": Attribute Error Happens! Initialize Sample request:", sample_req+"?count=50")
            print("Initialized header: firstSeq={}, nextSeq={}, lastSeq={}, uuid={}, instanceId={}".format(firstSeq, nextSeq, lastSeq, uuid, instanceId))
            # should be updated to handle Attribute Error;
            # continue
        
        ## Handling MySQL connection error
        retry_count = 0
        while retry_count < max_retries:
            connection = connect_mysql(HOST,USER,PASSWORD,DB,PORT) # define mysql connection object
            if connection:
                break
            else:
                print(datetime.datetime.now(),": Failing to connection, retry ({}/{}) in {}seconds...".format(retry_count, max_retries, delay))
                retry_count += 1

        if retry_count == max_retries:
            print(datetime.datetime.now(),": Unable to connect MySQL server aftery retrying {} times... Please check network status and/or server status".format(retry_count))
            break # if connection has not been made for maximum retries, break this program

        seq_s, seq_c, seq_e = None, None, None # initialize sequence of sample, condition, and event
        try:
            with connection.cursor() as cursor: # cursor object for interfacing using connection object
                cursor.execute("SET time_zone='+00:00';") # set timezone is UTC because input timestamp is UTC
                for device in root.iter(MTCONNECT_STR+"DeviceStream"): # find device stream
                    uuid = device.get('uuid') # get uuid
                    for sample in device.iter(MTCONNECT_STR+"Samples"): # for Sample category
                        for elem in sample: # for each element
                            seq_s = elem.get("sequence") # get sequence of each element
                            query = query_return(elem, "sample", uuid) # insert query for inserting data into DB
                            cursor.execute(query) # execute insert query
                            pass

                    for event in device.iter(MTCONNECT_STR+"Events"):
                        for elem in event:
                            seq_e = elem.get("sequence") # get sequence of each element
                            query = query_return(elem, "event", uuid) # insert query for inserting data into DB
                            cursor.execute(query) # execute insert query 
                            pass

                    for condition in device.iter(MTCONNECT_STR+"Condition"):
                        for elem in condition:
                            seq_c = elem.get("sequence") # get sequence of each element
                            query = query_return(elem, "condition", uuid) # insert query for inserting data into DB
                            cursor.execute(query) # execute insert query
                            pass
                    
                sequences = [var for var in [seq_s, seq_e, seq_c] if var is not None]

                if sequences:
                    latest_sequence = max(sequences)
                    instance_update_query = "UPDATE %s SET latest_sequence='%s' WHERE uuid='%s' AND instanceId='%s';" % ("mtc_instance", latest_sequence, uuid, instanceId,)
                    cursor.execute(instance_update_query) # update mtc_instance
                else:
                    print("No incoming data")
            connection.commit() # commit all insert and update queries

        except Exception as e:
            connection.rollback() # rolling back commit when error happens
            print(datetime.datetime.now(), "connection rollback!\nAn error occurred:", e)
            continue

        finally:
            if connection is not None: # if connection is alive
                connection.close() # firmly close connection to prevent duplicate connections

        updated_req = sample_req+"?from="+nextSeq+"&count=50" # HTTP request query update
        time.sleep(0.5)
        print(datetime.datetime.now(), "Loop: {} [sec]".format(time.time()-t_start))
        print(updated_req)

if __name__ == "__main__":
    ## mtconnect info.
    agent = "http://<MTConnect_IP>:<Port>/" # Your MTConnect Agent IP:Port
    probe_req = agent+"probe" # Probe request
    current_req = agent+"current" # Current request
    sample_req = agent+"sample" # Sample request

    ## MySQL credential
    HOST = "your.mysql.server.ip" # MySQl Server IP in IPv4 format
    PORT = 3306 # MySQl port number
    USER = "Username" # User credential
    PASSWORD = "Password" # User credential
    DB = "factory" # DB name

    main() # Run main method