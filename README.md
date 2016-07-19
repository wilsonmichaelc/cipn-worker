## This is a simple python app for fetching queued jobs from a database, running them, updating the results, and sending a push notification to the device that submitted the job.

#### 1. Edit the cipn upstart config file to match your system.

```python
# Set the user and group to run as
setuid cipn_user
setgid some_group
# Change directory to the path of the worker
chdir /opt/cipn/worker
# Execute the worker script
exec /usr/bin/python3 /opt/cipn/worker/worker.py
```

#### 2. Copy the upstart config file to /etc/init/

#### 3. Copy the worker directory to the location specified above

#### 4. Start the service

```bash
service cipn start
```
