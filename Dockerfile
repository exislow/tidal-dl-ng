# Official python 3.12 container image
FROM python:3.12-slim-bookworm

# Set the working directory in the container to /app
WORKDIR /app

# Updating repos
RUN apt update 

# Installing installing ffmpeg for tidal-dl-ng
RUN apt install -y ffmpeg

#Installing tidal-dl-ng from pip
RUN pip install --upgrade tidal-dl-ng

# Creating a user appuser to group users
RUN useradd -m -u 1000 -g users appuser 

# Creating .config and msuci folders and getting ownership of appuser's home folder
RUN mkdir -p /home/appuser/.config/tidal_dl_ng/
RUN mkdir -p /home/appuser/music
RUN chown appuser:users -R /home/appuser/ && chmod -R 755 /home/appuser/

# As appuser :
USER appuser

# Configuring ffmpeg and deownload path
RUN tidal-dl-ng cfg path_binary_ffmpeg /usr/bin/ffmpeg
RUN tidal-dl-ng cfg download_base_path /home/appuser/music

# Working directory is appuser's home
WORKDIR /home/appuser/

# Default command if none provided is bash shell
CMD ["/bin/bash"]
