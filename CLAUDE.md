This is a fastapi project that allows user to register a gmail account and a background thread processes emails to delete them or categorize them.
This project runs as a Docker container.
The database it persists data on is Mysql.
The database schemas get applied from ./sql folder.
Dockerfile has entrypoint that applied database schemas using flyway.

