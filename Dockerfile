FROM debian

# Install Python Setuptools
RUN apt-get update && apt-get install -y python-pip ca-certificates --no-install-recommends

# Bundle app source
ADD . /src

# Install test requirements
RUN pip install mock ansicolors

# Initialize app environment
WORKDIR /src
RUN python setup.py install
