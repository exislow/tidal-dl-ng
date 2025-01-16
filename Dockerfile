# Official python 3.12 container image
FROM python:3.12-slim-bookworm

# Set the working directory in the container to /app
WORKDIR /app

# Updating repos
RUN apt update 

# Installing nano just in case one need to edit something in the container, installing ffmpeg for tidal-dl-ng
RUN apt install -y nano ffmpeg

#Installing tidal-dl-ng from pip
RUN pip install --upgrade tidal-dl-ng

# Creating a user appuser to group users
RUN useradd -m -u 1000 -g users appuser 

# Getting ownership of user's home folder
RUN chown appuser:users -R /home/appuser/ && chmod -R 755 /home/appuser
ADD settings.json /home/appuser/.config/tidal_dl_ng/settings.json
RUN chown appuser:users /home/appuser/.config/tidal_dl_ng/settings.json 
RUN chmod 775 /home/appuser/.config/tidal_dl_ng/settings.json
# As appuser :
USER appuser

# Creating config folder for tidal-dl-ng and music folder 
RUN mkdir -p /home/appuser/.config/tidal_dl_ng/
RUN mkdir -p /home/appuser/music
# RUN chown appuser:users -R /home/appuser/music && chmod -R 755 /home/appuser/music


# Working directory is appuser's home
WORKDIR /home/appuser/

# Default command if none provided is bash shell
CMD ["/bin/bash"]
