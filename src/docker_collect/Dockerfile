# FROM python:3.9

# # Install Google Chrome (2023.10.11)
# RUN wget https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_132.0.6834.83-1_amd64.deb
# RUN apt-get -y update && apt-get install -y ./google-chrome-stable_132.0.6834.83-1_amd64.deb

# # Install ChromeDriver
# RUN apt-get install -yqq unzip
# RUN wget https://storage.googleapis.com/chrome-for-testing-public/132.0.6834.83/linux64/chromedriver-linux64.zip
# RUN unzip chromedriver-linux64.zip 
# RUN mv /chromedriver-linux64/chromedriver /usr/local/bin/

# # Set working directory
# WORKDIR /app

# # Copy application files
# COPY ./ksubscribe_share /app/ksubscribe_share
# COPY ./docker_collect /app/docker_collect

# # Add __init__.py to docker_collect if missing
# RUN touch /app/docker_collect/__init__.py

# # Install shared library
# RUN pip install --no-cache-dir /app/ksubscribe_share

# # Upgrade pip
# RUN pip install --no-cache-dir --upgrade pip

# # Install Python dependencies
# RUN pip install --no-cache-dir -r /app/docker_collect/requirements.txt

# # Set PYTHONPATH to include /app
# ENV PYTHONPATH=/app

# # Command to execute the script
# CMD ["python", "docker_collect/collect_v2.py"]


FROM python:3.9

# Install Google Chrome and its dependencies
RUN wget -q https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_132.0.6834.83-1_amd64.deb && \
    apt-get -y update && apt-get install -y ./google-chrome-stable_132.0.6834.83-1_amd64.deb && \
    rm google-chrome-stable_132.0.6834.83-1_amd64.deb && \
    apt-get clean && rm -rf /var/lib/apt/lists/*



# Install ChromeDriver
RUN wget -q https://storage.googleapis.com/chrome-for-testing-public/132.0.6834.83/linux64/chromedriver-linux64.zip && \
    unzip chromedriver-linux64.zip && \
    mv chromedriver-linux64/chromedriver /usr/local/bin/ && \
    rm -rf chromedriver-linux64.zip chromedriver-linux64

# Set working directory
WORKDIR /app

# Copy application files
COPY ./ksubscribe_share /app/ksubscribe_share
COPY ./docker_collect /app/docker_collect

# Add __init__.py to docker_collect if missing
RUN touch /app/docker_collect/__init__.py

# Install shared library
RUN pip install --no-cache-dir /app/ksubscribe_share

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/docker_collect/requirements.txt

# Set PYTHONPATH to include /app
ENV PYTHONPATH=/app

# Command to execute the script
CMD ["python", "docker_collect/collect_v2.py"]

