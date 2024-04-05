# Use the official Python image as the base image
FROM python:3.9

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install the project dependencies and gunicorn
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy the application code to the working directory
COPY . .

# Set the environment variables if necessary
# ENV VARIABLE_NAME=value

# Expose port 5000
EXPOSE 5000

# Start the Gunicorn server
CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:5000"]
