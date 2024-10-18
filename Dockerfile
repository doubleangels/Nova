FROM python:3.12.5-slim

ADD main.py .

RUN pip install -U pip

RUN pip install -U discord-py-interactions pickledb

CMD [ "python", "-u", "./main.py" ]