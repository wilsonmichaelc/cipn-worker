#!/usr/bin/python

import os, sys, subprocess, time, shutil, re, json, logging, mysql.connector
from job import Job
from pyfcm import FCMNotification

with open('config.json', 'r') as f:
    config = json.load(f)
    f.close()

logging.basicConfig(filename=config["LOG_FILE_NAME"],level=logging.DEBUG)
push_service = FCMNotification(api_key=config["FCM_API_KEY"])

def connection():
    conn = mysql.connector.connect(user=config['user'], password=onfig['password'], host=onfig['host'], port=onfig['port'], database=onfig['database'])
    return conn

def fetchJob():
    conn = connection()
    cursor = conn.cursor()
    querySelect = ("SELECT * FROM cipn.jobs WHERE status='submitted' LIMIT 1")
    cursor.execute(querySelect)
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row is not None:
        job = Job(row[0], row[1], row[3], row[4], row[5], row[8])
        return job
    else:
        return None

def updateStatus(id, status):
    conn = connection()
    cursor = conn.cursor()
    queryUpdate = "UPDATE jobs SET status='%s' WHERE id = %d" % (status, id,)
    cursor.execute(queryUpdate)
    conn.commit()
    cursor.close()
    conn.close()
    # TODO: Add code to verify success

def updateResult(id, results):
    conn = connection()
    cursor = conn.cursor()
    queryUpdate = "UPDATE jobs SET results='%s' WHERE id = %d" % (results, id,)
    cursor.execute(queryUpdate)
    conn.commit()
    cursor.close()
    conn.close()
    # TODO: Add code to verify success

def sendPush(device, message):
    logging.debug('Sending push notification to %s ...' % device)
    resultData = push_service.notify_single_device(registration_id=device, data_message=message)
    resultNotice = push_service.notify_single_device(registration_id=device, message_title="CIPN", message_body="Results are in...")
    logging.debug(resultData)
    logging.debug(resultNotice)

def executeJob(job):
    # New path for this job based on unique id
    path = "j%d" % (job.id,)
    # create new directory for this job
    os.makedirs(path)
    # copy the mod file into the new directory
    shutil.copy2('run.mod', path)
    # change to the new directory
    owd = os.getcwd()
    os.chdir(path)
    # write out the csv file
    df = open("data.csv", "w")
    df.write(job.data)
    df.close()

    # execute the job
    run = subprocess.Popen(["/usr/bin/execute", "run.mod"], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    err, out = run.communicate()

    if not err:
        times, ipred = [], []
        rdf = {}
        with open("plotme.tab", "r") as f:
            for line in f:
                line = line.strip()
                parts = re.split('\s+', line)
                t = float(parts[1])
                i = float(parts[2])
                times.append(float("{0:.2f}".format(t)))
                ipred.append(float("{0:.2f}".format(i)))
        f.close()
        rdf["times"] = times
        rdf["ipred"] = ipred
        job.results = rdf
    else:
        job.results = "error"
    os.chdir(owd)
    shutil.rmtree(path)
    return job

while True:
    try:
        job = fetchJob()
        if job is None:
            #print("No Jobs Found. Sleeping 10 seconds.")
            #logging.debug("No jobs. Sleeping 10 seconds...")
            time.sleep(10)
        else:
            #print("Executing Job: %d" % job.id)
            logging.debug("Executing Job: %d" % job.id)
            updateStatus(job.id, "running")
            job = executeJob(job)
            if job.results is "error":
                updateStatus(job.id, "error")
                if job.device:
                    message = {
                        "id": job.id,
                        "status": "error",
                        "results": ""
                    }
                    sendPush(job.device, message)
                logging.debug("Job failed.")
            else:
                updateResult(job.id, json.dumps(job.results))
                updateStatus(job.id, "done")
                if job.device:
                    message = {
                        "id": job.id,
                        "status": "done",
                        "results": job.results
                    }
                    sendPush(job.device, message)
                logging.debug("Job complete.")
    except Exception:
        pass
