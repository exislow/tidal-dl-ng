# Official python 3.12 container image
FROM python:3.12-slim-bookworm


# Environment variables 

# Name of the user that will be created
ENV USER_NAME="appuser"

# Name of the group in which the user will be added
ENV GROUP_NAME="users"

# Created user's ID
ENV UID="1000"

# User's home path
ENV HOME_PATH="/home/appuser"

# User's music directory 
ENV MUSIC_PATH="${HOME_PATH}/music"



# Set the working directory in the container to /app
WORKDIR /app

# Updating repos
RUN apt update 

# Installing ffmpeg for tidal-dl-ng from apt
RUN apt install -y ffmpeg

# Installing tidal-dl-ng from pip
RUN pip install --upgrade tidal-dl-ng

# Creating a user appuser belonging to group users along with its home directory
RUN useradd -m -u ${UID} -g ${GROUP_NAME} ${USER_NAME} 

# As appuser :
USER ${USER_NAME}

# Creating music folder
RUN mkdir -p ${MUSIC_PATH}

# Configuring ffmpeg and deownload path fir tidal-dl-ng
RUN tidal-dl-ng cfg path_binary_ffmpeg $(which ffmpeg)
RUN tidal-dl-ng cfg download_base_path ${MUSIC_PATH}

# Working directory is appuser's home
WORKDIR ${HOME_PATH}

# Default command if none provided is bash shell
CMD ["/bin/bash"]
