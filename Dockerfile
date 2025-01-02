# Use a lightweight base image with Python
FROM python:3.9-slim

# Set a working directory
WORKDIR /app

# Install necessary system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libxkbcommon-x11-0 \
    libnss3-dev \
    libglib2.0-0 \
    libxshmfence1 \
    libxrandr2 \
    libxcomposite1 \
    libasound2 \
    libpangocairo-1.0-0 \
    fonts-liberation \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -qO /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get update && apt-get install -y --no-install-recommends /tmp/google-chrome.deb && \
    rm /tmp/google-chrome.deb && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver with fallback handling
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d'.' -f1-2) && \
    echo "Detected Chrome version: $CHROME_VERSION" && \
    wget -qO /tmp/LATEST_RELEASE "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION" || \
    wget -qO /tmp/LATEST_RELEASE "https://chromedriver.storage.googleapis.com/LATEST_RELEASE" && \
    CHROMEDRIVER_VERSION=$(cat /tmp/LATEST_RELEASE) && \
    echo "Using ChromeDriver version: $CHROMEDRIVER_VERSION" && \
    wget -q https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip && \
    mv chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm chromedriver_linux64.zip /tmp/LATEST_RELEASE

# Install Playwright and browsers
RUN pip install --no-cache-dir playwright && \
    playwright install && \
    playwright install-deps

# Copy requirements and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Selenium script into the container
COPY script_om.py /app/script_om.py
COPY config.xml /app/config.xml
COPY CloudflareBypasser.py /app/CloudflareBypasser.py

RUN ls -l /app

# Expose the display port (for debugging with GUI)
ENV DISPLAY=:99

# Run the script by default
CMD ["python", "script_om.py"]
