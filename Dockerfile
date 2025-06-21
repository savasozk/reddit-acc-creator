# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements files into the container at /app
COPY requirements.txt requirements.dev.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Set environment variables from .env file (though these should be managed by Docker Compose)
# Note: This is more for documentation; docker-compose is the right way to manage this.
ARG CAPS_KEY
ARG CAPTCHA_2_KEY
ARG ADSPOWER_GROUP_ID

ENV CAPS_KEY=${CAPS_KEY}
ENV CAPTCHA_2_KEY=${CAPTCHA_2_KEY}
ENV ADSPOWER_GROUP_ID=${ADSPOWER_GROUP_ID}

# Command to run the application
CMD ["python", "-m", "src.main"] 