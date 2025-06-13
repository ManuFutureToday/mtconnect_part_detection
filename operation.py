'''
operation.py
06/13/2025 Yeeun Bae

This code aims to find each operation using Tool value (sample metric key) and insert records into operation table.
Specifically,
1. Input a set of sequences from MTConnect queue using sample request, distinguish each operation, and insert records into operation table.
2. Compare new incoming sequence's value with the value of last available operation sequence. If they are (starting tool , ending tool), insert a record into operation table.

'''

import xml.etree.ElementTree as ET
import requests
import time
from datetime import datetime, timedelta
import pymysql.cursors
import threading
from collections import deque

# Sample XML data (you should replace this with the actual XML content)
agent = "http://<MTConnect_IP>:<Port>/" # Your MTConnect Agent IP:Port
link_updated = agent
response_updated = "UNAVAILABLE" # initial response of MTConnect agent server

device_name = "device_name" 
dataItemId = "dataItemId"
data_item_xpath = "//DataItem[@id='" + dataItemId + "']"
link = f"{agent}/{device_name}/sample?path={data_item_xpath}"

## MySQL credential
HOST = "your.mysql.server.ip" # MySQl Server IP in IPv4 format
PORT = 3306 # MySQl port number
USER = "Username" # User credential
PASSWORD = "Password" # User credential
DB = "factory" # DB name

def connect_mysql(host, user, password, db, port):
    ##### loop until getting connection
    while True:
        try:
            connection = pymysql.connect(host=host,user=user,password=password,db=db,port=port)
            return connection
        except Exception as e:
            # print("Could not get Mysql connection.. retrying in 1 min..")
            print("Could not get Mysql connection.. retrying in 10 sec..")
            print("Exception error: ", e)
            time.sleep(10)
            continue

part_operations = {}

def execute_query(query, fetchone=True):
    connection = None
    while not connection:
        connection = connect_mysql(host=HOST, user=USER, password=PASSWORD, db=DB, port=PORT)

    try:
        with connection.cursor() as cursor:
            cursor.execute("SET time_zone='+00:00';")  # Ensure UTC
            cursor.execute(query)
            if fetchone:
                return cursor.fetchone()
            else:
                return cursor.fetchall()
    except pymysql.MySQLError as e:
        print(datetime.datetime.now(), "**** execute_query: error occurred:", e)
        return None
    finally:
        connection.close()

def fetch_tool_order():
    while True:
        query = """
            SELECT t1.idx, t1.uuid, t1.part, t1.tool_order
            FROM tool_order t1
            JOIN (
                SELECT DISTINCT part, uuid
                FROM tool_order
                WHERE is_active = 1
            ) t2 ON t1.part = t2.part AND t1.uuid = t2.uuid;
        """  # Only fetch the active tool order information for each part

        rows = execute_query(query, fetchone=False)
        if not rows:
            print(datetime.datetime.now(), "**** fetch_tool_order: no data fetched or query failed.")
            continue

        for row in rows:
            tool_idx = row[0]
            uuid = row[1]
            part = row[2]
            tool_orders = list(map(int, row[3].split(",")))  # Convert CSV string to list of integers

            if len(tool_orders) >= 6:
                start_transition = (tool_orders[0], tool_orders[1], tool_orders[2])
                end_transition = (tool_orders[-3], tool_orders[-2], tool_orders[-1])
            else:
                continue  # Skip if not enough values

            # Store results in dictionary
            part_operations[(uuid, part)] = {
                "tool_idx": tool_idx,
                "start_transition": start_transition,
                "end_transition": end_transition,
            }

        print("1 hour elapsed: updated part_operations: ", part_operations)
        time.sleep(3600)

def start_fetching_tool_order():
    fetch_thread = threading.Thread(target=fetch_tool_order)
    fetch_thread.daemon = True  # Allow the thread to exit when the main program exits
    fetch_thread.start()

start_fetching_tool_order()  

def query_return(uuid, part, start_timestamp, end_timestamp, tool_idx):
    connection = None
    while not connection:
        connection = connect_mysql(host=HOST, user=USER, password=PASSWORD, db=DB, port=PORT)  # Ensure connection is open
    
    # Format the start and end timestamps to MySQL-compatible format
    def format_timestamp(timestamp):
        if timestamp:
            if isinstance(timestamp, str) and 'T' in timestamp and 'Z' in timestamp:
                # Convert from ISO8601 string to MySQL datetime string
                timestamp = timestamp[:10] + " " + timestamp[11:26]  # Extract date and time parts
                timestamp = timestamp.replace("T", " ").replace("Z", "")  # Remove 'T' and 'Z'
        return timestamp

    start_timestamp = format_timestamp(start_timestamp)
    end_timestamp = format_timestamp(end_timestamp)

    # Run check query
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET time_zone='+00:00';")  # Ensure UTC time zone

            query = """
                INSERT INTO operation (uuid, part, start_timestamp, end_timestamp, tool_idx)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    end_timestamp = IFNULL(VALUES(end_timestamp), end_timestamp);
            """
            cursor.execute(query, (uuid, part, start_timestamp, end_timestamp, tool_idx))
            connection.commit()

    except pymysql.MySQLError as e:
        connection.rollback()
        print(datetime.datetime.now(), "**** query_return: connection rollback! Error:", e)

    finally:
        connection.close()  # Ensure connection is closed properly

max_retries = 1000 # maximum 10000 times of connection retry
delay = 10 # 10 seconds of delday for connection retry

last_start = [-1, 0, -1] # last available start tool transition:(value, timestamp, sequence)

# Append a set of operation rows from a set of sequences from first sample request response to operation table
def find_operation(data):
    # Detect start and end times for operations
    global last_start  # This ensures we modify the global variable
    
    for i in range (0, len(data) - 1):
        for (uuid, part_number), transitions in part_operations.items():
            # check for start_transition
            if (
                i + 2 < len(data) and  # Ensure there's a next row to compare
                data[i][0] == transitions['start_transition'][0] and
                data[i + 1][0] == transitions['start_transition'][1] and
                data[i + 2][0] == transitions['start_transition'][2]
            ):
                start_time = data[i][1]
                print("start: ", data[i], data[i+1])
                last_start = data[i]
                tool_idx = transitions.get("tool_idx")  # Fetch idx
                
                query_return(uuid, part_number, start_time, None, tool_idx)
            
                # Look ahead for the corresponding end transition
                for j in range(i + 3, len(data)):  # Start searching after the start transition

                    # Check if duplicated start tool transition found before finding end tool transition
                    if (j + 3 < len(data) and  
                        data[j][0] == transitions['start_transition'][0] and
                        data[j + 1][0] == transitions['start_transition'][1] and
                        data[j + 2][0] == transitions['start_transition'][2]
                    ): 
                        # update the start time with the new start time
                        start_time = data[j][1]
                        print("new start: ", data[j])
                        last_start = data[i] 
                        # insert the new start timestamp
                        query_return(uuid, part_number, start_time, None, tool_idx)
                        
                    elif (
                        j + 3 < len(data) and  # Ensure there's a next row to compare
                        data[j][0] == transitions['end_transition'][0] and
                        data[j + 1][0] == transitions['end_transition'][1] and
                        data[j + 2][0] == transitions['end_transition'][2]
                    ):
                        end_time = data[j+3][1]
                        last_start = data[j + 3]

                        print("end: ", end_time)
                        query_return(uuid, part_number, start_time, end_time, tool_idx)
                        break        
    print("**** find_operation: last_start: ", last_start)

first_iter = True
queue = deque(maxlen=3) # FIFO queue with max 3 elements, tracks the most recent three tool numbers (only integers)

while True:
    start = time.time()
    try:
        # result = requests.get(link_updated, timeout=10)
        result = requests.get(link_updated)
        response = "AVAILABLE"
        # print("Machine is Available.")
    except requests.exceptions.Timeout: # exception case for Timeout when machine is off.
        response = "UNAVAILABLE"
        # print("Machine is Unavailable: Timeout error occurs!!!")
    except requests.exceptions.ConnectionError: # exception case for Connection Error when machine is turning on or turning off.
        response = "UNAVAILABLE"
        # print("Machine is Unavailable: Connection error occurs!!!")

    if response_updated == response:
        if response == "AVAILABLE": # In case of machine is available continuously
            root = ET.fromstring(result.content)
            header = root.find("./{urn:mtconnect.org:MTConnectStreams:1.3}Header")
            try:
                header_attribs = header.attrib
                # In case nextSeq is bigger than lastSeq because of controller restart or machine reset, Attribute Error occurs. 
                # To prevent this case, exception for Attribute Error will redefine link from the first (http://host:5000/sample).
            except AttributeError:
                link_updated = link
                result = requests.get(link_updated, timeout=20)
                root = ET.fromstring(result.content)
                header = root.find("./{urn:mtconnect.org:MTConnectStreams:1.3}Header")
                header_attribs = header.attrib
            nextSeq = header_attribs["nextSequence"]
            firstSeq = header_attribs["firstSequence"]
            lastSeq = header_attribs["lastSequence"]

            if (not first_iter):
                # Retrieve value, timestamp, sequence of the most recent entry
                for elem in root.iter():
                    value = elem.text
                    sequence = elem.attrib.get('sequence', 'N/A')
                    timestamp = elem.attrib.get('timestamp', 'N/A')  # Default to 'N/A' if no timestamp

                # compare sequence of the most recent itme in queue to the newly arrived item
                if queue and (queue[-1][-1] != sequence) and (value != None and value != "UNAVAILABLE" and value != ""):
                    value = int(value)
                    
                    for (uuid, part_number), transitions in part_operations.items():
                        tool_idx = transitions.get("tool_idx")  # Fetch idx
    
                        #print("new : [", value, timestamp, sequence, "]  last_start : ", last_start, "  last_avail_seq_queue : ", last_avail_seq_queue) 

                        # if new start timestamp is found (== second tool of start transition is found)                       
                        if (queue[1][0], queue[2][0], value) == (transitions['start_transition'][0], transitions['start_transition'][1], transitions['start_transition'][2]):
                                query_return(uuid, part_number, queue[1][1], None, tool_idx)
                                last_start = queue[1] # new start
                                print("-------new start timestamp is found, last_start: ", last_start)

                        # if last_start = start tool of operation
                        elif last_start[0] == transitions['start_transition'][0]: 
                            # if 2nd, 3rd in queue, and new value is end transition of the operation
                            if (queue[0][0], queue[1][0], queue[2][0]) == (transitions['end_transition'][0], transitions['end_transition'][1], transitions['end_transition'][2]):
                                    query_return(uuid, part_number, last_start[1], timestamp, tool_idx)
                                    print("-------new end timestamp is found")
                
                else: # invalid tool value or not a new tool value (repeated)
                    for (uuid, part_number), transitions in part_operations.items():
                        tool_idx = transitions.get("tool_idx")  # Fetch idx
                        
                        if last_start and last_start[0] == transitions['start_transition'][0]: # find corresponding part number for the latest operation.
                                # if all 1st, 2nd, 3rd elements in queue form end transition
                                if (queue[0][0], queue[1][0], queue[2][0]) == (transitions['end_transition'][0], transitions['end_transition'][1], transitions['end_transition'][2]):
                                        # find timestamp of "STOPPED" value of dataitemid = "execution_status" that is greater than or equal to the most recent "timestamp"
                                        #  rely on mtc_event or get it through request. mtc_event will be easier.
                                        timestamp_src = None
                                        new_timestamp = None

                                        # print("DEBUG: match condition:", queue[-1][-1] == sequence)
                                                                                
                                        if (queue[-1][-1] == sequence): # if repeated value (the most recent tool value is already in the queue), find if execution is stopped, bring oldest timestamp
                                            # print("most recent timestamp: ", timestamp)
                                            def format_timestamp(timestamp):
                                                if timestamp and isinstance(timestamp, str) and 'T' in timestamp and 'Z' in timestamp:
                                                    # Convert from ISO8601 string to datetime object
                                                    dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
                                                    # Subtract 4 hours
                                                    dt_local = dt - timedelta(hours=4)
                                                    # Return in MySQL-compatible format
                                                    return dt_local.strftime("%Y-%m-%d %H:%M:%S.%f") # Trim to microseconds like DB format
                                                return timestamp
                                            temp = format_timestamp(timestamp)
                                            # print("formatted timestamp :", temp)

                                            # Metric key indicating current status of the machine — e.g., stopped, interrupted, etc.
                                            metric_key = 'execution_status'

                                            execution_query = f"""
                                                SELECT timestamp 
                                                FROM mtc_event 
                                                WHERE dataitemid = '{metric_key}' 
                                                AND (value = 'STOPPED' OR value = 'PROGRAM_STOPPED' OR value = 'FEED_HOLD')
                                                AND timestamp > '{temp}'
                                                ORDER BY timestamp ASC LIMIT 1
                                            """

                                            result = execute_query(execution_query)
                                            if result:
                                                new_timestamp = result[0]
                                                timestamp_src = 'Mpexecution'
                                                # print(timestamp_src, new_timestamp)
                                            # else: 
                                                # print("no pexecution timestamp")
                                                                

                                        if (value == None or value == "UNAVAILABLE" or value == ""): # if current value is invalid
                                            if new_timestamp == None or new_timestamp > timestamp:
                                                new_timestamp = timestamp # bring timestamp of the invalid value (which is the timestmap after the third tool in end_trnasition)
                                                timestamp_src = 'most recent tool'
                                                print(timestamp_src, new_timestamp)


                                        if (new_timestamp): 
                                            query_return(uuid, part_number, last_start[1], new_timestamp, tool_idx) # pass 
                                            # print("-------new end timestamp is found from //", timestamp_src)
                        
            else: # if first iter, process buffer
                data = []
                for elem in root.iter():
                    value = elem.text.strip() if elem.text and elem.text.strip() != "UNAVAILABLE" and elem.text.strip() != "" else None
                    print("first iter: ", value)
                    if value and value.isdigit():  # not empty and numeric
                        value = int(value)
                        sequence = elem.attrib.get('sequence', 'N/A')
                        timestamp = elem.attrib.get('timestamp', 'N/A')
                        data.append([value, timestamp, sequence])
                        if value != None and value != "UNAVAILABLE" and value != "": 
                            queue.append([value, timestamp, sequence]) # filter out any non-tool number value

                find_operation(data)

            # print(value, timestamp, sequence) 

            link_updated = link+"?from="+nextSeq

            # add to queue if value is valid and sequence is not in the queue
            if value not in (None, "UNAVAILABLE", "") and len(queue) > 2 and len(queue[2]) > 2 and sequence != queue[2][2]:
                queue.append([int(value), timestamp, sequence])
                # last_avail_seq_queue = [int(value), timestamp, sequence] # filter out any non-tool number value
            
            first_iter = False
        else: # In case of machine is unavailable continuously.
            print("Machine is ", response)
            #print("Nothing happens....")

    else:
        if response == "AVAILABLE": # In case machine availability is changed from unavailable to available, which means machine turned on just before.
            print("Machine is ", response)
        else: # In case machine availability is changed from available to unavailable, which means machine turned off just before.
            print("Machine is ", response) 
    response_updated = response
    time.sleep(1)
    end = time.time()



    